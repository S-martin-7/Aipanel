#!/bin/bash
# ============================================================
# AIPanel - Update Script
# ============================================================
# Usage: sudo ./deploy/update.sh
#
# This script will:
# 1. Pull latest code from git
# 2. Install new dependencies
# 3. Run migrations
# 4. Restart services
# ============================================================

set -e

APP_DIR="/opt/aipanel"
BACKEND_DIR="$APP_DIR/backend"
APP_USER="aipanel"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}[AIPanel]${NC} Starting update..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

cd $APP_DIR

# 1. Pull latest code
echo -e "${YELLOW}Pulling latest code...${NC}"
sudo -u $APP_USER git pull origin main 2>/dev/null || {
    echo "Git pull failed or not a git repo. Skipping..."
}

# 2. Install new dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
cd $BACKEND_DIR
sudo -u $APP_USER bash -c "
    source venv/bin/activate
    pip install -r requirements.txt --quiet
"

# 3. Run migrations
echo -e "${YELLOW}Running migrations...${NC}"
sudo -u $APP_USER bash -c "
    source venv/bin/activate
    alembic upgrade head
"

# 4. Restart service
echo -e "${YELLOW}Restarting service...${NC}"
systemctl restart aipanel

# 5. Check status
sleep 2
if systemctl is-active --quiet aipanel; then
    echo -e "${GREEN}✓ Update complete! Service is running.${NC}"
else
    echo -e "${YELLOW}Warning: Service may not be running. Check logs:${NC}"
    echo "  sudo journalctl -u aipanel -n 50"
fi
