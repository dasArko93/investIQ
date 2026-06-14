import pandas as pd
import streamlit as st

from services.holdings_service import HoldingsService
from services.universe_service import UniverseService


def render_sidebar():
    with st.sidebar:
        # Brand Header: Logo + App Name
        logo_col1, logo_col2 = st.columns([1, 4])
        with logo_col1:
            try:
                st.image("assets/logo.png", width=40)
            except Exception:
                pass
        with logo_col2:
            st.markdown("<h3 style='margin: 0; padding-top: 4px; font-weight: 800; color: #f8fafc;'>InvestIQ</h3>", unsafe_allow_html=True)
        
        st.write("") # subtle spacing
        
        # Only render navigation links if authenticated
        if st.session_state.get("authenticated", False):
            # Home Link
            st.page_link("app.py", label="Home", icon="🏠")
            
            # Holdings Page Link placed under Home
            st.page_link("pages/1_Portfolio.py", label="Holdings", icon="💼")
            
            st.divider()
            
            st.caption("🔍 Research")
            st.page_link("pages/2_Stock_Universe.py", label="Stock Universe")
            st.page_link("pages/4_Stock_Analysis.py", label="Fundamental Analysis")
            st.caption("🤖 Advisor")
            st.page_link("pages/9_Recommendations.py", label="Recommendations")
            st.caption("⚡ Actions")
            st.page_link("pages/8_Rebalance.py", label="Rebalance")
            st.caption("📊 Reports")
            st.page_link("pages/17_Portfolio_Report.py", label="Portfolio Report")
            st.caption("🧹 Database Operations")
            st.page_link("pages/18_Clear_Data.py", label="Clear Database", icon="🗑️")
            
            st.divider()
            if st.button("🚪 Log Out", use_container_width=True):
                st.session_state.authenticated = False
                st.rerun()


def require_auth():
    # Check if authenticated
    if st.session_state.get("authenticated", False):
        return True

    # Render custom styled login page
    st.markdown(
        """
        <style>
        /* Hide sidebar and collapse control */
        [data-testid="stSidebar"] {
            display: none !important;
        }
        [data-testid="collapsedControl"] {
            display: none !important;
        }
        
        /* App Background */
        .stApp {
            background: radial-gradient(circle at 50% 30%, #0f172a 0%, #020617 100%) !important;
        }
        
        /* Centered login card styling */
        div[data-testid="column"]:nth-of-type(2) {
            background: rgba(30, 41, 59, 0.35) !important;
            backdrop-filter: blur(20px) !important;
            -webkit-backdrop-filter: blur(20px) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 24px !important;
            padding: 45px 35px !important;
            box-shadow: 0 25px 60px rgba(0, 0, 0, 0.6) !important;
            margin-top: 50px !important;
        }
        
        /* Styled input wrappers */
        div[data-testid="stTextInput"] input {
            background-color: rgba(15, 23, 42, 0.6) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            color: #f8fafc !important;
            border-radius: 12px !important;
            padding: 12px 16px !important;
            font-size: 1rem !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }
        
        div[data-testid="stTextInput"] input:focus {
            border-color: #6366f1 !important;
            box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.25) !important;
            background-color: rgba(15, 23, 42, 0.8) !important;
        }
        
        /* Primary button custom style */
        button[kind="primary"] {
            background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%) !important;
            border: none !important;
            color: #ffffff !important;
            border-radius: 12px !important;
            padding: 12px 24px !important;
            font-weight: 600 !important;
            font-size: 1rem !important;
            width: 100% !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3) !important;
            margin-top: 15px;
        }
        
        button[kind="primary"]:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 25px rgba(99, 102, 241, 0.45) !important;
        }
        
        button[kind="primary"]:active {
            transform: translateY(0) !important;
        }
        
        /* Labels formatting */
        label {
            color: #cbd5e1 !important;
            font-weight: 500 !important;
            font-size: 0.9rem !important;
            margin-bottom: 6px !important;
        }
        
        /* Center image inside the column */
        div[data-testid="column"] img {
            display: block !important;
            margin-left: auto !important;
            margin-right: auto !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    col_left, col_center, col_right = st.columns([1.2, 2, 1.2])
    with col_center:
        # Centered logo using HTML flexbox
        st.markdown(
            '<div style="display: flex; justify-content: center; align-items: center; margin-top: 15px; width: 100%;">'
            '<img src="/app/static/logo.png" width="80" style="border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.4);">'
            '</div>',
            unsafe_allow_html=True
        )
        
        st.markdown(
            '<h1 style="text-align: center; font-family: \'Outfit\', \'Inter\', sans-serif; font-weight: 800; font-size: 2.2rem; background: linear-gradient(135deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 5px; margin-top: 10px;">InvestIQ</h1>', 
            unsafe_allow_html=True
        )
        st.markdown(
            '<p style="text-align: center; color: #94a3b8; font-size: 0.95rem; margin-bottom: 30px;">Wealth is created by owning quality assets, not chasing noise.</p>', 
            unsafe_allow_html=True
        )

        try:
            allowed_email = st.secrets.get("ALLOWED_EMAIL", "virus@investIQ")
            allowed_password = st.secrets.get("ALLOWED_PASSWORD", "Mylife123!@#")
        except Exception:
            allowed_email = "virus@investIQ"
            allowed_password = "Mylife123!@#"
        
        email_input = st.text_input("User ID", placeholder="Enter User ID", key="login_email_input")
        password_input = st.text_input("Password", type="password", placeholder="••••••••••••", key="login_password_input")
        
        st.write("")
        if st.button("Log In", type="primary", use_container_width=True):
            if email_input == allowed_email and password_input == allowed_password:
                st.session_state.authenticated = True
                st.success("Access Granted! Loading portal...")
                st.rerun()
            else:
                st.error("Invalid User ID or Password.")
                
    st.stop()




def load_holdings():
    return HoldingsService.dataframe()


def load_universe():
    return UniverseService.dataframe()


def require_data(df, message):
    if df.empty:
        st.info(message)
        return False
    return True


def merged_holdings():
    holdings = load_holdings()
    universe = load_universe()
    if holdings.empty or universe.empty:
        return pd.DataFrame()
    return holdings.merge(universe, left_on="Security", right_on="Ticker", how="left")
