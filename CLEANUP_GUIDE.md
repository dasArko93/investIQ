# Data Cleanup Utilities

Your portfolio was showing inflated data because the dashboard was displaying **demo data** when no real holdings were present. This has been fixed.

## Current Status

✅ **Database**: Completely empty (Rs 0 portfolio)
✅ **Dashboard**: Shows "Rs 0" instead of demo data  
✅ **Files**: No stray data files found

## Cleanup Utilities

### 1. **Clear All Database Records** (`clear_all_data.py`)
Removes ALL data from database including:
- Holdings (all snapshots)
- Price history
- Trend snapshots
- Portfolio snapshots
- Watchlist
- Alerts

**Usage:**
```bash
python clear_all_data.py
```

**Output:**
- Shows current record count
- Asks for confirmation before deleting
- Reports how many records were deleted

### 2. **Clean Up Data Files** (`cleanup_files.py`)
Finds and removes all CSV/Excel files related to holdings/stocks:
- Any file named `*holding*`, `*stock*`, `*portfolio*`, etc.
- From project root, `data/`, `uploads/`, `files/` directories

**Usage:**
```bash
python cleanup_files.py
```

**Output:**
- Lists all data files found with sizes
- Lists database files
- Asks for confirmation before deleting

## Why the Portfolio Showed Rs 138,691

The `dashboard_ui.py` had a `demo_portfolio()` function that auto-filled demo data when the portfolio was empty:
```
HDFC Bank: Rs 127,000
Infosys: Rs 113,000
ITC: Rs 102,000
Tata Motors: Rs 93,000
Reliance: Rs 78,000
```

This **demo data is now disabled** - empty portfolio shows Rs 0.

## Fresh Start Workflow

1. ✅ Database is clean
2. ✅ Demo data is disabled
3. 📤 **Next**: Upload your fresh holdings file via **Holdings** page
4. 📊 Dashboard will show real data from your upload

## Notes

- The versioning system is ready (each upload gets a snapshot_date)
- Price history is ready (use Yahoo Finance integration)
- Trend analysis is ready (compare snapshots over time)
- When you upload holdings next time, they will **append** (not replace) - same-day uploads go into one snapshot

---

**Ready to upload fresh holdings data!** 🚀
