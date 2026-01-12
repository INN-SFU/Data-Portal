# Nomad + Auto DevOps Integration - Implementation Plan

## Executive Summary

This document outlines the plan to integrate HashiCorp Nomad with GitLab Auto DevOps, enabling deployment to Nomad while maintaining compatibility with future Kubernetes support.

## Approach Analysis

### Option A: Override Auto DevOps Deploy Jobs
**Pros:**
- Simple, direct replacement
- Minimal code duplication

**Cons:**
- Loses Auto DevOps deploy features
- Hard to support both K8s and Nomad
- Less flexible for future changes

### Option B: Parallel Jobs (Disable K8s)
**Pros:**
- Can run alongside Auto DevOps
- Easy to enable/disable

**Cons:**
- Doesn't leverage Auto DevOps deploy infrastructure
- Duplicates environment management
- More complex pipeline

### Option C: Reusable Templates (SELECTED)
**Pros:**
- ✅ Extends Auto DevOps, maintains compatibility
- ✅ Can run parallel with K8s in future
- ✅ Reusable across projects
- ✅ Leverages Auto DevOps environment management
- ✅ Minimal divergence from standard Auto DevOps

**Cons:**
- Requires understanding Auto DevOps internals
- More initial setup complexity

**Decision: Option C** - We'll create reusable templates that extend Auto DevOps jobs, allowing us to override the deploy stage while maintaining compatibility.

## Architecture Design

### 1. Template Structure

```
.gitlab/deploy/
├── Deploy.nomad.gitlab-ci              # Main CI template (extends Auto DevOps)
├── nomad-templates/              # Nomad job specs
│   ├── base-service.template.nomad   # Base template
│   ├── frontend.template.nomad        # Frontend template
│   └── backend.template.nomad         # Backend template
└── scripts/
    ├── deploy-nomad.sh           # Deployment logic
    └── cleanup-review-app.sh     # Cleanup logic
```

### 2. Job Flow

```
Auto DevOps Pipeline:
├── build (unchanged) ✅
├── test (unchanged) ✅
├── security (unchanged) ✅
└── deploy (OVERRIDDEN)
    ├── .nomad-deploy-base       # Base job template
    ├── deploy:nomad:review       # Review Apps
    ├── deploy:nomad:development  # Development
    ├── deploy:nomad:staging      # Staging
    └── deploy:nomad:production   # Production
```

### 3. Environment Mapping Logic

```yaml
# Pseudo-logic
if $CI_MERGE_REQUEST_IID:
  ENVIRONMENT = "review"
  ENVIRONMENT_NAME = "review/pr-${CI_MERGE_REQUEST_IID}"
elif $CI_COMMIT_BRANCH == "main":
  ENVIRONMENT = "production"
  ENVIRONMENT_NAME = "production"
elif $CI_COMMIT_BRANCH == "development":
  ENVIRONMENT = "development"
  ENVIRONMENT_NAME = "development"
elif $CI_COMMIT_BRANCH == "staging":
  ENVIRONMENT = "staging"
  ENVIRONMENT_NAME = "staging"
else:
  ENVIRONMENT = "review"
  ENVIRONMENT_NAME = "review/${CI_COMMIT_REF_SLUG}"
```

### 4. Review Apps Strategy

**Naming Convention:**
- `review-pr-<MR_ID>` for merge requests (hyphenated)
- `review-<branch-name>` for feature branches (hyphenated)
- Uses hyphens, not slashes (e.g., `review-pr-123`, not `review/pr-123`)

**Cleanup Strategy:**
- Auto-stop on MR close (GitLab native)
- Auto-stop on MR merge (GitLab native)
- Manual cleanup via `stop_review_app` job
- Time-based cleanup (future enhancement)

**Routing:**
- Dynamic subdomain: `${SERVICE}-${ENVIRONMENT}.domain.com`
- Path-based: `domain.com/${ENVIRONMENT}/${SERVICE}`
- Traefik tags in Nomad service block

### 5. Health Checks & Monitoring

**Health Checks:**
- Nomad service health checks (HTTP/TCP)
- Readiness probes with retry logic
- Startup delay configuration

**Monitoring Placeholders:**
- Prometheus metrics endpoint configuration
- Grafana dashboard references
- Per-environment monitoring isolation

## Implementation Steps

### Phase 1: Core Infrastructure ✅
1. Create directory structure
2. Create base Nomad deployment template
3. Create environment mapping logic
4. Create deployment script

### Phase 2: Review Apps
1. Implement Review App naming logic
2. Create cleanup jobs
3. Configure Traefik routing
4. Test Review App lifecycle

### Phase 3: Health & Monitoring
1. Add health checks to Nomad templates
2. Create monitoring placeholders
3. Configure Prometheus integration points
4. Document Grafana setup

### Phase 4: Integration
1. Update frontend CI to use templates
2. Update backend CI to use templates
3. Test all environments
4. Document usage

### Phase 5: Future Enhancements
1. Kubernetes parallel support
2. Advanced monitoring
3. Multi-region support

## Key Design Decisions

### 1. Variable Naming Convention

We use `__VARIABLE__` prefix for `envsubst` variables to avoid conflicts:
- `${__SERVICE__}` - Service name (frontend/backend)
- `${__ENVIRONMENT__}` - Environment name (review/pr-123, production, etc.)
- `${__IMAGE_NAME__}` - Full image name
- `${__IMAGE_TAG__}` - Image tag
- `${__HOSTNAME__}` - Traefik hostname

### 2. Template Inheritance

```yaml
.nomad-deploy-base:
  extends: .deploy  # Extends Auto DevOps deploy job
  # Override script, keep other features
```

### 3. Environment Variables

**Required (secrets):**
- `NOMAD_SERVER_ADDRESS`
- `NOMAD_SERVER_TOKEN`
- `NOMAD_NAMESPACE`

**Optional (with defaults):**
- `NOMAD_DATACENTERS` (default: `["dc1"]`)
- `NOMAD_DEPLOY_ENABLED` (default: `"true"`)
- `SERVICE_NAME` (required per service)

### 4. Compatibility with Kubernetes

Future Kubernetes support will:
- Use same environment mapping logic
- Share environment variables
- Run in parallel (different job names)
- Use same Review Apps infrastructure

## Testing Strategy

1. **Unit Tests:**
   - Environment mapping logic
   - Template variable substitution
   - Script validation

2. **Integration Tests:**
   - Review App creation
   - Review App cleanup
   - Multi-environment deployment

3. **Manual Tests:**
   - Deploy to each environment
   - Verify Traefik routing
   - Check health endpoints
   - Test cleanup jobs

## Risk Mitigation

1. **Auto DevOps Updates:**
   - Monitor Auto DevOps template changes
   - Version pin templates if needed
   - Test after GitLab updates

2. **Nomad Cluster Issues:**
   - Implement retry logic
   - Add health checks before deploy
   - Graceful failure handling

3. **Review App Cleanup:**
   - Multiple cleanup triggers
   - Manual cleanup job
   - Monitoring for orphaned apps

## Success Criteria

- ✅ Deploy to Nomad from Auto DevOps pipeline
- ✅ Review Apps work for all PRs
- ✅ Automatic cleanup of Review Apps
- ✅ Health checks functional
- ✅ Monitoring placeholders in place
- ✅ Reusable across projects
- ✅ Compatible with future K8s support

## Next Steps

1. Review and approve this plan
2. Implement Phase 1 (Core Infrastructure)
3. Test with a single service
4. Iterate based on feedback
5. Roll out to all services

