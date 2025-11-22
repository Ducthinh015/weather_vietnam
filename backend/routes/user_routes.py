import os
from flask import Blueprint, request, jsonify
from backend.utils.jwt_utils import verify_token

user_bp = Blueprint("user", __name__)

@user_bp.route("/me", methods=["GET"])
def me():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "unauthorized"}), 401
    token = auth.split(" ", 1)[1].strip()
    payload = verify_token(token)
    if not payload:
        return jsonify({"error": "unauthorized"}), 401
    email = payload.get("email")
    name = payload.get("name")
    if not email and not name:
        return jsonify({"error": "unauthorized"}), 401
    return jsonify({"email": email, "name": name})
