"""
Staxx Intelligence — Shadow Evaluator Tests

Tests for:
  • Prompt hash computation (determinism, uniqueness)
  • Output validation (JSON, empty, truncation)
  • PII detection
  • Adapter interface contract
  • End-to-end eval flow with mocked adapter
"""

from __future__ import annotations

import hashlib
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shadow_eval.adapters.base import AdapterRequest, AdapterResponse
from shadow_eval.evaluator import compute_prompt_hash
from shadow_eval.validators import (
    PIICheckResult,
    ValidationResult,
    check_pii,
    validate_output,
)


# ===========================================================================
# Prompt Hash Tests
# ===========================================================================


class TestPromptHash:
    """Tests for compute_prompt_hash determinism and collision avoidance."""

    def test_deterministic(self):
        """Same messages should always produce the same hash."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Summarize this article."},
        ]
        h1 = compute_prompt_hash(messages)
        h2 = compute_prompt_hash(messages)
        assert h1 == h2

    def test_different_content_different_hash(self):
        m1 = [{"role": "user", "content": "Hello"}]
        m2 = [{"role": "user", "content": "Goodbye"}]
        assert compute_prompt_hash(m1) != compute_prompt_hash(m2)

    def test_different_roles_different_hash(self):
        m1 = [{"role": "user", "content": "Hello"}]
        m2 = [{"role": "system", "content": "Hello"}]
        assert compute_prompt_hash(m1) != compute_prompt_hash(m2)

    def test_hash_is_sha256(self):
        messages = [{"role": "user", "content": "test"}]
        h = compute_prompt_hash(messages)
        assert len(h) == 64  # SHA-256 hex digest length

    def test_empty_messages(self):
        h = compute_prompt_hash([])
        assert len(h) == 64  # Still a valid hash

    def test_multi_message_order_matters(self):
        m1 = [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "second"},
        ]
        m2 = [
            {"role": "assistant", "content": "second"},
            {"role": "user", "content": "first"},
        ]
        assert compute_prompt_hash(m1) != compute_prompt_hash(m2)


# ===========================================================================
# Output Validation Tests
# ===========================================================================


class TestValidateOutput:
    """Tests for the output validation logic."""

    def test_valid_text_output(self):
        result = validate_output("This is a valid summary.", "summarization")
        assert result.is_valid is True
        assert result.output_empty is False
        assert result.output_truncated is False
        assert result.json_valid is None  # Not a JSON task

    def test_empty_output(self):
        result = validate_output("", "summarization")
        assert result.output_empty is True
        assert result.is_valid is False

    def test_whitespace_only_output(self):
        result = validate_output("   \n  \t  ", "summarization")
        assert result.output_empty is True
        assert result.is_valid is False

    def test_truncation_by_finish_reason(self):
        result = validate_output("Some text that...", "summarization", finish_reason="length")
        assert result.output_truncated is True
        assert result.is_valid is False

    def test_truncation_by_ellipsis(self):
        result = validate_output("The result is...", "summarization")
        assert result.output_truncated is True

    def test_valid_json_extraction_task(self):
        valid_json = '{"name": "John", "age": 30}'
        result = validate_output(valid_json, "extraction")
        assert result.json_valid is True
        assert result.is_valid is True

    def test_invalid_json_extraction_task(self):
        invalid_json = "name: John, age: 30"
        result = validate_output(invalid_json, "extraction")
        assert result.json_valid is False
        assert result.is_valid is False

    def test_json_in_code_block(self):
        """JSON wrapped in markdown code block should still be valid."""
        output = '```json\n{"key": "value"}\n```'
        result = validate_output(output, "extraction")
        assert result.json_valid is True

    def test_auto_detect_json_output(self):
        """Even non-JSON tasks should validate if output starts with {."""
        output = '{"result": "success"}'
        result = validate_output(output, "summarization")
        assert result.json_valid is True

    def test_none_json_valid_for_non_json_task(self):
        """Non-JSON output for non-JSON task should have json_valid=None."""
        result = validate_output("Plain text summary", "summarization")
        assert result.json_valid is None

    def test_truncation_indicators(self):
        for indicator in ("...", "[truncated]", "[continued]"):
            result = validate_output(f"Some text {indicator}", "summarization")
            assert result.output_truncated is True, f"Failed for indicator: {indicator}"


# ===========================================================================
# PII Detection Tests
# ===========================================================================


class TestPIIDetection:
    """Tests for the PII regex filter."""

    def test_no_pii(self):
        result = check_pii("This is a clean prompt about summarization.")
        assert result.contains_pii is False
        assert result.matched_types == []

    def test_email_detected(self):
        result = check_pii("Contact john@example.com for details.")
        assert result.contains_pii is True
        assert "email" in result.matched_types

    def test_phone_us_detected(self):
        result = check_pii("Call me at (555) 123-4567.")
        assert result.contains_pii is True
        assert "phone_us" in result.matched_types

    def test_phone_intl_detected(self):
        result = check_pii("Reach us at +44 20 7946 0958.")
        assert result.contains_pii is True
        assert "phone_intl" in result.matched_types

    def test_ssn_detected(self):
        result = check_pii("SSN: 123-45-6789")
        assert result.contains_pii is True
        assert "ssn" in result.matched_types

    def test_credit_card_detected(self):
        result = check_pii("Card: 4111 1111 1111 1111")
        assert result.contains_pii is True
        assert "credit_card" in result.matched_types

    def test_multiple_pii_types(self):
        result = check_pii("Email john@example.com or call 555-123-4567")
        assert result.contains_pii is True
        assert len(result.matched_types) >= 2

    def test_empty_string(self):
        result = check_pii("")
        assert result.contains_pii is False

    def test_match_count(self):
        result = check_pii("john@a.com and jane@b.com")
        assert result.match_count >= 2


# ===========================================================================
# Adapter Interface Tests
# ===========================================================================


class TestAdapterInterface:
    """Tests that verify the adapter interface contract."""

    def test_adapter_request_defaults(self):
        req = AdapterRequest(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello"}],
        )
        assert req.temperature == 0.0
        assert req.max_tokens == 4096
        assert req.timeout_seconds == 30.0

    def test_adapter_response_success(self):
        resp = AdapterResponse(
            text_output="Hello!",
            input_tokens=10,
            output_tokens=5,
            latency_ms=200,
        )
        assert resp.success is True

    def test_adapter_response_error(self):
        resp = AdapterResponse(error="API key invalid")
        assert resp.success is False

    def test_adapter_response_empty_output(self):
        resp = AdapterResponse(text_output="")
        assert resp.success is False

    def test_adapter_response_defaults(self):
        resp = AdapterResponse()
        assert resp.text_output == ""
        assert resp.input_tokens == 0
        assert resp.output_tokens == 0
        assert resp.latency_ms == 0
        assert resp.error is None
        assert resp.raw_response == {}


# ===========================================================================
# Adapter supports_model Tests
# ===========================================================================


class TestAdapterModelSupport:
    """Tests that each adapter correctly identifies supported models."""

    def test_openai_supports_gpt4o(self):
        from shadow_eval.adapters.openai_adapter import OpenAIAdapter
        adapter = OpenAIAdapter()
        assert adapter.supports_model("gpt-4o") is True
        assert adapter.supports_model("gpt-4o-mini") is True
        assert adapter.supports_model("gpt-4o-2024-08-06") is True
        assert adapter.supports_model("gpt-3.5-turbo") is True
        assert adapter.supports_model("o1") is True
        assert adapter.supports_model("o1-mini") is True

    def test_openai_rejects_claude(self):
        from shadow_eval.adapters.openai_adapter import OpenAIAdapter
        adapter = OpenAIAdapter()
        assert adapter.supports_model("claude-3-haiku") is False
        assert adapter.supports_model("gemini-1.5-pro") is False

    def test_anthropic_supports_claude(self):
        from shadow_eval.adapters.anthropic_adapter import AnthropicAdapter
        adapter = AnthropicAdapter()
        assert adapter.supports_model("claude-3-5-sonnet-20241022") is True
        assert adapter.supports_model("claude-haiku-4-20250514") is True
        assert adapter.supports_model("claude-opus-4-20250514") is True

    def test_anthropic_rejects_gpt(self):
        from shadow_eval.adapters.anthropic_adapter import AnthropicAdapter
        adapter = AnthropicAdapter()
        assert adapter.supports_model("gpt-4o") is False

    def test_google_supports_gemini(self):
        from shadow_eval.adapters.google_adapter import GoogleAdapter
        adapter = GoogleAdapter()
        assert adapter.supports_model("gemini-2.0-flash") is True
        assert adapter.supports_model("gemini-1.5-pro") is True
        assert adapter.supports_model("gemini-1.5-flash") is True

    def test_google_rejects_gpt(self):
        from shadow_eval.adapters.google_adapter import GoogleAdapter
        adapter = GoogleAdapter()
        assert adapter.supports_model("gpt-4o") is False

    def test_bedrock_supports_llama(self):
        from shadow_eval.adapters.bedrock_adapter import BedrockAdapter
        adapter = BedrockAdapter()
        assert adapter.supports_model("llama-3.1-70b") is True
        assert adapter.supports_model("llama-3.1-8b") is True
        assert adapter.supports_model("meta.llama3-1-70b-instruct-v1:0") is True

    def test_bedrock_rejects_gpt(self):
        from shadow_eval.adapters.bedrock_adapter import BedrockAdapter
        adapter = BedrockAdapter()
        assert adapter.supports_model("gpt-4o") is False
