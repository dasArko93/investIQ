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
    for table_name, table_obj in Base.metadata.tables.items():
        if table_name in inspector.get_table_names():
            db_cols = {col["name"] for col in inspector.get_columns(table_name)}
            model_cols = {col.name for col in table_obj.columns}
            if not model_cols.issubset(db_cols):
                with engine.begin() as conn:
                    if engine.dialect.name == "sqlite":
                        conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
                    else:
                        conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
except Exception:
    pass

Base.metadata.create_all(bind=engine)

