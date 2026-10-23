from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.db.models import AuditEvent, PatientProfile, User, UserRole
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(RegisterRequest):
    pass


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUserResponse(BaseModel):
    id: UUID
    email: EmailStr
    role: UserRole


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_access_token(token)
        user_id = UUID(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive or unknown account")
    return user


def require_roles(*roles: UserRole):
    def check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return check


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_patient(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Public registration only creates patient accounts; privileged roles require admin workflow."""
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account already uses this email")
    user = User(email=payload.email.lower(), password_hash=hash_password(payload.password), role=UserRole.PATIENT)
    db.add(user)
    db.flush()
    db.add(PatientProfile(user_id=user.id))
    db.add(AuditEvent(actor_id=user.id, action="auth.register", resource_type="user", resource_id=str(user.id)))
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id, user.role.value))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    db.add(AuditEvent(actor_id=user.id, action="auth.login", resource_type="user", resource_id=str(user.id)))
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id, user.role.value))


@router.get("/me", response_model=CurrentUserResponse)
def current_user(user: User = Depends(get_current_user)) -> CurrentUserResponse:
    """Verify a bearer token and return only the caller's own account metadata."""
    return CurrentUserResponse(id=user.id, email=user.email, role=user.role)
