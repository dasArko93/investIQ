# PATH_FIX: ensure root imports work when Streamlit executes page scripts from the pages folder
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
import requests
import json

from utils.page_utils import render_sidebar, require_auth, load_holdings, load_universe
from database.repositories.metadata_repository import MetadataRepository

# Page Configuration
st.set_page_config(
    page_title="InvestIQ - Gemini AI",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Authentication and Navigation Sidebar
require_auth()
render_sidebar()

# Default Settings
DEFAULT_SYSTEM_PROMPT = """You are InvestIQ AI, an elite financial advisor and investment analyst.
You help users analyze their portfolio, track performance, evaluate individual stocks, and plan for financial goals.
Provide clear, mathematically sound, and objective financial analysis.
Format your responses with neat markdown, using tables, bullet points, bold text, and equations where appropriate to present insights clearly."""

# Initialize session state for Gemini chat history
if "gemini_chat_history" not in st.session_state:
    st.session_state.gemini_chat_history = [
        {
            "role": "model",
            "content": "Hello! I am your InvestIQ AI advisor. I can analyze your portfolio holdings, evaluate stock universe fundamentals, and perform risk assessments. How can I help you build wealth today?"
        }
    ]

# Safe retrieval of counts
holdings_count = 0
universe_count = 0
try:
    holdings_df = load_holdings()
    holdings_count = len(holdings_df) if not holdings_df.empty else 0
except Exception:
    pass

try:
    universe_df = load_universe()
    universe_count = len(universe_df) if not universe_df.empty else 0
except Exception:
    pass

# Helper to load/save Gemini API key to database metadata
def get_stored_api_key():
    return MetadataRepository.get("GEMINI_API_KEY") or ""

def save_api_key(key):
    MetadataRepository.set("GEMINI_API_KEY", key.strip())

# Helper to convert DataFrame to Markdown table manually without depending on tabulate package
def df_to_markdown_manual(df):
    if df.empty:
        return ""
    headers = list(df.columns)
    markdown = "| " + " | ".join(map(str, headers)) + " |\n"
    markdown += "| " + " | ".join(["---"] * len(headers)) + " |\n"
    for _, row in df.iterrows():
        # Escape any pipe characters inside values to avoid breaking markdown table formatting
        row_vals = [str(val).replace("\n", " ").replace("|", "\\|") for val in row.values]
        markdown += "| " + " | ".join(row_vals) + " |\n"
    return markdown

# Helper to build the context prompt block
def build_context_block(include_holdings, include_universe):
    context_parts = []
    
    if include_holdings:
        try:
            df = load_holdings()
            if df.empty:
                context_parts.append("PORTFOLIO HOLDINGS:\n(No active holdings found in database. Prompt the user to upload holdings first.)")
            else:
                cols = [c for c in ['Security', 'Quantity', 'Average Cost Rs', 'LTP Rs', 'Current Value Rs', 'PnL Rs', 'PnL %', 'Broker Sector', 'Asset Class'] if c in df.columns]
                df_subset = df[cols]
                
                # Overall Stats
                total_value = df['Current Value Rs'].sum() if 'Current Value Rs' in df.columns else 0
                total_invested = df['Invested Value Rs'].sum() if 'Invested Value Rs' in df.columns else 0
                total_pnl = total_value - total_invested
                total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
                
                summary = (
                    f"Total Invested Value: Rs. {total_invested:,.2f}\n"
                    f"Total Current Value: Rs. {total_value:,.2f}\n"
                    f"Overall Portfolio P&L: Rs. {total_pnl:,.2f} ({total_pnl_pct:+.2f}%)"
                )
                
                context_parts.append(
                    f"### USER'S PORTFOLIO HOLDINGS\n"
                    f"Portfolio Summary:\n{summary}\n\n"
                    f"Holdings Table:\n"
                    f"{df_to_markdown_manual(df_subset)}"
                )
        except Exception as e:
            context_parts.append(f"Error loading portfolio context: {str(e)}")
            
    if include_universe:
        try:
            df = load_universe()
            if df.empty:
                context_parts.append("STOCK UNIVERSE:\n(No universe stocks found in database. Prompt the user to upload stock data first.)")
            else:
                # Essential fields to limit payload tokens
                cols = [c for c in [
                    'Ticker', 'Name', 'Sub-Sector', 'Market Cap', 'Close Price', 'ROCE', 
                    'PE Ratio', 'Forward PE Ratio', 'QUALITY_SCORE', 'Fundamental Score', 
                    'PEG Ratio (Historical)', 'PEG Ratio (Forward)', 'Debt to Equity', 'Sharpe Ratio'
                ] if c in df.columns]
                df_subset = df[cols]
                
                context_parts.append(
                    f"### STOCK UNIVERSE DATABASE\n"
                    f"Listed Stock Metrics:\n"
                    f"{df_to_markdown_manual(df_subset)}"
                )
        except Exception as e:
            context_parts.append(f"Error loading stock universe context: {str(e)}")
            
    return "\n\n".join(context_parts)

# Helper to send query to Gemini
def call_gemini_api(api_key, model_name, messages, system_instruction, temperature, max_tokens):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    # Map roles and message structure to Gemini API format
    contents_payload = []
    for msg in messages:
        if msg["role"] in ["user", "model"]:
            contents_payload.append({
                "role": msg["role"] if msg["role"] != "assistant" else "model",
                "parts": [{"text": msg["content"]}]
            })
            
    payload = {
        "contents": contents_payload,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens
        }
    }
    
    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }
        
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=45)
        if response.status_code == 200:
            res_data = response.json()
            try:
                text_response = res_data['candidates'][0]['content']['parts'][0]['text']
                return {"success": True, "text": text_response}
            except (KeyError, IndexError):
                return {"success": False, "error": f"Invalid API response format: {json.dumps(res_data)}"}
        else:
            try:
                err_msg = response.json().get('error', {}).get('message', response.text)
            except Exception:
                err_msg = response.text
            return {"success": False, "error": f"API Error (Status {response.status_code}): {err_msg}"}
    except Exception as e:
        return {"success": False, "error": f"Connection Error: {str(e)}"}

