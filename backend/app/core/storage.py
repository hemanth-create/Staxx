import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class StorageBackend:
    """Abstraction for S3/MinIO storage interface."""

    def __init__(self):
        self.bucket = settings.S3_BUCKET_NAME
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1" # Stub region for MinIO compatibility
        )
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Creates the bucket on initialization if it doesn't exist."""
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "404":
                logger.info("Bucket %s does not exist. Creating...", self.bucket)
                self.client.create_bucket(Bucket=self.bucket)
            else:
                logger.error("Failed to check or create bucket: %s", str(e))

    def upload_json(self, object_name: str, json_data: str) -> bool:
        """Uploads a serialized JSON string to the bucket."""
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=object_name,
                Body=json_data.encode("utf-8"),
                ContentType="application/json"
            )
            return True
        except ClientError as e:
            logger.error("Failed to upload object %s to S3: %s", object_name, str(e))
            return False

    def get_json(self, object_name: str) -> str | None:
        """Retrieves raw JSON payload from the bucket."""
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=object_name)
            return response["Body"].read().decode("utf-8")
        except ClientError as e:
            logger.error("Failed to retrieve object %s from S3: %s", object_name, str(e))
            return None


# Singleton instance for injection
storage_client = StorageBackend()
