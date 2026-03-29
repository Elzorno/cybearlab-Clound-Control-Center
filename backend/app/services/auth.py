import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..config import settings
from ..models import User


@dataclass
class TokenEntry:
    user_id: str
    expires_at: datetime


_TOKEN_STORE: dict[str, TokenEntry] = {}


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, expected = password_hash.split("$", 1)
    except ValueError:
        return False
    computed = hash_password(password, salt)
    return hmac.compare_digest(computed, f"{salt}${expected}")


def bootstrap_admin_user(db: Session) -> None:
    existing = db.query(User).filter(User.username == settings.bootstrap_admin_username).first()
    if existing:
        return

    user = User(
        username=settings.bootstrap_admin_username,
        password_hash=hash_password(settings.bootstrap_admin_password),
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.commit()


def issue_token(user_id: str) -> tuple[str, int]:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(seconds=settings.token_ttl_seconds)
    _TOKEN_STORE[token] = TokenEntry(user_id=user_id, expires_at=expires)
    return token, settings.token_ttl_seconds


def get_token_user(token: str) -> str | None:
    entry = _TOKEN_STORE.get(token)
    if not entry:
        return None
    if entry.expires_at < datetime.now(timezone.utc):
        _TOKEN_STORE.pop(token, None)
        return None
    return entry.user_id
