import asyncio
import logging
import os
from typing import Optional

try:
    import boto3
    from botocore.exceptions import ClientError
    _BOTO3_AVAILABLE = True
except Exception:
    boto3 = None
    ClientError = Exception
    _BOTO3_AVAILABLE = False

logger = logging.getLogger(__name__)


class S3Storage:
    """Async-friendly S3 helper using boto3 in thread executor.

    Exposes upload and presign helpers used by the execution reporter.
    """

    def __init__(self, bucket: str, region: Optional[str] = None, aws_profile: Optional[str] = None):
        if not _BOTO3_AVAILABLE:
            raise RuntimeError("boto3 is required for S3Storage but it's not installed. Install boto3 or provide an alternative storage implementation.")
        session_args = {}
        if aws_profile:
            session_args["profile_name"] = aws_profile
        self.session = boto3.Session(**session_args)
        self.s3 = self.session.client("s3", region_name=region)
        self.bucket = bucket

    async def upload_file(self, local_path: str, key: str, retries: int = 3) -> dict:
        if not os.path.exists(local_path):
            raise FileNotFoundError(local_path)

        last_exc = None
        for attempt in range(1, retries + 1):
            try:
                await asyncio.to_thread(self.s3.upload_file, local_path, self.bucket, key)
                return {"bucket": self.bucket, "key": key, "url": f"s3://{self.bucket}/{key}"}
            except ClientError as e:
                last_exc = e
                logger.warning("S3 upload attempt %s failed for %s: %s", attempt, key, e)
                await asyncio.sleep(0.5 * attempt)

        raise last_exc

    async def presign_url(self, key: str, expires_in: int = 3600) -> str:
        try:
            url = await asyncio.to_thread(self.s3.generate_presigned_url, "get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=expires_in)
            return url
        except ClientError as e:
            logger.exception("Failed to create presigned URL for %s: %s", key, e)
            raise
