"""Alert database models."""

from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    DateTime,
    Boolean,
    ForeignKey,
    Enum,
    JSON,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from backend.app.db import Base


class AlertSeverity(str, enum.Enum):
    """Alert severity levels."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertType(str, enum.Enum):
    """Alert types."""

    QUALITY_DRIFT = "quality_drift"
    COST_ANOMALY = "cost_anomaly"
    OPPORTUNITY = "opportunity"


class Alert(Base):
    """Alert model for quality, cost, and opportunity monitoring."""

    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    alert_type = Column(Enum(AlertType), nullable=False, index=True)
    severity = Column(Enum(AlertSeverity), nullable=False, index=True)
    title = Column(String(256), nullable=False)
    description = Column(Text)

    # Optional context
    model = Column(String(128), nullable=True)
    task_type = Column(String(128), nullable=True)
    metric_name = Column(String(128), nullable=True)

    # Metadata
    metadata_json = Column(JSON, nullable=True)  # Extra context as JSON

    # Status tracking
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(36), nullable=True)
    resolved_by = Column(String(36), nullable=True)

    # Audit
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="alerts")
    notification_logs = relationship("NotificationLog", back_populates="alert")

    def __repr__(self):
        return f"<Alert {self.id} {self.alert_type} {self.severity}>"


class AlertThreshold(Base):
    """Organization-specific alert thresholds and settings."""

    __tablename__ = "alert_thresholds"

    id = Column(String(36), primary_key=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, unique=True)

    # Quality drift thresholds
    error_rate_threshold_multiplier = Column(Float, default=2.0)  # 2x baseline
    json_validity_drop_threshold = Column(Float, default=0.05)  # 5% absolute drop
    cv_threshold_multiplier = Column(Float, default=1.5)  # 1.5x baseline

    # Cost anomaly thresholds
    cost_spike_stddevs = Column(Float, default=2.0)  # 2 standard deviations
    volume_spike_stddevs = Column(Float, default=2.0)
    cost_per_req_change_threshold = Column(Float, default=0.1)  # 10% change

    # Enable/disable alert types
    enable_quality_alerts = Column(Boolean, default=True)
    enable_cost_alerts = Column(Boolean, default=True)
    enable_opportunity_alerts = Column(Boolean, default=True)

    # Notification settings
    email_recipients = Column(JSON, default=list)  # List of email addresses
    slack_webhook_url = Column(String(500), nullable=True)
    custom_webhook_urls = Column(JSON, default=list)  # List of webhook URLs

    # Alert routing
    alert_severity_filter = Column(String(20), default="warning")  # "critical", "warning", "info"

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    organization = relationship("Organization", back_populates="alert_threshold")

    def __repr__(self):
        return f"<AlertThreshold org_id={self.org_id}>"


class NotificationLog(Base):
    """Log of notification delivery attempts."""

    __tablename__ = "notification_logs"

    id = Column(String(36), primary_key=True)
    alert_id = Column(String(36), ForeignKey("alerts.id"), nullable=False)

    # Notification method
    method = Column(String(50), nullable=False)  # "email", "slack", "webhook"
    destination = Column(String(500), nullable=False)  # Email, Slack channel, webhook URL

    # Status
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)

    # Tracking
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    alert = relationship("Alert", back_populates="notification_logs")

    def __repr__(self):
        return f"<NotificationLog {self.id} {self.method}>"
