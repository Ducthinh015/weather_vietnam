"""Utility helpers to standardize API responses and errors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from flask import jsonify


DEFAULT_SUCCESS_MESSAGE = "ok"


@dataclass
class ApiError(Exception):
    """Typed application error converted to JSON in a single place."""

    message: str
    status_code: int = 400
    error_code: str = "bad_request"
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": "error",
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details or {},
            },
        }


def success_response(
    data: Optional[Dict[str, Any]] = None,
    *,
    message: str = DEFAULT_SUCCESS_MESSAGE,
    meta: Optional[Dict[str, Any]] = None,
    status_code: int = 200,
):
    payload = {
        "status": "success",
        "message": message,
        "data": data or {},
    }
    if meta:
        payload["meta"] = meta
    return jsonify(payload), status_code


def error_response(
    message: str,
    *,
    status_code: int = 400,
    error_code: str = "bad_request",
    details: Optional[Dict[str, Any]] = None,
):
    payload = {
        "status": "error",
        "error": {
            "code": error_code,
            "message": message,
            "details": details or {},
        },
    }
    return jsonify(payload), status_code
