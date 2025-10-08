# AMS Storage Gateway Service

Validates JWT tokens and streams files from POSIX filesystem.

## Overview

The Storage Gateway validates JWT tokens issued by the Storage Issuer and streams files from a POSIX filesystem. It enforces single-use tokens, supports HTTP Range requests, and can stream files, generate manifests, or create ZIP archives.

**Key Features:**
- JWT token validation using Issuer's JWKS
- Single-use token enforcement via Redis
- File streaming with HTTP Range support
- JSON manifest generation for folders
- On-the-fly ZIP compression for folder downloads
- Path validation (prevents directory traversal)
- IP pinning support (optional)

## Architecture

```
User → Storage Gateway (this service)
         ↓
         Validates JWT via Issuer's JWKS
         ↓
         Checks jti in Redis (single-use)
         ↓
         Streams file from POSIX filesystem
```

## API Endpoints

### GET /api/download?token={jwt}

Download file or folder using JWT token.

**Query Parameters:**
- `token` (required): JWT token from Storage Issuer

**Response Types (based on token's `bundle` claim):**
- **`bundle=file`** (default): Stream single file with HTTP Range support
- **`bundle=manifest`**: JSON listing of folder contents
- **`bundle=zip`**: ZIP archive of folder (streamed on-the-fly)

**Example:**
```bash
# Download single file
curl "http://localhost:9000/api/download?token=eyJhbGci..." -o file.txt

# Download with Range support (resume/seek)
curl "http://localhost:9000/api/download?token=eyJhbGci..." \
  -H "Range: bytes=0-1023" -o partial.txt

# Get folder manifest (JSON)
curl "http://localhost:9000/api/download?token=eyJhbGci..." | jq

# Download folder as ZIP
curl "http://localhost:9000/api/download?token=eyJhbGci..." -o folder.zip
```

### GET /api/health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "checks": {
    "jwt_validator": true,
    "jti_tracker": true,
    "file_streamer": true,
    "manifest_generator": true,
    "zip_streamer": true
  }
}
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `GATEWAY_HOST` | `0.0.0.0` | Service bind address |
| `GATEWAY_PORT` | `9000` | Service port |
| `LOG_LEVEL` | `INFO` | Logging level |
| `STORAGE_ROOT_PATH` | `/storage` | Root directory for file access |
| `JWKS_URL` | `http://storage-issuer:8001/.well-known/jwks.json` | Issuer's JWKS endpoint |
| `JWT_ISSUER` | `ams-storage-issuer` | Expected issuer claim (must match Issuer) |
| `JWT_AUDIENCE` | `ams-storage-gateway` | Expected audience claim (must match Issuer) |
| `JWKS_CACHE_TTL` | `3600` | JWKS cache TTL in seconds |
| `REDIS_HOST` | `localhost` | Redis server hostname |
| `REDIS_PORT` | `6379` | Redis server port |
| `REDIS_DB` | `0` | Redis database number |
| `REDIS_PASSWORD` | (none) | Redis password (optional) |

**IMPORTANT:** `JWT_ISSUER` and `JWT_AUDIENCE` must match the Storage Issuer configuration exactly.

## Token Validation Flow

1. **Extract JWT** from query parameter
2. **Fetch JWKS** from Issuer (cached)
3. **Validate signature** using public key
4. **Check expiration** (`exp` claim)
5. **Check audience** (`aud` claim must match `JWT_AUDIENCE`)
6. **Check issuer** (`iss` claim must match `JWT_ISSUER`)
7. **Validate claims** (path, op, jti present)
8. **Check client IP** (if `cip` claim present)
9. **Check jti** in Redis (replay prevention)
10. **Mark jti as used** in Redis with TTL
11. **Validate path** (prevent directory traversal)
12. **Stream file** from POSIX filesystem

## Security

- **JWT validation**: Validates signature, expiration, audience, issuer
- **Single-use tokens**: Redis jti tracking prevents replay attacks
- **Path validation**: Prevents directory traversal (`../` attacks)
- **IP pinning**: Optional client IP validation via `cip` claim
- **Read-only filesystem**: Docker mount in read-only mode
- **No private key**: Gateway only has public key (cannot forge tokens)

## Development

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r tests/requirements-test.txt

# Set environment variables
export STORAGE_ROOT_PATH=/path/to/storage
export JWKS_URL=http://localhost:8001/.well-known/jwks.json
export REDIS_HOST=localhost

# Run server
python server.py
```

### Running with Docker

```bash
# Build and start (includes Redis)
docker compose up -d --build

