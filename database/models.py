from sqlalchemy.orm import declarative_base
from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    DateTime,
    Boolean,
    Text
)

from datetime import datetime

Base = declarative_base()


class Holding(Base):

    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True)

    security = Column(String)

    quantity = Column(Float)

    average_cost = Column(Float)

    portfolio_weight = Column(Float)

    ltp = Column(Float)

    invested_value = Column(Float)

    current_value = Column(Float)

    pnl = Column(Float)

    snapshot_date = Column(DateTime, default=datetime.utcnow, index=True)  # Track holding version date

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class PriceHistory(Base):
    """Store historical closing prices for trend and statistical analysis."""

    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True)

    ticker = Column(String, index=True)

    date = Column(DateTime, index=True)

    close = Column(Float)

    high = Column(Float)

    low = Column(Float)

    open = Column(Float)

    volume = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)


class TrendSnapshot(Base):
    """Track portfolio composition changes over time for trend analysis."""

    __tablename__ = "trend_snapshot"

    id = Column(Integer, primary_key=True)

    snapshot_date = Column(DateTime, index=True, default=datetime.utcnow)

    security = Column(String)

    quantity = Column(Float)

    current_value = Column(Float)

    pnl = Column(Float)

    notes = Column(Text)  # e.g., "Bought", "Sold", "Rebalanced"


class StockMaster(Base):

    __tablename__ = "stock_master"

    ticker = Column(
        String,
        primary_key=True
    )

    name = Column(String)

    sub_sector = Column(String)

    market_cap = Column(Float)

    close_price = Column(Float)

    roce = Column(Float)

    pe_ratio = Column(Float)

    forward_pe_ratio = Column(Float)

    sector_pe = Column(Float)

    cagr_5y = Column(Float)

    revenue_growth_5y = Column(Float)

    free_cash_flow = Column(Float)

    debt_to_equity = Column(Float)

    return_vs_nifty = Column(Float)

    sharpe_ratio = Column(Float)

    alpha = Column(Float)

    quality_score = Column(Float)


class Metadata(Base):

    __tablename__ = "metadata"

    key = Column(
        String,
        primary_key=True
    )

    value = Column(String)


class PortfolioSnapshot(Base):

    __tablename__ = "portfolio_snapshots"

    id = Column(
        Integer,
        primary_key=True
    )

    portfolio_value = Column(Float)

    health_score = Column(Float)

    snapshot_date = Column(
        DateTime,
        default=datetime.utcnow
    )


class Watchlist(Base):

    __tablename__ = "watchlist"

    id = Column(
        Integer,
        primary_key=True
    )

    ticker = Column(String)

    added_date = Column(
        DateTime,
        default=datetime.utcnow
    )


class Alert(Base):

    __tablename__ = "alerts"

    id = Column(
        Integer,
        primary_key=True
    )

    ticker = Column(String)

    rule = Column(String)

    active = Column(
        Boolean,
        default=True
    )


class Journal(Base):

    __tablename__ = "journal"

    id = Column(
        Integer,
        primary_key=True
    )

    ticker = Column(String)

    notes = Column(Text)

    created_date = Column(
        DateTime,
        default=datetime.utcnow
    )


class Goal(Base):

    __tablename__ = "goals"

    id = Column(
        Integer,
        primary_key=True
    )

    goal_name = Column(String)

    target_amount = Column(Float)

    current_amount = Column(Float)

    target_date = Column(String)