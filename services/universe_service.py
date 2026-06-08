from database.models import StockMaster
from database.repositories.stock_repository import StockRepository
from engines.quality_score_engine import QualityScoreEngine
from utils.data_utils import number, pick, read_table, stocks_to_frame


class UniverseService:
    @staticmethod
    def upload(file):
        df = QualityScoreEngine.calculate(read_table(file))
        df["Ticker"] = df["Ticker"].astype(str).str.strip().str.upper()
        df = df[df["Ticker"].ne("")]
        df = df.drop_duplicates(subset=["Ticker"], keep="first")
        records = []

        for _, row in df.iterrows():
            records.append(
                StockMaster(
                    ticker=pick(row, ["Ticker"]),
                    name=pick(row, ["Name"]),
                    sub_sector=pick(row, ["Sub-Sector", "Sector"]),
                    market_cap=number(pick(row, ["Market Cap"])),
                    close_price=number(pick(row, ["Close Price"])),
                    roce=number(pick(row, ["ROCE"])),
                    pe_ratio=number(pick(row, ["PE Ratio"])),
                    forward_pe_ratio=number(pick(row, ["Forward PE Ratio"])),
                    sector_pe=number(pick(row, ["Sector PE"])),
                    cagr_5y=number(pick(row, ["5Y CAGR"])),
                    revenue_growth_5y=number(pick(row, ["5Y Historical Revenue Growth"])),
                    free_cash_flow=number(pick(row, ["Free Cash Flow"])),
                    debt_to_equity=number(pick(row, ["Debt to Equity"])),
                    return_vs_nifty=number(pick(row, ["1M Return vs Nifty"])),
                    sharpe_ratio=number(pick(row, ["Sharpe Ratio"])),
                    alpha=number(pick(row, ["Alpha"])),
                    quality_score=number(pick(row, ["QUALITY_SCORE"])),
                )
            )

        StockRepository.replace_all(records)
        return len(records)

    @staticmethod
    def dataframe():
        return stocks_to_frame(StockRepository.get_all())
