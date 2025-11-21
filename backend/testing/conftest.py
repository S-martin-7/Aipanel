"""
Configuracion de pytest y fixtures compartidos.

Este archivo contiene fixtures que pueden ser usados en todos los tests.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import create_app
from app.core.database import Base, get_db


# Database de prueba en memoria
SQLALCHEMY_DATABASE_URL = "sqlite:///./testing/test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """
    Fixture de sesion de base de datos para tests.

    Crea las tablas antes de cada test y las elimina despues.
    """
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """
    Fixture de cliente HTTP para tests.

    Crea un TestClient de FastAPI con la base de datos de prueba.
    """
    app = create_app()

    # Override dependency de base de datos
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_user_data():
    """Fixture con datos de usuario de ejemplo."""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "name": "Test User"
    }


@pytest.fixture
def sample_tenant_data():
    """Fixture con datos de tenant de ejemplo."""
    return {
        "name": "Test Tenant",
        "email": "tenant@example.com",
        "status": "ACTIVE"
    }


@pytest.fixture
def sample_agent_data():
    """Fixture con datos de agente de ejemplo."""
    return {
        "name": "Test Agent",
        "description": "Agent for testing",
        "model": "GPT5_MINI",
        "system_prompt": "You are a helpful assistant"
    }
