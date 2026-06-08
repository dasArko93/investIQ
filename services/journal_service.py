from database.repositories.journal_repository import (
    JournalRepository
)


class JournalService:

    @staticmethod
    def all():

        return (

            JournalRepository
            .get_all()

        )