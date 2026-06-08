import numpy as np

class SortinoEngine:

    @staticmethod
    def calculate(
        returns
    ):

        downside = (
            returns[
                returns < 0
            ]
        )

        return (

            returns.mean()
            * 252

        ) / (

            downside.std()
            *
            np.sqrt(252)

        )