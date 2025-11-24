#!/bin/bash
# ============================================================
# AIPanel - Management Script
# ============================================================
# Usage: sudo ./deploy/manage.sh [command]
# ============================================================

APP_DIR="/opt/aipanel"
BACKEND_DIR="$APP_DIR/backend"
APP_USER="aipanel"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

show_help() {
    echo ""
    echo -e "${BLUE}AIPanel Management Script${NC}"
    echo ""
    echo "Usage: sudo ./manage.sh [command]"
    echo ""
    echo "Commands:"
    echo "  status      Show service status"
    echo "  start       Start the service"
    echo "  stop        Stop the service"
    echo "  restart     Restart the service"
    echo "  logs        Show live logs"
    echo "  errors      Show error logs"
    echo "  migrate     Run database migrations"
    echo "  shell       Open Python shell"
    echo "  backup-db   Backup database"
    echo "  restore-db  Restore database from backup"
    echo "  nginx-test  Test Nginx configuration"
    echo "  ssl-renew   Renew SSL certificates"
    echo "  help        Show this help"
    echo ""
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}Please run as root (sudo)${NC}"
        exit 1
    fi
}

cmd_status() {
    echo -e "${BLUE}=== AIPanel Service Status ===${NC}"
    systemctl status aipanel --no-pager
    echo ""
    echo -e "${BLUE}=== PostgreSQL ===${NC}"
    systemctl status postgresql --no-pager -l | head -5
    echo ""
    echo -e "${BLUE}=== Redis ===${NC}"
    systemctl status redis-server --no-pager -l | head -5
    echo ""
    echo -e "${BLUE}=== Nginx ===${NC}"
    systemctl status nginx --no-pager -l | head -5
}

cmd_start() {
    echo "Starting AIPanel..."
    systemctl start aipanel
    sleep 2
    systemctl status aipanel --no-pager
}

cmd_stop() {
    echo "Stopping AIPanel..."
    systemctl stop aipanel
    echo -e "${GREEN}Service stopped${NC}"
}

cmd_restart() {
    echo "Restarting AIPanel..."
    systemctl restart aipanel
    sleep 2
    if systemctl is-active --quiet aipanel; then
        echo -e "${GREEN}✓ Service restarted successfully${NC}"
    else
        echo -e "${RED}Service failed to start. Check logs:${NC}"
        journalctl -u aipanel -n 20 --no-pager
    fi
}

cmd_logs() {
    echo -e "${BLUE}Live logs (Ctrl+C to exit):${NC}"
    journalctl -u aipanel -f
}

cmd_errors() {
    echo -e "${BLUE}=== Application Errors ===${NC}"
    tail -100 $BACKEND_DIR/logs/error.log 2>/dev/null || {
        echo "No error log found. Showing journalctl:"
        journalctl -u aipanel -p err -n 50 --no-pager
    }
}

cmd_migrate() {
    echo "Running migrations..."
    cd $BACKEND_DIR
    sudo -u $APP_USER bash -c "
        source venv/bin/activate
        alembic upgrade head
    "
    echo -e "${GREEN}✓ Migrations complete${NC}"
}

cmd_shell() {
    echo "Opening Python shell..."
    cd $BACKEND_DIR
    sudo -u $APP_USER bash -c "
        source venv/bin/activate
        python3 -c 'from app.models import *; print(\"Models loaded: Tenant, TenantUser, Agent, etc.\")'
        python3
    "
}

cmd_backup_db() {
    BACKUP_DIR="/opt/aipanel/backups"
    mkdir -p $BACKUP_DIR
    BACKUP_FILE="$BACKUP_DIR/aipanel_$(date +%Y%m%d_%H%M%S).sql"

    echo "Creating database backup..."
    sudo -u postgres pg_dump aipanel > $BACKUP_FILE
    gzip $BACKUP_FILE

    echo -e "${GREEN}✓ Backup created: ${BACKUP_FILE}.gz${NC}"
    echo ""
    echo "Recent backups:"
    ls -lh $BACKUP_DIR/*.gz 2>/dev/null | tail -5
}

cmd_restore_db() {
    BACKUP_DIR="/opt/aipanel/backups"

    echo "Available backups:"
    ls -lh $BACKUP_DIR/*.gz 2>/dev/null || {
        echo "No backups found in $BACKUP_DIR"
        exit 1
    }

    echo ""
    read -p "Enter backup filename (without path): " BACKUP_NAME

    if [ ! -f "$BACKUP_DIR/$BACKUP_NAME" ]; then
        echo -e "${RED}Backup file not found${NC}"
        exit 1
    fi

    echo -e "${YELLOW}WARNING: This will overwrite the current database!${NC}"
    read -p "Are you sure? (yes/no): " CONFIRM

    if [ "$CONFIRM" != "yes" ]; then
        echo "Aborted."
        exit 0
    fi

    echo "Stopping service..."
    systemctl stop aipanel

    echo "Restoring database..."
    gunzip -c "$BACKUP_DIR/$BACKUP_NAME" | sudo -u postgres psql aipanel

    echo "Starting service..."
    systemctl start aipanel

    echo -e "${GREEN}✓ Database restored${NC}"
}

cmd_nginx_test() {
    echo "Testing Nginx configuration..."
    nginx -t
}

cmd_ssl_renew() {
    echo "Renewing SSL certificates..."
    certbot renew --dry-run
    echo ""
    echo "To force renewal: certbot renew --force-renewal"
}

# Main
case "${1:-help}" in
    status)     check_root; cmd_status ;;
    start)      check_root; cmd_start ;;
    stop)       check_root; cmd_stop ;;
    restart)    check_root; cmd_restart ;;
    logs)       check_root; cmd_logs ;;
    errors)     check_root; cmd_errors ;;
    migrate)    check_root; cmd_migrate ;;
    shell)      check_root; cmd_shell ;;
    backup-db)  check_root; cmd_backup_db ;;
    restore-db) check_root; cmd_restore_db ;;
    nginx-test) check_root; cmd_nginx_test ;;
    ssl-renew)  check_root; cmd_ssl_renew ;;
    help|*)     show_help ;;
esac
