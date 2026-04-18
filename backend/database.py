import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# PRIORITIZES Environment Variable (PostgreSQL/Cloud)
# FALLS BACK to Local SQLite (Zero-Config Development)
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./smart_lot.db")

# Only use check_same_thread for SQLite
is_sqlite = SQLALCHEMY_DATABASE_URL.startswith("sqlite")
engine_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args=engine_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
