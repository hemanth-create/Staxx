"""
Staxx Proxy Gateway — OpenAI-compatible proxy routes.

Handles:
  - ``POST /v1/chat/completions``
  - ``POST /v1/completions``
  - ``POST /v1/embeddings``

Every request is forwarded transparently to the real OpenAI API.
Telemetry is published asynchronously after the response is sent.
"""

from __future__ import annotations

from typing import Any

import orjson
import structlog
from fastapi import APIRouter, Depends, Request, Response

from proxy.config import settings
from proxy.middleware.auth import validate_staxx_key
from proxy.middleware.telemetry import build_telemetry_event, publish_telemetry_event
from proxy.services.forwarder import ForwardResult, forward_request
from proxy.services.token_extractor import (
    estimate_tokens_from_text,
    extract_openai_tokens,
)

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["OpenAI Proxy"])

# ── header helpers ──────────────────────────────────────────────────────

_HEADERS_TO_STRIP = frozenset({
    "host",
    "x-staxx-key",
    "content-length",       # httpx recalculates
    "transfer-encoding",
})


def _build_forward_headers(request: Request) -> dict[str, str]:
    """Build the header dict to send to OpenAI.

    We forward all original headers *except* proxy-specific ones.
    The ``Authorization`` header passes through untouched — it carries
    the customer's real OpenAI key.
    """
    return {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in _HEADERS_TO_STRIP
    }


def _is_stream_requested(body: dict[str, Any]) -> bool:
    """Check whether the caller asked for a streaming response."""
    return body.get("stream", False) is True


def _extract_model(body: dict[str, Any]) -> str:
    """Extract the model identifier from the request body."""
    return body.get("model", "unknown")


# ── route handlers ──────────────────────────────────────────────────────

@router.post("/v1/chat/completions")
async def proxy_chat_completions(
    request: Request,
    org_id: str = Depends(validate_staxx_key),
) -> Response:
    """Proxy an OpenAI ``/v1/chat/completions`` call."""
    return await _proxy_openai(request, org_id, "/v1/chat/completions")


@router.post("/v1/completions")
async def proxy_completions(
    request: Request,
    org_id: str = Depends(validate_staxx_key),
) -> Response:
    """Proxy an OpenAI ``/v1/completions`` call."""
    return await _proxy_openai(request, org_id, "/v1/completions")


@router.post("/v1/embeddings")
async def proxy_embeddings(
    request: Request,
    org_id: str = Depends(validate_staxx_key),
) -> Response:
    """Proxy an OpenAI ``/v1/embeddings`` call."""
    return await _proxy_openai(request, org_id, "/v1/embeddings")


# ── shared proxy logic ──────────────────────────────────────────────────

async def _proxy_openai(
    request: Request,
    org_id: str,
    path: str,
) -> Response:
    """Core proxy logic shared by all OpenAI-compatible endpoints.

    1. Read the raw body and parse it to detect streaming / model.
    2. Forward the request to OpenAI via the async HTTP client.
    3. Fire-and-forget publish telemetry.
    4. Return the provider response as-is.
    """
    raw_body = await request.body()

    # Parse body for metadata extraction (streaming flag, model name).
    try:
        parsed_body: dict[str, Any] = orjson.loads(raw_body)
    except Exception:
        parsed_body = {}

    model = _extract_model(parsed_body)
    stream = _is_stream_requested(parsed_body)
    target_url = f"{settings.openai_base_url}{path}"

    headers = _build_forward_headers(request)

    log = logger.bind(org_id=org_id, model=model, path=path, stream=stream)
    log.info("openai_proxy.forwarding")

    result: ForwardResult = await forward_request(
        method="POST",
        target_url=target_url,
        headers=headers,
        body=raw_body,
        is_stream_requested=stream,
    )

    # ── Telemetry (non-blocking) ────────────────────────────────────
    if not stream:
        # Non-streaming: we already have the full response body.
        _emit_telemetry(org_id, model, parsed_body, result)
    else:
        # Streaming: telemetry will be emitted via a background wrapper
        # that runs *after* the last chunk is sent.
        result.response = _wrap_streaming_response(
            result, org_id, model, parsed_body,
        )

    return result.response


# ── telemetry helpers ───────────────────────────────────────────────────

def _emit_telemetry(
    org_id: str,
    model: str,
    request_body: dict[str, Any],
    result: ForwardResult,
) -> None:
    """Build and fire-and-forget publish a telemetry event."""
    response_body = result.body if isinstance(result.body, dict) else {}
    input_tokens, output_tokens = extract_openai_tokens(response_body)

    # Fallback estimation when usage is missing (e.g. error responses).
    if input_tokens == 0 and isinstance(request_body, dict):
        raw_prompt = orjson.dumps(request_body).decode()
        input_tokens = estimate_tokens_from_text(raw_prompt)

    event = build_telemetry_event(
        org_id=org_id,
        provider="openai",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=result.latency_ms,
        request_body=request_body,
        response_body=response_body,
        status_code=result.status_code,
        error="" if result.status_code < 400 else str(response_body),
    )
    publish_telemetry_event(event)


def _wrap_streaming_response(
    result: ForwardResult,
    org_id: str,
    model: str,
    request_body: dict[str, Any],
) -> Response:
    """Wrap the streaming response to emit telemetry after the last chunk.

    We wrap the original generator so that once it finishes, we parse
    the accumulated SSE data and publish telemetry.
    """
    from fastapi.responses import StreamingResponse
    import time as _time

    original_gen = result.response.body_iterator  # type: ignore[union-attr]
    accumulated_text: list[str] = getattr(result, "_accumulated_text", [])
    start_time: float = getattr(result, "_start_time", _time.perf_counter())

    async def _wrapper():
        async for chunk in original_gen:
            yield chunk

        # Stream complete — build telemetry.
        latency_ms = int((_time.perf_counter() - start_time) * 1000)
        full_text = "".join(accumulated_text)

        # Try to extract usage from the final SSE data event.
        response_body = _parse_stream_usage(full_text)
        input_tokens, output_tokens = extract_openai_tokens(response_body)

        if input_tokens == 0:
            raw_prompt = orjson.dumps(request_body).decode()
            input_tokens = estimate_tokens_from_text(raw_prompt)
        if output_tokens == 0:
            output_tokens = estimate_tokens_from_text(full_text)

        event = build_telemetry_event(
            org_id=org_id,
            provider="openai",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            request_body=request_body,
            response_body={"_streamed": True, "usage": response_body.get("usage", {})},
            status_code=result.status_code,
        )
        publish_telemetry_event(event)

    return StreamingResponse(
        _wrapper(),
        status_code=result.status_code,
        headers=result.headers,
        media_type=result.response.media_type,  # type: ignore[union-attr]
    )


def _parse_stream_usage(full_sse_text: str) -> dict[str, Any]:
    """Extract usage info from accumulated SSE lines.

    OpenAI includes a ``usage`` field in the final ``data:`` chunk when
    ``stream_options: {"include_usage": true}`` is set.  We look for
    the last ``data:`` line that contains ``"usage"``.
    """
    usage: dict[str, Any] = {}
    for line in reversed(full_sse_text.splitlines()):
        stripped = line.strip()
        if stripped.startswith("data:") and "usage" in stripped:
            json_str = stripped[len("data:"):].strip()
            if json_str == "[DONE]":
                continue
            try:
                parsed = orjson.loads(json_str)
                if isinstance(parsed, dict) and parsed.get("usage"):
                    return parsed
            except Exception:
                continue
    return {"usage": usage}
