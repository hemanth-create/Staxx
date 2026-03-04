"""
Staxx Task Classifier — Tier 2: ML Classifier (DistilBERT).

A lightweight transformer-based classifier used as a **fallback** when
the rule engine (Tier 1) confidence is below threshold.

Key design choices:
  - **Lazy-loaded:** Model weights are loaded on first call, not at import.
  - **Graceful degradation:** If ``torch`` or ``transformers`` are not
    installed, the classifier reports itself as unavailable and the
    orchestrator stays on Tier 1 only.
  - **Performance target:** < 50 ms per call on CPU.
"""

from __future__ import annotations

import logging
from typing import Any

from classifier.schemas import TaskType

logger = logging.getLogger(__name__)

# ── Availability check ─────────────────────────────────────────────────

_TORCH_AVAILABLE: bool = False
_TRANSFORMERS_AVAILABLE: bool = False

try:
    import torch  # noqa: F401

    _TORCH_AVAILABLE = True
except ImportError:
    pass

try:
    import transformers  # noqa: F401

    _TRANSFORMERS_AVAILABLE = True
except ImportError:
    pass


def is_available() -> bool:
    """Return ``True`` if the ML backend (torch + transformers) is installed."""
    return _TORCH_AVAILABLE and _TRANSFORMERS_AVAILABLE


# ── Label mapping ──────────────────────────────────────────────────────

LABEL_TO_TASK: dict[int, TaskType] = {
    0: TaskType.SUMMARIZATION,
    1: TaskType.EXTRACTION,
    2: TaskType.CLASSIFICATION,
    3: TaskType.CODE_GENERATION,
    4: TaskType.QUESTION_ANSWERING,
    5: TaskType.TRANSLATION,
    6: TaskType.CREATIVE_WRITING,
    7: TaskType.STRUCTURED_OUTPUT,
    8: TaskType.MULTI_TURN_CHAT,
    9: TaskType.OTHER,
}

TASK_TO_LABEL: dict[TaskType, int] = {v: k for k, v in LABEL_TO_TASK.items()}

NUM_LABELS: int = len(LABEL_TO_TASK)


# ── ML Classifier wrapper ─────────────────────────────────────────────

