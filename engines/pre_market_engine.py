import os
import json
import logging
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

import pandas as pd
import numpy as np
import yfinance as yf

from services.securities_master_service import SecuritiesMasterService
from database.db import SessionLocal
from database.models import PriceHistory

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_FILE = CACHE_DIR / "pre_market_scanner_cache.json"

# Representative and liquid NSE F&O Universe (~180 Most Actively Traded Equities)
NSE_FO_UNIVERSE = [
    "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "ITC", "LT", "SBIN",
    "BHARTIARTL", "KOTAKBANK", "AXISBANK", "HINDUNILVR", "BAJFINANCE", "MARUTI",
    "TITAN", "SUNPHARMA", "TATAMOTORS", "TATASTEEL", "ASIANPAINT", "NTPC",
    "POWERGRID", "ONGC", "COALINDIA", "M&M", "ADANIENT", "ADANIPORTS", "JSWSTEEL",
    "TECHM", "HCLTECH", "WIPRO", "BAJAJFINSV", "NESTLEIND", "GRASIM", "ULTRACEMCO",
    "BPCL", "CIPLA", "HEROMOTOCO", "DRREDDY", "EICHERMOT", "HINDALCO", "BRITANNIA",
    "APOLLOHOSP", "TATACONSUM", "SBILIFE", "HDFCLIFE", "INDUSINDBK", "BEL", "TRENT",
    "HAL", "BHEL", "DLF", "CANBK", "PNB", "BANKBARODA", "CHOLAFIN", "RECLTD", "PFC",
    "VBL", "POLYCAB", "CUMMINSIND", "PERSISTENT", "COFORGE", "LTTS", "DIXON", "SIEMENS",
    "ABB", "VOLTAS", "AUROPHARMA", "LUPIN", "TORNTPHARM", "ALKEM", "BIOCON", "GODREJCP",
    "DABUR", "MARICO", "PIDILITIND", "HAVELLS", "INDHOTEL", "JUBLFOOD", "ABCAPITAL",
    "MUTHOOTFIN", "SRF", "ASTRAL", "ASHOKLEY", "TVSMOTOR", "BALKRISIND", "CONCOR",
    "ESCORTS", "HINDPETRO", "IOC", "IGL", "MGL", "GUJGASLTD", "PETRONET", "NATIONALUM",
    "NMDC", "SAIL", "JINDALSTEL", "VEDL", "HDFCAMC", "NAUKRI", "ZOMATO", "OBEROIRLTY",
    "GODREJPROP", "PHOENIXLTD", "TATACOMM", "INDUSTOWER", "IDEA", "AMBUJACEM", "ACC",
    "DALBHARAT", "SHREECEM", "FEDERALBNK", "IDFCFIRSTB", "BANDHANBNK", "AUBANK",
    "L&TFH", "LICHSGFIN", "MANAPPURAM", "M&MFIN", "POONAWALLA", "SUNTV", "ZEEL",
    "PVRINOX", "BOSCHLTD", "MOTHERSON", "BHARATFORG", "SONACOMS", "TIINDIA", "EXIDEIND",
    "APOLLOTYRE", "MRF", "DEEPAKNTR", "TATACHEM", "PIIND", "UPL", "COROMANDEL",
    "CHAMBLFERT", "GNFC", "ATUL", "NAVINFLUOR", "SYNGENE", "GLENMARK", "IPCALAB",
    "LAURUSLABS", "GRANULES", "METROPOLIS", "LALPATHLAB", "MAXHEALTH", "FORTIS",
    "MPHASIS", "KPITTECH", "TATAELXSI", "OFSS", "CYIENT", "BSOFT", "PAGEIND",
    "BATAINDIA", "ABFRL", "RAYMOND", "IRCTC", "DEVYANI", "DELHIVERY"
]


