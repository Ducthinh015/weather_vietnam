import os
import json
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from ..config import Config
from ..db import get_db


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
        self._coll = get_db().users

    def find_by_email(self, email: str) -> Optional[User]:
        doc = self._coll.find_one({"email": email})
        if not doc:
            return None
        doc["id"] = str(doc.get("_id", doc.get("id")))
        doc.pop("_id", None)
        return User(**doc)

    def create(self, user: User) -> User:
        payload: Dict[str, Any] = asdict(user)
        payload.pop("id", None)
        res = self._coll.insert_one(payload)
        user.id = str(res.inserted_id)
        return user

    def to_public_dict(self, user: User) -> Dict[str, Any]:
        d = asdict(user)
        d.pop("password_hash", None)
        return d
