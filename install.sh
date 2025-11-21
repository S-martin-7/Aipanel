#!/bin/bash

# Script de instalación de AIPanel (Python Backend + Next.js Frontend)
# Ejecutar con: bash install.sh

set -e

echo "================================================"
echo "  AIPanel - Instalación en VPS"
echo "  Backend: Python 3.11 + FastAPI"
echo "  Frontend: Next.js"
echo "================================================"
echo ""

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Verificar que estamos en el directorio correcto
if [ ! -d "backend" ] && [ ! -d "frontend" ]; then
    echo -e "${RED}Error: Ejecuta este script desde el directorio raíz del proyecto${NC}"
    exit 1
fi

# Verificar usuario root
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLOW}Advertencia: Ejecutando como root${NC}"
    echo "Se recomienda crear un usuario específico para la aplicación"
    read -p "¿Deseas crear un usuario 'aipanel'? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo useradd -m -s /bin/bash aipanel
        echo -e "${GREEN}Usuario 'aipanel' creado${NC}"
    fi
fi

echo "==> Paso 1: Instalando dependencias del sistema"
echo ""

# Actualizar repositorios
sudo apt update

# Instalar Python 3.11 si no está instalado
if ! command -v python3.11 &> /dev/null; then
    echo "Instalando Python 3.11..."
    sudo apt install -y software-properties-common
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt update
    sudo apt install -y python3.11 python3.11-venv python3.11-dev
else
    PYTHON_VERSION=$(python3.11 --version)
    echo "Python 3.11 ya instalado: $PYTHON_VERSION"
fi

# Instalar pip
if ! python3.11 -m pip --version &> /dev/null; then
    echo "Instalando pip para Python 3.11..."
    curl -sS https://bootstrap.pypa.io/get-pip.py | sudo python3.11
fi

# Instalar Node.js 20.x (solo para el frontend)
if ! command -v node &> /dev/null; then
    echo "Instalando Node.js 20.x (para el frontend)..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt install -y nodejs
else
    NODE_VERSION=$(node -v)
    echo "Node.js ya instalado: $NODE_VERSION"
fi

# Instalar PostgreSQL si no está instalado
if ! command -v psql &> /dev/null; then
    echo "Instalando PostgreSQL 15..."
    sudo apt install -y postgresql postgresql-contrib
    sudo systemctl enable postgresql
    sudo systemctl start postgresql
else
    echo "PostgreSQL ya instalado"
fi

# Instalar Redis si no está instalado
if ! command -v redis-cli &> /dev/null; then
    echo "Instalando Redis..."
    sudo apt install -y redis-server
    sudo systemctl enable redis-server
    sudo systemctl start redis-server
else
    echo "Redis ya instalado"
fi

# Instalar Nginx si no está instalado
if ! command -v nginx &> /dev/null; then
    echo "Instalando Nginx..."
    sudo apt install -y nginx
    sudo systemctl enable nginx
    sudo systemctl start nginx
else
    echo "Nginx ya instalado"
fi

# Instalar herramientas de compilación (necesarias para algunas deps de Python)
echo "Instalando herramientas de compilación..."
sudo apt install -y build-essential libpq-dev

echo ""
echo "==> Paso 2: Configurando base de datos PostgreSQL"
echo ""

# Verificar si existe .env
if [ ! -f ".env" ]; then
    echo "Creando .env desde .env.example..."
    cp .env.example .env

    # Generar contraseñas aleatorias
    POSTGRES_PASS=$(openssl rand -base64 32)
    REDIS_PASS=$(openssl rand -base64 32)
    JWT_SECRET=$(openssl rand -base64 32)
    JWT_REFRESH=$(openssl rand -base64 32)

    # Actualizar .env con contraseñas generadas
    sed -i "s/change_this_password_in_production/$POSTGRES_PASS/g" .env
    sed -i "s/change_this_redis_password/$REDIS_PASS/g" .env
    sed -i "s/change_this_jwt_secret_key/$JWT_SECRET/g" .env
    sed -i "s/change_this_refresh_secret_key/$JWT_REFRESH/g" .env

    echo -e "${GREEN}✓ Archivo .env creado con contraseñas seguras${NC}"
    echo -e "${YELLOW}IMPORTANTE: Edita .env y configura tus API keys${NC}"
