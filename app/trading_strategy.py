import pandas as pd

class TradingStrategy:
    """
    Her mum kapanışında, o mumun rengine göre anında işlem açan
    yüksek frekanslı bir "momentum scalping" stratejisi.
    """
    def __init__(self):
        print(f"Aktif Strateji: 'Anlık Momentum Takibi'")

    def analyze_klines(self, klines: list) -> str:
        """
        Verilen mum listesini analiz eder.
        Neredeyse her zaman LONG veya SHORT döndürür.
        """
        if len(klines) < 1:
            return "HOLD"

        # Analiz edeceğimiz mum, en son kapanan mumdur.
        latest_candle = klines[-1]

        # Mum verilerini Binance API formatına göre alıyoruz:
        # [zaman, açılış, yüksek, düşük, kapanış, ...]
        open_price = float(latest_candle[1])
        close_price = float(latest_candle[4])

        signal = "HOLD"

        # En son kapanan mumun rengini kontrol et
        if close_price > open_price:
            # Mum YEŞİL ise (yükseliş momentumu), LONG sinyali üret
            signal = "LONG"
        elif close_price < open_price:
            # Mum KIRMIZI ise (düşüş momentumu), SHORT sinyali üret
            signal = "SHORT"
        
        return signal

# Strateji nesnesini oluşturalım
trading_strategy = TradingStrategy()
