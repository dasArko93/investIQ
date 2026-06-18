import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from datetime import datetime

class EmailService:
    @staticmethod
    def send_backup_email(smtp_server, smtp_port, smtp_user, smtp_password, recipient_email, db_path):
        """Send SQLite DB backup to recipient email."""
        db_path = Path(db_path)
        if not db_path.exists():
            return False, "Database file not found on disk."
            
        try:
            # Create message container
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = recipient_email
            msg['Subject'] = f"InvestIQ Database Backup - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            body = "Hello,\n\nPlease find attached the latest backup of your InvestIQ SQLite database.\n\nBest regards,\nInvestIQ Admin"
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach DB file
            filename = f"investiq_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            with open(db_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f"attachment; filename= {filename}")
                msg.attach(part)
                
            # Connect and send
            port = int(smtp_port)
            if port == 465:
                server = smtplib.SMTP_SSL(smtp_server, port, timeout=10)
            else:
                server = smtplib.SMTP(smtp_server, port, timeout=10)
                server.starttls()
                
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, recipient_email, msg.as_string())
            server.quit()
            
            return True, "Backup email sent successfully!"
        except Exception as e:
            return False, f"Failed to send email: {e}"
