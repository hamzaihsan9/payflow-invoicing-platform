from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User, UserRole
from app.schemas.schemas import UserCreate, UserResponse, Token
from app.services.auth_service import (
    verify_password, get_password_hash, create_access_token, 
    get_current_user, record_audit_log
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address is already registered."
        )
    
    hashed_pw = get_password_hash(user_in.password)
    user = User(
        email=user_in.email,
        hashed_password=hashed_pw,
        full_name=user_in.full_name,
        role=user_in.role,
        organization=user_in.organization
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    record_audit_log(
        db, user.id, "USER_REGISTERED", "USER", str(user.id),
        f"Registered new user account: {user.email} [{user.role}]"
    )
    return user

@router.post("/login", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password combination.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role.value, "user_id": user.id}
    )
    record_audit_log(
        db, user.id, "USER_LOGIN", "USER", str(user.id),
        f"User logged in from API client: {user.email}"
    )
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user
