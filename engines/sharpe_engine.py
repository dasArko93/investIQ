import numpy as np

class SharpeEngine:

    @staticmethod
    def calculate(
        returns,
        rf=0.07
    ):

        return (

            (
                returns.mean()
                * 252
            )
            -
            rf

        ) / (

            returns.std()
            *
            np.sqrt(252)

        )