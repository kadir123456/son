import pandas as pd

class TradingStrategy:
    """
    Gelen mum verilerini analiz ederek alım-satım sinyalleri üretir.
    Mevcut strateji: Üssel Hareketli Ortalama (EMA) Kesişimi.
    """
    def __init__(self, short_ema_period: int = 9, long_ema_period: int = 21):
        self.short_ema_period = short_ema_period
        self.long_ema_period = long_ema_period
        # Sinyalin tekrar tekrar tetiklenmesini önlemek için son sinyali sakla
        self.last_signal = None 
        print(f"Ticaret Stratejisi başlatıldı: EMA({self.short_ema_period}, {self.long_ema_period})")

    def analyze_klines(self, klines: list) -> str:
        """
        Verilen mum listesini analiz eder ve bir sinyal döndürür.
        Sinyaller: 'LONG', 'SHORT', 'HOLD'

        :param klines: Binance API'den gelen mum verisi listesi.
        :return: Sinyal string'i.
        """
        if len(klines) < self.long_ema_period:
            # Yeterli veri yoksa analiz yapma
            return "HOLD"

        # 1. Gelen listeyi bir Pandas DataFrame'e dönüştür
        df = pd.DataFrame(klines, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time',
            'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
            'taker_buy_quote_asset_volume', 'ignore'
        ])

        # 2. Gerekli sütunları sayısal tipe çevir
        df['close'] = pd.to_numeric(df['close'])

        # 3. Kısa ve Uzun Vadeli EMA'ları Hesapla
        df['short_ema'] = df['close'].ewm(span=self.short_ema_period, adjust=False).mean()
        df['long_ema'] = df['close'].ewm(span=self.long_ema_period, adjust=False).mean()

        # 4. Sinyal Mantığını Uygula
        # Son iki mumu kontrol ederek kesişimin "tam şimdi" olup olmadığını anlarız.
        # [-1] -> en son kapanan mum
        # [-2] -> bir önceki mum
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]

        signal = "HOLD" # Varsayılan durum

        # YUKARI KESİŞİM (LONG SİNYALİ):
        # Önceki mumda kısa EMA uzun EMA'nın altındayken,
        # şimdiki mumda kısa EMA uzun EMA'nın üzerine çıktıysa.
        if prev_row['short_ema'] < prev_row['long_ema'] and last_row['short_ema'] > last_row['long_ema']:
            signal = "LONG"

        # AŞAĞI KESİŞİM (SHORT SİNYALİ):
        # Önceki mumda kısa EMA uzun EMA'nın üzerindeyken,
        # şimdiki mumda kısa EMA uzun EMA'nın altına indiyse.
        elif prev_row['short_ema'] > prev_row['long_ema'] and last_row['short_ema'] < last_row['long_ema']:
            signal = "SHORT"
            
        # Sinyal tekrarını önle
        if signal != "HOLD" and signal == self.last_signal:
            return "HOLD"
        
        self.last_signal = signal
        return signal

# Strateji nesnesini daha hassas periyotlarla global olarak oluşturalım.
# DEĞİŞİKLİK BURADA YAPILDI:
trading_strategy = TradingStrategy(short_ema_period=5, long_ema_period=12)
