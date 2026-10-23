"""Create one development administrator from explicitly supplied environment variables."""
import os

from sqlalchemy import select

from app.core.security import hash_password
from app.db.models import User, UserRole
from app.db.session import SessionLocal


def main() -> None:
    email = os.environ.get("INITIAL_ADMIN_EMAIL")
    password = os.environ.get("INITIAL_ADMIN_PASSWORD")
    if not email or not password:
        raise SystemExit("Set INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD first.")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email.lower())):
            raise SystemExit("That email already exists.")
        db.add(User(email=email.lower(), password_hash=hash_password(password), role=UserRole.ADMINISTRATOR))
        db.commit()
    print("Development administrator created.")


if __name__ == "__main__":
    main()
