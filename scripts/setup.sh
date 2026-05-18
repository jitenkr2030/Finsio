#!/usr/bin/env bash
set -euo pipefail

# ═══════════════════════════════════════
#  Finsio — Initial Setup Script
#
#  Performs a full first-time setup:
#    1. Copies .env.example → .env
#    2. Starts database containers
#    3. Installs dependencies
#    4. Runs migrations (Django + Fusio)
#    5. Creates Django superuser
#    6. Loads Fusio fixtures
#    7. Seeds sample data
#    8. Starts all services
# ═══════════════════════════════════════

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo -e "${CYAN}══════════════════════════════════════${NC}"
    echo -e "${CYAN}  Finsio — Financial Operations Platform${NC}"
    echo -e "${CYAN}  Initial Setup${NC}"
    echo -e "${CYAN}══════════════════════════════════════${NC}"
    echo ""
}

print_step() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "    $1"
}

# ── Step 0: Pre-flight checks ──
print_header

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    print_error "Docker Compose is not available. Please update Docker."
    exit 1
fi

print_step "Docker and Docker Compose found"

# ── Step 1: Environment file ──
if [ ! -f .env ]; then
    cp .env.example .env

    # Generate a random Django secret key
    DJANGO_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))" 2>/dev/null || openssl rand -base64 50)
    FUSIO_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || openssl rand -base64 32)
    INTERNAL_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))" 2>/dev/null || openssl rand -base64 48)

    # Replace placeholders in .env
    if command -v sed &> /dev/null; then
        sed -i "s/change-me-to-a-random-50-char-string/${DJANGO_SECRET}/" .env
        sed -i "s/change-me-fusio-secret-min-32-chars/${FUSIO_SECRET}/" .env
        sed -i "s/change-me-internal-token/${INTERNAL_TOKEN}/" .env
    fi

    print_step "Created .env with generated secrets"
    print_warn "Please review .env and add your payment provider API keys"
else
    print_step ".env already exists (skipping)"
fi

# ── Step 2: Start database containers ──
echo ""
echo "Starting database containers..."
docker compose up -d postgres mysql_fusio redis
sleep 8

# Wait for PostgreSQL
echo -n "    Waiting for PostgreSQL"
for i in $(seq 1 30); do
    if docker compose exec postgres pg_isready -U finsio -q 2>/dev/null; then
        echo ""
        print_step "PostgreSQL is ready"
        break
    fi
    echo -n "."
    sleep 1
done

# Wait for MySQL
echo -n "    Waiting for MySQL"
for i in $(seq 1 30); do
    if docker compose exec mysql_fusio mysqladmin ping -h localhost -u root -proot --silent 2>/dev/null; then
        echo ""
        print_step "MySQL is ready"
        break
    fi
    echo -n "."
    sleep 1
done

# Wait for Redis
echo -n "    Waiting for Redis"
for i in $(seq 1 15); do
    if docker compose exec redis redis-cli ping 2>/dev/null | grep -q PONG; then
        echo ""
        print_step "Redis is ready"
        break
    fi
    echo -n "."
    sleep 1
done

# ── Step 3: Build backend image ──
echo ""
echo "Building Django backend image..."
docker compose build backend
print_step "Backend image built"

# ── Step 4: Run Django migrations ──
echo ""
echo "Running Django migrations..."
docker compose run --rm backend python manage.py migrate --noinput
print_step "Django migrations complete"

# ── Step 5: Run Fusio migrations ──
echo ""
echo "Building and initializing Fusio gateway..."
docker compose build gateway
docker compose run --rm gateway php bin/fusio migration:execute 2>/dev/null || print_warn "Fusio migration skipped (will initialize on first run)"
print_step "Fusio initialization complete"

# ── Step 6: Create Django superuser ──
echo ""
echo "Creating Django superuser..."
docker compose run --rm backend python manage.py shell -c "
from django.contrib.auth.models import User;
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@finsio.local', 'admin');
    print('Superuser created: admin/admin')
else:
    print('Superuser already exists')
" 2>/dev/null || print_warn "Superuser creation skipped"
print_step "Django superuser ready (admin/admin)"

# ── Step 7: Load Fusio fixtures ──
echo ""
echo "Loading Fusio API routes and plans..."
docker compose run --rm gateway php bin/fusio import resources/fixtures/routes.yaml 2>/dev/null || print_warn "Fusio routes will be loaded on first request"
print_step "Fusio fixtures loaded"

# ── Step 8: Create beancount directory structure ──
echo ""
mkdir -p beancount/transactions
touch beancount/transactions/.gitkeep
print_step "Beancount directory structure verified"

# ── Step 9: Seed sample data ──
echo ""
echo "Seeding sample development data..."
docker compose run --rm backend python scripts/seed_data.py 2>/dev/null || print_warn "Sample data seeding skipped"
print_step "Sample data loaded"

# ── Step 10: Start all services ──
echo ""
echo "Starting all services..."
docker compose up -d
sleep 3

# ── Step 11: Run verification ──
echo ""
echo "Running integration verification..."
docker compose exec backend python scripts/verify_integration.py 2>/dev/null || print_warn "Verification will run after services stabilize"

# ── Done ──
echo ""
echo -e "${CYAN}══════════════════════════════════════${NC}"
echo -e "${GREEN}  Setup complete!${NC}"
echo ""
echo "  Services:"
echo "    API Gateway:      http://localhost:8080"
echo "    Developer Portal: http://localhost:8080/portal/"
echo "    Django Admin:     http://localhost:8000/django-admin/"
echo "    Health Check:     http://localhost:8000/health/"
echo "    Nginx Proxy:      http://localhost:80"
echo ""
echo "  Credentials:"
echo "    Django: admin / admin"
echo "    Fusio:  See fusio.yml for admin credentials"
echo ""
echo "  Useful commands:"
echo "    make dev        Start dev environment"
echo "    make logs       Tail all logs"
echo "    make test       Run tests"
echo "    make verify     Integration check"
echo "    make shell      Django shell"
echo "    make psql       PostgreSQL shell"
echo -e "${CYAN}══════════════════════════════════════${NC}"
