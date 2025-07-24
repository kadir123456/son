import pandas as pd

class TradingStrategy:
    """
    Bir önceki mumun alıcı ve satıcı hacmine göre sinyal üreten strateji.
    """
    def __init__(self):
        print(f"Aktif Strateji: 'Hacim Analizi'")

    def analyze_klines(self, klines: list) -> str:
        """
        Verilen mum listesini analiz eder ve hacim baskınlığına göre sinyal üretir.
        """
        if len(klines) < 1:
            return "HOLD"

        # Analiz edeceğimiz mum, en son kapanan mumdur.
        latest_candle = klines[-1]

        # Mum verilerini Binance API formatına göre alıyoruz:
        # [..., 'volume', ..., 'taker_buy_base_asset_volume', ...]
        #   5. index -> Toplam Hacim
        #   9. index -> Alıcıların Başlattığı İşlem Hacmi (Taker Buy Volume)
        
        total_volume = float(latest_candle[5])
        taker_buy_volume = float(latest_candle[9])

        # Eğer toplam hacim sıfırsa bir şey yapma
        if total_volume == 0:
            return "HOLD"
            
        taker_sell_volume = total_volume - taker_buy_volume
        
        signal = "HOLD"

        # Hacim baskınlığını kontrol et
        if taker_buy_volume > taker_sell_volume:
            # Alıcılar baskınsa LONG sinyali üret
            signal = "LONG"
        elif taker_sell_volume > taker_buy_volume:
            # Satıcılar baskınsa SHORT sinyali üret
            signal = "SHORT"
        
        return signal

trading_strategy = TradingStrategy()
