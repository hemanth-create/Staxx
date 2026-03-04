"""
Tests for the Tier 1 Rule Engine.

Each test constructs a realistic ``ClassifierInput`` and verifies the
rule engine detects the correct task type with appropriate confidence.
"""

from __future__ import annotations

import pytest

from classifier.rule_engine import TIER1_CONFIDENCE_THRESHOLD, classify
from classifier.schemas import ClassifierInput, TaskType


# ── Helpers ─────────────────────────────────────────────────────────────

def _make_input(
    system: str = "",
    user: str = "",
    message_count: int | None = None,
    response_format: dict | None = None,
    model: str = "gpt-4o",
) -> ClassifierInput:
    """Build a ClassifierInput from simple strings."""
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    if user:
        messages.append({"role": "user", "content": user})
    # Pad with assistant/user turns if we need higher message count.
    if message_count and message_count > len(messages):
        for i in range(message_count - len(messages)):
            role = "assistant" if i % 2 == 0 else "user"
            messages.append({"role": role, "content": f"Turn {i}"})
    return ClassifierInput(
        messages=messages,
        model=model,
        response_format=response_format,
    )


# ── Summarization ──────────────────────────────────────────────────────

class TestSummarization:
    def test_explicit_summarize_keyword(self) -> None:
        inp = _make_input(
            system="You are a helpful assistant.",
            user="Summarize the following article in 3 bullet points: ...",
        )
        best, _ = classify(inp)
        assert best is not None
        assert best.task_type == TaskType.SUMMARIZATION
        assert best.score >= TIER1_CONFIDENCE_THRESHOLD

    def test_tldr(self) -> None:
        inp = _make_input(user="TL;DR of the following meeting notes: ...")
        best, _ = classify(inp)
        assert best is not None
        assert best.task_type == TaskType.SUMMARIZATION

    def test_condense_with_pattern(self) -> None:
        inp = _make_input(
            system="Provide a brief overview of texts given to you.",
            user="Condense this 5-page report into key takeaways.",
        )
        best, _ = classify(inp)
        assert best is not None
        assert best.task_type == TaskType.SUMMARIZATION


# ── Extraction ─────────────────────────────────────────────────────────

class TestExtraction:
    def test_named_entity_extraction(self) -> None:
        inp = _make_input(
            system="You are an NER system. Extract all named entities from the text.",
            user="Apple Inc. CEO Tim Cook announced new products in Cupertino on March 5.",
        )
        best, _ = classify(inp)
        assert best is not None
        assert best.task_type == TaskType.EXTRACTION
        assert best.score >= TIER1_CONFIDENCE_THRESHOLD

    def test_data_extraction(self) -> None:
        inp = _make_input(
            user="Extract the following fields from this invoice: date, total, vendor name.",
        )
        best, _ = classify(inp)
        assert best is not None
        assert best.task_type == TaskType.EXTRACTION


# ── Classification ─────────────────────────────────────────────────────

class TestClassification:
    def test_sentiment_analysis(self) -> None:
        inp = _make_input(
            system="Classify the sentiment of the following review as positive, negative, or neutral.",
            user="The hotel was amazing, staff were friendly, but the food was mediocre.",
        )
        best, _ = classify(inp)
        assert best is not None
        assert best.task_type == TaskType.CLASSIFICATION
        assert best.score >= TIER1_CONFIDENCE_THRESHOLD

    def test_label_assignment(self) -> None:
        inp = _make_input(
            system="Assign a category from the following labels: bug, feature_request, question.",
            user="I can't log in to my account since yesterday.",
        )
        best, _ = classify(inp)
        assert best is not None
        assert best.task_type == TaskType.CLASSIFICATION


# ── Code Generation ────────────────────────────────────────────────────

class TestCodeGeneration:
    def test_write_function(self) -> None:
        inp = _make_input(
            user="Write a Python function that sorts a list of dictionaries by a given key.",
        )
        best, _ = classify(inp)
        assert best is not None
        assert best.task_type == TaskType.CODE_GENERATION
        assert best.score >= TIER1_CONFIDENCE_THRESHOLD

    def test_debug_code(self) -> None:
        inp = _make_input(
            user="Fix this code that throws an IndexError:\n```python\ndef get(lst, i): return lst[i]\n```",
        )
        best, _ = classify(inp)
        assert best is not None
        assert best.task_type == TaskType.CODE_GENERATION


