#!/bin/bash

# Script de deployment para AIPanel (sin Docker)
# Ejecutar con: bash deploy.sh

set -e

echo "================================================"
echo "  AIPanel - Deployment Script"
echo "================================================"
echo ""

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Verificar directorio
if [ ! -f "ecosystem.config.js" ]; then
    echo -e "${RED}Error: ecosystem.config.js no encontrado${NC}"
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
echo "==> Paso 2: Instalando dependencias actualizadas"

# Backend
if [ -d "backend" ]; then
    echo "Actualizando backend..."
    cd backend
    npm install
    cd ..
fi

# Frontend
if [ -d "frontend" ]; then
    echo "Actualizando frontend..."
    cd frontend
    npm install
    cd ..
fi

echo ""
echo "==> Paso 3: Ejecutando migraciones de base de datos"
cd backend
npx prisma migrate deploy
npx prisma generate
cd ..

echo ""
echo "==> Paso 4: Construyendo aplicaciones"

# Build backend
if [ -d "backend" ]; then
    echo "Construyendo backend..."
    cd backend
    npm run build
    cd ..
fi

# Build frontend
if [ -d "frontend" ]; then
    echo "Construyendo frontend..."
    cd frontend
    npm run build
    cd ..
fi

echo ""
echo "==> Paso 5: Reiniciando aplicaciones con PM2"

# Verificar si PM2 está corriendo
if pm2 list | grep -q "aipanel"; then
    echo "Reloading aplicaciones existentes..."
    pm2 reload ecosystem.config.js
else
    echo "Iniciando aplicaciones por primera vez..."
    pm2 start ecosystem.config.js
fi

# Guardar lista de procesos PM2
pm2 save

# Mostrar estado
pm2 list

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  Deployment completado!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Comandos útiles:"
echo "  pm2 list              - Ver procesos corriendo"
echo "  pm2 logs              - Ver logs en tiempo real"
echo "  pm2 monit             - Monitor interactivo"
echo "  pm2 restart all       - Reiniciar todos los procesos"
echo "  pm2 stop all          - Detener todos los procesos"
echo ""
echo "Logs ubicados en:"
echo "  ./logs/backend-error.log"
echo "  ./logs/frontend-error.log"
echo ""
