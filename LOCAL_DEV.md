# AIPanel - Guía de Desarrollo Local

## Requisitos Previos

- **Python 3.10+** ([descargar](https://www.python.org/downloads/))
- **Docker Desktop** ([descargar](https://www.docker.com/products/docker-desktop/))
- **Git** ([descargar](https://git-scm.com/downloads))

## Quick Start

### Windows (PowerShell)

```powershell
# 1. Clonar el repositorio
git clone <repo-url>
cd Aipanel

# 2. Iniciar servicios (PostgreSQL + Redis)
docker-compose up -d

# 3. Setup del backend
cd backend
.\scripts\dev.ps1 setup

# 4. Configurar variables de entorno
copy .env.example .env
# Editar .env con tus configuraciones

# 5. Correr migraciones
.\scripts\dev.ps1 migrate

# 6. Iniciar servidor
.\scripts\dev.ps1 run
```

### Windows (CMD)

```cmd
# 1. Clonar e ir al directorio
git clone <repo-url>
cd Aipanel

# 2. Iniciar servicios
docker-compose up -d

# 3. Setup
cd backend
scripts\dev.bat setup

# 4. Configurar .env
copy .env.example .env

# 5. Migraciones y servidor
scripts\dev.bat migrate
scripts\dev.bat run
```

### Linux / macOS

```bash
# 1. Clonar el repositorio
git clone <repo-url>
cd Aipanel

# 2. Iniciar servicios (PostgreSQL + Redis)
docker-compose up -d

# 3. Setup del backend
cd backend
./scripts/dev.sh setup

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus configuraciones

# 5. Correr migraciones
./scripts/dev.sh migrate

# 6. Iniciar servidor
./scripts/dev.sh run
```

### Con Makefile (Linux/macOS)

```bash
# Desde la raíz del proyecto
make services    # Iniciar PostgreSQL y Redis
make setup       # Instalar dependencias
make migrate     # Correr migraciones
make run         # Iniciar servidor

# O todo junto:
make dev
```

## URLs Disponibles

| Servicio | URL |
|----------|-----|
| API Backend | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/api/docs |
| Health Check | http://localhost:8000/health |
| pgAdmin (opcional) | http://localhost:5050 |
| Redis Commander (opcional) | http://localhost:8081 |

## Comandos Disponibles

### Scripts (Windows/Linux/macOS)

| Comando | Descripción |
|---------|-------------|
| `setup` | Crear venv e instalar dependencias |
| `run` | Iniciar servidor de desarrollo |
| `migrate` | Ejecutar migraciones de BD |
| `test` | Ejecutar tests |
| `help` | Mostrar ayuda |

### Makefile (Linux/macOS)

| Comando | Descripción |
|---------|-------------|
| `make help` | Ver todos los comandos |
| `make services` | Iniciar PostgreSQL y Redis |
| `make setup` | Instalar dependencias |
| `make run` | Servidor de desarrollo |
| `make dev` | Servicios + servidor |
| `make migrate` | Correr migraciones |
| `make test` | Ejecutar tests |
| `make lint` | Linter |
| `make clean` | Limpiar cache |

## Docker Compose

```bash
# Servicios básicos (PostgreSQL + Redis)
docker-compose up -d

# Con herramientas de admin
docker-compose --profile tools up -d

# Ver logs
docker-compose logs -f

# Detener todo
docker-compose down

# Detener y borrar volúmenes (reset completo)
docker-compose down -v
```

## Configuración de .env

Copia `.env.example` a `.env` y configura:

```env
# Requeridos
DATABASE_URL=postgresql+asyncpg://aipanel:aipanel_password@localhost:5432/aipanel
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=tu-clave-secreta-minimo-32-caracteres

# Opcionales (para funcionalidad completa)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

## Solución de Problemas

### "make: command not found" (Windows)

Windows no incluye `make` por defecto. Opciones:
1. Usar los scripts: `.\scripts\dev.ps1 setup`
2. Instalar Make con Chocolatey: `choco install make`
3. Usar Git Bash que incluye make

### "docker-compose: command not found"

Docker Desktop debe estar instalado y corriendo. Alternativamente:
```bash
docker compose up -d  # Sintaxis nueva (sin guión)
```

### Error de conexión a PostgreSQL

Verificar que Docker está corriendo:
```bash
docker ps  # Debe mostrar aipanel-postgres
```

### Error de permisos en scripts (Linux/macOS)

```bash
chmod +x backend/scripts/dev.sh
```

### Puerto 8000 ya en uso

Cambiar el puerto en `.env`:
```env
PORT=8001
```

O matar el proceso existente:
```bash
# Linux/macOS
lsof -ti:8000 | xargs kill

# Windows
netstat -ano | findstr :8000
taskkill /PID <pid> /F
```