fi

# Leer variables de .env
source .env

# Crear base de datos y usuario en PostgreSQL
echo "Configurando base de datos PostgreSQL..."
sudo -u postgres psql -c "CREATE USER ${POSTGRES_USER} WITH PASSWORD '${POSTGRES_PASSWORD}';" 2>/dev/null || echo "Usuario ya existe"
sudo -u postgres psql -c "CREATE DATABASE ${POSTGRES_DB} OWNER ${POSTGRES_USER};" 2>/dev/null || echo "Base de datos ya existe"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${POSTGRES_DB} TO ${POSTGRES_USER};"

echo -e "${GREEN}✓ Base de datos configurada${NC}"

echo ""
echo "==> Paso 3: Configurando Redis"
echo ""

# Configurar contraseña de Redis
if [ ! -z "$REDIS_PASSWORD" ]; then
    sudo sed -i "s/# requirepass foobared/requirepass ${REDIS_PASSWORD}/g" /etc/redis/redis.conf
    sudo systemctl restart redis-server
    echo -e "${GREEN}✓ Redis configurado con contraseña${NC}"
fi

echo ""
echo "==> Paso 4: Configurando Backend (Python)"
echo ""

# Crear directorio de logs
sudo mkdir -p /var/log/aipanel
sudo mkdir -p /var/run/aipanel
sudo chown -R $(whoami):$(whoami) /var/log/aipanel /var/run/aipanel

# Instalar dependencias del backend
if [ -d "backend" ]; then
    echo "Configurando virtual environment para Python..."
    cd backend

    # Crear virtual environment
    python3.11 -m venv venv

    # Activar virtual environment
    source venv/bin/activate

    # Upgrade pip
    pip install --upgrade pip

    # Instalar dependencias
    echo "Instalando dependencias de Python..."
    pip install -r requirements.txt

    # Copiar .env al backend
    cp ../.env .env

    deactivate
    cd ..

    echo -e "${GREEN}✓ Backend Python configurado${NC}"
fi

echo ""
echo "==> Paso 5: Configurando Frontend (Next.js)"
echo ""

# Instalar dependencias del frontend
if [ -d "frontend" ]; then
    echo "Instalando dependencias del frontend..."
    cd frontend
    npm install
    cd ..
    echo -e "${GREEN}✓ Frontend instalado${NC}"
fi

echo ""
echo "==> Paso 6: Ejecutando migraciones de base de datos"
echo ""

cd backend
source venv/bin/activate

# Inicializar Alembic si es necesario
if [ ! -f "alembic.ini" ]; then
    echo "Inicializando Alembic..."
    alembic init alembic
fi

# Ejecutar migraciones
echo "Ejecutando migraciones..."
alembic upgrade head

deactivate
cd ..

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  Instalación completada!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Próximos pasos:"
echo ""
echo "1. Edita el archivo .env y configura:"
echo "   - OPENAI_API_KEY"
echo "   - ANTHROPIC_API_KEY"
echo "   - STRIPE_SECRET_KEY"
echo "   - AWS credentials"
echo "   - Dominios (FRONTEND_URL, NEXT_PUBLIC_API_URL)"
echo ""
echo "2. Ejecutar el script de deployment:"
echo "   bash deploy.sh"
echo ""
echo "3. Los servicios se gestionan con systemd:"
echo "   sudo systemctl status aipanel-api"
echo "   sudo systemctl status aipanel-worker"
echo "   sudo systemctl status aipanel-frontend"
echo ""
echo "4. Configurar Nginx (ver docs/DEPLOYMENT.md)"
echo ""
echo "5. Obtener certificados SSL con Let's Encrypt"
echo ""
