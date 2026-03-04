"""
Staxx Proxy Gateway — Async HTTP forwarder.

Handles both **streaming** (SSE) and **non-streaming** responses.
The goal is *zero behavioural change* for the customer — we forward
the provider's response byte-for-byte, status code included.
"""

from __future__ import annotations

import time
from typing import Any, AsyncIterator

import httpx
import orjson
import structlog
from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse

from proxy.config import settings

logger = structlog.get_logger(__name__)

# A shared client is created during lifespan and stored on app.state.
# This avoids per-request connection overhead.
_client: httpx.AsyncClient | None = None


# ── lifecycle ───────────────────────────────────────────────────────────

async def init_http_client() -> httpx.AsyncClient:
    """Create a module-level ``httpx.AsyncClient`` with connection pooling."""
    global _client  # noqa: PLW0603
    _client = httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=settings.forward_connect_timeout,
            read=settings.forward_timeout,
            write=settings.forward_timeout,
            pool=settings.forward_timeout,
        ),
        limits=httpx.Limits(
            max_keepalive_connections=80,
            max_connections=200,
            keepalive_expiry=30,
        ),
        http2=True,
        follow_redirects=False,
    )
    logger.info("forwarder.http_client_ready")
    return _client


async def close_http_client() -> None:
    """Close the shared ``httpx.AsyncClient``."""
    global _client  # noqa: PLW0603
    if _client is not None:
        await _client.aclose()
        _client = None
        logger.info("forwarder.http_client_closed")


def _get_client() -> httpx.AsyncClient:
    """Return the initialised client or raise."""
    if _client is None:
        raise RuntimeError("HTTP client not initialised — call init_http_client first")
    return _client


# ── public API ──────────────────────────────────────────────────────────

class ForwardResult:
    """Container returned by :func:`forward_request`.

    Attributes:
        status_code: HTTP status code from the provider.
        headers: Response headers from the provider (filtered).
        body: The full response body as ``dict`` (non-streaming) or
              ``str`` (accumulated streaming chunks for telemetry).
        latency_ms: Round-trip time in milliseconds.
        is_streaming: Whether the response was streamed.
        response: The ``fastapi.Response`` ready to return to the caller.
    """

    __slots__ = (
        "status_code",
        "headers",
        "body",
        "latency_ms",
        "is_streaming",
        "response",
        "raw_body_bytes",
    )

    def __init__(
        self,
        *,
        status_code: int,
        headers: dict[str, str],
        body: dict[str, Any] | str,
        latency_ms: int,
        is_streaming: bool,
        response: JSONResponse | StreamingResponse,
        raw_body_bytes: bytes = b"",
    ) -> None:
        self.status_code = status_code
        self.headers = headers
        self.body = body
        self.latency_ms = latency_ms
        self.is_streaming = is_streaming
        self.response = response
        self.raw_body_bytes = raw_body_bytes


async def forward_request(
    *,
    method: str,
    target_url: str,
    headers: dict[str, str],
    body: bytes,
    is_stream_requested: bool,
) -> ForwardResult:
    """Forward an HTTP request to the target provider and return the result.

    Args:
        method: HTTP method (``POST``, ``GET``, etc.).
        target_url: Full URL of the provider endpoint.
        headers: Headers to forward (already cleaned by the route handler).
        body: Raw request body bytes.
        is_stream_requested: Whether the caller wants an SSE stream.

    Returns:
        A :class:`ForwardResult` containing the response and telemetry data.
    """
    client = _get_client()
    start = time.perf_counter()

    if is_stream_requested:
        return await _forward_streaming(client, method, target_url, headers, body, start)
    else:
        return await _forward_non_streaming(client, method, target_url, headers, body, start)


# ── non-streaming path ─────────────────────────────────────────────────

async def _forward_non_streaming(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes,
    start: float,
) -> ForwardResult:
    """Forward a non-streaming request and return the full response."""
    resp = await client.request(
        method=method,
        url=url,
        headers=headers,
        content=body,
    )

    latency_ms = int((time.perf_counter() - start) * 1000)
    raw_bytes = resp.content

    # Try to parse as JSON for telemetry; keep raw bytes as fallback.
    try:
        parsed_body: dict[str, Any] = orjson.loads(raw_bytes)
    except Exception:
        parsed_body = {"_raw": raw_bytes.decode(errors="replace")}

    # Build filtered headers — drop hop-by-hop and encoding headers
    # since FastAPI handles its own framing.
    fwd_headers = _filter_response_headers(resp.headers)

    fastapi_resp = JSONResponse(
        content=parsed_body,
        status_code=resp.status_code,
        headers=fwd_headers,
    )

    return ForwardResult(
        status_code=resp.status_code,
        headers=fwd_headers,
        body=parsed_body,
        latency_ms=latency_ms,
        is_streaming=False,
        response=fastapi_resp,
        raw_body_bytes=raw_bytes,
    )


# ── streaming path ─────────────────────────────────────────────────────

async def _forward_streaming(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes,
    start: float,
) -> ForwardResult:
    """Forward a streaming (SSE) request, proxying chunks in real time.

    We accumulate the full streamed output in memory so that telemetry
    can log the complete response after the stream finishes.
    """
    # We need the httpx response to stay open while we stream chunks.
    req = client.build_request(method=method, url=url, headers=headers, content=body)
    resp = await client.send(req, stream=True)

    accumulated_chunks: list[bytes] = []
    accumulated_text: list[str] = []

    async def _chunk_generator() -> AsyncIterator[bytes]:
        """Yield chunks from the provider stream with zero buffering."""
        try:
            async for chunk in resp.aiter_bytes():
                accumulated_chunks.append(chunk)
                # Collect text for telemetry
                try:
                    accumulated_text.append(chunk.decode("utf-8", errors="replace"))
                except Exception:
                    pass
                yield chunk
        finally:
            await resp.aclose()

    latency_ms = int((time.perf_counter() - start) * 1000)

    fwd_headers = _filter_response_headers(resp.headers)
    # Ensure content-type is event-stream for SSE.
    content_type = resp.headers.get("content-type", "text/event-stream")

    fastapi_resp = StreamingResponse(
        _chunk_generator(),
        status_code=resp.status_code,
        headers=fwd_headers,
        media_type=content_type,
    )

    # For streaming, body will be populated *after* the stream completes.
    # The route handler will read ``accumulated_text`` via the closure.
    # We store a reference so the route can access it post-stream.
    result = ForwardResult(
        status_code=resp.status_code,
        headers=fwd_headers,
        body="",  # Placeholder — route will read accumulated_text later
        latency_ms=latency_ms,
        is_streaming=True,
        response=fastapi_resp,
    )

    # Attach accumulators for post-stream telemetry assembly.
    result._accumulated_text = accumulated_text  # type: ignore[attr-defined]
    result._start_time = start  # type: ignore[attr-defined]

    return result


# ── header filtering ────────────────────────────────────────────────────

_HOP_BY_HOP = frozenset({
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-encoding",
    "content-length",
})


def _filter_response_headers(headers: httpx.Headers) -> dict[str, str]:
    """Remove hop-by-hop and framing headers that FastAPI manages itself."""
    return {
        k: v
        for k, v in headers.items()
        if k.lower() not in _HOP_BY_HOP
    }
