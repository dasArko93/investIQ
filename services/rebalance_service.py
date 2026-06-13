from engines.advanced_rebalance_engine import AdvancedRebalanceEngine

class RebalanceService:

    @staticmethod
    def generate(df, strategy=None, new_capital=0.0, universe_df=None):
        if strategy is None:
            strategy = {
                "targetSectorAllocation": {},
                "maxStockAllocation": 15.0,
                "maxSectorAllocation": 30.0,
                "rebalanceThresholdPercent": 5.0,
                "riskProfile": "Moderate",
                "rebalanceFrequency": "Quarterly",
                "rebalanceMode": "Hybrid",
                "momentumOverride": False,
                "smartRebalancing": True,
                "allowNewStocks": True,
                "rebalanceLevel": "Stock-Level"
            }
        return AdvancedRebalanceEngine.rebalance(df, strategy, new_capital, universe_df)