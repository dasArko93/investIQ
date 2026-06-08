"""
Utility to completely clear all data from the database.
This will delete all holdings, price history, trend snapshots, and other records.
"""
from database.db import SessionLocal
from database.models import (
    Holding, 
    PriceHistory, 
    TrendSnapshot,
    PortfolioSnapshot,
    Watchlist,
    Alert,
    StockMaster,
    Metadata
)


def clear_all_data():
    """Clear all data from all tables."""
    db = SessionLocal()
    try:
        print("🧹 Clearing all data from database...\n")
        
        # Delete from all tables
        tables = [
            (Holding, "Holdings"),
            (PriceHistory, "Price History"),
            (TrendSnapshot, "Trend Snapshots"),
            (PortfolioSnapshot, "Portfolio Snapshots"),
            (Watchlist, "Watchlist"),
            (Alert, "Alerts"),
            (StockMaster, "Stock Master"),
            (Metadata, "Metadata"),
        ]
        
        for model, name in tables:
            count = db.query(model).delete()
            print(f"   ✓ Deleted {count} {name} records")
        
        db.commit()
        print("\n✅ All data cleared successfully!")
        print("   Database is now empty. Ready for fresh data upload.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error clearing data: {e}")
    finally:
        db.close()


def get_data_summary():
    """Show current data in database before clearing."""
    db = SessionLocal()
    try:
        tables = [
            (Holding, "Holdings"),
            (PriceHistory, "Price History"),
            (TrendSnapshot, "Trend Snapshots"),
            (PortfolioSnapshot, "Portfolio Snapshots"),
            (Watchlist, "Watchlist"),
            (Alert, "Alerts"),
        ]
        
        print("📊 Current Database State:\n")
        total = 0
        for model, name in tables:
            count = db.query(model).count()
            total += count
            print(f"   {name}: {count} records")
        
        print(f"\n   Total: {total} records\n")
        return total > 0
    
    finally:
        db.close()


if __name__ == "__main__":
    print("\n" + "="*50)
    print("  InvestIQ Database Cleaner")
    print("="*50 + "\n")
    
    has_data = get_data_summary()
    
    if has_data:
        response = input("⚠️  Are you sure you want to DELETE ALL DATA? (type 'yes' to confirm): ").strip().lower()
        if response == 'yes':
            clear_all_data()
        else:
            print("❌ Cancelled. No data was deleted.")
    else:
        print("✅ Database is already empty!")
    
    print("\n" + "="*50 + "\n")
