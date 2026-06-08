class PositionSizingEngine:
    @staticmethod
    def equal_weight(cash, tickers):
        if cash <= 0 or not tickers:
            return []
        amount = cash / len(tickers)
        return [{"Ticker": ticker, "Allocation Amount": round(amount)} for ticker in tickers]
