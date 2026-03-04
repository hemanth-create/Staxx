"""
Staxx Intelligence — Cost Calculator Tests

Comprehensive test suite covering:
  • Exact cost calculation with known models
  • Token estimation from character length
  • Fallback pricing for unknown models
  • Per-org markup application
  • Edge cases: zero tokens, missing fields, empty strings
  • Pricing catalog loading and alias resolution
"""

from __future__ import annotations

import os
import tempfile
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# We need to ensure the pricing catalog is loaded from a controlled YAML
# for deterministic tests, NOT from the default file which may change.
# ---------------------------------------------------------------------------

_TEST_YAML = textwrap.dedent("""\
    fallback_pricing:
      input_per_1m_tokens: 5.00
      output_per_1m_tokens: 20.00

    token_estimation_chars_per_token: 4

    providers:
      openai:
        models:
          gpt-4o:
            input_per_1m_tokens: 2.50
            output_per_1m_tokens: 10.00
            aliases:
              - "gpt-4o-2024-08-06"
          gpt-4o-mini:
            input_per_1m_tokens: 0.15
            output_per_1m_tokens: 0.60
            aliases:
              - "gpt-4o-mini-2024-07-18"
          gpt-3.5-turbo:
            input_per_1m_tokens: 0.50
            output_per_1m_tokens: 1.50
            aliases:
              - "gpt-3.5-turbo-0125"
      anthropic:
        models:
          claude-3-haiku-20240307:
            input_per_1m_tokens: 0.25
            output_per_1m_tokens: 1.25
            aliases:
              - "claude-3-haiku"
      google:
        models:
          gemini-2.0-flash:
            input_per_1m_tokens: 0.10
            output_per_1m_tokens: 0.40
            aliases: []
""")


@pytest.fixture(autouse=True)
def _reset_catalog_singleton():
    """
    Reset the module-level singleton before each test so every test
    gets a fresh catalog loaded from the test YAML.
    """
    import cost_engine.pricing_catalog as pc

    # Reset singleton
    pc._catalog_instance = None
    yield
    pc._catalog_instance = None


@pytest.fixture()
def test_yaml_path(tmp_path: Path) -> Path:
    """Write the test YAML to a temp file and return its path."""
    p = tmp_path / "pricing_test.yaml"
    p.write_text(_TEST_YAML, encoding="utf-8")
    return p


@pytest.fixture()
def catalog(test_yaml_path: Path):
    """Build a PricingCatalog from the test YAML."""
    from cost_engine.pricing_catalog import PricingCatalog

    return PricingCatalog(yaml_path=test_yaml_path, refresh_interval=0)


# ===========================================================================
# Pricing Catalog Tests
# ===========================================================================


class TestPricingCatalog:
    """Tests for the pricing catalog loading and lookup logic."""

    def test_load_models_count(self, catalog):
        """All canonical models and aliases should be indexed."""
        models = catalog.list_models()
        # 5 canonical models defined in the test YAML
        assert len(models) == 5

    def test_lookup_canonical_name(self, catalog):
        pricing = catalog.get_pricing("gpt-4o")
        assert pricing.canonical_name == "gpt-4o"
        assert pricing.provider == "openai"
        assert pricing.input_per_1m_tokens == 2.50
        assert pricing.output_per_1m_tokens == 10.00

    def test_lookup_alias(self, catalog):
        """An alias should resolve to the same canonical pricing."""
        pricing = catalog.get_pricing("gpt-4o-2024-08-06")
        assert pricing.canonical_name == "gpt-4o"
        assert pricing.input_per_1m_tokens == 2.50

    def test_lookup_case_insensitive(self, catalog):
        pricing = catalog.get_pricing("GPT-4O")
        assert pricing.canonical_name == "gpt-4o"

    def test_lookup_unknown_model_returns_fallback(self, catalog):
        pricing = catalog.get_pricing("some-unknown-model-v99")
        assert pricing.provider == "unknown"
        assert pricing.input_per_1m_tokens == 5.00
        assert pricing.output_per_1m_tokens == 20.00

    def test_lookup_partial_match(self, catalog):
        """gpt-4o-mini-2024-07-18 is an alias, but a new date version
        like gpt-4o-mini-2025-01-01 should still partial-match."""
        pricing = catalog.get_pricing("gpt-4o-mini-2025-01-01")
        assert pricing.canonical_name == "gpt-4o-mini"

    def test_fallback_pricing(self, catalog):
        fb = catalog.get_fallback()
        assert fb.input_per_1m_tokens == 5.00
        assert fb.output_per_1m_tokens == 20.00

    def test_org_markup(self, catalog):
        org = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"
        assert catalog.get_org_markup(org) == 0.0
        catalog.set_org_markup(org, 0.15)
        assert catalog.get_org_markup(org) == 0.15

    def test_reload_idempotent(self, catalog):
        """Calling reload() should not crash or lose data."""
        catalog.reload()
        pricing = catalog.get_pricing("gpt-4o")
        assert pricing.canonical_name == "gpt-4o"


