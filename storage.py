"""
storage.py — RustFS (S3-compatible) client. All file operations live here.
Only this file initialises or calls the RustFS/S3 client.
Uses aioboto3 for async S3-compatible operations.
"""
from __future__ import annotations

import aioboto3
from botocore.config import Config

from config import settings


def _session() -> aioboto3.Session:
    return aioboto3.Session(
        aws_access_key_id=settings.RUSTFS_ACCESS_KEY,
        aws_secret_access_key=settings.RUSTFS_SECRET_KEY,
    )


def _client_kwargs() -> dict:
    return {
        "service_name": "s3",
        "endpoint_url": settings.RUSTFS_ENDPOINT,
        "config": Config(signature_version="s3v4"),
    }


async def upload_file(key: str, data: bytes, content_type: str) -> str:
    """Upload bytes to RustFS under the given key. Returns the object URL."""
    async with _session().client(**_client_kwargs()) as s3:
        await s3.put_object(
            Bucket=settings.RUSTFS_BUCKET,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
    return f"{settings.RUSTFS_ENDPOINT}/{settings.RUSTFS_BUCKET}/{key}"


async def download_file(key: str) -> bytes:
    """Download an object from RustFS. Returns raw bytes."""
    async with _session().client(**_client_kwargs()) as s3:
        response = await s3.get_object(Bucket=settings.RUSTFS_BUCKET, Key=key)
        return await response["Body"].read()


async def delete_file(key: str) -> None:
    """Delete an object from RustFS."""
    async with _session().client(**_client_kwargs()) as s3:
        await s3.delete_object(Bucket=settings.RUSTFS_BUCKET, Key=key)


async def list_files(prefix: str = "") -> list[dict]:
    """
    List objects with an optional key prefix.
    Returns a list of dicts: key, size_bytes, last_modified.
    """
    async with _session().client(**_client_kwargs()) as s3:
        response = await s3.list_objects_v2(
            Bucket=settings.RUSTFS_BUCKET,
            Prefix=prefix,
        )
    return [
        {
            "key": obj["Key"],
            "size_bytes": obj["Size"],
            "last_modified": obj["LastModified"],
        }
        for obj in response.get("Contents", [])
    ]


async def get_presigned_url(key: str, expires_in: int = 3600) -> str:
    """
    Generate a presigned URL for temporary read access to an object.
    expires_in is in seconds (default: 1 hour, max: 24 hours).
    """
    async with _session().client(**_client_kwargs()) as s3:
        url = await s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.RUSTFS_BUCKET, "Key": key},
            ExpiresIn=expires_in,
        )
    return url
