"""Cost Anomaly Detection - Monitor cost spikes and volume changes."""

from typing import Optional
import math


class CostAnomalyDetector:
    """Detects anomalies in cost patterns and request volumes."""

    @staticmethod
    def detect_cost_spike(
        recent_cost: float,
        baseline_cost: float,
        baseline_stddev: float,
        num_stddevs: float = 2.0
    ) -> Optional[dict]:
        """
        Detect cost spike using statistical deviation from baseline.

        Args:
            recent_cost: Current period cost
            baseline_cost: Average historical cost
            baseline_stddev: Standard deviation of historical cost
            num_stddevs: Threshold in standard deviations (default 2)

        Returns:
            Alert dict if spike detected, None otherwise
        """
        if baseline_stddev == 0:
            # No historical variance; use percentage threshold
            if recent_cost > baseline_cost * 1.5:
                return {
                    "alert_type": "cost_anomaly",
                    "severity": "warning",
                    "title": "Cost Spike Detected",
                    "description": f"Cost increased to ${recent_cost:.2f} (baseline: ${baseline_cost:.2f})",
                }
            return None

        z_score = (recent_cost - baseline_cost) / baseline_stddev

        if z_score > num_stddevs:
            severity = "critical" if z_score > 3 else "warning"
            return {
                "alert_type": "cost_anomaly",
                "severity": severity,
                "title": "Cost Anomaly: Spending Spike",
                "description": f"Cost spiked to ${recent_cost:.2f} ({z_score:.1f}σ above baseline of ${baseline_cost:.2f})",
                "metric_name": "daily_cost",
            }

        return None

    @staticmethod
    def detect_volume_spike(
        recent_volume: int,
        baseline_volume: int,
        baseline_stddev: float,
        num_stddevs: float = 2.0
    ) -> Optional[dict]:
        """
        Detect request volume spike.

        Args:
            recent_volume: Current period request count
            baseline_volume: Average historical request count
            baseline_stddev: Standard deviation of historical volume
            num_stddevs: Threshold in standard deviations

        Returns:
            Alert dict if spike detected, None otherwise
        """
        if baseline_stddev == 0:
            if recent_volume > baseline_volume * 1.5:
                return {
                    "alert_type": "cost_anomaly",
                    "severity": "info",
                    "title": "Unusual Request Volume",
                    "description": f"Request volume increased to {recent_volume:,} (baseline: {baseline_volume:,})",
                }
            return None

        z_score = (recent_volume - baseline_volume) / baseline_stddev

        if z_score > num_stddevs:
            return {
                "alert_type": "cost_anomaly",
                "severity": "info",
                "title": "Cost Anomaly: Volume Spike",
                "description": f"Request volume spiked to {recent_volume:,} ({z_score:.1f}σ above {baseline_volume:,})",
                "metric_name": "request_volume",
            }

        return None

    @staticmethod
    def detect_cost_per_req_change(
        recent_cpr: float,
        baseline_cpr: float,
        threshold_percent: float = 0.1
    ) -> Optional[dict]:
        """
        Detect if cost per request has changed significantly.

        Args:
            recent_cpr: Current cost per request
            baseline_cpr: Historical average cost per request
            threshold_percent: Percentage change threshold (default 10%)

        Returns:
            Alert dict if change detected, None otherwise
        """
        if baseline_cpr == 0:
            return None

        percent_change = (recent_cpr - baseline_cpr) / baseline_cpr

        if abs(percent_change) > threshold_percent:
            direction = "increased" if percent_change > 0 else "decreased"
            return {
                "alert_type": "cost_anomaly",
                "severity": "info",
                "title": "Cost Per Request Changed",
                "description": f"Cost per request {direction} by {abs(percent_change)*100:.1f}% to ${recent_cpr:.4f}",
                "metric_name": "cost_per_request",
            }

        return None
