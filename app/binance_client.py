import asyncio
import websockets
import json
import ccxt.async_support as ccxt
from decimal import Decimal
from . import config

class BinanceClient:
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.exchange = ccxt.binance({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'options': {
                'defaultType': 'future',
            },
        })
        self.ws_connection = None
        self.agg_trade_data = []

    # --- WebSocket Metotları ---
    async def connect_aggtrade_ws(self, symbol):
        stream_name = f"{symbol.lower()}@aggTrade"
        url = f"{config.BINANCE_WEBSOCKET_URL}/{stream_name}"
        try:
            self.ws_connection = await websockets.connect(url)
            print(f"WebSocket bağlantısı başarılı: {symbol}")
            asyncio.create_task(self._listen_aggtrade())
            return True
        except Exception as e:
            print(f"WebSocket bağlantı hatası: {e}")
            return False

    async def _listen_aggtrade(self):
        while self.ws_connection and self.ws_connection.open:
            try:
                message = await self.ws_connection.recv()
                data = json.loads(message)
                trade = {
                    'q': Decimal(data['q']), # Miktar
                    'm': data['m']           # Alıcı mı satıcı mı? (True ise satıcı)
                }
                self.agg_trade_data.append(trade)
            except websockets.exceptions.ConnectionClosed:
                print("WebSocket bağlantısı kapandı.")
                break

    def get_and_clear_aggtrade_data(self):
        data_copy = self.agg_trade_data.copy()
        self.agg_trade_data.clear()
        return data_copy

    async def close_ws(self):
        if self.ws_connection:
            await self.ws_connection.close()
            print("WebSocket bağlantısı kapatıldı.")

    # --- REST API Metotları ---
    async def get_current_price(self, symbol):
        ticker = await self.exchange.fetch_ticker(symbol)
        return Decimal(ticker['last'])

    async def get_ema(self, symbol, timeframe, period):
        ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=period*2)
        closes = [Decimal(c[4]) for c in ohlcv]
        # Basit bir EMA hesaplaması (daha hassas bir kütüphane kullanılabilir)
        ema = sum(closes[-period:]) / period
        return ema

    async def create_market_order(self, symbol, side, amount):
        print(f"EMİR GÖNDERİLİYOR: {symbol} {side} {amount}")
        order = await self.exchange.create_market_order(symbol, side, amount)
        return order

    async def close_connection(self):
        await self.exchange.close()
