from pymongo import MongoClient
import logging
from backend.config import Config

_client = None
_db = None


def get_client() -> MongoClient:
    global _client

    if _client is None:
        cfg = Config()

        uri = cfg.MONGO_URI   # 🔥 đảm bảo luôn có, vì config.py đã kiểm tra rồi

        try:
            _client = MongoClient(
                uri,
                serverSelectionTimeoutMS=10000,
                appname="AgriCastAI"
            )
            _client.admin.command("ping")  # validate connection
        except Exception as exc:
            logging.error("❌ Mongo connection failed: %s", exc)
            raise

    return _client


def get_db():
    global _db

    if _db is None:
        cfg = Config()
        try:
            _db = get_client()[cfg.DB_NAME]
        except Exception:
            raise

    return _db
