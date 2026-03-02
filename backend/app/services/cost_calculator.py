import logging

logger = logging.getLogger(__name__)


class CostCalculator:
    """
    Calculates cost based on model identifiers and token counts.
    MVP implementation uses hardcoded static rates per 1M tokens.
    """

    # Static pricing per 1M tokens (USD)
    # Realistic examples for 2024 MVP
    MODEL_PRICING = {
        "gpt-4o-2024-08-06": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini-2024-07-18": {"input": 0.15, "output": 0.60},
        "claude-3-5-sonnet-20240620": {"input": 3.00, "output": 15.00},
        "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    }

    @classmethod
    def calculate(cls, model_id: str, input_tokens: int, output_tokens: int) -> float:
        """
        Calculates the exact cost of an API call in USD.
        """
        # Attempt to map generic model names to specific versions if exact isn't provided
        # MVP fallback handling
        normalized_model = model_id.lower()
        if "gpt-4o-mini" in normalized_model:
            pricing = cls.MODEL_PRICING["gpt-4o-mini-2024-07-18"]
        elif "gpt-4o" in normalized_model:
            pricing = cls.MODEL_PRICING["gpt-4o-2024-08-06"]
        elif "claude-3-5-sonnet" in normalized_model:
            pricing = cls.MODEL_PRICING["claude-3-5-sonnet-20240620"]
        elif "claude-3-haiku" in normalized_model or "claude-3-5-haiku" in normalized_model:
            pricing = cls.MODEL_PRICING["claude-3-haiku-20240307"]
        else:
            # Fallback to an average high-tier price if unknown model
            logger.warning("Unrecognized model '%s', using default high-tier pricing.", model_id)
            pricing = {"input": 3.00, "output": 15.00}

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost
