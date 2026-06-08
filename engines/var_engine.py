import numpy as np

class VaREngine:

    @staticmethod
    def calculate(
        returns,
        confidence=95
    ):

        return np.percentile(
            returns,
            100-confidence
        )