# ── Question Answering ─────────────────────────────────────────────────

class TestQuestionAnswering:
    def test_context_based_qa(self) -> None:
        inp = _make_input(
            system="Answer the question based on the context provided. Use only the provided context.",
            user="Context: The Eiffel Tower is 330m tall.\nQuestion: How tall is the Eiffel Tower?",
        )
        best, _ = classify(inp)
        assert best is not None
        assert best.task_type == TaskType.QUESTION_ANSWERING
        assert best.score >= TIER1_CONFIDENCE_THRESHOLD


# ── Translation ────────────────────────────────────────────────────────

class TestTranslation:
    def test_translate_to_language(self) -> None:
        inp = _make_input(
            user="Translate the following text from English to Spanish: 'Hello, how are you?'",
        )
        best, _ = classify(inp)
        assert best is not None
        assert best.task_type == TaskType.TRANSLATION
        assert best.score >= TIER1_CONFIDENCE_THRESHOLD


# ── Creative Writing ───────────────────────────────────────────────────

class TestCreativeWriting:
    def test_write_story(self) -> None:
        inp = _make_input(
            user="Write a short story about a robot who discovers emotions for the first time.",
        )
        best, _ = classify(inp)
        assert best is not None
        assert best.task_type == TaskType.CREATIVE_WRITING
        assert best.score >= TIER1_CONFIDENCE_THRESHOLD

    def test_marketing_copy(self) -> None:
        inp = _make_input(
            system="You are a marketing copywriter.",
            user="Write compelling ad copy for a new eco-friendly water bottle. Make it engaging and catchy.",
        )
        best, _ = classify(inp)
        assert best is not None
        assert best.task_type == TaskType.CREATIVE_WRITING


# ── Structured Output ──────────────────────────────────────────────────

class TestStructuredOutput:
    def test_response_format_json_object(self) -> None:
        inp = _make_input(
            user="List the top 5 programming languages.",
            response_format={"type": "json_object"},
        )
        best, _ = classify(inp)
        assert best is not None
        assert best.task_type == TaskType.STRUCTURED_OUTPUT
        assert best.score >= TIER1_CONFIDENCE_THRESHOLD

    def test_json_in_prompt(self) -> None:
        inp = _make_input(
            system="Always output valid JSON matching the provided schema.",
            user='Return JSON with keys "name", "age", "email" for the person described.',
        )
        best, _ = classify(inp)
        assert best is not None
        assert best.task_type == TaskType.STRUCTURED_OUTPUT


# ── Multi-Turn Chat ────────────────────────────────────────────────────

class TestMultiTurnChat:
    def test_long_conversation(self) -> None:
        inp = _make_input(
            system="You are a helpful assistant.",
            user="What should I have for dinner tonight?",
            message_count=8,
        )
        best, _ = classify(inp)
        assert best is not None
        assert best.task_type == TaskType.MULTI_TURN_CHAT
        assert best.score >= TIER1_CONFIDENCE_THRESHOLD


# ── Edge Cases ─────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_input_returns_none(self) -> None:
        inp = _make_input()
        best, _ = classify(inp)
        assert best is None  # No signals → below threshold

    def test_ambiguous_input_below_threshold(self) -> None:
        """A vague prompt shouldn't confidently classify."""
        inp = _make_input(user="Hello, help me with something.")
        best, _ = classify(inp)
        # Either None or below threshold.
        if best is not None:
            assert best.score < TIER1_CONFIDENCE_THRESHOLD

    def test_all_results_returned(self) -> None:
        """Verify the ranked results list includes all task types."""
        inp = _make_input(user="Summarize this article about Python code.")
        _, all_results = classify(inp)
        task_types_in_results = {r.task_type for r in all_results}
        # Should have an entry per task type (excluding OTHER).
        assert len(task_types_in_results) >= 8
