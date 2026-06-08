import numpy as np

class CVaREngine:

    @staticmethod
    def calculate(
        returns,
        confidence=95
    ):

        var = np.percentile(
            returns,
            100-confidence
        )

        return returns[
            returns <= var
        ].mean()