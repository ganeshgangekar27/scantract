"""
Authentication API endpoints.
"""
import os
import secrets
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import User, PasswordResetToken
from app.auth.password import hash_password, verify_password
from app.auth.jwt import create_access_token
from app.auth.dependencies import get_current_user


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# Request/Response models
class RegisterRequest(BaseModel):
    """Registration request."""
    email: EmailStr
    password: str
    full_name: str
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class RegisterResponse(BaseModel):
    """Registration response."""
    access_token: str
    token_type: str = "bearer"
    user: dict


class LoginRequest(BaseModel):
    """Login request."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response."""
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """User info response."""
    id: int
    email: str
    full_name: str
    created_at: datetime
    is_active: bool


class ForgotPasswordRequest(BaseModel):
    """Forgot password request."""
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """Forgot password response."""
    message: str
    demo_reset_link: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    """Reset password request."""
    token: str
    new_password: str
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
) -> RegisterResponse:
    """
    Register a new user.
    
    Args:
        request: Registration data
        db: Database session
    
    Returns:
        Access token and user info
    
    Raises:
        HTTPException: 409 if email already exists
    """
    # Check if email already exists (case-insensitive)
    email_lower = request.email.lower()
    result = await db.execute(
        select(User).where(User.email == email_lower)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists"
        )
    
    # Hash password
    password_hash = hash_password(request.password)
    
    # Create user
    user = User(
        email=email_lower,
        full_name=request.full_name,
        password_hash=password_hash,
        created_at=datetime.now(timezone.utc),
        is_active=True
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Create access token
    token = create_access_token(user.id, user.email)
    
    logger.info(f"New user registered: {user.email} (ID: {user.id})")
    
    return RegisterResponse(
        access_token=token,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "created_at": user.created_at.isoformat()
        }
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
) -> LoginResponse:
    """
    Login with email and password.
    
    Args:
        request: Login credentials
        db: Database session
    
    Returns:
        Access token
    
    Raises:
        HTTPException: 401 if credentials invalid
    """
    # Find user by email (case-insensitive)
    email_lower = request.email.lower()
    result = await db.execute(
        select(User).where(User.email == email_lower)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No account found with this email"
        )
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive"
        )
    
    # Create access token
    token = create_access_token(user.id, user.email)
    
    logger.info(f"User logged in: {user.email}")
    
    return LoginResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """
    Get current user info.
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        User info
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        created_at=current_user.created_at,
        is_active=current_user.is_active
    )


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
) -> ForgotPasswordResponse:
    """
    Initiate password reset process.
    
    Always returns same response regardless of whether email exists.
    
    Args:
        request: Email address
        db: Database session
    
    Returns:
        Success message (and demo link if in demo mode)
    """
    # Find user by email
    email_lower = request.email.lower()
    result = await db.execute(
        select(User).where(User.email == email_lower)
    )
    user = result.scalar_one_or_none()
    
    # Always return same message (don't reveal if email exists)
    response = ForgotPasswordResponse(
        message="If an account exists with this email, a password reset link has been sent."
    )
    
    # Only create token if user exists
    if user:
        # Generate reset token (URL-safe random string)
        raw_token = secrets.token_urlsafe(32)
        
        # Hash token for storage (SHA-256)
        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
        
        # Create token record
        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
            created_at=datetime.now(timezone.utc)
        )
        
        db.add(reset_token)
        await db.commit()
        
        # Get reset link mode
        reset_mode = os.getenv("RESET_LINK_MODE", "demo")
        
        if reset_mode == "demo":
            # In demo mode, include link in response and log it
            reset_link = f"http://localhost:3000/reset-password?token={raw_token}"
            response.demo_reset_link = reset_link
            logger.info(f"Password reset link for {user.email}: {reset_link}")
        else:
            # SMTP mode: send email (TODO)
            logger.warning("SMTP password reset not implemented yet")
            raise NotImplementedError(
                "Email sending not implemented. Set RESET_LINK_MODE=demo to use demo mode."
            )
    
    return response


@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Reset password using a valid token.
    
    Args:
        request: Token and new password
        db: Database session
    
    Returns:
        Success message
    
    Raises:
        HTTPException: 400 if token invalid, expired, or already used
    """
    # Hash the provided token
    token_hash = hashlib.sha256(request.token.encode('utf-8')).hexdigest()
    
    # Find token in database
    result = await db.execute(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == token_hash)
    )
    reset_token = result.scalar_one_or_none()
    
    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password reset link"
        )
    
    # Check if token already used
    if reset_token.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset link already used"
        )
    
    # Check if token expired
    if datetime.now(timezone.utc) > reset_token.expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset link has expired"
        )
    
    # Get user
    result = await db.execute(
        select(User).where(User.id == reset_token.user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )
    
    # Hash new password
    user.password_hash = hash_password(request.new_password)
    
    # Mark token as used
    reset_token.used_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    logger.info(f"Password reset successful for user: {user.email}")
    
    return {"message": "Password has been reset successfully"}




@router.delete("/me/data")
async def delete_my_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Delete all user data (contracts, findings, clauses) and user account.
    
    This action is irreversible. Deletes:
    - All user's contracts (and related findings/clauses via cascade)
    - The user account itself
    
    The JWT token becomes invalid after this operation.
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Number of contracts deleted
    """
    from sqlalchemy import delete as sql_delete
    from app.db.models import Contract, Clause, RiskFinding
    
    # Count contracts to delete
    result = await db.execute(
        select(Contract)
        .where(Contract.user_id == current_user.id)
    )
    contracts = result.scalars().all()
    contract_count = len(contracts)
    contract_ids = [c.id for c in contracts]
    
    # Delete related data
    if contract_ids:
        await db.execute(
            sql_delete(RiskFinding).where(RiskFinding.contract_id.in_(contract_ids))
        )
        await db.execute(
            sql_delete(Clause).where(Clause.contract_id.in_(contract_ids))
        )
        await db.execute(
            sql_delete(Contract).where(Contract.id.in_(contract_ids))
        )
    
    # Delete user
    await db.delete(current_user)
    await db.commit()
    
    logger.info(f"User deleted their data: {current_user.email} ({contract_count} contracts)")
    
    return {
        "success": True,
        "data": {
            "deleted_contracts": contract_count
        }
    }
