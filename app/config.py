import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # --- Temel Ayarlar (Aynı kalacak) ---
    API_KEY: str = os.getenv("BINANCE_API_KEY")
    API_SECRET: str = os.getenv("BINANCE_API_SECRET")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "LIVE")
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "admin")
    BOT_PASSWORD: str = os.getenv("BOT_PASSWORD", "changeme123")
    BASE_URL = "https://fapi.binance.com" if os.getenv("ENVIRONMENT", "TEST") == "LIVE" else "https://testnet.binancefuture.com"
    WEBSOCKET_URL = "wss://fstream.binance.com" if os.getenv("ENVIRONMENT", "TEST") == "LIVE" else "wss://stream.binancefuture.com"

    # --- İşlem Parametreleri (Aynı kalacak) ---
    LEVERAGE: int = 5
    ORDER_SIZE_USDT: float = 125.0
    TIMEFRAME: str = "5m"
    
    # --- YENİ DİNAMİK KÂR/ZARAR AYARLARI ---
    
    # 1. Başlangıçtaki Maksimum Riskimiz:
    # Fiyat en başta bu kadar ters giderse, küçük bir zararla pozisyon kapanır.
    STOP_LOSS_PERCENT: float = 0.003   # %0.4
    
    # 2. "Güvenlik Ağı" Kâr Hedefi:
    # Bu, Trailing Stop çalışmazsa veya çok büyük bir ani yükseliş olursa devreye girecek uzak bir hedeftir.
    TAKE_PROFIT_PERCENT: float = 0.01  # %2.6 (Sizin gözlemlediğiniz maksimum Long potansiyeli)
    
    # 3. Kâr Koruma (Trailing Stop) Ayarları - SİSTEMİN KALBİ
    
    # Kâr ne zaman korunmaya başlasın?
    # Kâr %0.3'e ulaştığında "kârı koru" modu devreye girer. Bu, işlemin artık zararla kapanmamasını sağlar.
    TRAILING_ACTIVATION_PERCENT: float = 0.003
    
    # Trend ne kadar geri çekilirse pozisyon kapansın?
    # Sizin gözleminize göre Short'lar %0.8 düşüyor. Biz bunun yarısı kadar bir geri çekilmeye izin verelim.
    # Bu, trendin nefes almasına izin verirken, kârın büyük kısmını masada bırakmayı önler.
    TRAILING_DISTANCE_PERCENT: float = 0.004 # %0.4

settings = Settings()
