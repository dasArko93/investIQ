"""
Admin Settings & Maintenance Page for InvestIQ
Manage database, clear data, and system maintenance
"""
import streamlit as st

from utils.page_utils import render_sidebar
from database.db import SessionLocal
from database.models import (
    Holding, PriceHistory, TrendSnapshot, PortfolioSnapshot,
    Watchlist, Alert, StockMaster, Metadata
)
from pathlib import Path


st.set_page_config(page_title="Admin Settings", page_icon="⚙️", layout="wide", initial_sidebar_state="expanded")
from utils.page_utils import require_auth
require_auth()
render_sidebar()

# Custom CSS
st.markdown("""
<style>
    .admin-section {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        border-left: 4px solid #ff4b4b;
    }
    .stat-box {
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        text-align: center;
    }
    .stat-number {
        font-size: 2em;
        font-weight: bold;
        color: #1f77b4;
    }
    .stat-label {
        color: #666;
        font-size: 0.9em;
        margin-top: 5px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("# ⚙️ Admin Settings & Maintenance")
st.markdown("Manage database, clear data, and system maintenance")
st.divider()

# ============================================================================
# 1. DATABASE STATUS
# ============================================================================
st.markdown("## 📊 Database Status")

def get_database_stats():
    """Get current database statistics."""
    db = SessionLocal()
    try:
        stats = {
            'holdings': db.query(Holding).count(),
            'price_history': db.query(PriceHistory).count(),
            'trend_snapshots': db.query(TrendSnapshot).count(),
            'portfolio_snapshots': db.query(PortfolioSnapshot).count(),
            'watchlist': db.query(Watchlist).count(),
            'alerts': db.query(Alert).count(),
            'stock_master': db.query(StockMaster).count(),
            'metadata': db.query(Metadata).count(),
        }
        return stats
    finally:
        db.close()

# Display database stats
stats = get_database_stats()
total_records = sum(stats.values())

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown('<div class="stat-box"><div class="stat-number">'+str(stats['holdings'])+'</div><div class="stat-label">Holdings</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="stat-box"><div class="stat-number">'+str(stats['price_history'])+'</div><div class="stat-label">Price Records</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown('<div class="stat-box"><div class="stat-number">'+str(stats['watchlist'])+'</div><div class="stat-label">Watchlist</div></div>', unsafe_allow_html=True)
with col4:
    st.markdown('<div class="stat-box"><div class="stat-number">'+str(total_records)+'</div><div class="stat-label">Total Records</div></div>', unsafe_allow_html=True)

st.markdown(f"**Database File:** `data/investiq.db`")

st.divider()

# ============================================================================
# 2. DATA CLEANUP SECTION
# ============================================================================
st.markdown("## 🧹 Data Cleanup Operations")

cleanup_tab1, cleanup_tab2, cleanup_tab3 = st.tabs(["Clear Holdings", "Clear Database", "Clear Files"])

# ---- TAB 1: CLEAR HOLDINGS ----
with cleanup_tab1:
    st.markdown("### Clear Holdings Data")
    st.warning("⚠️ This will delete all holdings records. This action **cannot be undone**.")
    
    if st.button("🗑️ Clear All Holdings", key="clear_holdings", use_container_width=True):
        confirmation = st.text_input("Type 'DELETE ALL HOLDINGS' to confirm:", key="confirm_holdings")
        if confirmation == "DELETE ALL HOLDINGS":
            db = SessionLocal()
            try:
                count = db.query(Holding).delete()
                db.commit()
                st.success(f"✅ Deleted {count} holdings records!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error: {e}")
            finally:
                db.close()
        elif confirmation:
            st.error("❌ Confirmation text doesn't match. Type exactly: DELETE ALL HOLDINGS")

# ---- TAB 2: CLEAR ALL DATABASE ----
with cleanup_tab2:
    st.markdown("### Clear All Database Records")
    st.error("🚨 DANGER ZONE - This will delete ALL data including price history, snapshots, alerts, etc.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Clear All Database Records", key="clear_all_db", use_container_width=True):
            confirmation = st.text_input("Type 'DELETE ALL DATABASE' to confirm:", key="confirm_all_db")
            if confirmation == "DELETE ALL DATABASE":
                db = SessionLocal()
                try:
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
                    
                    deleted_counts = []
                    for model, name in tables:
                        count = db.query(model).delete()
                        if count > 0:
                            deleted_counts.append((name, count))
                    
                    db.commit()
                    
                    st.success("✅ All database records cleared!")
                    for name, count in deleted_counts:
                        st.info(f"  • {name}: {count} records deleted")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {e}")
                finally:
                    db.close()
            elif confirmation:
                st.error("❌ Confirmation text doesn't match. Type exactly: DELETE ALL DATABASE")
    
    with col2:
        st.markdown("### What Gets Deleted?")
        st.markdown("""
        - 🏦 Holdings records
        - 📈 Price history (180-day prices)
        - 📊 Trend snapshots
        - 💼 Portfolio snapshots
        - 👀 Watchlist items
        - ⚠️ Alerts
        - 📋 Stock master data
        - ⚙️ Metadata
        """)

# ---- TAB 3: CLEAR FILES ----
with cleanup_tab3:
    st.markdown("### Clean Up Data Files")
    
    # Find data files
    project_root = Path(__file__).parent.parent
    data_extensions = ['.csv', '.xlsx', '.xls']
    data_keywords = ['holding', 'stock', 'portfolio', 'price', 'shares', 'position']
    
    found_files = []
    search_dirs = [
        project_root,
        project_root / 'data',
        project_root / 'uploads',
        project_root / 'files',
    ]
    
    for search_dir in search_dirs:
        if search_dir.exists():
            for file_path in search_dir.rglob('*'):
                if file_path.is_file() and file_path.suffix in data_extensions:
                    filename_lower = file_path.name.lower()
                    if any(keyword in filename_lower for keyword in data_keywords):
                        found_files.append(file_path)
    
    if found_files:
        st.warning(f"Found {len(found_files)} data file(s):")
        
        file_list = []
        for file_path in found_files:
            size_kb = file_path.stat().st_size / 1024
            st.markdown(f"- **{file_path.name}** ({size_kb:.2f} KB)")
            file_list.append(file_path)
        
        if st.button("🗑️ Delete All Data Files", key="delete_files", use_container_width=True):
            confirmation = st.text_input("Type 'DELETE FILES' to confirm:", key="confirm_files")
            if confirmation == "DELETE FILES":
                deleted = 0
                for file_path in file_list:
                    try:
                        file_path.unlink()
                        deleted += 1
                    except Exception as e:
                        st.error(f"Failed to delete {file_path.name}: {e}")
                
                st.success(f"✅ Deleted {deleted} file(s)!")
                st.rerun()
            elif confirmation:
                st.error("❌ Confirmation text doesn't match. Type exactly: DELETE FILES")
    else:
        st.success("✅ No data files found in project")

st.divider()

# ============================================================================
# 3. SYSTEM INFO
# ============================================================================
st.markdown("## ℹ️ System Information")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Database Configuration")
    st.code("""
    Database: SQLite
    Location: data/investiq.db
    Engine: SQLAlchemy ORM
    Models: 8 tables
    """, language="text")

with col2:
    st.markdown("### Recent Operations")
    st.info("""
    ✓ Holdings versioning enabled
    ✓ Price history ready (Yahoo Finance)
    ✓ Trend analysis available
    ✓ Snapshot tracking active
    """)

st.divider()

# ============================================================================
# 4. SNAPSHOTS & HISTORY
# ============================================================================
st.markdown("## 📅 Holdings Snapshots")

db = SessionLocal()
try:
    from sqlalchemy import distinct, func
    
    snapshots = db.query(
        distinct(Holding.snapshot_date).label('date'),
        func.count(Holding.id).label('count')
    ).group_by(Holding.snapshot_date).order_by(Holding.snapshot_date.desc()).all()
    
    if snapshots:
        st.markdown(f"Found {len(snapshots)} snapshot(s):")
        for snap_date, count in snapshots:
            st.markdown(f"📌 **{snap_date}** - {count} holdings")
    else:
        st.info("No snapshots yet. Upload holdings file to create first snapshot.")

finally:
    db.close()

st.divider()

# ============================================================================
# 5. UTILITIES
# ============================================================================
st.markdown("## 🛠️ Utilities")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Fetch Price History")
    if st.button("📥 Fetch 180-Day Prices", use_container_width=True):
        st.info("Run this command in terminal:\n```\npython services/price_history_service.py\n```")

with col2:
    st.markdown("### Analyze Trends")
    if st.button("📊 Run Trend Analysis", use_container_width=True):
        st.info("Run this command in terminal:\n```\npython demo_versioning.py\n```")

st.divider()

st.markdown("""
---
**Admin Tools v1.0** | InvestIQ Management Console

⚡ **Pro Tips:**
- Always backup your data before running cleanup operations
- Use command-line tools for batch operations
- Check database status before major changes
""")