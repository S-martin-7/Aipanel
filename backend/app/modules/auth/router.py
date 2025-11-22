"""
Authentication Module - Router

REST endpoints for authentication.
Delegates all business logic to AuthService.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, CurrentUser
from app.utils.logger import get_logger

from .service import AuthService
from .schemas import (
    LoginRequest,
    RegisterRequest,
    AuthResponse,
    RefreshTokenRequest,
    UserResponse
)

logger = get_logger(__name__)

router = APIRouter()


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Dependency to get AuthService with database session."""
    return AuthService(db)


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    service: AuthService = Depends(get_auth_service)
):
    """
    Authenticate user and get tokens.

    Args:
        request: Email and password

    Returns:
        AuthResponse: Access and refresh tokens
    """
    try:
        result = await service.login(request)
        return result
    except ValueError as exc:
        logger.warning(f"Login failed for {request.email}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    service: AuthService = Depends(get_auth_service)
):
    """
    Register a new admin user.

    Args:
        request: Registration data (email, password, name)

    Returns:
        AuthResponse: Access and refresh tokens
    """
    try:
        result = await service.register(request)
        return result
    except ValueError as exc:
        logger.warning(f"Registration failed for {request.email}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    service: AuthService = Depends(get_auth_service)
):
    """
    Refresh access token using refresh token.

    Args:
        request: Refresh token

    Returns:
        AuthResponse: New access and refresh tokens
    """
    try:
        result = await service.refresh_token(request.refresh_token)
        return result
    except ValueError as exc:
        logger.warning(f"Token refresh failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"}
        )


@router.post("/logout")
async def logout(
    current_user: CurrentUser,
    service: AuthService = Depends(get_auth_service)
):
    """
    Logout user (revoke refresh tokens).

    Requires valid access token.
    """
    user_id = current_user.get("id")
    await service.logout(user_id)
    logger.info(f"User logged out: {user_id}")
    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_current_user_info(
    current_user: CurrentUser,
    service: AuthService = Depends(get_auth_service)
):
    """
    Get current user information.

    Returns user data from JWT token, optionally enriched from database.
    """
    user_id = current_user.get("id")

    # Optionally fetch fresh data from database
    user = await service.get_user_by_id(user_id)

    if user:
        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at
        )

    # Fallback to token data
    return {
        "id": current_user.get("id"),
        "email": current_user.get("email"),
        "name": current_user.get("name"),
        "role": current_user.get("role")
    }
