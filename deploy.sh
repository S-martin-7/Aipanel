#!/bin/bash

# Script de deployment para AIPanel (Python Backend + Next.js Frontend)
# Ejecutar con: bash deploy.sh

set -e

echo "================================================"
echo "  AIPanel - Deployment Script"
echo "  Backend: Python 3.11 + FastAPI"
echo "  Frontend: Next.js"
echo "================================================"
echo ""

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Verificar directorio
if [ ! -d "backend" ] && [ ! -d "frontend" ]; then
    echo -e "${RED}Error: Ejecuta este script desde el directorio raíz del proyecto${NC}"
    exit 1
fi

# Verificar .env
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: archivo .env no encontrado${NC}"
    echo "Ejecuta primero: bash install.sh"
    exit 1
fi

echo "==> Paso 1: Pull de últimos cambios (si es un repo git)"
if [ -d ".git" ]; then
    git pull origin main || echo "No es un repo git o no hay cambios"
fi

echo ""
echo "==> Paso 2: Actualizando Backend (Python)"

if [ -d "backend" ]; then
    echo "Actualizando dependencias de Python..."
    cd backend

    # Activar virtual environment
    source venv/bin/activate

    # Actualizar dependencias
    pip install --upgrade pip
    pip install -r requirements.txt

    cd ..
    echo -e "${GREEN}✓ Backend actualizado${NC}"
fi

echo ""
echo "==> Paso 3: Ejecutando migraciones de base de datos"
cd backend
source venv/bin/activate

echo "Aplicando migraciones..."
alembic upgrade head

deactivate
cd ..

echo ""
echo "==> Paso 4: Actualizando Frontend (Next.js)"

if [ -d "frontend" ]; then
    echo "Actualizando frontend..."
    cd frontend

    # Actualizar dependencias
    npm install

    # Build para producción
    echo "Construyendo frontend..."
    npm run build

    cd ..
    echo -e "${GREEN}✓ Frontend construido${NC}"
fi

echo ""
echo "==> Paso 5: Instalando servicios systemd"

# Copiar archivos de servicio
if [ -d "deploy" ]; then
    echo "Instalando servicios systemd..."

    sudo cp deploy/aipanel-api.service /etc/systemd/system/
    sudo cp deploy/aipanel-worker.service /etc/systemd/system/
    sudo cp deploy/aipanel-beat.service /etc/systemd/system/
    sudo cp deploy/aipanel-frontend.service /etc/systemd/system/

    # Reload systemd
    sudo systemctl daemon-reload

    echo -e "${GREEN}✓ Servicios systemd instalados${NC}"
fi

echo ""
echo "==> Paso 6: Reiniciando servicios"

# Detener servicios si están corriendo
sudo systemctl stop aipanel-api || true
sudo systemctl stop aipanel-worker || true
sudo systemctl stop aipanel-beat || true
sudo systemctl stop aipanel-frontend || true

# Iniciar servicios
echo "Iniciando servicios..."
sudo systemctl start aipanel-api
sudo systemctl start aipanel-worker
sudo systemctl start aipanel-beat
sudo systemctl start aipanel-frontend

# Habilitar para inicio automático
sudo systemctl enable aipanel-api
sudo systemctl enable aipanel-worker
sudo systemctl enable aipanel-beat
sudo systemctl enable aipanel-frontend

# Esperar un momento
sleep 3

# Verificar estado
echo ""
echo "==> Verificando estado de los servicios"
echo ""

sudo systemctl status aipanel-api --no-pager || echo -e "${RED}API no está corriendo${NC}"
sudo systemctl status aipanel-worker --no-pager || echo -e "${RED}Worker no está corriendo${NC}"
sudo systemctl status aipanel-beat --no-pager || echo -e "${RED}Beat no está corriendo${NC}"
sudo systemctl status aipanel-frontend --no-pager || echo -e "${RED}Frontend no está corriendo${NC}"

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  Deployment completado!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Servicios corriendo:"
echo "  - API Backend (Python/FastAPI): http://localhost:8000"
echo "  - Frontend (Next.js): http://localhost:3000"
echo "  - Celery Worker: activo"
echo "  - Celery Beat: activo"
echo ""
echo "Comandos útiles:"
echo ""
echo "  # Ver logs de la API"
echo "  sudo journalctl -u aipanel-api -f"
echo ""
echo "  # Ver logs del worker"
echo "  sudo journalctl -u aipanel-worker -f"
echo ""
echo "  # Ver logs del frontend"
echo "  sudo journalctl -u aipanel-frontend -f"
echo ""
echo "  # Reiniciar servicio"
echo "  sudo systemctl restart aipanel-api"
echo ""
echo "  # Ver estado de todos los servicios"
echo "  sudo systemctl status 'aipanel-*'"
echo ""
echo "  # Detener todo"
echo "  sudo systemctl stop 'aipanel-*'"
echo ""
echo "Logs ubicados en:"
echo "  /var/log/aipanel/api-access.log"
echo "  /var/log/aipanel/api-error.log"
echo "  /var/log/aipanel/celery-worker.log"
echo "  /var/log/aipanel/celery-beat.log"
echo ""
echo -e "${YELLOW}IMPORTANTE:${NC}"
echo "  1. Configura Nginx usando el archivo nginx.conf"
echo "  2. Obtén certificados SSL con Let's Encrypt"
echo "  3. Verifica que el firewall permita los puertos 80 y 443"
echo ""
