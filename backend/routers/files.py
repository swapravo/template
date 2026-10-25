"""
routers/files.py — File upload, download, list, delete, and presigned URL endpoints.
All storage operations delegate to storage.py.
"""
from fastapi import (
    APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status,
)

import storage
from schemas import StorageFileInfo, StoragePresignedUrlResponse, StorageUploadResponse
from sessions import get_current_user

router = APIRouter(prefix="/api/v1/files", tags=["files"])


@router.post("/upload", response_model=StorageUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload a file to RustFS. Namespaced under the authenticated user ID."""
    key = f"{current_user['sub']}/{file.filename}"
    data = await file.read()
    content_type = file.content_type or "application/octet-stream"
    url = await storage.upload_file(key, data, content_type)
    return StorageUploadResponse(key=key, url=url, content_type=content_type, size_bytes=len(data))


@router.get("/", response_model=list[StorageFileInfo])
async def list_files(
    prefix: str = Query(default=""),
    current_user: dict = Depends(get_current_user),
):
    """List files for the current user, with optional sub-prefix filter."""
    user_prefix = f"{current_user['sub']}/{prefix}"
    files = await storage.list_files(user_prefix)
    return [StorageFileInfo(**f) for f in files]


@router.get("/{key:path}/presigned-url", response_model=StoragePresignedUrlResponse)
async def get_presigned_url(
    key: str,
    expires_in: int = Query(default=3600, ge=60, le=86400),
    current_user: dict = Depends(get_current_user),
):
    """Generate a time-limited presigned URL for temporary file access."""
    url = await storage.get_presigned_url(key, expires_in)
    return StoragePresignedUrlResponse(key=key, url=url, expires_in_seconds=expires_in)


@router.get("/{key:path}")
async def download_file(key: str, current_user: dict = Depends(get_current_user)):
    """Download a file from RustFS as raw bytes."""
    try:
        data = await storage.download_file(key)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    return Response(content=data, media_type="application/octet-stream")


@router.delete("/{key:path}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(key: str, current_user: dict = Depends(get_current_user)):
    """Delete a file from RustFS."""
    try:
        await storage.delete_file(key)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
