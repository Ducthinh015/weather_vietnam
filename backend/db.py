from pymongo import MongoClient
from .config import Config

_client = None
_db = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        cfg = Config()
        uri = cfg.MONGO_URI
        # Local default: no TLS; add small serverSelection timeout
        _client = MongoClient(uri, serverSelectionTimeoutMS=10000, appname="AgriCastAI")
    return _client


def get_db():
    global _db
    if _db is None:
        cfg = Config()
        _db = get_client()[cfg.DB_NAME]
    return _db
