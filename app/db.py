from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

SQLITE_URL = "sqlite:///./betting_analysis.db"
DATABASE_URL = os.getenv("BETTING_DB_URL", SQLITE_URL)

if DATABASE_URL.startswith("postgresql") and "psycopg2" not in DATABASE_URL:
    try:
        import psycopg2
    except ImportError:
        print("PostgreSQL driver not available, using SQLite instead")
        DATABASE_URL = SQLITE_URL

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    try:
        engine = create_engine(DATABASE_URL)
    except Exception as e:
        print(f"Failed to connect to database: {e}, using SQLite")
        engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from app import models_db
    Base.metadata.create_all(bind=engine)
