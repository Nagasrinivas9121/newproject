import json
import re
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from server.models.audit import AuditLog

# Regex patterns for sensitive data redaction
_SENSITIVE_PATTERNS = [
    (re.compile(r'"password":\s*"[^"]*"', re.IGNORECASE), '"password":"[REDACTED]"'),
    (re.compile(r'"token":\s*"[^"]*"', re.IGNORECASE), '"token":"[REDACTED]"'),
    (re.compile(r'"otp":\s*"[^"]*"', re.IGNORECASE), '"otp":"[REDACTED]"'),
    (re.compile(r'"mfa_code":\s*"[^"]*"', re.IGNORECASE), '"mfa_code":"[REDACTED]"'),
    (re.compile(r'"pin":\s*"[^"]*"', re.IGNORECASE), '"pin":"[REDACTED]"'),
    (re.compile(r'\b[0-9]{4}[ -]?[0-9]{4}[ -]?[0-9]{4}\b'), 'XXXX-XXXX-[REDACTED]'),  # 12-digit Aadhaar pattern
]


def sanitize_details(details: Any) -> str:
    """Ensure no passwords, OTPs, full Aadhaar numbers, or secrets are ever recorded in audit logs."""
    if details is None:
        return ""
    if isinstance(details, (dict, list)):
        text = json.dumps(details, default=str)
    else:
        text = str(details)

    for pattern, replacement in _SENSITIVE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


async def log_action(
    db: AsyncSession,
    action: str,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    details: Any = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """Record an immutable, privacy-compliant audit log entry."""
    sanitized_text = sanitize_details(details)
    log_entry = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else None,
        details_sanitized=sanitized_text,
        ip_address=ip_address,
    )
    db.add(log_entry)
    await db.flush()
    return log_entry
