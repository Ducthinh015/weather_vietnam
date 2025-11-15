import os
import json
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from ..config import Config

try:
    from pymongo import MongoClient
except Exception:
    MongoClient = None


@dataclass
class User:
    id: str
    name: str
    email: str
    password_hash: Optional[str] = None
    provider: str = "local"  # local | google | facebook


class UserRepository:
    def __init__(self, cfg: Optional[Config] = None):
        self.cfg = cfg or Config()
        self._json_path = os.path.join(self.cfg.DATA_PATH, "users.json")
        self._use_mongo = bool(self.cfg.MONGO_URI and MongoClient is not None)
        self._coll = None
        if self._use_mongo:
            client = MongoClient(self.cfg.MONGO_URI)
            self._coll = client.get_database().users
        else:
            os.makedirs(self.cfg.DATA_PATH, exist_ok=True)
            if not os.path.exists(self._json_path):
                with open(self._json_path, "w", encoding="utf-8") as f:
                    json.dump([], f)

    def _load_all_json(self):
        with open(self._json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_all_json(self, data):
        with open(self._json_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def find_by_email(self, email: str) -> Optional[User]:
        if self._use_mongo:
            doc = self._coll.find_one({"email": email})
            if not doc:
                return None
            doc["id"] = str(doc.get("_id", doc.get("id")))
            doc.pop("_id", None)
            return User(**doc)
        data = self._load_all_json()
        for d in data:
            if d.get("email") == email:
                return User(**d)
        return None

    def create(self, user: User) -> User:
        if self._use_mongo:
            payload: Dict[str, Any] = asdict(user)
            payload.pop("id", None)
            res = self._coll.insert_one(payload)
            user.id = str(res.inserted_id)
            return user
        data = self._load_all_json()
        data.append(asdict(user))
        self._save_all_json(data)
        return user

    def to_public_dict(self, user: User) -> Dict[str, Any]:
        d = asdict(user)
        d.pop("password_hash", None)
        return d
