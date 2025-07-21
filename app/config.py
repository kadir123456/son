import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    API_KEY: str = os.getenv("BINANCE_API_KEY")
    API_SECRET: str = os.getenv("BINANCE_API_SECRET")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "LIVE")
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "admin")
    BOT_PASSWORD: str = os.getenv("BOT_PASSWORD", "changeme123")
    BASE_URL = "https://fapi.binance.com" if os.getenv("ENVIRONMENT", "TEST") == "LIVE" else "https://testnet.binancefuture.com"
    WEBSOCKET_URL = "wss://fstream.binance.com" if os.getenv("ENVIRONMENT", "TEST") == "LIVE" else "wss://stream.binancefuture.com"
    LEVERAGE: int = 5
    ORDER_SIZE_USDT: float = 100.0
    TIMEFRAME: str = "5m"
    TAKE_PROFIT_PERCENT: float = 0.003
    STOP_LOSS_PERCENT: float = 0.005
    TRAILING_ACTIVATION_PERCENT: float = 0.0015
    TRAILING_DISTANCE_PERCENT: float = 0.001

settings = Settings()
