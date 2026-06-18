import pandas as pd
import streamlit as st

from services.holdings_service import HoldingsService
from services.universe_service import UniverseService


def inject_global_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

        /* Pastel Holographic Background */
        html, body, [data-testid="stAppViewContainer"], .stApp {
            background: linear-gradient(135deg, #d3e5ff 0%, #ffdced 35%, #e1d8ff 70%, #d5f7ec 100%) !important;
            background-attachment: fixed !important;
            color: #000000 !important;
            font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important;
            line-height: 1.55 !important;
            letter-spacing: -0.015em !important;
        }

        /* Top header bar transparent background */
        [data-testid="stHeader"] {
            background: transparent !important;
        }

        /* Sidebar Container Glassmorphism */
        [data-testid="stSidebar"] {
            background: rgba(255, 255, 255, 0.4) !important;
            backdrop-filter: blur(25px) !important;
            -webkit-backdrop-filter: blur(25px) !important;
            border-right: 1px solid rgba(255, 255, 255, 0.5) !important;
        }

        /* Hide collapse/expand sidebar controls */
        [data-testid="stSidebarCollapseButton"],
        [data-testid="collapsedControl"] {
            display: none !important;
        }

        /* Sidebar Text Colors */
        [data-testid="stSidebar"] * {
            color: #000000 !important;
            font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important;
        }

        [data-testid="stSidebar"] a {
            color: #000000 !important;
        }

        /* Sidebar Page Link Hover States */
        [data-testid="stSidebar"] div[data-testid="stPageLink-Container"] {
            background-color: transparent !important;
            border-radius: 8px !important;
            transition: all 0.2s ease !important;
        }
        
        [data-testid="stSidebar"] div[data-testid="stPageLink-Container"]:hover {
            background-color: rgba(255, 255, 255, 0.45) !important;
        }

        /* Headings styling */
        h1, h2, h3, h4, h5, h6 {
            color: #000000 !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-weight: 700 !important;
            letter-spacing: -0.025em !important;
        }

        /* General text elements */
        p, li, label, span, small, .stText, [data-testid="stMarkdownContainer"] p {
            color: #000000 !important;
            line-height: 1.55 !important;
        }

        /* Primary and secondary button styling */
        button[kind="primary"], div.stButton button, button[data-testid="baseButton-primary"] {
            background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%) !important;
            border: none !important;
            color: #ffffff !important;
            border-radius: 12px !important;
            padding: 10px 20px !important;
            font-weight: 600 !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.25) !important;
        }

        button[kind="primary"]:hover, div.stButton button:hover, button[data-testid="baseButton-primary"]:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 20px rgba(99, 102, 241, 0.35) !important;
            background: linear-gradient(135deg, #4f46e5 0%, #9333ea 100%) !important;
            color: #ffffff !important;
        }

        button[kind="secondary"], button[data-testid="baseButton-secondary"] {
            background: rgba(255, 255, 255, 0.5) !important;
            border: 1px solid rgba(255, 255, 255, 0.6) !important;
            color: #000000 !important;
            border-radius: 12px !important;
            font-weight: 500 !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            backdrop-filter: blur(10px) !important;
            -webkit-backdrop-filter: blur(10px) !important;
            transition: all 0.3s ease !important;
        }

        button[kind="secondary"]:hover, button[data-testid="baseButton-secondary"]:hover {
            background: rgba(255, 255, 255, 0.7) !important;
            border-color: rgba(255, 255, 255, 0.8) !important;
            color: #000000 !important;
        }

        /* Form Controls / Text inputs / Number inputs */
        div[data-testid="stTextInput"] input, 
        div[data-testid="stNumberInput"] input, 
        div[data-testid="stSelectbox"] select, 
        div[data-baseweb="input"],
        div[data-baseweb="select"],
        div[data-testid="stMultiSelect"] div[role="combobox"],
        textarea {
            background-color: rgba(255, 255, 255, 0.7) !important;
            border: 1px solid rgba(0, 0, 0, 0.15) !important;
            color: #000000 !important;
            border-radius: 12px !important;
            backdrop-filter: blur(10px) !important;
            -webkit-backdrop-filter: blur(10px) !important;
            box-shadow: 0 4px 12px rgba(31, 38, 135, 0.03) !important;
            font-family: 'Inter', sans-serif !important;
        }

        /* Ensure placeholder text inside inputs is dark gray and highly readable */
        input::placeholder, textarea::placeholder {
            color: #4b5563 !important;
            opacity: 0.85 !important;
        }

        div[data-testid="stTextInput"] input:focus, 
        div[data-testid="stNumberInput"] input:focus,
        div[data-baseweb="input"]:focus-within {
            border-color: #6366f1 !important;
            box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
            background-color: rgba(255, 255, 255, 0.85) !important;
        }

        /* Sliders */
        div[data-testid="stSlider"] [data-testid="stSliderTrack"] {
            background: rgba(255, 255, 255, 0.6) !important;
        }
        div[data-testid="stSlider"] [data-testid="stSliderThumb"] {
            background-color: #6366f1 !important;
            border: 2px solid #ffffff !important;
        }

        /* Glassmorphic Metrics / Cards */
        div[data-testid="stMetric"], .stMetric {
            background: rgba(255, 255, 255, 0.45) !important;
            backdrop-filter: blur(16px) !important;
            -webkit-backdrop-filter: blur(16px) !important;
            border: 1px solid rgba(255, 255, 255, 0.5) !important;
            border-radius: 16px !important;
            padding: 16px 18px !important;
            box-shadow: 0 10px 30px rgba(31, 38, 135, 0.04) !important;
        }

        div[data-testid="stMetric"] label {
            color: #000000 !important;
            font-weight: 600 !important;
        }

        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: #000000 !important;
            font-weight: 700 !important;
        }

        /* Dataframe background transparency */
        div[data-testid="stDataFrame"] {
            background: rgba(255, 255, 255, 0.4) !important;
            backdrop-filter: blur(10px) !important;
            -webkit-backdrop-filter: blur(10px) !important;
            border: 1px solid rgba(255, 255, 255, 0.5) !important;
            border-radius: 12px !important;
            padding: 10px !important;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.03) !important;
        }

        /* Expanders */
        div[data-testid="stExpander"] {
            background: rgba(255, 255, 255, 0.4) !important;
            backdrop-filter: blur(10px) !important;
            border: 1px solid rgba(255, 255, 255, 0.5) !important;
            border-radius: 12px !important;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.03) !important;
        }

        /* Tabs */
        button[data-baseweb="tab"] {
            color: #000000 !important;
            font-family: 'Outfit', sans-serif !important;
            font-weight: 500 !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #6366f1 !important;
            border-bottom-color: #6366f1 !important;
        }

        /* Alerts and success boxes */
        div[data-testid="stAlert"] {
            background: rgba(255, 255, 255, 0.45) !important;
            backdrop-filter: blur(10px) !important;
            border: 1px solid rgba(255, 255, 255, 0.5) !important;
            border-radius: 12px !important;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.03) !important;
        }
        div[data-testid="stAlert"] * {
            color: #000000 !important;
        }

        /* Code block wrapper */
        div[data-testid="stCodeBlock"] {
            border-radius: 12px !important;
            overflow: hidden !important;
        }

        /* Dropdown popover containers */
        div[data-baseweb="popover"], 
        div[data-baseweb="popover"] > div,
        div[data-baseweb="menu"], 
        [role="listbox"], 
        [role="listbox"] ul {
            background-color: #ffffff !important;
            border: 1px solid rgba(0, 0, 0, 0.15) !important;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15) !important;
            border-radius: 12px !important;
        }

        /* Reset lists inside markdown blocks to prevent oval styling */
        [data-testid="stMarkdownContainer"] ul, 
        [data-testid="stMarkdownContainer"] ol, 
        [data-testid="stMarkdownContainer"] li {
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            border-radius: 0 !important;
        }

        /* Option list items */
        div[data-baseweb="popover"] li, 
        div[data-baseweb="menu"] li, 
        [role="listbox"] li, 
        [role="option"],
        div[data-baseweb="popover"] [role="option"] {
            color: #000000 !important;
            background-color: #ffffff !important;
            transition: background-color 0.2s ease !important;
        }

        /* Text inside option list items */
        div[data-baseweb="popover"] li *, 
        div[data-baseweb="menu"] li *, 
        [role="listbox"] li *, 
        [role="option"] *,
        [role="option"] div,
        [role="option"] span {
            color: #000000 !important;
        }

        /* Highlight hovered item */
        div[data-baseweb="popover"] li:hover, 
        div[data-baseweb="menu"] li:hover, 
        [role="listbox"] li:hover, 
        [role="option"]:hover,
        [role="option"]:hover *,
        div[data-baseweb="popover"] li[aria-selected="true"], 
        [role="listbox"] li[aria-selected="true"],
        [role="option"][aria-selected="true"] {
            background-color: #f1f5f9 !important;
            color: #000000 !important;
        }

        div[data-baseweb="popover"] li:hover *, 
        div[data-baseweb="menu"] li:hover *, 
        [role="listbox"] li:hover *, 
        [role="option"]:hover * {
            color: #000000 !important;
        }

        /* Multiselect selected option chips */
        div[data-baseweb="tag"] {
            background-color: rgba(99, 102, 241, 0.15) !important;
            border: 1px solid rgba(99, 102, 241, 0.3) !important;
            border-radius: 6px !important;
        }
        div[data-baseweb="tag"] span, div[data-baseweb="tag"] * {
            color: #4f46e5 !important;
        }

        /* File Uploader styling to be light pastel with readable black text */
        div[data-testid="stFileUploader"], 
        div[data-testid="stFileUploader"] > section {
            background-color: rgba(255, 255, 255, 0.6) !important;
            border: 1px dashed rgba(99, 102, 241, 0.4) !important;
            border-radius: 16px !important;
            padding: 16px !important;
            color: #000000 !important;
        }

        div[data-testid="stFileUploader"] *, 
        div[data-testid="stFileUploader"] span, 
        div[data-testid="stFileUploader"] small, 
        div[data-testid="stFileUploader"] p {
            color: #000000 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def render_sidebar():
    inject_global_css()
    with st.sidebar:
        # Brand Header: Logo + App Name
        logo_col1, logo_col2 = st.columns([1, 4])
        with logo_col1:
            try:
                st.image("assets/logo.png", width=40)
            except Exception:
                pass
        with logo_col2:
            st.markdown("<h3 style='margin: 0; padding-top: 4px; font-weight: 800; color: #0f172a;'>InvestIQ</h3>", unsafe_allow_html=True)
        
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
            st.page_link("pages/18_Clear_Data.py", label="Database Admin", icon="⚙️")
            
            st.divider()
            if st.button("🚪 Log Out", use_container_width=True):
                st.session_state.authenticated = False
                st.rerun()


def safe_get_secret(key, default=""):
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


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
            background: linear-gradient(135deg, #d3e5ff 0%, #ffdced 35%, #e1d8ff 70%, #d5f7ec 100%) !important;
        }
        
        /* Centered login card styling */
        div[data-testid="column"]:nth-of-type(2) {
            background: rgba(255, 255, 255, 0.45) !important;
            backdrop-filter: blur(25px) !important;
            -webkit-backdrop-filter: blur(25px) !important;
            border: 1px solid rgba(255, 255, 255, 0.5) !important;
            border-radius: 24px !important;
            padding: 45px 35px !important;
            box-shadow: 0 20px 50px rgba(31, 38, 135, 0.05) !important;
            margin-top: 50px !important;
        }
        
        /* Styled input wrappers */
        div[data-testid="stTextInput"] input {
            background-color: rgba(255, 255, 255, 0.5) !important;
            border: 1px solid rgba(255, 255, 255, 0.6) !important;
            color: #0f172a !important;
            border-radius: 12px !important;
            padding: 12px 16px !important;
            font-size: 1rem !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }
        
        div[data-testid="stTextInput"] input:focus {
            border-color: #6366f1 !important;
            box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
            background-color: rgba(255, 255, 255, 0.7) !important;
        }
        
        /* Primary button custom style */
        button[kind="primary"] {
            background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%) !important;
            border: none !important;
            color: #ffffff !important;
            border-radius: 12px !important;
            padding: 12px 24px !important;
            font-weight: 600 !important;
            font-size: 1rem !important;
            width: 100% !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.25) !important;
            margin-top: 15px;
        }
        
        button[kind="primary"]:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4) !important;
            background: linear-gradient(135deg, #4f46e5 0%, #9333ea 100%) !important;
        }
        
        button[kind="primary"]:active {
            transform: translateY(0) !important;
        }
        
        /* Labels formatting */
        label {
            color: #0f172a !important;
            font-weight: 600 !important;
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
            '<img src="/app/static/logo.png" width="80" style="border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">'
            '</div>',
            unsafe_allow_html=True
        )
        
        st.markdown(
            '<h1 style="text-align: center; font-family: \'Outfit\', \'Inter\', sans-serif; font-weight: 800; font-size: 2.2rem; background: linear-gradient(135deg, #6366f1, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 5px; margin-top: 10px;">InvestIQ</h1>', 
            unsafe_allow_html=True
        )
        st.markdown(
            '<p style="text-align: center; color: #475569; font-size: 0.95rem; margin-bottom: 30px;">Wealth is created by owning quality assets, not chasing noise.</p>', 
            unsafe_allow_html=True
        )

        allowed_email = None
        allowed_password = None
        try:
            allowed_email = st.secrets.get("ALLOWED_EMAIL")
            allowed_password = st.secrets.get("ALLOWED_PASSWORD")
        except Exception:
            pass

        if not allowed_email or not allowed_password:
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
