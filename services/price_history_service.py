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
            df = df.rename(columns={"index": "date", "datetime": "date"})
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
        """
        Fetch 365 days of historical price data.
        Maintains a database cache. If first time (or cache has < 365 records), 
        fetches 550 calendar days of data to guarantee at least 365 trading days.
        On subsequent calls, fetches incremental data from the latest stored date to today, 
        appends it to the database table, and returns the last 365 data points.
        """
        db = SessionLocal()
        try:
            # Check existing records in DB
            records = db.query(PriceHistory).filter(PriceHistory.ticker == ticker).order_by(PriceHistory.date.asc()).all()
            
            if not records or len(records) < 365:
                # First time or insufficient cache: fetch 550 calendar days from Yahoo Finance
                df = PriceHistoryService.fetch_days(ticker, days=550, auto_map_nse=auto_map_nse)
                if not df.empty:
                    PriceHistoryService.store_price_history(ticker, df)
                    # Re-query to get stored records
                    records = db.query(PriceHistory).filter(PriceHistory.ticker == ticker).order_by(PriceHistory.date.asc()).all()
                else:
                    db.close()
                    return pd.DataFrame()
            
            # check latest date in DB
            max_db_date = max([r.date for r in records])
            today = datetime.utcnow()
            
            # If the latest date is older than today by at least 1 day, fetch incremental data
            if (today - max_db_date).days >= 1:
                start_date = max_db_date + timedelta(days=1)
                yahoo_ticker = f"{ticker}.NS" if auto_map_nse else ticker
                try:
                    df_new = yf.download(yahoo_ticker, start=start_date, end=today, progress=False)
                    if not df_new.empty:
                        df_new.reset_index(inplace=True)
                        if isinstance(df_new.columns, pd.MultiIndex):
                            df_new.columns = [column[0].lower().replace(" ", "_") for column in df_new.columns]
                        else:
                            df_new.columns = [str(column).lower().replace(" ", "_") for column in df_new.columns]
                        df_new = df_new.rename(columns={"index": "date", "datetime": "date"})
                        df_new['ticker'] = ticker
                        
                        # Add new records to DB
                        new_records = []
                        for _, row in df_new.iterrows():
                            # Double check to prevent duplicates
                            exists = db.query(PriceHistory).filter(
                                PriceHistory.ticker == ticker,
                                PriceHistory.date == row['date']
                            ).first()
                            if not exists:
                                new_records.append(
                                    PriceHistory(
                                        ticker=ticker,
                                        date=row['date'],
                                        open=row['open'],
                                        high=row['high'],
                                        low=row['low'],
                                        close=row['close'],
                                        volume=row['volume']
                                    )
                                )
                        if new_records:
                            db.bulk_save_objects(new_records)
                            db.commit()
                except Exception as ex:
                    print(f"Error fetching incremental data for {ticker}: {ex}")
            
            # Query all records from DB and return the last 365 data points
            updated_records = db.query(PriceHistory).filter(PriceHistory.ticker == ticker).order_by(PriceHistory.date.asc()).all()
            rows = [
                {
                    "ticker": r.ticker,
                    "date": r.date,
                    "open": r.open,
                    "high": r.high,
                    "low": r.low,
                    "close": r.close,
                    "volume": r.volume
                }
                for r in updated_records
            ]
            df_all = pd.DataFrame(rows)
            db.close()
            return df_all.tail(365)
        
        finally:
            db.close()

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