# ===========================================================================
# Cost Calculator Tests
# ===========================================================================


class TestCostCalculator:
    """Tests for the calculate_cost function."""

    @pytest.fixture(autouse=True)
    def _setup_catalog(self, catalog, test_yaml_path):
        """Inject the test catalog as the module singleton."""
        import cost_engine.pricing_catalog as pc

        pc._catalog_instance = catalog

    def _calc(self, **kwargs):
        from cost_engine.calculator import calculate_cost
        return calculate_cost(**kwargs)

    # --- Basic cost calculations ---

    def test_basic_gpt4o_cost(self):
        """1000 input + 500 output tokens on gpt-4o."""
        result = self._calc(
            model_id="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
        )
        # input:  (1000 / 1_000_000) * 2.50 = 0.0025
        # output: (500 / 1_000_000) * 10.00 = 0.005
        assert result.total_cost_usd == pytest.approx(0.0075, abs=1e-9)
        assert result.input_cost_usd == pytest.approx(0.0025, abs=1e-9)
        assert result.output_cost_usd == pytest.approx(0.005, abs=1e-9)
        assert result.was_estimated is False
        assert result.model_canonical == "gpt-4o"
        assert result.provider == "openai"

    def test_gpt4o_mini_cost(self):
        """100K input + 50K output tokens on gpt-4o-mini."""
        result = self._calc(
            model_id="gpt-4o-mini",
            input_tokens=100_000,
            output_tokens=50_000,
        )
        # input:  (100000 / 1M) * 0.15 = 0.015
        # output: (50000 / 1M) * 0.60  = 0.030
        assert result.total_cost_usd == pytest.approx(0.045, abs=1e-9)

    def test_alias_produces_same_cost(self):
        """Using an alias should produce identical cost to canonical name."""
        r1 = self._calc(model_id="gpt-4o", input_tokens=1000, output_tokens=500)
        r2 = self._calc(model_id="gpt-4o-2024-08-06", input_tokens=1000, output_tokens=500)
        assert r1.total_cost_usd == r2.total_cost_usd
        assert r1.model_canonical == r2.model_canonical

    def test_claude_haiku_cost(self):
        result = self._calc(
            model_id="claude-3-haiku",
            input_tokens=10_000,
            output_tokens=2_000,
        )
        # input:  (10000 / 1M) * 0.25 = 0.0025
        # output: (2000 / 1M) * 1.25  = 0.0025
        assert result.total_cost_usd == pytest.approx(0.005, abs=1e-9)

    def test_gemini_flash_cost(self):
        result = self._calc(
            model_id="gemini-2.0-flash",
            input_tokens=50_000,
            output_tokens=10_000,
        )
        # input:  (50000 / 1M) * 0.10 = 0.005
        # output: (10000 / 1M) * 0.40 = 0.004
        assert result.total_cost_usd == pytest.approx(0.009, abs=1e-9)

    # --- Token estimation ---

    def test_token_estimation_from_text(self):
        """When token counts are missing, estimate from text length."""
        text_400_chars = "a" * 400  # -> ~100 tokens at 4 chars/token
        result = self._calc(
            model_id="gpt-4o",
            input_text=text_400_chars,
            output_text="b" * 200,  # ~50 tokens
        )
        assert result.was_estimated is True
        assert result.input_tokens_used == 100
        assert result.output_tokens_used == 50
        # Cost: (100/1M)*2.50 + (50/1M)*10.00 = 0.00025 + 0.0005 = 0.00075
        assert result.total_cost_usd == pytest.approx(0.00075, abs=1e-9)

    def test_explicit_tokens_override_text(self):
        """Explicit token counts take priority over text estimation."""
        result = self._calc(
            model_id="gpt-4o",
            input_tokens=500,
            output_tokens=200,
            input_text="a" * 4000,  # Would estimate 1000 tokens, but ignored
            output_text="b" * 4000,
        )
        assert result.was_estimated is False
        assert result.input_tokens_used == 500
        assert result.output_tokens_used == 200

    def test_estimation_min_one_token(self):
        """Even a single character should estimate to at least 1 token."""
        result = self._calc(
            model_id="gpt-4o",
            input_text="x",
            output_tokens=0,
        )
        assert result.input_tokens_used == 1

    # --- Edge cases ---

    def test_zero_tokens(self):
        result = self._calc(
            model_id="gpt-4o",
            input_tokens=0,
            output_tokens=0,
        )
        assert result.total_cost_usd == 0.0

    def test_unknown_model_fallback(self):
        """Unknown model should use fallback pricing and log a warning."""
        result = self._calc(
            model_id="totally-fake-model-v99",
            input_tokens=1000,
            output_tokens=1000,
        )
        # Fallback: 5.00 input, 20.00 output per 1M
        expected = (1000 / 1_000_000) * 5.00 + (1000 / 1_000_000) * 20.00
        assert result.total_cost_usd == pytest.approx(expected, abs=1e-9)
        assert result.provider == "unknown"

    def test_missing_both_tokens_and_text(self):
        """If both tokens and text are missing, cost should be $0."""
        result = self._calc(model_id="gpt-4o")
        assert result.total_cost_usd == 0.0
        assert result.input_tokens_used == 0
        assert result.output_tokens_used == 0

    # --- Org markup ---

    def test_org_markup_applied(self, catalog):
        """Per-org markup should be applied on top of base cost."""
        org_id = "11112222-3333-4444-5555-666677778888"
        catalog.set_org_markup(org_id, 0.20)  # 20% markup

        result = self._calc(
            model_id="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
            org_id=org_id,
        )
        base = 0.0075  # same as test_basic_gpt4o_cost
        markup = base * 0.20
        assert result.total_cost_usd == pytest.approx(base, abs=1e-9)
        assert result.markup_usd == pytest.approx(markup, abs=1e-9)
        assert result.final_cost_usd == pytest.approx(base + markup, abs=1e-9)

    def test_no_markup_when_org_not_set(self):
        """Without org markup, final_cost == total_cost."""
        result = self._calc(
            model_id="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
        )
        assert result.markup_usd == 0.0
        assert result.final_cost_usd == result.total_cost_usd


# ===========================================================================
# Token Estimation Unit Tests
# ===========================================================================


class TestEstimateTokens:
    """Focused tests for the estimate_tokens helper."""

    def test_empty_string(self):
        from cost_engine.calculator import estimate_tokens
        assert estimate_tokens("") == 0

    def test_standard_estimation(self):
        from cost_engine.calculator import estimate_tokens
        # 400 chars / 4 chars_per_token = 100 tokens
        assert estimate_tokens("a" * 400) == 100

    def test_custom_ratio(self):
        from cost_engine.calculator import estimate_tokens
        # 400 chars / 5 chars_per_token = 80 tokens
        assert estimate_tokens("a" * 400, chars_per_token=5) == 80

    def test_minimum_one_token(self):
        from cost_engine.calculator import estimate_tokens
        assert estimate_tokens("x") == 1
        assert estimate_tokens("ab") == 1
        assert estimate_tokens("abc") == 1

    def test_exactly_divisible(self):
        from cost_engine.calculator import estimate_tokens
        assert estimate_tokens("a" * 8, chars_per_token=4) == 2
