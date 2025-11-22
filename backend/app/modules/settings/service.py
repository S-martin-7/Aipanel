"""
Settings Module - Service.

Business logic for settings management.
"""

import base64
from typing import Optional, List
from datetime import datetime

from cryptography.fernet import Fernet
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Tenant, TenantAPIKey, AIProviderType
from app.utils.logger import get_logger

from .schemas import (
    CreateAPIKeyRequest,
    UpdateAPIKeyRequest,
    APIKeyResponse,
    APIKeyListResponse,
    ProviderInfo,
    AvailableProvidersResponse,
    TenantSettingsResponse,
    ValidateAPIKeyResponse,
)

logger = get_logger(__name__)


class SettingsService:
    """
    Service for managing tenant settings.

    Handles API key CRUD, encryption, and validation.
    """

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db
        self._init_cipher()

    def _init_cipher(self) -> None:
        """Initialize encryption cipher."""
        # Use SECRET_KEY to derive Fernet key (must be 32 bytes base64)
        key_bytes = settings.SECRET_KEY.encode()[:32].ljust(32, b'0')
        self._cipher = Fernet(base64.urlsafe_b64encode(key_bytes))

    def _encrypt_key(self, api_key: str) -> str:
        """Encrypt an API key."""
        return self._cipher.encrypt(api_key.encode()).decode()

    def _decrypt_key(self, encrypted_key: str) -> str:
        """Decrypt an API key."""
        return self._cipher.decrypt(encrypted_key.encode()).decode()

    def _mask_key(self, api_key: str) -> str:
        """Mask API key showing only last 4 characters."""
        if len(api_key) <= 8:
            return "*" * len(api_key)
        return "*" * (len(api_key) - 4) + api_key[-4:]

    async def get_api_keys(self, tenant_id: str) -> APIKeyListResponse:
        """
        Get all API keys for a tenant.

        Args:
            tenant_id: Tenant ID

        Returns:
            List of API keys (masked)
        """
        result = await self.db.execute(
            select(TenantAPIKey).where(TenantAPIKey.tenant_id == tenant_id)
        )
        keys = result.scalars().all()

        items = []
        for key in keys:
            # Decrypt to get mask
            try:
                decrypted = self._decrypt_key(key.api_key_encrypted)
                masked = self._mask_key(decrypted)
            except Exception:
                masked = "****ERROR****"

            items.append(APIKeyResponse(
                id=key.id,
                provider_type=key.provider_type,
                provider_name=key.provider_name,
                organization_id=key.organization_id,
                base_url=key.base_url,
                is_active=key.is_active,
                is_valid=key.is_valid,
                api_key_masked=masked,
                last_validated_at=key.last_validated_at,
                last_error=key.last_error,
                created_at=key.created_at,
                updated_at=key.updated_at,
            ))

        return APIKeyListResponse(items=items, total=len(items))

    async def create_api_key(
        self,
        tenant_id: str,
        request: CreateAPIKeyRequest
    ) -> APIKeyResponse:
        """
        Create or update an API key for a tenant.

        If a key already exists for the provider, it will be updated.

        Args:
            tenant_id: Tenant ID
            request: API key creation request

        Returns:
            Created/updated API key response
        """
        # Check if key exists for this provider
        result = await self.db.execute(
            select(TenantAPIKey).where(
                TenantAPIKey.tenant_id == tenant_id,
                TenantAPIKey.provider_type == request.provider_type
            )
        )
        existing_key = result.scalar_one_or_none()

        encrypted_key = self._encrypt_key(request.api_key)

        if existing_key:
            # Update existing key
            existing_key.api_key_encrypted = encrypted_key
            existing_key.provider_name = request.provider_name
            existing_key.organization_id = request.organization_id
            existing_key.base_url = request.base_url
            existing_key.is_valid = True  # Reset validation status
            existing_key.last_error = None
            existing_key.updated_at = datetime.utcnow()

            await self.db.commit()
            await self.db.refresh(existing_key)

            logger.info(f"Updated API key for {request.provider_type} in tenant {tenant_id}")
            key = existing_key
        else:
            # Create new key
            key = TenantAPIKey(
                tenant_id=tenant_id,
                provider_type=request.provider_type,
                provider_name=request.provider_name,
                api_key_encrypted=encrypted_key,
                organization_id=request.organization_id,
                base_url=request.base_url,
                is_active=True,
                is_valid=True,
            )
            self.db.add(key)
            await self.db.commit()
            await self.db.refresh(key)

            logger.info(f"Created API key for {request.provider_type} in tenant {tenant_id}")

        return APIKeyResponse(
            id=key.id,
            provider_type=key.provider_type,
            provider_name=key.provider_name,
            organization_id=key.organization_id,
            base_url=key.base_url,
            is_active=key.is_active,
            is_valid=key.is_valid,
            api_key_masked=self._mask_key(request.api_key),
            last_validated_at=key.last_validated_at,
            last_error=key.last_error,
            created_at=key.created_at,
            updated_at=key.updated_at,
        )

    async def update_api_key(
        self,
        tenant_id: str,
        key_id: str,
        request: UpdateAPIKeyRequest
    ) -> Optional[APIKeyResponse]:
        """
        Update an API key.

        Args:
            tenant_id: Tenant ID
            key_id: API key ID
            request: Update request

        Returns:
            Updated API key or None if not found
        """
        result = await self.db.execute(
            select(TenantAPIKey).where(
                TenantAPIKey.id == key_id,
                TenantAPIKey.tenant_id == tenant_id
            )
        )
        key = result.scalar_one_or_none()

        if not key:
            return None

        if request.api_key is not None:
            key.api_key_encrypted = self._encrypt_key(request.api_key)
            key.is_valid = True
            key.last_error = None

        if request.organization_id is not None:
            key.organization_id = request.organization_id

        if request.base_url is not None:
            key.base_url = request.base_url

        if request.is_active is not None:
            key.is_active = request.is_active

        key.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(key)

        # Decrypt for masking
        decrypted = self._decrypt_key(key.api_key_encrypted)

        return APIKeyResponse(
            id=key.id,
            provider_type=key.provider_type,
            provider_name=key.provider_name,
            organization_id=key.organization_id,
            base_url=key.base_url,
            is_active=key.is_active,
            is_valid=key.is_valid,
            api_key_masked=self._mask_key(decrypted),
            last_validated_at=key.last_validated_at,
            last_error=key.last_error,
            created_at=key.created_at,
            updated_at=key.updated_at,
        )

    async def delete_api_key(self, tenant_id: str, key_id: str) -> bool:
        """
        Delete an API key.

        Args:
            tenant_id: Tenant ID
            key_id: API key ID

        Returns:
            True if deleted, False if not found
        """
        result = await self.db.execute(
            select(TenantAPIKey).where(
                TenantAPIKey.id == key_id,
                TenantAPIKey.tenant_id == tenant_id
            )
        )
        key = result.scalar_one_or_none()

        if not key:
            return False

        await self.db.delete(key)
        await self.db.commit()

        logger.info(f"Deleted API key {key_id} from tenant {tenant_id}")
        return True

    async def validate_api_key(
        self,
        tenant_id: str,
        key_id: str
    ) -> ValidateAPIKeyResponse:
        """
        Validate an API key by testing it with the provider.

        Args:
            tenant_id: Tenant ID
            key_id: API key ID

        Returns:
            Validation result
        """
        result = await self.db.execute(
            select(TenantAPIKey).where(
                TenantAPIKey.id == key_id,
                TenantAPIKey.tenant_id == tenant_id
            )
        )
        key = result.scalar_one_or_none()

        if not key:
            return ValidateAPIKeyResponse(
                is_valid=False,
                message="API key not found",
                provider_type=AIProviderType.CUSTOM
            )

        # Decrypt key
        try:
            api_key = self._decrypt_key(key.api_key_encrypted)
        except Exception as e:
            key.is_valid = False
            key.last_error = "Failed to decrypt key"
            await self.db.commit()
            return ValidateAPIKeyResponse(
                is_valid=False,
                message="Failed to decrypt API key",
                provider_type=key.provider_type
            )

        # Test key based on provider
        is_valid = False
        message = ""

        try:
            if key.provider_type == AIProviderType.OPENAI:
                is_valid, message = await self._validate_openai_key(api_key, key.organization_id)
            elif key.provider_type == AIProviderType.ANTHROPIC:
                is_valid, message = await self._validate_anthropic_key(api_key)
            else:
                is_valid = True
                message = "Validation not implemented for this provider"
        except Exception as e:
            is_valid = False
            message = str(e)

        # Update key status
        key.is_valid = is_valid
        key.last_validated_at = datetime.utcnow()
        key.last_error = None if is_valid else message
        await self.db.commit()

        return ValidateAPIKeyResponse(
            is_valid=is_valid,
            message=message,
            provider_type=key.provider_type
        )

    async def _validate_openai_key(
        self,
        api_key: str,
        organization_id: Optional[str] = None
    ) -> tuple[bool, str]:
        """Validate OpenAI API key."""
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=api_key, organization=organization_id)
            # Simple test: list models
            await client.models.list()
            return True, "OpenAI API key is valid"
        except Exception as e:
            return False, f"OpenAI validation failed: {str(e)}"

    async def _validate_anthropic_key(self, api_key: str) -> tuple[bool, str]:
        """Validate Anthropic API key."""
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=api_key)
            # Simple test: count tokens
            await client.count_tokens("test")
            return True, "Anthropic API key is valid"
        except Exception as e:
            return False, f"Anthropic validation failed: {str(e)}"

    async def get_available_providers(self) -> AvailableProvidersResponse:
        """Get list of available AI providers."""
        providers = [
            ProviderInfo(
                provider_type=AIProviderType.OPENAI,
                provider_name="OpenAI",
                description="GPT-4o, GPT-4o-mini, O1 and other OpenAI models",
                config_help="Get your API key from https://platform.openai.com/api-keys",
            ),
            ProviderInfo(
                provider_type=AIProviderType.ANTHROPIC,
                provider_name="Anthropic",
                description="Claude Sonnet 4.5, Claude Haiku and other Claude models",
                config_help="Get your API key from https://console.anthropic.com/",
            ),
            ProviderInfo(
                provider_type=AIProviderType.GOOGLE,
                provider_name="Google AI",
                description="Gemini Pro and other Google AI models",
                config_help="Get your API key from https://aistudio.google.com/",
            ),
        ]
        return AvailableProvidersResponse(providers=providers)

    async def get_tenant_settings(self, tenant_id: str) -> Optional[TenantSettingsResponse]:
        """Get tenant settings summary."""
        # Get tenant
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            return None

        # Count configured API keys
        keys_result = await self.db.execute(
            select(func.count(TenantAPIKey.id)).where(
                TenantAPIKey.tenant_id == tenant_id,
                TenantAPIKey.is_active == True
            )
        )
        api_keys_count = keys_result.scalar() or 0

        # Check specific providers
        openai_result = await self.db.execute(
            select(TenantAPIKey).where(
                TenantAPIKey.tenant_id == tenant_id,
                TenantAPIKey.provider_type == AIProviderType.OPENAI,
                TenantAPIKey.is_active == True
            )
        )
        has_openai = openai_result.scalar_one_or_none() is not None

        anthropic_result = await self.db.execute(
            select(TenantAPIKey).where(
                TenantAPIKey.tenant_id == tenant_id,
                TenantAPIKey.provider_type == AIProviderType.ANTHROPIC,
                TenantAPIKey.is_active == True
            )
        )
        has_anthropic = anthropic_result.scalar_one_or_none() is not None

        return TenantSettingsResponse(
            tenant_id=tenant.id,
            tenant_name=tenant.name,
            plan=tenant.plan.value,
            api_keys_configured=api_keys_count,
            has_openai=has_openai,
            has_anthropic=has_anthropic,
            monthly_token_limit=tenant.monthly_token_limit,
            current_usage=tenant.current_month_usage,
        )

    async def get_decrypted_api_key(
        self,
        tenant_id: str,
        provider_type: AIProviderType
    ) -> Optional[dict]:
        """
        Get decrypted API key config for a provider.

        This is used internally by the AI Engine.

        Args:
            tenant_id: Tenant ID
            provider_type: Provider type

        Returns:
            Dict with api_key and optional config, or None if not found
        """
        result = await self.db.execute(
            select(TenantAPIKey).where(
                TenantAPIKey.tenant_id == tenant_id,
                TenantAPIKey.provider_type == provider_type,
                TenantAPIKey.is_active == True
            )
        )
        key = result.scalar_one_or_none()

        if not key:
            return None

        try:
            api_key = self._decrypt_key(key.api_key_encrypted)
            return {
                "api_key": api_key,
                "organization_id": key.organization_id,
                "base_url": key.base_url,
            }
        except Exception:
            return None
