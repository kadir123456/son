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
        self.status = {
            "is_running": False, "symbol": None, "in_position": False,
            "status_message": "Bot başlatılmadı.", "last_signal": "N/A",
            "entry_price": 0.0, "highest_price": 0.0, "lowest_price": 0.0, "position_side": None
        }
        self.klines, self._stop_requested, self.quantity_precision, self.price_precision = [], False, 0, 0
        self.position_tracker_task = None
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
        await asyncio.gather(self.listen_market_stream(), self.listen_user_stream())
        await self.stop()

    async def listen_market_stream(self):
        ws_url = f"{settings.WEBSOCKET_URL}/ws/{self.status['symbol'].lower()}@kline_{settings.TIMEFRAME}"
        try:
            async with websockets.connect(ws_url, ping_interval=30, ping_timeout=15) as ws:
                print(f"Piyasa veri akışı kuruldu: {ws_url}")
                while not self._stop_requested:
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=60.0)
                        await self._handle_market_message(message)
                    except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
                        print("Piyasa veri akışı bağlantı sorunu, yeniden deneniyor..."); await asyncio.sleep(5); break
        except Exception as e: print(f"Piyasa veri akışı hatası: {e}")
    
    async def listen_user_stream(self):
        await binance_client.start_user_stream(self._handle_user_message)

    async def stop(self):
        self._stop_requested = True
        if self.position_tracker_task: self.position_tracker_task.cancel()
        if self.status["is_running"]:
            self.status.update({"is_running": False, "status_message": "Bot durduruldu."})
            print(self.status["status_message"]); await binance_client.close()

    async def _handle_market_message(self, message: str):
        # Bu fonksiyon artık sadece yeni sinyal aramakla görevli
        data = json.loads(message)
        if data.get('k', {}).get('x', False):
            print(f"Yeni mum kapandı: {self.status['symbol']} ({settings.TIMEFRAME}) - Kapanış: {data['k']['c']}")
            self.klines.pop(0); self.klines.append([data['k'][key] for key in ['t','o','h','l','c','v','T','q','n','V','Q']] + ['0'])
            if not self.status["in_position"]:
                signal = trading_strategy.analyze_klines(self.klines)
                self.status["last_signal"] = signal; print(f"Strateji analizi sonucu: {signal}")
                if signal in ["LONG", "SHORT"]: await self._execute_trade(signal)

    async def _handle_user_message(self, message: dict):
        # Bu fonksiyon, TP/SL ile kapanan işlemleri anında yakalar
        if message.get('e') == 'ORDER_TRADE_UPDATE':
            order_data = message.get('o', {})
            symbol = order_data.get('s')
            if symbol == self.status['symbol'] and self.status["in_position"]:
                if order_data.get('X') == 'FILLED' and order_data.get('o') in ['TAKE_PROFIT_MARKET', 'STOP_MARKET']:
                    print(f"--> GERÇEK ZAMANLI TESPİT: {symbol} için {order_data.get('o')} emri doldu!")
                    await self.close_and_log_position(f"CLOSED_BY_{order_data.get('o')}", float(order_data.get('p')))

    async def track_position_realtime(self):
        """Sadece pozisyon açıkken çalışır ve anlık fiyata göre Trailing Stop'u yönetir."""
        await binance_client.start_mark_price_stream(self.status['symbol'], self._handle_mark_price_update)

    async def _handle_mark_price_update(self, current_price: float):
        if not self.status["in_position"]:
            if self.position_tracker_task: self.position_tracker_task.cancel(); self.position_tracker_task = None
            return

        is_long = self.status["position_side"] == "LONG"
        entry_price = self.status["entry_price"]
        
        # Kâr koruma aktivasyonunu kontrol et
        activation_price = entry_price * (1 + settings.TRAILING_ACTIVATION_PERCENT) if is_long else entry_price * (1 - settings.TRAILING_ACTIVATION_PERCENT)
        trailing_active = (is_long and current_price > activation_price) or (not is_long and current_price < activation_price)
        
        if not trailing_active: return # Korumayı aktifleştirecek kadar kâra geçmediyse bekle

        # Zirve/Dip fiyatı güncelle
        if is_long:
            highest_price = self.status.get("highest_price", entry_price)
            if current_price > highest_price: self.status["highest_price"] = current_price
            trailing_stop_price = self.status["highest_price"] * (1 - settings.TRAILING_DISTANCE_PERCENT)
            if current_price < trailing_stop_price:
                print(f"--> ANLIK TESPİT: KÂR KORUMA (TRAILING STOP) TETİKLENDİ! Pozisyon kapatılıyor.")
                await self.close_and_log_position("CLOSED_BY_TRAILING_STOP", current_price)
        else: # SHORT
            lowest_price = self.status.get("lowest_price", entry_price)
            if current_price < lowest_price: self.status["lowest_price"] = current_price
            trailing_stop_price = self.status["lowest_price"] * (1 + settings.TRAILING_DISTANCE_PERCENT)
            if current_price > trailing_stop_price:
                print(f"--> ANLIK TESPİT: KÂR KORUMA (TRAILING STOP) TETİKLENDİ! Pozisyon kapatılıyor.")
                await self.close_and_log_position("CLOSED_BY_TRAILING_STOP", current_price)

    async def close_and_log_position(self, status_text: str, exit_price: float):
        if self.position_tracker_task: self.position_tracker_task.cancel(); self.position_tracker_task = None
        
        if status_text == "CLOSED_BY_TRAILING_STOP":
            await binance_client.close_open_position(self.status["symbol"])
        else:
            # TP/SL ile kapandıysa sadece "yetim" kalabilecek diğer emri temizle
            await binance_client.cancel_all_symbol_orders(self.status["symbol"])
        
        closed_pnl = await binance_client.get_last_trade_pnl(self.status["symbol"])
        trade_log = {"symbol": self.status["symbol"], "side": self.status.get("position_side"), "entry_price": self.status.get("entry_price"), "exit_price": exit_price, "status": status_text, "pnl": closed_pnl, "timestamp": datetime.now(timezone.utc)}
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
            self.status.update({"in_position": True, "status_message": f"{signal} pozisyonu {price} fiyattan açıldı.", "entry_price": price, "position_side": signal, "highest_price": price, "lowest_price": price})
            # Pozisyon açılınca anlık fiyat takibini başlat
            self.position_tracker_task = asyncio.create_task(self.track_position_realtime())
        else:
            self.status.update({"status_message": "Emir gönderilemedi.", "in_position": False})
        print(self.status["status_message"])

bot_core = BotCore()
