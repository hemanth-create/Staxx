"""
Staxx Intelligence — AWS Bedrock Adapter

Routes requests to AWS Bedrock via boto3's ``invoke_model`` API.
Since boto3 is synchronous, calls are wrapped in
``asyncio.to_thread`` for non-blocking execution.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from shadow_eval.adapters.base import AdapterRequest, AdapterResponse, BaseAdapter

logger = logging.getLogger(__name__)

_AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
_MAX_RETRIES = int(os.getenv("BEDROCK_MAX_RETRIES", "3"))
_RETRY_BASE_DELAY = float(os.getenv("BEDROCK_RETRY_BASE_DELAY", "1.0"))

# Model ID patterns that should be routed to Bedrock
_SUPPORTED_PATTERNS = (
    "llama-3.1-",
    "llama-3-",
    "meta.llama",
    "amazon.titan",
    "cohere.command",
    "ai21.j2",
    "mistral.",  # Bedrock-hosted Mistral variants
)

# Map friendly names to Bedrock model IDs
_MODEL_ID_MAP: dict[str, str] = {
    "llama-3.1-70b": "meta.llama3-1-70b-instruct-v1:0",
    "llama-3.1-70b-instruct": "meta.llama3-1-70b-instruct-v1:0",
    "llama-3.1-8b": "meta.llama3-1-8b-instruct-v1:0",
    "llama-3.1-8b-instruct": "meta.llama3-1-8b-instruct-v1:0",
}


class BedrockAdapter(BaseAdapter):
    """Adapter for AWS Bedrock models (Llama, Titan, etc.)."""

    PROVIDER = "bedrock"

    def __init__(self) -> None:
        self._region = _AWS_REGION
        self._client = None  # Lazy init
        self._semaphore = asyncio.Semaphore(
            int(os.getenv("BEDROCK_CONCURRENCY", "10"))
        )

    def _get_client(self) -> Any:
        """Lazy-initialise the Bedrock Runtime client."""
        if self._client is None:
            self._client = boto3.client(
                "bedrock-runtime",
                region_name=self._region,
                config=BotoConfig(
                    retries={"max_attempts": 0},  # We handle retries ourselves
                    read_timeout=60,
                    connect_timeout=10,
                ),
            )
        return self._client

    def supports_model(self, model_id: str) -> bool:
        lower = model_id.lower()
        return any(lower.startswith(p) or p in lower for p in _SUPPORTED_PATTERNS)

    def _resolve_model_id(self, model_id: str) -> str:
        """Map friendly model names to Bedrock ARN/ID format."""
        mapped = _MODEL_ID_MAP.get(model_id.lower())
        if mapped:
            return mapped
        # If it already looks like a Bedrock ID, use as-is
        if "." in model_id or ":" in model_id:
            return model_id
        return model_id

    async def invoke(self, request: AdapterRequest) -> AdapterResponse:
        async with self._semaphore:
            return await self._invoke_with_retry(request)

    async def _invoke_with_retry(self, request: AdapterRequest) -> AdapterResponse:
        last_error = ""
        bedrock_model_id = self._resolve_model_id(request.model)

        for attempt in range(_MAX_RETRIES):
            start = time.perf_counter()
            try:
                response = await asyncio.to_thread(
                    self._call_bedrock, bedrock_model_id, request
                )
                elapsed_ms = int((time.perf_counter() - start) * 1000)

                if response.get("error"):
                    last_error = response["error"]
                    if "ThrottlingException" in last_error or "ServiceUnavailable" in last_error:
                        logger.warning(
                            "Bedrock retryable error (attempt %d/%d): %s",
                            attempt + 1, _MAX_RETRIES, last_error,
                        )
                        await asyncio.sleep(_RETRY_BASE_DELAY * (2 ** attempt))
                        continue
                    return AdapterResponse(error=last_error, latency_ms=elapsed_ms)

                return AdapterResponse(
                    text_output=response.get("text_output", ""),
                    input_tokens=response.get("input_tokens", 0),
                    output_tokens=response.get("output_tokens", 0),
                    latency_ms=elapsed_ms,
                    raw_response=response,
                )

            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "Bedrock error (attempt %d/%d): %s",
                    attempt + 1, _MAX_RETRIES, last_error,
                )
                await asyncio.sleep(_RETRY_BASE_DELAY * (2 ** attempt))

        return AdapterResponse(error=f"Max retries exceeded. Last error: {last_error}")

    def _call_bedrock(self, model_id: str, request: AdapterRequest) -> dict[str, Any]:
        """
        Synchronous Bedrock invoke_model call.
        Formats the request body based on the model family.
        """
        client = self._get_client()

        # Build a prompt string from the messages
        prompt_parts: list[str] = []
        for msg in request.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                prompt_parts.append(f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{content}<|eot_id|>")
            elif role == "user":
                prompt_parts.append(f"<|start_header_id|>user<|end_header_id|>\n{content}<|eot_id|>")
            elif role == "assistant":
                prompt_parts.append(f"<|start_header_id|>assistant<|end_header_id|>\n{content}<|eot_id|>")

        prompt_parts.append("<|start_header_id|>assistant<|end_header_id|>\n")
        full_prompt = "\n".join(prompt_parts)

        # Llama 3 / Meta models via Bedrock Converse-style invoke
        body = json.dumps({
            "prompt": full_prompt,
            "max_gen_len": request.max_tokens,
            "temperature": request.temperature,
        })

        try:
            response = client.invoke_model(
                modelId=model_id,
                body=body,
                contentType="application/json",
                accept="application/json",
            )

            response_body = json.loads(response["body"].read())

            return {
                "text_output": response_body.get("generation", ""),
                "input_tokens": response_body.get("prompt_token_count", 0),
                "output_tokens": response_body.get("generation_token_count", 0),
            }

        except ClientError as exc:
            return {"error": f"Bedrock ClientError: {exc.response['Error']['Code']}: {exc.response['Error']['Message']}"}
        except Exception as exc:
            return {"error": f"Bedrock error: {type(exc).__name__}: {exc}"}
