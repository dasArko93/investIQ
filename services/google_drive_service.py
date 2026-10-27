import os
import sys
import json
import shutil
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from database.db import DATA_DIR

logger = logging.getLogger("investiq.gdrive")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
CONFIG_DIR.mkdir(exist_ok=True)
GDRIVE_DIR = CONFIG_DIR / "gdrive"
GDRIVE_DIR.mkdir(exist_ok=True)

GDRIVE_CONFIG_FILE = CONFIG_DIR / "gdrive_config.json"
DEFAULT_SERVICE_ACCOUNT_FILE = GDRIVE_DIR / "gdrive_service_account.json"
LEGACY_SERVICE_ACCOUNT_FILE = CONFIG_DIR / "gdrive_service_account.json"
LOCAL_DB_PATH = DATA_DIR / "investiq.db"
REMOTE_BACKUP_FILENAME = "investiq_backup.db"
DEFAULT_FOLDER_ID = "1atBhonsk_qdG7KW9zShYCppmtWYvxAmO"

# Scopes required for Drive file operations
SCOPES = ["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]


class GoogleDriveService:
    """
    Manages automated Google Drive backup and session startup synchronization
    for InvestIQ's SQLite database.
    
    Supports:
      1. Google Service Account (via JSON file under config/gdrive/ or Streamlit secrets)
      2. Configurable Google Drive Folder ID
      3. Auto-backup of investiq_backup.db whenever new holdings are uploaded
      4. Auto-restore of investiq_backup.db upon session startup
    """

    @classmethod
    def resolve_service_account_file(cls, path_hint: Optional[str] = None) -> Optional[Path]:
        """
        Resolves the service account JSON file needed for Google Drive backup.
        By default, it refers to the JSON file present in the 'config/gdrive/' folder,
        with fallback to 'config/'.
        """
        # If an explicit path is provided, try resolving it first
        if path_hint:
            p = Path(path_hint)
            candidates = [
                p,
                PROJECT_ROOT / p,
                CONFIG_DIR / p,
                GDRIVE_DIR / p,
            ]
            for cand in candidates:
                try:
                    if cand.is_file():
                        return cand.resolve()
                except Exception:
                    pass

        # 1. PRIMARY: Check config/gdrive/ folder
        if GDRIVE_DIR.exists():
            # Check standard file names
            for name in ["gdrive_service_account.json", "service_account.json", "credentials.json"]:
                target = GDRIVE_DIR / name
                if target.is_file():
                    return target.resolve()

            # Scan any *.json file in config/gdrive/
            try:
                for jf in GDRIVE_DIR.glob("*.json"):
                    if "config" in jf.name.lower():
                        continue
                    try:
                        with open(jf, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, dict) and ("client_email" in data or data.get("type") == "service_account"):
                                return jf.resolve()
                    except Exception:
                        pass
                # If there are any json files in config/gdrive/, return the first one
                gdrive_jsons = list(GDRIVE_DIR.glob("*.json"))
                if gdrive_jsons:
                    return gdrive_jsons[0].resolve()
            except Exception:
                pass

        # 2. FALLBACK: Check config/ folder
        if LEGACY_SERVICE_ACCOUNT_FILE.is_file():
            return LEGACY_SERVICE_ACCOUNT_FILE.resolve()

        if CONFIG_DIR.exists():
            for name in ["service_account.json", "credentials.json"]:
                target = CONFIG_DIR / name
                if target.is_file():
                    return target.resolve()

            try:
                for jf in CONFIG_DIR.glob("*.json"):
                    if "config" in jf.name.lower():
                        continue
                    try:
                        with open(jf, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, dict) and ("client_email" in data or data.get("type") == "service_account"):
                                return jf.resolve()
                    except Exception:
                        pass
            except Exception:
                pass

        return None

    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Loads configuration from secrets, env vars, or config/gdrive_config.json."""
        resolved_sa = cls.resolve_service_account_file()
        config = {
            "folder_id": DEFAULT_FOLDER_ID,
            "service_account_file": str(resolved_sa) if resolved_sa else "",
            "service_account_json_raw": "",
            "auto_backup_enabled": True,
            "auto_restore_enabled": True,
        }

        # 1. Check Streamlit secrets
        try:
            import streamlit as st
            if hasattr(st, "secrets"):
                # Case A: [google_drive] table
                if "google_drive" in st.secrets:
                    sec = st.secrets["google_drive"]
                    for k in ["folder_id", "service_account_file", "auto_backup_enabled", "auto_restore_enabled"]:
                        if k in sec:
                            config[k] = sec[k]
                    if "type" in sec and sec.get("type") == "service_account":
                        config["service_account_json_raw"] = json.dumps(dict(sec))
                    if "service_account" in sec:
                        sa_val = sec["service_account"]
                        if isinstance(sa_val, dict):
                            config["service_account_json_raw"] = json.dumps(dict(sa_val))
                        elif isinstance(sa_val, str):
                            config["service_account_json_raw"] = sa_val

                # Case B: [gdrive_service_account] table
                for key_name in ["gdrive_service_account", "gdrive", "service_account"]:
                    if key_name in st.secrets and not config.get("service_account_json_raw"):
                        val = st.secrets[key_name]
                        if isinstance(val, dict) and "client_email" in val:
                            config["service_account_json_raw"] = json.dumps(dict(val))
                        elif isinstance(val, str) and "client_email" in val:
                            config["service_account_json_raw"] = val

                # Case C: String key
                for str_key in ["GDRIVE_SERVICE_ACCOUNT_JSON", "gdrive_service_account_json", "SERVICE_ACCOUNT_JSON"]:
                    if str_key in st.secrets and not config.get("service_account_json_raw"):
                        val = st.secrets[str_key]
                        if isinstance(val, str) and "client_email" in val:
                            config["service_account_json_raw"] = val
        except Exception:
            pass

        # 2. Check local gdrive_config.json
        if GDRIVE_CONFIG_FILE.exists():
            try:
                with open(GDRIVE_CONFIG_FILE, "r", encoding="utf-8") as f:
                    file_conf = json.load(f)
                    for k, v in file_conf.items():
                        if v:
                            config[k] = v
            except Exception as e:
                logger.warning(f"Failed reading {GDRIVE_CONFIG_FILE}: {e}")

        # 3. Check environment variables
        env_folder = os.environ.get("GDRIVE_FOLDER_ID")
        if env_folder:
            config["folder_id"] = env_folder

        env_sa = os.environ.get("GDRIVE_SERVICE_ACCOUNT_FILE")
        if env_sa:
            config["service_account_file"] = env_sa

        # 4. Resolve service account file (prioritizing config/gdrive/)
        if not config.get("service_account_json_raw"):
            resolved = cls.resolve_service_account_file(config.get("service_account_file"))
            if resolved:
                config["service_account_file"] = str(resolved)
            elif not config.get("service_account_file"):
                config["service_account_file"] = str(DEFAULT_SERVICE_ACCOUNT_FILE)

        return config

    @classmethod
    def save_config(cls, folder_id: str, auto_backup: bool = True, auto_restore: bool = True, sa_file_path: str = "") -> bool:
        """Persists Google Drive configuration to config/gdrive_config.json."""
        current = cls.get_config()
        current["folder_id"] = folder_id.strip()
        current["auto_backup_enabled"] = bool(auto_backup)
        current["auto_restore_enabled"] = bool(auto_restore)
        if sa_file_path:
            current["service_account_file"] = sa_file_path.strip()
        elif not current.get("service_account_file"):
            current["service_account_file"] = "config/gdrive/gdrive_service_account.json"

        try:
            with open(GDRIVE_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(current, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to write config: {e}")
            return False

    @classmethod
    def save_service_account_json(cls, json_content: str) -> Tuple[bool, str]:
        """Saves uploaded service account JSON key to config/gdrive/gdrive_service_account.json."""
        try:
            parsed = json.loads(json_content) if isinstance(json_content, str) else json_content
            if not isinstance(parsed, dict) or "client_email" not in parsed:
                return False, "Invalid service account JSON: missing 'client_email' field."

            # Save in config/gdrive/ (PRIMARY)
            GDRIVE_DIR.mkdir(parents=True, exist_ok=True)
            with open(DEFAULT_SERVICE_ACCOUNT_FILE, "w", encoding="utf-8") as f:
                json.dump(parsed, f, indent=2)

            # Also mirror to config/ for backwards compatibility
            try:
                with open(LEGACY_SERVICE_ACCOUNT_FILE, "w", encoding="utf-8") as f:
                    json.dump(parsed, f, indent=2)
            except Exception:
                pass

            # Update config with relative path inside config/gdrive/
            rel_path = "config/gdrive/gdrive_service_account.json"
            cls.save_config(folder_id=cls.get_config().get("folder_id", ""), sa_file_path=rel_path)
            return True, f"Service account key saved for: {parsed.get('client_email')}"
        except Exception as e:
            return False, f"Failed parsing JSON key: {e}"

    @classmethod
    def is_configured(cls) -> bool:
        """Checks whether Google Drive credentials and folder_id are present."""
        cfg = cls.get_config()
        has_folder = bool(cfg.get("folder_id"))
        sa_resolved = cls.resolve_service_account_file(cfg.get("service_account_file"))
        has_credentials = bool(cfg.get("service_account_json_raw")) or (
            sa_resolved is not None and sa_resolved.exists()
        )
        return has_folder and has_credentials

    @classmethod
    def _build_drive_service(cls):
        """Constructs and returns Google Drive API v3 resource client."""
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        cfg = cls.get_config()
        sa_resolved = cls.resolve_service_account_file(cfg.get("service_account_file"))

        if cfg.get("service_account_json_raw"):
            info = json.loads(cfg["service_account_json_raw"])
            creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        elif sa_resolved and sa_resolved.exists():
            creds = service_account.Credentials.from_service_account_file(str(sa_resolved), scopes=SCOPES)
        else:
            raise ValueError(
                "No valid Google Service Account credentials found. "
                "Ensure your service account JSON file is present under 'config/gdrive/' or 'config/'."
            )

        return build("drive", "v3", credentials=creds, cache_discovery=False)


    @classmethod
    def test_connection(cls) -> Dict[str, Any]:
        """Validates credentials and tests folder read/write access."""
        if not cls.is_configured():
            return {"status": "not_configured", "message": "Google Drive credentials or Folder ID missing."}

        try:
            service = cls._build_drive_service()
            folder_id = cls.get_config()["folder_id"]

            # Verify folder exists & accessible
            folder_meta = service.files().get(
                fileId=folder_id,
                fields="id, name, mimeType, capabilities"
            ).execute()

            # Query files inside the folder
            query = f"'{folder_id}' in parents and trashed = false"
            results = service.files().list(
                q=query,
                spaces="drive",
                fields="files(id, name, modifiedTime, size)",
                pageSize=20
            ).execute()

            files = results.get("files", [])
            backup_file = next((f for f in files if f["name"] == REMOTE_BACKUP_FILENAME), None)

            return {
                "status": "connected",
                "folder_name": folder_meta.get("name", "InvestIQ Folder"),
                "folder_id": folder_id,
                "backup_found": bool(backup_file),
                "backup_meta": backup_file,
                "total_files_in_folder": len(files)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # -----------------------------------------------------------------------
    # Automated Backup & Upload
    # -----------------------------------------------------------------------
    @classmethod
    def auto_backup_db(cls, local_db_path: Path = None) -> Dict[str, Any]:
        """
        Backs up local SQLite database to Google Drive as 'investiq_backup.db'.
        Safe operation: uses SQLite's backup API or file copy to prevent dirty reads.
        """
        cfg = cls.get_config()
        if not cfg.get("auto_backup_enabled", True):
            return {"status": "skipped", "reason": "auto_backup_disabled"}

        if not cls.is_configured():
            return {"status": "skipped", "reason": "not_configured"}

        db_path = Path(local_db_path or LOCAL_DB_PATH)
        if not db_path.exists():
            return {"status": "error", "message": f"Local database not found at {db_path}"}

        try:
            from googleapiclient.http import MediaFileUpload

            service = cls._build_drive_service()
            folder_id = cfg["folder_id"]

            # Create a clean, consistent snapshot using SQLite vacuum/backup
            snapshot_dir = DATA_DIR / "snapshots"
            snapshot_dir.mkdir(exist_ok=True)
            snapshot_path = snapshot_dir / f"investiq_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

            # Safe SQLite backup
            source_conn = sqlite3.connect(str(db_path))
            dest_conn = sqlite3.connect(str(snapshot_path))
            with dest_conn:
                source_conn.backup(dest_conn)
            dest_conn.close()
            source_conn.close()

            # Search if investiq_backup.db already exists in this folder
            q = f"'{folder_id}' in parents and name = '{REMOTE_BACKUP_FILENAME}' and trashed = false"
            res = service.files().list(q=q, fields="files(id, name)").execute()
            existing_files = res.get("files", [])

            media = MediaFileUpload(str(snapshot_path), mimetype="application/x-sqlite3", resumable=True)

            if existing_files:
                file_id = existing_files[0]["id"]
                updated = service.files().update(
                    fileId=file_id,
                    media_body=media,
                    fields="id, name, modifiedTime, size"
                ).execute()
                action = "updated"
            else:
                file_metadata = {
                    "name": REMOTE_BACKUP_FILENAME,
                    "parents": [folder_id],
                    "description": "InvestIQ Automated SQLite Database Backup"
                }
                updated = service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields="id, name, modifiedTime, size"
                ).execute()
                action = "created"

            # Clean up local temporary snapshot
            try:
                snapshot_path.unlink()
            except Exception:
                pass

            file_size_kb = round(int(updated.get("size", 0)) / 1024, 1) if updated.get("size") else 0.0

            result = {
                "status": "success",
                "action": action,
                "file_id": updated.get("id"),
                "file_name": updated.get("name"),
                "modified_time": updated.get("modifiedTime"),
                "size_kb": file_size_kb,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            logger.info(f"Google Drive auto-backup succeeded: {result}")
            return result

        except Exception as e:
            logger.error(f"Google Drive auto-backup failed: {e}")
            return {"status": "error", "message": str(e)}

    # -----------------------------------------------------------------------
    # Automated Restore upon Session Startup
    # -----------------------------------------------------------------------
    @classmethod
    def auto_restore_db(cls, target_db_path: Path = None, force: bool = False) -> Dict[str, Any]:
        """
        Fetches 'investiq_backup.db' from Google Drive.
        Restores it locally if force=True, remote is newer, or local database has no holdings.
        Uses SQLite native backup API to avoid Windows file-locking or rename errors.
        """
        cfg = cls.get_config()
        if not force and not cfg.get("auto_restore_enabled", True):
            return {"status": "skipped", "reason": "auto_restore_disabled"}

        if not cls.is_configured():
            return {"status": "skipped", "reason": "not_configured"}

        db_path = Path(target_db_path or LOCAL_DB_PATH)

        try:
            import io
            from googleapiclient.http import MediaIoBaseDownload

            service = cls._build_drive_service()
            folder_id = cfg["folder_id"]

            # Locate investiq_backup.db in the designated Drive folder
            q = f"'{folder_id}' in parents and name = '{REMOTE_BACKUP_FILENAME}' and trashed = false"
            res = service.files().list(
                q=q,
                fields="files(id, name, modifiedTime, size)",
                orderBy="modifiedTime desc"
            ).execute()
            files = res.get("files", [])

            if not files:
                return {"status": "no_remote_backup", "message": f"No '{REMOTE_BACKUP_FILENAME}' found in Google Drive folder."}

            remote_meta = files[0]
            remote_id = remote_meta["id"]
            remote_time_str = remote_meta.get("modifiedTime", "")

            # Check if local DB exists and its holdings count
            should_restore = False
            reason = ""

            if force:
                should_restore = True
                reason = "manual_force_restore"
            elif not db_path.exists() or db_path.stat().st_size == 0:
                should_restore = True
                reason = "local_db_missing"
            else:
                # Check if local DB has holdings
                try:
                    conn = sqlite3.connect(str(db_path))
                    cur = conn.cursor()
                    cur.execute("SELECT count(*) FROM holdings")
                    holdings_count = cur.fetchone()[0]
                    conn.close()

                    if holdings_count == 0:
                        should_restore = True
                        reason = "local_db_empty_holdings"
                    else:
                        # Compare timestamps if ISO formatted
                        try:
                            # remote_time format: "2026-10-23T13:30:00.000Z"
                            r_dt = datetime.fromisoformat(remote_time_str.replace("Z", "+00:00"))
                            l_dt = datetime.fromtimestamp(db_path.stat().st_mtime).astimezone()
                            if r_dt > l_dt:
                                should_restore = True
                                reason = "remote_backup_is_newer"
                            else:
                                reason = "local_db_is_already_up_to_date"
                        except Exception:
                            # If timestamp parsing fails, only restore if local has no data
                            should_restore = (holdings_count == 0)
                except Exception:
                    should_restore = True
                    reason = "local_table_check_failed"

            if not should_restore:
                return {
                    "status": "already_up_to_date",
                    "reason": reason,
                    "remote_modified": remote_time_str,
                    "message": "Local database is up to date."
                }

            # Download remote backup into memory
            request = service.files().get_media(fileId=remote_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()

            fh.seek(0)
            data_bytes = fh.read()

            if len(data_bytes) < 100:
                return {"status": "error", "message": "Downloaded database file is corrupted or empty."}

            # Temporary file to verify integrity before applying
            temp_target = db_path.parent / f"temp_{REMOTE_BACKUP_FILENAME}"
            with open(temp_target, "wb") as f:
                f.write(data_bytes)

            # Test SQLite integrity of downloaded file
            test_conn = sqlite3.connect(str(temp_target))
            test_cur = test_conn.cursor()
            test_cur.execute("PRAGMA integrity_check;")
            integrity = test_cur.fetchone()[0]
            test_conn.close()

            if integrity != "ok":
                temp_target.unlink(missing_ok=True)
                return {"status": "error", "message": f"SQLite integrity check failed: {integrity}"}

            # Dispose active SQLAlchemy engine connections so file handles are released
            try:
                from database.db import engine
                engine.dispose()
            except Exception:
                pass

            # Create a backup of the existing local file
            if db_path.exists():
                try:
                    prev_bak = db_path.parent / "investiq.db.bak"
                    shutil.copy2(db_path, prev_bak)
                except Exception:
                    pass

            # Safely write restored data into db_path using SQLite's native backup API.
            # This completely avoids Windows [WinError 183] / [WinError 32] file locking conflicts.
            source_conn = sqlite3.connect(str(temp_target))
            dest_conn = sqlite3.connect(str(db_path), timeout=30.0)
            try:
                with dest_conn:
                    source_conn.backup(dest_conn)
            finally:
                source_conn.close()
                dest_conn.close()

            # Clean up temp file
            try:
                temp_target.unlink(missing_ok=True)
            except Exception:
                pass

            # Count holdings in restored database for reporting
            holdings_count = 0
            try:
                check_conn = sqlite3.connect(str(db_path))
                c_cur = check_conn.cursor()
                c_cur.execute("SELECT count(*) FROM holdings")
                holdings_count = c_cur.fetchone()[0]
                check_conn.close()
            except Exception:
                pass

            # Ensure SQLAlchemy models/tables are recognized
            try:
                from database.db import engine
                from database.models import Base
                Base.metadata.create_all(bind=engine)
            except Exception:
                pass

            logger.info(f"Google Drive restore completed successfully ({len(data_bytes)} bytes, {holdings_count} holdings)")
            return {
                "status": "restored",
                "reason": reason,
                "remote_modified": remote_time_str,
                "size_bytes": len(data_bytes),
                "holdings_count": holdings_count,
                "message": f"Successfully restored database from Google Drive ({round(len(data_bytes) / 1024, 1)} KB, {holdings_count} holdings loaded)."
            }

        except Exception as e:
            logger.error(f"Google Drive auto-restore failed: {e}")
            return {"status": "error", "message": str(e)}
