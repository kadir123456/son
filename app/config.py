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
    ORDER_SIZE_USDT: float = 125.0
    TIMEFRAME: str = "5m"  # Ana işlem döngüsü
    
    # --- Kâr/Zarar Ayarları (Sizin hedeflerinize göre hesaplandı) ---
    # Net ~0.50 USDT kâr hedefler
    TAKE_PROFIT_PERCENT: float = 0.002  # %0.18 Kâr Al
    
    # Net ~2.00 USDT zararı hedefler
    STOP_LOSS_PERCENT: float = 0.009   # %0.22 Zarar Durdur

settings = Settings()
