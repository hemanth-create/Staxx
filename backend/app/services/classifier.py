import logging

logger = logging.getLogger(__name__)

class TaskClassifier:
    """
    Rule-based stub for task classification.
    In Phase 1, we rely heavily on SDK tagging, falling back to basic prompt heuristics if tag is missing.
    In future phases, replace this with a lightweight DistilBERT or similar classification model.
    """

    CLASSIFICATION_RULES = {
        "summarization": ["summarize", "tldr", "tl;dr", "summary", "in brief"],
        "extraction": ["extract", "json", "parse", "fields from", "entities"],
        "classification": ["classify", "categorize", "is this", "label"],
        "code": ["python", "javascript", "function", "refactor", "bug", "code"],
    }

    @classmethod
    def classify(cls, prompt: str, provided_tag: str = "unclassified") -> str:
        """
        Classifies a given prompt based on a provided tag or fallback heuristics.
        """
        if provided_tag and provided_tag != "unclassified":
            return provided_tag.lower()

        prompt_lower = prompt.lower()
        for category, triggers in cls.CLASSIFICATION_RULES.items():
            if any(trigger in prompt_lower for trigger in triggers):
                return category

        return "generation" # Default catch-all
