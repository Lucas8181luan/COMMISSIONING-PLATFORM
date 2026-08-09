"""
database.py
Configuração do SQLAlchemy e conexão com o PostgreSQL do Render.

Variável de ambiente necessária:
  - DATABASE_URL -> string de conexão fornecida pelo Render (Postgres)
"""

import os
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "sqlite:///local_dev.db")
    # O Render às vezes fornece a URL com o prefixo antigo "postgres://",
    # mas o SQLAlchemy 2.x exige "postgresql://".
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def init_db(app):
    app.config["SQLALCHEMY_DATABASE_URI"] = get_database_url()
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
    db.init_app(app)
    with app.app_context():
        db.create_all()
        seed_unidades()


def seed_unidades():
    """Garante que a lista de unidades (incluindo ADMIN) exista no banco."""
    from models import Unidade

    UNIDADES_PADRAO = [
        "ADMIN",
        "IFP - Aguas Lindas", "IFP - Arapiraca", "IFP - Cajazeiras", "IFP - Camaçari",
        "IFP - Campina Grande", "IFP - Canaã", "IFP - Cariacica", "IFP - Caruaru",
        "IFP - Ceilândia", "IFP - Duque de Caxias", "IFP - Formosa", "IFP - Gama",
        "IFP - João Pessoa", "IFP - Luziânia", "IFP - Madureira", "IFP - Manaus",
        "IFP - Marabá", "IFP - Paranoá", "IFP - Parauapebas", "IFP - Planaltina DF",
        "IFP - Planaltina GO", "IFP - Recanto das Emas", "IFP - Ribeirão das Neves",
        "IFP - São Luís", "IFP - São Sebastião", "IFP - Serra", "IFP - Uberlândia",
        "IFP - Valparaíso", "IFP - Vitória da Conquista",
        "IFPA - Anápolis", "IFPA - Goiânia", "IFPA - Novo Gama", "IFPA - Taguatinga",
    ]

    existentes = {u.nome for u in Unidade.query.all()}
    novas = [Unidade(nome=nome) for nome in UNIDADES_PADRAO if nome not in existentes]
    if novas:
        db.session.bulk_save_objects(novas)
        db.session.commit()
