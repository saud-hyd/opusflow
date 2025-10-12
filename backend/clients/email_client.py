# Email client for sending negotiation emails
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Email configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER)


def send_negotiation_email(to_email: str, subject: str, body: str, metadata: Dict[str, Any] = None) -> bool:
    """
    Send negotiation email to supplier.

    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body content
        metadata: Optional metadata (session_id, round, etc.)

    Returns:
        True if sent successfully, False otherwise
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"[DEMO MODE] Would send email to {to_email}:")
        print(f"Subject: {subject}")
        print(f"Body: {body[:200]}...")
        return True  # Simulate success in demo mode

    try:
        msg = MIMEMultipart()
        msg['From'] = FROM_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject

        # Add metadata as custom header
        if metadata:
            msg['X-OpusFlow-Session'] = metadata.get('session_id', '')
            msg['X-OpusFlow-Round'] = str(metadata.get('round', 0))

        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        print(f"Email sent to {to_email}")
        return True

    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False
