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
        self.status["status_message"] = f"{symbol} ({settings.TIMEFRAME}) için döngü bekleniyor..."
        await asyncio.gather(self.listen_market_stream(), self.listen_user_stream())
        await self.stop()

    # --- YENİ: OTOMATİK YENİDEN BAĞLANMA DÖNGÜSÜ ---
    async def listen_market_stream(self):
        ws_url = f"{settings.WEBSOCKET_URL}/ws/{self.status['symbol'].lower()}@kline_{settings.TIMEFRAME}"
        while not self._stop_requested:
            try:
                async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20) as ws:
                    print(f"Ana döngü ({settings.TIMEFRAME}) dinleniyor: {ws_url}")
                    while not self._stop_requested:
                        try:
                            message = await asyncio.wait_for(ws.recv(), timeout=60.0)
                            await self._handle_websocket_message(message)
                        except asyncio.TimeoutError:
                            print("WebSocket 60 saniyedir mesaj göndermiyor, bağlantı kontrol ediliyor...")
                            # Ping mekanizması bu durumu yönetmeli, ama yine de devam et
                            continue
                        except websockets.exceptions.ConnectionClosed:
                            print("WebSocket bağlantısı kapandı. Yeniden bağlanılacak...")
                            break # İç döngüden çıkıp yeniden bağlanmayı tetikle
            except Exception as e:
                print(f"Ana döngü bağlantı hatası: {e}. 5 saniye sonra yeniden denenecek.")
                await asyncio.sleep(5)

    async def listen_user_stream(self):
        await binance_client.start_user_stream(self._handle_user_message)
    async def stop(self):
        self._stop_requested = True
        if self.status["is_running"]:
            self.status.update({"is_running": False, "status_message": "Bot durduruldu."})
            print(self.status["status_message"]); await binance_client.close()
            
    async def _handle_websocket_message(self, message: str):
        data = json.loads(message)
        if not data.get('k', {}).get('x', False): return
        
        kline_data = data['k']
        open_price_of_new_candle = float(kline_data['c'])
        
        print(f"--- {settings.TIMEFRAME} Mum Kapandı: Yeni Analiz Döngüsü Başlıyor ---")
        
        print("Strateji gereği 30 saniye bekleniyor...")
        await asyncio.sleep(30)
        
        current_price = await binance_client.get_market_price(self.status["symbol"])
        if not current_price:
            print("Uyarı: Anlık fiyat alınamadı, döngü atlanıyor.")
            return
            
        signal = "HOLD"
        if current_price > open_price_of_new_candle:
            signal = "LONG"
        elif current_price < open_price_of_new_candle:
            signal = "SHORT"
        
        print(f"30 saniye sonraki duruma göre yön: {signal} (Açılış: {open_price_of_new_candle}, Anlık: {current_price})")

        if signal != "HOLD" and signal != self.status.get("position_side"):
            await self._flip_position(signal, current_price)
        else:
            print(f"Yön aynı ({signal}), mevcut pozisyon korunuyor veya beklemeye devam ediliyor.")

    async def _handle_user_message(self, message: dict):
        if message.get('e') == 'ORDER_TRADE_UPDATE':
            order_data = message.get('o', {})
            symbol = order_data.get('s')
            if symbol == self.status['symbol'] and self.status.get("position_side") is not None:
                if order_data.get('X') == 'FILLED' and order_data.get('o') in ['TAKE_PROFIT_MARKET', 'STOP_MARKET']:
                    print(f"--> GERÇEK ZAMANLI TESPİT: {symbol} için {order_data.get('o')} emri doldu!")
                    await self.close_and_log_position(f"CLOSED_BY_{order_data.get('o')}", float(order_data.get('p')))

    async def close_and_log_position(self, status_text: str, exit_price: float):
        await binance_client.cancel_all_symbol_orders(self.status["symbol"])
        pnl = await binance_client.get_last_trade_pnl(self.status["symbol"])
        trade_log = {"symbol": self.status["symbol"], "side": self.status.get("position_side"), "entry_price": self.status.get("entry_price"), "exit_price": exit_price, "status": status_text, "pnl": pnl, "timestamp": datetime.now(timezone.utc)}
        firebase_manager.log_trade(trade_log)
        self.status["position_side"] = None

    def _format_quantity(self, quantity: float):
        if self.quantity_precision == 0: return math.floor(quantity)
        factor = 10 ** self.quantity_precision; return math.floor(quantity * factor) / factor

    async def _flip_position(self, new_signal: str, entry_price: float):
        symbol = self.status["symbol"]
        
        open_positions = await binance_client.get_open_positions(symbol)
        if open_positions:
            position = open_positions[0]
            position_amt = float(position['positionAmt'])
            side_to_close = 'SELL' if position_amt > 0 else 'BUY'
            print(f"--> Yön Değişikliği: Mevcut {self.status['position_side']} pozisyonu kapatılıyor...")
            await binance_client.close_position(symbol, position_amt, side_to_close)
            await asyncio.sleep(1)
            await self.close_and_log_position("CLOSED_BY_FLIP", entry_price)

        print(f"--> Yeni {new_signal} pozisyonu açılıyor...")
        side = "BUY" if new_signal == "LONG" else "SELL"
        quantity = self._format_quantity((settings.ORDER_SIZE_USDT * settings.LEVERAGE) / entry_price)
        if quantity <= 0: print("Hesaplanan miktar çok düşük."); self.status["position_side"] = None; return

        order = await binance_client.create_market_order_with_tp_sl(symbol, side, quantity, entry_price, self.price_precision)
        if order:
            self.status["position_side"] = new_signal
            self.status["entry_price"] = entry_price
            self.status["status_message"] = f"Yeni {new_signal} pozisyonu {entry_price} fiyattan açıldı."
        else:
            self.status["position_side"] = None
            self.status["status_message"] = "Yeni pozisyon açılamadı."
        print(self.status["status_message"])

bot_core = BotCore()
