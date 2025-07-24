import asyncio
import json
import websockets
from .config import settings
from .binance_client import binance_client
from .trading_strategy import trading_strategy
from .firebase_manager import firebase_manager
from datetime import datetime, timezone
import math

class BotCore:
    def __init__(self):
        self.status = {"is_running": False, "symbol": None, "position_side": None, "status_message": "Bot başlatılmadı."}
        self.klines, self._stop_requested, self.quantity_precision, self.price_precision = [], False, 0, 0
    def _get_precision_from_filter(self, symbol_info, filter_type, key):
        for f in symbol_info['filters']:
            if f['filterType'] == filter_type:
                size_str = f[key]
                if '.' in size_str: return len(size_str.split('.')[1].rstrip('0'))
                return 0
        return 0
    async def start(self, symbol: str):
        if self.status["is_running"]: print("Bot zaten çalışıyor."); return
        self._stop_requested = False
        self.status.update({"is_running": True, "symbol": symbol, "position_side": None, "status_message": f"{symbol} için başlatılıyor..."})
        print(self.status["status_message"])
        await binance_client.initialize()
        symbol_info = await binance_client.get_symbol_info(symbol)
        if not symbol_info: self.status["status_message"] = f"{symbol} için borsa bilgileri alınamadı."; await self.stop(); return
        self.quantity_precision = self._get_precision_from_filter(symbol_info, 'LOT_SIZE', 'stepSize')
        self.price_precision = self._get_precision_from_filter(symbol_info, 'PRICE_FILTER', 'tickSize')
        print(f"{symbol} için Miktar Hassasiyeti: {self.quantity_precision}, Fiyat Hassasiyeti: {self.price_precision}")
        if not await binance_client.set_leverage(symbol, settings.LEVERAGE): self.status["status_message"] = "Kaldıraç ayarlanamadı."; await self.stop(); return
        self.klines = await binance_client.get_historical_klines(symbol, settings.TIMEFRAME, limit=50)
        if not self.klines: self.status["status_message"] = "Geçmiş veri alınamadı."; await self.stop(); return
        self.status["status_message"] = f"{symbol} ({settings.TIMEFRAME}) için sinyal bekleniyor..."
        await asyncio.gather(self.listen_market_stream(), self.listen_user_stream())
        await self.stop()
    async def listen_market_stream(self):
        ws_url = f"{settings.WEBSOCKET_URL}/ws/{self.status['symbol'].lower()}@kline_{settings.TIMEFRAME}"
        while not self._stop_requested:
            try:
                async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20) as ws:
                    print(f"Piyasa veri akışı kuruldu: {ws_url}")
                    while not self._stop_requested:
                        try:
                            message = await asyncio.wait_for(ws.recv(), timeout=60.0)
                            await self._handle_market_message(message)
                        except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
                            print("Piyasa veri akışı bağlantı sorunu, yeniden bağlanılıyor..."); break
            except Exception as e:
                print(f"Ana döngü bağlantı hatası: {e}. 5 saniye sonra yeniden denenecek."); await asyncio.sleep(5)
    async def listen_user_stream(self):
        await binance_client.start_user_stream(self._handle_user_message)
    async def stop(self):
        self._stop_requested = True
        if self.status["is_running"]:
            self.status.update({"is_running": False, "status_message": "Bot durduruldu."})
            print(self.status["status_message"]); await binance_client.close()
            
    async def _handle_market_message(self, message: str):
        data = json.loads(message)
        if data.get('k', {}).get('x', False):
            print(f"--- Yeni Mum Kapandı: {self.status['symbol']} ({settings.TIMEFRAME}) ---")
            self.klines.pop(0); self.klines.append([data['k'][key] for key in ['t','o','h','l','c','v','T','q','n','V','Q']] + ['0'])
            
            # Her mumda pozisyonu SL olup olmadığını kontrol et
            open_positions = await binance_client.get_open_positions()
            # Eğer bot pozisyonda olduğunu sanıyor ama Binance'te pozisyon yoksa (SL/TP ile kapanmış) durumu sıfırla
            if self.status["in_position"] and not any(p['symbol'] == self.status['symbol'] for p in open_positions):
                 print(f"--> Pozisyonun kapandığı periyodik kontrol ile tespit edildi. Durum sıfırlanıyor.")
                 self.status.update({"in_position": False})

            # Yeni sinyali al
            signal = trading_strategy.analyze_klines(self.klines)
            print(f"Strateji analizi sonucu: {signal}")

            # Eğer sinyal varsa ve mevcut pozisyonla aynı değilse, pozisyonu döndür
            if signal != "HOLD" and signal != self.status.get("position_side"):
                await self._flip_position(signal)

    async def _handle_user_message(self, message: dict):
        if message.get('e') == 'ORDER_TRADE_UPDATE':
            order_data = message.get('o', {})
            symbol = order_data.get('s')
            if symbol == self.status['symbol'] and self.status["in_position"]:
                if order_data.get('X') == 'FILLED' and order_data.get('o') in ['TAKE_PROFIT_MARKET', 'STOP_MARKET']:
                    print(f"--> GERÇEK ZAMANLI TESPİT: {symbol} için {order_data.get('o')} emri doldu! Yetim emirler temizleniyor.")
                    await binance_client.cancel_all_symbol_orders(symbol)
                    closed_pnl = float(order_data.get('rp', 0.0))
                    trade_log = {"symbol": symbol, "side": self.status.get("position_side"), "entry_price": self.status.get("entry_price"), "exit_price": float(order_data.get('p')), "status": f"CLOSED_BY_{order_data.get('o')}", "pnl": closed_pnl, "timestamp": datetime.now(timezone.utc)}
                    firebase_manager.log_trade(trade_log)
                    self.status.update({"in_position": False, "status_message": f"{self.status['symbol']} için sinyal bekleniyor..."})
    
    def _format_quantity(self, quantity: float):
        if self.quantity_precision == 0: return math.floor(quantity)
        factor = 10 ** self.quantity_precision; return math.floor(quantity * factor) / factor
        
    async def _flip_position(self, new_signal: str):
        symbol = self.status["symbol"]
        
        open_positions = await binance_client.get_open_positions()
        if open_positions and any(p['symbol'] == symbol for p in open_positions):
            position = next((p for p in open_positions if p['symbol'] == symbol), None)
            position_amt = float(position['positionAmt'])
            side_to_close = 'SELL' if position_amt > 0 else 'BUY'
            print(f"--> Yön Değişikliği: Mevcut {self.status['position_side']} pozisyonu kapatılıyor...")
            await binance_client.close_position(symbol, position_amt, side_to_close)
            await asyncio.sleep(1) # Pozisyonun kapandığından emin olmak için bekle
            pnl = await binance_client.get_last_trade_pnl(symbol)
            firebase_manager.log_trade({"symbol": symbol, "pnl": pnl, "status": "CLOSED_BY_FLIP", "timestamp": datetime.now(timezone.utc)})

        print(f"--> Yeni {new_signal} pozisyonu açılıyor...")
        side = "BUY" if new_signal == "LONG" else "SELL"
        price = await binance_client.get_market_price(symbol)
        if not price: self.status["status_message"] = "Yeni pozisyon için fiyat alınamadı."; return
        
        quantity = self._format_quantity((settings.ORDER_SIZE_USDT * settings.LEVERAGE) / price)
        if quantity <= 0: print("Hesaplanan miktar çok düşük, emir gönderilemiyor."); return

        order = await binance_client.create_market_order_with_tp_sl(symbol, side, quantity, price, self.price_precision)
        
        if order:
            self.status.update({"in_position": True, "status_message": f"Yeni {new_signal} pozisyonu {price} fiyattan açıldı.", "entry_price": price, "position_side": new_signal})
        else:
            self.status.update({"in_position": False, "status_message": "Yeni pozisyon açılamadı."})
        print(self.status["status_message"])

bot_core = BotCore()
