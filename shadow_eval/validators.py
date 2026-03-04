"""
Staxx Intelligence — Output Validators

Validates shadow evaluation outputs for quality signals:
  • JSON schema validity
  • Empty output detection
  • Truncation detection
  • PII detection (for prompt filtering)
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PII Detection Patterns
# ---------------------------------------------------------------------------

_PII_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("email", re.compile(
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
        re.IGNORECASE,
    )),
    ("phone_us", re.compile(
        r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
    )),
    ("phone_intl", re.compile(
        r"\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}",
    )),
    ("ssn", re.compile(
        r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",
    )),
    ("credit_card", re.compile(
        r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
    )),
]


@dataclass
class PIICheckResult:
    """Result of PII scanning on a text input."""

    contains_pii: bool
    matched_types: list[str]
    match_count: int


def check_pii(text: str) -> PIICheckResult:
    """
    Scan *text* for common PII patterns.

    Returns a ``PIICheckResult`` indicating whether PII was found
    and which types matched.  This is a basic regex-based filter —
    not a substitute for a full PII detection service.
    """
    if not text:
        return PIICheckResult(contains_pii=False, matched_types=[], match_count=0)

    matched_types: list[str] = []
    total_matches = 0

    for pii_type, pattern in _PII_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            matched_types.append(pii_type)
            total_matches += len(matches)

    return PIICheckResult(
        contains_pii=len(matched_types) > 0,
        matched_types=matched_types,
        match_count=total_matches,
    )


# ---------------------------------------------------------------------------
# Output Quality Validation
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """Result of validating a shadow eval output."""

    json_valid: Optional[bool]  # None if not a JSON task
    output_empty: bool
    output_truncated: bool
    is_valid: bool  # Overall validity flag


# Known JSON task types where we expect structured output
_JSON_TASK_TYPES = frozenset({
    "extraction",
    "classification",
    "structured_output",
    "json_generation",
    "data_parsing",
})

# Common truncation indicators
_TRUNCATION_INDICATORS = (
    "...",
    "[truncated]",
    "[continued]",
    "<!-- truncated",
)
# Finish reason strings that indicate truncation
_TRUNCATION_FINISH_REASONS = frozenset({
    "length",
    "max_tokens",
})


def validate_output(
    text_output: str,
    task_type: str,
    finish_reason: Optional[str] = None,
    max_tokens: int = 4096,
) -> ValidationResult:
    """
    Validate a shadow evaluation output for quality signals.

    Args:
        text_output: The raw text output from the candidate model.
        task_type: The classified task type.
        finish_reason: The model's finish/stop reason (if available).
        max_tokens: The max_tokens parameter used in the request.

    Returns:
        A ``ValidationResult`` with individual quality flags.
    """
    # --- Empty check ---------------------------------------------------------
    stripped = text_output.strip() if text_output else ""
    output_empty = len(stripped) == 0

    # --- Truncation check ----------------------------------------------------
    output_truncated = False

    if finish_reason and finish_reason.lower() in _TRUNCATION_FINISH_REASONS:
        output_truncated = True
    elif stripped and any(stripped.endswith(ind) for ind in _TRUNCATION_INDICATORS):
        output_truncated = True

    # --- JSON validity check -------------------------------------------------
    json_valid: Optional[bool] = None

    if task_type.lower() in _JSON_TASK_TYPES:
        json_valid = _check_json_valid(stripped)

    # Also check if the output looks like it was supposed to be JSON
    # (starts with { or [) even if the task type doesn't suggest it
    if json_valid is None and stripped:
        first_char = stripped[0]
        if first_char in ("{", "["):
            json_valid = _check_json_valid(stripped)

    # --- Overall validity ----------------------------------------------------
    is_valid = not output_empty and not output_truncated
    if json_valid is False:
        is_valid = False

    return ValidationResult(
        json_valid=json_valid,
        output_empty=output_empty,
        output_truncated=output_truncated,
        is_valid=is_valid,
    )


def _check_json_valid(text: str) -> bool:
    """Attempt to parse *text* as JSON.  Returns True if valid."""
    try:
        json.loads(text)
        return True
    except (json.JSONDecodeError, ValueError):
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
        if json_match:
            try:
                json.loads(json_match.group(1))
                return True
            except (json.JSONDecodeError, ValueError):
                pass
        return False
