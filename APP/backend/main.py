"""
main.py
API Flask do painel IFP: login (JWT em cookie httpOnly) + verificação de sessão.
Versão inicial sem integração de dados (Sheets/PDF/Excel).

Colocar em: APP/backend/main.py

Variáveis de ambiente necessárias no Render:
  - SECRET_KEY      -> string aleatória qualquer
  - APP_USERNAME     -> usuário de login (ex: lucas)
  - APP_PASSWORD     -> senha de login
  - FRONTEND_ORIGIN  -> URL do frontend no Render (ex: https://ifp-frontend.onrender.com)
"""

import os
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS

app = Flask(__name__)

SECRET_KEY = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao")
APP_USERNAME = os.environ.get("APP_USERNAME", "admin")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "admin")
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "*")
COOKIE_NAME = "ifp_token"

CORS(app, supports_credentials=True, origins=[FRONTEND_ORIGIN] if FRONTEND_ORIGIN != "*" else "*")


def gerar_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=12),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def login_obrigatorio(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.cookies.get(COOKIE_NAME)
        if not token:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1]
        if not token:
            return jsonify({"erro": "Não autenticado"}), 401
        try:
            jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"erro": "Sessão expirada"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"erro": "Token inválido"}), 401
        return f(*args, **kwargs)
    return wrapper


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    usuario = body.get("usuario", "")
    senha = body.get("senha", "")

    if usuario != APP_USERNAME or senha != APP_PASSWORD:
        return jsonify({"erro": "Usuário ou senha inválidos"}), 401

    token = gerar_token(usuario)
    resp = make_response(jsonify({"ok": True}))
    resp.set_cookie(
        COOKIE_NAME, token,
        httponly=True, secure=True, samesite="None",
        max_age=12 * 60 * 60,
    )
    return resp


@app.route("/api/logout", methods=["POST"])
def logout():
    resp = make_response(jsonify({"ok": True}))
    resp.delete_cookie(COOKIE_NAME)
    return resp


@app.route("/api/session", methods=["GET"])
@login_obrigatorio
def session_ok():
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
