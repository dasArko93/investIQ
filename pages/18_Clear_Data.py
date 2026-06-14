# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
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
from utils.page_utils import render_sidebar

# Set up Streamlit Page
st.set_page_config(page_title="InvestIQ - Clear Data", layout="wide", initial_sidebar_state="expanded")
from utils.page_utils import require_auth
require_auth()
render_sidebar()

st.title("🧹 Database Operations & Maintenance")
st.write("Monitor database records and perform cleanup operations. You can selectively delete specific categories or perform a full system reset.")

# Helper function to get current counts of database records
def get_db_stats():
    db = SessionLocal()
    try:
        stats = {
            "Holdings": db.query(Holding).count(),
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

# Load stats
stats = get_db_stats()

# -------------------------------------------------------------
# 1. Database Summary Board
# -------------------------------------------------------------
st.subheader("📊 Current Database Summary")
if stats:
    cols = st.columns(4)
    cols[0].metric("Holdings & Snapshots", f"{stats['Holdings'] + stats['Trend Snapshots'] + stats['Portfolio Snapshots']:,}")
    cols[1].metric("Stock Universe Master", f"{stats['Stock Universe Master']:,}")
    cols[2].metric("Price History Cache", f"{stats['Price History Cache']:,}")
    cols[3].metric("Watchlists & Alerts", f"{stats['Watchlist'] + stats['Alerts']:,}")
    
    # Detail expander
    with st.expander("🔍 Show detailed database table counts"):
        st.json(stats)
else:
    st.warning("Could not retrieve database status. Verify database connectivity.")

st.divider()

# Setup Columns for Selective and Full Purge operations
col_left, col_right = st.columns(2)

# -------------------------------------------------------------
# 2. Selective Purge Operation
# -------------------------------------------------------------
with col_left:
    st.subheader("⚡ Selective Purge")
    st.write("Choose specific data categories to delete. Other records will remain intact.")
    
    # Selection checkboxes
    clear_holdings = st.checkbox("💼 Portfolio Holdings & Snapshots", value=False, help="Delete all transaction records, holdings history, and trend snapshots.")
    clear_universe = st.checkbox("📈 Stock Screener Universe Master", value=False, help="Delete all stock master files uploaded to the screener universe.")
    clear_price_cache = st.checkbox("❄️ Price History Cache", value=False, help="Delete historical price series data cached for charts and quant models.")
    clear_watchlist = st.checkbox("⭐ Watchlist & Alerts", value=False, help="Delete active watchlist items and price threshold notifications.")
    clear_metadata = st.checkbox("ℹ️ System Metadata", value=False, help="Delete upload timestamps and general app parameters.")
    
    st.write("")
    
    # Safety Check
    confirm_text_selective = st.text_input(
        "To authorize selective deletion, type **PURGE** below:",
        placeholder="Type here...",
        key="confirm_selective"
    )
    
    # Disable button unless criteria are met
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

# -------------------------------------------------------------
# 3. Full Database Purge Operation
# -------------------------------------------------------------
with col_right:
    # Danger Zone Styling
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
    
    # Safety Check
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