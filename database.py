"""Database configuration"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from models import Base

DB_URL = os.getenv('DATABASE_URL', 'mysql+pymysql://root:upp7ufary@localhost:3306/teacherdb?charset=utf8mb4')
import pymysql

# Configure pymysql to handle authentication issues
pymysql.install_as_MySQLdb()

engine = create_engine(DB_URL, pool_pre_ping=True, pool_recycle=3600, connect_args={
    "ssl_disabled": True
})

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db():
    """Инициализация базы данных"""
    Base.metadata.create_all(engine)


@contextmanager
def get_session():
    """Контекстный менеджер для сессий"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
