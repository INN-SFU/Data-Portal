# Local Development

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
