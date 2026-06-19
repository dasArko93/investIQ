import io
import os
import zipfile
import pandas as pd
from datetime import datetime
from database.models import MFHolding
from database.db import SessionLocal

class MFHoldingService:
    @staticmethod
    def load_from_db() -> dict:
        """Load all mf holdings from sqlite db and pivot them back into wide format DataFrames."""
        db = SessionLocal()
        try:
            rows = db.query(MFHolding).all()
        finally:
            db.close()

        if not rows:
            return {}

        records = []
        for r in rows:
            records.append({
                "Fund": r.fund_name,
                "Sector": r.sector,
                "Date": r.date,
                "Allocation": r.allocation
            })
        df = pd.DataFrame(records)

        mf_holdings = {}
        for fund_name, group in df.groupby("Fund"):
            pivoted = group.pivot(index="Sector", columns="Date", values="Allocation").reset_index()
            pivoted = pivoted.rename(columns={"Sector": "Holding Type"})
            
            # Sort columns chronologically if possible
            date_cols = [c for c in pivoted.columns if c != "Holding Type"]
            try:
                sorted_cols = sorted(date_cols, key=lambda d: pd.to_datetime(d, format="%d-%b-%y"))
                pivoted = pivoted[["Holding Type"] + sorted_cols]
            except Exception:
                pass
                
            mf_holdings[fund_name] = pivoted
        return mf_holdings

    @staticmethod
    def save_to_db(fund_name: str, df: pd.DataFrame):
        """Save a mutual fund holding wide DataFrame to the database in long format."""
        db = SessionLocal()
        try:
            # Delete existing rows for this fund
            db.query(MFHolding).filter(MFHolding.fund_name == fund_name).delete()
            db.commit()
        except Exception:
            db.rollback()
            raise

        date_cols = [c for c in df.columns if c != "Holding Type"]
        records = []
        for _, row in df.iterrows():
            sector = row["Holding Type"]
            for date_col in date_cols:
                records.append(
                    MFHolding(
                        fund_name=fund_name,
                        sector=sector,
                        date=date_col,
                        allocation=float(row[date_col])
                    )
                )
        try:
            db.bulk_save_objects(records)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def clear_all_from_db():
        """Clear all mutual fund holding records from the database."""
        db = SessionLocal()
        try:
            db.query(MFHolding).delete()
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def parse_tickertape_file(uploaded_file) -> tuple[str, pd.DataFrame]:
        """
        Parses a Tickertape 'Holding Pattern History' CSV/TXT file.
        Returns (fund_name, dataframe) where dataframe has columns:
            Holding Type | <date1> | <date2> | ...
        """
        if hasattr(uploaded_file, "read"):
            raw_bytes = uploaded_file.read()
            name = getattr(uploaded_file, "name", "unknown.csv")
        else:
            with open(uploaded_file, "rb") as f:
                raw_bytes = f.read()
            name = os.path.basename(uploaded_file)

        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = raw_bytes.decode("latin-1")

        lines = text.splitlines()

        # ── Extract fund name from header lines ──────────────────────────────────
        fund_name = name.replace(".csv", "").replace(".txt", "")
        for line in lines[:10]:
            stripped = line.strip()
            if stripped.lower().startswith("for:"):
                candidate = stripped[4:].strip().strip('"').strip()
                if candidate:
                    fund_name = candidate
                break

        # ── Find the CSV body (starts with "Holding Type") ───────────────────────
        csv_start = None
        for idx, line in enumerate(lines):
            if line.strip().lower().startswith("holding type"):
                csv_start = idx
                break

        if csv_start is None:
            raise ValueError(
                f"Could not find 'Holding Type' header row in file '{name}'. "
                "Please ensure it is a valid Tickertape Holding Pattern export."
            )

        csv_body = "\n".join(lines[csv_start:])
        df = pd.read_csv(io.StringIO(csv_body))

        # ── Clean column names ───────────────────────────────────────────────────
        df.columns = [c.strip().strip('"') for c in df.columns]
        df["Holding Type"] = df["Holding Type"].astype(str).str.strip().str.strip('"')

        # ── Convert date columns to numeric ──────────────────────────────────────
        date_cols = [c for c in df.columns if c != "Holding Type"]
        for col in date_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

        df = df[df["Holding Type"].notna() & (df["Holding Type"] != "")]

        return fund_name, df

    @classmethod
    def process_zip_file(cls, uploaded_zip) -> tuple[int, list[str]]:
        """
        Parses a ZIP backup containing multiple fund CSV/TXT files and saves them to the DB.
        Returns (loaded_count, errors_list)
        """
        errors = []
        loaded = 0
        
        # If it's a Streamlit UploadedFile or file-like object
        if hasattr(uploaded_zip, "read"):
            # If the file-like object was already read, reset pointer if possible
            if hasattr(uploaded_zip, "seek"):
                uploaded_zip.seek(0)
            zip_file = zipfile.ZipFile(uploaded_zip)
        else:
            zip_file = zipfile.ZipFile(uploaded_zip, 'r')
            
        with zip_file as zf:
            for info in zf.infolist():
                if info.filename.endswith("/") or info.filename.startswith("__MACOSX") or os.path.basename(info.filename).startswith("."):
                    continue
                if info.filename.endswith(".csv") or info.filename.endswith(".txt"):
                    try:
                        content = zf.read(info.filename)
                        
                        class MockFile:
                            def __init__(self, name, content):
                                self.name = name
                                self.content = content
                            def read(self):
                                return self.content
                                
                        mock_f = MockFile(os.path.basename(info.filename), content)
                        fund_name, df = cls.parse_tickertape_file(mock_f)
                        cls.save_to_db(fund_name, df)
                        loaded += 1
                    except Exception as e:
                        errors.append(f"{info.filename}: {e}")
        return loaded, errors
