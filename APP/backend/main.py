"""
main.py
API Flask da Plataforma de Comissionamento por Indicação de Alunos.

Fluxo:
  - Aluno escolhe a unidade, se cadastra ou faz login -> recebe um código de
    afiliado único e um link de indicação (/r/<codigo>).
  - Cada acesso ao link gera um "clique" registrado para aquele aluno.
  - Quando o indicado se matricula, é criada uma Indicação com status
    "pendente" (por enquanto via rota pública simples; futuramente uma API
    de pagamento vai confirmar automaticamente).
  - O ADMIN (unidade especial "ADMIN") confirma indicações manualmente por
    enquanto, e enxerga todas as unidades/alunos/indicações.
  - Regra de valor: R$50 por indicação confirmada. As 4 primeiras viram
    desconto na mensalidade (até R$200); da 5ª em diante vira saldo.

Variáveis de ambiente necessárias no Render:
  - SECRET_KEY        -> string aleatória qualquer
  - APP_USERNAME       -> usuário do ADMIN master
  - APP_PASSWORD       -> senha do ADMIN master
  - FRONTEND_ORIGIN    -> URL do frontend no Render
  - DATABASE_URL       -> string de conexão Postgres (fornecida pelo Render)
"""

import os
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import Flask, request, jsonify, make_response, redirect
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

from database import db, init_db
from models import Unidade, Aluno, Indicacao, Clique, gerar_codigo_afiliado

app = Flask(__name__)

SECRET_KEY = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao")
APP_USERNAME = os.environ.get("APP_USERNAME", "admin")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "admin")
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "*")
COOKIE_NAME = "comissionamento_token"

CORS(app, supports_credentials=True, origins=[FRONTEND_ORIGIN] if FRONTEND_ORIGIN != "*" else "*")

init_db(app)


# ---------------------------------------------------------------------------
# Autenticação (JWT com "role": aluno | admin)
# ---------------------------------------------------------------------------

def gerar_token(payload_extra: dict) -> str:
    payload = {
        **payload_extra,
        "exp": datetime.now(timezone.utc) + timedelta(hours=12),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def _extrair_token():
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
    return token


def login_obrigatorio(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = _extrair_token()
        if not token:
            return jsonify({"erro": "Não autenticado"}), 401
        try:
            dados = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"erro": "Sessão expirada"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"erro": "Token inválido"}), 401
        request.usuario = dados
        return f(*args, **kwargs)
    return wrapper


def admin_obrigatorio(f):
    @wraps(f)
    @login_obrigatorio
    def wrapper(*args, **kwargs):
        if request.usuario.get("role") != "admin":
            return jsonify({"erro": "Acesso restrito ao admin"}), 403
        return f(*args, **kwargs)
    return wrapper


def aluno_obrigatorio(f):
    @wraps(f)
    @login_obrigatorio
    def wrapper(*args, **kwargs):
        if request.usuario.get("role") != "aluno":
            return jsonify({"erro": "Acesso restrito a alunos"}), 403
        return f(*args, **kwargs)
    return wrapper


def _set_cookie_resposta(payload_extra: dict, corpo: dict):
    token = gerar_token(payload_extra)
    resp = make_response(jsonify(corpo))
    resp.set_cookie(
        COOKIE_NAME, token,
        httponly=True, secure=True, samesite="None",
        max_age=12 * 60 * 60,
    )
    return resp


# ---------------------------------------------------------------------------
# Rotas públicas
# ---------------------------------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/unidades", methods=["GET"])
def listar_unidades():
    unidades = Unidade.query.order_by(Unidade.nome.asc()).all()
    return jsonify({"unidades": [u.to_dict() for u in unidades]})


