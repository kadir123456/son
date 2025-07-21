import firebase_admin
from firebase_admin import credentials, db, auth
import os
import json
from datetime import datetime

class FirebaseManager:
    def __init__(self):
        self.db_ref = None
        try:
            if not firebase_admin._apps:
                cred_json_str = os.getenv("FIREBASE_CREDENTIALS_JSON")
                database_url = os.getenv("FIREBASE_DATABASE_URL")
                if cred_json_str and database_url:
                    cred_dict = json.loads(cred_json_str)
                    cred = credentials.Certificate(cred_dict)
                    firebase_admin.initialize_app(cred, {'databaseURL': database_url})
                    print("Firebase (Admin SDK & Realtime DB) başarıyla başlatıldı.")
                else:
                    print("UYARI: Firebase kimlik bilgileri bulunamadı.")
            if firebase_admin._apps:
                self.db_ref = db.reference('trades')
        except Exception as e:
            print(f"Firebase başlatılırken hata oluştu: {e}")

    def log_trade(self, trade_data: dict):
        if not self.db_ref:
            print("Veritabanı bağlantısı yok, işlem kaydedilemedi.")
            return
        try:
            if 'timestamp' in trade_data and isinstance(trade_data['timestamp'], datetime):
                trade_data['timestamp'] = trade_data['timestamp'].isoformat()
            self.db_ref.push(trade_data)
            print(f"--> İşlem başarıyla Firebase Realtime DB'e kaydedildi.")
        except Exception as e:
            print(f"Firebase'e işlem kaydedilirken hata oluştu: {e}")

    def verify_token(self, token: str):
        try:
            if not firebase_admin._apps: return None
            return auth.verify_id_token(token)
        except Exception as e:
            print(f"Token doğrulama hatası: {e}")
            return None

firebase_manager = FirebaseManager()
