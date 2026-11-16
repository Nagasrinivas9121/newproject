import hashlib
import os
import re
import uuid
from typing import Dict
from fastapi import HTTPException, status
from server.core.config import settings


def sanitize_filename(name: str) -> str:
    """Sanitize filename to prevent directory traversal and special character injection."""
    base = os.path.basename(name)
    sanitized = re.sub(r"[^a-zA-Z0-9_.-]", "_", base)
    if not sanitized.lower().endswith(".pdf"):
        sanitized += ".pdf"
    return sanitized[:128]


async def save_ticket_pdf(
    tenant_id: str,
    family_id: str,
    original_filename: str,
    file_bytes: bytes
) -> Dict[str, any]:
    """Validate, sanitize, compute checksum, and store a tenant ticket PDF privately."""
    # 1. Size Validation
    if len(file_bytes) > settings.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Ticket PDF exceeds maximum permitted size of {settings.MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB."
        )

    # 2. Magic byte validation (must begin with %PDF)
    if not file_bytes.startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format: File header does not match a valid PDF document (%PDF signature missing)."
        )

    # 3. Checksum
    sha256 = hashlib.sha256(file_bytes).hexdigest()

    # 4. Tenant-isolated directory structure
    safe_name = sanitize_filename(original_filename)
    unique_prefix = uuid.uuid4().hex[:12]
    stored_name = f"{unique_prefix}_{safe_name}"

    tenant_dir = os.path.abspath(os.path.join(settings.STORAGE_DIR, tenant_id, "tickets"))
    os.makedirs(tenant_dir, exist_ok=True)

    dest_path = os.path.join(tenant_dir, stored_name)

    # Directory traversal safety check
    if not os.path.abspath(dest_path).startswith(tenant_dir):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security violation: Invalid file path traversal detected."
        )

    # Write file securely
    with open(dest_path, "wb") as f:
        f.write(file_bytes)

    return {
        "original_filename": original_filename,
        "safe_filename": stored_name,
        "storage_path": dest_path,
        "file_size": len(file_bytes),
        "sha256_checksum": sha256,
        "mime_type": "application/pdf"
    }


def verify_ticket_access(tenant_id: str, storage_path: str) -> str:
    """Ensure requested file resides strictly within the authorized tenant directory."""
    tenant_dir = os.path.abspath(os.path.join(settings.STORAGE_DIR, tenant_id, "tickets"))
    abs_path = os.path.abspath(storage_path)

    if not abs_path.startswith(tenant_dir):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not have permission to access files outside your tenant boundary."
        )

    if not os.path.exists(abs_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket PDF file not found on server storage."
        )

    return abs_path
