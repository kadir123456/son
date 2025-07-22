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
    BASE_URL = "https.fapi.binance.com" if os.getenv("ENVIRONMENT", "TEST") == "LIVE" else "https://testnet.binancefuture.com"
    WEBSOCKET_URL = "wss://fstream.binance.com" if os.getenv("ENVIRONMENT", "TEST") == "LIVE" else "wss://stream.binancefuture.com"

    # --- İşlem Parametreleri ---
    LEVERAGE: int = 10
    ORDER_SIZE_USDT: float = 125.0
    TIMEFRAME: str = "5m"
    
    # --- Kâr/Zarar Ayarları (DÜZENLENDİ) ---
    # Sabit kâr hedefi. Trailing Stop'ın çalışması için uzağa ayarlandı.
    TAKE_PROFIT_PERCENT: float = 0.005  # %10 (Güvenlik ağı olarak)
    
    # Başlangıçtaki maksimum riskimiz.
    STOP_LOSS_PERCENT: float = 0.003   # %0.3 (Başlangıç Stop Noktası)
    
    # --- Kâr Koruma Ayarları (SİSTEMİN KALBİ) ---
    # Kâr %0.2'ye ulaştığında "kârı koru" modu devreye girer.
    TRAILING_ACTIVATION_PERCENT: float = 0.002
    
    # Fiyat ulaştığı zirveden %0.3 geri çekilirse pozisyonu kârla kapat.
    TRAILING_DISTANCE_PERCENT: float = 0.003

settings = Settings()
