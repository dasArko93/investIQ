import numpy as np

class MonteCarloEngine:

    @staticmethod
    def simulate(
        returns,
        initial=100000,
        days=252,
        simulations=1000
    ):

        results = np.zeros(
            (
                days,
                simulations
            )
        )

        mean = returns.mean()
        std = returns.std()

        for s in range(
            simulations
        ):

            prices = [initial]

            for _ in range(days):

                shock = np.random.normal(
                    mean,
                    std
                )

                prices.append(
                    prices[-1]
                    *
                    (
                        1 + shock
                    )
                )

            results[:,s] = prices[1:]

        return results