"""
Seed script to create initial admin user.

Run with: python -m app.scripts.seed_admin
"""

import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, init_database
from app.core.security import hash_password
from app.core.config import settings
from app.models import User
from app.models.enums import UserRole


async def create_admin_user(
    email: str,
    password: str,
    name: str = "Administrator"
) -> User:
    """
    Create an admin user if not exists.

    Args:
        email: Admin email
        password: Admin password
        name: Admin name

    Returns:
        User: Created or existing user
    """
    async with AsyncSessionLocal() as db:
        # Check if user exists
        result = await db.execute(
            select(User).where(User.email == email)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(f"Admin user already exists: {email}")
            return existing_user

        # Create admin user
        user = User(
            email=email,
            password_hash=hash_password(password),
            name=name,
            role=UserRole.SUPER_ADMIN,
            is_active=True
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        print(f"Admin user created: {email}")
        return user


async def seed_default_admin():
    """Create default admin from environment variables."""
    email = os.getenv("ADMIN_EMAIL", "admin@aipanel.local")
    password = os.getenv("ADMIN_PASSWORD", "admin123456")
    name = os.getenv("ADMIN_NAME", "Administrator")

    print(f"Creating admin user: {email}")

    await init_database()
    await create_admin_user(email, password, name)

    print("Seed completed!")


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Seed admin user")
    parser.add_argument("--email", help="Admin email")
    parser.add_argument("--password", help="Admin password")
    parser.add_argument("--name", default="Administrator", help="Admin name")

    args = parser.parse_args()

    await init_database()

    if args.email and args.password:
        await create_admin_user(args.email, args.password, args.name)
    else:
        await seed_default_admin()


if __name__ == "__main__":
    asyncio.run(main())
