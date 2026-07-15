from database.models import StockMaster
from database.repositories.stock_repository import StockRepository
from engines.quality_score_engine import QualityScoreEngine
from utils.data_utils import number, pick, read_table, stocks_to_frame


class UniverseService:
    @staticmethod
    def calculate_peg(pe, growth):
        try:
            pe_val = float(pe)
            growth_val = float(growth)
            if growth_val <= 0:
                return 0.0
            return round(pe_val / growth_val, 2)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def upload(file):
        from database.db import engine
        from database.models import StockMaster
        
        # Drop and recreate stock_master table to ensure new column structure is applied
        StockMaster.__table__.drop(bind=engine, checkfirst=True)
        StockMaster.__table__.create(bind=engine, checkfirst=True)

        df = QualityScoreEngine.calculate(read_table(file))
        df["Ticker"] = df["Ticker"].astype(str).str.strip().str.upper()
        df = df[df["Ticker"].ne("")]
        df = df.drop_duplicates(subset=["Ticker"], keep="first")
        records = []

        for _, row in df.iterrows():
            pe = number(pick(row, ["PE Ratio"]))
            fwd_pe = number(pick(row, ["Forward PE Ratio"]))
            eps_growth_hist = number(pick(row, ["5Y Historical EPS Growth"]))
            eps_growth_fwd = number(pick(row, ["1Y Forward EPS Growth"]))

            peg_hist = UniverseService.calculate_peg(pe, eps_growth_hist)
            peg_fwd = UniverseService.calculate_peg(fwd_pe, eps_growth_fwd)

            records.append(
                StockMaster(
                    ticker=pick(row, ["Ticker"]),
                    name=pick(row, ["Name"]),
                    sub_sector=pick(row, ["Sub-Sector", "Sector"]),
                    market_cap=number(pick(row, ["Market Cap"])),
                    close_price=number(pick(row, ["Close Price"])),
                    roce=number(pick(row, ["ROCE", "Return on Equity"])),  # fallback to Return on Equity if ROCE not present
                    pe_ratio=pe,
                    forward_pe_ratio=fwd_pe,
                    sector_pe=number(pick(row, ["Sector PE"])),
                    cagr_5y=number(pick(row, ["5Y CAGR"])),
                    revenue_growth_5y=number(pick(row, ["5Y Historical Revenue Growth"])),
                    free_cash_flow=number(pick(row, ["Free Cash Flow"])),
                    debt_to_equity=number(pick(row, ["Debt to Equity"])),
                    return_vs_nifty=number(pick(row, ["1M Return vs Nifty"])),
                    sharpe_ratio=number(pick(row, ["Sharpe Ratio"])),
                    alpha=number(pick(row, ["Alpha"])),
                    quality_score=number(pick(row, ["QUALITY_SCORE"])),
                    return_on_equity=number(pick(row, ["Return on Equity"])),
                    return_on_equity_5y_avg=number(pick(row, ["5Y Avg Return on Equity"])),
                    revenue_growth_1y_fwd=number(pick(row, ["1Y Forward Revenue Growth"])),
                    eps_growth_5y_hist=eps_growth_hist,
                    eps_growth_1y_fwd=eps_growth_fwd,
                    op_cash_flow_growth_5y_hist=number(pick(row, ["5Y Hist Op. Cash Flow Growth"])),
                    op_cash_flow_growth_1y_fwd=number(pick(row, ["1Y Fwd Op. Cash Flow Growth"])),
                    net_profit_margin_5y_avg=number(pick(row, ["5Y Avg Net Profit Margin"])),
                    earnings_quality_rank=number(pick(row, ["Earnings Quality Rank"])),
                    price_to_intrinsic_value_rank=number(pick(row, ["Price to Intrinsic Value Rank"])),
                    fundamental_score=number(pick(row, ["Fundamental Score"])),
                    peg_historical=peg_hist,
                    peg_forward=peg_fwd,
                )
            )

        StockRepository.replace_all(records)
        return len(records)

    @staticmethod
    def dataframe():
        return stocks_to_frame(StockRepository.get_all())