class MLTaskClassifier:
    """Lazy-loaded DistilBERT-based task classifier.

    The model is loaded on the first call to :meth:`predict`.  If a
    fine-tuned checkpoint is not available, we fall back to a zero-shot
    pipeline using ``distilbert-base-uncased`` with simple label mapping.

    Attributes:
        model_name: HuggingFace model identifier or local path.
        max_length: Maximum token length for the tokenizer.
    """

    def __init__(
        self,
        model_name: str = "distilbert-base-uncased",
        max_length: int = 512,
    ) -> None:
        self.model_name = model_name
        self.max_length = max_length
        self._pipeline: Any | None = None
        self._loaded: bool = False

    # ── lazy loading ────────────────────────────────────────────────

    def _ensure_loaded(self) -> bool:
        """Load the model pipeline if not already loaded.

        Returns:
            ``True`` if the pipeline is ready, ``False`` if the ML
            backend is unavailable.
        """
        if self._loaded:
            return self._pipeline is not None

        self._loaded = True

        if not is_available():
            logger.warning(
                "ML classifier unavailable — torch or transformers not installed. "
                "Tier 2 classification will be skipped."
            )
            return False

        try:
            from transformers import pipeline as hf_pipeline

            # Try loading as a fine-tuned sequence classification model.
            # If the checkpoint doesn't exist locally, fall back to
            # zero-shot classification.
            try:
                self._pipeline = hf_pipeline(
                    "text-classification",
                    model=self.model_name,
                    tokenizer=self.model_name,
                    top_k=NUM_LABELS,
                    truncation=True,
                    max_length=self.max_length,
                    device=-1,  # CPU only — keep it fast and portable
                )
                logger.info(
                    "ML classifier loaded (text-classification): %s",
                    self.model_name,
                )
            except (OSError, ValueError):
                # Model not fine-tuned for our labels — use zero-shot.
                self._pipeline = hf_pipeline(
                    "zero-shot-classification",
                    model="facebook/bart-large-mnli",
                    device=-1,
                    truncation=True,
                    max_length=self.max_length,
                )
                logger.info(
                    "ML classifier loaded (zero-shot fallback): facebook/bart-large-mnli",
                )
            return True

        except Exception:
            logger.error("Failed to load ML classifier", exc_info=True)
            return False

    # ── prediction ──────────────────────────────────────────────────

    def predict(self, text: str) -> tuple[TaskType, float, list[dict[str, Any]]]:
        """Classify the given text into a task type.

        Args:
            text: The concatenated system + user prompt (first 512 tokens).

        Returns:
            Tuple of ``(task_type, confidence, raw_scores)``.
            If the ML backend is unavailable, returns
            ``(TaskType.OTHER, 0.0, [])``.
        """
        if not self._ensure_loaded():
            return TaskType.OTHER, 0.0, []

        # Truncate text to first ~2048 characters (~512 tokens).
        truncated = text[:2048]

        try:
            return self._run_inference(truncated)
        except Exception:
            logger.error("ML classifier inference failed", exc_info=True)
            return TaskType.OTHER, 0.0, []

    def _run_inference(self, text: str) -> tuple[TaskType, float, list[dict[str, Any]]]:
        """Execute the model pipeline and map outputs to our labels."""
        pipeline = self._pipeline

        # Detect which pipeline type we're using.
        task_type_str = getattr(pipeline, "task", "")

        if task_type_str == "zero-shot-classification":
            return self._zero_shot_inference(text)
        else:
            return self._classification_inference(text)

    def _classification_inference(
        self, text: str
    ) -> tuple[TaskType, float, list[dict[str, Any]]]:
        """Run a standard text-classification pipeline.

        Expects the model to have been fine-tuned with our label set.
        """
        results = self._pipeline(text)
        if not results:
            return TaskType.OTHER, 0.0, []

        # ``top_k=NUM_LABELS`` returns a list of dicts sorted by score.
        raw_scores: list[dict[str, Any]] = []
        best_type = TaskType.OTHER
        best_score = 0.0

        for item in results:
            label_str: str = item.get("label", "")
            score: float = item.get("score", 0.0)

            # Map model label to our TaskType.
            task = _label_string_to_task(label_str)
            raw_scores.append({"task_type": task.value, "score": score})

            if score > best_score:
                best_score = score
                best_type = task

        return best_type, best_score, raw_scores

    def _zero_shot_inference(
        self, text: str
    ) -> tuple[TaskType, float, list[dict[str, Any]]]:
        """Run a zero-shot classification pipeline.

        Uses natural language descriptions as candidate labels.
        """
        candidate_labels = [
            "text summarization",
            "data extraction or entity recognition",
            "text classification or categorization",
            "code generation or programming",
            "question answering",
            "language translation",
            "creative writing or content generation",
            "structured output like JSON or XML",
            "multi-turn conversation or chat",
            "other general task",
        ]
        label_to_task_map: dict[str, TaskType] = {
            label: list(LABEL_TO_TASK.values())[i]
            for i, label in enumerate(candidate_labels)
        }

        result = self._pipeline(text, candidate_labels=candidate_labels)

        raw_scores: list[dict[str, Any]] = []
        labels = result.get("labels", [])
        scores = result.get("scores", [])

        best_type = TaskType.OTHER
        best_score = 0.0

        for label, score in zip(labels, scores):
            task = label_to_task_map.get(label, TaskType.OTHER)
            raw_scores.append({"task_type": task.value, "score": score})
            if score > best_score:
                best_score = score
                best_type = task

        return best_type, best_score, raw_scores


# ── helpers ─────────────────────────────────────────────────────────────

def _label_string_to_task(label: str) -> TaskType:
    """Map a model output label string back to a TaskType.

    Handles both ``LABEL_0`` style and human-readable label strings.
    """
    label_clean = label.strip().lower()

    # LABEL_N format (from HuggingFace default)
    if label_clean.startswith("label_"):
        try:
            idx = int(label_clean.split("_")[1])
            return LABEL_TO_TASK.get(idx, TaskType.OTHER)
        except (IndexError, ValueError):
            pass

    # Direct match against TaskType values
    for tt in TaskType:
        if tt.value == label_clean:
            return tt

    # Fuzzy match
    for tt in TaskType:
        if tt.value.replace("_", " ") in label_clean or label_clean in tt.value:
            return tt

    return TaskType.OTHER


# ── Module-level singleton ─────────────────────────────────────────────
# Created once and reused across calls.

_default_classifier: MLTaskClassifier | None = None


def get_default_classifier() -> MLTaskClassifier:
    """Return (or create) the module-level ML classifier instance."""
    global _default_classifier  # noqa: PLW0603
    if _default_classifier is None:
        _default_classifier = MLTaskClassifier()
    return _default_classifier
