from engines.sharpe_engine import SharpeEngine

from engines.sortino_engine import SortinoEngine

from engines.drawdown_engine import DrawdownEngine


class QuantService:

    @staticmethod
    def analyze(

        returns,

        cumulative_returns

    ):

        return {

            "sharpe":

                SharpeEngine
                .calculate(returns),

            "sortino":

                SortinoEngine
                .calculate(returns),

            "drawdown":

                DrawdownEngine
                .calculate(
                    cumulative_returns
                )

        }