# View logs
docker compose logs -f

# Stop
docker compose down
```

### Running Tests

```bash
pip install -r requirements.txt -r tests/requirements-test.txt
python -m pytest tests/ -v
```

## Token Claims

Tokens must contain these claims:

```json
{
  "iss": "ams-storage-issuer",       // Issuer (must match config)
  "aud": "ams-storage-gateway",      // Audience (must match config)
  "sub": "user-uuid",                 // User UUID
  "exp": 1728394496,                  // Expiration (Unix timestamp)
  "iat": 1728390896,                  // Issued at
  "jti": "unique-id",                 // Token ID (for replay prevention)
  "path": "folder/file.txt",          // Resource path (locked)
  "op": "read",                       // Operation (must be "read")
  "bundle": "file",                   // Download type (file|manifest|zip)
  "cip": "192.168.1.100",            // Client IP (optional, for IP pinning)
  "iid": "instance-uuid"              // Instance UUID (optional)
}
```

## Bundle Types

### bundle=file (Default)
- Streams single file
- Supports HTTP Range requests (206 Partial Content)
- Use for: Single file downloads, video streaming, resume support

### bundle=manifest
- Returns JSON list of files in folder
- Includes file metadata (size, modified time)
- Use for: File browsers, folder exploration

### bundle=zip
- Streams folder as ZIP archive on-the-fly
- Compresses files without loading entire folder in memory
- Use for: Folder downloads, batch downloads

## HTTP Range Support

Gateway supports HTTP Range requests for `bundle=file`:

```bash
# Download first 1KB
curl "http://localhost:9000/api/download?token=..." \
  -H "Range: bytes=0-1023"

# Download last 500 bytes
curl "http://localhost:9000/api/download?token=..." \
  -H "Range: bytes=-500"

# Download from byte 1000 to end
curl "http://localhost:9000/api/download?token=..." \
  -H "Range: bytes=1000-"
```

## Integration with Storage Issuer

Gateway fetches public keys from Issuer's JWKS endpoint:

```
Storage Issuer (http://storage-issuer:8001)
  ↓ (provides)
/.well-known/jwks.json (public key)
  ↓ (fetched by)
Storage Gateway
  ↓ (validates tokens)
User downloads
```

**Configuration Coordination:**
- Gateway's `JWKS_URL` must point to Issuer's JWKS endpoint
- Gateway's `JWT_ISSUER` must match Issuer's `JWT_ISSUER`
- Gateway's `JWT_AUDIENCE` must match Issuer's `JWT_AUDIENCE`

## Deployment

### Development (Single Host)
```bash
# Start Storage Issuer
cd storage-issuer
docker compose up -d

# Start Storage Gateway
cd storage-gateway
docker compose up -d
```

### Production (Distributed)
Deploy Gateway on storage server with filesystem access:

```yaml
# storage-gateway on storage server
volumes:
  - /mnt/storage:/storage:ro  # Read-only mount

environment:
  JWKS_URL: https://issuer.domain.com/.well-known/jwks.json
  JWT_ISSUER: ams-storage-issuer
  JWT_AUDIENCE: ams-storage-gateway
  REDIS_HOST: redis.domain.com
```

## Monitoring

### Logs
Structured logging with request context:
```
2025-10-08 12:34:56 - storage-gateway.api.download - INFO - Token validated
  Extra: {"jti": "abc-123", "user": "user-uuid", "path": "file.txt", "op": "read"}
```

### Health Check
```bash
curl http://localhost:9000/api/health
```

## Troubleshooting

### "Invalid token signature"
- Check `JWKS_URL` points to correct Issuer
- Verify Issuer is running and JWKS endpoint is accessible
- Check network connectivity between Gateway and Issuer

### "Invalid token audience" or "Invalid token issuer"
- Verify `JWT_ISSUER` and `JWT_AUDIENCE` match between Gateway and Issuer
- Check environment variables are set correctly

### "Token has already been used"
- Token was already used (jti in Redis)
- This is expected behavior (single-use enforcement)
- Request new token from Backend

### "File not found"
- Check `STORAGE_ROOT_PATH` is correct
- Verify file exists at path specified in token
- Check filesystem permissions

### Redis connection failed
- Verify Redis is running
- Check `REDIS_HOST` and `REDIS_PORT` are correct
- Verify network connectivity to Redis

## API Documentation

Interactive API docs available at:
- Swagger UI: http://localhost:9000/docs
- ReDoc: http://localhost:9000/redoc
