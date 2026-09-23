from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.core.security import hash_password
from backend.app.db.models.enums import UserRole
from backend.app.db.models.user import User


class DuplicateEmailError(Exception):
    pass


def create_user(db: Session, email: str, password: str, role: UserRole) -> User:
    existing = db.query(User).filter(User.email == email).one_or_none()
    if existing is not None:
        raise DuplicateEmailError(f"A user with email {email} already exists")

    user = User(email=email, hashed_password=hash_password(password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session) -> list[User]:
    return db.query(User).order_by(User.created_at).all()
