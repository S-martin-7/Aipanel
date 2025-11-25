#!/bin/bash
# ============================================================
# AIPanel - Quick Install (Simplified)
# ============================================================
# Usage: bash deploy/quick-install.sh
# ============================================================

set -e

echo "╔════════════════════════════════════════╗"
echo "║   AIPanel - Quick Install (VPS)       ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Check root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Please run as root"
    echo "Usage: sudo bash deploy/quick-install.sh"
    exit 1
fi

# Variables
APP_DIR="/opt/aipanel"
BACKEND_DIR="$APP_DIR/backend"
APP_USER="aipanel"

echo ">>> Step 1: Updating system..."
apt-get update -qq

echo ">>> Step 2: Installing system packages..."
apt-get install -y -qq \
    python3 \
    python3-pip \
    python3-venv \
    postgresql \
    postgresql-contrib \
    redis-server \
    nginx \
    ufw \
    curl \
    git

echo ">>> Step 3: Starting services..."
systemctl start postgresql
systemctl enable postgresql
systemctl start redis-server
systemctl enable redis-server

echo ">>> Step 4: Creating database..."
sudo -u postgres psql -c "CREATE USER aipanel WITH PASSWORD 'aipanel_password';" 2>/dev/null || echo "User already exists"
sudo -u postgres psql -c "CREATE DATABASE aipanel OWNER aipanel;" 2>/dev/null || echo "Database already exists"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE aipanel TO aipanel;" 2>/dev/null || true

echo ">>> Step 5: Creating app user..."
useradd -r -m -d /home/aipanel -s /bin/bash aipanel 2>/dev/null || echo "User already exists"

echo ">>> Step 6: Setting up application directory..."
mkdir -p $APP_DIR
mkdir -p $BACKEND_DIR/logs

# Check if we're running from project root
if [ -d "backend" ]; then
    echo "Copying backend files..."
    cp -r backend/* $BACKEND_DIR/
else
    echo "WARNING: backend directory not found in current location"
    echo "Please copy your files manually to $BACKEND_DIR"
fi

chown -R aipanel:aipanel $APP_DIR

echo ">>> Step 7: Setting up Python environment..."
cd $BACKEND_DIR
sudo -u aipanel python3 -m venv venv

echo ">>> Step 8: Installing Python dependencies..."
sudo -u aipanel bash << 'EOFU'
cd /opt/aipanel/backend
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
pip install --quiet gunicorn uvicorn[standard]
EOFU

echo ">>> Step 9: Creating .env file..."
if [ ! -f "$BACKEND_DIR/.env" ]; then
    cat > "$BACKEND_DIR/.env" << 'EOF'
ENVIRONMENT=production
DEBUG=false
PORT=8000
DATABASE_URL=postgresql+asyncpg://aipanel:aipanel_password@localhost:5432/aipanel
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=CHANGE-THIS-TO-SECURE-KEY-MIN-32-CHARS
JWT_REFRESH_SECRET=CHANGE-THIS-TO-ANOTHER-SECURE-KEY-32-CHARS
JWT_ALGORITHM=HS256
JWT_EXPIRES_IN=900
JWT_REFRESH_EXPIRES_IN=604800
CORS_ORIGINS=http://localhost:3000
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
EOF
    chown aipanel:aipanel "$BACKEND_DIR/.env"
    chmod 600 "$BACKEND_DIR/.env"
    echo "IMPORTANT: Edit $BACKEND_DIR/.env with your settings!"
fi

echo ">>> Step 10: Running migrations..."
cd $BACKEND_DIR
sudo -u aipanel bash << 'EOFU'
cd /opt/aipanel/backend
source venv/bin/activate
alembic upgrade head
EOFU

echo ">>> Step 11: Creating systemd service..."
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
    --bind 127.0.0.1:8000 \
    --access-logfile /opt/aipanel/backend/logs/access.log \
    --error-logfile /opt/aipanel/backend/logs/error.log
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable aipanel
systemctl start aipanel

echo ">>> Step 12: Configuring Nginx..."
cat > /etc/nginx/sites-available/aipanel << 'EOF'
server {
    listen 80;
    server_name _;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

ln -sf /etc/nginx/sites-available/aipanel /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo ">>> Step 13: Configuring firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
echo "y" | ufw enable

echo ""
echo "╔════════════════════════════════════════╗"
echo "║     Installation Complete!             ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "1. Edit configuration: nano $BACKEND_DIR/.env"
echo "2. Generate secrets: openssl rand -hex 32"
echo "3. Restart service: systemctl restart aipanel"
echo ""
echo "Check status:"
echo "  systemctl status aipanel"
echo "  journalctl -u aipanel -f"
echo ""
IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
echo "URLs:"
echo "  API: http://$IP/api/docs"
echo "  Health: http://$IP/health"
echo ""
