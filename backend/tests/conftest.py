"""
Pytest configuration and fixtures.
"""
import asyncio
import pytest
from typing import AsyncGenerator, Generator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db, Base
from app.core.config import settings


# Test database URL (SQLite in-memory for speed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ============ Auth Fixtures ============

@pytest.fixture
async def admin_token(client: AsyncClient) -> str:
    """Get admin authentication token."""
    # Create admin user first
    from app.models.user import User
    from app.core.security import get_password_hash

    # This would typically be set up in test data
    return "test_admin_token"


@pytest.fixture
async def tenant_token(client: AsyncClient) -> str:
    """Get tenant user authentication token."""
    return "test_tenant_token"


# ============ Data Fixtures ============

@pytest.fixture
async def sample_tenant(db_session: AsyncSession):
    """Create a sample tenant for testing."""
    from app.models.tenant import Tenant

    tenant = Tenant(
        name="Test Tenant",
        slug="test-tenant",
        email="test@tenant.com",
        plan_code="demo"
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest.fixture
async def sample_agent(db_session: AsyncSession, sample_tenant):
    """Create a sample agent for testing."""
    from app.models.agent import Agent
    from app.models.enums import AgentStatus

    agent = Agent(
        tenant_id=sample_tenant.id,
        name="Test Agent",
        system_prompt="You are a helpful assistant.",
        status=AgentStatus.ACTIVE
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)
    return agent
