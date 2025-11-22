#!/bin/bash
# AIPanel - Setup Script
# Run as root or with sudo

set -e

echo "=== AIPanel Setup Script ==="

# Variables
APP_USER="aipanel"
APP_DIR="/opt/aipanel"
DB_NAME="aipanel"
DB_USER="aipanel"
DB_PASS="change-this-password"

# 1. Create user
echo "Creating application user..."
useradd -r -m -s /bin/bash $APP_USER || true

# 2. Install system dependencies
echo "Installing system dependencies..."
apt-get update
apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    postgresql \
    postgresql-contrib \
    nginx \
    nodejs \
    npm \
    certbot \
    python3-certbot-nginx

# 3. Setup PostgreSQL
echo "Setting up PostgreSQL..."
sudo -u postgres psql <<EOF
CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';
CREATE DATABASE $DB_NAME OWNER $DB_USER;
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF

# 4. Create directories
echo "Creating application directories..."
mkdir -p $APP_DIR/{backend,frontend,logs,uploads}
chown -R $APP_USER:$APP_USER $APP_DIR

# 5. Copy application files
echo "Copying application files..."
cp -r backend/* $APP_DIR/backend/
cp -r frontend/* $APP_DIR/frontend/

# 6. Setup backend
echo "Setting up backend..."
cd $APP_DIR/backend
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Copy and configure .env
cp .env.example .env
echo ">>> Edit $APP_DIR/backend/.env with your configuration <<<"

# Run migrations
alembic upgrade head

# Create admin user
python -m app.scripts.seed_admin

deactivate

# 7. Setup frontend
echo "Setting up frontend..."
cd $APP_DIR/frontend
npm install
npm run build

# 8. Install systemd services
echo "Installing systemd services..."
cp deploy/aipanel-backend.service /etc/systemd/system/
cp deploy/aipanel-frontend.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable aipanel-backend aipanel-frontend

# 9. Setup nginx
echo "Setting up nginx..."
cp deploy/nginx.conf /etc/nginx/sites-available/aipanel
ln -sf /etc/nginx/sites-available/aipanel /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx

# 10. Set permissions
chown -R $APP_USER:$APP_USER $APP_DIR

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Edit /opt/aipanel/backend/.env with your configuration"
echo "2. Update /etc/nginx/sites-available/aipanel with your domain"
echo "3. Run: certbot --nginx -d your-domain.com"
echo "4. Start services: systemctl start aipanel-backend aipanel-frontend"
echo ""
