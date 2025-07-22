import pandas as pd

class TradingStrategy:
    """
    Saf EMA kesişimine dayalı alım-satım stratejisi.
    Trend filtresi olmadan, her kesişimde sinyal üretir.
    """
    def __init__(self, short_ema_period: int = 9, long_ema_period: int = 21):
        self.short_ema_period = short_ema_period
        self.long_ema_period = long_ema_period
        self.last_signal = None 
        print(f"Saf Kesişim Stratejisi başlatıldı: EMA({self.short_ema_period}, {self.long_ema_period})")

    def analyze_klines(self, klines: list) -> str:
        if len(klines) < self.long_ema_period:
            return "HOLD"

        df = pd.DataFrame(klines, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time',
            'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
            'taker_buy_quote_asset_volume', 'ignore'
        ])
        df['close'] = pd.to_numeric(df['close'])

        df['short_ema'] = df['close'].ewm(span=self.short_ema_period, adjust=False).mean()
        df['long_ema'] = df['close'].ewm(span=self.long_ema_period, adjust=False).mean()

        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        signal = "HOLD"

        # YUKARI KESİŞİM (LONG SİNYALİ)
        if prev_row['short_ema'] < prev_row['long_ema'] and last_row['short_ema'] > last_row['long_ema']:
            signal = "LONG"
        
        # AŞAĞI KESİŞİM (SHORT SİNYALİ)
        elif prev_row['short_ema'] > prev_row['long_ema'] and last_row['short_ema'] < last_row['long_ema']:
            signal = "SHORT"
            
        if signal != "HOLD" and signal == self.last_signal:
            return "HOLD"
        
        self.last_signal = signal
        return signal

# Stratejiyi sizin Binance grafiğinizdeki (9, 21) ayarlarla başlatıyoruz
trading_strategy = TradingStrategy(short_ema_period=9, long_ema_period=21)
