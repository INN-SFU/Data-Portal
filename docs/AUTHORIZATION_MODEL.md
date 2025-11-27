# AMS Data Portal - Authorization Model Analysis

A systematic analysis of authorization mechanisms across all API endpoints and manager operations.

---

## Current State Analysis

### Authorization Mechanisms

The system currently uses TWO distinct authorization mechanisms:

1. **Keycloak Role-Based Authorization**
   - Checked via: `is_user_admin(token_payload)` → looks for "admin" in `realm_access.roles` or `resource_access.{client}.roles`
   - Applied via: `Depends(require_admin)` dependency
   - Scope: **System-wide** - grants access to admin API endpoints

2. **Casbin Policy-Based Authorization**
   - Checked via: `policy_manager.validate_policy(Policy(user_uuid, instance_uuid, resource, action))`
   - Applied via: Manual checks in endpoint code
   - Scope: **Instance/Resource-level** - grants access to specific resources with specific actions
   - Actions: `read`, `write`, `admin`, `list`, `delete`

---

## Endpoint Authorization Matrix

### User Management Endpoints (`/api/users/`)

| Endpoint | Method | Authorization | Notes |
|----------|--------|--------------|-------|
| `/api/users/` | GET | Keycloak Admin | List all users |
| `/api/users/dashboard` | GET | Keycloak Admin | User management dashboard |
| `/api/users/{username}` | GET | Owner OR Keycloak Admin | View user details |
| `/api/users/` | POST | Keycloak Admin | Create user in Keycloak |
| `/api/users/{username}` | DELETE | Owner OR Keycloak Admin | Delete user |

**Manager:** `AbstractUserManager` → `KeycloakUserManager`

**Authorization Model:**
- **Keycloak Admin Role**: Can perform ALL user operations
- **Owner**: Can view/delete own account
- **No Casbin checks**: User operations do NOT check Casbin policies

**Concerns:**
- ✅ Appropriate - user management is system-wide administrative task
- ⚠️ Consider: Should user deletion require additional confirmation for non-owners?

---

### Storage Instance Management Endpoints (`/api/instances/`)

| Endpoint | Method | Authorization | Notes |
|----------|--------|--------------|-------|
| `/api/instances/` | GET | Keycloak Admin | List all instances |
| `/api/instances/{id}` | GET | Keycloak Admin | Get instance details |
| `/api/instances/dashboard` | GET | Keycloak Admin | Instance management dashboard |
| `/api/instances/` | POST | Keycloak Admin | Create instance + grants creator Casbin admin |
| `/api/instances/{id}` | DELETE | Keycloak Admin + Casbin Admin | Delete instance + cleanup policies |

**Manager:** `AbstractInstanceManager` → `InstanceManager`

**Authorization Model:**
- **Keycloak Admin Role**: Required for ALL instance endpoints
- **Casbin Admin Check**: Instance deletion REQUIRES Casbin `admin` action with `.*` resource
- **Side effect on creation**: Creator automatically gets `p, user_uuid, instance_uuid, .*, admin` Casbin policy

**Implementation:**
- ✅ Instance creation: Keycloak admin only (auto-grants creator Casbin admin)
- ✅ Instance deletion: Keycloak admin + must have `p, user_uuid, instance_uuid, .*, admin`
- ✅ Prevents unauthorized deletion by admins without instance-level permissions

---

### Policy Management Endpoints (`/api/policies/`)

| Endpoint | Method | Authorization | Notes |
|----------|--------|--------------|-------|
| `/api/policies/` | GET | Keycloak Admin | List all policies (filterable) |
| `/api/policies/dashboard` | GET | Keycloak Admin | Policy dashboard - shows instances user has Casbin admin on |
| `/api/policies/` | POST | Keycloak Admin + Casbin Admin | Create policy for users on instances where you have admin |
| `/api/policies/` | DELETE | Keycloak Admin + Casbin Admin | Delete policies for instances where you have admin |
| `/api/policies/validate` | POST | Keycloak Admin | Validate policy (check only, no modification) |

**Manager:** `AbstractPolicyManager` → `CasbinPolicyManager`

**Authorization Model:**
- **Keycloak Admin Role**: Required for ALL policy endpoints
- **Casbin Admin Enforcement**: Policy creation/deletion REQUIRE Casbin `admin` action on target instance/resource
- **Dashboard filtering**: Shows only instances where user has Casbin `admin` action

