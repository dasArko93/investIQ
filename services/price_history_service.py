"""Fetch and manage historical price data from Yahoo Finance."""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from database.models import PriceHistory
from database.db import SessionLocal


class PriceHistoryService:
    """Fetch and analyze historical stock prices for statistical analysis."""

    @staticmethod
    def fetch_days(ticker, days=180, auto_map_nse=True):
        """
        Fetch historical price data from Yahoo Finance.
        
        Args:
            ticker: Stock ticker (e.g., 'HDFC' or 'HDFCBANK.NS' for NSE)
            days: Number of calendar days to fetch
            auto_map_nse: If True, assume Indian stock and append .NS suffix
        
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        try:
            # Map ticker for NSE if needed
            yahoo_ticker = f"{ticker}.NS" if auto_map_nse else ticker
            
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            df = yf.download(yahoo_ticker, start=start_date, end=end_date, progress=False)
            
            if df.empty:
                return pd.DataFrame()
            
            df.reset_index(inplace=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [column[0].lower().replace(" ", "_") for column in df.columns]
            else:
                df.columns = [str(column).lower().replace(" ", "_") for column in df.columns]
            df = df.rename(columns={"datetime": "date"})
            df['ticker'] = ticker
            
            return df[['ticker', 'date', 'open', 'high', 'low', 'close', 'volume']]
        
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
            return pd.DataFrame()

    @staticmethod
    def fetch_180_days(ticker, auto_map_nse=True):
        """Fetch 180 days of historical price data from Yahoo Finance."""
        return PriceHistoryService.fetch_days(ticker, days=180, auto_map_nse=auto_map_nse)

    @staticmethod
    def fetch_365_days(ticker, auto_map_nse=True):
        """Fetch 365 days of historical price data from Yahoo Finance."""
        return PriceHistoryService.fetch_days(ticker, days=365, auto_map_nse=auto_map_nse)

    @staticmethod
    def store_price_history(ticker, df):
        """Store price history in database."""
        db = SessionLocal()
        try:
            # Delete old records for this ticker
            db.query(PriceHistory).filter(PriceHistory.ticker == ticker).delete()
            
            records = []
            for _, row in df.iterrows():
                records.append(
                    PriceHistory(
                        ticker=ticker,
                        date=row['date'],
                        open=row['open'],
                        high=row['high'],
                        low=row['low'],
                        close=row['close'],
                        volume=row['volume'],
                    )
                )
            
            db.bulk_save_objects(records)
            db.commit()
        
        except Exception as e:
            db.rollback()
            print(f"Error storing price history: {e}")
        
        finally:
            db.close()

    @staticmethod
    def get_price_history(ticker):
        """Retrieve price history for a ticker."""
        db = SessionLocal()
        try:
            return db.query(PriceHistory).filter(PriceHistory.ticker == ticker).order_by(PriceHistory.date).all()
        finally:
            db.close()

    @staticmethod
    def calculate_stats(ticker):
        """Calculate statistical metrics for a stock."""
        db = SessionLocal()
        try:
            prices = db.query(PriceHistory.close).filter(PriceHistory.ticker == ticker).order_by(PriceHistory.date).all()
            
            if not prices or len(prices) < 2:
                return {}
            
            closes = [p[0] for p in prices]
            df_prices = pd.DataFrame({'close': closes})
            
            # Calculate metrics
            returns = df_prices['close'].pct_change()
            
            stats = {
                'current_price': closes[-1],
                'avg_price_180d': sum(closes) / len(closes),
                'min_price_180d': min(closes),
                'max_price_180d': max(closes),
                'volatility': returns.std(),
                'return_180d': (closes[-1] - closes[0]) / closes[0] * 100,
                'moving_avg_20': df_prices['close'].rolling(window=20).mean().iloc[-1],
                'moving_avg_50': df_prices['close'].rolling(window=50).mean().iloc[-1],
            }
            
            return stats
        
        except Exception as e:
            print(f"Error calculating stats: {e}")
            return {}
        
        finally:
            db.close()

    @staticmethod
    def bulk_fetch_and_store(tickers):
        """Fetch and store price history for multiple tickers."""
        results = {}
        for ticker in tickers:
            df = PriceHistoryService.fetch_180_days(ticker, auto_map_nse=True)
            if not df.empty:
                PriceHistoryService.store_price_history(ticker, df)
                results[ticker] = len(df)
        return results
