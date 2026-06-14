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

    # Otherwise, render login form on the page
    st.markdown("<h2 style='text-align: center; margin-top: 50px; font-weight: 800; color: #f8fafc;'>🔒 Secure Portal Login</h2>", unsafe_allow_html=True)
    st.write("")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            allowed_email = st.secrets.get("ALLOWED_EMAIL", "virus@investIQ")
            allowed_password = st.secrets.get("ALLOWED_PASSWORD", "Mylife123!@#")
        except Exception:
            allowed_email = "virus@investIQ"
            allowed_password = "Mylife123!@#"
        
        email_input = st.text_input("User ID / Email", key="login_email_input")
        password_input = st.text_input("Password", type="password", key="login_password_input")
        
        if st.button("Log In", type="primary", use_container_width=True):
            if email_input == allowed_email and password_input == allowed_password:
                st.session_state.authenticated = True
                st.success("Access Granted! Loading portal...")
                st.rerun()
            else:
                st.error("Invalid User ID or password.")

                
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
