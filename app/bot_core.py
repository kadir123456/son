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
        ws_url = f"{settings.WEBSOCKET_URL}/ws/{symbol.lower()}@kline_{settings.TIMEFRAME}"
        try:
            async with websockets.connect(ws_url, ping_interval=30, ping_timeout=15) as ws:
                print(f"WebSocket bağlantısı kuruldu: {ws_url}")
                while not self._stop_requested:
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=60.0)
                        await self._handle_websocket_message(message)
                    except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
                        print("Piyasa veri akışı bağlantı sorunu..."); await asyncio.sleep(5); break
        except Exception as e: print(f"WebSocket bağlantı hatası: {e}")
        await self.stop()
        
    async def stop(self):
        self._stop_requested = True
        if self.status["is_running"]:
            self.status.update({"is_running": False, "status_message": "Bot durduruldu."})
            print(self.status["status_message"]); await binance_client.close()
            
    async def _handle_websocket_message(self, message: str):
        data = json.loads(message)
        if not data.get('k', {}).get('x', False): return
            
        print(f"Yeni mum kapandı: {self.status['symbol']} ({settings.TIMEFRAME}) - Kapanış: {data['k']['c']}")
        self.klines.append([data['k'][key] for key in ['t','o','h','l','c','v','T','q','n','V','Q']] + ['0'])
        if len(self.klines) > 50: self.klines.pop(0)
        
        # Her mumda pozisyonu SL olup olmadığını kontrol et
        open_positions = await binance_client.get_open_positions(self.status["symbol"])
        if self.status["position_side"] is not None and not open_positions:
            print(f"--> Pozisyon SL ile kapandı. Yeni sinyal bekleniyor.")
            pnl = await binance_client.get_last_trade_pnl(self.status["symbol"])
            firebase_manager.log_trade({"symbol": self.status["symbol"], "pnl": pnl, "status": "CLOSED_BY_SL", "timestamp": datetime.now(timezone.utc)})
            self.status["position_side"] = None

        # Yeni sinyali al
        signal = trading_strategy.analyze_klines(self.klines)
        print(f"Strateji analizi sonucu: {signal}")

        # Eğer sinyal varsa ve mevcut pozisyonla aynı değilse, pozisyonu döndür
        if signal != "HOLD" and signal != self.status.get("position_side"):
            await self._flip_position(signal)

    def _format_quantity(self, quantity: float):
        if self.quantity_precision == 0: return math.floor(quantity)
        factor = 10 ** self.quantity_precision; return math.floor(quantity * factor) / factor

    async def _flip_position(self, new_signal: str):
        symbol = self.status["symbol"]
        
        # 1. Adım: Mevcut bir pozisyon varsa kapat
        open_positions = await binance_client.get_open_positions(symbol)
        if open_positions:
            position = open_positions[0]
            position_amt = float(position['positionAmt'])
            side_to_close = 'SELL' if position_amt > 0 else 'BUY'
            print(f"--> Ters sinyal geldi. Mevcut {self.status['position_side']} pozisyonu kapatılıyor...")
            await binance_client.close_position(symbol, position_amt, side_to_close)
            await asyncio.sleep(1)
            pnl = await binance_client.get_last_trade_pnl(symbol)
            firebase_manager.log_trade({"symbol": symbol, "pnl": pnl, "status": "CLOSED_BY_FLIP", "timestamp": datetime.now(timezone.utc)})

        # 2. Adım: Yeni pozisyonu aç
        print(f"--> Yeni {new_signal} pozisyonu açılıyor...")
        side = "BUY" if new_signal == "LONG" else "SELL"
        price = await binance_client.get_market_price(symbol)
        if not price: print("Yeni pozisyon için fiyat alınamadı."); return
        quantity = self._format_quantity((settings.ORDER_SIZE_USDT * settings.LEVERAGE) / price)
        if quantity <= 0: print("Hesaplanan miktar çok düşük."); return

        order = await binance_client.create_market_order_with_sl(symbol, side, quantity, price, self.price_precision)
        if order:
            self.status["position_side"] = new_signal
            self.status["status_message"] = f"Yeni {new_signal} pozisyonu {price} fiyattan açıldı."
        else:
            self.status["position_side"] = None
            self.status["status_message"] = "Yeni pozisyon açılamadı."
        print(self.status["status_message"])

bot_core = BotCore()
