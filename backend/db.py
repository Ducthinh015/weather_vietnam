from pymongo import MongoClient
import logging
from backend.config import Config

_client = None
_db = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        cfg = Config()
        uri = cfg.MONGO_URI or "mongodb+srv://2331540234_db_user:0905175313@cluster0.qyfcbff.mongodb.net/agricast?retryWrites=true&w=majority"
        try:
            _client = MongoClient(uri, serverSelectionTimeoutMS=10000, appname="AgriCastAI")
            # Trigger a ping to validate connection early
            _client.admin.command("ping")
        except Exception as exc:
            logging.error("Mongo connection failed: %s", exc)
            raise
    return _client


def get_db():
    global _db
    if _db is None:
        cfg = Config()
        try:
            _db = get_client()[cfg.DB_NAME]
        except Exception:
            # Bubble up after logging in get_client; keep None to retry on next call
            raise
    return _db
