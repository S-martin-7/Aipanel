#!/bin/bash
# ============================================================
# AIPanel - Debian/Ubuntu VPS Deployment Script
# ============================================================
# Usage: sudo ./deploy/install.sh
#
# This script will:
# 1. Install system dependencies (Python, PostgreSQL, Redis, Nginx)
# 2. Create application user and directories
# 3. Setup Python virtual environment
# 4. Configure systemd services
# 5. Setup Nginx reverse proxy
# 6. Configure firewall
# ============================================================

set -e

# ============================================================
# Configuration
# ============================================================
APP_NAME="aipanel"
APP_USER="aipanel"
APP_DIR="/opt/aipanel"
BACKEND_DIR="$APP_DIR/backend"
DOMAIN=""  # Set your domain here or pass as argument
PYTHON_VERSION="3.11"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================================
# Helper Functions
# ============================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}         ${GREEN}AIPanel - VPS Deployment Script${NC}              ${BLUE}║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# ============================================================
# Installation Steps
# ============================================================

install_system_dependencies() {
    log_info "Installing system dependencies..."

    # Update package list
    apt-get update -qq

    # Install essential packages
    apt-get install -y -qq \
        curl \
        wget \
        git \
        build-essential \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release \
        ufw \
        supervisor

    log_success "System dependencies installed"
}

install_python() {
    log_info "Installing Python ${PYTHON_VERSION}..."

    # Add deadsnakes PPA for latest Python (Ubuntu)
    if command -v add-apt-repository &> /dev/null; then
        add-apt-repository -y ppa:deadsnakes/ppa 2>/dev/null || true
    fi

    apt-get update -qq

    # Try to install specific version, fallback to python3
    if apt-cache show python${PYTHON_VERSION} &>/dev/null; then
        apt-get install -y -qq \
            python${PYTHON_VERSION} \
            python${PYTHON_VERSION}-venv \
            python${PYTHON_VERSION}-dev
        PYTHON_BIN="python${PYTHON_VERSION}"
    else
        apt-get install -y -qq \
            python3 \
            python3-venv \
            python3-dev \
            python3-pip
        PYTHON_BIN="python3"
    fi

    log_success "Python installed: $($PYTHON_BIN --version)"
}

install_postgresql() {
    log_info "Installing PostgreSQL..."

    apt-get install -y -qq postgresql postgresql-contrib

    # Start and enable PostgreSQL
    systemctl start postgresql
    systemctl enable postgresql

    # Create database and user
    sudo -u postgres psql -c "CREATE USER ${APP_NAME} WITH PASSWORD '${APP_NAME}_password';" 2>/dev/null || true
    sudo -u postgres psql -c "CREATE DATABASE ${APP_NAME} OWNER ${APP_NAME};" 2>/dev/null || true
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${APP_NAME} TO ${APP_NAME};" 2>/dev/null || true

    log_success "PostgreSQL installed and configured"
}

install_redis() {
    log_info "Installing Redis..."

    apt-get install -y -qq redis-server

    # Configure Redis
    sed -i 's/supervised no/supervised systemd/' /etc/redis/redis.conf

    # Start and enable Redis
    systemctl start redis-server
    systemctl enable redis-server

    log_success "Redis installed and running"
}

install_nginx() {
    log_info "Installing Nginx..."

    apt-get install -y -qq nginx

    systemctl start nginx
    systemctl enable nginx

    log_success "Nginx installed"
}

create_app_user() {
    log_info "Creating application user..."

    # Create user if doesn't exist
    if ! id "$APP_USER" &>/dev/null; then
        useradd -r -m -d /home/$APP_USER -s /bin/bash $APP_USER
        log_success "User '$APP_USER' created"
    else
        log_warn "User '$APP_USER' already exists"
    fi
}