# --- Layout Configuration ---
st.markdown(
    """
    <div style='margin-bottom: 25px;'>
        <h1 style='margin: 0; background: linear-gradient(135deg, #6366f1, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>🤖 Gemini AI Portfolio Assistant</h1>
        <p style='color: #475569; font-size: 1.1rem; margin-top: 5px;'>Utilize Gemini models using your own API credentials to perform direct analytics on your active portfolio and universe metadata.</p>
    </div>
    """,
    unsafe_allow_html=True
)

col_settings, col_chat = st.columns([1, 2.3], gap="large")

with col_settings:
    st.markdown(
        """
        <div style='background: rgba(255,255,255,0.4); padding: 18px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.5); box-shadow: 0 4px 15px rgba(0,0,0,0.02); margin-bottom: 20px;'>
            <h4 style='margin: 0 0 15px 0; color: #0f172a;'>⚙️ Service configuration</h4>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # 1. AI Premium Subscription vs API Key guide
    stored_key = get_stored_api_key()
    with st.expander("💡 Subscription vs API Guide", expanded=not stored_key):
        st.markdown(
            """
            **Using Google One AI Premium?**
            
            Google does not allow embedding the consumer web interface (`gemini.google.com`) directly inside other apps due to clickjacking and credential phishing protections.
            
            However, you can easily wire up **free** developer API access using your same Google account:
            1. Open [Google AI Studio](https://aistudio.google.com/) (Completely Free).
            2. Sign in with your Google account.
            3. Click **Get API key**, copy your key, and paste it below.
            
            No credit card is required, and there are no extra developer costs for standard usage.
            """
        )
        st.markdown(
            '<div style="display: flex; gap: 10px; margin-bottom: 10px;">'
            '<a href="https://aistudio.google.com/" target="_blank" style="flex: 1; text-align: center; background: rgba(99, 102, 241, 0.15); color: #4f46e5; border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 8px; padding: 8px 6px; font-size: 0.85rem; font-weight: 600; text-decoration: none; transition: all 0.2s;">🔑 Get Free API Key</a>'
            '<a href="https://gemini.google.com/" target="_blank" style="flex: 1; text-align: center; background: rgba(255,255,255,0.5); color: #000; border: 1px solid rgba(0,0,0,0.15); border-radius: 8px; padding: 8px 6px; font-size: 0.85rem; font-weight: 500; text-decoration: none; transition: all 0.2s;">🌐 Gemini Web Chat</a>'
            '</div>',
            unsafe_allow_html=True
        )

    # 2. API Key Input
    api_key_input = st.text_input(
        "Gemini API Key",
        value=stored_key,
        type="password",
        placeholder="AIzaSy...",
        help="The key is stored locally in your SQLite metadata table. Charges are applied directly to your Google AI developer account."
    )
    
    if api_key_input != stored_key:
        if st.button("💾 Save API Key", use_container_width=True):
            save_api_key(api_key_input)
            st.success("API Key saved successfully!")
            st.rerun()
            
    if not api_key_input:
        st.warning("⚠️ Please provide a Gemini API Key to enable the chat panel.")
        
    st.markdown("<hr style='margin: 15px 0; border: none; border-top: 1px solid rgba(0,0,0,0.1);' />", unsafe_allow_html=True)
    
    # 2. Model Selection
    model_choice = st.selectbox(
        "Select Model",
        options=["gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash", "gemini-1.5-pro", "Custom Model"],
        index=0,
        help="gemini-3.5-flash is recommended for general speed and cost efficiency. Use gemini-2.5-pro or gemini-3.5-pro for complex reasoning."
    )
    
    if model_choice == "Custom Model":
        model_name = st.text_input("Enter Custom Model Name", "gemini-3.5-flash")
    else:
        model_name = model_choice
        
    # 3. Context Injection Toggles
    st.markdown("<h5 style='margin: 15px 0 10px 0;'>📊 Context & Data Toggles</h5>", unsafe_allow_html=True)
    inject_holdings = st.checkbox(
        f"🔗 Inject Holdings ({holdings_count} assets)",
        value=True if holdings_count > 0 else False,
        disabled=(holdings_count == 0),
        help="Let Gemini read your uploaded stock and mutual fund holdings list to assess returns, allocation, and risk."
    )
    
    inject_universe = st.checkbox(
        f"🔗 Inject Stock Universe ({universe_count} stocks)",
        value=False,
        disabled=(universe_count == 0),
        help="Let Gemini read your Stock screener master data to rank and filter stocks based on quality scores, PEG, ROCE, and fundamentals."
    )
    
    if holdings_count == 0:
        st.info("💡 Upload holdings in the 'holding' section to unlock portfolio context injection.")
    if universe_count == 0:
        st.info("💡 Upload stock master data in the 'Stock Universe' page to unlock database metric query capabilities.")
        
    # 4. Advanced Settings Expander
    with st.expander("🛠️ Advanced Parameters", expanded=False):
        temperature = st.slider("Temperature", min_value=0.0, max_value=2.0, value=0.7, step=0.1, help="Higher values create more creative outputs, lower values are more deterministic.")
        max_tokens = st.number_input("Max Output Tokens", min_value=128, max_value=8192, value=2048, step=128)
        system_prompt = st.text_area("System Instructions", value=DEFAULT_SYSTEM_PROMPT, height=200)

    # 5. Clear Chat Button
    if st.button("🧹 Clear Chat History", use_container_width=True):
        st.session_state.gemini_chat_history = [
            {
                "role": "model",
                "content": "Hello! I am your InvestIQ AI advisor. I can analyze your portfolio holdings, evaluate stock universe fundamentals, and perform risk assessments. How can I help you build wealth today?"
            }
        ]
        st.rerun()

    # 6. Context Viewer
    context_data = build_context_block(inject_holdings, inject_universe)
    if context_data:
        st.markdown("<hr style='margin: 15px 0; border: none; border-top: 1px solid rgba(0,0,0,0.1);' />", unsafe_allow_html=True)
        with st.expander("🔍 View Injected Context Data", expanded=False):
            st.markdown(f"```markdown\n{context_data}\n```")

with col_chat:
    # Render Chat title header
    st.markdown(
        """
        <div style='background: rgba(255,255,255,0.4); padding: 18px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.5); box-shadow: 0 4px 15px rgba(0,0,0,0.02); margin-bottom: 10px;'>
            <h4 style='margin: 0; color: #0f172a;'>💬 Chat Timeline</h4>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Independently scrollable chat pane
    chat_container = st.container(height=600)
    
    # Render chat bubbles from history inside the scrollable container
    with chat_container:
        for message in st.session_state.gemini_chat_history:
            role = "assistant" if message["role"] == "model" else "user"
            with st.chat_message(role):
                st.write(message["content"])
            
    # Input box (pinned to bottom of page by Streamlit)
    if prompt := st.chat_input("Ask a question about your portfolio, stocks or metrics...", disabled=not api_key_input):
        # Render user message inside the container immediately
        with chat_container:
            with st.chat_message("user"):
                st.write(prompt)
            
        # Append user message to history
        st.session_state.gemini_chat_history.append({"role": "user", "content": prompt})
        
        # Build System Prompt and Context
        context_data = build_context_block(inject_holdings, inject_universe)
        
        # To ensure maximum recall, we prepend/append context directly into the API message payload
        messages_to_send = []
        for msg in st.session_state.gemini_chat_history[:-1]:
            messages_to_send.append(msg)
            
        last_msg = st.session_state.gemini_chat_history[-1]
        if context_data:
            augmented_content = f"[DATABASE CONTEXT DATA]:\n{context_data}\n\n[USER QUERY]:\n{last_msg['content']}"
            messages_to_send.append({"role": "user", "content": augmented_content})
        else:
            messages_to_send.append(last_msg)
            
        # Call API inside the container with typing spinner
        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner("Analyzing portfolio data & generating response..."):
                    response_res = call_gemini_api(
                        api_key=api_key_input,
                        model_name=model_name,
                        messages=messages_to_send,
                        system_instruction=system_prompt,
                        temperature=temperature,
                        max_tokens=int(max_tokens)
                    )
                    
                    if response_res["success"]:
                        ans_text = response_res["text"]
                        st.write(ans_text)
                        st.session_state.gemini_chat_history.append({"role": "model", "content": ans_text})
                    else:
                        err_msg = response_res["error"]
                        st.error(f"❌ Gemini API Call Failed.\n\n{err_msg}")
                        # Remove last user message from history so the context doesn't get messed up
                        st.session_state.gemini_chat_history.pop()
        
        st.rerun()
