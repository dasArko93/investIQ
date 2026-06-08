from database.db import SessionLocal
from database.models import Holding
from datetime import datetime
from sqlalchemy import distinct


class HoldingRepository:

    @staticmethod
    def replace_all(records):

        db = SessionLocal()

        try:

            db.query(
                Holding
            ).delete()

            db.bulk_save_objects(
                records
            )

            db.commit()

        except Exception:

            db.rollback()
            raise

        finally:

            db.close()

    @staticmethod
    def append_all(records):
        """Append holdings (don't delete existing)."""
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
    def get_all():

        db = SessionLocal()

        try:
            return db.query(Holding).order_by(Holding.snapshot_date.desc()).all()

        finally:
            db.close()

    @staticmethod
    def get_snapshot_dates():
        """Get list of distinct snapshot dates."""
        db = SessionLocal()

        try:
            dates = db.query(distinct(Holding.snapshot_date)).order_by(Holding.snapshot_date.desc()).all()
            return [d[0] for d in dates]

        finally:
            db.close()

    @staticmethod
    def get_by_snapshot_date(snapshot_date):
        """Get all holdings for a specific snapshot date."""
        db = SessionLocal()

        try:
            return db.query(Holding).filter(Holding.snapshot_date == snapshot_date).all()

        finally:
            db.close()
