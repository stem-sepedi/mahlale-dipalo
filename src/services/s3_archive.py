"""S3 archive worker — archives concept snapshots to MinIO/S3-compatible storage."""

import json
import logging
import os
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://localhost:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "minioadmin")
S3_BUCKET = os.getenv("S3_BUCKET", "polelo-snapshots")


class S3ArchiveWorker:
    """Archives version snapshots to S3-compatible storage (MinIO)."""

    def __init__(self, endpoint: str = S3_ENDPOINT, bucket: str = S3_BUCKET):
        self._endpoint = endpoint.rstrip("/")
        self._bucket = bucket
        self._client = httpx.AsyncClient(
            base_url=self._endpoint,
            auth=(S3_ACCESS_KEY, S3_SECRET_KEY),
            timeout=60.0,
        )

    async def ensure_bucket(self) -> None:
        """Create the bucket if it doesn't exist."""
        try:
            resp = await self._client.put(f"/{self._bucket}")
            if resp.status_code in (200, 409):
                logger.info("Bucket %s ready", self._bucket)
        except Exception as exc:
            logger.warning("Could not create bucket: %s", exc)

    async def archive_snapshot(
        self,
        concept_id: str,
        version_number: int,
        snapshot_data: dict,
    ) -> str:
        """Upload a snapshot to S3. Returns the S3 key."""
        key = f"concept/{concept_id}/v{version_number}.json"
        body = json.dumps(snapshot_data, indent=2, default=str).encode()
        resp = await self._client.put(
            f"/{self._bucket}/{key}",
            content=body,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        logger.info("Archived snapshot: s3://%s/%s", self._bucket, key)
        return f"s3://{self._bucket}/{key}"

    async def restore_snapshot(self, concept_id: str, version_number: int) -> dict:
        """Download a snapshot from S3."""
        key = f"concept/{concept_id}/v{version_number}.json"
        resp = await self._client.get(f"/{self._bucket}/{key}")
        resp.raise_for_status()
        return resp.json()

    async def close(self):
        await self._client.aclose()
