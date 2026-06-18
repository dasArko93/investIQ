from database.models import Holding, TrendSnapshot
from database.repositories.holding_repository import HoldingRepository
from database.db import SessionLocal
from sqlalchemy import distinct
from utils.data_utils import holdings_to_frame, number, pick, parse_holdings_file, HOLDING_COLUMNS
from datetime import datetime


class HoldingsService:
    @staticmethod
    def upload(file):
        """Parse, clean, append/overwrite, and prune holdings history to 15 entries."""
        df, snapshot_date = parse_holdings_file(file)
        if df.empty:
            return 0

        # Overwrite same-day snapshot if it already exists
        db = SessionLocal()
        try:
            db.query(Holding).filter(Holding.snapshot_date == snapshot_date).delete()
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        records = []
        for _, row in df.iterrows():
            records.append(
                Holding(
                    security=pick(row, ["Security"]),
                    no_of_smallcases=number(pick(row, ["No. of Smallcases", "No of Smallcases", "Smallcases"])),
                    quantity=number(pick(row, ["Quantity"])),
                    average_cost=number(pick(row, ["Average Cost ₹", "Average Cost Rs", "Average Cost"])),
                    portfolio_weight=number(pick(row, ["Portfolio Weight %"])),
                    ltp=number(pick(row, ["LTP ₹", "LTP Rs", "LTP"])),
                    invested_value=number(pick(row, ["Invested Value ₹", "Invested Value Rs", "Invested Value"])),
                    current_value=number(pick(row, ["Current Value ₹", "Current Value Rs", "Current Value"])),
                    pnl=number(pick(row, ["P & L ₹", "P&L ₹", "PnL Rs", "P & L Rs", "P & L", "PnL"])),
                    pnl_pct=number(pick(row, ["Net Change %", "PnL %", "Return %", "Unrealized Gain %", "P&L %", "PnL Percent", "Gain Percent", "Gain %"])),
                    day_pnl=number(pick(row, ["Daily Change ₹", "Daily Change Rs", "Daily Change", "Day PnL", "Day's PnL"])),
                    day_pnl_pct=number(pick(row, ["Daily Change %", "Daily Change Percent", "Day PnL %", "Day's PnL %"])),
                    broker_sector=str(pick(row, ["Sector", "Sub-Sector", "Broker Sector", "Industry", "Sub Sector"], default="Unknown")),
                    asset_class=str(pick(row, ["Asset Class", "Instrument Type", "Segment", "Category", "Instrument"], default="Equity")),
                    snapshot_date=snapshot_date,
                )
            )

        # Save holdings snapshot history
        HoldingsService.append_and_prune(records)
        return len(records)

    @staticmethod
    def append_and_prune(records):
        db = SessionLocal()
        try:
            db.bulk_save_objects(records)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def dataframe(snapshot_date=None):
        """Return a DataFrame of holdings. By default, returns the LATEST snapshot only."""
        if snapshot_date is None:
            dates = HoldingsService.get_snapshots()
            if not dates:
                return pd_empty_df()
            snapshot_date = dates[0]
        return holdings_to_frame(HoldingRepository.get_by_snapshot_date(snapshot_date))

    @staticmethod
    def get_snapshot_summary(limit=None):
        """Return chronological summary of snapshots (invested and pnl)."""
        db = SessionLocal()
        try:
            dates = db.query(distinct(Holding.snapshot_date)).order_by(Holding.snapshot_date.asc()).all()
            date_list = [d[0] for d in dates]
            if limit is not None:
                date_list = date_list[-limit:]
            
            summary = []
            for d in date_list:
                rows = db.query(Holding).filter(Holding.snapshot_date == d).all()
                invested = sum(r.invested_value for r in rows)
                current = sum(r.current_value for r in rows)
                pnl = sum(r.pnl for r in rows)
                summary.append({
                    "date": d,
                    "invested": invested,
                    "current": current,
                    "pnl": pnl
                })
            return summary
        finally:
            db.close()

    @staticmethod
    def group_snapshots_by_mode(snapshots, view_mode):
        """
        Groups a list of snapshot dicts by:
        - "All Uploads": returns all snapshots (sorted by date)
        - "Monthly View": Groups by Year and Month, picking the latest snapshot of each month.
        - "Yearly View": Groups by Year, picking the latest snapshot of each year.
        """
        if not snapshots:
            return []
        
        sorted_snaps = sorted(snapshots, key=lambda s: s["date"])
        
        if view_mode == "Monthly View":
            grouped = {}
            for snap in sorted_snaps:
                key = (snap["date"].year, snap["date"].month)
                grouped[key] = snap
            return sorted(grouped.values(), key=lambda s: s["date"])
            
        elif view_mode == "Yearly View":
            grouped = {}
            for snap in sorted_snaps:
                key = snap["date"].year
                grouped[key] = snap
            return sorted(grouped.values(), key=lambda s: s["date"])
            
        else:
            return sorted_snaps

    @staticmethod
    def get_snapshots():
        """Get list of distinct snapshot dates."""
        return HoldingRepository.get_snapshot_dates()

    @staticmethod
    def get_holdings_at_date(snapshot_date):
        """Get holdings for a specific snapshot date."""
        return HoldingRepository.get_by_snapshot_date(snapshot_date)



def pd_empty_df():
    import pandas as pd
    return pd.DataFrame(columns=HOLDING_COLUMNS)

