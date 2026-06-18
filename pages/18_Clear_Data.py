# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from datetime import datetime
from pathlib import Path
from database.db import SessionLocal, DATA_DIR, DATABASE_URL, engine
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
from utils.page_utils import render_sidebar

# Set up Streamlit Page
st.set_page_config(page_title="InvestIQ - Database Admin", page_icon="⚙️", layout="wide", initial_sidebar_state="expanded")
from utils.page_utils import require_auth
require_auth()
render_sidebar()

st.title("⚙️ Database Admin & Operations")
st.write("Monitor database records, download backups, configure cloud persistence, and perform maintenance or reset operations.")
st.divider()

# Helper function to get current counts of database records
def get_db_stats():
    db = SessionLocal()
    try:
        from sqlalchemy import func
        latest_date = db.query(func.max(Holding.snapshot_date)).scalar()
        unique_stocks = 0
        if latest_date:
            unique_stocks = db.query(Holding).filter(Holding.snapshot_date == latest_date).count()

        stats = {
            "Holdings (Total Records)": db.query(Holding).count(),
            "Unique Stocks (Current)": unique_stocks,
            "Trend Snapshots": db.query(TrendSnapshot).count(),
            "Portfolio Snapshots": db.query(PortfolioSnapshot).count(),
            "Stock Universe Master": db.query(StockMaster).count(),
            "Price History Cache": db.query(PriceHistory).count(),
            "Watchlist": db.query(Watchlist).count(),
            "Alerts": db.query(Alert).count(),
            "System Metadata": db.query(Metadata).count()
        }
        return stats
    except Exception as e:
        st.error(f"Error fetching database statistics: {e}")
        return {}
    finally:
        db.close()

# Define tabs
tab_status, tab_backup, tab_cloud, tab_maintenance = st.tabs([
    "📊 Database Status", 
    "💾 Backup & Restore", 
    "☁️ Cloud Persistence", 
    "🧹 Maintenance & Reset"
])

# -------------------------------------------------------------
# TAB 1: Database Status
# -------------------------------------------------------------
with tab_status:
    st.subheader("Current Database Summary")
    stats = get_db_stats()
    if stats:
        cols = st.columns(4)
        cols[0].metric("Unique Stocks (Current Holdings)", f"{stats['Unique Stocks (Current)']:,}")
        cols[1].metric("Stock Universe Master", f"{stats['Stock Universe Master']:,}")
        cols[2].metric("Price History Cache", f"{stats['Price History Cache']:,}")
        cols[3].metric("Watchlists & Alerts", f"{stats['Watchlist'] + stats['Alerts']:,}")
        
        # Detail expander
        with st.expander("🔍 Show detailed database table counts"):
            st.json(stats)
    else:
        st.warning("Could not retrieve database status. Verify database connectivity.")
        
    st.divider()
    
    st.subheader("📅 Holdings Snapshots Summary")
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
                st.markdown(f"📌 **{snap_date}** - {count} holdings records")
        else:
            st.info("No snapshots found. Upload a holdings file in the Portfolio page to create your first snapshot.")
    finally:
        db.close()

