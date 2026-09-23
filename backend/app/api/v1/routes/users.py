from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db, require_roles
from backend.app.db.models.enums import UserRole
from backend.app.db.models.user import User
from backend.app.schemas.user import UserCreate, UserRead
from backend.app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
def create_user(body: UserCreate, db: Session = Depends(get_db)) -> User:
    try:
        return user_service.create_user(db, body.email, body.password, body.role)
    except user_service.DuplicateEmailError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get(
    "",
    response_model=list[UserRead],
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
def list_users(db: Session = Depends(get_db)) -> list[User]:
    return user_service.list_users(db)


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user
