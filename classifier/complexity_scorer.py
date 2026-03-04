"""
Staxx Task Classifier — Prompt Complexity Scorer.

Computes a 0.0–1.0 complexity grade for a given prompt based on
multiple heuristic dimensions:

  1. **Token volume** — raw size of the prompt.
  2. **Instruction specificity** — how constrained / detailed the
     system prompt is.
  3. **Output schema constraints** — free-form text vs. strict JSON.
  4. **Context window utilisation** — what fraction of the model's
     context the prompt occupies.
  5. **Chain-of-thought indicators** — does the prompt ask for
     step-by-step reasoning?

Each dimension produces a sub-score in [0, 1].  The final score is a
weighted average, clamped to [0, 1].
"""

from __future__ import annotations

from classifier.patterns import (
    COT_PATTERNS,
    INSTRUCTION_SPECIFICITY_PATTERNS,
    JSON_SCHEMA_PATTERN,
)
from classifier.schemas import ClassifierInput


# ── Model context window sizes (tokens) ────────────────────────────────
# Used to compute context utilisation.  Defaults to 128k if unknown.

MODEL_CONTEXT_WINDOWS: dict[str, int] = {
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4-turbo": 128_000,
    "gpt-4": 8_192,
    "gpt-3.5-turbo": 16_385,
    "o1": 200_000,
    "o1-mini": 128_000,
    "claude-opus-4-20250514": 200_000,
    "claude-sonnet-4-20250514": 200_000,
    "claude-haiku-4-20250514": 200_000,
    "claude-3-5-sonnet-20241022": 200_000,
    "claude-3-5-haiku-20241022": 200_000,
    "claude-3-opus-20240229": 200_000,
    "gemini-2.0-flash": 1_000_000,
    "gemini-1.5-pro": 2_000_000,
    "gemini-1.5-flash": 1_000_000,
    "llama-3.1-70b": 128_000,
    "llama-3.1-8b": 128_000,
    "mistral-large": 128_000,
    "mistral-small": 32_000,
    "mistral-nemo": 128_000,
}

_DEFAULT_CONTEXT_WINDOW: int = 128_000

# ── Dimension weights (must sum to ~1.0) ───────────────────────────────
_WEIGHT_TOKEN_VOLUME: float = 0.25
_WEIGHT_INSTRUCTION_SPECIFICITY: float = 0.25
_WEIGHT_SCHEMA_CONSTRAINTS: float = 0.20
_WEIGHT_CONTEXT_UTILISATION: float = 0.15
_WEIGHT_COT: float = 0.15


def score(inp: ClassifierInput) -> float:
    """Compute the prompt complexity score for a classifier input.

    Args:
        inp: The normalised classifier input.

    Returns:
        A float in ``[0.0, 1.0]`` where 0 is trivially simple and
        1 is maximally complex.
    """
    token_vol = _score_token_volume(inp)
    specificity = _score_instruction_specificity(inp)
    schema = _score_schema_constraints(inp)
    ctx_util = _score_context_utilisation(inp)
    cot = _score_chain_of_thought(inp)

    raw = (
        _WEIGHT_TOKEN_VOLUME * token_vol
        + _WEIGHT_INSTRUCTION_SPECIFICITY * specificity
        + _WEIGHT_SCHEMA_CONSTRAINTS * schema
        + _WEIGHT_CONTEXT_UTILISATION * ctx_util
        + _WEIGHT_COT * cot
    )
    return max(0.0, min(1.0, raw))


# ── Dimension scorers ──────────────────────────────────────────────────

def _estimate_tokens(text: str) -> int:
    """Rough token count: ~4 chars per token for English."""
    return max(1, len(text) // 4)


def _score_token_volume(inp: ClassifierInput) -> float:
    """Score based on total prompt length.

    Breakpoints (rough):
      - < 100 tokens → 0.1 (trivial)
      - 100–500       → 0.3
      - 500–2000      → 0.5
      - 2000–8000     → 0.7
      - > 8000        → 0.9+
    """
    total_tokens = _estimate_tokens(inp.full_prompt)
    if inp.max_tokens:
        total_tokens += inp.max_tokens

    if total_tokens < 100:
        return 0.1
    if total_tokens < 500:
        return 0.3
    if total_tokens < 2000:
        return 0.5
    if total_tokens < 8000:
        return 0.7
    return 0.9


def _score_instruction_specificity(inp: ClassifierInput) -> float:
    """Score based on how detailed / constrained the system prompt is.

    Counts specificity-indicating patterns (e.g. "must", "exactly",
    "do not", "constraints") and maps the count to [0, 1].
    """
    system = inp.system_prompt
    if not system:
        return 0.1  # No system prompt — minimal constraints.

    specificity = 0.0
    for pattern, weight in INSTRUCTION_SPECIFICITY_PATTERNS:
        matches = pattern.findall(system)
        specificity += len(matches) * weight

    # Also factor in raw system prompt length (longer = more specific).
    length_factor = min(len(system) / 2000, 0.5)  # Cap at 0.5

    raw = min(specificity + length_factor, 1.0)
    return raw


def _score_schema_constraints(inp: ClassifierInput) -> float:
    """Score based on output format constraints.

    Strict JSON schema → high.  Free-form text → low.
    """
    prompt = inp.full_prompt
    rf = inp.response_format or inp.raw_body.get("response_format")

    score = 0.0

    # Explicit response_format
    if isinstance(rf, dict):
        fmt_type = rf.get("type", "")
        if fmt_type == "json_schema":
            score += 0.8
        elif fmt_type == "json_object":
            score += 0.6

    # JSON schema patterns in the prompt text
    if JSON_SCHEMA_PATTERN.search(prompt):
        score += 0.3

    # Mentions of strict format
    lower = prompt.lower()
    if "valid json" in lower or "json schema" in lower:
        score += 0.2
    if "xml" in lower or "yaml" in lower:
        score += 0.15

    return min(score, 1.0)


def _score_context_utilisation(inp: ClassifierInput) -> float:
    """Fraction of the model's context window consumed by the prompt."""
    est_tokens = _estimate_tokens(inp.full_prompt)

    # Look up model context window.
    ctx_window = _DEFAULT_CONTEXT_WINDOW
    model_lower = inp.model.lower()
    for model_prefix, window in MODEL_CONTEXT_WINDOWS.items():
        if model_prefix in model_lower:
            ctx_window = window
            break

    utilisation = est_tokens / ctx_window
    return min(utilisation, 1.0)


def _score_chain_of_thought(inp: ClassifierInput) -> float:
    """Score based on chain-of-thought / reasoning indicators."""
    prompt = inp.full_prompt
    matched = 0
    for pattern in COT_PATTERNS:
        if pattern.search(prompt):
            matched += 1
    # Each match adds ~0.3, capped at 1.0.
    return min(matched * 0.3, 1.0)
