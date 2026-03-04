"""
Staxx Intelligence — Anthropic Adapter

Routes requests to the Anthropic Messages API via async httpx.
Handles the Anthropic-specific message format (system prompt as
a top-level parameter, not in the messages array).
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

_API_KEY = os.getenv("STAXX_ANTHROPIC_API_KEY", "")
_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
_API_VERSION = os.getenv("ANTHROPIC_API_VERSION", "2023-06-01")
_MAX_RETRIES = int(os.getenv("ANTHROPIC_MAX_RETRIES", "3"))
_RETRY_BASE_DELAY = float(os.getenv("ANTHROPIC_RETRY_BASE_DELAY", "1.0"))

_SUPPORTED_PREFIXES = (
    "claude-opus-4",
    "claude-sonnet-4",
    "claude-haiku-4",
    "claude-3-5-sonnet",
    "claude-3-5-haiku",
    "claude-3.5-sonnet",
    "claude-3.5-haiku",
    "claude-3-opus",
    "claude-3-haiku",
    "claude-3-sonnet",
)


class AnthropicAdapter(BaseAdapter):
    """Adapter for Anthropic Messages API."""

    PROVIDER = "anthropic"

    def __init__(self) -> None:
        self._api_key = _API_KEY
        self._base_url = _BASE_URL.rstrip("/")
        self._semaphore = asyncio.Semaphore(
            int(os.getenv("ANTHROPIC_CONCURRENCY", "15"))
        )

    def supports_model(self, model_id: str) -> bool:
        lower = model_id.lower()
        return any(lower.startswith(p) for p in _SUPPORTED_PREFIXES)

    async def invoke(self, request: AdapterRequest) -> AdapterResponse:
        if not self._api_key:
            return AdapterResponse(error="STAXX_ANTHROPIC_API_KEY not configured")

        # Anthropic wants system prompt as a top-level field,
        # not inside the messages array
        system_prompt = ""
        messages: list[dict[str, str]] = []
        for msg in request.messages:
            if msg.get("role") == "system":
                system_prompt += msg.get("content", "") + "\n"
            else:
                messages.append(msg)

        if not messages:
            return AdapterResponse(error="No user messages provided")

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": _API_VERSION,
            "Content-Type": "application/json",
        }

        body: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        if system_prompt.strip():
            body["system"] = system_prompt.strip()

        async with self._semaphore:
            return await self._invoke_with_retry(headers, body, request.timeout_seconds)

    async def _invoke_with_retry(
        self,
        headers: dict[str, str],
        body: dict[str, Any],
        timeout: float,
    ) -> AdapterResponse:
        last_error = ""

        for attempt in range(_MAX_RETRIES):
            start = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(
                        f"{self._base_url}/v1/messages",
                        headers=headers,
                        json=body,
                    )

                elapsed_ms = int((time.perf_counter() - start) * 1000)

                if resp.status_code == 200:
                    data = resp.json()
                    # Anthropic returns content as a list of content blocks
                    content_blocks = data.get("content", [])
                    text_parts = [
                        block.get("text", "")
                        for block in content_blocks
                        if block.get("type") == "text"
                    ]
                    text_output = "".join(text_parts)

                    usage = data.get("usage", {})
                    return AdapterResponse(
                        text_output=text_output,
                        input_tokens=usage.get("input_tokens", 0),
                        output_tokens=usage.get("output_tokens", 0),
                        latency_ms=elapsed_ms,
                        raw_response=data,
                    )

                if resp.status_code in (429, 500, 502, 503, 529):
                    last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    logger.warning(
                        "Anthropic retryable error (attempt %d/%d): %s",
                        attempt + 1, _MAX_RETRIES, last_error,
                    )
                    # Respect Retry-After header if present
                    retry_after = resp.headers.get("retry-after")
                    if retry_after:
                        await asyncio.sleep(float(retry_after))
                    else:
                        await asyncio.sleep(_RETRY_BASE_DELAY * (2 ** attempt))
                    continue

                return AdapterResponse(
                    error=f"HTTP {resp.status_code}: {resp.text[:500]}",
                    latency_ms=elapsed_ms,
                )

            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "Anthropic connection error (attempt %d/%d): %s",
                    attempt + 1, _MAX_RETRIES, last_error,
                )
                await asyncio.sleep(_RETRY_BASE_DELAY * (2 ** attempt))

        return AdapterResponse(error=f"Max retries exceeded. Last error: {last_error}")