@app.route("/api/aluno/cadastro", methods=["POST"])
def cadastro_aluno():
    body = request.get_json(silent=True) or {}
    nome = (body.get("nome") or "").strip()
    cpf = (body.get("cpf") or "").strip()
    email = (body.get("email") or "").strip()
    senha = body.get("senha") or ""
    unidade_id = body.get("unidade_id")

    if not nome or not cpf or not senha or not unidade_id:
        return jsonify({"erro": "Preencha nome, CPF, senha e unidade."}), 400

    unidade = Unidade.query.get(unidade_id)
    if not unidade or unidade.nome == "ADMIN":
        return jsonify({"erro": "Unidade inválida."}), 400

    if Aluno.query.filter_by(cpf=cpf).first():
        return jsonify({"erro": "Já existe um cadastro com esse CPF."}), 409

    aluno = Aluno(
        nome=nome, cpf=cpf, email=email or None,
        senha_hash=generate_password_hash(senha),
        unidade_id=unidade.id,
        codigo_afiliado=gerar_codigo_afiliado(),
    )
    db.session.add(aluno)
    db.session.commit()

    return _set_cookie_resposta(
        {"sub": aluno.cpf, "role": "aluno", "aluno_id": aluno.id},
        {"ok": True, "aluno": aluno.to_dict()},
    )


@app.route("/api/aluno/login", methods=["POST"])
def login_aluno():
    body = request.get_json(silent=True) or {}
    cpf = (body.get("cpf") or "").strip()
    senha = body.get("senha") or ""
    unidade_id = body.get("unidade_id")

    aluno = Aluno.query.filter_by(cpf=cpf, unidade_id=unidade_id).first()
    if not aluno or not check_password_hash(aluno.senha_hash, senha):
        return jsonify({"erro": "CPF ou senha inválidos para essa unidade."}), 401

    return _set_cookie_resposta(
        {"sub": aluno.cpf, "role": "aluno", "aluno_id": aluno.id},
        {"ok": True, "aluno": aluno.to_dict()},
    )


@app.route("/api/admin/login", methods=["POST"])
def login_admin():
    body = request.get_json(silent=True) or {}
    usuario = body.get("usuario", "")
    senha = body.get("senha", "")

    if usuario != APP_USERNAME or senha != APP_PASSWORD:
        return jsonify({"erro": "Usuário ou senha inválidos"}), 401

    return _set_cookie_resposta(
        {"sub": usuario, "role": "admin"},
        {"ok": True},
    )


@app.route("/api/logout", methods=["POST"])
def logout():
    resp = make_response(jsonify({"ok": True}))
    resp.delete_cookie(COOKIE_NAME)
    return resp


@app.route("/api/session", methods=["GET"])
@login_obrigatorio
def session_ok():
    return jsonify({"ok": True, "role": request.usuario.get("role")})


@app.route("/r/<codigo>", methods=["GET"])
def redirecionar_link_afiliado(codigo):
    """Link público de indicação: registra o clique e redireciona para a
    página de matrícula do frontend, levando o código junto."""
    aluno = Aluno.query.filter_by(codigo_afiliado=codigo).first()
    if not aluno:
        return jsonify({"erro": "Link inválido."}), 404

    clique = Clique(aluno_id=aluno.id, ip=request.headers.get("X-Forwarded-For", request.remote_addr))
    db.session.add(clique)
    db.session.commit()

    destino = f"{FRONTEND_ORIGIN}/matricula.html?ref={codigo}" if FRONTEND_ORIGIN != "*" else f"/matricula.html?ref={codigo}"
    return redirect(destino)


@app.route("/api/indicacao/publica", methods=["POST"])
def registrar_indicacao_publica():
    """Chamada pela página pública de matrícula quando o indicado demonstra
    interesse. Fica como 'pendente' até confirmação (manual por enquanto,
    depois via API de pagamento)."""
    body = request.get_json(silent=True) or {}
    codigo = (body.get("codigo_afiliado") or "").strip()
    nome_indicado = (body.get("nome_indicado") or "").strip()
    cpf_indicado = (body.get("cpf_indicado") or "").strip()

    if not codigo or not nome_indicado:
        return jsonify({"erro": "Dados incompletos."}), 400

    aluno = Aluno.query.filter_by(codigo_afiliado=codigo).first()
    if not aluno:
        return jsonify({"erro": "Código de indicação inválido."}), 404

    indicacao = Indicacao(aluno_id=aluno.id, nome_indicado=nome_indicado, cpf_indicado=cpf_indicado or None)
    db.session.add(indicacao)
    db.session.commit()

    return jsonify({"ok": True, "indicacao": indicacao.to_dict()})


