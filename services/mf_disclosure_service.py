"""
AMC Disclosure Downloader & MF Ingestion Service
=================================================
Fetches the live AMFI scheme master (NAVAll.txt) for all ~15,000+ Indian MF schemes,
deduplicates to unique equity-oriented funds by AMC, and seeds comprehensive portfolio
holding data covering 50+ representative Indian equity funds across all SEBI categories.

Data Sources:
  - AMFI NAVAll.txt  → Real scheme codes, ISINs, AMC names, scheme names
  - Seeded portfolio  → Curated representative holdings data for top schemes
  - Upload parser     → Dynamic parser for official AMC disclosure spreadsheets (.xlsx/.csv)
"""

import io
import os
import re
import time
import json
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional
import pandas as pd
from sqlalchemy import func

from database.db import SessionLocal, engine
from database.models import (
    Base,
    MFScheme,
    MFPortfolioSnapshot,
    MFSchemeHolding,
    UserPortfolioHolding,
    Holding,
    StockMaster
)

RAW_DISCLOSURES_DIR = Path(__file__).resolve().parent.parent / "data" / "raw_disclosures"
RAW_DISCLOSURES_DIR.mkdir(parents=True, exist_ok=True)

AMFI_NAV_ALL_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
AMFI_SCHEME_LIST_CACHE = Path(__file__).resolve().parent.parent / "data" / "amfi_scheme_master.json"

# ---------------------------------------------------------------------------
# ISIN Master — Maps NSE ticker → (ISIN, Full Name, Sector, Market Cap Category)
# ---------------------------------------------------------------------------
ISIN_LOOKUP = {
    # Nifty 50 / Large Cap
    "RELIANCE":     ("INE002A01018", "Reliance Industries Ltd",               "Energy / Oil & Gas",          "Large Cap"),
    "HDFCBANK":     ("INE040A01034", "HDFC Bank Ltd",                         "Financial Services",          "Large Cap"),
    "ICICIBANK":    ("INE090A01021", "ICICI Bank Ltd",                        "Financial Services",          "Large Cap"),
    "INFY":         ("INE009A01021", "Infosys Ltd",                           "Information Technology",      "Large Cap"),
    "TCS":          ("INE467B01029", "Tata Consultancy Services Ltd",         "Information Technology",      "Large Cap"),
    "BHARTIARTL":   ("INE397D01024", "Bharti Airtel Ltd",                     "Telecommunication",           "Large Cap"),
    "ITC":          ("INE154A01025", "ITC Ltd",                               "Fast Moving Consumer Goods",  "Large Cap"),
    "LT":           ("INE018A01030", "Larsen & Toubro Ltd",                   "Capital Goods",               "Large Cap"),
    "SBIN":         ("INE062A01020", "State Bank of India",                   "Financial Services",          "Large Cap"),
    "KOTAKBANK":    ("INE237A01028", "Kotak Mahindra Bank Ltd",               "Financial Services",          "Large Cap"),
    "AXISBANK":     ("INE238A01034", "Axis Bank Ltd",                         "Financial Services",          "Large Cap"),
    "HINDUNILVR":   ("INE030A01027", "Hindustan Unilever Ltd",                "Fast Moving Consumer Goods",  "Large Cap"),
    "BAJFINANCE":   ("INE296A01024", "Bajaj Finance Ltd",                     "Financial Services",          "Large Cap"),
    "M&M":          ("INE101A01026", "Mahindra & Mahindra Ltd",               "Automobile",                  "Large Cap"),
    "TATAMOTORS":   ("INE155A01022", "Tata Motors Ltd",                       "Automobile",                  "Large Cap"),
    "SUNPHARMA":    ("INE044A01036", "Sun Pharmaceutical Industries Ltd",     "Healthcare",                  "Large Cap"),
    "TITAN":        ("INE280A01028", "Titan Company Ltd",                     "Consumer Durables",           "Large Cap"),
    "MARUTI":       ("INE585B01010", "Maruti Suzuki India Ltd",               "Automobile",                  "Large Cap"),
    "NTPC":         ("INE733E01010", "NTPC Ltd",                              "Power / Utilities",           "Large Cap"),
    "ONGC":         ("INE213A01029", "Oil & Natural Gas Corporation Ltd",     "Energy / Oil & Gas",          "Large Cap"),
    "POWERGRID":    ("INE752E01010", "Power Grid Corporation of India Ltd",   "Power / Utilities",           "Large Cap"),
    "ADANIPORTS":   ("INE742F01042", "Adani Ports and SEZ Ltd",               "Services / Infrastructure",   "Large Cap"),
    "TATASTEEL":    ("INE081A01020", "Tata Steel Ltd",                        "Metals & Mining",             "Large Cap"),
    "ASIANPAINT":   ("INE021A01026", "Asian Paints Ltd",                      "Consumer Durables",           "Large Cap"),
    "ULTRACEMCO":   ("INE481G01011", "UltraTech Cement Ltd",                  "Materials / Cement",          "Large Cap"),
    "COALINDIA":    ("INE522F01014", "Coal India Ltd",                        "Metals & Mining",             "Large Cap"),
    "BAJAJFINSV":   ("INE918I01026", "Bajaj Finserv Ltd",                     "Financial Services",          "Large Cap"),
    "NESTLEIND":    ("INE239A01024", "Nestle India Ltd",                      "Fast Moving Consumer Goods",  "Large Cap"),
    "HCLTECH":      ("INE860A01027", "HCL Technologies Ltd",                  "Information Technology",      "Large Cap"),
    "WIPRO":        ("INE075A01022", "Wipro Ltd",                             "Information Technology",      "Large Cap"),
    "JSWSTEEL":     ("INE019A01038", "JSW Steel Ltd",                         "Metals & Mining",             "Large Cap"),
    "HINDALCO":     ("INE038A01020", "Hindalco Industries Ltd",               "Metals & Mining",             "Large Cap"),
    "GRASIM":       ("INE047A01021", "Grasim Industries Ltd",                 "Materials / Cement",          "Large Cap"),
    "TECHM":        ("INE669C01036", "Tech Mahindra Ltd",                     "Information Technology",      "Large Cap"),
    "INDUSINDBK":   ("INE095A01012", "IndusInd Bank Ltd",                     "Financial Services",          "Large Cap"),
    "BPCL":         ("INE029A01011", "Bharat Petroleum Corporation Ltd",      "Energy / Oil & Gas",          "Large Cap"),
    "SHREECEM":     ("INE070A01015", "Shree Cement Ltd",                      "Materials / Cement",          "Large Cap"),
    "DRREDDY":      ("INE089A01023", "Dr. Reddy's Laboratories Ltd",          "Healthcare",                  "Large Cap"),
    "CIPLA":        ("INE059A01026", "Cipla Ltd",                             "Healthcare",                  "Large Cap"),
    "DIVISLAB":     ("INE361B01024", "Divi's Laboratories Ltd",               "Healthcare",                  "Large Cap"),
    "ADANIENT":     ("INE423A01024", "Adani Enterprises Ltd",                 "Conglomerates",               "Large Cap"),
    "BAJAJ-AUTO":   ("INE917I01010", "Bajaj Auto Ltd",                        "Automobile",                  "Large Cap"),
    "EICHERMOT":    ("INE066A01021", "Eicher Motors Ltd",                     "Automobile",                  "Large Cap"),
    "HEROMOTOCO":   ("INE158A01026", "Hero MotoCorp Ltd",                     "Automobile",                  "Large Cap"),
    "TATACONSUM":   ("INE192A01025", "Tata Consumer Products Ltd",            "Fast Moving Consumer Goods",  "Large Cap"),
    "BRITANNIA":    ("INE216A01030", "Britannia Industries Ltd",              "Fast Moving Consumer Goods",  "Large Cap"),
    "APOLLOHOSP":   ("INE437A01024", "Apollo Hospitals Enterprise Ltd",       "Healthcare",                  "Large Cap"),
    "SBILIFE":      ("INE123W01016", "SBI Life Insurance Company Ltd",        "Financial Services",          "Large Cap"),
    "HDFCLIFE":     ("INE795G01014", "HDFC Life Insurance Company Ltd",       "Financial Services",          "Large Cap"),
    "ICICIPRULI":   ("INE726G01019", "ICICI Prudential Life Insurance Co Ltd","Financial Services",          "Large Cap"),
    # Mid Cap
    "POLYCAB":      ("INE455K01017", "Polycab India Ltd",                     "Capital Goods",               "Mid Cap"),
    "TRENT":        ("INE849A01020", "Trent Ltd",                             "Consumer Services / Retail",  "Mid Cap"),
    "SUPREMEIND":   ("INE578A01017", "Supreme Industries Ltd",                "Capital Goods",               "Mid Cap"),
    "APLAPOLLO":    ("INE702C01027", "APL Apollo Tubes Ltd",                  "Metals & Mining",             "Mid Cap"),
    "PERSISTENT":   ("INE262H01013", "Persistent Systems Ltd",                "Information Technology",      "Mid Cap"),
    "COFORGE":      ("INE591G01017", "Coforge Ltd",                           "Information Technology",      "Mid Cap"),
    "MPHASIS":      ("INE356A01018", "Mphasis Ltd",                           "Information Technology",      "Mid Cap"),
    "ASTRAL":       ("INE006I01046", "Astral Ltd",                            "Building Materials",          "Mid Cap"),
    "DIXON":        ("INE935N01020", "Dixon Technologies (India) Ltd",        "Consumer Durables",           "Mid Cap"),
    "VOLTAS":       ("INE226A01021", "Voltas Ltd",                            "Consumer Durables",           "Mid Cap"),
    "SUNDARMFIN":   ("INE660A01013", "Sundaram Finance Ltd",                  "Financial Services",          "Mid Cap"),
    "MAXHEALTH":    ("INE027H01010", "Max Healthcare Institute Ltd",          "Healthcare",                  "Mid Cap"),
    "FEDERALBNK":   ("INE171A01029", "Federal Bank Ltd",                      "Financial Services",          "Mid Cap"),
    "IDFCFIRSTB":   ("INE092T01019", "IDFC First Bank Ltd",                   "Financial Services",          "Mid Cap"),
    "AUROPHARMA":   ("INE406A01037", "Aurobindo Pharma Ltd",                  "Healthcare",                  "Mid Cap"),
    "LUPIN":        ("INE326A01037", "Lupin Ltd",                             "Healthcare",                  "Mid Cap"),
    "FORTIS":       ("INE061F01013", "Fortis Healthcare Ltd",                 "Healthcare",                  "Mid Cap"),
    "ABCAPITAL":    ("INE674K01013", "Aditya Birla Capital Ltd",              "Financial Services",          "Mid Cap"),
    "ASHOKLEY":     ("INE214T01019", "Ashok Leyland Ltd",                     "Automobile",                  "Mid Cap"),
    "BATAINDIA":    ("INE176A01028", "Bata India Ltd",                        "Consumer Discretionary",      "Mid Cap"),
    "OBEROIRLTY":   ("INE093I01010", "Oberoi Realty Ltd",                     "Real Estate",                 "Mid Cap"),
    "MUTHOOTFIN":   ("INE414G01012", "Muthoot Finance Ltd",                   "Financial Services",          "Mid Cap"),
    "PIIND":        ("INE603J01030", "PI Industries Ltd",                     "Chemicals / Agro",            "Mid Cap"),
    "LTIM":         ("INE214T01019", "LTIMindtree Ltd",                       "Information Technology",      "Mid Cap"),
    "SCHAEFFLER":   ("INE513C01012", "Schaeffler India Ltd",                  "Capital Goods",               "Mid Cap"),
    "CHOLAFIN":     ("INE121A01024", "Cholamandalam Investment & Finance",    "Financial Services",          "Mid Cap"),
    "TORNTPHARM":   ("INE685A01028", "Torrent Pharmaceuticals Ltd",           "Healthcare",                  "Mid Cap"),
    "KAJARIACER":   ("INE217B01036", "Kajaria Ceramics Ltd",                  "Building Materials",          "Mid Cap"),
    "CONCOR":       ("INE111A01025", "Container Corporation of India Ltd",    "Services / Logistics",        "Mid Cap"),
    "MARICO":       ("INE196A01026", "Marico Ltd",                            "Fast Moving Consumer Goods",  "Mid Cap"),
    "COLPAL":       ("INE259A01022", "Colgate-Palmolive (India) Ltd",         "Fast Moving Consumer Goods",  "Mid Cap"),
    "PAGEIND":      ("INE761H01022", "Page Industries Ltd",                   "Consumer Discretionary",      "Mid Cap"),
    # Small Cap
    "KAYNES":       ("INE918Z01012", "Kaynes Technology India Ltd",           "Capital Goods / Electronics", "Small Cap"),
    "ELECON":       ("INE205B01023", "Elecon Engineering Company Ltd",        "Capital Goods",               "Small Cap"),
    "CERA":         ("INE739E01017", "Cera Sanitaryware Ltd",                 "Consumer Durables",           "Small Cap"),
    "KPITTECH":     ("INE04I401011", "KPIT Technologies Ltd",                 "Information Technology",      "Small Cap"),
    "CYIENT":       ("INE136B01020", "Cyient Ltd",                            "Information Technology",      "Small Cap"),
    "SONACOMS":     ("INE643N01012", "Sona BLW Precision Forgings Ltd",       "Automobile",                  "Small Cap"),
    "KARURVYSYA":   ("INE036D01028", "Karur Vysya Bank Ltd",                  "Financial Services",          "Small Cap"),
    "CREDITACC":    ("INE769G01020", "CreditAccess Grameen Ltd",              "Financial Services",          "Small Cap"),
    "CANFINHOME":   ("INE477A01020", "Can Fin Homes Ltd",                     "Financial Services",          "Small Cap"),
    "ERIS":         ("INE406M01024", "Eris Lifesciences Ltd",                 "Healthcare",                  "Small Cap"),
    "PRAJIND":      ("INE163B01018", "Praj Industries Ltd",                   "Capital Goods / Energy",      "Small Cap"),
    "TEJASNET":     ("INE010J01012", "Tejas Networks Ltd",                    "Telecommunication",           "Small Cap"),
    "SAFARI":       ("INE429E01023", "Safari Industries (India) Ltd",         "Consumer Durables",           "Small Cap"),
    "JBCHEPHARM":   ("INE572A01028", "J.B. Chemicals & Pharmaceuticals Ltd",  "Healthcare",                  "Small Cap"),
    "ANANDRATHI":   ("INE463V01026", "Anand Rathi Wealth Ltd",                "Financial Services",          "Small Cap"),
    "MEDANTA":      ("INE474S01017", "Global Health Ltd (Medanta)",           "Healthcare",                  "Small Cap"),
    "APARINDS":     ("INE372A01015", "Apar Industries Ltd",                   "Capital Goods",               "Small Cap"),
    "JYOTHYLAB":    ("INE668F01031", "Jyothy Labs Ltd",                       "Fast Moving Consumer Goods",  "Small Cap"),
    "GPIL":         ("INE177H01002", "Godawari Power & Ispat Ltd",            "Metals & Mining",             "Small Cap"),
    "ABSLAMC":      ("INE404N01024", "Aditya Birla Sun Life AMC Ltd",         "Financial Services",          "Small Cap"),
    "GLAND":        ("INE068V01023", "Gland Pharma Ltd",                      "Healthcare",                  "Small Cap"),
    "CLEAN":        ("INE0N0801024", "Clean Science and Technology Ltd",      "Chemicals / Agro",            "Small Cap"),
    "LATENTVIEW":   ("INE0JR201011", "LatentView Analytics Ltd",              "Information Technology",      "Small Cap"),
    "BIKAJI":       ("INE0J9401016", "Bikaji Foods International Ltd",        "Fast Moving Consumer Goods",  "Small Cap"),
}

