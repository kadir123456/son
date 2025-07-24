from decimal import Decimal

# Strateji Parametreleri
POSITION_SIZE_USDT = Decimal('30')
LEVERAGE = 5
TAKE_PROFIT_PERCENT = Decimal('0.0053') # ~0.80 USDT kar hedefi icin
STOP_LOSS_PERCENT = Decimal('0.0053')  # 1:1 Risk/Odul orani
ANALYSIS_DURATION_SECONDS = 60 # Mumun ilk kaç saniyesinin analiz edileceği
TIMEFRAME_SECONDS = 300 # 5 dakika = 300 saniye

# Trend Filtresi
USE_TREND_FILTER = True
TREND_FILTER_EMA_PERIOD = 50
TREND_FILTER_TIMEFRAME = '5m'

# Binance Ayarları
BINANCE_WEBSOCKET_URL = "wss://stream.binance.com:9443/ws"
