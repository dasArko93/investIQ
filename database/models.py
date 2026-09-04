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


class MFScheme(Base):
    """Mutual fund scheme metadata categorized by SEBI market cap classification."""
    __tablename__ = "schemes"

    id = Column(Integer, primary_key=True)
    scheme_code = Column(String, unique=True, index=True)
    scheme_name = Column(String, index=True)
    amc = Column(String, index=True)
    category = Column(String, index=True)  # Large Cap, Mid Cap, Small Cap, Flexi/Multi Cap
    aum_cr = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class MFPortfolioSnapshot(Base):
    """Records disclosure download batch dates and audit metadata."""
    __tablename__ = "mf_snapshots"

    id = Column(Integer, primary_key=True)
    snapshot_date = Column(DateTime, index=True)
    month_str = Column(String, index=True)  # e.g., '2026-03', '2026-02'
    source = Column(String, default="AMC Disclosure")
    total_schemes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class MFSchemeHolding(Base):
    """Junction table mapping individual stock holdings per scheme per snapshot date."""
    __tablename__ = "scheme_holdings"

    id = Column(Integer, primary_key=True)
    scheme_id = Column(Integer, index=True)
    isin = Column(String, index=True)
    ticker = Column(String, index=True)
    stock_name = Column(String, index=True)
    sector = Column(String, index=True)
    market_cap_category = Column(String, index=True)  # Large Cap, Mid Cap, Small Cap
    weight_pct = Column(Float, default=0.0)
    quantity = Column(Float, default=0.0)
    market_value = Column(Float, default=0.0)
    snapshot_date = Column(DateTime, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserPortfolioHolding(Base):
    """User portfolio stock holdings mapped by ISIN for consensus gap analysis."""
    __tablename__ = "user_portfolio"

    id = Column(Integer, primary_key=True)
    isin = Column(String, index=True)
    ticker = Column(String, index=True)
    stock_name = Column(String)
    holding_qty = Column(Float, default=0.0)
    current_weight_pct = Column(Float, default=0.0)
    current_value = Column(Float, default=0.0)
    snapshot_date = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)