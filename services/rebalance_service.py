from engines.advanced_rebalance_engine import (
    AdvancedRebalanceEngine
)


class RebalanceService:

    @staticmethod
    def generate(df):

        return (

            AdvancedRebalanceEngine

            .rebalance(df)

        )