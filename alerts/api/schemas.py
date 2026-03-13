"""Alert API request/response schemas."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID


class AlertResponse(BaseModel):
    """Alert response model."""

    id: UUID
    org_id: UUID
    alert_type: str
    severity: str
    title: str
    description: Optional[str] = None
    task_type: Optional[str] = None
    model: Optional[str] = None
    metric_name: Optional[str] = None
    current_value: Optional[float] = None
    threshold_value: Optional[float] = None
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    """List of alerts."""

    alerts: List[AlertResponse]
    total: int
    limit: int
    offset: int


class AlertThresholdResponse(BaseModel):
    """Alert threshold configuration."""

    id: UUID
    org_id: UUID
    quality_drift_threshold: float = Field(default=0.95, description="JSON validity threshold")
    error_rate_threshold: float = Field(default=0.02, description="Max error rate")
    cost_spike_std_devs: float = Field(default=2.0, description="Std devs for cost spike detection")
    volume_change_pct: float = Field(default=0.5, description="Volume change % threshold")
    latency_regression_pct: float = Field(default=0.2, description="Latency increase % threshold")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertThresholdUpdate(BaseModel):
    """Alert threshold update request."""

    quality_drift_threshold: Optional[float] = None
    error_rate_threshold: Optional[float] = None
    cost_spike_std_devs: Optional[float] = None
    volume_change_pct: Optional[float] = None
    latency_regression_pct: Optional[float] = None


class AlertAcknowledge(BaseModel):
    """Acknowledge alert request."""

    acknowledged: bool = True


class AlertResolve(BaseModel):
    """Resolve alert request."""

    resolved: bool = True
