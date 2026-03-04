"""
Staxx Intelligence — Candidate Selector Tests

Tests for:
  • Selecting cheaper candidates for an expensive model
  • Task-type compatibility filtering
  • Edge cases: cheapest model (no candidates), unknown model
  • Savings percentage calculation
  • Max candidates limit
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Test pricing YAML (subset for deterministic tests)
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
            aliases: []
          o1:
            input_per_1m_tokens: 15.00
            output_per_1m_tokens: 60.00
            aliases: []
      anthropic:
        models:
          claude-3-5-sonnet-20241022:
            input_per_1m_tokens: 3.00
            output_per_1m_tokens: 15.00
            aliases:
              - "claude-3.5-sonnet"
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
          gemini-1.5-pro:
            input_per_1m_tokens: 1.25
            output_per_1m_tokens: 5.00
            aliases: []
      meta:
        models:
          llama-3.1-70b:
            input_per_1m_tokens: 2.65
            output_per_1m_tokens: 3.50
            aliases: []
          llama-3.1-8b:
            input_per_1m_tokens: 0.30
            output_per_1m_tokens: 0.60
            aliases: []
      mistral:
        models:
          mistral-large:
            input_per_1m_tokens: 2.00
            output_per_1m_tokens: 6.00
            aliases: []
          mistral-small:
            input_per_1m_tokens: 0.20
            output_per_1m_tokens: 0.60
            aliases: []
          mistral-nemo:
            input_per_1m_tokens: 0.15
            output_per_1m_tokens: 0.15
            aliases: []
""")


@pytest.fixture(autouse=True)
def _reset_catalog():
    """Reset the pricing catalog singleton before each test."""
    import cost_engine.pricing_catalog as pc
    pc._catalog_instance = None
    yield
    pc._catalog_instance = None


@pytest.fixture()
def test_yaml_path(tmp_path: Path) -> Path:
    p = tmp_path / "pricing_test.yaml"
    p.write_text(_TEST_YAML, encoding="utf-8")
    return p


@pytest.fixture()
def catalog(test_yaml_path: Path):
    from cost_engine.pricing_catalog import PricingCatalog
    return PricingCatalog(yaml_path=test_yaml_path, refresh_interval=0)


@pytest.fixture(autouse=True)
def _inject_catalog(catalog):
    """Inject the test catalog as the module singleton."""
    import cost_engine.pricing_catalog as pc
    pc._catalog_instance = catalog


def _mock_get_adapter(model_id: str):
    """
    Mock adapter that returns a fake adapter for all models.
    This allows candidate_selector to think all models have adapters.
    """
    mock = MagicMock()
    mock.supports_model.return_value = True
    return mock


# ===========================================================================
# Tests
# ===========================================================================


class TestCandidateSelector:

    @patch("shadow_eval.candidate_selector.get_adapter", side_effect=_mock_get_adapter)
    def test_selects_cheaper_models_for_gpt4o(self, mock_adapter):
        from shadow_eval.candidate_selector import select_candidates

        candidates = select_candidates("gpt-4o", "summarization")

        # gpt-4o avg cost = (2.50 + 10.00) / 2 = 6.25
        # Top 5 cheapest should be selected
        assert len(candidates) > 0
        names = [c.canonical_name for c in candidates]
        # These are confirmed in the top-5 by savings %
        assert "gpt-4o-mini" in names
        assert "gemini-2.0-flash" in names
        assert "mistral-nemo" in names
        # claude-3-haiku is 6th, so it appears when limit > 5
        candidates_10 = select_candidates("gpt-4o", "summarization", max_candidates=10)
        names_10 = [c.canonical_name for c in candidates_10]
        assert "claude-3-haiku-20240307" in names_10

    @patch("shadow_eval.candidate_selector.get_adapter", side_effect=_mock_get_adapter)
    def test_no_candidates_for_cheapest_model(self, mock_adapter):
        from shadow_eval.candidate_selector import select_candidates

        # mistral-nemo is the cheapest model in the catalog (avg $0.15)
        candidates = select_candidates("mistral-nemo", "summarization")
        assert len(candidates) == 0

    @patch("shadow_eval.candidate_selector.get_adapter", side_effect=_mock_get_adapter)
    def test_candidates_sorted_by_savings(self, mock_adapter):
        from shadow_eval.candidate_selector import select_candidates

        candidates = select_candidates("o1", "summarization")
        # o1 is the most expensive, so all models are candidates
        # They should be sorted by savings_pct (highest first)
        assert len(candidates) > 0
        savings = [c.savings_pct for c in candidates]
        assert savings == sorted(savings, reverse=True)

    @patch("shadow_eval.candidate_selector.get_adapter", side_effect=_mock_get_adapter)
    def test_max_candidates_limit(self, mock_adapter):
        from shadow_eval.candidate_selector import select_candidates

        candidates = select_candidates("o1", "summarization", max_candidates=3)
        assert len(candidates) <= 3

    @patch("shadow_eval.candidate_selector.get_adapter", side_effect=_mock_get_adapter)
    def test_savings_pct_is_positive(self, mock_adapter):
        from shadow_eval.candidate_selector import select_candidates

        candidates = select_candidates("gpt-4o", "summarization")
        for c in candidates:
            assert c.savings_pct > 0

    @patch("shadow_eval.candidate_selector.get_adapter", side_effect=_mock_get_adapter)
    def test_original_model_not_in_candidates(self, mock_adapter):
        from shadow_eval.candidate_selector import select_candidates

        candidates = select_candidates("gpt-4o", "summarization")
        names = [c.canonical_name for c in candidates]
        assert "gpt-4o" not in names

    @patch("shadow_eval.candidate_selector.get_adapter", side_effect=_mock_get_adapter)
    def test_task_type_blocklist_filters(self, mock_adapter):
        """llama-3.1-8b should be blocked for code_generation."""
        from shadow_eval.candidate_selector import select_candidates

        candidates = select_candidates("o1", "code_generation")
        names = [c.canonical_name for c in candidates]
        assert "llama-3.1-8b" not in names

    @patch("shadow_eval.candidate_selector.get_adapter", side_effect=_mock_get_adapter)
    def test_min_savings_threshold(self, mock_adapter):
        from shadow_eval.candidate_selector import select_candidates

        # With 50% minimum savings, only significantly cheaper models pass
        candidates = select_candidates("gpt-4o", "summarization", min_savings_pct=50.0)
        for c in candidates:
            assert c.savings_pct >= 50.0

    @patch("shadow_eval.candidate_selector.get_adapter", return_value=None)
    def test_no_adapter_means_no_candidate(self, mock_adapter):
        """Models without an adapter should not appear as candidates."""
        from shadow_eval.candidate_selector import select_candidates

        candidates = select_candidates("gpt-4o", "summarization")
        assert len(candidates) == 0

    @patch("shadow_eval.candidate_selector.get_adapter", side_effect=_mock_get_adapter)
    def test_candidate_has_provider_info(self, mock_adapter):
        from shadow_eval.candidate_selector import select_candidates

        candidates = select_candidates("o1", "summarization")
        for c in candidates:
            assert c.provider != ""
            assert c.canonical_name != ""
            assert c.avg_cost_per_1m_tokens > 0
