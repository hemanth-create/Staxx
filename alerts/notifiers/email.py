"""Email notifier using SendGrid or SES."""

import os
import logging
from typing import Optional
from alerts.notifiers.base import BaseNotifier
from alerts.db.models import Alert

logger = logging.getLogger(__name__)


class EmailNotifier(BaseNotifier):
    """Send alerts via email (SendGrid or SES)."""

    def __init__(self, provider: str = "sendgrid"):
        """Initialize email notifier."""
        self.provider = provider
        if provider == "sendgrid":
            self.api_key = os.getenv("SENDGRID_API_KEY")
        elif provider == "ses":
            import boto3

            self.client = boto3.client("ses", region_name=os.getenv("AWS_REGION"))
        else:
            raise ValueError(f"Unknown email provider: {provider}")

    async def send(self, alert: Alert, recipient: str) -> bool:
        """Send alert via email."""
        try:
            formatted = self.format_alert(alert)

            subject = f"[{alert.severity.upper()}] {alert.title}"
            html_body = self._build_html_email(formatted)

            if self.provider == "sendgrid":
                return await self._send_sendgrid(recipient, subject, html_body)
            elif self.provider == "ses":
                return await self._send_ses(recipient, subject, html_body)

        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False

    async def _send_sendgrid(self, recipient: str, subject: str, html: str) -> bool:
        """Send via SendGrid."""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, To

            message = Mail(
                from_email="alerts@staxx.ai",
                to_emails=To(recipient),
                subject=subject,
                html_content=html,
            )
            sg = SendGridAPIClient(self.api_key)
            response = sg.send(message)
            return response.status_code in (200, 201, 202)
        except Exception as e:
            logger.error(f"SendGrid error: {e}")
            return False

    async def _send_ses(self, recipient: str, subject: str, html: str) -> bool:
        """Send via AWS SES."""
        try:
            self.client.send_email(
                Source="alerts@staxx.ai",
                Destination={"ToAddresses": [recipient]},
                Message={
                    "Subject": {"Data": subject},
                    "Body": {"Html": {"Data": html}},
                },
            )
            return True
        except Exception as e:
            logger.error(f"SES error: {e}")
            return False

    def _build_html_email(self, alert_data: dict) -> str:
        """Build HTML email template."""
        severity_color = {
            "critical": "#EF4444",
            "warning": "#F59E0B",
            "info": "#3B82F6",
        }.get(alert_data["severity"], "#3B82F6")

        return f"""
        <html>
            <body style="font-family: Inter, sans-serif; background: #f3f4f6; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <div style="padding: 12px 16px; background: {severity_color}; color: white; border-radius: 6px; margin-bottom: 24px;">
                        <h2 style="margin: 0; font-size: 18px;">{alert_data['title']}</h2>
                    </div>

                    <p style="color: #374151; line-height: 1.6; margin-bottom: 16px;">
                        {alert_data['description']}
                    </p>

                    <table style="width: 100%; margin: 24px 0; border-collapse: collapse;">
                        <tr style="border-bottom: 1px solid #e5e7eb;">
                            <td style="padding: 12px 0; color: #6b7280;">Alert Type</td>
                            <td style="padding: 12px 0; color: #111827; font-weight: 600;">{alert_data['type']}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #e5e7eb;">
                            <td style="padding: 12px 0; color: #6b7280;">Severity</td>
                            <td style="padding: 12px 0; color: #111827; font-weight: 600;">{alert_data['severity'].upper()}</td>
                        </tr>
                        {f'<tr style="border-bottom: 1px solid #e5e7eb;"><td style="padding: 12px 0; color: #6b7280;">Task Type</td><td style="padding: 12px 0; color: #111827; font-weight: 600;">{alert_data["task_type"]}</td></tr>' if alert_data.get('task_type') else ''}
                        {f'<tr style="border-bottom: 1px solid #e5e7eb;"><td style="padding: 12px 0; color: #6b7280;">Model</td><td style="padding: 12px 0; color: #111827; font-weight: 600;">{alert_data["model"]}</td></tr>' if alert_data.get('model') else ''}
                    </table>

                    <div style="background: #f9fafb; padding: 16px; border-radius: 6px; margin: 24px 0;">
                        <p style="margin: 0; color: #6b7280; font-size: 12px;">Alert created: {alert_data['created_at']}</p>
                    </div>

                    <a href="https://dashboard.staxx.ai/alerts" style="display: inline-block; background: #0ea5e9; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600;">View Alert</a>

                    <hr style="margin: 24px 0; border: none; border-top: 1px solid #e5e7eb;">
                    <p style="font-size: 12px; color: #9ca3af; margin: 0;">
                        This alert was sent by Staxx Intelligence. <a href="https://staxx.ai/alerts/settings" style="color: #0ea5e9;">Manage preferences</a>
                    </p>
                </div>
            </body>
        </html>
        """
