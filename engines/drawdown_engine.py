class DrawdownEngine:

    @staticmethod
    def calculate(
        cumulative_returns
    ):

        rolling_max = (
            cumulative_returns
            .cummax()
        )

        drawdown = (

            cumulative_returns

            - rolling_max

        ) / rolling_max

        return drawdown.min()