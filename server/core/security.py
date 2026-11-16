import base64
import datetime
import hashlib
import hmac
import secrets
import struct
import time
from typing import Any, Dict, Optional, Tuple
import bcrypt
import jwt

from server.core.config import settings

# In-memory Token Revocation / Blocklist (can be backed by Redis in distributed setups)
_REVOKED_TOKENS: set[str] = set()

# In-memory Rate Limiting Tracker: ip_or_username -> list of unix timestamps
_LOGIN_ATTEMPTS: dict[str, list[float]] = {}


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt with strong work factor."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def create_access_token(
    subject: str,
    tenant_id: Optional[str] = None,
    role: str = "TENANT_OPERATOR",
    expires_delta: Optional[datetime.timedelta] = None
) -> str:
    """Create a signed JWT access token."""
    now = datetime.datetime.now(datetime.timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": subject,
        "tenant_id": tenant_id,
        "role": role,
        "type": "access",
        "jti": secrets.token_hex(16),
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    subject: str,
    tenant_id: Optional[str] = None,
    role: str = "TENANT_OPERATOR"
) -> str:
    """Create a long-lived signed JWT refresh token."""
    now = datetime.datetime.now(datetime.timezone.utc)
    expire = now + datetime.timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": subject,
        "tenant_id": tenant_id,
        "role": role,
        "type": "refresh",
        "jti": secrets.token_hex(16),
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_password_reset_token(email: str) -> str:
    """Create a short-lived token (15 mins) for password reset verification."""
    now = datetime.datetime.now(datetime.timezone.utc)
    expire = now + datetime.timedelta(minutes=15)
    payload = {
        "sub": email,
        "type": "reset",
        "jti": secrets.token_hex(16),
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT token, ensuring it is not revoked."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        jti = payload.get("jti")
        if jti and jti in _REVOKED_TOKENS:
            return None
        return payload
    except (jwt.PyJWTError, Exception):
        return None


def revoke_token(token: str) -> bool:
    """Add token JTI to the revocation set upon logout."""
    try:
        # Decode without verifying expiration to allow revoking expired/active tokens
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": False}
        )
        jti = payload.get("jti")
        if jti:
            _REVOKED_TOKENS.add(jti)
            return True
    except Exception:
        pass
    return False


def is_rate_limited(key: str, max_attempts: int = 5, window_seconds: int = 60) -> bool:
    """Check if an IP address or username has exceeded the allowed login rate."""
    now = time.time()
    attempts = _LOGIN_ATTEMPTS.get(key, [])
    # Filter attempts within the current sliding window
    attempts = [ts for ts in attempts if now - ts < window_seconds]
    if len(attempts) >= max_attempts:
        _LOGIN_ATTEMPTS[key] = attempts
        return True
    attempts.append(now)
    _LOGIN_ATTEMPTS[key] = attempts
    return False


def clear_rate_limit(key: str) -> None:
    """Reset rate limit counter on successful login."""
    if key in _LOGIN_ATTEMPTS:
        del _LOGIN_ATTEMPTS[key]


# --- RFC 6238 TOTP Multi-Factor Authentication Helpers ---

def generate_totp_secret() -> str:
    """Generate a high-entropy Base32 secret for TOTP authenticator apps."""
    return base64.b32encode(secrets.token_bytes(20)).decode("utf-8").replace("=", "")


def get_totp_token(secret: str, time_step: int = 30, t: Optional[int] = None) -> str:
    """Calculate the 6-digit TOTP code for the given secret and timestamp."""
    if t is None:
        t = int(time.time())
    counter = int(t // time_step)
    pad_len = (8 - len(secret) % 8) % 8
    key = base64.b32decode(secret + "=" * pad_len)
    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    code = (struct.unpack(">I", h[offset:offset + 4])[0] & 0x7FFFFFFF) % 1_000_000
    return f"{code:06d}"


def verify_totp(secret: str, code: str, tolerance: int = 1) -> bool:
    """Verify a 6-digit TOTP code within a 1-step clock skew tolerance."""
    if not secret or not code:
        return False
    now = int(time.time())
    code_str = str(code).strip()
    for offset in range(-tolerance, tolerance + 1):
        if get_totp_token(secret, t=now + offset * 30) == code_str:
            return True
    return False


def get_totp_uri(secret: str, account_name: str, issuer: str = "SrivaniSaaS") -> str:
    """Generate an otpauth URI for QR code generation in authenticator apps."""
    return f"otpauth://totp/{issuer}:{account_name}?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"
