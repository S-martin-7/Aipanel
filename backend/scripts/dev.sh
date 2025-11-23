#!/bin/bash
# AIPanel Backend - Development Server Script
# Usage: ./scripts/dev.sh [command]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

cd "$BACKEND_DIR"

# Functions
print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}     ${GREEN}AIPanel Backend - Dev Server${NC}        ${BLUE}║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: Python 3 is required but not installed.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} Python 3 found: $(python3 --version)"
}

check_env() {
    if [ ! -f ".env" ]; then
        echo -e "${YELLOW}Warning: .env file not found. Creating from .env.example...${NC}"
        if [ -f ".env.example" ]; then
            cp .env.example .env
            echo -e "${GREEN}✓${NC} Created .env from .env.example"
            echo -e "${YELLOW}  Please update .env with your configuration${NC}"
        else
            echo -e "${RED}Error: .env.example not found${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✓${NC} .env file found"
    fi
}

setup_venv() {
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv venv
        echo -e "${GREEN}✓${NC} Virtual environment created"
    fi

    # Activate venv
    source venv/bin/activate
    echo -e "${GREEN}✓${NC} Virtual environment activated"
}

install_deps() {
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    if [ -f "requirements-dev.txt" ]; then
        pip install -q -r requirements-dev.txt
    fi
    echo -e "${GREEN}✓${NC} Dependencies installed"
}

check_services() {
    echo -e "\n${BLUE}Checking services...${NC}"

    # Check PostgreSQL
    if pg_isready -q 2>/dev/null || nc -z localhost 5432 2>/dev/null; then
        echo -e "${GREEN}✓${NC} PostgreSQL is running"
    else
        echo -e "${YELLOW}⚠${NC} PostgreSQL is not running on port 5432"
        echo -e "  Run: ${BLUE}docker-compose up -d postgres${NC} or start PostgreSQL manually"
    fi

    # Check Redis
    if redis-cli ping &>/dev/null || nc -z localhost 6379 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Redis is running"
    else
        echo -e "${YELLOW}⚠${NC} Redis is not running on port 6379"
        echo -e "  Run: ${BLUE}docker-compose up -d redis${NC} or start Redis manually"
    fi
}

run_migrations() {
    echo -e "\n${YELLOW}Running database migrations...${NC}"
    alembic upgrade head
    echo -e "${GREEN}✓${NC} Migrations applied"
}

start_server() {
    echo -e "\n${GREEN}Starting development server...${NC}"
    echo -e "${BLUE}API Docs: http://localhost:8000/api/docs${NC}"
    echo -e "${BLUE}Health:   http://localhost:8000/health${NC}"
    echo ""

    uvicorn app.main:app \
        --host 0.0.0.0 \
        --port ${PORT:-8000} \
        --reload \
        --log-level info
}

# Command handlers
cmd_run() {
    print_header
    check_python
    check_env
    setup_venv
    check_services
    start_server
}

cmd_setup() {
    print_header
    check_python
    check_env
    setup_venv
    install_deps
    echo -e "\n${GREEN}Setup complete!${NC}"
    echo -e "Run ${BLUE}./scripts/dev.sh run${NC} to start the server"
}

cmd_migrate() {
    setup_venv
    run_migrations
}

cmd_shell() {
    setup_venv
    python3 -c "
from app.core.database import get_db
from app.models import *
print('Models loaded. Use: Tenant, TenantUser, Agent, etc.')
"
    python3
}

cmd_test() {
    setup_venv
    pytest tests/ -v "$@"
}

cmd_lint() {
    setup_venv
    echo -e "${YELLOW}Running linters...${NC}"
    ruff check app/ --fix
    echo -e "${GREEN}✓${NC} Linting complete"
}

cmd_help() {
    echo "AIPanel Backend Development Script"
    echo ""
    echo "Usage: ./scripts/dev.sh [command]"
    echo ""
    echo "Commands:"
    echo "  run       Start the development server (default)"
    echo "  setup     Install dependencies and setup environment"
    echo "  migrate   Run database migrations"
    echo "  test      Run tests"
    echo "  lint      Run linters"
    echo "  shell     Open Python shell with models loaded"
    echo "  help      Show this help message"
}

# Main
case "${1:-run}" in
    run)
        cmd_run
        ;;
    setup)
        cmd_setup
        ;;
    migrate)
        cmd_migrate
        ;;
    test)
        shift
        cmd_test "$@"
        ;;
    lint)
        cmd_lint
        ;;
    shell)
        cmd_shell
        ;;
    help|--help|-h)
        cmd_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        cmd_help
        exit 1
        ;;
esac
