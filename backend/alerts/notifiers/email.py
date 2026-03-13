"""Email notifier using SendGrid or AWS SES."""

from typing import Dict, Any, Optional
import logging
from .base import BaseNotifier

logger = logging.getLogger(__name__)


class EmailNotifier(BaseNotifier):
    """Send alerts via email using SendGrid or AWS SES."""

    async def send(self, alert: Dict[str, Any]) -> bool:
        """
        Send alert via email.

        Args:
            alert: Alert dictionary

        Returns:
            True if email sent successfully
        """
        recipients = self.config.get("recipients", [])
        if not recipients:
            logger.warning("No email recipients configured")
            return False

        provider = self.config.get("provider", "sendgrid").lower()

        try:
            if provider == "sendgrid":
                return await self._send_via_sendgrid(alert, recipients)
            elif provider == "ses":
                return await self._send_via_ses(alert, recipients)
            else:
                logger.error(f"Unknown email provider: {provider}")
                return False
        except Exception as e:
            logger.error(f"Failed to send email alert: {str(e)}")
            return False

    async def _send_via_sendgrid(self, alert: Dict[str, Any], recipients: list) -> bool:
        """Send via SendGrid API."""
        try:
            # Import here to avoid hard dependency
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail

            api_key = self.config.get("api_key")
            sender = self.config.get("sender_email", "alerts@staxx.ai")

            message = Mail(
                from_email=sender,
                to_emails=recipients,
                subject=alert.get("title", "Staxx Alert"),
                html_content=self._format_alert_html(alert)
            )

            sg = SendGridAPIClient(api_key)
            response = await sg.send(message)
            return 200 <= response.status_code < 300
        except ImportError:
            logger.error("SendGrid SDK not installed")
            return False

    async def _send_via_ses(self, alert: Dict[str, Any], recipients: list) -> bool:
        """Send via AWS SES."""
        try:
            # Import here to avoid hard dependency
            import boto3

            client = boto3.client(
                "ses",
                region_name=self.config.get("region", "us-east-1"),
                aws_access_key_id=self.config.get("access_key"),
                aws_secret_access_key=self.config.get("secret_key")
            )

            sender = self.config.get("sender_email", "alerts@staxx.ai")

            response = client.send_email(
                Source=sender,
                Destination={"ToAddresses": recipients},
                Message={
                    "Subject": {"Data": alert.get("title", "Staxx Alert")},
                    "Body": {"Html": {"Data": self._format_alert_html(alert)}}
                }
            )

            return response["ResponseMetadata"]["HTTPStatusCode"] == 200
        except ImportError:
            logger.error("AWS SDK not installed")
            return False
