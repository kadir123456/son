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
    LEVERAGE: int = 5
    ORDER_SIZE_USDT: float = 100.0
    TIMEFRAME: str = "5m"
    
    # --- Kâr/Zarar Ayarları (Net 0.50 USDT Hedefi İçin) ---
    TAKE_PROFIT_PERCENT: float = 0.002  # %0.2 Kâr Al
    STOP_LOSS_PERCENT: float = 0.002   # %0.2 Zarar Durdur

settings = Settings()
