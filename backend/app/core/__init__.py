"""
Core module - Application foundation.

Provides configuration, database, security, and dependency injection.
"""

from .config import settings
from .database import get_db, Base, init_database, close_database
from .security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token
)
from .dependencies import (
    get_current_user,
    get_current_active_user,
    get_current_admin_user,
    get_current_tenant_user,
    DB,
    CurrentUser,
    ActiveUser,
    AdminUser,
    TenantUser
)

__all__ = [
    # Config
    "settings",
    # Database
    "get_db",
    "Base",
    "init_database",
    "close_database",
    # Security
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_access_token",
    "decode_refresh_token",
    # Dependencies
    "get_current_user",
    "get_current_active_user",
    "get_current_admin_user",
    "get_current_tenant_user",
    "DB",
    "CurrentUser",
    "ActiveUser",
    "AdminUser",
    "TenantUser",
]
