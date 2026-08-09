"""
models.py
Modelos do banco: Unidade, Aluno, Indicacao (indicação/matrícula) e Clique.
"""

import secrets
from datetime import datetime, timezone

from database import db

VALOR_POR_INDICACAO = 50.0
LIMITE_INDICACOES_DESCONTO = 4  # a partir da 5ª, o valor vira saldo


def agora():
    return datetime.now(timezone.utc)


class Unidade(db.Model):
    __tablename__ = "unidades"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), unique=True, nullable=False)

    alunos = db.relationship("Aluno", backref="unidade", lazy=True)

    def to_dict(self):
        return {"id": self.id, "nome": self.nome}


def gerar_codigo_afiliado() -> str:
    """Gera um código curto e único para o link de indicação do aluno."""
    while True:
        codigo = secrets.token_hex(4)  # 8 caracteres hexadecimais
        if not Aluno.query.filter_by(codigo_afiliado=codigo).first():
            return codigo


class Aluno(db.Model):
    __tablename__ = "alunos"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(160), nullable=False)
    cpf = db.Column(db.String(14), nullable=False, unique=True)
    email = db.Column(db.String(160), nullable=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    unidade_id = db.Column(db.Integer, db.ForeignKey("unidades.id"), nullable=False)
    codigo_afiliado = db.Column(db.String(16), unique=True, nullable=False)
    criado_em = db.Column(db.DateTime(timezone=True), default=agora)

    indicacoes = db.relationship("Indicacao", backref="indicador", lazy=True,
                                  foreign_keys="Indicacao.aluno_id")
    cliques = db.relationship("Clique", backref="aluno", lazy=True)

    def resumo_financeiro(self):
        confirmadas = [i for i in self.indicacoes if i.status == "confirmada"]
        pendentes = [i for i in self.indicacoes if i.status == "pendente"]
        n_confirmadas = len(confirmadas)
        n_desconto = min(n_confirmadas, LIMITE_INDICACOES_DESCONTO)
        n_saldo = max(n_confirmadas - LIMITE_INDICACOES_DESCONTO, 0)
        return {
            "total_indicacoes_confirmadas": n_confirmadas,
            "total_indicacoes_pendentes": len(pendentes),
            "desconto_mensalidade": n_desconto * VALOR_POR_INDICACAO,
            "saldo": n_saldo * VALOR_POR_INDICACAO,
            "total_cliques": len(self.cliques),
        }

    def to_dict(self, incluir_financeiro=True):
        base = {
            "id": self.id,
            "nome": self.nome,
            "cpf": self.cpf,
            "email": self.email,
            "unidade": self.unidade.nome if self.unidade else None,
            "unidade_id": self.unidade_id,
            "codigo_afiliado": self.codigo_afiliado,
            "criado_em": self.criado_em.strftime("%d/%m/%Y %H:%M") if self.criado_em else None,
        }
        if incluir_financeiro:
            base.update(self.resumo_financeiro())
        return base


class Indicacao(db.Model):
    __tablename__ = "indicacoes"
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey("alunos.id"), nullable=False)
    nome_indicado = db.Column(db.String(160), nullable=False)
    cpf_indicado = db.Column(db.String(14), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pendente")  # pendente | confirmada | rejeitada
    criado_em = db.Column(db.DateTime(timezone=True), default=agora)
    confirmada_em = db.Column(db.DateTime(timezone=True), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "aluno_id": self.aluno_id,
            "aluno_nome": self.indicador.nome if self.indicador else None,
            "unidade": self.indicador.unidade.nome if self.indicador and self.indicador.unidade else None,
            "nome_indicado": self.nome_indicado,
            "cpf_indicado": self.cpf_indicado,
            "status": self.status,
            "criado_em": self.criado_em.strftime("%d/%m/%Y %H:%M") if self.criado_em else None,
            "confirmada_em": self.confirmada_em.strftime("%d/%m/%Y %H:%M") if self.confirmada_em else None,
        }


class Clique(db.Model):
    __tablename__ = "cliques"
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey("alunos.id"), nullable=False)
    criado_em = db.Column(db.DateTime(timezone=True), default=agora)
    ip = db.Column(db.String(64), nullable=True)