setup_app_directory() {
    log_info "Setting up application directory..."

    # Create app directory
    mkdir -p $APP_DIR
    mkdir -p $BACKEND_DIR/logs

    # Copy application files (assuming script is run from project root)
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

    if [ -d "$PROJECT_ROOT/backend" ]; then
        cp -r "$PROJECT_ROOT/backend/"* "$BACKEND_DIR/"
        log_success "Application files copied"
    else
        log_warn "Backend directory not found. Copy files manually to $BACKEND_DIR"
    fi

    # Set permissions
    chown -R $APP_USER:$APP_USER $APP_DIR
    chmod -R 755 $APP_DIR

    log_success "Application directory configured"
}

setup_python_environment() {
    log_info "Setting up Python virtual environment..."

    cd $BACKEND_DIR

    # Create virtual environment
    sudo -u $APP_USER $PYTHON_BIN -m venv venv

    # Install dependencies
    sudo -u $APP_USER bash -c "
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        pip install gunicorn uvicorn[standard]
    "

    log_success "Python environment configured"
}

setup_environment_file() {
    log_info "Setting up environment file..."

    ENV_FILE="$BACKEND_DIR/.env"

    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "$BACKEND_DIR/.env.example" ]; then
            cp "$BACKEND_DIR/.env.example" "$ENV_FILE"
        else
            cat > "$ENV_FILE" << 'ENVEOF'
# AIPanel Production Configuration
ENVIRONMENT=production
DEBUG=false
PORT=8000

# Database
DATABASE_URL=postgresql+asyncpg://aipanel:aipanel_password@localhost:5432/aipanel

# Redis
REDIS_URL=redis://localhost:6379/0

# Security - CHANGE THESE!
JWT_SECRET=change-this-to-a-secure-random-string-at-least-32-chars
JWT_REFRESH_SECRET=change-this-to-another-secure-random-string-32-chars
JWT_ALGORITHM=HS256
JWT_EXPIRES_IN=900
JWT_REFRESH_EXPIRES_IN=604800

# CORS
CORS_ORIGINS=https://yourdomain.com

# AI Providers
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Transbank
TRANSBANK_COMMERCE_CODE=
TRANSBANK_API_KEY=
TRANSBANK_ENV=production
ENVEOF
        fi

        chown $APP_USER:$APP_USER "$ENV_FILE"
        chmod 600 "$ENV_FILE"

        log_warn "Environment file created. EDIT $ENV_FILE with your settings!"
    else
        log_warn "Environment file already exists"
    fi
}

run_migrations() {
    log_info "Running database migrations..."

    cd $BACKEND_DIR
    sudo -u $APP_USER bash -c "
        source venv/bin/activate
        alembic upgrade head
    "

    log_success "Database migrations completed"
}

setup_systemd_service() {
    log_info "Setting up systemd service..."

    cat > /etc/systemd/system/aipanel.service << EOF
[Unit]
Description=AIPanel Backend API
After=network.target postgresql.service redis-server.service
Wants=postgresql.service redis-server.service

[Service]
Type=exec
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$BACKEND_DIR/venv/bin"
EnvironmentFile=$BACKEND_DIR/.env
ExecStart=$BACKEND_DIR/venv/bin/gunicorn app.main:app \\
    --workers 4 \\
    --worker-class uvicorn.workers.UvicornWorker \\
    --bind 127.0.0.1:8000 \\
    --access-logfile $BACKEND_DIR/logs/access.log \\
    --error-logfile $BACKEND_DIR/logs/error.log \\
    --capture-output \\
    --log-level info

Restart=always
RestartSec=5

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$BACKEND_DIR/logs

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable aipanel
    systemctl start aipanel

    log_success "Systemd service configured and started"
}

