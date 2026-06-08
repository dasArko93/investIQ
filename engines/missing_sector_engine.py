TARGET_SECTORS = [

    "Technology",
    "Consumer",
    "Insurance",
    "Private Banking",
    "Pharma",
    "Infrastructure",
    "Energy",
    "ETF"
]

class MissingSectorEngine:

    @staticmethod
    def identify(
        current_sectors
    ):

        return [

            s

            for s

            in TARGET_SECTORS

            if s not in current_sectors

        ]