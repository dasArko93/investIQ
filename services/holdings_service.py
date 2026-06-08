from database.models import Holding, TrendSnapshot
from database.repositories.holding_repository import HoldingRepository
from utils.data_utils import holdings_to_frame, number, pick, read_table
from datetime import datetime


class HoldingsService:
    @staticmethod
    def upload(file):
        """Append new holdings data with snapshot date (append mode, don't replace)."""
        df = read_table(file)
        records = []
        snapshot_date = datetime.utcnow()

        for _, row in df.iterrows():
            records.append(
                Holding(
                    security=pick(row, ["Security"]),
                    quantity=number(pick(row, ["Quantity"])),
                    average_cost=number(pick(row, ["Average Cost Rs", "Average Cost"])),
                    portfolio_weight=number(pick(row, ["Portfolio Weight %"])),
                    ltp=number(pick(row, ["LTP Rs", "LTP"])),
                    invested_value=number(pick(row, ["Invested Value Rs", "Invested Value"])),
                    current_value=number(pick(row, ["Current Value Rs", "Current Value"])),
                    pnl=number(pick(row, ["PnL Rs", "P&L Rs", "P & L Rs", "P & L", "PnL"])),
                    snapshot_date=snapshot_date,  # Tag with snapshot date
                )
            )

        # Append instead of replace
        HoldingRepository.append_all(records)
        return len(records)

    @staticmethod
    def dataframe():
        return holdings_to_frame(HoldingRepository.get_all())
    
    @staticmethod
    def get_snapshots():
        """Get list of distinct snapshot dates."""
        return HoldingRepository.get_snapshot_dates()
    
    @staticmethod
    def get_holdings_at_date(snapshot_date):
        """Get holdings for a specific snapshot date."""
        return HoldingRepository.get_by_snapshot_date(snapshot_date)
