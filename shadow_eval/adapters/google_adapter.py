"""
Staxx Intelligence — Google Vertex / Gemini Adapter

Routes requests to the Google Generative AI REST API via async httpx.
Uses the ``generateContent`` endpoint for Gemini models.
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

_API_KEY = os.getenv("STAXX_GOOGLE_API_KEY", "")
_BASE_URL = os.getenv(
    "GOOGLE_GENAI_BASE_URL",
    "https://generativelanguage.googleapis.com/v1beta",
)
_MAX_RETRIES = int(os.getenv("GOOGLE_MAX_RETRIES", "3"))
_RETRY_BASE_DELAY = float(os.getenv("GOOGLE_RETRY_BASE_DELAY", "1.0"))

_SUPPORTED_PREFIXES = (
    "gemini-2.0",
    "gemini-1.5",
    "gemini-1.0",
    "gemini-pro",
    "gemini-flash",
)


class GoogleAdapter(BaseAdapter):
    """Adapter for Google Gemini generativeai REST API."""

    PROVIDER = "google"

    def __init__(self) -> None:
        self._api_key = _API_KEY
        self._base_url = _BASE_URL.rstrip("/")
        self._semaphore = asyncio.Semaphore(
            int(os.getenv("GOOGLE_CONCURRENCY", "15"))
        )

    def supports_model(self, model_id: str) -> bool:
        lower = model_id.lower()
        return any(lower.startswith(p) for p in _SUPPORTED_PREFIXES)

    async def invoke(self, request: AdapterRequest) -> AdapterResponse:
        if not self._api_key:
            return AdapterResponse(error="STAXX_GOOGLE_API_KEY not configured")

        async with self._semaphore:
            return await self._invoke_with_retry(request)

    async def _invoke_with_retry(self, request: AdapterRequest) -> AdapterResponse:
        last_error = ""

        # Convert OpenAI-style messages to Gemini format
        contents = self._build_contents(request.messages)

        model_name = request.model
        # Ensure model name has "models/" prefix for the API
        if not model_name.startswith("models/"):
            model_name = f"models/{model_name}"

        url = f"{self._base_url}/{model_name}:generateContent?key={self._api_key}"

        body: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            },
        }

        for attempt in range(_MAX_RETRIES):
            start = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=request.timeout_seconds) as client:
                    resp = await client.post(
                        url,
                        json=body,
                        headers={"Content-Type": "application/json"},
                    )

                elapsed_ms = int((time.perf_counter() - start) * 1000)

                if resp.status_code == 200:
                    data = resp.json()
                    return self._parse_response(data, elapsed_ms)

                if resp.status_code in (429, 500, 502, 503):
                    last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    logger.warning(
                        "Google retryable error (attempt %d/%d): %s",
                        attempt + 1, _MAX_RETRIES, last_error,
                    )
                    await asyncio.sleep(_RETRY_BASE_DELAY * (2 ** attempt))
                    continue

                return AdapterResponse(
                    error=f"HTTP {resp.status_code}: {resp.text[:500]}",
                    latency_ms=int((time.perf_counter() - start) * 1000),
                )

            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "Google connection error (attempt %d/%d): %s",
                    attempt + 1, _MAX_RETRIES, last_error,
                )
                await asyncio.sleep(_RETRY_BASE_DELAY * (2 ** attempt))

        return AdapterResponse(error=f"Max retries exceeded. Last error: {last_error}")

    @staticmethod
    def _build_contents(messages: list[dict[str, str]]) -> list[dict[str, Any]]:
        """
        Convert OpenAI-style messages to Gemini ``contents`` format.
        Gemini uses ``user`` and ``model`` roles (no ``system``);
        system messages are prepended to the first user message.
        """
        system_text = ""
        contents: list[dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                system_text += content + "\n"
                continue

            gemini_role = "model" if role == "assistant" else "user"

            # Prepend system text to first user message
            if gemini_role == "user" and system_text:
                content = system_text.strip() + "\n\n" + content
                system_text = ""

            contents.append({
                "role": gemini_role,
                "parts": [{"text": content}],
            })

        # If there's only system text and no user messages, create one
        if system_text and not contents:
            contents.append({
                "role": "user",
                "parts": [{"text": system_text.strip()}],
            })

        return contents

    @staticmethod
    def _parse_response(data: dict[str, Any], elapsed_ms: int) -> AdapterResponse:
        """Parse Gemini generateContent response into AdapterResponse."""
        candidates = data.get("candidates", [])
        if not candidates:
            # Check for safety block
            block_reason = data.get("promptFeedback", {}).get("blockReason")
            if block_reason:
                return AdapterResponse(
                    error=f"Blocked by safety filter: {block_reason}",
                    latency_ms=elapsed_ms,
                )
            return AdapterResponse(error="No candidates in response", latency_ms=elapsed_ms)

        candidate = candidates[0]
        content = candidate.get("content", {})
        parts = content.get("parts", [])
        text_output = "".join(p.get("text", "") for p in parts)

        usage = data.get("usageMetadata", {})

        return AdapterResponse(
            text_output=text_output,
            input_tokens=usage.get("promptTokenCount", 0),
            output_tokens=usage.get("candidatesTokenCount", 0),
            latency_ms=elapsed_ms,
            raw_response=data,
        )
