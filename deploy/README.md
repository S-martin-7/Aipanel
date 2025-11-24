# AIPanel - Deployment Guide (Debian/Ubuntu VPS)

## Requisitos del Servidor

- **OS**: Debian 11/12 o Ubuntu 20.04/22.04
- **RAM**: Mínimo 2GB (recomendado 4GB)
- **CPU**: 2 cores mínimo
- **Disco**: 20GB mínimo

## Quick Start

### 1. Copiar archivos al servidor

```bash
# Desde tu PC local
scp -r Aipanel root@tu-servidor:/opt/

# O clonar desde git
ssh root@tu-servidor
cd /opt
git clone <tu-repo> aipanel
```

### 2. Ejecutar instalación

```bash
cd /opt/aipanel
chmod +x deploy/*.sh
sudo ./deploy/install.sh

# Con dominio y SSL
sudo ./deploy/install.sh -d tudominio.com
```

### 3. Configurar .env

```bash
# Editar configuración
sudo nano /opt/aipanel/backend/.env

# Generar claves seguras
openssl rand -hex 32  # Para JWT_SECRET
openssl rand -hex 32  # Para JWT_REFRESH_SECRET
```

### 4. Reiniciar servicio

```bash
sudo systemctl restart aipanel
```

## Scripts Disponibles

| Script | Uso | Descripción |
|--------|-----|-------------|
| `install.sh` | `sudo ./deploy/install.sh` | Instalación completa |
| `update.sh` | `sudo ./deploy/update.sh` | Actualizar código y dependencias |
| `manage.sh` | `sudo ./deploy/manage.sh [cmd]` | Gestión del servicio |

### Comandos de manage.sh

```bash
sudo ./deploy/manage.sh status      # Ver estado
sudo ./deploy/manage.sh restart     # Reiniciar
sudo ./deploy/manage.sh logs        # Ver logs en vivo
sudo ./deploy/manage.sh errors      # Ver errores
sudo ./deploy/manage.sh migrate     # Correr migraciones
sudo ./deploy/manage.sh backup-db   # Backup de base de datos
sudo ./deploy/manage.sh restore-db  # Restaurar backup
```

## Comandos Útiles

```bash
# Estado del servicio
sudo systemctl status aipanel

# Reiniciar
sudo systemctl restart aipanel

# Ver logs
sudo journalctl -u aipanel -f

# Logs de error
sudo tail -f /opt/aipanel/backend/logs/error.log

# Nginx logs
sudo tail -f /var/log/nginx/aipanel_error.log
```

## Estructura en el Servidor

```
/opt/aipanel/
├── backend/
│   ├── app/
│   ├── alembic/
│   ├── venv/
│   ├── logs/
│   │   ├── access.log
│   │   └── error.log
│   ├── .env
│   └── requirements.txt
├── deploy/
│   ├── install.sh
│   ├── update.sh
│   └── manage.sh
└── backups/
    └── aipanel_YYYYMMDD_HHMMSS.sql.gz
```

## Configuración de Firewall

El script configura UFW automáticamente:

```bash
# Puertos abiertos
- 22 (SSH)
- 80 (HTTP)
- 443 (HTTPS)

# Verificar
sudo ufw status
```

## SSL con Let's Encrypt

```bash
# Instalación automática (si pasaste dominio)
sudo ./deploy/install.sh -d tudominio.com

# Instalación manual
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d tudominio.com

# Renovar certificados
sudo certbot renew

# Auto-renovación (ya configurado por certbot)
sudo systemctl status certbot.timer
```

## Base de Datos

```bash
# Acceder a PostgreSQL
sudo -u postgres psql aipanel

# Backup manual
sudo -u postgres pg_dump aipanel > backup.sql

# Restaurar
sudo -u postgres psql aipanel < backup.sql
```

## Solución de Problemas

### El servicio no inicia

```bash
# Ver logs detallados
sudo journalctl -u aipanel -n 100 --no-pager

# Verificar configuración
sudo -u aipanel bash -c "
    cd /opt/aipanel/backend
    source venv/bin/activate
    python -c 'from app.main import app; print(\"OK\")'
"
```

### Error de conexión a PostgreSQL

```bash
# Verificar que PostgreSQL está corriendo
sudo systemctl status postgresql

# Verificar usuario y base de datos
sudo -u postgres psql -c "\du"
sudo -u postgres psql -c "\l"
```

### Error de conexión a Redis

```bash
# Verificar que Redis está corriendo
sudo systemctl status redis-server
redis-cli ping
```

### Nginx 502 Bad Gateway

```bash
# Verificar que el backend está corriendo
curl http://127.0.0.1:8000/health

# Si no responde, revisar logs del backend
sudo journalctl -u aipanel -n 50
```

## Actualización de Producción

```bash
# Opción 1: Script automático
sudo ./deploy/update.sh

# Opción 2: Manual
cd /opt/aipanel
sudo -u aipanel git pull
cd backend
sudo -u aipanel bash -c "source venv/bin/activate && pip install -r requirements.txt"
sudo -u aipanel bash -c "source venv/bin/activate && alembic upgrade head"
sudo systemctl restart aipanel
```

## Monitoreo

### Health Check

```bash
curl http://localhost/health
```

### Métricas Prometheus

```bash
curl http://localhost/metrics
```

## Seguridad

1. **Cambiar contraseñas por defecto** en `.env`
2. **Configurar CORS** correctamente
3. **Usar HTTPS** en producción
4. **Mantener actualizado** el sistema
5. **Backup regular** de la base de datos

```bash
# Cron para backups diarios
echo "0 3 * * * root /opt/aipanel/deploy/manage.sh backup-db" | sudo tee /etc/cron.d/aipanel-backup
```
