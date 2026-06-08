from database.db import SessionLocal
from database.models import Goal


class GoalRepository:

    @staticmethod
    def add(record):

        db = SessionLocal()

        db.add(record)

        db.commit()

        db.close()

    @staticmethod
    def get_all():

        db = SessionLocal()

        rows = db.query(
            Goal
        ).all()

        db.close()

        return rows