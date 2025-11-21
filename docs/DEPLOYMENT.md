# Guía de Deployment - AIPanel en VPS (Sin Docker)

Esta guía te ayudará a desplegar AIPanel directamente en tu VPS sin usar Docker, optimizando el uso de recursos.

## [-] Prerrequisitos

- VPS con Ubuntu 20.04+ o Debian 11+
- Mínimo 2GB RAM, 2 vCPUs
- Acceso root o sudo
- Dominio apuntando a tu VPS
- Puertos disponibles (ej: 3000, 4000)

## [+] Ventajas de No Usar Docker

- [OK] Menor uso de RAM (~200-300MB menos)
- [OK] Menor uso de CPU (sin overhead de contenedores)
- [OK] Más simple para debugging
- [OK] Perfecto para 2-3 apps por servidor
- [OK] Acceso directo a logs y procesos

## [*] Instalación Rápida

### Paso 1: Clonar el Repositorio

```bash
# Ir al directorio de aplicaciones
cd /var/www  # o donde prefieras

# Clonar el repositorio
git clone <tu-repositorio-url> aipanel
cd aipanel
```

### Paso 2: Ejecutar Script de Instalación

```bash
# Este script instalará:
# - Node.js 20
# - PostgreSQL 15
# - Redis
# - Nginx
# - PM2
# - Dependencias del proyecto

bash install.sh
```

El script te preguntará si deseas cargar datos de prueba. Responde según necesites.

### Paso 3: Configurar API Keys

```bash
# Editar el archivo .env
nano .env
```

Configura las siguientes variables:

```env
# APIs de AI
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx

# Pagos (Stripe)
STRIPE_SECRET_KEY=sk_live_xxxxxxxxxxxxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx

# Storage (AWS S3 o compatible)
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxx
AWS_S3_BUCKET=aipanel-storage

# Email (SendGrid o similar)
SENDGRID_API_KEY=SG.xxxxxxxxxxxxx

# Dominios públicos
FRONTEND_URL=https://aipanel.tudominio.com
NEXT_PUBLIC_API_URL=https://api.aipanel.tudominio.com
```

### Paso 4: Construir y Desplegar

```bash
# Este script:
# - Instala dependencias
# - Ejecuta migraciones
# - Construye las apps
# - Inicia con PM2

bash deploy.sh
```

## [?] Configuración de Puertos

Si ya tienes otras aplicaciones corriendo, cambia los puertos en `.env`:

```env
# Estos son los puertos por defecto, cámbialos si están en uso
BACKEND_PORT=4000
FRONTEND_PORT=3000
POSTGRES_PORT=5432
REDIS_PORT=6379
```

## [T] Configurar Nginx

### 1. Copiar Configuración

```bash
sudo cp nginx.conf /etc/nginx/sites-available/aipanel
```

### 2. Editar Dominios y Puertos

```bash
sudo nano /etc/nginx/sites-available/aipanel
```

Busca y reemplaza:
- `aipanel.tudominio.com` → tu dominio
- `api.aipanel.tudominio.com` → tu subdominio de API
- `localhost:4000` → tu BACKEND_PORT si es diferente
- `localhost:3000` → tu FRONTEND_PORT si es diferente

### 3. Habilitar Sitio

```bash
# Crear symlink
sudo ln -s /etc/nginx/sites-available/aipanel /etc/nginx/sites-enabled/

# Verificar configuración
sudo nginx -t

# Recargar Nginx
sudo systemctl reload nginx
```

## [?] SSL con Let's Encrypt

```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx

# Obtener certificados
sudo certbot --nginx -d aipanel.tudominio.com -d api.aipanel.tudominio.com

# Verificar auto-renovación
sudo certbot renew --dry-run
```

## [?] Configurar DNS

En tu proveedor de DNS:

```
Tipo A:
aipanel.tudominio.com       →  IP_DE_TU_VPS
api.aipanel.tudominio.com   →  IP_DE_TU_VPS
```

## [=] Gestión con PM2

### Ver Procesos

```bash
# Lista de procesos
pm2 list

# Monitor en tiempo real
pm2 monit

# Logs en tiempo real
pm2 logs

# Logs de un proceso específico
pm2 logs aipanel-backend
pm2 logs aipanel-frontend
```

### Controlar Procesos

```bash
# Reiniciar todo
pm2 restart all

# Reiniciar solo backend
pm2 restart aipanel-backend

# Detener todo
pm2 stop all

# Iniciar todo
pm2 start ecosystem.config.js

# Guardar configuración actual
pm2 save
```

### Ver Métricas

```bash
# Uso de CPU y memoria
pm2 monit

# Estadísticas
pm2 describe aipanel-backend
```

## [?] Actualizaciones

```bash
cd /var/www/aipanel

# Pull de cambios
git pull origin main

# Re-deployar
bash deploy.sh
```

## [?] Base de Datos

### Acceder a PostgreSQL

```bash
# Como usuario postgres
sudo -u postgres psql

# Conectar a la base de datos
\c aipanel

# Ver tablas
\dt

# Salir
\q
```

### Ejecutar Migraciones Manualmente

```bash
cd /var/www/aipanel/backend
npx prisma migrate deploy
```

### Backup de Base de Datos

