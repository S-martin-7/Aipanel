# Guia de Desarrollo - AIPanel

Guia completa para desarrollar el proyecto AIPanel con arquitectura modular.

## Principios Fundamentales

### 1. Sin Emojis
- NUNCA usar emojis en codigo, logs o mensajes
- Usar solo caracteres ASCII
- Razon: Compatibilidad total con Windows/Linux/Mac
- Evita errores de encoding

### 2. Modularidad
- Cada modulo es independiente
- Se puede desarrollar, testear y desplegar por separado
- Comunicacion via interfaces bien definidas

### 3. Separacion de Responsabilidades
- Codigo de produccion: backend/app/
- Tests: backend/testing/
- Debugging: backend/debugging/
- Logs: backend/logs/
- Errores: backend/errors/
- Documentacion: documentation/

## Configuracion del Entorno

### Requisitos
- Python 3.11+
- Node.js 20+
- PostgreSQL 15+
- Redis 7+

### Setup Inicial

```bash
# 1. Clonar repositorio
git clone <repo-url> aipanel
cd aipanel

# 2. Backend - Crear virtual environment
cd backend
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows

# 3. Instalar dependencias
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Para development

# 4. Configurar variables de entorno
cp ../.env.example .env
# Editar .env con tus credenciales

# 5. Frontend - Instalar dependencias
cd ../frontend
npm install

# 6. Base de datos - Ejecutar migraciones
cd ../backend
alembic upgrade head
```

## Crear un Nuevo Modulo

### Paso 1: Crear Estructura de Directorios

```bash
cd backend/app/modules
mkdir nuevo_modulo
cd nuevo_modulo

# Crear archivos base
touch __init__.py
touch router.py
touch service.py
touch schemas.py
touch models.py
```

### Paso 2: Definir Schemas (schemas.py)

```python
"""
Modulo Nuevo - Schemas

Define validacion de datos con Pydantic.
"""

from pydantic import BaseModel, Field
from datetime import datetime


class CreateRequest(BaseModel):
    """Request para crear recurso."""
    name: str = Field(..., min_length=2, max_length=100)
    description: str | None = None


class UpdateRequest(BaseModel):
    """Request para actualizar recurso."""
    name: str | None = None
    description: str | None = None


class ResourceResponse(BaseModel):
    """Response con datos del recurso."""
    id: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

### Paso 3: Definir Modelos de BD (models.py)

```python
"""
Modulo Nuevo - Models

Define modelos de base de datos con SQLAlchemy.
"""

from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func

from app.core.database import Base


