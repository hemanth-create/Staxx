"""Alert database models."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, DateTime, Float, String, Text, UUID, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Alert(Base):
    """Alert record for drift, cost spikes, opportunities."""

    __tablename__ = "alerts"

    id = Column(UUID, primary_key=True, server_default="gen_random_uuid()")
    org_id = Column(UUID, nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)  # quality_drift, cost_spike, price_change, new_opportunity
    severity = Column(String(20), nullable=False)  # critical, warning, info
    title = Column(String(255), nullable=False)
    description = Column(Text)
    task_type = Column(String(100))
    model = Column(String(100))
    metric_name = Column(String(100))
    current_value = Column(Float)
    threshold_value = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    acknowledged_at = Column(DateTime)
    resolved_at = Column(DateTime)

    __table_args__ = (
        {"schema": "public"},
    )


class AlertThreshold(Base):
    """Organization-level alert thresholds."""

    __tablename__ = "alert_thresholds"

    id = Column(UUID, primary_key=True, server_default="gen_random_uuid()")
    org_id = Column(UUID, nullable=False, unique=True, index=True)
    quality_drift_threshold = Column(Float, default=0.95)  # JSON validity must stay >= 95%
    error_rate_threshold = Column(Float, default=0.02)  # Error rate must stay <= 2%
    cost_spike_std_devs = Column(Float, default=2.0)  # Alert on spikes > 2 std devs
    volume_change_pct = Column(Float, default=0.5)  # Alert on ±50% volume changes
    latency_regression_pct = Column(Float, default=0.2)  # Alert on >20% latency increase
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        {"schema": "public"},
    )
