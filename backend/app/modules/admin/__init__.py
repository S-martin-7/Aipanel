"""
Admin Module - Multi-level administration panels.

Level 1: Platform Admin (Super Admin) - Server/platform control
Level 2: Tenant Admin - Tenant-specific management
Level 3: User Portal - End user interface
"""

from .platform_service import PlatformAdminService
from .platform_router import router as platform_router
from .tenant_service import TenantAdminService
from .tenant_router import router as tenant_router
from .user_portal_service import UserPortalService
from .user_portal_router import router as user_portal_router

__all__ = [
    # Level 1 - Platform Admin
    "PlatformAdminService",
    "platform_router",
    # Level 2 - Tenant Admin
    "TenantAdminService",
    "tenant_router",
    # Level 3 - User Portal
    "UserPortalService",
    "user_portal_router",
]