class Resource(Base):
    """Modelo de recurso."""

    __tablename__ = "resources"

    id = Column(String, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### Paso 4: Implementar Logica de Negocio (service.py)

```python
"""
Modulo Nuevo - Service

Contiene toda la logica de negocio.
NO debe tener codigo de FastAPI.
"""

from typing import List
from sqlalchemy.orm import Session

from .models import Resource
from .schemas import CreateRequest, UpdateRequest, ResourceResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ResourceService:
    """Servicio de recursos."""

    def __init__(self, db: Session):
        """
        Inicializar servicio.

        Args:
            db: Sesion de base de datos
        """
        self.db = db

    async def create(self, request: CreateRequest) -> ResourceResponse:
        """
        Crear nuevo recurso.

        Args:
            request: Datos del recurso

        Returns:
            ResourceResponse: Recurso creado
        """
        logger.info(f"Creating resource: {request.name}")

        resource = Resource(
            name=request.name,
            description=request.description
        )

        self.db.add(resource)
        await self.db.commit()
        await self.db.refresh(resource)

        logger.info(f"Resource created: {resource.id}")

        return ResourceResponse.from_orm(resource)

    async def get_all(self) -> List[ResourceResponse]:
        """
        Obtener todos los recursos.

        Returns:
            List[ResourceResponse]: Lista de recursos
        """
        resources = await self.db.query(Resource).all()
        return [ResourceResponse.from_orm(r) for r in resources]

    async def get_by_id(self, resource_id: str) -> ResourceResponse:
        """
        Obtener recurso por ID.

        Args:
            resource_id: ID del recurso

        Returns:
            ResourceResponse: Recurso encontrado

        Raises:
            ValueError: Si recurso no existe
        """
        resource = await self.db.query(Resource).filter(
            Resource.id == resource_id
        ).first()

        if not resource:
            raise ValueError(f"Resource not found: {resource_id}")

        return ResourceResponse.from_orm(resource)

    async def update(self, resource_id: str, request: UpdateRequest) -> ResourceResponse:
        """
        Actualizar recurso.

        Args:
            resource_id: ID del recurso
            request: Datos a actualizar

        Returns:
            ResourceResponse: Recurso actualizado
        """
        resource = await self.db.query(Resource).filter(
            Resource.id == resource_id
        ).first()

        if not resource:
            raise ValueError(f"Resource not found: {resource_id}")

        # Actualizar solo campos proporcionados
        if request.name is not None:
            resource.name = request.name
        if request.description is not None:
            resource.description = request.description

        await self.db.commit()
        await self.db.refresh(resource)

        return ResourceResponse.from_orm(resource)

    async def delete(self, resource_id: str) -> None:
        """
        Eliminar recurso.

        Args:
            resource_id: ID del recurso
        """
        resource = await self.db.query(Resource).filter(
            Resource.id == resource_id
        ).first()

        if not resource:
            raise ValueError(f"Resource not found: {resource_id}")

        await self.db.delete(resource)
        await self.db.commit()
```

### Paso 5: Definir Endpoints REST (router.py)

```python
"""
Modulo Nuevo - Router

Define endpoints REST del modulo.
NO contiene logica de negocio.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from .service import ResourceService
from .schemas import CreateRequest, UpdateRequest, ResourceResponse
from app.core.dependencies import get_db, get_current_user
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED)
async def create_resource(
    request: CreateRequest,
    service: ResourceService = Depends(),
    current_user = Depends(get_current_user)
):
    """
    Crear nuevo recurso.

    Args:
        request: Datos del recurso
        service: Servicio de recursos (inyectado)
        current_user: Usuario actual (inyectado)

    Returns:
        ResourceResponse: Recurso creado
    """
    try:
        return await service.create(request)
    except Exception as exc:
        logger.error(f"Failed to create resource: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )


@router.get("/", response_model=List[ResourceResponse])
async def get_resources(
    service: ResourceService = Depends(),
    current_user = Depends(get_current_user)
):
    """
    Obtener todos los recursos.

    Args:
        service: Servicio de recursos (inyectado)
        current_user: Usuario actual (inyectado)

    Returns:
        List[ResourceResponse]: Lista de recursos
    """
    return await service.get_all()


@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(
    resource_id: str,
    service: ResourceService = Depends(),
    current_user = Depends(get_current_user)
):
    """
    Obtener recurso por ID.

    Args:
        resource_id: ID del recurso
        service: Servicio de recursos (inyectado)
        current_user: Usuario actual (inyectado)

    Returns:
        ResourceResponse: Recurso encontrado
    """
    try:
        return await service.get_by_id(resource_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc)
        )


@router.put("/{resource_id}", response_model=ResourceResponse)
async def update_resource(
    resource_id: str,
    request: UpdateRequest,
    service: ResourceService = Depends(),
    current_user = Depends(get_current_user)
):
    """
    Actualizar recurso.

    Args:
        resource_id: ID del recurso
        request: Datos a actualizar
        service: Servicio de recursos (inyectado)
        current_user: Usuario actual (inyectado)

    Returns:
        ResourceResponse: Recurso actualizado
    """
    try:
        return await service.update(resource_id, request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc)
        )


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(
    resource_id: str,
    service: ResourceService = Depends(),
    current_user = Depends(get_current_user)
):
    """
    Eliminar recurso.

    Args:
        resource_id: ID del recurso
        service: Servicio de recursos (inyectado)
        current_user: Usuario actual (inyectado)
    """
    try:
        await service.delete(resource_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc)
        )
```

### Paso 6: Exportar Interfaces Publicas (__init__.py)

```python
"""
Modulo Nuevo

Exporta interfaces publicas del modulo.
"""

from .router import router
from .service import ResourceService
from .schemas import ResourceResponse

__all__ = ["router", "ResourceService", "ResourceResponse"]
```

### Paso 7: Registrar Router en main.py

```python
# En backend/app/main.py

from app.modules.nuevo_modulo.router import router as nuevo_router

# En _register_routers()
app.include_router(
    nuevo_router,
    prefix=f"{api_prefix}/recursos",
    tags=["recursos"]
)
```

## Crear Tests del Modulo

```python
# backend/testing/test_nuevo_modulo.py

"""
Tests del modulo Nuevo.

Todos los tests del modulo deben estar aqui.
"""

import pytest
from fastapi import status


class TestResourceCreate:
    """Tests de creacion de recursos."""

    def test_create_success(self, client, sample_user_data):
        """Test de creacion exitosa."""
        response = client.post(
            "/api/v1/recursos",
            json={
                "name": "Test Resource",
                "description": "Test description"
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Test Resource"
        assert "id" in data

    def test_create_missing_name(self, client):
        """Test de creacion sin nombre."""
        response = client.post(
            "/api/v1/recursos",
            json={"description": "Test"}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestResourceRead:
    """Tests de lectura de recursos."""

    def test_get_all(self, client):
        """Test de obtener todos los recursos."""
        response = client.get("/api/v1/recursos")

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    def test_get_by_id_not_found(self, client):
        """Test de obtener recurso que no existe."""
        response = client.get("/api/v1/recursos/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND
```

## Ejecutar Tests

```bash
# Todos los tests
pytest backend/testing/

# Test especifico
pytest backend/testing/test_nuevo_modulo.py

# Con coverage
pytest backend/testing/ --cov=backend/app --cov-report=html

# Ver reporte de coverage
open htmlcov/index.html
```

## Crear Script de Debugging

```python
# backend/debugging/debug_nuevo_modulo.py

"""
Script de debugging para el modulo nuevo.

Uso:
    python backend/debugging/debug_nuevo_modulo.py
"""

import asyncio
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.modules.nuevo_modulo.service import ResourceService
from app.utils.logger import setup_logging, get_logger

logger = get_logger(__name__)


async def test_create_resource():
    """Test de creacion de recurso."""

    print("=" * 60)
    print("RESOURCE CREATION TEST")
    print("=" * 60)

    try:
        # TODO: Crear instancia de service
        # service = ResourceService(db=test_db)

        # TODO: Crear recurso de prueba
        # result = await service.create(CreateRequest(
        #     name="Test Resource",
        #     description="Test description"
        # ))

        # print(f"Success: Resource created with ID: {result.id}")

        print("Test not implemented yet")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        print(traceback.format_exc())

    print("=" * 60)


async def main():
    """Main entry point."""

    setup_logging()

    print("\nStarting debugging...")

    await test_create_resource()

    print("\nDebugging completed!")


if __name__ == "__main__":
    asyncio.run(main())
```

## Convenciones de Codigo

### Python

```python
# Imports ordenados
# 1. Standard library
import os
from datetime import datetime

# 2. Third party
from fastapi import APIRouter
from sqlalchemy import Column

# 3. Local
from app.core.config import settings
from app.utils.logger import get_logger

# Nombres de variables y funciones: snake_case
user_name = "John"
def get_user_by_id(user_id: str): pass

# Nombres de clases: PascalCase
class UserService: pass
class UserResponse: pass

# Constantes: UPPER_CASE
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# Type hints siempre
def create_user(name: str, email: str) -> User: pass

# Docstrings en todas las funciones publicas
def login(email: str, password: str) -> AuthResponse:
    """
    Autenticar usuario.

    Args:
        email: Email del usuario
        password: Password en texto plano

    Returns:
        AuthResponse: Tokens de autenticacion

    Raises:
        ValueError: Si credenciales invalidas
    """
    pass
```

### Logging

```python
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Niveles de log
logger.debug("Informacion de debugging")
logger.info("Informacion general")
logger.warning("Advertencia")
logger.error("Error")
logger.critical("Error critico")

# Log con contexto
logger.info(f"User logged in: {user.email}")
logger.error(f"Failed to create resource: {error}")

# Log de excepciones
try:
    # codigo
    pass
except Exception as exc:
    logger.error(f"Unexpected error: {exc}", exc_info=True)
```

### Manejo de Errores

```python
# En service.py - Usar excepciones de Python
def get_by_id(self, user_id: str) -> User:
    user = self.db.query(User).filter(User.id == user_id).first()

    if not user:
        raise ValueError(f"User not found: {user_id}")

    return user


# En router.py - Convertir a HTTPException
@router.get("/{user_id}")
async def get_user(user_id: str, service: UserService = Depends()):
    try:
        return await service.get_by_id(user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc)
        )
```

## Comandos Utiles

### Development

```bash
# Ejecutar backend con auto-reload
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Ejecutar frontend
cd frontend
npm run dev

# Ver logs en tiempo real
tail -f backend/logs/app.log

# Buscar en logs
grep "ERROR" backend/logs/app.log
grep "user_123" backend/logs/app.log
```

### Database

```bash
# Crear migracion
cd backend
alembic revision --autogenerate -m "Add new table"

# Ejecutar migraciones
alembic upgrade head

# Revertir ultima migracion
alembic downgrade -1

# Ver historial de migraciones
alembic history
```

### Testing

```bash
# Todos los tests
pytest backend/testing/

# Tests con output verbose
pytest backend/testing/ -v

# Test especifico
pytest backend/testing/test_auth.py::TestAuthLogin::test_login_success

# Con coverage
pytest backend/testing/ --cov=backend/app --cov-report=html

# Solo tests marcados (si usas markers)
pytest backend/testing/ -m "integration"
```

### Code Quality

```bash
# Formatear codigo con black
black backend/app/

# Lint con ruff
ruff check backend/app/

# Type checking con mypy
mypy backend/app/
```

## Checklist para Nuevo Modulo

- [ ] Crear directorio del modulo
- [ ] Definir schemas.py con Pydantic
- [ ] Definir models.py con SQLAlchemy
- [ ] Implementar service.py con logica de negocio
- [ ] Implementar router.py con endpoints REST
- [ ] Crear __init__.py exportando interfaces
- [ ] Registrar router en main.py
- [ ] Crear test_modulo.py con tests unitarios
- [ ] Crear debug_modulo.py con scripts de debugging
- [ ] Ejecutar tests y verificar que pasan
- [ ] Actualizar documentacion si es necesario

## Troubleshooting

### Error: Module not found

```bash
# Verificar que virtual environment esta activado
which python  # Debe mostrar path de venv

# Reinstalar dependencias
pip install -r requirements.txt
```

### Error: Database connection failed

```bash
# Verificar que PostgreSQL esta corriendo
sudo systemctl status postgresql

# Verificar credenciales en .env
cat .env | grep DATABASE_URL
```

### Error: Tests failing

```bash
# Limpiar cache de pytest
pytest --cache-clear

# Recrear base de datos de test
rm backend/testing/test.db
pytest backend/testing/
```

### Error: Import circular

- Revisar imports en __init__.py
- Evitar importar entre modulos del mismo nivel
- Usar imports relativos cuando sea necesario

## Recursos Adicionales

- FastAPI Docs: https://fastapi.tiangolo.com/
- SQLAlchemy Docs: https://docs.sqlalchemy.org/
- Pydantic Docs: https://docs.pydantic.dev/
- Pytest Docs: https://docs.pytest.org/
