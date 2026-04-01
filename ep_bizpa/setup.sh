#!/bin/bash
set -e

echo "============================================"
echo " BizPA Setup Script"
echo "============================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} Node.js is not installed. Please install Node.js 18+ from https://nodejs.org"
    exit 1
fi
NODE_VER=$(node -v)
echo -e "${GREEN}[OK]${NC} Node.js found: $NODE_VER"

# Check for PostgreSQL psql
SKIP_DB=0
if ! command -v psql &> /dev/null; then
    echo -e "${YELLOW}[WARN]${NC} psql not found in PATH. Database setup will be skipped."
    echo "       Install PostgreSQL or add psql to PATH to enable database setup."
    SKIP_DB=1
else
    echo -e "${GREEN}[OK]${NC} PostgreSQL psql found"
fi

# Navigate to backend directory
cd "$SCRIPT_DIR/solution/backend"

# Create .env if not exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}[INFO]${NC} Creating .env from .env.example..."
    if [ -f "../../.env.example" ]; then
        cp "../../.env.example" ".env"
    else
        echo -e "${YELLOW}[INFO]${NC} Creating default .env file..."
        cat > .env << 'EOF'
PORT=5055
DB_HOST=localhost
DB_PORT=5432
DB_NAME=bizpa
DB_USER=postgres
DB_PASSWORD=postgres
SUPABASE_URL=http://localhost:54321
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key
JWT_SECRET=your-jwt-secret-change-in-production
EOF
    fi
    echo -e "${GREEN}[OK]${NC} .env file created"
else
    echo -e "${GREEN}[OK]${NC} .env file exists"
fi

# Install npm dependencies
echo ""
echo -e "${YELLOW}[INFO]${NC} Installing npm dependencies..."
npm install
echo -e "${GREEN}[OK]${NC} Dependencies installed"

# Database setup
if [ "$SKIP_DB" -eq 0 ]; then
    echo ""
    echo -e "${YELLOW}[INFO]${NC} Setting up database..."

    # Load env vars
    export $(grep -v '^#' .env | xargs)

    # Set defaults
    DB_HOST=${DB_HOST:-localhost}
    DB_PORT=${DB_PORT:-5432}
    DB_NAME=${DB_NAME:-bizpa}
    DB_USER=${DB_USER:-postgres}
    export PGPASSWORD=${DB_PASSWORD:-postgres}

    # Check if database exists
    if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
        echo -e "${YELLOW}[INFO]${NC} Creating database $DB_NAME..."
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || {
            echo -e "${YELLOW}[WARN]${NC} Could not create database. It may already exist or require manual creation."
        }
    else
        echo -e "${GREEN}[OK]${NC} Database $DB_NAME exists"
    fi

    # Apply schema
    echo -e "${YELLOW}[INFO]${NC} Applying database schema..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "src/models/schema.sql" 2>/dev/null || {
        echo -e "${YELLOW}[WARN]${NC} Schema application had warnings. Check database manually."
    }
    echo -e "${GREEN}[OK]${NC} Schema applied"

    # Apply migrations
    echo -e "${YELLOW}[INFO]${NC} Applying migrations..."
    for migration in src/models/*_migration.sql; do
        if [ -f "$migration" ]; then
            echo "  - Applying $(basename "$migration")"
            psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$migration" 2>/dev/null || true
        fi
    done
    echo -e "${GREEN}[OK]${NC} Migrations applied"

    unset PGPASSWORD
fi

# Final status
echo ""
echo "============================================"
echo " Setup Complete!"
echo "============================================"
echo ""
echo "To start the server:"
echo "  cd solution/backend"
echo "  npm start"
echo ""
echo "Or use Docker:"
echo "  docker-compose up -d"
echo ""
echo "API will be available at:"
echo "  http://127.0.0.1:5055"
echo "  http://127.0.0.1:5055/api/v1"
echo "  http://127.0.0.1:5055/health"
echo ""
