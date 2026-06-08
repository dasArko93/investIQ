"""Demo script to test holdings versioning, price history, and trend analysis."""
from services.holdings_service import HoldingsService
from services.price_history_service import PriceHistoryService
from services.trend_analysis_service import TrendAnalysisService
import pandas as pd


def demo_snapshot_workflow():
    """Example workflow: snapshots, price history, trend analysis."""
    
    print("\n=== Holdings Snapshot Workflow ===\n")
    
    # 1. Check available snapshots
    print("1. Available holding snapshots:")
    snapshots = HoldingsService.get_snapshots()
    for i, snap_date in enumerate(snapshots):
        print(f"   {i+1}. {snap_date}")
    
    if len(snapshots) >= 2:
        # 2. Compare two snapshots
        print(f"\n2. Comparing snapshots: {snapshots[0]} vs {snapshots[1]}")
        comparison = TrendAnalysisService.compare_snapshots(snapshots[1], snapshots[0])
        
        if comparison['added']:
            print(f"   Added: {[s['security'] for s in comparison['added']]}")
        if comparison['removed']:
            print(f"   Removed: {[s['security'] for s in comparison['removed']]}")
        if comparison['increased']:
            print(f"   Increased: {[s['security'] for s in comparison['increased']]}")
        if comparison['decreased']:
            print(f"   Decreased: {[s['security'] for s in comparison['decreased']]}")
    
    # 3. Get current holdings
    print("\n3. Current holdings (latest snapshot):")
    df_holdings = HoldingsService.dataframe()
    print(df_holdings[['security', 'quantity', 'current_value', 'pnl']].to_string())
    
    # 4. Fetch and store 180-day price history
    print("\n4. Fetching 180-day price history for stocks...")
    if not df_holdings.empty:
        tickers = df_holdings['security'].unique()[:3]  # First 3 stocks
        results = PriceHistoryService.bulk_fetch_and_store(tickers)
        for ticker, count in results.items():
            print(f"   {ticker}: {count} days of data")
        
        # 5. Calculate statistics
        print("\n5. Statistical analysis:")
        for ticker in tickers:
            if ticker in results:
                stats = PriceHistoryService.calculate_stats(ticker)
                if stats:
                    print(f"\n   {ticker}:")
                    print(f"      Current Price: ₹{stats.get('current_price', 0):.2f}")
                    print(f"      180D Return: {stats.get('return_180d', 0):.2f}%")
                    print(f"      Volatility: {stats.get('volatility', 0):.4f}")
                    print(f"      180D Range: ₹{stats.get('min_price_180d', 0):.2f} - ₹{stats.get('max_price_180d', 0):.2f}")
    
    # 6. Portfolio trend
    print("\n6. Portfolio value trend:")
    trend = TrendAnalysisService.portfolio_trend_over_time()
    for t in trend[-5:]:  # Last 5 snapshots
        print(f"   {t['snapshot_date']}: ₹{t['total_value']:,.0f} (Holdings: {t['holding_count']})")
    
    print("\n=== Demo Complete ===\n")


if __name__ == "__main__":
    demo_snapshot_workflow()
