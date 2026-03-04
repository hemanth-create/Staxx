"""
Tests for the full classification engine (engine.py).

These tests exercise the end-to-end ``classify()`` function including
input normalisation, Tier 1 → Tier 2 fallback, and complexity scoring.

At least 10 diverse prompt examples are included as specified.
"""

from __future__ import annotations

import pytest

from classifier.engine import classify
from classifier.schemas import ClassificationTier, TaskClassification


# ── Helpers ─────────────────────────────────────────────────────────────

def _assert_classification(
    result: TaskClassification,
    expected_type: str,
    min_confidence: float = 0.5,
) -> None:
    """Assert a classification result matches expectations."""
    assert result.task_type == expected_type, (
        f"Expected {expected_type}, got {result.task_type} "
        f"(confidence={result.confidence}, signals={result.signals})"
    )
    assert result.confidence >= min_confidence
    assert 0.0 <= result.prompt_complexity_score <= 1.0
    assert result.classification_tier in (
        ClassificationTier.RULE_ENGINE.value,
        ClassificationTier.ML_CLASSIFIER.value,
    )


# ── Test Suite: 15 diverse real-world prompts ──────────────────────────

class TestEndToEndClassification:
    """End-to-end tests with diverse, realistic prompts."""

    # 1. Summarization — Customer support email digest
    def test_01_summarize_email_thread(self) -> None:
        body = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that summarizes email threads."},
                {"role": "user", "content": (
                    "Summarize the following email thread into 3 key action items:\n\n"
                    "From: alice@company.com\nSubject: Q4 Budget Review\n"
                    "Hi team, I've reviewed the Q4 numbers and we're 15% over budget...\n"
                    "---\nFrom: bob@company.com\nRe: Q4 Budget Review\n"
                    "Thanks Alice. I think we should cut the marketing spend...\n"
                    "---\nFrom: carol@company.com\nRe: Q4 Budget Review\n"
                    "Agreed with Bob. Let's also postpone the new hire requests..."
                )},
            ],
        }
        result = classify(body)
        _assert_classification(result, "summarization", min_confidence=0.85)

    # 2. Extraction — Invoice parsing
    def test_02_extract_invoice_fields(self) -> None:
        body = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "Extract structured data from invoices."},
                {"role": "user", "content": (
                    "Extract the following fields from this invoice: "
                    "vendor name, invoice date, total amount, line items.\n\n"
                    "INVOICE #12345\nVendor: Acme Corp\nDate: 2024-03-15\n"
                    "Item: Widget A — $50.00\nItem: Widget B — $75.00\nTotal: $125.00"
                )},
            ],
        }
        result = classify(body)
        _assert_classification(result, "extraction", min_confidence=0.85)

    # 3. Classification — Support ticket routing
    def test_03_classify_support_ticket(self) -> None:
        body = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": (
                    "Classify the following support ticket into one of the following "
                    "categories: billing, technical, account, feature_request, other."
                )},
                {"role": "user", "content": (
                    "I was charged twice on my credit card for the same subscription "
                    "last month. Please refund the duplicate charge."
                )},
            ],
        }
        result = classify(body)
        _assert_classification(result, "classification", min_confidence=0.85)

    # 4. Code generation — Python function
    def test_04_generate_python_function(self) -> None:
        body = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "You are an expert Python engineer."},
                {"role": "user", "content": (
                    "Write a Python function that takes a list of timestamps and "
                    "returns the median time gap between consecutive events. "
                    "Include type hints and handle edge cases (empty list, single element). "
                    "Write unit tests using pytest."
                )},
            ],
        }
        result = classify(body)
        _assert_classification(result, "code_generation", min_confidence=0.85)

    # 5. Question answering — RAG-style
    def test_05_qa_with_context(self) -> None:
        body = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": (
                    "Answer the question based on the context provided. "
                    "Use only the provided context. If the answer is not in the "
                    "context, say 'I don't have enough information.'"
                )},
                {"role": "user", "content": (
                    "Context: The company was founded in 2019 by three MIT graduates. "
                    "It raised $5M in Series A funding in 2021 and expanded to "
                    "15 countries by 2023.\n\n"
                    "Question: When was the company founded and how much did they raise?"
                )},
            ],
        }
        result = classify(body)
        _assert_classification(result, "question_answering", min_confidence=0.85)

    # 6. Translation — English to French
    def test_06_translate_to_french(self) -> None:
        body = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": (
                    "Translate the following product description from English to French:\n\n"
                    "'Our premium wireless headphones deliver crystal-clear audio "
                    "with 30-hour battery life and active noise cancellation.'"
                )},
            ],
        }
        result = classify(body)
        _assert_classification(result, "translation", min_confidence=0.85)

    # 7. Creative writing — Marketing copy
    def test_07_write_marketing_copy(self) -> None:
        body = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "You are a creative marketing copywriter."},
                {"role": "user", "content": (
                    "Write a compelling ad copy for a new eco-friendly water bottle. "
                    "The target audience is health-conscious millennials. "
                    "Make it engaging, include a catchy tagline and a slogan."
                )},
            ],
        }
        result = classify(body)
        _assert_classification(result, "creative_writing", min_confidence=0.85)

    # 8. Structured output — JSON response_format
    def test_08_structured_json_output(self) -> None:
        body = {
            "model": "gpt-4o",
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Return the analysis as valid JSON."},
                {"role": "user", "content": "Analyze the pros and cons of remote work."},
            ],
        }
        result = classify(body)
        _assert_classification(result, "structured_output", min_confidence=0.85)

    # 9. Multi-turn chat — Long conversation
    def test_09_multi_turn_conversation(self) -> None:
        body = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hi, I need help planning a trip to Japan."},
                {"role": "assistant", "content": "I'd love to help! When are you planning to visit?"},
                {"role": "user", "content": "In April, for the cherry blossoms."},
                {"role": "assistant", "content": "Great choice! Do you have a budget in mind?"},
                {"role": "user", "content": "Around $3000 for two weeks."},
                {"role": "assistant", "content": "That's doable. Let me suggest an itinerary."},
                {"role": "user", "content": "Yes please! Focus on Tokyo and Kyoto."},
            ],
        }
        result = classify(body)
        _assert_classification(result, "multi_turn_chat", min_confidence=0.85)

    # 10. Classification — Spam detection
    def test_10_spam_classification(self) -> None:
        body = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "Classify the following email as spam or not spam."},
                {"role": "user", "content": (
                    "Subject: You've won $1,000,000!\n"
                    "Click here to claim your prize now! Limited time offer!"
                )},
            ],
        }
        result = classify(body)
        _assert_classification(result, "classification", min_confidence=0.85)


