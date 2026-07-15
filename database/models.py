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

    pnl_pct = Column(Float)

    day_pnl = Column(Float)

    day_pnl_pct = Column(Float)

    broker_sector = Column(String)

    asset_class = Column(String)

    no_of_smallcases = Column(Float)

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

    return_on_equity = Column(Float)

    return_on_equity_5y_avg = Column(Float)

    revenue_growth_1y_fwd = Column(Float)

    eps_growth_5y_hist = Column(Float)

    eps_growth_1y_fwd = Column(Float)

    op_cash_flow_growth_5y_hist = Column(Float)

    op_cash_flow_growth_1y_fwd = Column(Float)

    net_profit_margin_5y_avg = Column(Float)

    earnings_quality_rank = Column(Float)

    price_to_intrinsic_value_rank = Column(Float)

    fundamental_score = Column(Float)

    peg_historical = Column(Float)

    peg_forward = Column(Float)


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


class MFHolding(Base):
    __tablename__ = "mf_holdings"

    id = Column(Integer, primary_key=True)
    fund_name = Column(String, index=True)
    sector = Column(String)
    date = Column(String)
    allocation = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)