**Implementation:**
- ✅ Policy creation: Keycloak admin + must have `p, admin_uuid, instance_uuid, resource, admin`
- ✅ Policy deletion: Keycloak admin + must have `p, admin_uuid, instance_uuid, resource, admin`
- ✅ Consistent with dashboard: Both filter and enforce based on Casbin admin

**Example Authorization:**
```
Alice (Keycloak admin) with policy: p, alice_uuid, instance_x_uuid, .*, admin

Alice CAN:
- Create policy: p, bob_uuid, instance_x_uuid, data/*, read  ✅
- Delete policy: p, charlie_uuid, instance_x_uuid, reports/*, write  ✅

Alice CANNOT:
- Create policy: p, bob_uuid, instance_y_uuid, .*, read  ❌ (no admin on instance Y)
- Delete policy: p, charlie_uuid, instance_z_uuid, .*, write  ❌ (no admin on instance Z)
```

---

### Asset/File Access Endpoints (`/api/assets/`)

| Endpoint | Method | Authorization | Notes |
|----------|--------|--------------|-------|
| `/api/assets/dashboard` | GET | Keycloak Admin | Asset dashboard - all instances |
| `/api/assets/user-home-data` | GET | Authenticated User | User's accessible instances |
| `/api/assets/user-assets-data` | GET | Authenticated User | User's accessible files (Casbin filtered) |
| `/api/assets/download` | GET | Casbin: `read` | Download file(s) |
| `/api/assets/upload` | PUT | Casbin: `write` | Upload file |
| `/api/assets/delete` | DELETE | Casbin: `delete` | Delete file |

**Manager:** N/A (uses `InstanceManager` + `PolicyManager` + `StorageAgent`)

**Authorization Model:**
- **Keycloak Admin**: Only for dashboard view
- **Casbin policies**: ALL file operations check Casbin (read/write/delete)
- **Proper enforcement**: File access properly restricted by policies

**Status:**
- ✅ **CORRECT**: File operations appropriately use Casbin policies
- ✅ **CONSISTENT**: All file operations check policies before granting access

---

## Manager Governance Specification

### User Manager (`KeycloakUserManager`)

**Governs:**
- User account lifecycle in Keycloak
- User authentication credentials
- User metadata (username, email, etc.)

**Should be restricted by:**
- ✅ Keycloak Admin Role (current implementation)
- ❌ NOT Casbin policies (correct - users are system-wide, not per-instance)

**Operations:**
- `create_user()` - Create user in Keycloak
- `get_user()` - Get user details
- `get_all_users()` - List all users
- `delete_user()` - Delete user from Keycloak
- `get_user_uuid()` - Get user UUID by username

---

### Instance Manager (`InstanceManager`)

**Governs:**
- Storage instance lifecycle
- Storage agent creation/destruction
- Instance configuration persistence

**Should be restricted by:**
- ✅ Keycloak Admin Role (all operations)
- ✅ Casbin `admin` action for instance deletion (IMPLEMENTED)
- ✅ Creation remains Keycloak Admin only (grants creator admin policy)

**Operations:**
- `get_instances()` - List all instances
- `get_instance_by_uuid()` - Get specific instance
- `create_instance()` - Create new instance (grants creator admin policy)
- `delete_instance()` - **Checks Casbin admin with `.*` resource**
- `save_configuration()` - Persist instance config

**Current Authorization:**

| Operation | Keycloak Admin | Casbin Admin (instance-level) |
|-----------|----------------|------------------------------|
| List all instances | ✅ Required | ❌ Not checked |
| View instance details | ✅ Required | ❌ Not checked |
| Create instance | ✅ Required | ❌ Not applicable (auto-grants creator admin) |
| Delete instance | ✅ Required | ✅ **ENFORCED** (requires `.*` resource) |
| Modify instance config | ✅ Required | ⚠️ Not implemented yet |

---

### Policy Manager (`CasbinPolicyManager`)

**Governs:**
- Access control policies (Casbin rules)
- Policy enforcement (validate_policy)
- Policy persistence (user .policies files)

**Should be restricted by:**
- ✅ Keycloak Admin Role (all operations)
- ✅ Casbin `admin` action for policy CRUD (IMPLEMENTED)

