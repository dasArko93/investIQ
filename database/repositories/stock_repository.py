from database.db import SessionLocal
from database.models import StockMaster


class StockRepository:

    @staticmethod
    def replace_all(records):

        db = SessionLocal()

        try:

            db.query(
                StockMaster
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
    def get_all():

        db = SessionLocal()

        try:

            return db.query(
                StockMaster
            ).all()

        finally:

            db.close()

    @staticmethod
    def count():

        db = SessionLocal()

        try:

            return db.query(
                StockMaster
            ).count()

        finally:

            db.close()
