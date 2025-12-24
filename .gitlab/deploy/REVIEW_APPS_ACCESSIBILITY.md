# Review Apps Accessibility Analysis

## Question: Do all Nomad deployed jobs need to be accessible to Review Apps?

**Answer: Yes, for testing purposes.**

All services deployed in a Review App environment should be accessible via the web (Traefik) to enable:
- End-to-end testing of the full stack
- Direct API testing (bypassing frontend)
- Service-specific testing
- Debugging and troubleshooting

## Current Implementation Analysis

### Services Deployed
Based on `.gitlab/backend.yaml`, the following services are deployed:
1. **data-service** - Backend data service
2. **api-gateway** - API gateway service  
3. **frontend** - Frontend application

### Environment Detection

The current implementation correctly detects Review Apps:

```bash
if [ -n "$CI_MERGE_REQUEST_IID" ]; then
  NOMAD_ENVIRONMENT="review"
  NOMAD_ENVIRONMENT_NAME="review-pr-${CI_MERGE_REQUEST_IID}"
elif [ "$CI_COMMIT_BRANCH" = "$CI_DEFAULT_BRANCH" ]; then
  # production
elif [ "$CI_COMMIT_BRANCH" = "development" ]; then
  # development
elif [ "$CI_COMMIT_BRANCH" = "staging" ]; then
  # staging
else
  # Feature branches → review
  NOMAD_ENVIRONMENT="review"
  NOMAD_ENVIRONMENT_NAME="review-${CI_COMMIT_REF_SLUG}"
fi
```

✅ **All Review App scenarios are covered:**
- Merge Requests: `review-pr-123` (hyphenated)
- Feature branches: `review-feature-branch-name` (hyphenated)

### Accessibility Logic

**Frontend Services:**
- ✅ Always get Traefik tags (external access)
- ✅ Hostname: `frontend-${CI_COMMIT_REF_SLUG}.domain.com`
- ✅ URL: `https://frontend-feature-branch.domain.com`

**Backend Services in Review Apps:**
- ✅ Get Traefik tags (external access for testing)
- ✅ Hostname: `${SERVICE_NAME}-${CI_COMMIT_REF_SLUG}.domain.com`
- ✅ Examples:
  - `data-service-feature-branch.domain.com`
  - `api-gateway-feature-branch.domain.com`
- ✅ URL: `https://${SERVICE_NAME}-feature-branch.domain.com`

**Backend Services in Production/Staging/Development:**
- ✅ Simple tags `["api"]` (internal service discovery only)
- ✅ No external access (security best practice)

## Issues Fixed

### 1. Environment Naming Convention

**Requirement:** Review Apps should be hyphenated: `review-<branch-name>` (not `review/pr-123`)

**Implementation:**
- Merge Requests: `review-pr-123` (hyphenated)
- Feature branches: `review-feature-branch-name` (hyphenated)

**Impact:**
- Router names: `data-service-review-pr-123` (valid, no slashes)
- Hostnames: `data-service-feature-branch.domain.com` (unchanged, already valid)
- Environment names are already safe for Traefik (no sanitization needed)

### 2. All Services Get External Access in Review Apps

**Current Behavior:**
- ✅ Frontend: Always external
- ✅ Backend in Review: External (for testing)
- ✅ Backend in Production/Staging/Dev: Internal only

**This ensures:**
- All Review App services are accessible via web
- Each service gets its own unique hostname
- Production services remain secure (internal only)

## Hostname Generation

For Review Apps, each service gets a unique hostname:

| Service | Environment | Hostname Pattern | Example |
|---------|------------|------------------|---------|
| frontend | review-pr-123 | `frontend-${CI_COMMIT_REF_SLUG}.domain` | `frontend-feature-branch.domain.com` |
| data-service | review-pr-123 | `data-service-${CI_COMMIT_REF_SLUG}.domain` | `data-service-feature-branch.domain.com` |
| api-gateway | review-pr-123 | `api-gateway-${CI_COMMIT_REF_SLUG}.domain` | `api-gateway-feature-branch.domain.com` |

**Note:** `CI_COMMIT_REF_SLUG` is the branch name sanitized for URLs (lowercase, special chars replaced with `-`).

## Traefik Routing Rules

Each service gets unique Traefik routing:

**Frontend:**
```
Host(`frontend-feature-branch.domain.com`)
```

**Backend Services (Review Apps):**
```
Host(`data-service-feature-branch.domain.com`) || PathPrefix(`/api/review-feature-branch`)
```

This allows:
- Direct hostname access: `https://data-service-feature-branch.domain.com`
- Path-based access: `https://frontend-feature-branch.domain.com/api/review-feature-branch`

## Verification Checklist

✅ All services in Review Apps get Traefik tags
✅ Each service gets unique hostname
✅ Environment names use hyphens (no slashes) - safe for Traefik
✅ Review Apps are accessible via web
✅ Production/Staging/Dev backends remain internal only
✅ Environment detection covers all scenarios (MR, feature branches)
✅ Naming convention: `review-<branch-name>` (hyphenated)

## Summary

**Yes, the current implementation ensures all Review App services are accessible via www:**

1. ✅ Environment detection correctly identifies Review Apps
2. ✅ All services (frontend + backend) get Traefik tags in Review Apps
3. ✅ Each service gets a unique hostname
4. ✅ Traefik router names are sanitized (no slashes)
5. ✅ All services are accessible via HTTPS

The implementation properly distinguishes between:
- **Review Apps**: Full external access for testing
- **Production/Staging/Dev**: Frontend external, backend internal (secure)

