"""
Staxx Intelligence — Pricing Catalog

Loads LLM provider pricing from a YAML configuration file, builds
an in-memory lookup index (canonical name + all aliases), and
auto-refreshes on a configurable interval.

Usage:
    catalog = PricingCatalog()           # loads pricing.yaml
    price = catalog.get_pricing("gpt-4o")
    # -> ModelPricing(input_per_1m_tokens=2.50, output_per_1m_tokens=10.00, provider="openai", canonical_name="gpt-4o")
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

_DEFAULT_YAML_PATH = Path(__file__).parent / "pricing.yaml"
_REFRESH_INTERVAL = int(os.getenv("PRICING_REFRESH_INTERVAL_SECONDS", "3600"))


@dataclass(frozen=True)
class ModelPricing:
    """Immutable pricing record for a single model."""

    input_per_1m_tokens: float
    output_per_1m_tokens: float
    provider: str
    canonical_name: str


@dataclass(frozen=True)
class FallbackPricing:
    """Fallback pricing used when a model is not found in the catalog."""

    input_per_1m_tokens: float
    output_per_1m_tokens: float


@dataclass
class PricingCatalog:
    """
    Thread-safe, auto-refreshing pricing catalog.

    The catalog is loaded from a YAML file at construction time and
    cached in memory.  A background daemon thread reloads the file
    every ``refresh_interval`` seconds so that pricing changes are
    picked up without service restarts.
    """

    yaml_path: Path = field(default_factory=lambda: _DEFAULT_YAML_PATH)
    refresh_interval: int = field(default_factory=lambda: _REFRESH_INTERVAL)

    # ---- internal state (not part of __init__ signature) --------------------
    _index: dict[str, ModelPricing] = field(default_factory=dict, init=False, repr=False)
    _fallback: FallbackPricing = field(
        default_factory=lambda: FallbackPricing(3.00, 15.00), init=False, repr=False
    )
    _chars_per_token: int = field(default=4, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _last_loaded: float = field(default=0.0, init=False, repr=False)
    _refresh_thread: Optional[threading.Thread] = field(default=None, init=False, repr=False)
    _org_markups: dict[str, float] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        self._load()
        self._start_refresh_loop()

    # ---- public API ---------------------------------------------------------

    def get_pricing(self, model_id: str) -> ModelPricing:
        """
        Look up pricing for *model_id* (case-insensitive).

        Returns the matched ``ModelPricing`` or a synthetic record
        built from fallback pricing if the model is unknown.
        """
        key = model_id.strip().lower()
        with self._lock:
            pricing = self._index.get(key)

        if pricing is not None:
            return pricing

        # Try partial matching — e.g. "gpt-4o-2024-08-06" might match "gpt-4o"
        # Collect ALL partial matches and pick the longest (most specific) one
        # to avoid "gpt-4o" matching before "gpt-4o-mini".
        with self._lock:
            best_match: ModelPricing | None = None
            best_key_len = 0
            for registered_key, registered_pricing in self._index.items():
                if registered_key in key or key in registered_key:
                    if len(registered_key) > best_key_len:
                        best_key_len = len(registered_key)
                        best_match = registered_pricing

        if best_match is not None:
            logger.debug(
                "Partial match: '%s' resolved to canonical '%s'",
                model_id,
                best_match.canonical_name,
            )
            return best_match

        logger.warning(
            "Unknown model '%s' — using fallback pricing ($%.2f input / $%.2f output per 1M tokens)",
            model_id,
            self._fallback.input_per_1m_tokens,
            self._fallback.output_per_1m_tokens,
        )
        return ModelPricing(
            input_per_1m_tokens=self._fallback.input_per_1m_tokens,
            output_per_1m_tokens=self._fallback.output_per_1m_tokens,
            provider="unknown",
            canonical_name=model_id,
        )

    def get_fallback(self) -> FallbackPricing:
        """Return the current fallback pricing."""
        with self._lock:
            return self._fallback

    @property
    def chars_per_token(self) -> int:
        """Approximate characters-per-token for token estimation."""
        return self._chars_per_token

    def set_org_markup(self, org_id: str, markup_pct: float) -> None:
        """
        Set a custom markup percentage for a specific organisation.

        Args:
            org_id: UUID string of the organisation.
            markup_pct: Markup as a fraction (e.g. 0.15 for 15%).
        """
        with self._lock:
            self._org_markups[org_id] = markup_pct
        logger.info("Org %s markup set to %.1f%%", org_id, markup_pct * 100)

    def get_org_markup(self, org_id: str) -> float:
        """
        Return the markup fraction for *org_id*, or 0.0 if none is set.
        """
        with self._lock:
            return self._org_markups.get(org_id, 0.0)

    def list_models(self) -> list[ModelPricing]:
        """Return a deduplicated list of all canonical model pricings."""
        with self._lock:
            seen: set[str] = set()
            result: list[ModelPricing] = []
            for pricing in self._index.values():
                ident = f"{pricing.provider}:{pricing.canonical_name}"
                if ident not in seen:
                    seen.add(ident)
                    result.append(pricing)
            return result

    def reload(self) -> None:
        """Force an immediate reload of the pricing YAML."""
        self._load()

    # ---- internal -----------------------------------------------------------

    def _load(self) -> None:
        """Parse the YAML file and rebuild the lookup index."""
        try:
            with open(self.yaml_path, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
        except FileNotFoundError:
            logger.error("Pricing YAML not found at %s — keeping stale catalog", self.yaml_path)
            return
        except yaml.YAMLError as exc:
            logger.error("Failed to parse pricing YAML: %s — keeping stale catalog", exc)
            return

        new_index: dict[str, ModelPricing] = {}

        # Fallback pricing
        fb = data.get("fallback_pricing", {})
        fallback = FallbackPricing(
            input_per_1m_tokens=float(fb.get("input_per_1m_tokens", 3.00)),
            output_per_1m_tokens=float(fb.get("output_per_1m_tokens", 15.00)),
        )

        chars_per_token = int(data.get("token_estimation_chars_per_token", 4))

        # Build index
        providers = data.get("providers", {})
        for provider_name, provider_data in providers.items():
            models = provider_data.get("models", {})
            for model_name, model_data in models.items():
                pricing = ModelPricing(
                    input_per_1m_tokens=float(model_data["input_per_1m_tokens"]),
                    output_per_1m_tokens=float(model_data["output_per_1m_tokens"]),
                    provider=provider_name,
                    canonical_name=model_name,
                )
                # Index by canonical name
                new_index[model_name.lower()] = pricing
                # Index by all aliases
                for alias in model_data.get("aliases", []):
                    new_index[alias.strip().lower()] = pricing

        with self._lock:
            self._index = new_index
            self._fallback = fallback
            self._chars_per_token = chars_per_token
            self._last_loaded = time.monotonic()

        logger.info(
            "Pricing catalog loaded: %d models indexed from %s",
            len(new_index),
            self.yaml_path,
        )

    def _start_refresh_loop(self) -> None:
        """Launch a daemon thread that reloads the catalog periodically."""
        if self.refresh_interval <= 0:
            return

        def _loop() -> None:
            while True:
                time.sleep(self.refresh_interval)
                logger.debug("Auto-refreshing pricing catalog...")
                self._load()

        self._refresh_thread = threading.Thread(target=_loop, daemon=True, name="pricing-refresh")
        self._refresh_thread.start()


# ---------------------------------------------------------------------------
# Module-level singleton — import this from anywhere in cost_engine
# ---------------------------------------------------------------------------
_catalog_instance: Optional[PricingCatalog] = None
_instance_lock = threading.Lock()


def get_catalog() -> PricingCatalog:
    """
    Return the module-level singleton ``PricingCatalog``.

    Thread-safe lazy initialization. Call this instead of constructing
    ``PricingCatalog()`` manually to avoid loading the YAML multiple times.
    """
    global _catalog_instance
    if _catalog_instance is None:
        with _instance_lock:
            if _catalog_instance is None:
                _catalog_instance = PricingCatalog()
    return _catalog_instance
