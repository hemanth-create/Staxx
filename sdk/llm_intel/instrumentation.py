import asyncio
import logging
import os
import time
from inspect import iscoroutinefunction
from typing import Any, Callable, Dict, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

# By default, point to the FastAPI trace ingest endpoint
LLM_INTEL_API_URL = os.getenv("LLM_INTEL_API_URL", "http://localhost:8000/api/v1/capture")
LLM_INTEL_API_KEY = os.getenv("LLM_INTEL_API_KEY", "")

# Shared HTTP client for background shipping
_http_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=5.0)
    return _http_client


async def ship_metrics_async(payload: Dict[str, Any]):
    """
    Asynchronously fires the payload to the ingestion API.
    Fails silently to avoid breaking the host application on telemetry failure.
    """
    try:
        client = get_http_client()
        headers = {"Authorization": f"Bearer {LLM_INTEL_API_KEY}"} if LLM_INTEL_API_KEY else {}
        await client.post(LLM_INTEL_API_URL, json=payload, headers=headers)
    except Exception as e:
        logger.debug("llm-intel: Failed to ship metrics - %s", str(e))


def extract_openai_metrics(response: Any, latency_ms: float, error: Optional[str] = None) -> Dict[str, Any]:
    """Extract standard metrics from an OpenAI completion response."""
    # Assuming text completion for MVP scope
    if error:
        return {
            "error": error,
            "latency_ms": latency_ms,
        }
    
    usage = getattr(response, "usage", None)
    return {
        "model": getattr(response, "model", "unknown"),
        "input_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
        "output_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
        "latency_ms": latency_ms,
    }


def extract_anthropic_metrics(response: Any, request_kwargs: dict, latency_ms: float, error: Optional[str] = None) -> Dict[str, Any]:
    """Extract standard metrics from an Anthropic message response."""
    if error:
        return {
            "model": request_kwargs.get("model", "unknown"),
            "error": error,
            "latency_ms": latency_ms,
        }
    
    usage = getattr(response, "usage", None)
    return {
        "model": getattr(response, "model", request_kwargs.get("model", "unknown")),
        "input_tokens": getattr(usage, "input_tokens", 0) if usage else 0,
        "output_tokens": getattr(usage, "output_tokens", 0) if usage else 0,
        "latency_ms": latency_ms,
    }
