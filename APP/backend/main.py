"""
main.py
API Flask: login (JWT em cookie httpOnly) + rotas para listar polos,
atualizar o dashboard de um polo e baixar o PDF atualizado desse polo.

Colocar em: APP/backend/main.py  (SUBSTITUI o main.py atual)

Variáveis de ambiente necessárias no Render:
  - SECRET_KEY               -> string aleatória qualquer
  - APP_USERNAME              -> usuário de login (ex: lucas)
  - APP_PASSWORD              -> senha de login
  - GOOGLE_CREDENTIALS_JSON   -> conteúdo INTEIRO do JSON da service account (uma linha)
  - FRONTEND_ORIGIN           -> URL do frontend no Render (ex: https://seu-frontend.onrender.com)
"""

import os
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS

import dashboard_movimenta
import dashboard_fortaleza
import dashboard_eduthree
from pdf_generator import gerar_pdf_dashboard, gerar_pdf_fortaleza, gerar_pdf_eduthree
from excel_generator import gerar_excel_dashboard

app = Flask(__name__)

SECRET_KEY = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao")
APP_USERNAME = os.environ.get("APP_USERNAME", "admin")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "admin")
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "*")
COOKIE_NAME = "movimenta_token"

CORS(app, supports_credentials=True, origins=[FRONTEND_ORIGIN] if FRONTEND_ORIGIN != "*" else "*")

POLOS = {
    "movimenta": {
        "nome": "Movimenta Rio",
        "atualizar": dashboard_movimenta.atualizar_dashboard,
        "ler": dashboard_movimenta.ler_dashboard_atual,
        "visual": dashboard_movimenta.obter_dashboard_visual,
        "gerar_pdf": gerar_pdf_dashboard,
        "excel_titulo": "RELAÇÃO DE LEADS — MOVIMENTA RIO — DASHBOARD",
        "excel_cor_header": "0B0B0B",
        "excel_cor_texto": "00E5FF",
    },
    "fortaleza": {
        "nome": "Fortaleza",
        "atualizar": dashboard_fortaleza.atualizar_dashboard,
        "ler": dashboard_fortaleza.ler_dashboard_atual,
        "visual": dashboard_fortaleza.obter_dashboard_visual,
        "gerar_pdf": gerar_pdf_fortaleza,
        "excel_titulo": "RELAÇÃO DE LEADS — FORTALEZA — DASHBOARD",
        "excel_cor_header": "000000",
        "excel_cor_texto": "FFFFFF",
    },
    "eduthree": {
        "nome": "Eduthree",
        "atualizar": dashboard_eduthree.atualizar_dashboard,
        "ler": dashboard_eduthree.ler_dashboard_atual,
        "visual": dashboard_eduthree.obter_dashboard_visual,
        "gerar_pdf": gerar_pdf_eduthree,
        "excel_titulo": "RELAÇÃO DE LEADS — EDUTHREE — DASHBOARD",
        "excel_cor_header": "BD9500",
        "excel_cor_texto": "FFFFFF",
    },
}


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


def _get_polo_ou_erro():
    polo_id = request.args.get("polo", "").strip().lower()
    if polo_id not in POLOS:
        return None, (jsonify({"erro": f"Polo inválido. Use um de: {', '.join(POLOS.keys())}"}), 400)
    return polo_id, None


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


@app.route("/api/polos", methods=["GET"])
@login_obrigatorio
def listar_polos():
    return jsonify({
        "polos": [{"id": pid, "nome": info["nome"]} for pid, info in POLOS.items()]
    })


@app.route("/api/dashboard-visual", methods=["GET"])
@login_obrigatorio
def dashboard_visual():
    polo_id, erro = _get_polo_ou_erro()
    if erro:
        return erro
    try:
        dados = POLOS[polo_id]["visual"]()
        return jsonify({"ok": True, "dados": dados})
    except Exception as e:
        return jsonify({"ok": False, "erro": str(e)}), 500


@app.route("/api/atualizar", methods=["POST"])
@login_obrigatorio
def atualizar():
    polo_id, erro = _get_polo_ou_erro()
    if erro:
        return erro
    try:
        resumo = POLOS[polo_id]["atualizar"]()
        return jsonify(resumo)
    except Exception as e:
        return jsonify({"ok": False, "erro": str(e)}), 500


@app.route("/api/baixar-excel", methods=["GET"])
@login_obrigatorio
def baixar_excel():
    polo_id, erro = _get_polo_ou_erro()
    if erro:
        return erro
    try:
        polo = POLOS[polo_id]
        dados = polo["ler"]()
        excel_bytes = gerar_excel_dashboard(
            dados["headers"], dados["rows"],
            titulo=polo["excel_titulo"],
            cor_header_hex=polo["excel_cor_header"],
            cor_texto_header_hex=polo["excel_cor_texto"],
        )
        resp = make_response(excel_bytes)
        resp.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        nome_arquivo = f"RELACAO_DE_LEADS_{polo_id.upper()}_DASHBOARD_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        resp.headers["Content-Disposition"] = f"attachment; filename={nome_arquivo}"
        return resp
    except Exception as e:
        return jsonify({"ok": False, "erro": str(e)}), 500


@app.route("/api/baixar-pdf", methods=["GET"])
@login_obrigatorio
def baixar_pdf():
    polo_id, erro = _get_polo_ou_erro()
    if erro:
        return erro
    responsavel_filtro = request.args.get("responsavel", "").strip()
    try:
        polo = POLOS[polo_id]
        if responsavel_filtro and polo_id == "movimenta":
            dados = dashboard_movimenta.ler_dashboard_filtrado_por_responsavel(responsavel_filtro)
        else:
            dados = polo["ler"]()
        pdf_bytes = polo["gerar_pdf"](dados["headers"], dados["rows"])
        resp = make_response(pdf_bytes)
        resp.headers["Content-Type"] = "application/pdf"
        sufixo = f"_{responsavel_filtro.upper()}" if (responsavel_filtro and polo_id == "movimenta") else ""
        nome_arquivo = f"RELACAO_DE_LEADS_{polo_id.upper()}{sufixo}_DASHBOARD_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        resp.headers["Content-Disposition"] = f"attachment; filename={nome_arquivo}"
        return resp
    except Exception as e:
        return jsonify({"ok": False, "erro": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
