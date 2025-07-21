import pandas as pd

class TradingStrategy:
    """
    EMA kesişimini, daha yavaş bir EMA ile trend filtresi olarak birleştiren strateji.
    """
    def __init__(self, short_ema_period: int, long_ema_period: int, trend_filter_period: int):
        self.short_ema_period = short_ema_period
        self.long_ema_period = long_ema_period
        self.trend_filter_period = trend_filter_period
        self.last_signal = None 
        print(f"Trend Filtreli Strateji başlatıldı: Kesişim EMA({self.short_ema_period}, {self.long_ema_period}) + Filtre EMA({self.trend_filter_period})")

    def analyze_klines(self, klines: list) -> str:
        """Verilen mum listesini analiz eder ve bir sinyal döndürür."""
        if len(klines) < self.trend_filter_period:
            return "HOLD"

        df = pd.DataFrame(klines, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time',
            'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
            'taker_buy_quote_asset_volume', 'ignore'
        ])
        df['close'] = pd.to_numeric(df['close'])

        # --- Göstergeleri Hesapla ---
        df['short_ema'] = df['close'].ewm(span=self.short_ema_period, adjust=False).mean()
        df['long_ema'] = df['close'].ewm(span=self.long_ema_period, adjust=False).mean()
        df['trend_ema'] = df['close'].ewm(span=self.trend_filter_period, adjust=False).mean()

        # --- Sinyal Mantığı ---
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        signal = "HOLD"

        # YUKARI KESİŞİM (LONG SİNYALİ) KONTROLÜ
        is_crossover_up = prev_row['short_ema'] < prev_row['long_ema'] and last_row['short_ema'] > last_row['long_ema']
        is_uptrend = last_row['close'] > last_row['trend_ema']
        
        if is_crossover_up and is_uptrend:
            signal = "LONG"

        # AŞAĞI KESİŞİM (SHORT SİNYALİ) KONTROLÜ
        is_crossover_down = prev_row['short_ema'] > prev_row['long_ema'] and last_row['short_ema'] < last_row['long_ema']
        is_downtrend = last_row['close'] < last_row['trend_ema']

        if is_crossover_down and is_downtrend:
            signal = "SHORT"
            
        if signal != "HOLD" and signal == self.last_signal:
            return "HOLD"
        
        self.last_signal = signal
        return signal

# Strateji nesnesini SİZİN istediğiniz 9, 21, 50 periyotlarıyla oluşturalım.
trading_strategy = TradingStrategy(short_ema_period=9, long_ema_period=21, trend_filter_period=50)