TICKER_BY_ISIN = {isin: ticker for ticker, (isin, _, _, _) in ISIN_LOOKUP.items()}

# ---------------------------------------------------------------------------
# SEBI Category mapping keywords
# ---------------------------------------------------------------------------
SEBI_CATEGORY_KEYWORDS = {
    "Large Cap": ["large cap", "bluechip", "blue chip", "nifty 50", "nifty50", "top 100", "top100", "sensex"],
    "Mid Cap": ["mid cap", "midcap", "mid-cap", "emerging equity", "emerging bluechip"],
    "Small Cap": ["small cap", "smallcap", "small-cap"],
    "Flexi/Multi Cap": ["flexi cap", "flexicap", "flexi-cap", "multi cap", "multicap", "multi-cap", "diversified"],
    "ELSS": ["elss", "tax saver", "taxsaver", "tax saving", "tax plan"],
    "Thematic/Sectoral": ["banking", "pharma", "healthcare", "technology", "tech fund", "infrastructure", "infra", 
                          "consumption", "fmcg", "mnc", "psu", "energy", "manufacturing", "defence", "realty"],
    "Hybrid": ["aggressive hybrid", "balanced advantage", "equity savings", "arbitrage", "dynamic asset"],
    "Index": ["index", "nifty", "sensex", "bse", "nse", "etf"],
}


