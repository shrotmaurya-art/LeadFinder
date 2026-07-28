import smtplib
from email.mime.text import MIMEText

import config
from utils.logger import get_logger

logger = get_logger(__name__)


def send_email_notification(summary: dict) -> None:
    try:
        subject = f"LeadFinderAI: {summary['messages_ready']} new leads ready to review"
        body = (
            f"LeadFinder Daily Summary\n\n"
            f"Businesses Found: {summary['found']}\n"
            f"New Leads: {summary['new']}\n"
            f"Duplicates: {summary['duplicates']}\n"
            f"Messages Ready: {summary['messages_ready']}\n\n"
            f"Open {config.STREAMLIT_URL} to review."
        )

        msg = MIMEText(body, "plain")
        msg["Subject"] = subject
        msg["From"] = config.SMTP_USER
        msg["To"] = config.NOTIFY_EMAIL

        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.sendmail(config.SMTP_USER, [config.NOTIFY_EMAIL], msg.as_string())

        logger.info("Email notification sent to %s", config.NOTIFY_EMAIL)
    except Exception as exc:
        logger.warning("Failed to send email notification: %s", exc)


def send_desktop_notification(summary: dict) -> None:
    try:
        from plyer import notification

        notification.notify(
            title="LeadFinderAI",
            message=f"{summary['messages_ready']} new leads ready to review",
            timeout=10,
        )
        logger.info("Desktop notification sent")
    except Exception as exc:
        logger.warning("Failed to send desktop notification: %s", exc)
