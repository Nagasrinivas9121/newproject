"""
SRIVANI BOOKING MANAGER - PHASE 9
Document Management Module for Supporting Documents & Ticket Attachments

Features:
- Secure local storage under data/documents/{family_id}/
- PDF and image attachment support (.pdf, .png, .jpg, .jpeg)
- SHA-256 integrity checks and deduplication
- File validation (size, extension, existence)
- Document preview launcher
- Strictly offline local storage (never uploaded to TTD)
"""

import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import DATA_DIR

DOCUMENTS_DIR = DATA_DIR / "documents"
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_DOC_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def sanitize_doc_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal and invalid characters."""
    base = os.path.basename(filename)
    sanitized = re.sub(r"[^a-zA-Z0-9_.-]", "_", base)
    return sanitized[:128]


def compute_file_hash(filepath: str | Path) -> str:
    """Compute SHA-256 checksum of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def validate_document_file(src_path: str | Path) -> Tuple[bool, str]:
    """Validate document file existence, extension, and size."""
    p = Path(src_path)
    if not p.exists() or not p.is_file():
        return False, f"File does not exist: {src_path}"

    ext = p.suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Unsupported file type '{ext}'. Allowed formats: PDF, PNG, JPG, JPEG"

    size = p.stat().st_size
    if size > MAX_DOC_SIZE_BYTES:
        max_mb = MAX_DOC_SIZE_BYTES // (1024 * 1024)
        return False, f"File size ({size / (1024 * 1024):.1f}MB) exceeds maximum limit of {max_mb}MB"

    if size == 0:
        return False, "File is empty (0 bytes)"

    return True, "Valid document"


def store_family_document(
    family_id: int,
    source_file_path: str | Path,
    doc_type: str = "ID_PROOF",
    notes: str = "",
) -> Dict[str, Any]:
    """
    Copy and store supporting document into secure family-isolated local directory.
    Returns metadata dictionary for database insertion.
    """
    valid, err = validate_document_file(source_file_path)
    if not valid:
        raise ValueError(err)

    src = Path(source_file_path)
    safe_name = sanitize_doc_filename(src.name)

    # Family-isolated storage path
    family_doc_dir = DOCUMENTS_DIR / str(family_id)
    family_doc_dir.mkdir(parents=True, exist_ok=True)

    dest_path = family_doc_dir / safe_name
    # Handle filename collision within family folder
    if dest_path.exists():
        stem = src.stem
        ext = src.suffix
        counter = 1
        while dest_path.exists():
            dest_path = family_doc_dir / f"{stem}_{counter}{ext}"
            counter += 1

    shutil.copy2(src, dest_path)
    sha256_hash = compute_file_hash(dest_path)
    file_size = dest_path.stat().st_size

    return {
        "family_id": family_id,
        "doc_type": doc_type,
        "file_name": dest_path.name,
        "file_path": str(dest_path.resolve()),
        "file_size": file_size,
        "sha256": sha256_hash,
        "notes": notes,
    }


def open_document_preview(file_path: str | Path) -> bool:
    """Launch file in system default viewer (PDF viewer or Image viewer)."""
    p = Path(file_path)
    if not p.exists():
        return False

    try:
        if sys.platform == "win32":
            os.startfile(str(p.resolve()))
            return True
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(p.resolve())])
            return True
        else:
            subprocess.Popen(["xdg-open", str(p.resolve())])
            return True
    except Exception:
        return False
