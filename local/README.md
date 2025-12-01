# Local Development

## Starting Services locally (with Docker)

Requires the minimum `.env` file within `local` folder:

```bash
# .env

# Keycloak Authorization and Authentication management (mandatory)
KEYCLOAK_ADMIN=<CHANGE_ME_WITH_KEYCLOAK_ADMIN_USER>
KEYCLOAK_ADMIN_PASSWORD=<CHANGE_ME_WITH_KEYCLOAK_ADMIN_PASS>

# Admin credentials
KEYCLOAK_ADMIN_CLIENT_SECRET=<CHANGE_ME_WITH_KEYCLOAK_CLIENT_SECRET_STRING>

# MINIO credentials
MINIO_ROOT_USER=<CHANGE_ME_WITH_ADMIN_USER>
MINIO_ROOT_PASSWORD=<CHANGE_ME_WITH_ADMIN_USER>

```

A file named `.env` in the current directory is automatically loaded. Run services with:

```bash
cd local
docker compose up -d --build
# Starts:
# 1. Keycloak (pre-configured) (deploy)
# 2. Backend via backend/docker-compose.backend.yml (deploy)
# 3. Frontend via frontend/docker-compose.prod.yml (build and deploy)
```

## Starting Services

```bash
# 1. Start Keycloak
cd local/keycloak
./start.sh
# Wait 30-60 seconds for Keycloak to start

# 2. Configure Keycloak (one-time, or when reconfiguring)
cd local/keycloak
./configure_keycloak.sh

# 3. Start Backend
cd backend
# Load environment variables in your IDE (PyCharm: Run > Edit Configurations > EnvFile)
# Or export them: export $(cat .env.development | grep -v '^#' | xargs)
python3 server.py

# 4. Start Frontend
cd frontend
npm start
```

## Access

- Keycloak: http://localhost:8080/admin (admin/admin123)
- Backend: http://localhost:8000/docs
- Frontend: http://localhost:3000

## Environment Files

Each service has its own `.env.development` file:
- `backend/.env.development` - Backend configuration
- `frontend/.env.development` - Frontend configuration
- `local/keycloak/.env.development` - Keycloak configuration

**Important:** When running `server.py` directly, ensure environment variables from `backend/.env.development` are loaded in your IDE or shell.
