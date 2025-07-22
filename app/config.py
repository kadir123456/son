import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # --- Temel Ayarlar ---
    API_KEY: str = os.getenv("BINANCE_API_KEY")
    API_SECRET: str = os.getenv("BINANCE_API_SECRET")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "LIVE")
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "admin")
    BOT_PASSWORD: str = os.getenv("BOT_PASSWORD", "changeme123")
    BASE_URL = "https://fapi.binance.com" if os.getenv("ENVIRONMENT", "TEST") == "LIVE" else "https://testnet.binancefuture.com"
    WEBSOCKET_URL = "wss://fstream.binance.com" if os.getenv("ENVIRONMENT", "TEST") == "LIVE" else "wss://stream.binancefuture.com"

    # --- İşlem Parametreleri ---
    LEVERAGE: int = 10
    ORDER_SIZE_USDT: float = 100.0
    TIMEFRAME: str = "5m"
    
    # --- Kâr/Zarar Ayarları (SABİT 5 USDT HEDEFİ) ---
    TAKE_PROFIT_PERCENT: float = 0.006  # %0.6 Kâr Al (~5 USDT net kâr için)
    STOP_LOSS_PERCENT: float = 0.004   # %0.4 Zarar Durdur (~5 USDT net zarar için)

settings = Settings()