# ---------------------------------------------------------------------------
# Área do aluno
# ---------------------------------------------------------------------------

@app.route("/api/aluno/perfil", methods=["GET"])
@aluno_obrigatorio
def perfil_aluno():
    aluno = Aluno.query.get(request.usuario["aluno_id"])
    if not aluno:
        return jsonify({"erro": "Aluno não encontrado."}), 404

    origem = FRONTEND_ORIGIN if FRONTEND_ORIGIN != "*" else ""
    dados = aluno.to_dict()
    dados["link_afiliado"] = f"{request.host_url.rstrip('/')}/r/{aluno.codigo_afiliado}"
    dados["indicacoes"] = [i.to_dict() for i in sorted(aluno.indicacoes, key=lambda i: i.criado_em, reverse=True)]
    return jsonify({"ok": True, "aluno": dados})


# ---------------------------------------------------------------------------
# Área do admin (usuário master)
# ---------------------------------------------------------------------------

@app.route("/api/admin/unidades-resumo", methods=["GET"])
@admin_obrigatorio
def admin_unidades_resumo():
    unidades = Unidade.query.filter(Unidade.nome != "ADMIN").order_by(Unidade.nome.asc()).all()
    resumo = []
    for u in unidades:
        n_alunos = len(u.alunos)
        n_confirmadas = sum(
            1 for a in u.alunos for i in a.indicacoes if i.status == "confirmada"
        )
        n_pendentes = sum(
            1 for a in u.alunos for i in a.indicacoes if i.status == "pendente"
        )
        resumo.append({
            "unidade_id": u.id, "unidade": u.nome,
            "total_alunos": n_alunos,
            "indicacoes_confirmadas": n_confirmadas,
            "indicacoes_pendentes": n_pendentes,
        })
    return jsonify({"ok": True, "unidades": resumo})


@app.route("/api/admin/alunos", methods=["GET"])
@admin_obrigatorio
def admin_listar_alunos():
    unidade_id = request.args.get("unidade_id")
    query = Aluno.query
    if unidade_id:
        query = query.filter_by(unidade_id=unidade_id)
    alunos = query.order_by(Aluno.nome.asc()).all()
    return jsonify({"ok": True, "alunos": [a.to_dict() for a in alunos]})


@app.route("/api/admin/indicacoes", methods=["GET"])
@admin_obrigatorio
def admin_listar_indicacoes():
    status_filtro = request.args.get("status")
    query = Indicacao.query
    if status_filtro:
        query = query.filter_by(status=status_filtro)
    indicacoes = query.order_by(Indicacao.criado_em.desc()).all()
    return jsonify({"ok": True, "indicacoes": [i.to_dict() for i in indicacoes]})


@app.route("/api/admin/indicacoes/<int:indicacao_id>/confirmar", methods=["POST"])
@admin_obrigatorio
def admin_confirmar_indicacao(indicacao_id):
    indicacao = Indicacao.query.get(indicacao_id)
    if not indicacao:
        return jsonify({"erro": "Indicação não encontrada."}), 404
    indicacao.status = "confirmada"
    indicacao.confirmada_em = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({"ok": True, "indicacao": indicacao.to_dict()})


@app.route("/api/admin/indicacoes/<int:indicacao_id>/rejeitar", methods=["POST"])
@admin_obrigatorio
def admin_rejeitar_indicacao(indicacao_id):
    indicacao = Indicacao.query.get(indicacao_id)
    if not indicacao:
        return jsonify({"erro": "Indicação não encontrada."}), 404
    indicacao.status = "rejeitada"
    db.session.commit()
    return jsonify({"ok": True, "indicacao": indicacao.to_dict()})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
