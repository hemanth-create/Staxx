"""
Staxx Intelligence — OpenAI Adapter

Routes requests to the OpenAI Chat Completions API via async httpx.
Handles retries with exponential backoff, timeouts, and token-bucket
rate limiting.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

import httpx

from shadow_eval.adapters.base import AdapterRequest, AdapterResponse, BaseAdapter

logger = logging.getLogger(__name__)

_API_KEY = os.getenv("STAXX_OPENAI_API_KEY", "")
_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
_MAX_RETRIES = int(os.getenv("OPENAI_MAX_RETRIES", "3"))
_RETRY_BASE_DELAY = float(os.getenv("OPENAI_RETRY_BASE_DELAY", "1.0"))

# Models this adapter serves (case-insensitive prefix matching)
_SUPPORTED_PREFIXES = (
    "gpt-4o",
    "gpt-4-turbo",
    "gpt-3.5-turbo",
    "o1",
    "o1-mini",
    "gpt-4o-mini",
)


class OpenAIAdapter(BaseAdapter):
    """Adapter for OpenAI Chat Completions API."""

    PROVIDER = "openai"

    def __init__(self) -> None:
        self._api_key = _API_KEY
        self._base_url = _BASE_URL.rstrip("/")
        # Token bucket: limit requests per second (simple sliding window)
        self._rate_limit_rpm = int(os.getenv("OPENAI_RATE_LIMIT_RPM", "500"))
        self._semaphore = asyncio.Semaphore(
            int(os.getenv("OPENAI_CONCURRENCY", "20"))
        )

    def supports_model(self, model_id: str) -> bool:
        lower = model_id.lower()
        return any(lower.startswith(p) for p in _SUPPORTED_PREFIXES)

    async def invoke(self, request: AdapterRequest) -> AdapterResponse:
        """Send a chat completion request to OpenAI."""
        if not self._api_key:
            return AdapterResponse(error="STAXX_OPENAI_API_KEY not configured")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        body: dict[str, Any] = {
            "model": request.model,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        async with self._semaphore:
            return await self._invoke_with_retry(headers, body, request.timeout_seconds)

    async def _invoke_with_retry(
        self,
        headers: dict[str, str],
        body: dict[str, Any],
        timeout: float,
    ) -> AdapterResponse:
        """Execute the request with exponential backoff retries."""
        last_error: str = ""

        for attempt in range(_MAX_RETRIES):
            start = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(
                        f"{self._base_url}/chat/completions",
                        headers=headers,
                        json=body,
                    )

                elapsed_ms = int((time.perf_counter() - start) * 1000)

                if resp.status_code == 200:
                    data = resp.json()
                    choice = data.get("choices", [{}])[0]
                    message = choice.get("message", {})
                    usage = data.get("usage", {})

                    return AdapterResponse(
                        text_output=message.get("content", ""),
                        input_tokens=usage.get("prompt_tokens", 0),
                        output_tokens=usage.get("completion_tokens", 0),
                        latency_ms=elapsed_ms,
                        raw_response=data,
                    )

                # Retryable status codes
                if resp.status_code in (429, 500, 502, 503, 504):
                    last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    logger.warning(
                        "OpenAI retryable error (attempt %d/%d): %s",
                        attempt + 1, _MAX_RETRIES, last_error,
                    )
                    await asyncio.sleep(_RETRY_BASE_DELAY * (2 ** attempt))
                    continue

                # Non-retryable error
                return AdapterResponse(
                    error=f"HTTP {resp.status_code}: {resp.text[:500]}",
                    latency_ms=int((time.perf_counter() - start) * 1000),
                )

            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                elapsed_ms = int((time.perf_counter() - start) * 1000)
                last_error = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "OpenAI connection error (attempt %d/%d): %s",
                    attempt + 1, _MAX_RETRIES, last_error,
                )
                await asyncio.sleep(_RETRY_BASE_DELAY * (2 ** attempt))

        return AdapterResponse(error=f"Max retries exceeded. Last error: {last_error}")
