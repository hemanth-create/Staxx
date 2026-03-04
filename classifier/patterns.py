"""
Staxx Task Classifier — Compiled regex patterns and keyword lists.

All patterns are **pre-compiled** at module load time so that the rule
engine hot path is pure matching with zero compilation overhead.

Organisation:
  - ``TASK_KEYWORDS``: weighted keyword lists per task type.
  - ``TASK_PATTERNS``: compiled regexes per task type (system + user prompt).
  - ``STRUCTURAL_DETECTORS``: callables that inspect ``ClassifierInput``
    structural properties (message count, response_format, etc.).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from classifier.schemas import ClassifierInput

# ── Keyword lists ──────────────────────────────────────────────────────
# Each entry is ``(keyword_or_phrase, weight)``.
# Weights let us boost strong indicators (e.g. "summarize this article"
# is more diagnostic than the word "summary" which might appear anywhere).

TASK_KEYWORDS: dict[str, list[tuple[str, float]]] = {
    "summarization": [
        ("summarize", 2.0),
        ("summarise", 2.0),
        ("summarize the", 1.5),
        ("summarise the", 1.5),
        ("summarize this", 1.5),
        ("summarise this", 1.5),
        ("summary", 1.5),
        ("tldr", 3.0),
        ("tl;dr", 3.0),
        ("condense", 1.5),
        ("shorten", 1.2),
        ("brief overview", 1.5),
        ("key points", 1.2),
        ("main takeaways", 1.5),
        ("abstract", 1.0),
        ("recap", 1.5),
        ("digest", 1.2),
        ("boil down", 1.5),
        ("in a nutshell", 1.5),
    ],
    "extraction": [
        ("extract", 2.0),
        ("pull out", 1.5),
        ("identify the", 1.0),
        ("find all", 1.2),
        ("named entities", 2.0),
        ("ner", 1.5),
        ("parse", 1.2),
        ("detect", 1.0),
        ("locate", 1.0),
        ("pick out", 1.2),
        ("get the names", 1.5),
        ("extract the following", 2.0),
        ("key-value", 1.5),
        ("data extraction", 2.0),
        ("entity recognition", 2.0),
    ],
    "classification": [
        ("classify", 2.0),
        ("categorize", 2.0),
        ("categorise", 2.0),
        ("label", 1.5),
        ("sentiment", 2.0),
        ("positive or negative", 1.5),
        ("which category", 1.5),
        ("assign a category", 2.0),
        ("assign a label", 2.0),
        ("is this spam", 1.5),
        ("topic classification", 2.0),
        ("intent detection", 2.0),
        ("classify the following", 2.0),
        ("one of the following labels", 2.0),
        ("from the following labels", 2.0),
        ("from the following categories", 2.0),
        ("select the best category", 2.0),
        ("tag this", 1.2),
    ],
    "code_generation": [
        ("write code", 2.0),
        ("write a function", 2.0),
        ("write a script", 2.0),
        ("implement", 1.2),
        ("code this", 2.0),
        ("write python", 2.0),
        ("write javascript", 2.0),
        ("write sql", 1.5),
        ("generate code", 2.0),
        ("programming", 1.0),
        ("refactor", 1.5),
        ("debug", 1.2),
        ("fix this code", 1.5),
        ("unit test", 1.5),
        ("```python", 1.5),
        ("```javascript", 1.5),
        ("```typescript", 1.5),
        ("def ", 1.0),
        ("function(", 1.0),
        ("import ", 0.5),
        ("code review", 1.5),
        ("explain this code", 1.5),
    ],
    "question_answering": [
        ("answer the following question", 2.0),
        ("answer the question", 2.0),
        ("based on the context", 1.5),
        ("given the text", 1.2),
        ("according to", 1.0),
        ("what is", 0.8),
        ("what are", 0.8),
        ("how does", 0.8),
        ("why does", 0.8),
        ("explain", 0.8),
        ("reading comprehension", 2.0),
        ("use the following context", 2.0),
        ("answer using only", 1.5),
        ("refer to the document", 1.5),
    ],
    "translation": [
        ("translate", 2.5),
        ("translation", 2.0),
        ("convert to english", 2.0),
        ("convert to spanish", 2.0),
        ("convert to french", 2.0),
        ("into english", 1.5),
        ("into spanish", 1.5),
        ("into french", 1.5),
        ("into german", 1.5),
        ("into chinese", 1.5),
        ("into japanese", 1.5),
        ("in english", 0.8),
        ("from english to", 2.0),
        ("localize", 1.5),
        ("localise", 1.5),
        ("target language", 2.0),
        ("source language", 2.0),
    ],
    "creative_writing": [
        ("write a story", 2.0),
        ("story about", 1.5),
        ("short story", 2.0),
        ("write a poem", 2.0),
        ("write a blog", 1.5),
        ("write a post", 1.2),
        ("creative", 1.0),
        ("marketing copy", 2.0),
        ("ad copy", 2.0),
        ("tagline", 1.5),
        ("slogan", 1.5),
        ("brainstorm", 1.2),
        ("generate ideas", 1.0),
        ("narrative", 1.2),
        ("fiction", 1.5),
        ("write an email", 1.2),
        ("draft a letter", 1.2),
        ("compose", 1.0),
        ("rewrite this", 1.0),
        ("make it more engaging", 1.5),
        ("write a description", 1.0),
    ],
    "structured_output": [
        ("json", 1.5),
        ("output as json", 2.0),
        ("return json", 2.0),
        ("json schema", 2.0),
        ("json format", 2.0),
        ("yaml", 1.5),
        ("xml", 1.5),
        ("csv", 1.2),
        ("output format", 1.0),
        ("structured", 1.0),
        ("markdown table", 1.5),
        ("return a table", 1.2),
        ("respond with json", 2.0),
        ('{"', 1.0),
        ("valid json", 2.0),
    ],
}

# ── Compiled regex patterns ────────────────────────────────────────────
# Each pattern targets strong indicators in the combined prompt text.

_FLAGS = re.IGNORECASE | re.DOTALL

TASK_PATTERNS: dict[str, list[tuple[re.Pattern[str], float]]] = {
    "summarization": [
        (re.compile(r"\b(summarize|summarise)\b.{0,40}\b(text|article|document|passage|content|email|report|page)\b", _FLAGS), 3.0),
        (re.compile(r"\b(provide|give|write|create)\b.{0,20}\b(summary|synopsis|overview|abstract)\b", _FLAGS), 2.5),
        (re.compile(r"\btl\s*;?\s*dr\b", _FLAGS), 3.0),
        (re.compile(r"\bkey\s+(points|takeaways|findings|insights)\b", _FLAGS), 2.0),
        (re.compile(r"\bin\s+\d+\s+(words?|sentences?|bullet\s*points?|paragraphs?)\b", _FLAGS), 1.5),
    ],
    "extraction": [
        (re.compile(r"\bextract\b.{0,30}\b(data|information|entities|names|dates|numbers|fields|values)\b", _FLAGS), 3.0),
        (re.compile(r"\b(named\s+entit|ner|entity\s+recognition)\b", _FLAGS), 3.0),
        (re.compile(r"\b(pull|get|find|identify|locate)\s+(out\s+)?(all\s+)?(the\s+)?\b(names|emails|phone|dates|addresses|urls|amounts)\b", _FLAGS), 2.5),
        (re.compile(r"\bparse\b.{0,20}\b(document|text|input|resume|invoice|receipt)\b", _FLAGS), 2.0),
    ],
    "classification": [
        (re.compile(r"\b(classify|categorize|categorise)\b.{0,30}\b(text|input|message|email|review|comment|ticket)\b", _FLAGS), 3.0),
        (re.compile(r"\b(sentiment|polarity)\s*(analysis|detection|score)?\b", _FLAGS), 3.0),
        (re.compile(r"\b(one|from)\s+(of\s+)?(the\s+)?following\s+(labels|categories|classes|options)\b", _FLAGS), 2.5),
        (re.compile(r"\b(positive|negative|neutral)\b.*\b(positive|negative|neutral)\b", _FLAGS), 2.0),
        (re.compile(r"\bspam\s*(or|vs\.?|/)\s*not\s*spam\b", _FLAGS), 3.0),
    ],
    "code_generation": [
        (re.compile(r"\b(write|create|generate|implement|build|code)\b.{0,40}\b(function|class|script|program|module|api|endpoint|component|test)\b", _FLAGS), 3.0),
        (re.compile(r"\b(python|javascript|typescript|java|rust|go|c\+\+|ruby|sql|html|css)\s+(code|function|script|class)\b", _FLAGS), 3.0),
        (re.compile(r"```\w+\n", _FLAGS), 2.0),
        (re.compile(r"\b(refactor|debug|fix|optimize|review)\s+(this|the|my)?\s*(code|function|script|bug)\b", _FLAGS), 2.5),
    ],
    "question_answering": [
        (re.compile(r"\b(answer|respond\s+to)\b.{0,20}\b(question|query|queries)\b", _FLAGS), 3.0),
        (re.compile(r"\bbased\s+on\s+(the\s+)?(context|passage|text|document|information)\b.{0,60}\b(answer|respond|reply)\b", _FLAGS), 3.0),
        (re.compile(r"\buse\s+(only\s+)?(the\s+)?(provided|following|above|given)\s+(context|text|information|document)\b", _FLAGS), 2.5),
        (re.compile(r"\breading\s+comprehension\b", _FLAGS), 3.0),
    ],
    "translation": [
        (re.compile(r"\btranslate\b.{0,30}\b(to|into|from)\b.{0,20}\b(english|spanish|french|german|chinese|japanese|korean|portuguese|italian|arabic|hindi|russian|dutch)\b", _FLAGS), 3.5),
        (re.compile(r"\b(source|target)\s+language\b", _FLAGS), 2.5),
        (re.compile(r"\bfrom\s+(english|spanish|french|german|chinese|japanese)\s+to\s+(english|spanish|french|german|chinese|japanese)\b", _FLAGS), 3.5),
    ],
    "creative_writing": [
        (re.compile(r"\bwrite\b.{0,40}\b(story|poem|essay|blog|article|post|narrative|script|dialogue|letter|email|copy)\b", _FLAGS), 3.0),
        (re.compile(r"\b(marketing|ad|advertising)\s+(copy|content|text|material)\b", _FLAGS), 3.0),
        (re.compile(r"\b(brainstorm|ideate|generate)\b.{0,20}\b(ideas|names|titles|headlines|slogans|taglines)\b", _FLAGS), 2.5),
        (re.compile(r"\bmake\s+it\s+(more\s+)?(engaging|creative|compelling|persuasive|catchy|witty)\b", _FLAGS), 2.0),
    ],
    "structured_output": [
        (re.compile(r"\b(output|respond|return|format|give)\b.{0,20}\b(as\s+|in\s+)?(valid\s+)?(json|yaml|xml|csv)\b", _FLAGS), 3.0),
        (re.compile(r"\bjson\s+schema\b", _FLAGS), 3.0),
        (re.compile(r'["\']type["\']\s*:\s*["\']json_object["\']', _FLAGS), 3.0),
        (re.compile(r"\breturn\s+a\s+(markdown\s+)?table\b", _FLAGS), 2.0),
    ],
}


# ── Structural detectors ───────────────────────────────────────────────
# Each callable receives a ClassifierInput and returns
# ``(detected: bool, signal_detail: str, weight: float)``.

def _detect_multi_turn(inp: ClassifierInput) -> tuple[bool, str, float]:
    """Messages with > 4 entries are likely multi-turn conversations."""
    if inp.message_count > 4:
        return True, "message_count_gt_4", 6.0
    return False, "", 0.0


def _detect_response_format_json(inp: ClassifierInput) -> tuple[bool, str, float]:
    """``response_format: {"type": "json_object"}`` → structured_output."""
    rf = inp.response_format or inp.raw_body.get("response_format")
    if isinstance(rf, dict) and rf.get("type") == "json_object":
        return True, "response_format_json_object", 6.0
    return False, "", 0.0


def _detect_json_schema_in_body(inp: ClassifierInput) -> tuple[bool, str, float]:
    """``response_format: {"type": "json_schema", ...}`` → structured_output."""
    rf = inp.response_format or inp.raw_body.get("response_format")
    if isinstance(rf, dict) and rf.get("type") == "json_schema":
        return True, "response_format_json_schema", 7.0
    return False, "", 0.0


def _detect_code_blocks_in_prompt(inp: ClassifierInput) -> tuple[bool, str, float]:
    """Fenced code blocks in the user prompt suggest code-related tasks."""
    if "```" in inp.user_prompt:
        return True, "code_block_in_prompt", 1.5
    return False, "", 0.0


# Maps: task_type → list of structural detector functions.
STRUCTURAL_DETECTORS: dict[str, list] = {
    "multi_turn_chat": [_detect_multi_turn],
    "structured_output": [_detect_response_format_json, _detect_json_schema_in_body],
    "code_generation": [_detect_code_blocks_in_prompt],
}


# ── Complexity signal patterns ─────────────────────────────────────────
# Used by the prompt complexity scorer.

COT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bstep[\s-]by[\s-]step\b", _FLAGS),
    re.compile(r"\bthink\s+(through|carefully|about)\b", _FLAGS),
    re.compile(r"\bchain[\s-]of[\s-]thought\b", _FLAGS),
    re.compile(r"\breason(ing)?\s+(through|step)\b", _FLAGS),
    re.compile(r"\blet'?s\s+think\b", _FLAGS),
    re.compile(r"\bexplain\s+your\s+(reasoning|logic|thought)\b", _FLAGS),
    re.compile(r"\bshow\s+your\s+work\b", _FLAGS),
]

JSON_SCHEMA_PATTERN: re.Pattern[str] = re.compile(
    r'["\']type["\']\s*:\s*["\'](?:object|array|string|number|integer|boolean)["\']',
    _FLAGS,
)

INSTRUCTION_SPECIFICITY_PATTERNS: list[tuple[re.Pattern[str], float]] = [
    # Very specific instructions boost complexity
    (re.compile(r"\bmust\b", _FLAGS), 0.2),
    (re.compile(r"\bexactly\b", _FLAGS), 0.3),
    (re.compile(r"\bdo not\b", _FLAGS), 0.2),
    (re.compile(r"\brequired\b", _FLAGS), 0.2),
    (re.compile(r"\bconstraints?\b", _FLAGS), 0.3),
    (re.compile(r"\brules?\s*:", _FLAGS), 0.3),
    (re.compile(r"\bformat\s*:", _FLAGS), 0.2),
    (re.compile(r"\bexample\s*(output|response)?\s*:", _FLAGS), 0.2),
    (re.compile(r"\btemperature\b", _FLAGS), 0.1),
]
