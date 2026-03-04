"""
Staxx Intelligence — S3/MinIO Storage for Shadow Eval Outputs

Stores full shadow evaluation outputs in S3/MinIO for audit trail
and later analysis by the Scoring Engine.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

_S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", None)
_S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", os.getenv("AWS_ACCESS_KEY_ID", ""))
_S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", os.getenv("AWS_SECRET_ACCESS_KEY", ""))
_S3_BUCKET = os.getenv("SHADOW_EVAL_BUCKET", os.getenv("S3_BUCKET_NAME", "staxx-shadow-evals"))
_S3_REGION = os.getenv("S3_REGION", "us-east-1")


class ShadowEvalStorage:
    """
    S3/MinIO storage backend for shadow evaluation outputs.

    Stores outputs under the key pattern:
        shadow_evals/{org_id}/{task_type}/{original_model}/{candidate_model}/{run_id}.json

    Each stored object contains:
        - prompt_hash
        - candidate model output text
        - metadata (tokens, latency, cost, validation results)
    """

    def __init__(
        self,
        bucket: str = _S3_BUCKET,
        endpoint_url: Optional[str] = _S3_ENDPOINT_URL,
    ) -> None:
        self._bucket = bucket
        kwargs: dict[str, Any] = {
            "region_name": _S3_REGION,
            "config": BotoConfig(signature_version="s3v4"),
        }
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        if _S3_ACCESS_KEY:
            kwargs["aws_access_key_id"] = _S3_ACCESS_KEY
        if _S3_SECRET_KEY:
            kwargs["aws_secret_access_key"] = _S3_SECRET_KEY

        self._client = boto3.client("s3", **kwargs)
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Create the bucket if it doesn't exist."""
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in ("404", "NoSuchBucket"):
                logger.info("Creating S3 bucket: %s", self._bucket)
                try:
                    self._client.create_bucket(Bucket=self._bucket)
                except ClientError:
                    logger.warning("Could not create bucket '%s' — will try uploads anyway", self._bucket)
            else:
                logger.warning("S3 head_bucket check failed: %s — will try uploads anyway", exc)

    def store_output(
        self,
        org_id: str,
        task_type: str,
        original_model: str,
        candidate_model: str,
        prompt_hash: str,
        output_text: str,
        metadata: dict[str, Any],
    ) -> str:
        """
        Store a shadow eval output in S3 and return the object key.

        Args:
            org_id: Organisation UUID string.
            task_type: Classified task type.
            original_model: The production model being evaluated against.
            candidate_model: The cheaper candidate model that produced the output.
            prompt_hash: SHA-256 hash of the prompt (for dedup/reference).
            output_text: Full text output from the candidate model.
            metadata: Additional metadata (tokens, latency, cost, etc.).

        Returns:
            The S3 object key where the output was stored.
        """
        run_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        # Build the S3 key
        s3_key = (
            f"shadow_evals/{org_id}/{task_type}/"
            f"{original_model}/{candidate_model}/{run_id}.json"
        )

        # Build the payload
        payload = {
            "run_id": run_id,
            "org_id": org_id,
            "task_type": task_type,
            "original_model": original_model,
            "candidate_model": candidate_model,
            "prompt_hash": prompt_hash,
            "output_text": output_text,
            "metadata": metadata,
            "stored_at": timestamp,
        }

        try:
            self._client.put_object(
                Bucket=self._bucket,
                Key=s3_key,
                Body=json.dumps(payload, default=str).encode("utf-8"),
                ContentType="application/json",
            )
            logger.debug("Stored shadow eval output: s3://%s/%s", self._bucket, s3_key)
        except ClientError as exc:
            logger.error("Failed to store shadow eval output to S3: %s", exc)
            # Return the key anyway — the DB record will still be created
            # and the output can be re-uploaded later

        return s3_key

    def retrieve_output(self, s3_key: str) -> Optional[dict[str, Any]]:
        """
        Retrieve a shadow eval output from S3.

        Returns:
            Parsed JSON dict, or None if retrieval fails.
        """
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=s3_key)
            body = response["Body"].read().decode("utf-8")
            return json.loads(body)
        except ClientError as exc:
            logger.error("Failed to retrieve s3://%s/%s: %s", self._bucket, s3_key, exc)
            return None
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.error("Failed to parse s3://%s/%s: %s", self._bucket, s3_key, exc)
            return None


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_storage_instance: Optional[ShadowEvalStorage] = None


def get_storage() -> ShadowEvalStorage:
    """Return the module-level storage singleton (lazy init)."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = ShadowEvalStorage()
    return _storage_instance
