import pandas as pd

class TradingStrategy:
    """
    Verilen mum verilerine göre mevcut trendin yönünü belirler.
    Bu strateji, ana bot döngüsü tarafından çağrılır ve sadece yön tespiti yapar.
    Kural: EMA(9) > EMA(21) ise LONG, değilse SHORT.
    """
    def __init__(self, short_ema_period: int = 9, long_ema_period: int = 21):
        self.short_ema_period = short_ema_period
        self.long_ema_period = long_ema_period
        print(f"3/5 Hibrit Strateji Yön Belirleyici Başlatıldı: EMA({self.short_ema_period}, {self.long_ema_period})")

    def get_trend_direction(self, klines: list) -> str:
        """
        Verilen mum listesine göre o anki trendin yönünü döndürür.
        Bu fonksiyon bir "kesişim anı" aramaz, sadece son durumu bildirir.
        """
        if len(klines) < self.long_ema_period:
            # Yeterli veri yoksa bir yön belirtme
            return "HOLD"

        df = pd.DataFrame(klines, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time',
            'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
            'taker_buy_quote_asset_volume', 'ignore'
        ])
        df['close'] = pd.to_numeric(df['close'])

        # Gerekli EMA'ları hesapla
        df['short_ema'] = df['close'].ewm(span=self.short_ema_period, adjust=False).mean()
        df['long_ema'] = df['close'].ewm(span=self.long_ema_period, adjust=False).mean()

        # Sadece en son mumdaki duruma bak
        last_row = df.iloc[-1]

        if last_row['short_ema'] > last_row['long_ema']:
            # Hızlı EMA yavaşın üzerindeyse, yükseliş trendi var demektir.
            return "LONG"
        elif last_row['short_ema'] < last_row['long_ema']:
            # Hızlı EMA yavaşın altındaysa, düşüş trendi var demektir.
            return "SHORT"
        
        # EMA'lar eşitse veya bir sorun varsa bekle
        return "HOLD"

# Strateji nesnesini oluşturalım
trading_strategy = TradingStrategy(short_ema_period=9, long_ema_period=21)