setup_nginx() {
    log_info "Configuring Nginx..."

    NGINX_CONF="/etc/nginx/sites-available/aipanel"

    # Determine server_name
    if [ -n "$DOMAIN" ]; then
        SERVER_NAME="$DOMAIN"
    else
        SERVER_NAME="_"
    fi

    cat > $NGINX_CONF << EOF
# AIPanel Nginx Configuration

upstream aipanel_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 80;
    listen [::]:80;
    server_name $SERVER_NAME;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logs
    access_log /var/log/nginx/aipanel_access.log;
    error_log /var/log/nginx/aipanel_error.log;

    # Max upload size
    client_max_body_size 50M;

    # API Backend
    location /api {
        proxy_pass http://aipanel_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Health check
    location /health {
        proxy_pass http://aipanel_backend;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
    }

    # Metrics (restrict access in production)
    location /metrics {
        proxy_pass http://aipanel_backend;
        # allow 127.0.0.1;
        # deny all;
    }

    # Root - serve frontend or redirect
    location / {
        # If you have a frontend, serve it here
        # root /opt/aipanel/frontend/dist;
        # try_files \$uri \$uri/ /index.html;

        # Or redirect to API docs
        return 301 /api/docs;
    }
}
EOF

    # Enable site
    ln -sf $NGINX_CONF /etc/nginx/sites-enabled/aipanel

    # Remove default site
    rm -f /etc/nginx/sites-enabled/default

    # Test and reload
    nginx -t
    systemctl reload nginx

    log_success "Nginx configured"
}

setup_firewall() {
    log_info "Configuring firewall..."

    ufw --force reset
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow ssh
    ufw allow http
    ufw allow https
    ufw --force enable

    log_success "Firewall configured (SSH, HTTP, HTTPS allowed)"
}

setup_ssl() {
    if [ -z "$DOMAIN" ]; then
        log_warn "No domain specified. Skipping SSL setup."
        log_info "To setup SSL later, run: certbot --nginx -d yourdomain.com"
        return
    fi

    log_info "Setting up SSL with Let's Encrypt..."

    apt-get install -y -qq certbot python3-certbot-nginx

    certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN || {
        log_warn "SSL setup failed. Run manually: certbot --nginx -d $DOMAIN"
    }
}

print_summary() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}            ${BLUE}Installation Complete!${NC}                      ${GREEN}║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Important next steps:${NC}"
    echo ""
    echo "1. Edit environment file:"
    echo -e "   ${BLUE}sudo nano $BACKEND_DIR/.env${NC}"
    echo ""
    echo "2. Change these values in .env:"
    echo "   - JWT_SECRET (generate with: openssl rand -hex 32)"
    echo "   - JWT_REFRESH_SECRET"
    echo "   - OPENAI_API_KEY / ANTHROPIC_API_KEY"
    echo "   - CORS_ORIGINS (your frontend domain)"
    echo ""
    echo "3. Restart after editing .env:"
    echo -e "   ${BLUE}sudo systemctl restart aipanel${NC}"
    echo ""
    echo -e "${YELLOW}Useful commands:${NC}"
    echo "   sudo systemctl status aipanel    # Check status"
    echo "   sudo systemctl restart aipanel   # Restart"
    echo "   sudo journalctl -u aipanel -f    # View logs"
    echo "   sudo tail -f $BACKEND_DIR/logs/error.log"
    echo ""
    echo -e "${YELLOW}URLs:${NC}"
    if [ -n "$DOMAIN" ]; then
        echo "   API: https://$DOMAIN/api"
        echo "   Docs: https://$DOMAIN/api/docs"
    else
        IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
        echo "   API: http://$IP/api"
        echo "   Docs: http://$IP/api/docs"
    fi
    echo ""
}

# ============================================================
# Main
# ============================================================

main() {
    print_header

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--domain)
                DOMAIN="$2"
                shift 2
                ;;
            -h|--help)
                echo "Usage: sudo ./install.sh [-d domain.com]"
                echo ""
                echo "Options:"
                echo "  -d, --domain    Domain name for SSL setup"
                echo "  -h, --help      Show this help"
                exit 0
                ;;
            *)
                shift
                ;;
        esac
    done

    check_root

    log_info "Starting AIPanel installation..."
    echo ""

    install_system_dependencies
    install_python
    install_postgresql
    install_redis
    install_nginx
    create_app_user
    setup_app_directory
    setup_python_environment
    setup_environment_file
    run_migrations
    setup_systemd_service
    setup_nginx
    setup_firewall

    if [ -n "$DOMAIN" ]; then
        setup_ssl
    fi

    print_summary
}

main "$@"
