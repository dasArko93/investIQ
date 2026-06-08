from database.repositories.watchlist_repository import (
    WatchlistRepository
)


class WatchlistService:

    @staticmethod
    def get_all():

        return (

            WatchlistRepository
            .get_all()

        )