# ── Test: Anthropic format normalisation ───────────────────────────────

class TestInputNormalisation:
    def test_anthropic_format_with_top_level_system(self) -> None:
        """Anthropic puts the system prompt in a top-level 'system' field."""
        body = {
            "model": "claude-sonnet-4-20250514",
            "system": "You are a helpful assistant. Summarize texts concisely.",
            "messages": [
                {"role": "user", "content": "Summarize this article about climate change..."},
            ],
        }
        result = classify(body)
        _assert_classification(result, "summarization", min_confidence=0.85)


# ── Test: Complexity scoring integration ───────────────────────────────

class TestComplexityIntegration:
    def test_simple_prompt_low_complexity(self) -> None:
        body = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": "Classify this as positive or negative: 'I love it!'"},
            ],
        }
        result = classify(body)
        assert result.prompt_complexity_score < 0.4

    def test_complex_prompt_higher_complexity(self) -> None:
        body = {
            "model": "gpt-4o",
            "response_format": {"type": "json_schema", "json_schema": {"type": "object"}},
            "messages": [
                {"role": "system", "content": (
                    "You are an expert legal document analyzer. You must follow "
                    "these constraints exactly: 1) Extract all parties. 2) Identify "
                    "key dates. 3) Format as valid JSON matching the schema. "
                    "Do not include any information not in the document. "
                    "Think through each section step-by-step before producing output. "
                    "Rules: no hallucination, no assumptions."
                )},
                {"role": "user", "content": "Analyze the following 50-page contract..." + "x" * 5000},
            ],
        }
        result = classify(body)
        assert result.prompt_complexity_score > 0.4


# ── Test: Output schema validation ─────────────────────────────────────

class TestOutputSchema:
    def test_result_has_all_fields(self) -> None:
        body = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Summarize this text."}],
        }
        result = classify(body)
        assert isinstance(result.task_type, str)
        assert isinstance(result.confidence, float)
        assert isinstance(result.classification_tier, str)
        assert isinstance(result.signals, list)
        assert isinstance(result.prompt_complexity_score, float)
        assert 0.0 <= result.confidence <= 1.0
        assert 0.0 <= result.prompt_complexity_score <= 1.0

    def test_signals_are_strings(self) -> None:
        body = {
            "model": "gpt-4o",
            "messages": [
                {"role": "user", "content": "Translate this to Spanish: Hello world"},
            ],
        }
        result = classify(body)
        for signal in result.signals:
            assert isinstance(signal, str)


# ── Test: Error handling ───────────────────────────────────────────────

class TestErrorHandling:
    def test_empty_body(self) -> None:
        result = classify({})
        assert result.task_type == "other"
        assert result.confidence == 0.0

    def test_missing_messages(self) -> None:
        result = classify({"model": "gpt-4o"})
        assert result.task_type == "other"

    def test_no_args_raises(self) -> None:
        with pytest.raises(ValueError, match="Either raw_body or input_data"):
            classify()
