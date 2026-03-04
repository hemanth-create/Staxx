"""
Staxx Proxy Gateway — Anthropic Messages API proxy route.

Handles:
  - ``POST /v1/messages``

Anthropic uses a different auth scheme (``x-api-key`` header instead of
``Authorization: Bearer``) and a different response shape, so it gets
its own route module.
"""

from __future__ import annotations

import time as _time
from typing import Any

import orjson
import structlog
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import StreamingResponse

from proxy.config import settings
from proxy.middleware.auth import validate_staxx_key
from proxy.middleware.telemetry import build_telemetry_event, publish_telemetry_event
from proxy.services.forwarder import ForwardResult, forward_request
from proxy.services.token_extractor import (
    estimate_tokens_from_text,
    extract_anthropic_tokens,
)

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Anthropic Proxy"])

# Headers we strip before forwarding — proxy-specific or recomputed.
_HEADERS_TO_STRIP = frozenset({
    "host",
    "x-staxx-key",
    "content-length",
    "transfer-encoding",
})


def _build_forward_headers(request: Request) -> dict[str, str]:
    """Build headers for the Anthropic API.

    Anthropic expects ``x-api-key`` (not ``Authorization: Bearer``).
    We forward whatever the customer sent — if they're using the
    Anthropic SDK it will already have ``x-api-key`` set.
    We also ensure ``anthropic-version`` is present.
    """
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in _HEADERS_TO_STRIP
    }

    # Guarantee the version header so Anthropic doesn't reject.
    if "anthropic-version" not in headers:
        headers["anthropic-version"] = "2023-06-01"

    return headers


def _is_stream_requested(body: dict[str, Any]) -> bool:
    """Check whether the caller asked for SSE streaming."""
    return body.get("stream", False) is True


def _extract_model(body: dict[str, Any]) -> str:
    """Extract the model identifier from the request body."""
    return body.get("model", "unknown")


# ── route handler ───────────────────────────────────────────────────────

@router.post("/v1/messages")
async def proxy_messages(
    request: Request,
    org_id: str = Depends(validate_staxx_key),
) -> Response:
    """Proxy an Anthropic ``/v1/messages`` call.

    Flow:
      1. Read raw body, parse for metadata (model, stream flag).
      2. Forward to Anthropic via the shared HTTP client.
      3. Publish telemetry asynchronously (non-blocking).
      4. Return the provider response unchanged.
    """
    raw_body = await request.body()

    try:
        parsed_body: dict[str, Any] = orjson.loads(raw_body)
    except Exception:
        parsed_body = {}

    model = _extract_model(parsed_body)
    stream = _is_stream_requested(parsed_body)
    target_url = f"{settings.anthropic_base_url}/v1/messages"

    headers = _build_forward_headers(request)

    log = logger.bind(org_id=org_id, model=model, stream=stream)
    log.info("anthropic_proxy.forwarding")

    result: ForwardResult = await forward_request(
        method="POST",
        target_url=target_url,
        headers=headers,
        body=raw_body,
        is_stream_requested=stream,
    )

    # ── Telemetry ───────────────────────────────────────────────────
    if not stream:
        _emit_telemetry(org_id, model, parsed_body, result)
    else:
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
    """Build and fire-and-forget publish a telemetry event for Anthropic."""
    response_body = result.body if isinstance(result.body, dict) else {}
    input_tokens, output_tokens = extract_anthropic_tokens(response_body)

    if input_tokens == 0 and isinstance(request_body, dict):
        raw_prompt = orjson.dumps(request_body).decode()
        input_tokens = estimate_tokens_from_text(raw_prompt)

    event = build_telemetry_event(
        org_id=org_id,
        provider="anthropic",
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
    """Wrap Anthropic SSE stream to emit telemetry after completion.

    Anthropic SSE events include ``message_start`` (with input token
    count) and ``message_delta`` (with output token count and stop
    reason).  We parse these from the accumulated chunks.
    """
    original_gen = result.response.body_iterator  # type: ignore[union-attr]
    accumulated_text: list[str] = getattr(result, "_accumulated_text", [])
    start_time: float = getattr(result, "_start_time", _time.perf_counter())

    async def _wrapper():
        async for chunk in original_gen:
            yield chunk

        # Stream finished — build telemetry from accumulated SSE data.
        latency_ms = int((_time.perf_counter() - start_time) * 1000)
        full_text = "".join(accumulated_text)

        input_tokens, output_tokens = _extract_anthropic_stream_usage(full_text)

        if input_tokens == 0:
            raw_prompt = orjson.dumps(request_body).decode()
            input_tokens = estimate_tokens_from_text(raw_prompt)
        if output_tokens == 0:
            output_tokens = estimate_tokens_from_text(full_text)

        event = build_telemetry_event(
            org_id=org_id,
            provider="anthropic",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            request_body=request_body,
            response_body={
                "_streamed": True,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
            status_code=result.status_code,
        )
        publish_telemetry_event(event)

    return StreamingResponse(
        _wrapper(),
        status_code=result.status_code,
        headers=result.headers,
        media_type=result.response.media_type,  # type: ignore[union-attr]
    )


def _extract_anthropic_stream_usage(full_sse_text: str) -> tuple[int, int]:
    """Parse Anthropic SSE events to extract token usage.

    Anthropic streams include:
      - ``event: message_start`` → data has ``message.usage.input_tokens``
      - ``event: message_delta`` → data has ``usage.output_tokens``

    We scan all ``data:`` lines for these fields.
    """
    input_tokens = 0
    output_tokens = 0

    for line in full_sse_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("data:"):
            continue
        json_str = stripped[len("data:"):].strip()
        if not json_str or json_str == "[DONE]":
            continue
        try:
            parsed = orjson.loads(json_str)
        except Exception:
            continue

        if not isinstance(parsed, dict):
            continue

        # message_start event
        msg = parsed.get("message", {})
        if isinstance(msg, dict):
            usage = msg.get("usage", {})
            if isinstance(usage, dict) and usage.get("input_tokens"):
                input_tokens = int(usage["input_tokens"])

        # message_delta event
        delta_usage = parsed.get("usage", {})
        if isinstance(delta_usage, dict) and delta_usage.get("output_tokens"):
            output_tokens = int(delta_usage["output_tokens"])

    return input_tokens, output_tokens
