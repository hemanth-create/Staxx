"""Quality Drift Detection - Monitor error rates, JSON validity, and coefficient of variation."""

from typing import Optional, List
from datetime import datetime, timedelta


class QualityDriftDetector:
    """Detects quality degradation through error rate and validity monitoring."""

    def __init__(self, baseline_window_hours: int = 24):
        """
        Args:
            baseline_window_hours: Rolling window for baseline calculation (default 24h)
        """
        self.baseline_window_hours = baseline_window_hours

    def detect_error_rate_spike(
        self,
        recent_error_rate: float,
        baseline_error_rate: float,
        threshold_multiplier: float = 2.0
    ) -> Optional[dict]:
        """
        Detect if error rate has spiked above baseline.

        Args:
            recent_error_rate: Current error rate (0-1)
            baseline_error_rate: Historical average error rate
            threshold_multiplier: How many times baseline = alert (default 2x)

        Returns:
            Alert dict if spike detected, None otherwise
        """
        if baseline_error_rate == 0:
            if recent_error_rate > 0.05:  # 5% absolute threshold if no baseline
                return {
                    "alert_type": "quality_drift",
                    "severity": "warning",
                    "title": "Unexpected Error Rate Detected",
                    "description": f"Error rate has spiked to {recent_error_rate*100:.1f}%",
                    "metric_name": "error_rate",
                }
            return None

        if recent_error_rate > baseline_error_rate * threshold_multiplier:
            return {
                "alert_type": "quality_drift",
                "severity": "critical" if recent_error_rate > 0.1 else "warning",
                "title": "Quality Drift: Error Rate Spike",
                "description": f"Error rate increased to {recent_error_rate*100:.1f}% (baseline: {baseline_error_rate*100:.1f}%)",
                "metric_name": "error_rate",
            }

        return None

    def detect_json_validity_drop(
        self,
        recent_validity: float,
        baseline_validity: float,
        threshold_drop: float = 0.05
    ) -> Optional[dict]:
        """
        Detect if JSON validity has dropped.

        Args:
            recent_validity: Current JSON validity rate (0-1)
            baseline_validity: Historical average validity rate
            threshold_drop: Percentage point drop threshold

        Returns:
            Alert dict if drop detected, None otherwise
        """
        drop = baseline_validity - recent_validity

        if drop > threshold_drop:
            return {
                "alert_type": "quality_drift",
                "severity": "warning",
                "title": "Quality Drift: JSON Validity Drop",
                "description": f"JSON validity decreased by {drop*100:.1f}% to {recent_validity*100:.1f}%",
                "metric_name": "json_validity",
            }

        return None

    def detect_cv_spike(
        self,
        recent_cv: float,
        baseline_cv: float,
        threshold_multiplier: float = 1.5
    ) -> Optional[dict]:
        """
        Detect if coefficient of variation (consistency) has degraded.

        Args:
            recent_cv: Current coefficient of variation
            baseline_cv: Historical average CV
            threshold_multiplier: How many times baseline = alert

        Returns:
            Alert dict if spike detected, None otherwise
        """
        if recent_cv > baseline_cv * threshold_multiplier:
            return {
                "alert_type": "quality_drift",
                "severity": "info",
                "title": "Quality Drift: Output Consistency Degraded",
                "description": f"Output consistency (CV) increased from {baseline_cv:.2f} to {recent_cv:.2f}",
                "metric_name": "output_consistency",
            }

        return None
