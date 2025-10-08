# AMS Backend - Quick Start

## Prerequisites

Add to `/etc/hosts`:
```
127.0.0.1 keycloak.local
127.0.0.1 backend.local
127.0.0.1 frontend.local
```

## Startup

```bash
# 1. Start Keycloak
cd backend
docker compose -p ams-keycloak -f docker-compose.keycloak.yml up -d

# 2. Start Backend
docker compose -p ams-backend -f docker-compose.backend.yml up -d --build

# 3. Start Frontend
cd ../frontend
docker compose -p ams-frontend -f docker-compose.frontend.yml up -d

# 4. Configure Keycloak (ONE-TIME ONLY - after first Keycloak start)
docker exec ams-backend-dev bash /app/init_keycloak.sh

# 5. Restart backend to apply Keycloak config
docker restart ams-backend-dev
```

## Access

- Keycloak: http://keycloak.local:8080/admin (admin/admin123)
- Backend API: http://backend.local:8000/docs
- Frontend: http://frontend.local:3000

## Shutdown

```bash
docker compose -p ams-keycloak -f docker-compose.keycloak.yml down
docker compose -p ams-backend -f docker-compose.backend.yml down
docker compose -p ams-frontend -f docker-compose.frontend.yml down
```
