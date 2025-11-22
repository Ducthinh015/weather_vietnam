import os
import uuid
import bcrypt
from typing import Optional, Dict, Any
from backend.models.user_model import User, UserRepository
from backend.utils.jwt_utils import generate_token


class AuthService:
    def __init__(self, repo: Optional[UserRepository] = None):
        self.repo = repo or UserRepository()

    def register(self, name: str, email: str, password: str) -> Dict[str, Any]:
        email = (email or "").strip().lower()
        if not name or not email or not password:
            raise ValueError("missing_fields")
        if self.repo.find_by_email(email):
            raise ValueError("email_exists")
        salt = bcrypt.gensalt()
        pw_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
        user = User(id=str(uuid.uuid4()), name=name.strip(), email=email, password_hash=pw_hash, provider="local")
        user = self.repo.create(user)
        token = generate_token({"sub": user.id, "email": user.email, "name": user.name})
        return {"user": self.repo.to_public_dict(user), "token": token}

    def login(self, email: str, password: str) -> Dict[str, Any]:
        email = (email or "").strip().lower()
        user = self.repo.find_by_email(email)
        if not user or not user.password_hash:
            raise ValueError("invalid_credentials")
        ok = bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8"))
        if not ok:
            raise ValueError("invalid_credentials")
        token = generate_token({"sub": user.id, "email": user.email, "name": user.name})
        return {"user": self.repo.to_public_dict(user), "token": token}

    def oauth_login(self, name: str, email: str, provider: str) -> Dict[str, Any]:
        email = (email or "").strip().lower()
        user = self.repo.find_by_email(email)
        if not user:
            user = User(id=str(uuid.uuid4()), name=name or email.split('@')[0], email=email, provider=provider)
            user = self.repo.create(user)
        token = generate_token({"sub": user.id, "email": user.email, "name": user.name})
        return {"user": self.repo.to_public_dict(user), "token": token}
