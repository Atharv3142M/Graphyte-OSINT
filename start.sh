#!/bin/bash
# Startup script for Graphyte OSINT Platform

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$PROJECT_ROOT/venv"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║      GRAPHYTE OSINT PLATFORM - STARTUP SCRIPT               ║"
echo "╚════════════════════════════════════════════════════════════╝"

# Activate virtual environment
if [ -d "$VENV_PATH" ]; then
    echo "✓ Virtual environment found"
    source "$VENV_PATH/bin/activate"
else
    echo "✗ Virtual environment not found at $VENV_PATH"
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_PATH"
    source "$VENV_PATH/bin/activate"
    echo "✓ Virtual environment created"
    
    echo "Installing dependencies..."
    pip install -q -r "$PROJECT_ROOT/backend/requirements.txt"
    echo "✓ Dependencies installed"
fi

# Load environment
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "⚠ .env file not found. Copying from .env.example..."
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    echo "→ Please edit .env with your configuration"
fi

# Check services
echo ""
echo "Checking service dependencies..."

# Check Redis
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        echo "✓ Redis is running"
    else
        echo "⚠ Redis is not running. Start with: redis-server"
    fi
else
    echo "⚠ Redis CLI not found. Make sure Redis is running"
fi

# Check PostgreSQL
if command -v psql &> /dev/null; then
    if psql -lqt &> /dev/null 2>&1; then
        echo "✓ PostgreSQL is running"
    else
        echo "⚠ PostgreSQL is not running"
    fi
else
    echo "⚠ PostgreSQL CLI not found. Make sure PostgreSQL is running"
fi

# Check Neo4j
if [ -n "$NEO4J_URI" ]; then
    echo "✓ Neo4j configured at $NEO4J_URI"
else
    echo "⚠ Neo4j not configured"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              STARTING GRAPHYTE BACKEND                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Start backend
cd "$PROJECT_ROOT"
python main.py