# -------------------------------------------------------------
# TAB 2: Backup & Restore
# -------------------------------------------------------------
with tab_backup:
    st.subheader("Local Database Backup & Restore")
    
    is_sqlite = DATABASE_URL is None or DATABASE_URL.startswith("sqlite")
    
    if not is_sqlite:
        st.info("💡 **Active Database Type:** PostgreSQL Cloud Database")
        st.success("You are connected to a remote database. Data is persistently stored in the cloud and will not reset on inactivity.")
    else:
        st.info(
            "💡 **Active Database Type:** Local File-Based SQLite\n\n"
            "InvestIQ is currently using a local temporary SQLite file (`data/investiq.db`). "
            "If this application is deployed on Streamlit Cloud, the file is ephemeral and resets after inactivity. "
            "Download a backup of your database below to restore it the next time you access the app."
        )
        
        col_back, col_rest = st.columns(2)
        
        with col_back:
            st.markdown("### 📤 Download Backup")
            st.write("Save your current database state (holdings, universe, and alerts) to your computer.")
            
            db_path = DATA_DIR / "investiq.db"
            if db_path.exists():
                try:
                    with open(db_path, "rb") as f:
                        db_bytes = f.read()
                    st.download_button(
                        label="📥 Download Database Backup File (.db)",
                        data=db_bytes,
                        file_name=f"investiq_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
                        mime="application/octet-stream",
                        use_container_width=True
                    )
                    st.caption(f"File path: `data/investiq.db` | Size: {len(db_bytes)/1024:.2f} KB")
                except Exception as e:
                    st.error(f"Error reading SQLite file: {e}")
            else:
                st.warning("Database file not found on disk yet. It will be initialized on first write.")
                
        with col_rest:
            st.markdown("### 📥 Restore Backup")
            st.write("Upload a previously downloaded SQLite `.db` backup file to restore all database tables.")
            
            uploaded_file = st.file_uploader("Upload .db Backup File", type=["db"])
            if uploaded_file is not None:
                st.warning("⚠️ **Warning:** Restoring a backup will completely overwrite your current database. This cannot be undone.")
                if st.button("🔥 Confirm & Overwrite Database", type="primary", use_container_width=True):
                    try:
                        # Close any active connections before replacing the SQLite file
                        engine.dispose()
                        
                        db_path = DATA_DIR / "investiq.db"
                        with open(db_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                            
                        st.success("✅ Database restored successfully! Reloading portal...")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to restore SQLite file: {e}")

# -------------------------------------------------------------
# TAB 3: Cloud Persistence Guide
# -------------------------------------------------------------
with tab_cloud:
    st.subheader("☁️ Permanent Cloud Database Persistence")
    st.write(
        "To avoid manual backup/restore steps, you can connect InvestIQ to a permanent cloud database. "
        "A free PostgreSQL instance (from Neon, Supabase, or Aiven) is ideal for this application."
    )
    
    st.markdown(
        """
        ### Step-by-Step Setup Guide
        
        1. **Deploy a Free Postgres Database:**
           - Register for a free account at [Neon.tech](https://neon.tech/) or [Supabase.com](https://supabase.com/).
           - Create a new database project and copy the **Connection String** (PostgreSQL URI).
             *Format example:* `postgresql://user:password@host/dbname?sslmode=require`
        
        2. **Configure Streamlit secrets (for Streamlit Community Cloud):**
           - Open your Streamlit App dashboard.
           - Go to **App Settings** -> **Secrets**.
           - Paste your database URL as `DATABASE_URL`:
             ```toml
             DATABASE_URL = "postgresql://user:password@host/dbname?sslmode=require"
             ```
           - Click **Save**. Streamlit will automatically restart the app with the new persistence settings.
        
        3. **Configure Locally (for Development):**
           - Create a file named `.env` in the root folder of the project.
           - Add:
             ```text
             DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
             ```
        
        ---
        """
    )
    
    st.subheader("Current Configuration Status")
    if DATABASE_URL is None or DATABASE_URL.startswith("sqlite"):
        st.warning("⚠️ **Vulnerable:** Currently running on local temporary SQLite. Data will reset on container inactivity.")
    else:
        st.success("✅ **Secure:** Connected to a remote persistent database.")
        # Print sanitised database host details
        host_info = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL
        st.code(f"Host Details: {host_info}", language="text")

# -------------------------------------------------------------
# TAB 4: Maintenance & Reset
# -------------------------------------------------------------
with tab_maintenance:
    col_left, col_right = st.columns(2)
    
    # ---- Left Column: Selective Purge ----
    with col_left:
        st.subheader("⚡ Selective Purge")
        st.write("Choose specific data categories to delete. Other records will remain intact.")
        
        clear_holdings = st.checkbox("💼 Portfolio Holdings & Snapshots", value=False, help="Delete all transaction records, holdings history, and trend snapshots.")
        clear_universe = st.checkbox("📈 Stock Screener Universe Master", value=False, help="Delete all stock master files uploaded to the screener universe.")
        clear_price_cache = st.checkbox("❄️ Price History Cache", value=False, help="Delete historical price series data cached for charts and quant models.")
        clear_watchlist = st.checkbox("⭐ Watchlist & Alerts", value=False, help="Delete active watchlist items and price threshold notifications.")
        clear_metadata = st.checkbox("ℹ️ System Metadata", value=False, help="Delete upload timestamps and general app parameters.")
        
        st.write("")
        
        confirm_text_selective = st.text_input(
            "To authorize selective deletion, type **PURGE** below:",
            placeholder="Type here...",
            key="confirm_selective"
        )
        
        any_checked = clear_holdings or clear_universe or clear_price_cache or clear_watchlist or clear_metadata
        btn_disabled_selective = (confirm_text_selective != "PURGE") or not any_checked
        
        if st.button("🗑️ Purge Selected Categories", type="primary", use_container_width=True, disabled=btn_disabled_selective):
            db = SessionLocal()
            deleted_log = []
            try:
                if clear_holdings:
                    h_cnt = db.query(Holding).delete()
                    ts_cnt = db.query(TrendSnapshot).delete()
                    ps_cnt = db.query(PortfolioSnapshot).delete()
                    deleted_log.append(f"Holdings ({h_cnt}), Trend Snapshots ({ts_cnt}), Portfolio Snapshots ({ps_cnt})")
                    
                if clear_universe:
                    u_cnt = db.query(StockMaster).delete()
                    deleted_log.append(f"Stock Universe Master ({u_cnt})")
                    
                if clear_price_cache:
                    p_cnt = db.query(PriceHistory).delete()
                    deleted_log.append(f"Price History Cache ({p_cnt})")
                    
                if clear_watchlist:
                    w_cnt = db.query(Watchlist).delete()
                    a_cnt = db.query(Alert).delete()
                    deleted_log.append(f"Watchlist ({w_cnt}), Alerts ({a_cnt})")
                    
                if clear_metadata:
                    m_cnt = db.query(Metadata).delete()
                    deleted_log.append(f"System Metadata ({m_cnt})")
                    
                db.commit()
                st.success("✅ Selected categories purged successfully:\n" + "\n".join([f"- {item}" for item in deleted_log]))
                st.rerun()
            except Exception as e:
                db.rollback()
                st.error(f"Error executing selective purge: {e}")
            finally:
                db.close()
                
    # ---- Right Column: Full Database Wipe & File Cleanup ----
    with col_right:
        st.markdown(
            """
            <div style="border: 2px solid #ef4444; border-radius: 8px; padding: 20px; background-color: rgba(239, 68, 68, 0.05);">
                <h3 style="color: #ef4444; margin-top: 0;">⚠️ Danger Zone: Full Wipe</h3>
                <p style="color: #cbd5e1; font-size: 0.9rem;">
                    Performing a full database purge will completely wipe the database clean. All portfolios, watchlists,
                    recommendations, cached stock histories, and system settings will be irreversibly deleted.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        st.write("")
        
        confirm_text_full = st.text_input(
            "To authorize complete database wipe, type **PURGE ALL** below:",
            placeholder="Type here...",
            key="confirm_full"
        )
        
        btn_disabled_full = (confirm_text_full != "PURGE ALL")
        
        if st.button("🔥 Full Database Reset (Delete All)", type="primary", use_container_width=True, disabled=btn_disabled_full):
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
                
                summary_msgs = []
                for model, name in tables:
                    count = db.query(model).delete()
                    summary_msgs.append(f"- Deleted {count} {name} records")
                    
                db.commit()
                st.success("🎉 Full database reset completed successfully:\n" + "\n".join(summary_msgs))
                st.rerun()
            except Exception as e:
                db.rollback()
                st.error(f"Error resetting database: {e}")
            finally:
                db.close()
                
        st.divider()
        st.subheader("🧹 Clean Up Temporary Files")
        
        project_root = Path(__file__).parent.parent
        data_extensions = ['.csv', '.xlsx', '.xls']
        data_keywords = ['holding', 'stock', 'portfolio', 'price', 'shares', 'position']
        
        found_files = []
        search_dirs = [project_root, project_root / 'data', project_root / 'uploads', project_root / 'files']
        
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
                
            st.write("")
            confirm_files_wipe = st.text_input(
                "To authorize deletion of temporary files, type **DELETE FILES** below:",
                placeholder="Type here...",
                key="confirm_files"
            )
            
            if st.button("🗑️ Delete All Data Files", key="delete_files", use_container_width=True, disabled=(confirm_files_wipe != "DELETE FILES")):
                deleted = 0
                for file_path in file_list:
                    try:
                        file_path.unlink()
                        deleted += 1
                    except Exception as e:
                        st.error(f"Failed to delete {file_path.name}: {e}")
                st.success(f"✅ Deleted {deleted} file(s)!")
                st.rerun()
        else:
            st.success("✅ No temporary files found in project directories.")