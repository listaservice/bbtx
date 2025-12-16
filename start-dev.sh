#!/bin/bash

# ============================================
# BETIX LOCAL - Start Development Environment
# ============================================

echo "🚀 Starting BETIX Development Environment..."
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker Desktop first.${NC}"
    exit 1
fi

# Start Docker services
echo -e "${YELLOW}📦 Starting Docker services (PostgreSQL + Redis)...${NC}"
docker compose -f docker-compose.dev.yml up -d

# Wait for services to be ready
echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
sleep 5

# Check PostgreSQL
if docker compose -f docker-compose.dev.yml exec -T postgres pg_isready -U betix > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL is ready${NC}"
else
    echo -e "${RED}❌ PostgreSQL failed to start${NC}"
    exit 1
fi

# Check Redis
if docker compose -f docker-compose.dev.yml exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis is ready${NC}"
else
    echo -e "${RED}❌ Redis failed to start${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ All services are running!${NC}"
echo ""
echo "📊 Services available:"
echo "  • PostgreSQL: localhost:5432"
echo "  • Redis: localhost:6379"
echo "  • Adminer (DB UI): http://localhost:8080"
echo ""
echo "🔧 Next steps:"
echo "  1. Open new terminal and run: cd backend && source venv/bin/activate && python -m app.main"
echo "  2. Open another terminal and run: cd frontend && npm run dev"
echo ""
echo "📖 Read README-DEV.md for full documentation"
echo ""
