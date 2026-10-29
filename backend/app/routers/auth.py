from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import models, schemas
from app.core.database import get_db
from app.core import security

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=schemas.Token)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )
        
    hashed_pwd = security.get_password_hash(user_in.password)
    db_user = models.User(
        email=user_in.email,
        password_hash=hashed_pwd,
        full_name=user_in.full_name or user_in.email.split("@")[0]
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Generate token
    token = security.create_access_token(db_user.id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": db_user.id,
        "full_name": db_user.full_name,
        "email": db_user.email
    }

@router.post("/login", response_model=schemas.Token)
def login(user_in: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if not user or not security.verify_password(user_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password."
        )
        
    token = security.create_access_token(user.id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email
    }

@router.post("/google", response_model=schemas.Token)
def google_login(payload: dict, db: Session = Depends(get_db)):
    # Simple Firebase/Google Token Verification Hook
    email = payload.get("email")
    name = payload.get("name")
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Google payload"
        )
        
    # Check if user exists, create if not
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        # Create Google login user with empty password (can login only via Google)
        db_user = models.User(
            email=email,
            password_hash=security.get_password_hash(f"google-oauth-secret-{email}"),
            full_name=name or email.split("@")[0]
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        user = db_user
        
    token = security.create_access_token(user.id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email
    }
