from . import config

class TradingStrategy:
    def __init__(self):
        # Stratejiye özel değişkenler burada tutulabilir
        pass

    def get_signal(self, buyer_volume, seller_volume, current_price, ema_filter_price):
        """
        Verilen hacim ve trend verilerine göre alım/satım sinyali üretir.
        
        Returns:
            'long', 'short', veya None
        """
        
        # Trend Filtresi kontrolü
        if config.USE_TREND_FILTER:
            is_uptrend = current_price > ema_filter_price
            is_downtrend = current_price < ema_filter_price
        else:
            # Filtre kullanılmıyorsa, her sinyal geçerlidir.
            is_uptrend = True
            is_downtrend = True

        # Karar verme mantığı
        if buyer_volume > seller_volume and is_uptrend:
            print(f"STRATEJİ SİNYALİ: LONG - Alıcı hacmi baskın ve trend uygun.")
            return 'long'
        elif seller_volume > buyer_volume and is_downtrend:
            print(f"STRATEJİ SİNYALİ: SHORT - Satıcı hacmi baskın ve trend uygun.")
            return 'short'
        else:
            # Diğer tüm durumlarda işlem açma
            print("STRATEJİ SİNYALİ YOK: Koşullar sağlanmadı.")
            return None
