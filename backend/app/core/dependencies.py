"""
FastAPI dependencies for dependency injection.

Provides reusable dependencies for authentication, database access, etc.
"""

from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import decode_access_token
from app.utils.logger import get_logger

logger = get_logger(__name__)

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# API Key header scheme (optional - doesn't raise error if missing)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


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


async def get_api_key_auth(
    request: Request,
    api_key: Optional[str] = Depends(api_key_header),
    db: AsyncSession = Depends(get_db)
) -> Optional[dict]:
    """
    Validate API key from X-API-Key header.

    Returns None if no API key provided (allows fallback to JWT).
    Returns auth context dict if valid API key.
    Raises HTTPException if invalid API key.
    """
    if not api_key:
        return None

    # Import here to avoid circular imports
    from app.models import ExternalAPIKey, Tenant, TenantStatus
    from app.models.external_api_key import hash_api_key

    # Hash the provided key
    key_hash = hash_api_key(api_key)

    # Look up the key
    result = await db.execute(
        select(ExternalAPIKey).where(ExternalAPIKey.key_hash == key_hash)
    )
    api_key_record = result.scalar_one_or_none()

    if not api_key_record:
        logger.warning(f"Invalid API key attempt: {api_key[:12]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    # Check if key is valid
    if not api_key_record.is_valid:
        logger.warning(f"Expired/inactive API key: {api_key_record.key_prefix}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is expired or inactive"
        )

    # Check IP restriction
    client_ip = request.client.host if request.client else "unknown"
    if not api_key_record.check_ip(client_ip):
        logger.warning(f"API key IP restriction: {api_key_record.key_prefix} from {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="IP address not allowed for this API key"
        )

    # Get tenant and verify it's active
    result = await db.execute(
        select(Tenant).where(Tenant.id == api_key_record.tenant_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant or tenant.status != TenantStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is not active"
        )

    # Update usage tracking
    api_key_record.record_usage()
    await db.commit()

    logger.info(f"API key auth: {api_key_record.key_prefix} for tenant {tenant.slug}")

    return {
        "auth_type": "api_key",
        "api_key_id": api_key_record.id,
        "api_key_name": api_key_record.name,
        "tenant_id": api_key_record.tenant_id,
        "tenant_slug": tenant.slug,
        "agent_id": api_key_record.agent_id,  # Optional: restricted to specific agent
        "scopes": api_key_record.scopes or [],
        "rate_limit": api_key_record.rate_limit,
    }


async def get_api_or_jwt_auth(
    request: Request,
    api_key: Optional[str] = Depends(api_key_header),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Authenticate via API key OR JWT token.

    First tries API key (X-API-Key header).
    If no API key, falls back to JWT (Authorization: Bearer).

    Returns auth context with:
    - auth_type: "api_key" or "jwt"
    - tenant_id: The tenant ID
    - Additional context based on auth type
    """
    # Try API key first
    api_auth = await get_api_key_auth(request, api_key, db)
    if api_auth:
        return api_auth

    # Fall back to JWT
    # Extract bearer token manually since we need optional auth
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide X-API-Key header or Authorization: Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header.replace("Bearer ", "")

    # Decode JWT
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenant associated with this user"
        )

    return {
        "auth_type": "jwt",
        "user_id": user_id,
        "email": payload.get("email"),
        "role": payload.get("role", "USER"),
        "tenant_id": tenant_id,
        "scopes": [],  # JWT has all scopes
    }


def require_scope(scope: str):
    """
    Dependency factory to require a specific scope.

    Usage:
        @router.post("/chat")
        async def chat(auth = Depends(require_scope("chat"))):
            ...
    """
    async def check_scope(auth: dict = Depends(get_api_or_jwt_auth)) -> dict:
        # JWT auth has all scopes
        if auth.get("auth_type") == "jwt":
            return auth

        # API key auth - check scopes
        scopes = auth.get("scopes", [])
        if scopes and scope not in scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key does not have required scope: {scope}"
            )

        return auth

    return check_scope


# Type aliases for cleaner dependency injection
DB = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(get_current_user)]
ActiveUser = Annotated[dict, Depends(get_current_active_user)]
AdminUser = Annotated[dict, Depends(get_current_admin_user)]
TenantUser = Annotated[dict, Depends(get_current_tenant_user)]
APIKeyAuth = Annotated[Optional[dict], Depends(get_api_key_auth)]
APIOrJWTAuth = Annotated[dict, Depends(get_api_or_jwt_auth)]