```bash
# Crear backup
sudo -u postgres pg_dump aipanel > backup_$(date +%Y%m%d).sql

# Restaurar backup
sudo -u postgres psql aipanel < backup_20250101.sql
```

### Limpiar y Recrear Base de Datos

```bash
cd backend

# CUIDADO: Esto borra todos los datos
npx prisma migrate reset

# Crear nuevamente las tablas
npx prisma migrate deploy

# Cargar datos de prueba
npx prisma db seed
```

## [?] Estructura de Logs

Los logs se guardan en:

```
/var/www/aipanel/logs/
├── backend-error.log
├── backend-out.log
├── frontend-error.log
├── frontend-out.log
├── worker-error.log
└── worker-out.log
```

Ver logs:

```bash
# Logs del backend
tail -f logs/backend-out.log

# Logs de errores
tail -f logs/backend-error.log

# Con PM2
pm2 logs
```

## [!] Firewall

```bash
# Permitir HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# SSH (si no está)
sudo ufw allow 22/tcp

# Habilitar firewall
sudo ufw enable

# Ver estado
sudo ufw status
```

**NOTA**: No expongas los puertos de las apps (3000, 4000) directamente. Nginx hace de reverse proxy.

## [?] Uso de Recursos

### Monitorear Sistema

```bash
# Uso general
htop

# Memoria
free -h

# Disco
df -h

# Procesos de Node
ps aux | grep node

# Tráfico de red
iftop
```

### Límites Recomendados por Servidor

Para un VPS con 2GB RAM:

- **Backend**: ~500MB RAM, 1-2 instancias PM2
- **Frontend**: ~400MB RAM, 1 instancia
- **PostgreSQL**: ~256MB RAM
- **Redis**: ~100MB RAM
- **Nginx**: ~50MB RAM

**Total**: ~1.3-1.5GB RAM (deja ~500MB libre para el sistema)

## 🆘 Troubleshooting

### Error: Puerto ya en uso

```bash
# Ver qué proceso usa el puerto
sudo lsof -i :4000

# Matar proceso
sudo kill -9 <PID>

# O cambiar puerto en .env
```

### Error: No se puede conectar a PostgreSQL

```bash
# Verificar que esté corriendo
sudo systemctl status postgresql

# Reiniciar
sudo systemctl restart postgresql

# Ver logs
sudo tail -f /var/log/postgresql/postgresql-15-main.log
```

### Error: PM2 no inicia las apps

```bash
# Ver logs detallados
pm2 logs --lines 100

# Reiniciar PM2
pm2 kill
pm2 start ecosystem.config.js
pm2 save
```

### Error: 502 Bad Gateway

```bash
# Verificar que las apps estén corriendo
pm2 list

# Verificar puertos en Nginx
grep "server localhost" /etc/nginx/sites-available/aipanel

# Comparar con .env
grep PORT .env

# Reiniciar Nginx
sudo systemctl restart nginx
```

### Error: Memoria insuficiente

```bash
# Ver uso de memoria
free -h

# Reducir instancias de PM2
# Edita ecosystem.config.js
nano ecosystem.config.js

# Cambia "instances: 2" a "instances: 1"
# Luego:
pm2 reload ecosystem.config.js
```

### Limpiar Memoria

```bash
# Limpiar cache de npm
npm cache clean --force

# Limpiar logs antiguos de PM2
pm2 flush

# Limpiar logs del sistema
sudo journalctl --vacuum-time=7d
```

## [?] Seguridad Adicional

### 1. Crear Usuario Específico

```bash
# Crear usuario para la app
sudo useradd -m -s /bin/bash aipanel

# Cambiar dueño de archivos
sudo chown -R aipanel:aipanel /var/www/aipanel

# Ejecutar PM2 como ese usuario
sudo -u aipanel pm2 start ecosystem.config.js
```

### 2. Fail2ban

```bash
sudo apt install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 3. Actualizar Sistema

```bash
sudo apt update && sudo apt upgrade -y
```

## [?] Variables de Entorno Importantes

```env
# Producción vs Desarrollo
NODE_ENV=production

# Puertos
BACKEND_PORT=4000
FRONTEND_PORT=3000

# URLs públicas (para CORS)
FRONTEND_URL=https://aipanel.tudominio.com
NEXT_PUBLIC_API_URL=https://api.aipanel.tudominio.com

# Rate limiting
RATE_LIMIT_TTL=60
RATE_LIMIT_MAX=100

# Suspensión automática
GRACE_PERIOD_DAYS=14
PAYMENT_REMINDER_DAYS=7,10,13
```

## [?] Comandos Rápidos de Referencia

```bash
# Ver estado de todo
pm2 status

# Reiniciar backend
pm2 restart aipanel-backend

# Ver logs en vivo
pm2 logs --lines 50

# Monitor de recursos
pm2 monit

# Guardar configuración
pm2 save

# Detener todo
pm2 stop all

# Iniciar todo
pm2 start all

# Eliminar todos los procesos
pm2 delete all

# Deployment completo
bash deploy.sh
```

---

**¡Listo!** Tu AIPanel está corriendo de forma nativa sin Docker, optimizando recursos del servidor.

**URLs:**
- Frontend: https://aipanel.tudominio.com
- Backend API: https://api.aipanel.tudominio.com
- API Docs: https://api.aipanel.tudominio.com/api/docs
