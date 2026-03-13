"""Alert API schemas for FastAPI."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class AlertSeverityEnum(str, Enum):
    """Alert severity levels."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertTypeEnum(str, Enum):
    """Alert types."""

    QUALITY_DRIFT = "quality_drift"
    COST_ANOMALY = "cost_anomaly"
    OPPORTUNITY = "opportunity"


class AlertResponse(BaseModel):
    """Alert response model."""

    id: str
    alert_type: AlertTypeEnum
    severity: AlertSeverityEnum
    title: str
    description: Optional[str] = None
    model: Optional[str] = None
    task_type: Optional[str] = None
    metric_name: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    """Response for alert list endpoint."""

    alerts: List[AlertResponse]
    total: int
    limit: int
    offset: int


class AcknowledgeAlertRequest(BaseModel):
    """Request to acknowledge an alert."""

    pass


class ResolveAlertRequest(BaseModel):
    """Request to resolve an alert."""

    pass


class AlertThresholdUpdate(BaseModel):
    """Update alert threshold configuration."""

    error_rate_threshold_multiplier: Optional[float] = Field(
        None, ge=1.0, le=10.0, description="Error rate spike multiplier (1-10x baseline)"
    )
    json_validity_drop_threshold: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="JSON validity drop threshold (0-100%)"
    )
    cv_threshold_multiplier: Optional[float] = Field(
        None, ge=1.0, le=10.0, description="Output consistency multiplier"
    )
    cost_spike_stddevs: Optional[float] = Field(
        None, ge=1.0, le=5.0, description="Cost spike threshold in standard deviations"
    )
    volume_spike_stddevs: Optional[float] = Field(
        None, ge=1.0, le=5.0, description="Volume spike threshold"
    )
    cost_per_req_change_threshold: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Cost per request change threshold"
    )
    enable_quality_alerts: Optional[bool] = None
    enable_cost_alerts: Optional[bool] = None
    enable_opportunity_alerts: Optional[bool] = None
    email_recipients: Optional[List[str]] = None
    slack_webhook_url: Optional[str] = None
    custom_webhook_urls: Optional[List[str]] = None
    alert_severity_filter: Optional[str] = Field(
        None, regex="^(critical|warning|info)$", description="Minimum severity to send notifications"
    )


class AlertThresholdResponse(BaseModel):
    """Alert threshold configuration response."""

    org_id: str
    error_rate_threshold_multiplier: float
    json_validity_drop_threshold: float
    cv_threshold_multiplier: float
    cost_spike_stddevs: float
    volume_spike_stddevs: float
    cost_per_req_change_threshold: float
    enable_quality_alerts: bool
    enable_cost_alerts: bool
    enable_opportunity_alerts: bool
    email_recipients: List[str]
    slack_webhook_url: Optional[str] = None
    custom_webhook_urls: List[str]
    alert_severity_filter: str
    updated_at: datetime

    class Config:
        from_attributes = True