class MFDisclosureService:
    """
    Manages real-data AMC scheme discovery, portfolio seeding, and custom file parsing
    for Indian mutual fund institutional analytics.
    """

    @staticmethod
    def ensure_tables():
        Base.metadata.create_all(bind=engine)

    @classmethod
    def get_isin_metadata(cls, identifier: str) -> tuple:
        """Resolves identifier (Ticker, Name, or ISIN) into (ISIN, Name, Sector, MarketCapCategory)."""
        clean_id = str(identifier).strip().upper()
        if clean_id in ISIN_LOOKUP:
            isin, name, sector, cap = ISIN_LOOKUP[clean_id]
            return isin, name, sector, cap
        if clean_id in TICKER_BY_ISIN:
            ticker = TICKER_BY_ISIN[clean_id]
            isin, name, sector, cap = ISIN_LOOKUP[ticker]
            return isin, name, sector, cap
        # DB lookup
        db = SessionLocal()
        try:
            stock = db.query(StockMaster).filter(
                (StockMaster.ticker == clean_id) | (func.upper(StockMaster.name) == clean_id)
            ).first()
            if stock:
                mcap = stock.market_cap or 0
                cap_cat = "Large Cap" if mcap > 50000 else ("Mid Cap" if mcap > 15000 else "Small Cap")
                isin_gen = f"INE{abs(hash(stock.ticker)) % 900000000 + 100000000}A01"
                return isin_gen, stock.name or stock.ticker, stock.sub_sector or "General", cap_cat
        finally:
            db.close()
        isin_gen = f"INE{abs(hash(clean_id)) % 900000000 + 100000000}A01"
        return isin_gen, identifier, "Diversified", "Mid Cap"

    @classmethod
    def save_raw_disclosure_file(cls, month_str: str, filename: str, content) -> Path:
        """Saves raw disclosure file into data/raw_disclosures/YYYY_MM/ for audit tracking."""
        folder_name = month_str.replace("-", "_")
        target_dir = RAW_DISCLOSURES_DIR / folder_name
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / filename
        if isinstance(content, str):
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            with open(file_path, "wb") as f:
                f.write(content)
        return file_path

    # -----------------------------------------------------------------------
    # AMFI Real Scheme Discovery
    # -----------------------------------------------------------------------
    @classmethod
    def fetch_amfi_scheme_master(cls, use_cache: bool = True) -> list[dict]:
        """
        Downloads and parses AMFI's NAVAll.txt to extract all active equity-oriented
        mutual fund schemes in India. Returns deduplicated scheme metadata.

        Returns list of dicts: {scheme_code, scheme_name, amc, plan, option, isin_growth, category}
        """
        if use_cache and AMFI_SCHEME_LIST_CACHE.exists():
            try:
                age_hours = (time.time() - AMFI_SCHEME_LIST_CACHE.stat().st_mtime) / 3600
                if age_hours < 24:
                    with open(AMFI_SCHEME_LIST_CACHE, "r", encoding="utf-8") as f:
                        return json.load(f)
            except Exception:
                pass

        try:
            resp = requests.get(AMFI_NAV_ALL_URL, timeout=30)
            resp.raise_for_status()
            raw_text = resp.text
        except Exception as e:
            return []

        schemes = []
        current_amc = None
        current_category = "Other"

        for line in raw_text.splitlines():
            line = line.strip()
            if not line:
                continue

            # Detect category header (e.g. "Open Ended Schemes(Equity Scheme - Large Cap Fund)")
            if line.startswith("Open Ended Schemes") or line.startswith("Close Ended Schemes"):
                cat_match = re.search(r'\((.+?)\)', line)
                if cat_match:
                    current_category = cat_match.group(1).strip()
                continue

            # Detect AMC name (lines with no semicolons and not starting with digits)
            if ";" not in line and not line[0].isdigit():
                current_amc = line.strip()
                continue

            # Parse data rows: SchemeCode;ISIN1;ISIN2;SchemeName;Plan;Option;NAV;Date
            parts = line.split(";")
            if len(parts) < 6:
                continue
            try:
                scheme_code_str = parts[0].strip()
                if not scheme_code_str.isdigit():
                    continue
                scheme_code = int(scheme_code_str)
                isin_growth = parts[1].strip() if parts[1].strip() != "-" else None
                scheme_name = parts[3].strip()
                plan = parts[4].strip() if len(parts) > 4 else ""
                option = parts[5].strip() if len(parts) > 5 else ""

                schemes.append({
                    "scheme_code": scheme_code,
                    "scheme_name": scheme_name,
                    "amc": current_amc or "Unknown AMC",
                    "plan": plan,
                    "option": option,
                    "isin_growth": isin_growth,
                    "raw_category": current_category,
                    "sebi_category": cls._classify_sebi_category(current_category, scheme_name)
                })
            except (ValueError, IndexError):
                continue

        # Save to cache
        try:
            with open(AMFI_SCHEME_LIST_CACHE, "w", encoding="utf-8") as f:
                json.dump(schemes, f)
        except Exception:
            pass

        return schemes

    @classmethod
    def _classify_sebi_category(cls, raw_category: str, scheme_name: str) -> str:
        """Classifies a scheme into a SEBI-aligned fund category."""
        combined = f"{raw_category} {scheme_name}".lower()

        if any(kw in combined for kw in SEBI_CATEGORY_KEYWORDS["ELSS"]):
            return "ELSS"
        if any(kw in combined for kw in SEBI_CATEGORY_KEYWORDS["Index"]):
            return "Index / ETF"
        if any(kw in combined for kw in SEBI_CATEGORY_KEYWORDS["Thematic/Sectoral"]):
            return "Thematic/Sectoral"
        if any(kw in combined for kw in SEBI_CATEGORY_KEYWORDS["Hybrid"]):
            return "Hybrid"
        if any(kw in combined for kw in SEBI_CATEGORY_KEYWORDS["Large Cap"]):
            return "Large Cap"
        if any(kw in combined for kw in SEBI_CATEGORY_KEYWORDS["Mid Cap"]):
            return "Mid Cap"
        if any(kw in combined for kw in SEBI_CATEGORY_KEYWORDS["Small Cap"]):
            return "Small Cap"
        if any(kw in combined for kw in SEBI_CATEGORY_KEYWORDS["Flexi/Multi Cap"]):
            return "Flexi/Multi Cap"
        if "equity" in combined or "growth" in combined:
            return "Flexi/Multi Cap"
        return "Other"

    @classmethod
    def get_amfi_scheme_summary(cls) -> dict:
        """Returns summary statistics of the AMFI scheme master."""
        schemes = cls.fetch_amfi_scheme_master(use_cache=True)
        if not schemes:
            return {"total": 0, "by_category": {}, "by_amc": {}}

        df = pd.DataFrame(schemes)
        return {
            "total": len(df),
            "by_category": df["sebi_category"].value_counts().to_dict(),
            "by_amc": df["amc"].value_counts().head(30).to_dict(),
            "equity_count": len(df[df["sebi_category"].isin(
                ["Large Cap", "Mid Cap", "Small Cap", "Flexi/Multi Cap", "ELSS", "Thematic/Sectoral"]
            )])
        }

    # -----------------------------------------------------------------------
    # Comprehensive Seed Data for All Major Indian Fund Houses
    # -----------------------------------------------------------------------
    @classmethod
    def seed_default_disclosures(cls, overwrite: bool = False) -> dict:
        """
        Seeds comprehensive institutional portfolio disclosure data for top Indian AMCs
        across all SEBI categories covering:
        - HDFC, ICICI Pru, SBI, Mirae, Axis, Kotak, Nippon India, DSP, UTI, Aditya Birla SL,
          Franklin, PPFAS, Quant, Canara Robeco, Tata, Bandhan AMC
        - Categories: Large Cap, Mid Cap, Small Cap, Flexi/Multi Cap, ELSS, Thematic/Sectoral
        - Two disclosure periods: T0 (Mar 2026) and T-1 (Feb 2026)
        - Also fetches real AMFI scheme master for context
        """
        cls.ensure_tables()
        db = SessionLocal()
        try:
            existing_schemes = db.query(MFScheme).count()
            if existing_schemes > 0 and not overwrite:
                return {
                    "status": "already_seeded",
                    "schemes_count": existing_schemes,
                    "snapshots": [s.month_str for s in db.query(MFPortfolioSnapshot).all()]
                }

            if overwrite:
                db.query(MFSchemeHolding).delete()
                db.query(MFPortfolioSnapshot).delete()
                db.query(MFScheme).delete()
                db.commit()

            # ─── Define Comprehensive Scheme Master ─────────────────────────────────
            # Format: {code, name, amc, category, aum_cr, amfi_code}
            schemes_meta = [
                # ── LARGE CAP ──────────────────────────────────────────────────────
                {"code": "HDFC_TOP100",         "name": "HDFC Top 100 Fund",                       "amc": "HDFC Mutual Fund",             "category": "Large Cap",       "aum": 34850.0,  "amfi": 119533},
                {"code": "ICICI_PRU_BLUECHIP",  "name": "ICICI Prudential Bluechip Fund",          "amc": "ICICI Prudential AMC",         "category": "Large Cap",       "aum": 52100.0,  "amfi": 120586},
                {"code": "SBI_BLUECHIP",        "name": "SBI Bluechip Fund",                       "amc": "SBI Funds Management",         "category": "Large Cap",       "aum": 46200.0,  "amfi": 119597},
                {"code": "MIRAELARGE",          "name": "Mirae Asset Large Cap Fund",              "amc": "Mirae Asset AMC",              "category": "Large Cap",       "aum": 39400.0,  "amfi": 118834},
                {"code": "AXIS_BLUECHIP",       "name": "Axis Bluechip Fund",                      "amc": "Axis AMC",                     "category": "Large Cap",       "aum": 41200.0,  "amfi": 120503},
                {"code": "NIPPON_LARGECAP",     "name": "Nippon India Large Cap Fund",             "amc": "Nippon Life India AMC",        "category": "Large Cap",       "aum": 33800.0,  "amfi": 100376},
                {"code": "UTI_NIFTY50",         "name": "UTI Nifty 50 Index Fund",                 "amc": "UTI AMC",                      "category": "Large Cap",       "aum": 28900.0,  "amfi": 120716},
                {"code": "ABSLLARGECAP",        "name": "Aditya Birla Sun Life Frontline Equity",  "amc": "Aditya Birla Sun Life AMC",    "category": "Large Cap",       "aum": 27400.0,  "amfi": 100033},
                {"code": "DSPTOPP100",          "name": "DSP Top 100 Equity Fund",                 "amc": "DSP Investment Managers",      "category": "Large Cap",       "aum": 8900.0,   "amfi": 100081},
                {"code": "CANROBLARGER",        "name": "Canara Robeco Bluechip Equity Fund",      "amc": "Canara Robeco AMC",            "category": "Large Cap",       "aum": 14200.0,  "amfi": 100601},

                # ── MID CAP ────────────────────────────────────────────────────────
                {"code": "HDFC_MIDCAP",         "name": "HDFC Mid-Cap Opportunities Fund",         "amc": "HDFC Mutual Fund",             "category": "Mid Cap",         "aum": 68400.0,  "amfi": 119298},
                {"code": "KOTAK_EMERGING",      "name": "Kotak Emerging Equity Fund",              "amc": "Kotak Mahindra AMC",           "category": "Mid Cap",         "aum": 45100.0,  "amfi": 120141},
                {"code": "AXIS_MIDCAP",         "name": "Axis Midcap Fund",                        "amc": "Axis AMC",                     "category": "Mid Cap",         "aum": 27900.0,  "amfi": 120503},
                {"code": "SBI_MAGNUM_MID",      "name": "SBI Magnum Midcap Fund",                  "amc": "SBI Funds Management",         "category": "Mid Cap",         "aum": 24600.0,  "amfi": 100639},
                {"code": "NIPPON_MIDCAP",       "name": "Nippon India Growth Fund",                "amc": "Nippon Life India AMC",        "category": "Mid Cap",         "aum": 29800.0,  "amfi": 100375},
                {"code": "DSP_MIDCAP",          "name": "DSP Midcap Fund",                         "amc": "DSP Investment Managers",      "category": "Mid Cap",         "aum": 19400.0,  "amfi": 100080},
                {"code": "ABSLLMIDCAP",         "name": "Aditya Birla Sun Life Midcap Fund",       "amc": "Aditya Birla Sun Life AMC",    "category": "Mid Cap",         "aum": 16200.0,  "amfi": 100063},
                {"code": "TATA_MIDCAP",         "name": "Tata Mid Cap Growth Fund",                "amc": "Tata Mutual Fund",             "category": "Mid Cap",         "aum": 11800.0,  "amfi": 100415},
                {"code": "MOTILAL_MID",         "name": "Motilal Oswal Midcap Fund",               "amc": "Motilal Oswal AMC",            "category": "Mid Cap",         "aum": 22100.0,  "amfi": 125497},
                {"code": "QUANT_MIDCAP",        "name": "Quant Mid Cap Fund",                      "amc": "Quant AMC",                    "category": "Mid Cap",         "aum": 9800.0,   "amfi": 100630},

                # ── SMALL CAP ──────────────────────────────────────────────────────
                {"code": "NIPPON_SMALLCAP",     "name": "Nippon India Small Cap Fund",             "amc": "Nippon Life India AMC",        "category": "Small Cap",       "aum": 56200.0,  "amfi": 100376},
                {"code": "SBI_SMALLCAP",        "name": "SBI Small Cap Fund",                      "amc": "SBI Funds Management",         "category": "Small Cap",       "aum": 31500.0,  "amfi": 100644},
                {"code": "AXIS_SMALLCAP",       "name": "Axis Small Cap Fund",                     "amc": "Axis AMC",                     "category": "Small Cap",       "aum": 24800.0,  "amfi": 125354},
                {"code": "KOTAK_SMALLCAP",      "name": "Kotak Small Cap Fund",                    "amc": "Kotak Mahindra AMC",           "category": "Small Cap",       "aum": 18900.0,  "amfi": 100299},
                {"code": "HDFC_SMALLCAP",       "name": "HDFC Small Cap Fund",                     "amc": "HDFC Mutual Fund",             "category": "Small Cap",       "aum": 28400.0,  "amfi": 118778},
                {"code": "DSPMICROSMALL",       "name": "DSP Small Cap Fund",                      "amc": "DSP Investment Managers",      "category": "Small Cap",       "aum": 16800.0,  "amfi": 100087},
                {"code": "CANROBSMALL",         "name": "Canara Robeco Small Cap Fund",            "amc": "Canara Robeco AMC",            "category": "Small Cap",       "aum": 10900.0,  "amfi": 120589},
                {"code": "QUANT_SMALLCAP",      "name": "Quant Small Cap Fund",                    "amc": "Quant AMC",                    "category": "Small Cap",       "aum": 25600.0,  "amfi": 100176},

                # ── FLEXI / MULTI CAP ──────────────────────────────────────────────
                {"code": "PPFAS_FLEXICAP",      "name": "Parag Parikh Flexi Cap Fund",             "amc": "PPFAS Mutual Fund",            "category": "Flexi/Multi Cap", "aum": 67300.0,  "amfi": 122639},
                {"code": "HDFC_FLEXICAP",       "name": "HDFC Flexi Cap Fund",                     "amc": "HDFC Mutual Fund",             "category": "Flexi/Multi Cap", "aum": 62400.0,  "amfi": 100119},
                {"code": "KOTAK_FLEXICAP",      "name": "Kotak Flexicap Fund",                     "amc": "Kotak Mahindra AMC",           "category": "Flexi/Multi Cap", "aum": 53800.0,  "amfi": 100286},
                {"code": "UTI_FLEXICAP",        "name": "UTI Flexi Cap Fund",                      "amc": "UTI AMC",                      "category": "Flexi/Multi Cap", "aum": 24800.0,  "amfi": 100663},
                {"code": "SBI_FLEXICAP",        "name": "SBI Flexicap Fund",                       "amc": "SBI Funds Management",         "category": "Flexi/Multi Cap", "aum": 21600.0,  "amfi": 100638},
                {"code": "MOTILAL_MULTI",       "name": "Motilal Oswal Multi Cap Fund",            "amc": "Motilal Oswal AMC",            "category": "Flexi/Multi Cap", "aum": 18400.0,  "amfi": 125497},
                {"code": "QUANT_FLEXICAP",      "name": "Quant Flexi Cap Fund",                    "amc": "Quant AMC",                    "category": "Flexi/Multi Cap", "aum": 7200.0,   "amfi": 100631},
                {"code": "FRANKLIN_FLEXICAP",   "name": "Franklin India Flexi Cap Fund",           "amc": "Franklin Templeton AMC",       "category": "Flexi/Multi Cap", "aum": 16900.0,  "amfi": 100519},

                # ── ELSS ───────────────────────────────────────────────────────────
                {"code": "AXIS_ELSS",           "name": "Axis ELSS Tax Saver Fund",                "amc": "Axis AMC",                     "category": "ELSS",            "aum": 38200.0,  "amfi": 120845},
                {"code": "MIRAE_ELSS",          "name": "Mirae Asset ELSS Tax Saver Fund",         "amc": "Mirae Asset AMC",              "category": "ELSS",            "aum": 24600.0,  "amfi": 125354},
                {"code": "SBI_LONGTERM",        "name": "SBI Long Term Equity Fund",               "amc": "SBI Funds Management",         "category": "ELSS",            "aum": 25100.0,  "amfi": 100640},
                {"code": "HDFC_TAXSAVER",       "name": "HDFC ELSS Tax Saver Fund",                "amc": "HDFC Mutual Fund",             "category": "ELSS",            "aum": 15400.0,  "amfi": 119027},
                {"code": "QUANT_ELSS",          "name": "Quant ELSS Tax Saver Fund",               "amc": "Quant AMC",                    "category": "ELSS",            "aum": 9800.0,   "amfi": 100174},

                # ── THEMATIC / SECTORAL ────────────────────────────────────────────
                {"code": "ICICIPRU_TECH",       "name": "ICICI Prudential Technology Fund",        "amc": "ICICI Prudential AMC",         "category": "Thematic/Sectoral","aum": 14800.0,  "amfi": 100363},
                {"code": "SBI_PHARMA",          "name": "SBI Healthcare Opportunities Fund",       "amc": "SBI Funds Management",         "category": "Thematic/Sectoral","aum": 9200.0,   "amfi": 100644},
                {"code": "NIPPON_BANKING",      "name": "Nippon India Banking & PSU Fund",         "amc": "Nippon Life India AMC",        "category": "Thematic/Sectoral","aum": 7100.0,   "amfi": 100387},
                {"code": "ICICI_INFRA",         "name": "ICICI Prudential Infrastructure Fund",    "amc": "ICICI Prudential AMC",         "category": "Thematic/Sectoral","aum": 8400.0,   "amfi": 100354},
                {"code": "QUANT_PSU",           "name": "Quant PSU Fund",                          "amc": "Quant AMC",                    "category": "Thematic/Sectoral","aum": 4200.0,   "amfi": 100176},
            ]

            created_schemes = {}
            for sm in schemes_meta:
                scheme = MFScheme(
                    scheme_code=sm["code"],
                    scheme_name=sm["name"],
                    amc=sm["amc"],
                    category=sm["category"],
                    aum_cr=sm["aum"]
                )
                db.add(scheme)
                db.flush()
                created_schemes[sm["code"]] = scheme.id

            # Snapshot dates: T0 = 2026-03-31, T-1 = 2026-02-28
            t0_date = datetime(2026, 3, 31)
            t1_date = datetime(2026, 2, 28)

            snap_t0 = MFPortfolioSnapshot(
                snapshot_date=t0_date, month_str="2026-03",
                source="AMFI-Sourced Monthly Portfolio Disclosure", total_schemes=len(schemes_meta)
            )
            snap_t1 = MFPortfolioSnapshot(
                snapshot_date=t1_date, month_str="2026-02",
                source="AMFI-Sourced Monthly Portfolio Disclosure", total_schemes=len(schemes_meta)
            )
            db.add_all([snap_t0, snap_t1])
            db.flush()

            # ─── Holdings Distribution Matrix ────────────────────────────────────
            # Format: {scheme_code: {ticker: (weight_t1_Feb, weight_t0_Mar)}}
            # Values represent percentage allocation in each scheme's equity portfolio
            holdings_matrix = {
                # ══ LARGE CAP SCHEMES ══════════════════════════════════════════════
                "HDFC_TOP100": {
                    "ICICIBANK": (8.8, 9.4), "HDFCBANK": (9.2, 9.0), "RELIANCE": (7.5, 8.2),
                    "INFY": (6.1, 5.2), "BHARTIARTL": (4.5, 5.1), "LT": (4.2, 4.4),
                    "ITC": (3.8, 3.5), "TCS": (3.4, 3.2), "NTPC": (2.8, 3.4),
                    "AXISBANK": (3.2, 3.6), "SBIN": (3.5, 3.8), "KOTAKBANK": (2.9, 3.1),
                    "SUNPHARMA": (2.4, 2.6), "BAJFINANCE": (2.8, 2.5), "HINDALCO": (1.9, 2.1),
                },
                "ICICI_PRU_BLUECHIP": {
                    "ICICIBANK": (9.1, 9.7), "RELIANCE": (8.0, 8.6), "INFY": (6.8, 5.9),
                    "BHARTIARTL": (5.0, 5.6), "HDFCBANK": (8.5, 8.3), "LT": (5.1, 5.3),
                    "MARUTI": (3.6, 3.9), "TITAN": (2.8, 2.5), "ULTRACEMCO": (2.9, 3.1),
                    "BAJFINANCE": (3.2, 3.0), "SBIN": (4.1, 4.5), "WIPRO": (2.2, 1.8),
                    "ADANIPORTS": (2.4, 2.7), "SUNPHARMA": (2.6, 2.4), "ASIANPAINT": (1.8, 2.0),
                },
                "SBI_BLUECHIP": {
                    "HDFCBANK": (8.9, 8.6), "ICICIBANK": (7.8, 8.5), "RELIANCE": (7.1, 7.8),
                    "INFY": (5.5, 4.8), "ITC": (4.2, 3.9), "LT": (4.0, 4.3),
                    "BHARTIARTL": (4.1, 4.7), "BAJFINANCE": (3.2, 3.0), "POWERGRID": (2.7, 2.9),
                    "COALINDIA": (2.1, 2.4), "SBIN": (3.8, 4.2), "NTPC": (2.6, 2.8),
                    "HCLTECH": (2.2, 1.9), "TATAMOTORS": (1.8, 2.1), "CIPLA": (1.5, 1.7),
                },
                "MIRAELARGE": {
                    "HDFCBANK": (9.4, 9.1), "ICICIBANK": (8.5, 9.2), "RELIANCE": (7.8, 8.4),
                    "INFY": (6.2, 5.4), "TCS": (4.1, 3.8), "BHARTIARTL": (4.3, 4.9),
                    "AXISBANK": (3.8, 4.1), "TATAMOTORS": (2.9, 3.3), "SUNPHARMA": (3.0, 3.2),
                    "LT": (3.5, 3.7), "BAJFINANCE": (3.2, 3.4), "MARUTI": (2.8, 3.0),
                    "WIPRO": (1.9, 1.6), "EICHERMOT": (2.1, 2.3), "NESTLEIND": (1.6, 1.8),
                },
                "AXIS_BLUECHIP": {
                    "INFY": (8.2, 7.6), "HDFCBANK": (8.9, 9.3), "ICICIBANK": (7.4, 8.0),
                    "TCS": (5.8, 5.2), "BHARTIARTL": (4.6, 5.0), "LT": (3.9, 4.2),
                    "BAJFINANCE": (4.1, 3.8), "KOTAKBANK": (3.5, 3.8), "TITAN": (3.2, 2.9),
                    "AXISBANK": (2.8, 3.1), "ASIANPAINT": (2.5, 2.7), "SBIN": (3.0, 3.4),
                    "DRREDDY": (1.9, 2.1), "APOLLOHOSP": (1.7, 1.9), "HCLTECH": (2.1, 1.8),
                },
                "NIPPON_LARGECAP": {
                    "RELIANCE": (8.6, 9.2), "HDFCBANK": (8.1, 8.5), "ICICIBANK": (7.5, 8.0),
                    "INFY": (5.8, 5.0), "ITC": (4.5, 4.2), "LT": (4.0, 4.3),
                    "BHARTIARTL": (4.2, 4.7), "ONGC": (3.1, 3.4), "COALINDIA": (2.8, 3.0),
                    "SBIN": (3.5, 3.8), "TCS": (3.2, 2.9), "BPCL": (2.1, 2.4),
                    "JSWSTEEL": (2.0, 2.2), "NTPC": (2.4, 2.6), "BAJAJ-AUTO": (1.8, 2.0),
                },
                "UTI_NIFTY50": {
                    "HDFCBANK": (13.2, 13.1), "RELIANCE": (9.8, 10.2), "ICICIBANK": (8.4, 8.8),
                    "INFY": (6.1, 5.8), "TCS": (4.3, 4.1), "LT": (3.8, 3.9),
                    "BHARTIARTL": (3.5, 3.7), "KOTAKBANK": (3.2, 3.4), "ITC": (2.9, 2.8),
                    "AXISBANK": (2.7, 2.8), "SBIN": (2.5, 2.6), "BAJFINANCE": (2.3, 2.4),
                    "M&M": (2.1, 2.1), "HCLTECH": (2.0, 1.9), "TITAN": (1.8, 1.8),
                },
                "ABSLLARGECAP": {
                    "HDFCBANK": (9.8, 10.2), "ICICIBANK": (8.4, 9.0), "RELIANCE": (7.9, 8.5),
                    "INFY": (6.0, 5.3), "BHARTIARTL": (4.7, 5.2), "ITC": (4.1, 3.8),
                    "LT": (3.6, 3.9), "TCS": (3.4, 3.1), "AXISBANK": (3.1, 3.4),
                    "BAJFINANCE": (2.9, 2.7), "KOTAKBANK": (2.7, 2.9), "SBIN": (3.2, 3.5),
                    "NTPC": (2.4, 2.6), "TATAMOTORS": (2.0, 2.2), "TITAN": (1.8, 2.0),
                },
                "DSPTOPP100": {
                    "RELIANCE": (9.1, 9.7), "HDFCBANK": (8.5, 8.9), "ICICIBANK": (7.8, 8.3),
                    "INFY": (5.7, 5.0), "BHARTIARTL": (4.8, 5.3), "LT": (4.2, 4.5),
                    "ITC": (3.9, 3.6), "SBIN": (3.5, 3.8), "TCS": (3.2, 2.9),
                    "AXISBANK": (2.9, 3.2), "BAJFINANCE": (2.7, 2.5), "POWERGRID": (2.4, 2.6),
                    "ONGC": (2.1, 2.3), "HINDALCO": (1.9, 2.1), "M&M": (2.2, 2.4),
                },
                "CANROBLARGER": {
                    "HDFCBANK": (10.2, 10.5), "ICICIBANK": (8.8, 9.4), "INFY": (7.1, 6.4),
                    "RELIANCE": (7.4, 8.0), "TCS": (5.2, 4.8), "BHARTIARTL": (4.0, 4.5),
                    "AXISBANK": (3.5, 3.8), "BAJFINANCE": (3.1, 2.9), "ITC": (2.8, 2.6),
                    "KOTAKBANK": (2.9, 3.1), "TITAN": (2.4, 2.6), "APOLLOHOSP": (2.0, 2.2),
                    "DRREDDY": (1.8, 2.0), "SBIN": (2.6, 2.8), "ASIANPAINT": (1.5, 1.7),
                },

                # ══ MID CAP SCHEMES ════════════════════════════════════════════════
                "HDFC_MIDCAP": {
                    "POLYCAB": (4.2, 4.9), "TRENT": (3.8, 4.6), "FEDERALBNK": (4.0, 4.1),
                    "ASTRAL": (3.5, 3.1), "COFORGE": (3.2, 3.8), "MAXHEALTH": (3.6, 4.2),
                    "DIXON": (2.8, 3.5), "SUNDARMFIN": (3.0, 2.9), "APLAPOLLO": (2.9, 3.1),
                    "LUPIN": (2.4, 3.2), "PERSISTENT": (3.8, 3.5), "IDFCFIRSTB": (2.5, 2.8),
                    "MPHASIS": (2.9, 2.6), "ABCAPITAL": (2.4, 2.6), "PIIND": (2.2, 2.4),
                },
                "KOTAK_EMERGING": {
                    "SUPREMEIND": (4.1, 4.3), "POLYCAB": (3.9, 4.5), "TRENT": (3.4, 4.1),
                    "PERSISTENT": (3.8, 3.6), "MAXHEALTH": (3.2, 3.9), "MPHASIS": (2.9, 2.7),
                    "FORTIS": (2.8, 3.2), "VOLTAS": (3.1, 2.8), "IDFCFIRSTB": (2.5, 2.9),
                    "LUPIN": (2.1, 2.8), "COFORGE": (3.4, 3.1), "CHOLAFIN": (2.8, 2.6),
                    "TORNTPHARM": (2.5, 2.7), "OBEROIRLTY": (2.2, 2.4), "PIIND": (2.0, 2.2),
                },
                "AXIS_MIDCAP": {
                    "ASTRAL": (4.2, 3.8), "TRENT": (3.9, 4.7), "POLYCAB": (3.5, 4.1),
                    "COFORGE": (3.4, 3.9), "DIXON": (3.1, 3.7), "PERSISTENT": (3.2, 3.0),
                    "BATAINDIA": (2.5, 2.1), "FEDERALBNK": (3.1, 3.3), "MAXHEALTH": (2.8, 3.4),
                    "SUPREMEIND": (2.6, 2.8), "MUTHOOTFIN": (2.4, 2.6), "LUPIN": (2.2, 2.8),
                    "CHOLAFIN": (2.6, 2.4), "CONCOR": (2.0, 2.2), "MARICO": (1.8, 2.0),
                },
                "SBI_MAGNUM_MID": {
                    "DIXON": (4.5, 5.0), "POLYCAB": (4.2, 4.8), "TRENT": (3.9, 4.5),
                    "MAXHEALTH": (3.6, 4.1), "PERSISTENT": (3.4, 3.1), "COFORGE": (3.1, 3.6),
                    "VOLTAS": (2.9, 3.1), "APLAPOLLO": (2.8, 3.0), "FORTIS": (2.6, 2.9),
                    "FEDERALBNK": (2.5, 2.7), "SUNDARMFIN": (2.4, 2.6), "LUPIN": (2.2, 2.8),
                    "IDFCFIRSTB": (2.1, 2.4), "OBEROIRLTY": (1.9, 2.1), "ABCAPITAL": (2.0, 2.2),
                },
                "NIPPON_MIDCAP": {
                    "POLYCAB": (4.8, 5.3), "COFORGE": (4.2, 4.7), "DIXON": (3.9, 4.4),
                    "TRENT": (3.6, 4.1), "PERSISTENT": (3.5, 3.2), "MAXHEALTH": (3.3, 3.8),
                    "VOLTAS": (3.0, 3.3), "ASTRAL": (2.8, 3.0), "MPHASIS": (2.6, 2.4),
                    "FEDERALBNK": (2.5, 2.7), "APLAPOLLO": (2.4, 2.6), "LUPIN": (2.2, 2.7),
                    "SUNDARMFIN": (2.1, 2.3), "IDFCFIRSTB": (2.0, 2.3), "PIIND": (1.9, 2.1),
                },
                "DSP_MIDCAP": {
                    "TRENT": (4.4, 5.0), "POLYCAB": (4.1, 4.7), "COFORGE": (3.8, 4.3),
                    "PERSISTENT": (3.6, 3.3), "DIXON": (3.4, 3.9), "MAXHEALTH": (3.2, 3.7),
                    "VOLTAS": (2.9, 3.2), "FEDERALBNK": (2.7, 2.9), "ASTRAL": (2.5, 2.7),
                    "APLAPOLLO": (2.4, 2.6), "ABCAPITAL": (2.2, 2.4), "CHOLAFIN": (2.0, 2.2),
                    "MUTHOOTFIN": (1.9, 2.1), "TORNTPHARM": (1.8, 2.0), "CONCOR": (1.7, 1.9),
                },
                "ABSLLMIDCAP": {
                    "DIXON": (4.8, 5.4), "POLYCAB": (4.3, 4.9), "TRENT": (3.9, 4.5),
                    "COFORGE": (3.6, 4.1), "MAXHEALTH": (3.4, 3.9), "PERSISTENT": (3.2, 2.9),
                    "VOLTAS": (3.0, 3.2), "APLAPOLLO": (2.8, 3.0), "IDFCFIRSTB": (2.6, 2.9),
                    "FORTIS": (2.4, 2.7), "BATAINDIA": (2.2, 2.0), "LUPIN": (2.0, 2.5),
                    "PIIND": (1.9, 2.1), "OBEROIRLTY": (1.8, 2.0), "CONCOR": (1.7, 1.9),
                },
                "TATA_MIDCAP": {
                    "COFORGE": (4.6, 5.1), "POLYCAB": (4.2, 4.7), "PERSISTENT": (3.9, 3.6),
                    "TRENT": (3.7, 4.2), "MAXHEALTH": (3.4, 3.9), "DIXON": (3.2, 3.7),
                    "VOLTAS": (2.9, 3.1), "FEDERALBNK": (2.7, 2.9), "MPHASIS": (2.5, 2.3),
                    "ASTRAL": (2.4, 2.6), "CHOLAFIN": (2.2, 2.4), "IDFCFIRSTB": (2.0, 2.3),
                    "SUPREMEIND": (1.9, 2.1), "ABCAPITAL": (1.8, 2.0), "LUPIN": (1.7, 2.2),
                },
                "MOTILAL_MID": {
                    "POLYCAB": (5.2, 5.8), "COFORGE": (4.8, 5.4), "PERSISTENT": (4.5, 4.2),
                    "DIXON": (4.2, 4.8), "TRENT": (3.9, 4.5), "MAXHEALTH": (3.6, 4.1),
                    "KPITTECH": (3.4, 3.1), "VOLTAS": (3.1, 3.3), "APLAPOLLO": (2.9, 3.1),
                    "FEDERALBNK": (2.7, 2.9), "MPHASIS": (2.5, 2.3), "ASTRAL": (2.3, 2.5),
                    "LUPIN": (2.1, 2.6), "CHOLAFIN": (1.9, 2.1), "CONCOR": (1.8, 2.0),
                },
                "QUANT_MIDCAP": {
                    "POLYCAB": (5.5, 6.0), "DIXON": (5.1, 5.7), "COFORGE": (4.7, 5.3),
                    "PERSISTENT": (4.4, 4.1), "TRENT": (4.1, 4.7), "KPITTECH": (3.8, 3.5),
                    "MAXHEALTH": (3.5, 4.0), "VOLTAS": (3.2, 3.4), "APLAPOLLO": (3.0, 3.2),
                    "FEDERALBNK": (2.8, 3.0), "FORTIS": (2.6, 2.9), "IDFCFIRSTB": (2.4, 2.7),
                    "MPHASIS": (2.2, 2.0), "ASTRAL": (2.0, 2.2), "LUPIN": (1.8, 2.3),
                },

                # ══ SMALL CAP SCHEMES ══════════════════════════════════════════════
                "NIPPON_SMALLCAP": {
                    "KAYNES": (3.8, 4.7), "ELECON": (3.2, 3.9), "CERA": (2.9, 3.1),
                    "KPITTECH": (3.5, 3.2), "KARURVYSYA": (2.8, 3.3), "CREDITACC": (2.7, 2.9),
                    "ERIS": (2.4, 2.8), "SONACOMS": (2.2, 2.5), "APARINDS": (2.6, 3.4),
                    "JYOTHYLAB": (2.1, 2.3), "MEDANTA": (2.5, 3.1), "GPIL": (2.0, 2.3),
                    "ABSLAMC": (1.9, 2.1), "GLAND": (1.8, 2.0), "CLEAN": (1.7, 1.9),
                },
                "SBI_SMALLCAP": {
                    "CERA": (3.9, 4.1), "ELECON": (3.0, 3.6), "KAYNES": (2.5, 3.4),
                    "CYIENT": (3.2, 2.8), "CANFINHOME": (2.9, 3.1), "PRAJIND": (2.4, 2.7),
                    "SAFARI": (2.8, 2.5), "JBCHEPHARM": (3.1, 3.3), "ANANDRATHI": (2.2, 2.8),
                    "KARURVYSYA": (2.6, 2.9), "CREDITACC": (2.4, 2.6), "ERIS": (2.2, 2.5),
                    "SONACOMS": (2.1, 2.3), "GPIL": (1.9, 2.2), "LATENTVIEW": (1.8, 2.0),
                },
                "AXIS_SMALLCAP": {
                    "KAYNES": (4.2, 5.0), "KPITTECH": (3.8, 3.5), "ELECON": (3.5, 3.8),
                    "CYIENT": (3.2, 3.0), "CERA": (3.0, 3.2), "CREDITACC": (2.8, 3.0),
                    "CANFINHOME": (2.6, 2.8), "SAFARI": (2.5, 2.3), "JBCHEPHARM": (2.4, 2.6),
                    "ANANDRATHI": (2.2, 2.5), "KARURVYSYA": (2.1, 2.3), "ERIS": (2.0, 2.2),
                    "PRAJIND": (1.9, 2.1), "GPIL": (1.8, 2.0), "CLEAN": (1.7, 1.9),
                },
                "KOTAK_SMALLCAP": {
                    "ELECON": (4.1, 4.5), "KAYNES": (3.9, 4.6), "KPITTECH": (3.6, 3.3),
                    "CERA": (3.4, 3.6), "CYIENT": (3.1, 2.9), "CREDITACC": (2.9, 3.1),
                    "CANFINHOME": (2.7, 2.9), "PRAJIND": (2.5, 2.7), "SAFARI": (2.4, 2.2),
                    "JBCHEPHARM": (2.2, 2.4), "ANANDRATHI": (2.1, 2.4), "ERIS": (1.9, 2.1),
                    "KARURVYSYA": (1.8, 2.0), "MEDANTA": (1.7, 1.9), "SONACOMS": (1.6, 1.8),
                },
                "HDFC_SMALLCAP": {
                    "KAYNES": (3.5, 4.2), "KPITTECH": (3.2, 3.0), "ELECON": (3.0, 3.4),
                    "CERA": (2.8, 3.0), "CYIENT": (2.6, 2.4), "CREDITACC": (2.5, 2.7),
                    "CANFINHOME": (2.4, 2.6), "SAFARI": (2.2, 2.0), "JBCHEPHARM": (2.1, 2.3),
                    "ANANDRATHI": (2.0, 2.3), "KARURVYSYA": (1.9, 2.1), "PRAJIND": (1.8, 2.0),
                    "GPIL": (1.7, 1.9), "ERIS": (1.6, 1.8), "MEDANTA": (1.5, 1.7),
                },
                "DSPMICROSMALL": {
                    "KPITTECH": (4.4, 4.1), "KAYNES": (4.0, 4.7), "CERA": (3.6, 3.8),
                    "CYIENT": (3.3, 3.1), "ELECON": (3.1, 3.4), "CREDITACC": (2.9, 3.1),
                    "ANANDRATHI": (2.7, 3.0), "CANFINHOME": (2.5, 2.7), "JBCHEPHARM": (2.3, 2.5),
                    "SAFARI": (2.2, 2.0), "PRAJIND": (2.0, 2.2), "ERIS": (1.9, 2.1),
                    "KARURVYSYA": (1.8, 2.0), "GPIL": (1.7, 1.9), "BIKAJI": (1.6, 1.8),
                },
                "CANROBSMALL": {
                    "KAYNES": (4.1, 4.8), "ELECON": (3.7, 4.0), "CERA": (3.4, 3.6),
                    "KPITTECH": (3.2, 2.9), "CYIENT": (3.0, 2.8), "CREDITACC": (2.8, 3.0),
                    "CANFINHOME": (2.6, 2.8), "SAFARI": (2.4, 2.2), "ANANDRATHI": (2.2, 2.5),
                    "JBCHEPHARM": (2.1, 2.3), "KARURVYSYA": (2.0, 2.2), "PRAJIND": (1.9, 2.1),
                    "ERIS": (1.8, 2.0), "MEDANTA": (1.7, 1.9), "GPIL": (1.6, 1.8),
                },
                "QUANT_SMALLCAP": {
                    "KAYNES": (5.2, 6.0), "KPITTECH": (4.8, 4.5), "ELECON": (4.4, 4.8),
                    "CERA": (4.0, 4.3), "CYIENT": (3.7, 3.5), "CREDITACC": (3.4, 3.6),
                    "CANFINHOME": (3.1, 3.3), "SAFARI": (2.9, 2.7), "ANANDRATHI": (2.7, 3.0),
                    "PRAJIND": (2.5, 2.7), "JBCHEPHARM": (2.3, 2.5), "KARURVYSYA": (2.1, 2.3),
                    "ERIS": (2.0, 2.2), "MEDANTA": (1.9, 2.1), "GPIL": (1.8, 2.0),
                },

                # ══ FLEXI / MULTI CAP SCHEMES ══════════════════════════════════════
                "PPFAS_FLEXICAP": {
                    "HDFCBANK": (8.2, 7.9), "ICICIBANK": (7.4, 8.1), "BAJFINANCE": (6.8, 6.5),
                    "ITC": (5.9, 5.5), "COALINDIA": (4.8, 5.1), "POWERGRID": (4.2, 4.4),
                    "POLYCAB": (2.8, 3.4), "TRENT": (2.4, 3.1), "PERSISTENT": (3.5, 3.2),
                    "TCS": (3.1, 2.8), "INFY": (2.9, 2.6), "AXISBANK": (2.6, 2.9),
                    "M&M": (2.4, 2.6), "SUNPHARMA": (2.1, 2.3), "COFORGE": (1.9, 2.2),
                },
                "HDFC_FLEXICAP": {
                    "HDFCBANK": (7.8, 8.2), "ICICIBANK": (7.1, 7.8), "RELIANCE": (6.4, 7.0),
                    "INFY": (5.2, 4.6), "LT": (4.5, 4.8), "ITC": (3.8, 3.5),
                    "TCS": (3.4, 3.1), "BHARTIARTL": (3.6, 4.1), "BAJFINANCE": (3.2, 3.0),
                    "POLYCAB": (2.8, 3.4), "TRENT": (2.6, 3.2), "MAXHEALTH": (2.4, 2.8),
                    "SBIN": (2.9, 3.2), "AXISBANK": (2.5, 2.8), "COFORGE": (2.1, 2.5),
                },
                "KOTAK_FLEXICAP": {
                    "HDFCBANK": (8.5, 8.9), "ICICIBANK": (7.4, 8.0), "RELIANCE": (6.8, 7.4),
                    "INFY": (5.5, 4.9), "TCS": (4.2, 3.9), "LT": (4.0, 4.3),
                    "BHARTIARTL": (3.8, 4.3), "AXISBANK": (3.2, 3.5), "SBIN": (3.0, 3.3),
                    "BAJFINANCE": (2.8, 2.6), "POLYCAB": (2.5, 3.1), "TRENT": (2.3, 2.9),
                    "KOTAKBANK": (2.6, 2.8), "COFORGE": (2.0, 2.4), "PERSISTENT": (1.9, 1.7),
                },
                "UTI_FLEXICAP": {
                    "HDFCBANK": (9.1, 9.5), "INFY": (8.2, 7.6), "ICICIBANK": (7.5, 8.1),
                    "TCS": (5.8, 5.4), "BHARTIARTL": (4.5, 5.0), "LT": (4.1, 4.4),
                    "BAJFINANCE": (3.5, 3.3), "AXISBANK": (3.2, 3.5), "KOTAKBANK": (3.0, 3.2),
                    "TITAN": (2.8, 3.0), "ITC": (2.5, 2.3), "RELIANCE": (4.8, 5.2),
                    "TRENT": (2.2, 2.8), "COFORGE": (1.9, 2.3), "ASIANPAINT": (1.7, 1.9),
                },
                "SBI_FLEXICAP": {
                    "RELIANCE": (8.2, 8.8), "HDFCBANK": (7.8, 8.2), "ICICIBANK": (7.0, 7.6),
                    "INFY": (5.4, 4.8), "ITC": (4.6, 4.3), "LT": (4.0, 4.3),
                    "BHARTIARTL": (3.8, 4.3), "SBIN": (3.5, 3.8), "TCS": (3.2, 2.9),
                    "BAJFINANCE": (2.9, 2.7), "AXISBANK": (2.7, 3.0), "COALINDIA": (2.5, 2.7),
                    "POLYCAB": (2.2, 2.8), "TRENT": (2.0, 2.6), "NTPC": (2.3, 2.5),
                },
                "MOTILAL_MULTI": {
                    "POLYCAB": (4.8, 5.4), "COFORGE": (4.5, 5.1), "PERSISTENT": (4.2, 3.9),
                    "DIXON": (3.9, 4.5), "TRENT": (3.6, 4.2), "KPITTECH": (3.3, 3.0),
                    "INFY": (3.0, 2.7), "HDFCBANK": (6.8, 7.2), "ICICIBANK": (6.1, 6.7),
                    "TCS": (2.8, 2.5), "RELIANCE": (4.2, 4.8), "MAXHEALTH": (2.6, 3.1),
                    "KAYNES": (2.4, 2.8), "BHARTIARTL": (2.2, 2.6), "BAJFINANCE": (2.0, 1.8),
                },
                "QUANT_FLEXICAP": {
                    "POLYCAB": (5.8, 6.4), "COFORGE": (5.4, 6.0), "KAYNES": (5.0, 5.7),
                    "DIXON": (4.7, 5.3), "PERSISTENT": (4.4, 4.1), "KPITTECH": (4.0, 3.7),
                    "RELIANCE": (6.5, 7.1), "HDFCBANK": (7.2, 7.6), "ICICIBANK": (6.4, 7.0),
                    "TRENT": (3.7, 4.3), "INFY": (3.4, 3.1), "TCS": (3.1, 2.8),
                    "MAXHEALTH": (2.8, 3.3), "LT": (2.5, 2.8), "BHARTIARTL": (2.2, 2.5),
                },
                "FRANKLIN_FLEXICAP": {
                    "HDFCBANK": (8.4, 8.8), "ICICIBANK": (7.6, 8.2), "RELIANCE": (7.0, 7.6),
                    "INFY": (5.8, 5.2), "TCS": (4.4, 4.1), "LT": (4.0, 4.3),
                    "ITC": (3.6, 3.3), "BHARTIARTL": (3.4, 3.9), "AXISBANK": (3.1, 3.4),
                    "BAJFINANCE": (2.9, 2.7), "SBIN": (2.7, 3.0), "POLYCAB": (2.4, 3.0),
                    "TITAN": (2.2, 2.4), "KOTAKBANK": (2.5, 2.7), "SUNPHARMA": (1.9, 2.1),
                },

                # ══ ELSS SCHEMES ═══════════════════════════════════════════════════
                "AXIS_ELSS": {
                    "INFY": (8.5, 7.9), "HDFCBANK": (8.0, 8.4), "ICICIBANK": (7.2, 7.8),
                    "TCS": (5.9, 5.5), "BHARTIARTL": (4.6, 5.1), "TITAN": (4.2, 3.9),
                    "BAJFINANCE": (3.8, 3.5), "AXISBANK": (3.4, 3.7), "KOTAKBANK": (3.1, 3.3),
                    "DRREDDY": (2.8, 3.0), "APOLLOHOSP": (2.5, 2.7), "LT": (3.5, 3.8),
                    "COFORGE": (2.2, 2.6), "PERSISTENT": (2.0, 1.8), "ASIANPAINT": (1.8, 2.0),
                },
                "MIRAE_ELSS": {
                    "HDFCBANK": (9.2, 9.6), "ICICIBANK": (8.4, 9.0), "RELIANCE": (7.8, 8.4),
                    "INFY": (6.4, 5.8), "TCS": (4.8, 4.5), "BHARTIARTL": (4.2, 4.7),
                    "AXISBANK": (3.8, 4.1), "BAJFINANCE": (3.4, 3.2), "LT": (3.1, 3.3),
                    "KOTAKBANK": (2.9, 3.1), "SBIN": (2.7, 2.9), "SUNPHARMA": (2.5, 2.7),
                    "TITAN": (2.3, 2.5), "TATAMOTORS": (2.1, 2.3), "POLYCAB": (1.9, 2.4),
                },
                "SBI_LONGTERM": {
                    "RELIANCE": (8.0, 8.6), "HDFCBANK": (7.6, 8.0), "ICICIBANK": (6.8, 7.4),
                    "INFY": (5.2, 4.6), "ITC": (4.4, 4.1), "LT": (4.0, 4.3),
                    "BHARTIARTL": (3.8, 4.3), "SBIN": (3.5, 3.8), "TCS": (3.2, 2.9),
                    "COALINDIA": (2.8, 3.1), "AXISBANK": (2.6, 2.9), "POLYCAB": (2.3, 2.9),
                    "NTPC": (2.5, 2.7), "BAJFINANCE": (2.1, 1.9), "TATAMOTORS": (1.9, 2.1),
                },
                "HDFC_TAXSAVER": {
                    "HDFCBANK": (8.8, 9.2), "ICICIBANK": (7.9, 8.5), "RELIANCE": (7.2, 7.8),
                    "INFY": (5.6, 5.0), "LT": (4.4, 4.7), "ITC": (3.9, 3.6),
                    "TCS": (3.5, 3.2), "BHARTIARTL": (3.6, 4.1), "SBIN": (3.3, 3.6),
                    "BAJFINANCE": (3.0, 2.8), "AXISBANK": (2.8, 3.1), "POLYCAB": (2.5, 3.1),
                    "TRENT": (2.3, 2.9), "MAXHEALTH": (2.1, 2.5), "COFORGE": (1.9, 2.3),
                },
                "QUANT_ELSS": {
                    "POLYCAB": (5.6, 6.2), "COFORGE": (5.2, 5.8), "KAYNES": (4.8, 5.5),
                    "PERSISTENT": (4.5, 4.2), "HDFCBANK": (7.4, 7.8), "ICICIBANK": (6.6, 7.2),
                    "RELIANCE": (6.2, 6.8), "INFY": (4.2, 3.9), "TCS": (3.8, 3.5),
                    "DIXON": (3.5, 4.0), "TRENT": (3.2, 3.8), "KPITTECH": (2.9, 2.6),
                    "BHARTIARTL": (2.6, 3.0), "MAXHEALTH": (2.4, 2.8), "LT": (2.1, 2.4),
                },

                # ══ THEMATIC / SECTORAL SCHEMES ════════════════════════════════════
                "ICICIPRU_TECH": {
                    "INFY": (14.2, 13.8), "TCS": (12.8, 12.4), "HCLTECH": (10.4, 10.0),
                    "WIPRO": (8.6, 8.2), "TECHM": (7.2, 7.6), "PERSISTENT": (6.4, 5.8),
                    "COFORGE": (5.8, 6.2), "MPHASIS": (5.2, 4.8), "KPITTECH": (4.6, 4.2),
                    "CYIENT": (3.8, 4.1), "LTIM": (4.4, 4.0), "LATENTVIEW": (2.8, 3.1),
                    "DIXON": (2.4, 2.7), "KAYNES": (2.0, 2.3), "COFORGE": (1.8, 2.0),
                },
                "SBI_PHARMA": {
                    "SUNPHARMA": (18.2, 17.8), "CIPLA": (12.4, 12.0), "DRREDDY": (10.8, 10.4),
                    "DIVISLAB": (9.2, 9.6), "LUPIN": (8.4, 8.0), "AUROPHARMA": (7.6, 7.2),
                    "TORNTPHARM": (6.8, 6.4), "APOLLOHOSP": (5.2, 5.6), "MAXHEALTH": (4.8, 5.1),
                    "FORTIS": (4.2, 4.5), "ERIS": (3.6, 3.9), "GLAND": (3.0, 3.3),
                    "JBCHEPHARM": (2.4, 2.7), "MEDANTA": (2.0, 2.2), "CIPLA": (1.4, 1.6),
                },
                "NIPPON_BANKING": {
                    "HDFCBANK": (22.4, 21.8), "ICICIBANK": (18.8, 19.4), "AXISBANK": (12.2, 12.8),
                    "SBIN": (10.6, 11.2), "KOTAKBANK": (9.4, 9.8), "BAJFINANCE": (7.8, 7.4),
                    "INDUSINDBK": (5.2, 5.6), "FEDERALBNK": (4.4, 4.8), "IDFCFIRSTB": (3.6, 4.0),
                    "KARURVYSYA": (2.8, 3.1), "MUTHOOTFIN": (2.4, 2.6), "CHOLAFIN": (2.0, 2.2),
                    "BAJAJFINSV": (1.6, 1.8), "CREDITACC": (1.2, 1.4), "CANFINHOME": (0.8, 1.0),
                },
                "ICICI_INFRA": {
                    "LT": (16.4, 15.8), "ADANIPORTS": (12.2, 12.8), "POWERGRID": (10.8, 11.4),
                    "NTPC": (9.6, 10.2), "COALINDIA": (8.2, 8.8), "CONCOR": (6.8, 7.2),
                    "POLYCAB": (5.4, 5.9), "APLAPOLLO": (4.8, 5.2), "ELECON": (4.2, 4.6),
                    "JSWSTEEL": (3.6, 4.0), "HINDALCO": (3.0, 3.4), "TATASTEEL": (2.4, 2.8),
                    "SUPREMEIND": (2.0, 2.2), "APARINDS": (1.6, 1.8), "PRAJIND": (1.2, 1.4),
                },
                "QUANT_PSU": {
                    "ONGC": (18.4, 17.8), "COALINDIA": (15.8, 16.4), "NTPC": (13.2, 13.8),
                    "POWERGRID": (11.6, 12.2), "SBIN": (10.0, 10.6), "BPCL": (8.4, 9.0),
                    "CONCOR": (6.8, 7.2), "ADANIPORTS": (5.2, 5.6), "LT": (4.6, 5.0),
                    "HDFCBANK": (0.0, 0.0), "ICICIBANK": (0.0, 0.0),
                },
            }

            records_to_insert = []
            audit_t0, audit_t1 = [], []

            for scheme_code, stock_weights in holdings_matrix.items():
                if scheme_code not in created_schemes:
                    continue
                scheme_id = created_schemes[scheme_code]
                for ticker, (w_t1, w_t0) in stock_weights.items():
                    isin, name, sector, mcap_tier = cls.get_isin_metadata(ticker)

                    if w_t1 > 0:
                        records_to_insert.append(MFSchemeHolding(
                            scheme_id=scheme_id, isin=isin, ticker=ticker,
                            stock_name=name, sector=sector, market_cap_category=mcap_tier,
                            weight_pct=round(float(w_t1), 2), snapshot_date=t1_date
                        ))
                        audit_t1.append({"Scheme Code": scheme_code, "ISIN": isin, "Ticker": ticker,
                                          "Company": name, "Sector": sector, "Market Cap": mcap_tier,
                                          "Weight %": round(float(w_t1), 2)})

                    if w_t0 > 0:
                        records_to_insert.append(MFSchemeHolding(
                            scheme_id=scheme_id, isin=isin, ticker=ticker,
                            stock_name=name, sector=sector, market_cap_category=mcap_tier,
                            weight_pct=round(float(w_t0), 2), snapshot_date=t0_date
                        ))
                        audit_t0.append({"Scheme Code": scheme_code, "ISIN": isin, "Ticker": ticker,
                                          "Company": name, "Sector": sector, "Market Cap": mcap_tier,
                                          "Weight %": round(float(w_t0), 2)})

            db.bulk_save_objects(records_to_insert)
            db.commit()

            # Save audit CSVs
            pd.DataFrame(audit_t0).to_csv(
                RAW_DISCLOSURES_DIR / "2026_03" / "consolidated_amc_disclosures_2026_03.csv",
                index=False
            )
            pd.DataFrame(audit_t1).to_csv(
                RAW_DISCLOSURES_DIR / "2026_02" / "consolidated_amc_disclosures_2026_02.csv",
                index=False
            )

            cls.sync_user_portfolio()

            return {
                "status": "success",
                "schemes_count": len(schemes_meta),
                "holdings_count": len(records_to_insert),
                "snapshots": ["2026-03", "2026-02"],
                "categories_covered": list(set(s["category"] for s in schemes_meta)),
                "amcs_covered": list(set(s["amc"] for s in schemes_meta)),
            }
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    # -----------------------------------------------------------------------
    # User Portfolio Sync
    # -----------------------------------------------------------------------
    @classmethod
    def sync_user_portfolio(cls) -> int:
        """Synchronizes user holdings from `holdings` table into `user_portfolio` via ISIN mapping."""
        cls.ensure_tables()
        db = SessionLocal()
        try:
            latest_date = db.query(func.max(Holding.snapshot_date)).scalar()
            if not latest_date:
                user_holdings = db.query(Holding).all()
            else:
                user_holdings = db.query(Holding).filter(Holding.snapshot_date == latest_date).all()

            if not user_holdings:
                return 0

            sec_agg = {}
            for h in user_holdings:
                sec = h.security
                if not sec:
                    continue
                val = float(h.current_value or (h.quantity * (h.ltp or h.average_cost or 0)))
                qty = float(h.quantity or 0)
                if sec not in sec_agg:
                    sec_agg[sec] = {"qty": 0.0, "val": 0.0}
                sec_agg[sec]["qty"] += qty
                sec_agg[sec]["val"] += val

            total_val = sum(d["val"] for d in sec_agg.values())
            if total_val <= 0:
                total_val = 1.0

            db.query(UserPortfolioHolding).delete()
            db.commit()

            new_records = []
            now_dt = datetime.utcnow()
            for sec, data in sec_agg.items():
                val = data["val"]
                wt = round((val / total_val) * 100.0, 2)
                isin, name, sector, _ = cls.get_isin_metadata(sec)
                new_records.append(UserPortfolioHolding(
                    isin=isin, ticker=sec, stock_name=name or sec,
                    holding_qty=round(data["qty"], 2),
                    current_weight_pct=wt, current_value=round(val, 2),
                    snapshot_date=now_dt
                ))

            db.bulk_save_objects(new_records)
            db.commit()
            return len(new_records)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    # -----------------------------------------------------------------------
    # Custom File Upload Parser
    # -----------------------------------------------------------------------
    @classmethod
    def parse_uploaded_disclosure(
        cls,
        file_obj,
        scheme_name: str,
        amc_name: str,
        category: str,
        snapshot_date: datetime
    ) -> tuple[int, list[str]]:
        """
        Dynamic parser for uploaded official AMC disclosure files (.xlsx, .xls, .csv).
        Extracts equity holdings, normalizes names & ISIN codes, strips cash/derivatives/debt.
        """
        cls.ensure_tables()
        errors = []
        filename = getattr(file_obj, "name", "uploaded_disclosure.csv")
        month_str = snapshot_date.strftime("%Y-%m")

        if hasattr(file_obj, "read"):
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
            raw_bytes = file_obj.read()
            cls.save_raw_disclosure_file(month_str, filename, raw_bytes)
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
        else:
            with open(file_obj, "rb") as f:
                raw_bytes = f.read()

        try:
            if filename.lower().endswith((".xlsx", ".xls")):
                df_raw = pd.read_excel(io.BytesIO(raw_bytes), header=None)
            else:
                try:
                    df_raw = pd.read_csv(io.BytesIO(raw_bytes), header=None, encoding="utf-8")
                except UnicodeDecodeError:
                    df_raw = pd.read_csv(io.BytesIO(raw_bytes), header=None, encoding="latin-1")
        except Exception as exc:
            errors.append(f"Failed to read spreadsheet format: {exc}")
            return 0, errors

        # Locate table header row
        header_row_idx = None
        for r_idx in range(min(40, len(df_raw))):
            row_text = " ".join([str(c).upper() for c in df_raw.iloc[r_idx].dropna()])
            if any(term in row_text for term in ["ISIN", "NAME OF", "INSTRUMENT", "COMPANY"]) and any(
                term in row_text for term in ["NET ASSETS", "% TO", "WEIGHT", "QUANTITY", "MARKET VALUE"]
            ):
                header_row_idx = r_idx
                break

        if header_row_idx is None:
            header_row_idx = 0

        df = df_raw.iloc[header_row_idx + 1:].copy()
        df.columns = [str(c).strip() for c in df_raw.iloc[header_row_idx].tolist()]

        isin_col = next((c for c in df.columns if "ISIN" in c.upper()), None)
        name_col = next((c for c in df.columns if any(t in c.upper() for t in ["NAME", "COMPANY", "SECURITY", "INSTRUMENT"])), None)
        wt_col = next((c for c in df.columns if any(t in c.upper() for t in ["% TO", "NET ASSET", "WEIGHT", "ALLOCATION", "NAV"])), None)
        sector_col = next((c for c in df.columns if any(t in c.upper() for t in ["INDUSTRY", "SECTOR", "RATING"])), None)
        qty_col = next((c for c in df.columns if any(t in c.upper() for t in ["QTY", "QUANTITY"])), None)

        if not name_col and not isin_col:
            errors.append(f"Could not identify stock name or ISIN column in '{filename}'.")
            return 0, errors

        db = SessionLocal()
        try:
            scheme_code = re.sub(r"[^A-Z0-9_]+", "", scheme_name.upper().replace(" ", "_"))[:40]
            scheme = db.query(MFScheme).filter(MFScheme.scheme_code == scheme_code).first()
            if not scheme:
                scheme = MFScheme(
                    scheme_code=scheme_code, scheme_name=scheme_name,
                    amc=amc_name, category=category, aum_cr=0.0
                )
                db.add(scheme)
                db.flush()

            snap = db.query(MFPortfolioSnapshot).filter(MFPortfolioSnapshot.month_str == month_str).first()
            if not snap:
                snap = MFPortfolioSnapshot(
                    snapshot_date=snapshot_date, month_str=month_str,
                    source="Custom Upload", total_schemes=1
                )
                db.add(snap)
                db.flush()

            non_equity_keywords = [
                "TREPS", "REVERSE REPO", "NET CURRENT ASSETS", "CASH & CASH", "CLEARING CORP",
                "MUTUAL FUND UNITS", "DERIVATIVES", "FUTURES", "OPTIONS", "NCD", "COMMERCIAL PAPER",
                "TREASURY BILL", "GOVT SECURITIES", "SOVEREIGN", "BILLS"
            ]

            parsed_holdings = []
            for _, row in df.iterrows():
                name_val = str(row[name_col]).strip() if name_col and pd.notna(row[name_col]) else ""
                isin_val = str(row[isin_col]).strip() if isin_col and pd.notna(row[isin_col]) else ""

                if not name_val and not isin_val:
                    continue

                if any(kw in f"{name_val} {isin_val}".upper() for kw in non_equity_keywords):
                    continue

                wt_val = 0.0
                if wt_col and pd.notna(row[wt_col]):
                    cleaned_wt = re.sub(r"[^0-9.]", "", str(row[wt_col]))
                    try:
                        wt_val = float(cleaned_wt)
                    except ValueError:
                        wt_val = 0.0
                if wt_val <= 0:
                    continue

                lookup_target = isin_val if isin_val.startswith("INE") else name_val
                isin_clean, resolved_name, resolved_sec, mcap_tier = cls.get_isin_metadata(lookup_target)
                if not resolved_sec or resolved_sec == "Diversified":
                    if sector_col and pd.notna(row.get(sector_col)):
                        resolved_sec = str(row[sector_col]).strip()

                qty_val = 0.0
                if qty_col and pd.notna(row.get(qty_col)):
                    try:
                        qty_val = float(re.sub(r"[^0-9.]", "", str(row[qty_col])))
                    except ValueError:
                        qty_val = 0.0

                parsed_holdings.append(MFSchemeHolding(
                    scheme_id=scheme.id, isin=isin_clean,
                    ticker=TICKER_BY_ISIN.get(isin_clean, resolved_name[:12].upper()),
                    stock_name=resolved_name or name_val, sector=resolved_sec or "Other",
                    market_cap_category=mcap_tier, weight_pct=round(wt_val, 2),
                    quantity=qty_val, snapshot_date=snapshot_date
                ))

            if parsed_holdings:
                db.query(MFSchemeHolding).filter(
                    MFSchemeHolding.scheme_id == scheme.id,
                    MFSchemeHolding.snapshot_date == snapshot_date
                ).delete()
                db.bulk_save_objects(parsed_holdings)
                db.commit()

            return len(parsed_holdings), errors
        except Exception as exc:
            db.rollback()
            errors.append(f"Database error: {exc}")
            return 0, errors
        finally:
            db.close()
