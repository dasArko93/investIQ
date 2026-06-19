import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional


class EmailService:
    @staticmethod
    def send_backup_email(
        smtp_server: str,
        smtp_port: str,
        smtp_user: str,
        smtp_password: str,
        recipient_email: str,
        db_path,
        extra_attachments: Optional[List[Tuple[str, bytes, str]]] = None,
    ):
        """
        Send SQLite DB backup (and optional extra files) to recipient email.

        Parameters
        ----------
        extra_attachments : list of (filename, file_bytes, mime_subtype)
            Additional files to attach alongside the SQLite DB.
            Example: [("mf_holding_pattern.zip", zip_bytes, "zip")]
        """
        db_path = Path(db_path)
        if not db_path.exists():
            return False, "Database file not found on disk."

        try:
            # ── Build message ─────────────────────────────────────────────────
            msg = MIMEMultipart()
            msg["From"] = smtp_user
            msg["To"] = recipient_email
            msg["Subject"] = (
                f"InvestIQ Database Backup — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            has_extras = bool(extra_attachments)
            extra_list = (
                "\n".join(f"  • {name}" for name, _, _ in extra_attachments)
                if has_extras
                else ""
            )
            body = (
                "Hello,\n\n"
                "Please find attached the latest backup of your InvestIQ database.\n\n"
                "Attachments included:\n"
                f"  • investiq_backup_*.db  (SQLite portfolio database)\n"
                + (extra_list + "\n" if has_extras else "")
                + "\nBest regards,\nInvestIQ Admin"
            )
            msg.attach(MIMEText(body, "plain"))

            # ── Attach SQLite DB ──────────────────────────────────────────────
            db_filename = f"investiq_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            with open(db_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={db_filename}")
                msg.attach(part)

            # ── Attach extra files (e.g. MF holding ZIP) ──────────────────────
            if extra_attachments:
                for attach_name, attach_bytes, mime_subtype in extra_attachments:
                    extra_part = MIMEBase("application", mime_subtype)
                    extra_part.set_payload(attach_bytes)
                    encoders.encode_base64(extra_part)
                    extra_part.add_header(
                        "Content-Disposition", f"attachment; filename={attach_name}"
                    )
                    msg.attach(extra_part)

            # ── Connect and send ─────────────────────────────────────────────
            port = int(smtp_port)
            if port == 465:
                server = smtplib.SMTP_SSL(smtp_server, port, timeout=10)
            else:
                server = smtplib.SMTP(smtp_server, port, timeout=10)
                server.starttls()

            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, recipient_email, msg.as_string())
            server.quit()

            n_extras = len(extra_attachments) if extra_attachments else 0
            suffix = f" (+{n_extras} extra file(s))" if n_extras else ""
            return True, f"Backup email sent successfully!{suffix}"

        except Exception as e:
            return False, f"Failed to send email: {e}"
