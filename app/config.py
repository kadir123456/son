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
    ORDER_SIZE_USDT: float = 50.0
    TIMEFRAME: str = "5m"
    
    # --- Kâr/Zarar Ayarları ---
    # Sabit kâr hedefi, trendin çok ileri gitmesi ihtimaline karşı bir güvenlik ağıdır.
    TAKE_PROFIT_PERCENT: float = 0.10  # %10 (Uzak Hedef)
    
    # Başlangıçtaki maksimum riskimiz.
    STOP_LOSS_PERCENT: float = 0.004   # %0.4
    
    # --- YENİ AGRESİF KÂR KORUMA AYARLARI ---
    
    # Kâr %0.3'e ulaştığında "kârı koru" modu devreye girer.
    TRAILING_ACTIVATION_PERCENT: float = 0.003
    
    # Fiyat ulaştığı zirveden %0.1 geri çekilirse pozisyonu kârla kapat.
    # Bu mesafeyi aktivasyondan daha küçük tutmak, net kârı garantiler.
    TRAILING_DISTANCE_PERCENT: float = 0.001

settings = Settings()
