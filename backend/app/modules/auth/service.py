"""
Authentication Service - Business Logic

Handles user authentication, registration, and token management.
Uses SQLAlchemy models and JWT tokens.
"""

from datetime import datetime, timedelta
from typing import Optional
import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token
)
from app.models import User, RefreshToken
from app.models.enums import UserRole
from app.utils.logger import get_logger

from .schemas import LoginRequest, RegisterRequest, AuthResponse, UserResponse

logger = get_logger(__name__)


class AuthService:
    """
    Authentication service.

    Handles login, registration, token refresh, and logout.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize service with database session.

        Args:
            db: Async database session
        """
        self.db = db

    async def login(self, request: LoginRequest) -> AuthResponse:
        """
        Authenticate user and generate tokens.

        Args:
            request: Login credentials (email, password)

        Returns:
            AuthResponse: Access and refresh tokens

        Raises:
            ValueError: If credentials are invalid
        """
        logger.info(f"Login attempt for: {request.email}")

        # Find user by email
        result = await self.db.execute(
            select(User).where(User.email == request.email)
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"User not found: {request.email}")
            raise ValueError("Invalid credentials")

        # Verify password
        if not verify_password(request.password, user.password_hash):
            logger.warning(f"Invalid password for: {request.email}")
            raise ValueError("Invalid credentials")

        # Check if user is active
        if not user.is_active:
            logger.warning(f"Inactive user attempted login: {request.email}")
            raise ValueError("Account is deactivated")

        # Generate tokens
        access_token = create_access_token(
            subject=user.id,
            additional_claims={
                "email": user.email,
                "role": user.role.value,
                "name": user.name
            }
        )

        refresh_token = create_refresh_token(subject=user.id)

        # Store refresh token in database
        await self._store_refresh_token(user.id, refresh_token)

        logger.info(f"Login successful for: {request.email}")

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.JWT_EXPIRES_IN,
            user=UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                role=user.role.value,
                is_active=user.is_active,
                created_at=user.created_at
            )
        )

    async def register(self, request: RegisterRequest) -> AuthResponse:
        """
        Register a new admin user.

        Args:
            request: Registration data

        Returns:
            AuthResponse: Access and refresh tokens

        Raises:
            ValueError: If email already exists
        """
        logger.info(f"Registration attempt for: {request.email}")

        # Check if email already exists
        result = await self.db.execute(
            select(User).where(User.email == request.email)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            logger.warning(f"Email already registered: {request.email}")
            raise ValueError("Email already registered")

        # Parse role
        try:
            role = UserRole(request.role)
        except ValueError:
            role = UserRole.ADMIN

        # Create new user
        user = User(
            email=request.email,
            password_hash=hash_password(request.password),
            name=request.name,
            role=role,
            is_active=True
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        logger.info(f"User registered: {request.email}")

        # Generate tokens
        access_token = create_access_token(
            subject=user.id,
            additional_claims={
                "email": user.email,
                "role": user.role.value,
                "name": user.name
            }
        )

        refresh_token = create_refresh_token(subject=user.id)

        # Store refresh token
        await self._store_refresh_token(user.id, refresh_token)

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.JWT_EXPIRES_IN,
            user=UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                role=user.role.value,
                is_active=user.is_active,
                created_at=user.created_at
            )
        )

    async def refresh_token(self, token: str) -> AuthResponse:
        """
        Refresh access token using refresh token.

        Args:
            token: Valid refresh token

        Returns:
            AuthResponse: New access and refresh tokens

        Raises:
            ValueError: If refresh token is invalid or revoked
        """
        # Decode refresh token
        payload = decode_refresh_token(token)
        if not payload:
            raise ValueError("Invalid refresh token")

        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Invalid refresh token")

        # Check if token is in database and not revoked
        token_hash = self._hash_token(token)
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.is_revoked == False
            )
        )
        stored_token = result.scalar_one_or_none()

        if not stored_token:
            raise ValueError("Refresh token not found or revoked")

        # Get user
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise ValueError("User not found or inactive")

        # Revoke old refresh token
        stored_token.is_revoked = True

        # Generate new tokens
        new_access_token = create_access_token(
            subject=user.id,
            additional_claims={
                "email": user.email,
                "role": user.role.value,
                "name": user.name
            }
        )

        new_refresh_token = create_refresh_token(subject=user.id)

        # Store new refresh token
        await self._store_refresh_token(user.id, new_refresh_token)

        await self.db.commit()

        logger.info(f"Token refreshed for user: {user.email}")

        return AuthResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.JWT_EXPIRES_IN,
            user=UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                role=user.role.value,
                is_active=user.is_active,
                created_at=user.created_at
            )
        )

    async def logout(self, user_id: str, refresh_token: Optional[str] = None) -> None:
        """
        Logout user by revoking refresh tokens.

        Args:
            user_id: User ID
            refresh_token: Specific token to revoke (optional)
        """
        if refresh_token:
            # Revoke specific token
            token_hash = self._hash_token(refresh_token)
            result = await self.db.execute(
                select(RefreshToken).where(
                    RefreshToken.token_hash == token_hash,
                    RefreshToken.user_id == user_id
                )
            )
            stored_token = result.scalar_one_or_none()
            if stored_token:
                stored_token.is_revoked = True
        else:
            # Revoke all tokens for user
            result = await self.db.execute(
                select(RefreshToken).where(
                    RefreshToken.user_id == user_id,
                    RefreshToken.is_revoked == False
                )
            )
            tokens = result.scalars().all()
            for token in tokens:
                token.is_revoked = True

        await self.db.commit()
        logger.info(f"User logged out: {user_id}")

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def _store_refresh_token(
        self,
        user_id: str,
        token: str,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> None:
        """Store refresh token in database."""
        expires_at = datetime.utcnow() + timedelta(seconds=settings.JWT_REFRESH_EXPIRES_IN)

        refresh_token = RefreshToken(
            user_id=user_id,
            token_hash=self._hash_token(token),
            expires_at=expires_at.isoformat(),
            device_info=device_info,
            ip_address=ip_address
        )

        self.db.add(refresh_token)
        await self.db.flush()

    def _hash_token(self, token: str) -> str:
        """Hash a token for secure storage."""
        return hashlib.sha256(token.encode()).hexdigest()
