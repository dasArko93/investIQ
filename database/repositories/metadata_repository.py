from database.db import SessionLocal
from database.models import Metadata


class MetadataRepository:

    @staticmethod
    def set(key, value):

        db = SessionLocal()

        try:

            record = db.query(
                Metadata
            ).filter(
                Metadata.key == key
            ).first()

            if record:

                record.value = value

            else:

                db.add(
                    Metadata(
                        key=key,
                        value=value
                    )
                )

            db.commit()

        finally:

            db.close()

    @staticmethod
    def get(key):

        db = SessionLocal()

        try:

            record = db.query(
                Metadata
            ).filter(
                Metadata.key == key
            ).first()

            return record.value if record else None

        finally:

            db.close()