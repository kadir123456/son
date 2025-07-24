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
        self.status = {"is_running": False, "symbol": None, "in_position": False, "status_message": "Bot başlatılmadı.", "last_signal": "N/A", "entry_price": 0.0, "position_side": None}
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
        self.status.update({"is_running": True, "symbol": symbol, "in_position": False, "status_message": f"{symbol} için başlatılıyor..."})
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
        # İki görevi (piyasa dinleme ve emir dinleme) aynı anda çalıştır
        await asyncio.gather(
            self.listen_market_stream(),
            self.listen_user_stream()
        )
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
            print(f"Yeni mum kapandı: {self.status['symbol']} ({settings.TIMEFRAME}) - Kapanış: {data['k']['c']}")
            self.klines.pop(0); self.klines.append([data['k'][key] for key in ['t','o','h','l','c','v','T','q','n','V','Q']] + ['0'])
            
            if self.status["in_position"]:
                # --- DEĞİŞİKLİK BURADA YAPILDI ---
                # Fonksiyona artık doğru şekilde 'symbol' gönderiliyor.
                open_positions = await binance_client.get_open_positions(self.status["symbol"])
                if not any(p['symbol'] == self.status['symbol'] for p in open_positions):
                    print(f"--> Pozisyon kapandığı periyodik kontrol ile tespit edildi. Durum sıfırlanıyor.")
                    self.status.update({"in_position": False, "status_message": f"{self.status['symbol']} için sinyal bekleniyor..."})
                else:
                    print("--> Pozisyon açık, yeni sinyal aranmıyor. Emir durumu bekleniyor.")
            
            if not self.status["in_position"]:
                signal = trading_strategy.analyze_klines(self.klines)
                self.status["last_signal"] = signal; print(f"Strateji analizi sonucu: {signal}")
                if signal in ["LONG", "SHORT"]: 
                    await self._execute_trade(signal)

    async def _handle_user_message(self, message: dict):
        if message.get('e') == 'ORDER_TRADE_UPDATE':
            order_data = message.get('o', {})
            symbol = order_data.get('s')
            order_status = order_data.get('X')
            order_type = order_data.get('o')
            if symbol == self.status['symbol'] and self.status["in_position"]:
                if order_status == 'FILLED' and order_type in ['TAKE_PROFIT_MARKET', 'STOP_MARKET']:
                    print(f"--> GERÇEK ZAMANLI TESPİT: {symbol} için {order_type} emri doldu! Yetim emirler temizleniyor.")
                    await binance_client.cancel_all_symbol_orders(symbol)
                    closed_pnl = float(order_data.get('rp', 0.0))
                    trade_log = {"symbol": symbol, "side": self.status.get("position_side"), "entry_price": self.status.get("entry_price"), "exit_price": float(order_data.get('p')), "status": f"CLOSED_BY_{order_type}", "pnl": closed_pnl, "timestamp": datetime.now(timezone.utc)}
                    firebase_manager.log_trade(trade_log)
                    self.status.update({"in_position": False, "status_message": f"{self.status['symbol']} için sinyal bekleniyor..."})
    
    def _format_quantity(self, quantity: float):
        if self.quantity_precision == 0: return math.floor(quantity)
        factor = 10 ** self.quantity_precision; return math.floor(quantity * factor) / factor
        
    async def _execute_trade(self, signal: str):
        symbol = self.status["symbol"]; side = "BUY" if signal == "LONG" else "SELL"
        await binance_client.cancel_all_symbol_orders(symbol)
        await asyncio.sleep(0.2)
        self.status["status_message"] = f"{signal} sinyali alındı..."; print(self.status["status_message"])
        price = await binance_client.get_market_price(symbol)
        if not price: self.status["status_message"] = "İşlem için fiyat alınamadı."; return
        quantity = self._format_quantity((settings.ORDER_SIZE_USDT * settings.LEVERAGE) / price)
        print(f"Hesaplanan Miktar: {quantity} {symbol.replace('USDT','')}")
        if quantity <= 0: print("Hesaplanan miktar çok düşük, emir gönderilemiyor."); return
        order = await binance_client.create_market_order_with_tp_sl(symbol, side, quantity, price, self.price_precision)
        if order:
            self.status.update({"in_position": True, "status_message": f"{signal} pozisyonu {price} fiyattan açıldı.", "entry_price": price, "position_side": signal})
        else:
            self.status.update({"status_message": "Emir gönderilemedi.", "in_position": False})
        print(self.status["status_message"])

bot_core = BotCore()