**Operations:**
- `add_policy()` - Checks Casbin admin for the instance/resource
- `add_policies()` - Checks Casbin admin for each instance/resource
- `remove_policy()` - Checks Casbin admin for the instance/resource
- `remove_policies()` - Checks Casbin admin for each instance/resource
- `get_instance_policies()` - Returns all policies for instance
- `filter_policies()` - Returns filtered policies
- `validate_policy()` - Checking mechanism (no modification)

**Current Authorization:**

| Operation | Keycloak Admin | Casbin Admin (instance/resource-level) |
|-----------|----------------|----------------------------------------|
| List policies | ✅ Required | ❌ Not filtered (returns all) |
| View policy dashboard | ✅ Required | ✅ Filters by admin access |
| Create policy | ✅ Required | ✅ **ENFORCED** (for target instance/resource) |
| Delete policy | ✅ Required | ✅ **ENFORCED** (for target instance/resource) |
| Validate policy | ✅ Required | ❌ Not checked (OK - just validation, no modification) |

---

## Casbin Admin Action Semantics

### Current Implementation

The Casbin `admin` action is used for:
1. ✅ Filtering instances shown in `/api/policies/dashboard`
2. ✅ Filtering resources shown in policy management UI
3. ❌ NOT enforced for policy CRUD operations
4. ❌ NOT enforced for instance deletion

### Current Implementation (After Security Fix)

**Casbin `admin` action grants:**
- ✅ Ability to create policies for resources matching the pattern
- ✅ Ability to delete policies for resources matching the pattern
- ✅ Ability to delete the instance (if pattern is `.*`)
- ✅ Ability to modify instance configuration (if pattern is `.*`)
- ❌ Does NOT grant file read/write/delete access

**Example:**
```
p, alice_uuid, instance_x_uuid, .*, admin
```
Alice can:
- ✅ Create/delete policies for ANY resource on instance X
- ✅ Delete instance X
- ✅ View instance X configuration
- ❌ Read/write/delete files on instance X (needs separate read/write policies)

