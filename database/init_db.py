from database.db import engine
from database.models import Base


def init_db():
    Base.metadata.create_all(bind=engine)
    
    # Auto-migration for new columns in SQLite
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if 'holdings' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('holdings')]
        with engine.begin() as conn:
            if 'pnl_pct' not in columns:
                conn.execute(text("ALTER TABLE holdings ADD COLUMN pnl_pct FLOAT"))
            if 'day_pnl' not in columns:
                conn.execute(text("ALTER TABLE holdings ADD COLUMN day_pnl FLOAT"))
            if 'day_pnl_pct' not in columns:
                conn.execute(text("ALTER TABLE holdings ADD COLUMN day_pnl_pct FLOAT"))
            if 'broker_sector' not in columns:
                conn.execute(text("ALTER TABLE holdings ADD COLUMN broker_sector VARCHAR"))
            if 'asset_class' not in columns:
                conn.execute(text("ALTER TABLE holdings ADD COLUMN asset_class VARCHAR"))
            if 'no_of_smallcases' not in columns:
                conn.execute(text("ALTER TABLE holdings ADD COLUMN no_of_smallcases FLOAT"))


if __name__ == "__main__":
    init_db()
    print("InvestIQ database initialized")
