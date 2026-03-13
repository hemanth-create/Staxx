"""Opportunity Detection - Monitor for new models and price drops."""

from typing import Optional, List, Dict


class OpportunityDetector:
    """Detects new model releases and pricing improvements."""

    @staticmethod
    def detect_new_model(
        model_name: str,
        provider: str,
        release_date: str,
        estimated_performance_improvement: float = 0.05
    ) -> Optional[dict]:
        """
        Alert on new model release that might benefit current workloads.

        Args:
            model_name: Name of the new model
            provider: Provider (openai, anthropic, google, etc.)
            release_date: Release date of model
            estimated_performance_improvement: Expected % improvement vs current model

        Returns:
            Alert dict if worth noting, None otherwise
        """
        if estimated_performance_improvement < 0.02:  # At least 2% improvement
            return None

        return {
            "alert_type": "opportunity",
            "severity": "info",
            "title": f"New Model Available: {model_name}",
            "description": f"{provider.capitalize()} released {model_name} on {release_date} "
            f"with estimated {estimated_performance_improvement*100:.0f}% improvement",
            "model": model_name,
        }

    @staticmethod
    def detect_price_drop(
        model_name: str,
        provider: str,
        old_price: float,
        new_price: float,
        price_type: str = "input"  # or "output"
    ) -> Optional[dict]:
        """
        Alert on model price reduction.

        Args:
            model_name: Model name
            provider: Provider name
            old_price: Previous price per 1M tokens
            new_price: New price per 1M tokens
            price_type: "input" or "output"

        Returns:
            Alert dict if price dropped, None otherwise
        """
        if new_price >= old_price:
            return None

        percent_drop = ((old_price - new_price) / old_price) * 100

        return {
            "alert_type": "opportunity",
            "severity": "info",
            "title": f"Price Drop: {model_name} {price_type.capitalize()} Token Price",
            "description": f"{provider.capitalize()} reduced {model_name} {price_type} price by {percent_drop:.1f}% "
            f"from ${old_price:.6f} to ${new_price:.6f} per 1M tokens",
            "model": model_name,
        }

    @staticmethod
    def detect_competitive_advantage(
        current_model: str,
        better_model: str,
        cost_savings_percent: float,
        quality_improvement_percent: float
    ) -> Optional[dict]:
        """
        Alert when a competitive model offers better value.

        Args:
            current_model: Current model being used
            better_model: Alternative model with better value
            cost_savings_percent: Estimated cost savings if switching
            quality_improvement_percent: Estimated quality improvement

        Returns:
            Alert dict if competitive advantage detected, None otherwise
        """
        if cost_savings_percent < 0.05 and quality_improvement_percent < 0.05:
            return None

        improvements = []
        if cost_savings_percent > 0:
            improvements.append(f"{cost_savings_percent*100:.0f}% cost savings")
        if quality_improvement_percent > 0:
            improvements.append(f"{quality_improvement_percent*100:.0f}% quality improvement")

        return {
            "alert_type": "opportunity",
            "severity": "info",
            "title": f"Competitive Opportunity: {better_model}",
            "description": f"{better_model} offers {' and '.join(improvements)} vs {current_model}. "
            "Consider running a shadow evaluation.",
            "model": better_model,
        }
