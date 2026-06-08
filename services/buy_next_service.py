from engines.buy_next_engine import (
    BuyNextEngine
)


class BuyNextService:

    @staticmethod
    def suggest(

        universe,

        portfolio,

        cash

    ):

        return (

            BuyNextEngine

            .recommend(

                universe,

                portfolio,

                cash

            )

        )