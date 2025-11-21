"""
Modulo de Autenticacion - Router

Define todos los endpoints REST relacionados con autenticacion.
NO contiene logica de negocio, solo define las rutas y delega a service.py
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from .service import AuthService
from .schemas import (
    LoginRequest,
    RegisterRequest,
    AuthResponse,
    RefreshTokenRequest,
    UserResponse
)
from app.core.dependencies import get_current_user
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    service: AuthService = Depends()
):
    """
    Endpoint de login.

    Args:
        request: Email y password del usuario
        service: Servicio de autenticacion (inyectado)

    Returns:
        AuthResponse: Tokens de acceso y refresh

    Raises:
        HTTPException: Si credenciales son invalidas
    """
    logger.info(f"Login attempt for user: {request.email}")

    try:
        result = await service.login(request)
        logger.info(f"Login successful for user: {request.email}")
        return result
    except Exception as exc:
        logger.error(f"Login failed for user: {request.email} - {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales invalidas"
        )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    service: AuthService = Depends()
):
    """
    Endpoint de registro de nuevos usuarios.

    Args:
        request: Datos del nuevo usuario
        service: Servicio de autenticacion (inyectado)

    Returns:
        AuthResponse: Tokens de acceso y refresh

    Raises:
        HTTPException: Si el email ya esta registrado
    """
    logger.info(f"Registration attempt for email: {request.email}")

    try:
        result = await service.register(request)
        logger.info(f"Registration successful for email: {request.email}")
        return result
    except ValueError as exc:
        logger.warning(f"Registration failed for email: {request.email} - {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    service: AuthService = Depends()
):
    """
    Renovar access token usando refresh token.

    Args:
        request: Refresh token
        service: Servicio de autenticacion (inyectado)

    Returns:
        AuthResponse: Nuevos tokens

    Raises:
        HTTPException: Si refresh token es invalido
    """
    try:
        result = await service.refresh_token(request.refresh_token)
        return result
    except Exception as exc:
        logger.error(f"Token refresh failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalido"
        )


@router.post("/logout")
async def logout(
    current_user: UserResponse = Depends(get_current_user),
    service: AuthService = Depends()
):
    """
    Logout de usuario (invalida refresh token).

    Args:
        current_user: Usuario actual (inyectado desde JWT)
        service: Servicio de autenticacion (inyectado)

    Returns:
        dict: Mensaje de confirmacion
    """
    logger.info(f"Logout for user: {current_user.id}")

    await service.logout(current_user.id)

    return {"message": "Logout exitoso"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Obtener informacion del usuario actual.

    Args:
        current_user: Usuario actual (inyectado desde JWT)

    Returns:
        UserResponse: Datos del usuario
    """
    return current_user
