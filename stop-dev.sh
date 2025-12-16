#!/bin/bash

# ============================================
# BETIX LOCAL - Stop Development Environment
# ============================================

echo "🛑 Stopping BETIX Development Environment..."
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Stop Docker services
echo -e "${YELLOW}📦 Stopping Docker services...${NC}"
docker compose -f docker-compose.dev.yml down

echo ""
echo -e "${GREEN}✅ All services stopped!${NC}"
echo ""
echo "💡 To remove all data (volumes), run:"
echo "   docker-compose -f docker-compose.dev.yml down -v"
echo ""
