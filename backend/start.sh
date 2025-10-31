#!/usr/bin/env bash
# Simple startup script for complete AMS system (all services)
set -e

echo "🚀 Starting Complete AMS System (All Services)..."
echo ""

# Check if network exists, create if not
if ! docker network inspect ams-network >/dev/null 2>&1; then
    echo "Creating ams-network..."
    docker network create ams-network
fi

# Start all services
echo "Starting all services (this will take ~60 seconds)..."
echo "  - Keycloak + Init"
echo "  - Backend API"
echo "  - Frontend"
echo ""
docker compose -f docker-compose.dev-all.yml up -d --build

echo ""
echo "⏳ Waiting for services to be healthy..."
echo ""

# Wait for backend to be healthy (indicates most services are up)
for i in {1..90}; do
    if curl -sf http://localhost:8000/api/health/ready >/dev/null 2>&1; then
        echo "✅ Backend is healthy!"
        break
    fi
    echo -n "."
    sleep 2
done

echo ""
echo ""
echo "=== 🎉 AMS System Started ===="
echo ""
echo "Services:"
echo "  - Keycloak Admin:  http://localhost:8080/admin (admin/admin123)"
echo "  - Backend API:     http://localhost:8000/docs"
echo "  - Frontend UI:     http://localhost:3000"
echo ""
echo "To view logs:"
echo "  docker compose -f docker-compose.dev-all.yml logs -f [service-name]"
echo ""
echo "To stop all services:"
echo "  docker compose -f docker-compose.dev-all.yml down"
echo ""
