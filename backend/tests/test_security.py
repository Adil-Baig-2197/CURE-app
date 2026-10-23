import os
from uuid import uuid4

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://cure:test@localhost:5432/cure")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-only-not-for-deployment")

from app.core.config import get_settings
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_cannot_be_used_as_the_original_password() -> None:
    password = "A-long-test-password-123"
    stored_hash = hash_password(password)
    assert stored_hash != password
    assert verify_password(password, stored_hash)
    assert not verify_password("wrong-password", stored_hash)


def test_access_token_round_trip_includes_identity_and_role() -> None:
    get_settings.cache_clear()
    user_id = uuid4()
    payload = decode_access_token(create_access_token(user_id, "patient"))
    assert payload["sub"] == str(user_id)
    assert payload["role"] == "patient"
    assert "exp" in payload
