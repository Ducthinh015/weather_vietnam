import os
import urllib.parse
import requests
from flask import Blueprint, request, jsonify, redirect
from backend.services.auth_service import AuthService
from backend.utils.jwt_utils import require_auth
from backend.models.user_model import UserRepository

auth_bp = Blueprint("auth", __name__)
svc = AuthService()
user_repo = UserRepository()


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(force=True, silent=True) or {}
    try:
        res = svc.register(
            name=data.get("name"),
            email=data.get("email"),
            password=data.get("password"),
        )
        return jsonify(res)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True, silent=True) or {}
    try:
        res = svc.login(
            email=data.get("email"),
            password=data.get("password"),
        )
        return jsonify(res)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@auth_bp.route("/me", methods=["GET"])
@require_auth
def me():
    payload = getattr(request, "user", {})
    email = payload.get("email")
    user_doc = user_repo.find_by_email(email) if email else None
    if user_doc:
        user_data = user_repo.to_public_dict(user_doc)
    else:
        user_data = {
            "id": payload.get("sub"),
            "email": email,
            "name": payload.get("name"),
        }
    return jsonify({"user": user_data})


# Google OAuth
@auth_bp.route("/google/login", methods=["GET"])
def google_login():
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    scope = "openid email profile"
    missing = [k for k, v in {
        "GOOGLE_CLIENT_ID": client_id,
        "GOOGLE_REDIRECT_URI": redirect_uri,
    }.items() if not v]
    if missing:
        return jsonify({"error": "missing_oauth_config", "missing": missing}), 500
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "access_type": "offline",
        "prompt": "consent",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return redirect(url)


@auth_bp.route("/google/callback", methods=["GET"])
def google_callback():
    code = request.args.get("code")
    if not code:
        return jsonify({"error": "missing_code"}), 400
    token_url = "https://oauth2.googleapis.com/token"
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    missing = [k for k, v in {
        "GOOGLE_CLIENT_ID": client_id,
        "GOOGLE_CLIENT_SECRET": client_secret,
        "GOOGLE_REDIRECT_URI": redirect_uri,
    }.items() if not v]
    if missing:
        return jsonify({"error": "missing_oauth_config", "missing": missing}), 500
    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    tok = requests.post(token_url, data=data, timeout=20).json()
    id_token = tok.get("id_token")
    access_token = tok.get("access_token")
    if not access_token:
        return jsonify({"error": "token_exchange_failed", "detail": tok}), 400
    userinfo = requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}, timeout=20
    ).json()
    email = userinfo.get("email")
    name = userinfo.get("name") or email
    res = svc.oauth_login(name=name, email=email, provider="google")
    fe_base = os.getenv("FRONTEND_BASE_URL")
    if not fe_base:
        return jsonify({"error": "missing_oauth_config", "missing": ["FRONTEND_BASE_URL"]}), 500
    success_url = f"{fe_base}/pages/oauth_success.html?token=" + urllib.parse.quote(res["token"]) 
    return redirect(success_url)


# Facebook OAuth
@auth_bp.route("/facebook/login", methods=["GET"])
def facebook_login():
    client_id = os.getenv("FACEBOOK_CLIENT_ID")
    redirect_uri = os.getenv("FACEBOOK_REDIRECT_URI")
    missing = [k for k, v in {
        "FACEBOOK_CLIENT_ID": client_id,
        "FACEBOOK_REDIRECT_URI": redirect_uri,
    }.items() if not v]
    if missing:
        return jsonify({"error": "missing_oauth_config", "missing": missing}), 500
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "email,public_profile",
    }
    url = "https://www.facebook.com/v18.0/dialog/oauth?" + urllib.parse.urlencode(params)
    return redirect(url)


@auth_bp.route("/facebook/callback", methods=["GET"])
def facebook_callback():
    code = request.args.get("code")
    if not code:
        return jsonify({"error": "missing_code"}), 400
    token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
    client_id = os.getenv("FACEBOOK_CLIENT_ID")
    client_secret = os.getenv("FACEBOOK_CLIENT_SECRET")
    redirect_uri = os.getenv("FACEBOOK_REDIRECT_URI")
    missing = [k for k, v in {
        "FACEBOOK_CLIENT_ID": client_id,
        "FACEBOOK_CLIENT_SECRET": client_secret,
        "FACEBOOK_REDIRECT_URI": redirect_uri,
    }.items() if not v]
    if missing:
        return jsonify({"error": "missing_oauth_config", "missing": missing}), 500
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "code": code,
    }
    tok = requests.get(token_url, params=params, timeout=20).json()
    access_token = tok.get("access_token")
    if not access_token:
        return jsonify({"error": "token_exchange_failed", "detail": tok}), 400
    userinfo = requests.get(
        "https://graph.facebook.com/me",
        params={"fields": "id,name,email", "access_token": access_token}, timeout=20
    ).json()
    email = userinfo.get("email") or f"fb_{userinfo.get('id')}@facebook.local"
    name = userinfo.get("name") or email
    res = svc.oauth_login(name=name, email=email, provider="facebook")
    fe_base = os.getenv("FRONTEND_BASE_URL")
    if not fe_base:
        return jsonify({"error": "missing_oauth_config", "missing": ["FRONTEND_BASE_URL"]}), 500
    success_url = f"{fe_base}/pages/oauth_success.html?token=" + urllib.parse.quote(res["token"]) 
    return redirect(success_url)
