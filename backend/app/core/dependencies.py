"""
FastAPI dependencies for dependency injection.

Provides reusable dependencies for authentication, database access, etc.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.utils.logger import get_logger

logger = get_logger(__name__)

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current authenticated user from JWT token.

    Args:
        token: JWT token from Authorization header
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode token
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # TODO: Fetch user from database
    # user = await db.execute(select(User).where(User.id == user_id))
    # user = user.scalar_one_or_none()
    # if user is None:
    #     raise credentials_exception

    # Placeholder: Return a dict with user info from token
    # In production, fetch from database
    return {
        "id": user_id,
        "email": payload.get("email"),
        "role": payload.get("role", "USER"),
        "tenant_id": payload.get("tenant_id")
    }


async def get_current_active_user(
    current_user: Annotated[dict, Depends(get_current_user)]
):
    """
    Get the current user and verify they are active.

    Args:
        current_user: User from get_current_user dependency

    Returns:
        Active user object

    Raises:
        HTTPException: If user is inactive
    """
    # TODO: Check if user is active in database
    # if not current_user.is_active:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Inactive user"
    #     )

    return current_user


async def get_current_admin_user(
    current_user: Annotated[dict, Depends(get_current_active_user)]
):
    """
    Get the current user and verify they have admin role.

    Args:
        current_user: Active user from get_current_active_user

    Returns:
        Admin user object

    Raises:
        HTTPException: If user is not admin
    """
    if current_user.get("role") not in ["ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    return current_user


async def get_current_tenant_user(
    current_user: Annotated[dict, Depends(get_current_active_user)]
):
    """
    Get the current user and verify they belong to a tenant.

    Args:
        current_user: Active user from get_current_active_user

    Returns:
        Tenant user object with tenant_id

    Raises:
        HTTPException: If user doesn't have tenant association
    """
    if not current_user.get("tenant_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with a tenant"
        )

    return current_user


# Type aliases for cleaner dependency injection
DB = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(get_current_user)]
ActiveUser = Annotated[dict, Depends(get_current_active_user)]
AdminUser = Annotated[dict, Depends(get_current_admin_user)]
TenantUser = Annotated[dict, Depends(get_current_tenant_user)]
