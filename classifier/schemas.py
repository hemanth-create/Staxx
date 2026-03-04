"""
Staxx Task Classifier — Pydantic schemas.

Defines the data models used across the classifier pipeline:
input representations, output results, and internal signal types.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Task type enumeration ──────────────────────────────────────────────

class TaskType(str, Enum):
    """Supported LLM task type labels."""

    SUMMARIZATION = "summarization"
    EXTRACTION = "extraction"
    CLASSIFICATION = "classification"
    CODE_GENERATION = "code_generation"
    QUESTION_ANSWERING = "question_answering"
    TRANSLATION = "translation"
    CREATIVE_WRITING = "creative_writing"
    STRUCTURED_OUTPUT = "structured_output"
    MULTI_TURN_CHAT = "multi_turn_chat"
    OTHER = "other"


# ── Classification tier ────────────────────────────────────────────────

class ClassificationTier(str, Enum):
    """Which stage of the classifier produced the result."""

    RULE_ENGINE = "rule_engine"
    ML_CLASSIFIER = "ml_classifier"


# ── Classifier input ───────────────────────────────────────────────────

class ClassifierInput(BaseModel):
    """Normalised input to the classification pipeline.

    Attributes:
        messages: The full message array from the LLM call
                  (OpenAI format: list of ``{"role": ..., "content": ...}``).
        model: The model identifier string (e.g. ``gpt-4o-2024-08-06``).
        response_format: Optional response format hint from the request
                         body (e.g. ``{"type": "json_object"}``).
        max_tokens: Optional max_tokens from the request body.
        raw_body: The entire original request body, for signals that
                  need fields beyond ``messages``.
    """

    messages: list[dict[str, Any]] = Field(default_factory=list)
    model: str = "unknown"
    response_format: dict[str, Any] | None = None
    max_tokens: int | None = None
    raw_body: dict[str, Any] = Field(default_factory=dict)

    # ── convenience accessors ───────────────────────────────────────

    @property
    def system_prompt(self) -> str:
        """Return the concatenated content of all ``system`` messages."""
        parts: list[str] = []
        for msg in self.messages:
            if msg.get("role") == "system":
                content = msg.get("content", "")
                if isinstance(content, str):
                    parts.append(content)
                elif isinstance(content, list):
                    # Vision / multimodal — extract text parts
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            parts.append(part.get("text", ""))
        return "\n".join(parts)

    @property
    def user_prompt(self) -> str:
        """Return the content of the **last** ``user`` message."""
        for msg in reversed(self.messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    texts = [
                        p.get("text", "")
                        for p in content
                        if isinstance(p, dict) and p.get("type") == "text"
                    ]
                    return "\n".join(texts)
        return ""

    @property
    def full_prompt(self) -> str:
        """Concatenate system + user prompt for analysis."""
        parts = [self.system_prompt, self.user_prompt]
        return "\n".join(p for p in parts if p)

    @property
    def message_count(self) -> int:
        """Total number of messages in the conversation."""
        return len(self.messages)

    @property
    def total_char_count(self) -> int:
        """Approximate total character count across all messages."""
        total = 0
        for msg in self.messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += len(content)
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict):
                        total += len(part.get("text", ""))
        return total


# ── Classification output ──────────────────────────────────────────────

class TaskClassification(BaseModel):
    """Result of the task classification pipeline.

    Attributes:
        task_type: Detected task type label.
        confidence: Confidence score in ``[0.0, 1.0]``.
        classification_tier: Which tier produced the result.
        signals: Human-readable list of signals that drove the decision.
        prompt_complexity_score: Complexity grade in ``[0.0, 1.0]``.
    """

    task_type: str = Field(description="Detected task type, e.g. 'summarization'")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence 0–1")
    classification_tier: str = Field(description="'rule_engine' or 'ml_classifier'")
    signals: list[str] = Field(default_factory=list, description="Signals that drove the classification")
    prompt_complexity_score: float = Field(
        ge=0.0, le=1.0,
        description="Prompt complexity 0 (trivial) to 1 (highly complex)",
    )


# ── Internal: rule engine signal ────────────────────────────────────────

class RuleSignal(BaseModel):
    """A single signal detected by the rule engine."""

    source: str  # e.g. "keyword", "system_prompt_pattern", "structural"
    detail: str  # e.g. "summarize", "json_schema_present"
    weight: float = 1.0  # Relative importance

    @property
    def label(self) -> str:
        """Human-readable signal label for the output."""
        return f"{self.source}:{self.detail}"


class RuleResult(BaseModel):
    """Intermediate result from the rule engine for a single task type."""

    task_type: TaskType
    score: float = 0.0  # Accumulated weighted score
    signals: list[RuleSignal] = Field(default_factory=list)
