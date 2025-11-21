"""
Tests del modulo de autenticacion.

Todos los tests del modulo auth deben estar en este archivo.
"""

import pytest
from fastapi import status


class TestAuthLogin:
    """Tests de login."""

    def test_login_success(self, client, sample_user_data):
        """Test de login exitoso."""
        # TODO: Crear usuario en BD primero
        # client.post("/api/v1/auth/register", json=sample_user_data)

        # Intentar login
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": sample_user_data["email"],
                "password": sample_user_data["password"]
            }
        )

        # Verificar respuesta
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, client):
        """Test de login con credenciales invalidas."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "wrong@example.com",
                "password": "wrongpassword"
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_missing_fields(self, client):
        """Test de login con campos faltantes."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com"}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestAuthRegister:
    """Tests de registro."""

    def test_register_success(self, client, sample_user_data):
        """Test de registro exitoso."""
        response = client.post(
            "/api/v1/auth/register",
            json=sample_user_data
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == sample_user_data["email"]

    def test_register_duplicate_email(self, client, sample_user_data):
        """Test de registro con email duplicado."""
        # Registrar primera vez
        client.post("/api/v1/auth/register", json=sample_user_data)

        # Intentar registrar de nuevo
        response = client.post(
            "/api/v1/auth/register",
            json=sample_user_data
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_invalid_email(self, client, sample_user_data):
        """Test de registro con email invalido."""
        sample_user_data["email"] = "invalid-email"

        response = client.post(
            "/api/v1/auth/register",
            json=sample_user_data
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_short_password(self, client, sample_user_data):
        """Test de registro con password muy corto."""
        sample_user_data["password"] = "short"

        response = client.post(
            "/api/v1/auth/register",
            json=sample_user_data
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestAuthRefresh:
    """Tests de refresh token."""

    def test_refresh_token_success(self, client, sample_user_data):
        """Test de refresh exitoso."""
        # TODO: Implementar cuando refresh token este listo
        pytest.skip("Refresh token not implemented yet")

    def test_refresh_token_invalid(self, client):
        """Test de refresh con token invalido."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAuthLogout:
    """Tests de logout."""

    def test_logout_success(self, client):
        """Test de logout exitoso."""
        # TODO: Implementar cuando logout este listo
        pytest.skip("Logout not implemented yet")
