import os
import time
import functools
from typing import Dict, Any, Optional, Callable
import jwt
from flask import request, jsonify
from backend.config import Config


def _secret() -> str:
    return os.getenv("JWT_SECRET", "change_this")


def generate_token(payload: Dict[str, Any], expires_in_seconds: int = 7 * 24 * 3600) -> str:
    now = int(time.time())
    body = {
        **payload,
        "iat": now,
        "exp": now + expires_in_seconds,
    }
    return jwt.encode(body, _secret(), algorithm="HS256")


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, _secret(), algorithms=["HS256"])
    except Exception:
        return None


def decode_token(token: str) -> Dict[str, Any]:
    """Decode JWT token and raise if invalid."""
    return jwt.decode(token, _secret(), algorithms=["HS256"])


def require_auth(fn: Callable):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "missing_or_invalid_token"}), 401
        token = auth.split(" ", 1)[1].strip()
        payload = verify_token(token)
        if not payload:
            return jsonify({"error": "invalid_token"}), 401
        request.user = payload
        return fn(*args, **kwargs)
    return wrapper
