"""
Seed script for AI providers and models.

Run with: python -m app.scripts.seed_ai_providers
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal, init_database
from app.core.config import settings
from app.models import AIProvider, AIModel, AIParamProfile, AIRoute
from app.models.enums import AIModelStatus


# Provider definitions
PROVIDERS = [
    {
        "id": "openai",
        "name": "OpenAI",
        "display_name": "OpenAI",
        "handler_module": "app.integrations.openai_client",
        "handler_class": "OpenAIProvider",
        "is_active": True,
        "allowed_in_prod": True,
        "requests_per_minute": 500,
        "tokens_per_minute": 150000,
    },
    {
        "id": "anthropic",
        "name": "Anthropic",
        "display_name": "Anthropic (Claude)",
        "handler_module": "app.integrations.anthropic_client",
        "handler_class": "AnthropicClient",
        "is_active": True,
        "allowed_in_prod": True,
        "requests_per_minute": 50,
        "tokens_per_minute": 40000,
    },
]

# Model definitions
MODELS = [
    # OpenAI Models
    {
        "id": "gpt-4o",
        "provider_id": "openai",
        "name": "gpt-4o",
        "display_name": "GPT-4o",
        "description": "Most capable GPT-4 model with vision",
        "capabilities": ["chat", "vision", "streaming", "tools", "json_mode"],
        "status": AIModelStatus.STABLE,
        "pricing_input": 0.0025,
        "pricing_output": 0.01,
        "max_tokens": 16384,
        "context_window": 128000,
        "supports_streaming": True,
        "supports_vision": True,
        "supports_tools": True,
        "supports_json_mode": True,
    },
    {
        "id": "gpt-4o-mini",
        "provider_id": "openai",
        "name": "gpt-4o-mini",
        "display_name": "GPT-4o Mini",
        "description": "Fast and affordable GPT-4 model",
        "capabilities": ["chat", "vision", "streaming", "tools", "json_mode"],
        "status": AIModelStatus.STABLE,
        "pricing_input": 0.00015,
        "pricing_output": 0.0006,
        "max_tokens": 16384,
        "context_window": 128000,
        "supports_streaming": True,
        "supports_vision": True,
        "supports_tools": True,
        "supports_json_mode": True,
    },
    {
        "id": "o1",
        "provider_id": "openai",
        "name": "o1",
        "display_name": "O1 (Reasoning)",
        "description": "Advanced reasoning model",
        "capabilities": ["chat", "reasoning"],
        "status": AIModelStatus.EXPERIMENTAL,
        "pricing_input": 0.015,
        "pricing_output": 0.06,
        "max_tokens": 100000,
        "context_window": 200000,
        "supports_streaming": False,
        "supports_vision": False,
        "supports_tools": False,
        "supports_json_mode": False,
    },
    {
        "id": "o1-mini",
        "provider_id": "openai",
        "name": "o1-mini",
        "display_name": "O1 Mini (Reasoning)",
        "description": "Faster reasoning model",
        "capabilities": ["chat", "reasoning"],
        "status": AIModelStatus.EXPERIMENTAL,
        "pricing_input": 0.003,
        "pricing_output": 0.012,
        "max_tokens": 65536,
        "context_window": 128000,
        "supports_streaming": False,
        "supports_vision": False,
        "supports_tools": False,
        "supports_json_mode": False,
    },
    # Anthropic Models
    {
        "id": "claude-sonnet-4-5",
        "provider_id": "anthropic",
        "name": "claude-sonnet-4-5-20250929",
        "display_name": "Claude Sonnet 4.5",
        "description": "Latest Claude model with extended thinking",
        "capabilities": ["chat", "vision", "streaming", "tools", "extended_thinking"],
        "status": AIModelStatus.STABLE,
        "pricing_input": 0.003,
        "pricing_output": 0.015,
        "pricing_cached": 0.0003,
        "max_tokens": 8192,
        "context_window": 200000,
        "supports_streaming": True,
        "supports_vision": True,
        "supports_tools": True,
        "supports_json_mode": True,
    },
    {
        "id": "claude-haiku-3-5",
        "provider_id": "anthropic",
        "name": "claude-3-5-haiku-20241022",
        "display_name": "Claude 3.5 Haiku",
        "description": "Fast and affordable Claude model",
        "capabilities": ["chat", "vision", "streaming", "tools"],
        "status": AIModelStatus.STABLE,
        "pricing_input": 0.0008,
        "pricing_output": 0.004,
        "max_tokens": 8192,
        "context_window": 200000,
        "supports_streaming": True,
        "supports_vision": True,
        "supports_tools": True,
        "supports_json_mode": True,
    },
]

# Parameter profiles
PARAM_PROFILES = [
    {
        "id": "creative",
        "name": "creative",
        "description": "High creativity, varied responses",
        "temperature": 0.9,
        "top_p": 0.95,
        "max_tokens": 4096,
    },
    {
        "id": "balanced",
        "name": "balanced",
        "description": "Balanced creativity and precision",
        "temperature": 0.7,
        "top_p": 1.0,
        "max_tokens": 2048,
    },
    {
        "id": "precise",
        "name": "precise",
        "description": "Low temperature, factual responses",
        "temperature": 0.3,
        "top_p": 0.9,
        "max_tokens": 2048,
    },
    {
        "id": "code",
        "name": "code",
        "description": "Optimized for code generation",
        "temperature": 0.2,
        "top_p": 0.95,
        "max_tokens": 4096,
    },
]

# Default routes
DEFAULT_ROUTES = [
    {
        "id": "default-chat",
        "name": "Default Chat Route",
        "description": "Default route for chat interactions",
        "mode": "CHAT",
        "model_id": "gpt-4o-mini",
        "param_profile_id": "balanced",
        "priority": 0,
        "is_active": True,
    },
    {
        "id": "default-realtime",
        "name": "Default Realtime Route",
        "description": "Default route for realtime interactions",
        "mode": "REALTIME",
        "model_id": "gpt-4o-mini",
        "param_profile_id": "balanced",
        "priority": 0,
        "is_active": True,
    },
]


async def seed_providers():
    """Seed AI providers."""
    async with AsyncSessionLocal() as db:
        for provider_data in PROVIDERS:
            # Check if exists
            result = await db.execute(
                select(AIProvider).where(AIProvider.id == provider_data["id"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"Provider already exists: {provider_data['name']}")
                continue

            # Add config from settings
            config = {}
            if provider_data["name"] == "OpenAI":
                config = {
                    "api_key": settings.OPENAI_API_KEY,
                    "organization_id": settings.OPENAI_ORG_ID
                }
            elif provider_data["name"] == "Anthropic":
                config = {
                    "api_key": settings.ANTHROPIC_API_KEY
                }

            provider = AIProvider(
                **provider_data,
                config_json=config
            )
            db.add(provider)
            print(f"Created provider: {provider_data['name']}")

        await db.commit()


async def seed_models():
    """Seed AI models."""
    async with AsyncSessionLocal() as db:
        for model_data in MODELS:
            result = await db.execute(
                select(AIModel).where(AIModel.id == model_data["id"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"Model already exists: {model_data['name']}")
                continue

            model = AIModel(**model_data)
            db.add(model)
            print(f"Created model: {model_data['name']}")

        await db.commit()


async def seed_param_profiles():
    """Seed parameter profiles."""
    async with AsyncSessionLocal() as db:
        for profile_data in PARAM_PROFILES:
            result = await db.execute(
                select(AIParamProfile).where(AIParamProfile.id == profile_data["id"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"Profile already exists: {profile_data['name']}")
                continue

            profile = AIParamProfile(**profile_data, is_active=True)
            db.add(profile)
            print(f"Created profile: {profile_data['name']}")

        await db.commit()


async def seed_routes():
    """Seed default routes."""
    async with AsyncSessionLocal() as db:
        for route_data in DEFAULT_ROUTES:
            result = await db.execute(
                select(AIRoute).where(AIRoute.id == route_data["id"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"Route already exists: {route_data['name']}")
                continue

            route = AIRoute(**route_data)
            db.add(route)
            print(f"Created route: {route_data['name']}")

        await db.commit()


async def main():
    """Run all seeds."""
    print("Initializing database...")
    await init_database()

    print("\n=== Seeding AI Providers ===")
    await seed_providers()

    print("\n=== Seeding AI Models ===")
    await seed_models()

    print("\n=== Seeding Parameter Profiles ===")
    await seed_param_profiles()

    print("\n=== Seeding Default Routes ===")
    await seed_routes()

    print("\n=== Seed completed! ===")


if __name__ == "__main__":
    asyncio.run(main())
