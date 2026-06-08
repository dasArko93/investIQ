class ChecklistEngine:

    @staticmethod
    def passes(stock):

        return (

            stock["ROCE"] > 15

            and

            stock["5Y CAGR"] > 15

            and

            stock["Debt to Equity"] < 0.5

            and

            stock["PE Ratio"]

            <

            stock["Sector PE"]

        )