import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Hybrid Database URL support (PostgreSQL in cloud, SQLite locally)
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    DATABASE_URL = f"sqlite:///{DATA_DIR / 'investiq.db'}"

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False
        }
    )
else:
    # Auto-adjust postgres driver dialect for SQLAlchemy 2.0 compatibility
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

from database.models import Base
from sqlalchemy import inspect, Table, MetaData, text

try:
    inspector = inspect(engine)
    if "stock_master" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("stock_master")]
        if "return_on_equity" not in columns:
            with engine.begin() as conn:
                if engine.dialect.name == "sqlite":
                    conn.execute(text("DROP TABLE IF EXISTS stock_master"))
                else:
                    conn.execute(text("DROP TABLE IF EXISTS stock_master CASCADE"))
except Exception:
    pass

Base.metadata.create_all(bind=engine)

