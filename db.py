import os
from urllib.parse import quote_plus
from sqlalchemy import (
    create_engine, Column, Integer, String, Numeric,
    Date, Enum, ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from dotenv import load_dotenv
import enum

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "financas")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

DATABASE_URL = (
    f"postgresql+psycopg2://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class TipoTransacao(str, enum.Enum):
    gasto = "gasto"
    receita = "receita"


class Categoria(Base):
    __tablename__ = "categorias"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), nullable=False, unique=True)
    cor = Column(String(7), default="#4CAF50")
    transacoes = relationship("Transacao", back_populates="categoria")
    metas = relationship("Meta", back_populates="categoria")


class Transacao(Base):
    __tablename__ = "transacoes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    data = Column(Date, nullable=False)
    descricao = Column(String(200), nullable=False)
    valor = Column(Numeric(12, 2), nullable=False)
    tipo = Column(Enum(TipoTransacao), nullable=False)
    categoria_id = Column(Integer, ForeignKey("categorias.id"), nullable=True)
    categoria = relationship("Categoria", back_populates="transacoes")


class Meta(Base):
    __tablename__ = "metas"
    id = Column(Integer, primary_key=True, autoincrement=True)
    categoria_id = Column(Integer, ForeignKey("categorias.id"), nullable=False)
    mes = Column(Integer, nullable=False)
    ano = Column(Integer, nullable=False)
    limite = Column(Numeric(12, 2), nullable=False)
    categoria = relationship("Categoria", back_populates="metas")


def init_db():
    Base.metadata.create_all(bind=engine)
    _seed_categorias()


def _seed_categorias():
    session = SessionLocal()
    try:
        if session.query(Categoria).count() == 0:
            defaults = [
                ("Moradia", "#E53935"),
                ("Alimentacao", "#FB8C00"),
                ("Transporte", "#F4D03F"),
                ("Saude", "#43A047"),
                ("Educacao", "#1E88E5"),
                ("Lazer", "#8E24AA"),
                ("Servicos", "#00ACC1"),
                ("Impostos", "#6D4C41"),
                ("Investimentos", "#00897B"),
                ("Outros", "#757575"),
                ("Salario", "#2E7D32"),
            ]
            for nome, cor in defaults:
                session.add(Categoria(nome=nome, cor=cor))
            session.commit()
    finally:
        session.close()


def get_session():
    return SessionLocal()