```
p, bob_uuid, instance_y_uuid, data/reports/.*, admin
```
Bob can:
- ✅ Create/delete policies for resources under `data/reports/`
- ❌ Delete instance Y (doesn't have admin on `.*`)
- ❌ Create policies for `data/uploads/` (doesn't match pattern)

---

## System Admin vs Instance Admin

### System Admin (Keycloak Role)

**Who:** Users with "admin" in `realm_access.roles` or `resource_access.{client}.roles`

**Can do:**
- ✅ Create/delete users (Keycloak operations)
- ✅ Create storage instances
- ✅ View all instances (system-wide visibility)
- ✅ View all policies (system-wide visibility)
- ⚠️ **PROPOSED RESTRICTION**: Cannot modify/delete instances without Casbin admin
- ⚠️ **PROPOSED RESTRICTION**: Cannot create/delete policies without Casbin admin for target instance

**Purpose:** System administration and initial setup

### Instance Admin (Casbin Policy)

**Who:** Users with `action='admin'` in Casbin policy for an instance

**Can do:**
- ✅ Create/delete policies for resources they have admin on
- ✅ Delete instances they have `.*` admin pattern on
- ✅ Manage access for other users to their instance
- ❌ Cannot create users (Keycloak operation)
- ❌ Cannot create new instances (system-level operation)

**Purpose:** Delegated instance/resource management

---

## Recommended Authorization Flow

### Instance Creation
```
1. User requests: POST /api/instances/
2. Check: Keycloak Admin role? ✅
3. Create instance
4. Auto-grant: p, creator_uuid, instance_uuid, .*, admin
5. Result: Creator becomes instance admin
```

### Instance Deletion
```
1. User requests: DELETE /api/instances/{uuid}
2. Check: Keycloak Admin role? ✅
3. NEW: Check Casbin: p, user_uuid, instance_uuid, .*, admin? ✅
4. Delete instance
5. Cleanup all policies for instance
```

### Policy Creation
```
1. User requests: POST /api/policies/ {user: bob, instance: X, resource: data/*, action: read}
2. Check: Keycloak Admin role? ✅
3. NEW: Check Casbin: Does requester have admin on instance X, resource data/*? ✅
4. Create policy
```

### Policy Deletion
```
1. User requests: DELETE /api/policies/ {user: bob, instance: X, resource: data/*, action: read}
2. Check: Keycloak Admin role? ✅
3. NEW: Check Casbin: Does requester have admin on instance X, resource data/*? ✅
4. Delete policy
```

### File Access (Already Correct)
```
1. User requests: GET /api/assets/download?instance=X&resource=data/file.txt
2. Check: Valid JWT? ✅
3. Check Casbin: p, user_uuid, instance_uuid, data/file.txt, read? ✅
4. Generate presigned URL
```

---

## Security Concerns Summary

### Critical Issues

1. ✅ **Instance Deletion Bypass** - FIXED
   - ~~Any Keycloak admin can delete ANY instance~~
   - Now requires Casbin `admin` action with `.*` resource pattern on instance

2. ✅ **Policy Management Bypass** - FIXED
   - ~~Any Keycloak admin can create/delete policies for ANY instance~~
   - Now requires Casbin `admin` action on instance/resource being managed

### Medium Issues

3. ✅ **Inconsistent Authorization Model** - FIXED
   - ~~Dashboard filters by Casbin admin~~
   - ~~CRUD operations ignore Casbin admin~~
   - Now consistent: Both dashboard AND CRUD operations check Casbin admin

4. ✅ **Privilege Escalation Risk** - FIXED
   - ~~Keycloak admin can grant themselves policies without instance-level permission~~
   - ~~Example: Alice (admin) creates: `p, alice_uuid, bob_instance, .*, read`~~
   - Now prevented: Alice must have Casbin admin on bob_instance to create policies for it

---

## Implementation Summary

### ✅ Phase 1: Add Casbin Checks to Instance Operations - COMPLETED

**Implementation:** `/backend/api/v0_1/endpoints/service/instances.py`

Instance deletion now requires:
- Keycloak Admin role (existing)
- Casbin `admin` action with `.*` resource pattern on the instance (NEW)

```python
# instances.py - delete_instance() - lines 275-287
admin_uuid = UUID(admin_user.get("sub"))
admin_check = Policy(
    user_uuid=admin_uuid,
    instance_uuid=instance_uuid,
    resource='.*',
    action='admin'
)
if not policy_manager.validate_policy(admin_check):
    raise HTTPException(
        status_code=403,
        detail=f"You must have admin access to instance '{instance.name}' to delete it"
    )
```

### ✅ Phase 2: Add Casbin Checks to Policy Operations - COMPLETED

**Implementation:** `/backend/api/v0_1/endpoints/service/policies.py`

Policy creation and deletion now require:
- Keycloak Admin role (existing)
- Casbin `admin` action on the target instance/resource (NEW)

```python
# policies.py - create_policy() - lines 123-135
admin_uuid = admin_user.get("sub")
admin_check = Policy(
    user_uuid=admin_uuid,
    instance_uuid=policy.instance_uuid,
    resource=policy.resource,
    action='admin'
)
if not policy_manager.validate_policy(admin_check):
    raise HTTPException(
        status_code=403,
        detail=f"You must have admin access to instance/resource '{policy.resource}' to create policies for it"
    )

# policies.py - delete_policy() - lines 199-211
# Same implementation as above
```

### 🔄 Phase 3: Update Documentation - IN PROGRESS

**Status:** Partially complete

- ✅ AUTHORIZATION_MODEL.md - Updated with implementation status
- ⏳ GLOSSARY.md - Needs update to reflect enforced Casbin checks
- ⏳ Sequence diagrams - Need to show Casbin checks in policy/instance operations

### 💡 Phase 4: Consider Superadmin Role - FUTURE CONSIDERATION

**Priority:** LOW
**Impact:** Allows escape hatch for emergency operations

Consider adding a "superadmin" role that:
- Bypasses Casbin checks (Keycloak admin + special flag)
- Used only for emergency recovery
- Logged separately for audit

**Note:** Not implemented in this security fix. Can be added later if needed.

---

## Testing Checklist

After implementing Casbin checks:

- [ ] Keycloak admin WITHOUT Casbin admin cannot delete instance
- [ ] Keycloak admin WITH Casbin admin CAN delete instance
- [ ] Keycloak admin WITHOUT Casbin admin cannot create policies for instance
- [ ] Keycloak admin WITH Casbin admin CAN create policies for instance
- [ ] Instance creator automatically gets admin policy
- [ ] File operations still work with read/write policies
- [ ] Dashboard still shows only instances user has admin on

---

**Last Updated:** 2025-01-27
**Status:** ✅ IMPLEMENTED - Casbin checks now enforced
