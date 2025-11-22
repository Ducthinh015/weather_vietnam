import os
import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional, Dict, Any
from backend.config import Config
from backend.db import get_db


@dataclass
class User:
    id: str
    name: str
    email: str
    password_hash: Optional[str] = None
    provider: str = "local"  # local | google | facebook
    avatar: Optional[str] = None
    session_token: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


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

    def find_by_session_token(self, token: str) -> Optional[User]:
        doc = self._coll.find_one({"session_token": token})
        if not doc:
            return None
        doc["id"] = str(doc.get("_id", doc.get("id")))
        doc.pop("_id", None)
        return User(**doc)

    def create(self, user: User) -> User:
        payload: Dict[str, Any] = asdict(user)
        payload.pop("id", None)
        now = datetime.utcnow()
        payload.setdefault("created_at", now)
        payload.setdefault("updated_at", now)
        res = self._coll.insert_one(payload)
        user.id = str(res.inserted_id)
        return user

    def to_public_dict(self, user: User) -> Dict[str, Any]:
        d = asdict(user)
        d.pop("password_hash", None)
        return d

    def upsert_google_user(self, *, email: str, name: Optional[str], avatar: Optional[str]) -> User:
        now = datetime.utcnow()
        doc = self._coll.find_one({"email": email})
        if doc:
            updates: Dict[str, Any] = {
                "updated_at": now,
                "provider": "google",
            }
            if name:
                updates["name"] = name
            if avatar:
                updates["avatar"] = avatar
            self._coll.update_one({"_id": doc["_id"]}, {"$set": updates})
            doc.update(updates)
            doc["id"] = str(doc.get("_id", doc.get("id")))
            doc.pop("_id", None)
            return User(**doc)

        user = User(
            id="",
            name=name or (email.split("@")[0] if email else "User"),
            email=email,
            provider="google",
            avatar=avatar,
        )
        return self.create(user)

    def update_session_token(self, *, email: str, session_token: str):
        now = datetime.utcnow()
        self._coll.update_one(
            {"email": email},
            {"$set": {"session_token": session_token, "updated_at": now}},
        )
