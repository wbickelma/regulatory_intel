"""Gmail SMTP email client for sending reports with attachments."""
from __future__ import annotations

import logging
import mimetypes
import os
import smtplib
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path

logger = logging.getLogger(__name__)


class EmailClient:
    """Gmail SMTP-based email client for report delivery."""

    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587

    def __init__(
        self,
        gmail_address: str | None = None,
        app_password: str | None = None,
    ):
        """Initialize with Gmail credentials.

        Args:
            gmail_address: Gmail address. Falls back to GMAIL_ADDRESS env var.
            app_password: Gmail app password. Falls back to GMAIL_APP_PASSWORD env var.
        """
        self.gmail_address = gmail_address or os.getenv("GMAIL_ADDRESS")
        self.app_password = app_password or os.getenv("GMAIL_APP_PASSWORD")

        if not self.gmail_address:
            raise ValueError("Missing GMAIL_ADDRESS")
        if not self.app_password:
            raise ValueError("Missing GMAIL_APP_PASSWORD")

    def send_report(
        self,
        to_emails: list[str],
        subject: str,
        body_html: str,
        attachment_path: str | Path | None = None,
        from_email: str | None = None,
    ) -> bool:
        """Send an email with optional attachment.

        Args:
            to_emails: List of recipient email addresses.
            subject: Email subject line.
            body_html: HTML body content.
            attachment_path: Path to file to attach (e.g., .docx report).
            from_email: Sender email (defaults to gmail_address).

        Returns:
            True if sent successfully, False otherwise.
        """
        from_email = from_email or self.gmail_address

        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = ", ".join(to_emails)
        msg["Subject"] = subject

        msg.attach(MIMEText(body_html, "html"))

        if attachment_path:
            attachment_path = Path(attachment_path)
            if attachment_path.exists():
                mime_type, _ = mimetypes.guess_type(str(attachment_path))
                mime_type = mime_type or "application/octet-stream"
                main_type, sub_type = mime_type.split("/", 1)

                with open(attachment_path, "rb") as f:
                    part = MIMEBase(main_type, sub_type)
                    part.set_payload(f.read())

                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={attachment_path.name}",
                )
                msg.attach(part)
            else:
                logger.warning(f"Attachment not found: {attachment_path}")

        try:
            with smtplib.SMTP(self.SMTP_SERVER, self.SMTP_PORT) as server:
                server.starttls()
                server.login(self.gmail_address, self.app_password)
                server.sendmail(from_email, to_emails, msg.as_string())
            logger.info(f"Email sent to {to_emails}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
