# Instalación en VPS (Debian/Ubuntu) - Guía Paso a Paso

## Método 1: Instalación Rápida (Recomendado)

### Paso 1: Conectar al servidor

```bash
ssh root@tu-servidor-ip
```

### Paso 2: Copiar el proyecto

**Opción A - Desde Git:**
```bash
cd /opt
git clone https://github.com/tu-usuario/Aipanel.git aipanel
cd aipanel
```

**Opción B - Desde tu PC (ejecutar en tu PC):**
```bash
# Comprimir proyecto
tar -czf aipanel.tar.gz Aipanel/

# Subir al servidor
scp aipanel.tar.gz root@tu-servidor:/opt/

# En el servidor, descomprimir
ssh root@tu-servidor
cd /opt
tar -xzf aipanel.tar.gz
mv Aipanel aipanel
cd aipanel
```

### Paso 3: Ejecutar instalación

```bash
# Dar permisos de ejecución
chmod +x deploy/*.sh

# Ejecutar instalación rápida
bash deploy/quick-install.sh
```

**Eso es todo!** El script instalará automáticamente:
- Python 3
- PostgreSQL
- Redis
- Nginx
- Systemd service
- Firewall

### Paso 4: Configurar variables de entorno

```bash
# Editar configuración
nano /opt/aipanel/backend/.env

# Cambiar estas líneas:
JWT_SECRET=resultado-de-openssl-rand-hex-32
JWT_REFRESH_SECRET=resultado-de-openssl-rand-hex-32
OPENAI_API_KEY=tu-api-key
CORS_ORIGINS=https://tudominio.com
```

Para generar claves seguras:
```bash
openssl rand -hex 32
```

### Paso 5: Reiniciar el servicio

```bash
systemctl restart aipanel
```

### Paso 6: Verificar que funciona

```bash
# Ver estado
systemctl status aipanel

# Ver logs
journalctl -u aipanel -f

# Probar API
curl http://localhost/health
```

---

## Método 2: Instalación Manual Paso a Paso

Si el script automático falla, sigue estos pasos:

### 1. Actualizar sistema

```bash
apt-get update
apt-get upgrade -y
```

### 2. Instalar dependencias

```bash
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    postgresql \
    postgresql-contrib \
    redis-server \
    nginx \
    git \
    curl
```

### 3. Configurar PostgreSQL

```bash
# Iniciar PostgreSQL
systemctl start postgresql
systemctl enable postgresql

# Crear base de datos
sudo -u postgres psql << EOF
CREATE USER aipanel WITH PASSWORD 'aipanel_password';
CREATE DATABASE aipanel OWNER aipanel;
GRANT ALL PRIVILEGES ON DATABASE aipanel TO aipanel;
\q
EOF
```

### 4. Configurar Redis

```bash
systemctl start redis-server
systemctl enable redis-server
```

### 5. Crear usuario de aplicación

```bash
useradd -r -m -s /bin/bash aipanel
```

### 6. Copiar archivos

```bash
mkdir -p /opt/aipanel
cp -r backend /opt/aipanel/
chown -R aipanel:aipanel /opt/aipanel
```

### 7. Configurar Python

```bash
cd /opt/aipanel/backend

# Como usuario aipanel
sudo -u aipanel bash << 'EOF'
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn uvicorn[standard]
EOF
```

### 8. Crear archivo .env

```bash
cat > /opt/aipanel/backend/.env << 'EOF'
ENVIRONMENT=production
DEBUG=false
PORT=8000
DATABASE_URL=postgresql+asyncpg://aipanel:aipanel_password@localhost:5432/aipanel
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=CAMBIAR-POR-CLAVE-SEGURA
JWT_REFRESH_SECRET=CAMBIAR-POR-OTRA-CLAVE-SEGURA
JWT_ALGORITHM=HS256
CORS_ORIGINS=http://localhost:3000
EOF

chown aipanel:aipanel /opt/aipanel/backend/.env
chmod 600 /opt/aipanel/backend/.env
```

### 9. Ejecutar migraciones

```bash
cd /opt/aipanel/backend
sudo -u aipanel bash << 'EOF'
source venv/bin/activate
alembic upgrade head
EOF
```

### 10. Crear servicio systemd

```bash
cat > /etc/systemd/system/aipanel.service << 'EOF'
[Unit]
Description=AIPanel Backend
After=network.target postgresql.service redis-server.service

[Service]
Type=exec
User=aipanel
Group=aipanel
WorkingDirectory=/opt/aipanel/backend
Environment="PATH=/opt/aipanel/backend/venv/bin"
EnvironmentFile=/opt/aipanel/backend/.env
ExecStart=/opt/aipanel/backend/venv/bin/gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable aipanel
systemctl start aipanel
```

### 11. Configurar Nginx

```bash
cat > /etc/nginx/sites-available/aipanel << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF

ln -sf /etc/nginx/sites-available/aipanel /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
```

### 12. Configurar firewall

```bash
ufw allow ssh
ufw allow http
ufw allow https
ufw --force enable
```

---

## Comandos Útiles Post-Instalación

### Ver estado del servicio
```bash
systemctl status aipanel
```

### Ver logs en tiempo real
```bash
journalctl -u aipanel -f
```

### Reiniciar servicio
```bash
systemctl restart aipanel
```

### Probar API
```bash
curl http://localhost/health
curl http://tu-ip/api/docs
```

### Backup de base de datos
```bash
sudo -u postgres pg_dump aipanel > backup_$(date +%Y%m%d).sql
```

### Ver logs de Nginx
```bash
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

---

## Solución de Problemas

### Error: "permission denied" al ejecutar script
```bash
chmod +x deploy/quick-install.sh
bash deploy/quick-install.sh
```

### Error: servicio no inicia
```bash
# Ver logs detallados
journalctl -u aipanel -n 100 --no-pager

# Probar manualmente
cd /opt/aipanel/backend
sudo -u aipanel bash
source venv/bin/activate
python -c "from app.main import app; print('OK')"
```

### Error: no se puede conectar a PostgreSQL
```bash
# Verificar que está corriendo
systemctl status postgresql

# Verificar conexión
sudo -u postgres psql -c "\l"
```

### Error: puerto 80 en uso
```bash
# Ver qué está usando el puerto
lsof -i :80

# Detener Apache si está instalado
systemctl stop apache2
systemctl disable apache2
```

### Error: Nginx 502 Bad Gateway
```bash
# Verificar que backend está corriendo
curl http://127.0.0.1:8000/health

# Ver logs del backend
journalctl -u aipanel -n 50
```

---

## SSL con Let's Encrypt

```bash
# Instalar certbot
apt-get install -y certbot python3-certbot-nginx

# Obtener certificado (cambiar tudominio.com)
certbot --nginx -d tudominio.com

# Renovación automática ya está configurada
systemctl status certbot.timer
```

---

## Actualizar la aplicación

```bash
cd /opt/aipanel
git pull
systemctl restart aipanel
```

O usar el script:
```bash
bash deploy/update.sh
```