class PreMarketEngine:
    """
    Implements the 3-Stage EOD Stock Filtering Funnel for Pre-Market Stock Selection
    across all listed Indian Equities (Large, Mid, Small - strictly excluding Penny Stocks).
    """
    CACHE_FILE = CACHE_FILE

    @classmethod
    def set_manual_vix(cls, vix_val: float) -> Dict[str, Any]:
        """Manually sets/overrides the India VIX value for simulation and testing."""
        as_of_time = datetime.now().strftime("%d %b %Y, %I:%M %p")
        c_data = {}
        if cls.CACHE_FILE.exists():
            try:
                with open(cls.CACHE_FILE, "r") as f:
                    c_data = json.load(f)
            except Exception:
                pass
        c_data["regime"] = {
            "vix_value": round(float(vix_val), 2),
            "as_of": as_of_time,
            "source": "Manual Simulation"
        }
        try:
            with open(cls.CACHE_FILE, "w") as f:
                json.dump(c_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Error saving manual VIX: {e}")
        return cls.get_market_regime(force_refresh=False)

    @classmethod
    def get_market_regime(cls, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Calculates current India VIX market regime and GIFT Nifty sentiment guidance.
        Rules from PDF:
          - Below 12: Range-bound / quiet, favors mean reversion. Breakout trades risky.
          - 13 to 18: Solid directional trends ideal for breakouts (2% to 5% expansion).
          - Above 20: High volatility; wide stop losses, reduced position sizing.
        """
        vix_val = 13.8  # Default baseline
        as_of_time = datetime.now().strftime("%d %b %Y, %I:%M %p")
        source_note = "Cached"

        # Check cache if not forcing refresh
        if CACHE_FILE.exists() and not force_refresh:
            try:
                with open(CACHE_FILE, "r") as f:
                    c_data = json.load(f)
                    if "regime" in c_data and "vix_value" in c_data["regime"]:
                        vix_val = float(c_data["regime"]["vix_value"])
                        as_of_time = c_data["regime"].get("as_of", as_of_time)
                        source_note = c_data["regime"].get("source", "Cached")
            except Exception:
                pass

        if force_refresh:
            as_of_time = datetime.now().strftime("%d %b %Y, %I:%M %p")
            # Attempt live fetch via yfinance
            try:
                import yfinance as yf
                ticker = yf.Ticker("^INDIAVIX")
                hist = ticker.history(period="5d", timeout=4)
                if not hist.empty and "Close" in hist.columns:
                    vix_val = round(float(hist["Close"].dropna().iloc[-1]), 2)
                    source_note = "Live Market (Yahoo / NSE)"
                else:
                    source_note = "Latest EOD (Market Closed)"
            except Exception as e:
                logger.warning(f"Live VIX fetch timed out or network offline: {e}. Retaining latest value.")
                source_note = "Latest Available (Offline / Cached)"

            # Persist updated regime to CACHE_FILE
            try:
                c_data = {}
                if CACHE_FILE.exists():
                    with open(CACHE_FILE, "r") as f:
                        c_data = json.load(f)
                c_data["regime"] = {
                    "vix_value": vix_val,
                    "as_of": as_of_time,
                    "source": source_note
                }
                with open(CACHE_FILE, "w") as f:
                    json.dump(c_data, f, indent=2)
            except Exception as e:
                logger.warning(f"Could not persist refreshed regime to cache: {e}")

        if vix_val < 12.0:
            regime = "Quiet / Range-Bound (Mean Reversion Mode)"
            badge_color = "#eab308"  # Yellow
            sentiment_icon = "🟡"
            guidance = (
                "India VIX is below 12. Anticipate compressed intraday price ranges and frequent breakout failures. "
                "Strategies like mean reversion (buying support, selling resistance) work best. Avoid chasing aggressive breakout orders."
            )
        elif 12.0 <= vix_val <= 18.5:
            regime = "Optimal Directional Trend (Prime Breakout Mode)"
            badge_color = "#16a34a"  # Green
            sentiment_icon = "🟢"
            guidance = (
                "India VIX is in the sweet spot (12-18). Solid directional trends are highly probable. "
                "Ideal environment for NR7, Inside Bar, and Narrow CPR breakouts with 2% to 5% expansion targets."
            )
        else:
            regime = "High Volatility (Defensive Risk Mode)"
            badge_color = "#ef4444"  # Red
            sentiment_icon = "🔴"
            guidance = (
                "India VIX is elevated (> 18.5). Expect wider price swings, gap risks, and erratic spikes. "
                "Widen stop loss buffers, use conservative 0.5x position sizing, and trail stops aggressively via ATR."
            )

        return {
            "vix_value": vix_val,
            "regime": regime,
            "badge_color": badge_color,
            "sentiment_icon": sentiment_icon,
            "guidance": guidance,
            "as_of": as_of_time,
            "source": source_note
        }

    @classmethod
    def get_eligible_universe(
        cls,
        tier: str = "All",
        min_price: float = 100.0,
        max_stocks: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Retrieves eligible non-penny Indian equities from SecuritiesMasterService across:
          - Large Cap (Rank 1-100)
          - Mid Cap (Rank 101-250)
          - Small Cap (Rank 251+)
          - F&O Universe (~180 Stocks)
        """
        SecuritiesMasterService.load_master()
        df = SecuritiesMasterService._master_df
        if df is None or df.empty:
            # Fallback to predefined F&O list
            return [{"ticker": t, "name": t, "sector": "Diversified", "market_cap_tier": "F&O Liquid", "ltp": 500.0} for t in NSE_FO_UNIVERSE[:max_stocks]]

        # Strictly non-penny equities (LTP >= min_price, instrument_type == Equity)
        filtered = df[(df["instrument_type"] == "Equity") & (df["ltp"] >= min_price)].copy()

        # Exclude non-corporate trusts, InvITs, and REITs (not regular equities)
        non_equity_mask = (
            filtered["ticker"].str.endswith(("INVIT", "REIT", "-IV", "-RR")) |
            filtered["name"].str.contains(r"(?i)\b(?:InvIT|REIT|Trust|Infrastructure Trust|Real Estate Investment Trust)\b", regex=True, na=False)
        )
        filtered = filtered[~non_equity_mask]

        if tier == "Large Cap":
            filtered = filtered[filtered["market_cap_tier"] == "Large Cap"]
        elif tier == "Mid Cap":
            filtered = filtered[filtered["market_cap_tier"] == "Mid Cap"]
        elif tier == "Small Cap":
            filtered = filtered[filtered["market_cap_tier"] == "Small Cap"]
        elif tier == "F&O Universe":
            filtered = filtered[filtered["ticker"].isin(NSE_FO_UNIVERSE)]
        elif tier == "Large & Mid Cap":
            filtered = filtered[filtered["market_cap_tier"].isin(["Large Cap", "Mid Cap"])]

        # Order by market cap rank or market cap descending
        if "market_cap_rank" in filtered.columns:
            filtered = filtered.sort_values(by="market_cap_rank", ascending=True)
        elif "market_cap_cr" in filtered.columns:
            filtered = filtered.sort_values(by="market_cap_cr", ascending=False)

        if max_stocks and max_stocks > 0:
            filtered = filtered.head(max_stocks)

        candidates = []
        for _, r in filtered.iterrows():
            candidates.append({
                "ticker": str(r["ticker"]).strip(),
                "name": str(r.get("name", r["ticker"])).strip(),
                "sector": str(r.get("sector", "Diversified")).strip(),
                "market_cap_tier": str(r.get("market_cap_tier", "Equity")).strip(),
                "ltp": float(r.get("ltp", 0.0))
            })

        return candidates

    @classmethod
    def analyze_single_stock(
        cls,
        ticker: str,
        df: Optional[pd.DataFrame] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Executes Stage 1 (Compression) & Stage 2 (Confirmation) math on a single ticker.
        """
        clean_ticker = ticker.replace(".NS", "").strip()
        yf_sym = f"{clean_ticker}.NS"
        meta = metadata or {}

        try:
            if df is None or len(df) < 8:
                try:
                    df = yf.download(yf_sym, period="2mo", interval="1d", progress=False)
                except Exception:
                    df = None

            # Fallback to local PriceHistory database if yfinance returned empty or failed
            if df is None or len(df) < 8:
                db = SessionLocal()
                try:
                    records = db.query(PriceHistory).filter(PriceHistory.ticker == clean_ticker).order_by(PriceHistory.date.asc()).all()
                    if records and len(records) >= 8:
                        df = pd.DataFrame([{
                            "Date": r.date,
                            "Open": r.open,
                            "High": r.high,
                            "Low": r.low,
                            "Close": r.close,
                            "Volume": r.volume or 1000000.0
                        } for r in records]).set_index("Date")
                finally:
                    db.close()
            
            if df is None or len(df) < 8:
                return None

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Ensure numeric types
            for c in ["Open", "High", "Low", "Close", "Volume"]:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors="coerce")

            df = df.dropna(subset=["High", "Low", "Close"])
            if len(df) < 8:
                return None

            df["Range"] = df["High"] - df["Low"]

            curr = df.iloc[-1]
            prev = df.iloc[-2]

            curr_close = float(curr["Close"])
            curr_high = float(curr["High"])
            curr_low = float(curr["Low"])
            curr_range = float(curr["Range"])
            curr_vol = float(curr["Volume"]) if "Volume" in curr else 0.0

            # Strictly exclude penny stocks (price < 100)
            if curr_close < 100.0:
                return None

            # ---------------------------------------------------------
            # Stage 1: Volatility & Price Compression Scans
            # ---------------------------------------------------------
            last_7_ranges = df["Range"].iloc[-7:]
            last_4_ranges = df["Range"].iloc[-4:]
            min_7 = float(last_7_ranges.min())
            min_4 = float(last_4_ranges.min())

            is_nr7 = bool(curr_range <= min_7 + 1e-4)
            is_nr4 = bool(curr_range <= min_4 + 1e-4)
            is_inside_bar = bool((curr_high < float(prev["High"])) and (curr_low > float(prev["Low"])))

            # Narrow Central Pivot Range (CPR) for Next Session
            p = (curr_high + curr_low + curr_close) / 3.0
            bc = (curr_high + curr_low) / 2.0
            tc = (p - bc) + p
            cpr_width = abs(tc - bc)
            cpr_pct = (cpr_width / curr_close) * 100.0 if curr_close > 0 else 1.0
            is_narrow_cpr = bool(cpr_pct < 0.25)

            # Has any Stage 1 compression setup
            has_compression = is_nr7 or is_nr4 or is_inside_bar or is_narrow_cpr

            # ---------------------------------------------------------
            # Stage 2: Institutional Confirmation (Volume & Close Location)
            # ---------------------------------------------------------
            vol_20_series = df["Volume"].iloc[-21:-1]
            vol_20_avg = float(vol_20_series.mean()) if len(vol_20_series) > 0 else curr_vol
            vol_surge = bool(curr_vol >= (1.5 * vol_20_avg)) if vol_20_avg > 0 else False
            vol_ratio = round(curr_vol / vol_20_avg, 2) if vol_20_avg > 0 else 1.0

            # Candle close location: Top 20% or Bottom 20%
            if curr_range > 0:
                candle_pos = (curr_close - curr_low) / curr_range
            else:
                candle_pos = 0.5

            strong_bullish_close = bool(candle_pos >= 0.80)
            strong_bearish_close = bool(candle_pos <= 0.20)
            strong_close = strong_bullish_close or strong_bearish_close

            # Directional Bias
            if strong_bullish_close or candle_pos >= 0.55:
                direction = "BULLISH"
                dir_icon = "🚀"
                dir_color = "#16a34a"
            elif strong_bearish_close or candle_pos <= 0.45:
                direction = "BEARISH"
                dir_icon = "🔻"
                dir_color = "#dc2626"
            else:
                direction = "NEUTRAL"
                dir_icon = "⚪"
                dir_color = "#64748b"

            # ---------------------------------------------------------
            # Stage 3: Daily ATR & Next-Day Trigger Prep
            # ---------------------------------------------------------
            tr1 = df["High"] - df["Low"]
            tr2 = (df["High"] - df["Close"].shift(1)).abs()
            tr3 = (df["Low"] - df["Close"].shift(1)).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr14 = float(tr.rolling(14).mean().iloc[-1])
            if np.isnan(atr14) or atr14 <= 0:
                atr14 = curr_range if curr_range > 0 else curr_close * 0.02

            atr_pct = round((atr14 / curr_close) * 100.0, 2)

            pdh = round(curr_high, 2)
            pdl = round(curr_low, 2)

            # Target & Stop Loss calculations (1.5x to 2.0x ATR expansion)
            if direction == "BULLISH":
                trigger_rule = f"Buy on 5-min candle breakout ABOVE PDH (₹{pdh:,.2f}) with expanding volume"
                target_1_5x = round(pdh + (1.5 * atr14), 2)
                target_2_0x = round(pdh + (2.0 * atr14), 2)
                stop_loss = round(max(pdl, curr_close - (0.5 * atr14)), 2)
                expansion_pct_est = round(((target_1_5x - pdh) / pdh) * 100.0, 1)
            else:
                trigger_rule = f"Sell on 5-min candle breakdown BELOW PDL (₹{pdl:,.2f}) with expanding volume"
                target_1_5x = round(pdl - (1.5 * atr14), 2)
                target_2_0x = round(pdl - (2.0 * atr14), 2)
                stop_loss = round(min(pdh, curr_close + (0.5 * atr14)), 2)
                expansion_pct_est = round(((pdl - target_1_5x) / pdl) * 100.0, 1)

            # Setup Tags
            setups_detected = []
            if is_nr7:
                setups_detected.append("NR7")
            elif is_nr4:
                setups_detected.append("NR4")
            if is_inside_bar:
                setups_detected.append("Inside Bar")
            if is_narrow_cpr:
                setups_detected.append("Narrow CPR (<0.25%)")
            if vol_surge:
                setups_detected.append(f"Volume Surge ({vol_ratio}x)")
            if strong_bullish_close:
                setups_detected.append("Top 20% Close")
            elif strong_bearish_close:
                setups_detected.append("Bottom 20% Close")

            setup_str = " + ".join(setups_detected) if setups_detected else "Compression Candidate"

            # High conviction requires: Stage 1 Compression + (Volume Surge OR Narrow CPR OR Strong Close)
            is_high_conviction = has_compression and (vol_surge or is_narrow_cpr or strong_close)

            # Metadata enrichment
            stock_name = meta.get("name", clean_ticker)
            sector_name = meta.get("sector", "Diversified")
            mcap_tier = meta.get("market_cap_tier", "Equity")

            return {
                "Ticker": clean_ticker,
                "Stock Name": stock_name,
                "Sector": sector_name,
                "Market Cap Tier": mcap_tier,
                "Close": round(curr_close, 2),
                "PDH": pdh,
                "PDL": pdl,
                "Range": round(curr_range, 2),
                "Range_Pct": round((curr_range / curr_close) * 100.0, 2),
                "NR7": is_nr7,
                "NR4": is_nr4,
                "InsideBar": is_inside_bar,
                "CPR_Pct": round(cpr_pct, 3),
                "Narrow_CPR": is_narrow_cpr,
                "Volume": int(curr_vol),
                "Vol_20D_Avg": int(vol_20_avg),
                "Vol_Surge_1_5x": vol_surge,
                "Vol_Ratio": vol_ratio,
                "Candle_Position_Pct": round(candle_pos * 100.0, 1),
                "Strong_Close": strong_close,
                "Direction": direction,
                "Direction_Icon": dir_icon,
                "Direction_Color": dir_color,
                "Daily_ATR": round(atr14, 2),
                "Daily_ATR_Pct": atr_pct,
                "Target_1_5x": target_1_5x,
                "Target_2_0x": target_2_0x,
                "Stop_Loss": stop_loss,
                "Estimated_Expansion_Pct": expansion_pct_est,
                "Trigger_Rule": trigger_rule,
                "Setup_Tags": setup_str,
                "Has_Compression": has_compression,
                "Is_High_Conviction": is_high_conviction,
                "Last_Date": curr.name.strftime("%Y-%m-%d") if hasattr(curr.name, "strftime") else str(curr.name)
            }
        except Exception as e:
            logger.warning(f"Error analyzing ticker {ticker}: {e}")
            return None

    @classmethod
    def run_screener(
        cls,
        tier: str = "All",
        min_price: float = 100.0,
        max_stocks: int = 150,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Runs the full EOD pre-market screening pipeline across non-penny Indian equities.
        Caches results locally for responsive dashboard rendering.
        """
        today_str = date.today().strftime("%Y-%m-%d")
        cache_key = f"{tier}_{int(min_price)}_{max_stocks}"

        if not force_refresh and CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r") as f:
                    cache_data = json.load(f)
                    if (cache_data.get("scan_date") == today_str and 
                        "results" in cache_data and len(cache_data["results"]) > 0):
                        logger.info("Loaded pre-market scan from cache.")
                        df_all = pd.DataFrame(cache_data["results"])
                        
                        # Filter by min_price
                        if not df_all.empty and "Close" in df_all.columns:
                            df_all = df_all[df_all["Close"] >= min_price]

                        # Filter by tier if specified
                        if not df_all.empty and "Market Cap Tier" in df_all.columns:
                            if tier == "Large Cap":
                                df_all = df_all[df_all["Market Cap Tier"] == "Large Cap"]
                            elif tier == "Mid Cap":
                                df_all = df_all[df_all["Market Cap Tier"] == "Mid Cap"]
                            elif tier == "Small Cap":
                                df_all = df_all[df_all["Market Cap Tier"] == "Small Cap"]
                            elif tier == "Large & Mid Cap":
                                df_all = df_all[df_all["Market Cap Tier"].isin(["Large Cap", "Mid Cap"])]
                            elif tier == "F&O Universe":
                                df_all = df_all[df_all["Ticker"].isin(NSE_FO_UNIVERSE)]

                        high_conv = df_all[df_all["Is_High_Conviction"] == True] if not df_all.empty else pd.DataFrame()
                        comp_only = df_all[df_all["Has_Compression"] == True] if not df_all.empty else pd.DataFrame()
                        return {
                            "all_results_df": df_all,
                            "high_conviction_df": high_conv,
                            "compression_df": comp_only,
                            "regime": cache_data.get("regime", cls.get_market_regime()),
                            "scan_timestamp": cache_data.get("timestamp", today_str),
                            "total_scanned": len(df_all)
                        }
            except Exception as e:
                logger.warning(f"Could not read cache: {e}")

        # Retrieve eligible non-penny universe candidates
        candidates = cls.get_eligible_universe(tier=tier, min_price=min_price, max_stocks=max_stocks)
        meta_map = {c["ticker"]: c for c in candidates}
        tickers_to_scan = [c["ticker"] for c in candidates]

        if not tickers_to_scan:
            tickers_to_scan = NSE_FO_UNIVERSE[:max_stocks]

        # Batch download daily bars via yfinance
        yf_symbols = [f"{t}.NS" for t in tickers_to_scan]
        logger.info(f"Downloading daily bars for {len(yf_symbols)} tickers in tier '{tier}'...")

        try:
            batch_data = yf.download(
                yf_symbols,
                period="2mo",
                interval="1d",
                group_by="ticker",
                progress=False,
                threads=True
            )
        except Exception as e:
            logger.error(f"Batch yfinance download failed: {e}")
            batch_data = None

        results = []
        for sym in tickers_to_scan:
            yf_k = f"{sym}.NS"
            stock_df = None
            if batch_data is not None:
                try:
                    if isinstance(batch_data.columns, pd.MultiIndex):
                        if yf_k in batch_data.columns.levels[0]:
                            stock_df = batch_data[yf_k].dropna(subset=["Close"])
                        elif sym in batch_data.columns.levels[0]:
                            stock_df = batch_data[sym].dropna(subset=["Close"])
                except Exception:
                    stock_df = None

            res = cls.analyze_single_stock(sym, df=stock_df, metadata=meta_map.get(sym))
            if res:
                results.append(res)

        df_all = pd.DataFrame(results) if results else pd.DataFrame()
        high_conv = df_all[df_all["Is_High_Conviction"] == True] if not df_all.empty else pd.DataFrame()
        comp_only = df_all[df_all["Has_Compression"] == True] if not df_all.empty else pd.DataFrame()

        regime_info = cls.get_market_regime()
        now_str = datetime.now().strftime("%d %b %Y, %I:%M %p")

        # Save to cache
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump({
                    "scan_date": today_str,
                    "cache_key": cache_key,
                    "timestamp": now_str,
                    "regime": regime_info,
                    "results": results
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not write cache: {e}")

        return {
            "all_results_df": df_all,
            "high_conviction_df": high_conv,
            "compression_df": comp_only,
            "regime": regime_info,
            "scan_timestamp": now_str,
            "total_scanned": len(df_all)
        }
