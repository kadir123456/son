import asyncio
import time
from threading import Thread
from .binance_client import BinanceClient
from .trading_strategy import TradingStrategy
from .firebase_manager import FirebaseManager
from . import config

class BotCore(Thread):
    def __init__(self, user_id, api_key, api_secret, symbol):
        super().__init__()
        self.user_id = user_id
        self.symbol = symbol
        self.is_running = True
        
        self.client = BinanceClient(api_key, api_secret)
        self.strategy = TradingStrategy()
        self.db = FirebaseManager()

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.main_loop())

    async def main_loop(self):
        print(f"BOT BAŞLATILDI: Kullanıcı={self.user_id}, Parite={self.symbol}")
        
        while self.is_running:
            try:
                # 1. Bir sonraki mumun başlangıcını bekle
                self.wait_for_next_candle()
                if not self.is_running: break

                # 2. Hacim analizi için WebSocket'i başlat
                await self.client.connect_aggtrade_ws(self.symbol)
                await asyncio.sleep(config.ANALYSIS_DURATION_SECONDS)
                
                # 3. Veriyi topla ve WebSocket'i kapat
                trades = self.client.get_and_clear_aggtrade_data()
                await self.client.close_ws()

                # 4. Hacimleri hesapla
                buyer_volume = sum(trade['q'] for trade in trades if not trade['m'])
                seller_volume = sum(trade['q'] for trade in trades if trade['m'])
                
                # 5. Stratejiden sinyal al
                current_price = await self.client.get_current_price(self.symbol)
                ema_filter = await self.client.get_ema(self.symbol, config.TREND_FILTER_TIMEFRAME, config.TREND_FILTER_EMA_PERIOD)
                signal = self.strategy.get_signal(buyer_volume, seller_volume, current_price, ema_filter)

                # 6. Sinyal varsa işlem yap
                if signal:
                    await self.execute_trade(signal, current_price)

            except Exception as e:
                print(f"HATA: Bot ana döngüsünde hata (Kullanıcı: {self.user_id}): {e}")
                self.db.log_error(self.user_id, str(e))
                await asyncio.sleep(60)

        await self.client.close_connection()
        print(f"BOT DURDURULDU: Kullanıcı={self.user_id}")

    async def execute_trade(self, side, entry_price):
        try:
            quantity = (config.POSITION_SIZE_USDT * config.LEVERAGE) / entry_price
            order = await self.client.create_market_order(self.symbol, side, quantity)
            print(f"İŞLEM BAŞARILI: {side.upper()} @ {entry_price}")
            self.db.save_trade(self.user_id, order)
            # Not: TP/SL emirleri de burada client üzerinden gönderilmeli.
        except Exception as e:
            print(f"İŞLEM HATASI (Kullanıcı: {self.user_id}): {e}")

    def wait_for_next_candle(self):
        current_time = time.time()
        wait_time = config.TIMEFRAME_SECONDS - (current_time % config.TIMEFRAME_SECONDS)
        print(f"Bir sonraki mum için {wait_time:.2f} saniye bekleniyor...")
        time.sleep(wait_time)

    def stop(self):
        self.is_running = False
