# Storage Access Sequence Diagrams

## File Download Flow (S3)

Complete flow for downloading a file from S3-compatible storage.

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant Backend
    participant Casbin
    participant S3Agent
    participant S3Storage

    User->>Frontend: Click Download File
    Frontend->>Backend: GET /api/asset/download<br/>Bearer {token}<br/>instance_name={name}&resource=data/file.txt

    Backend->>Backend: Validate JWT Token
    Backend->>Backend: Extract User Claims<br/>(user_id, roles)

    Backend->>Casbin: enforce(user_id, instance_uuid, read)
    Note over Casbin: Check Policy Rules:<br/>p, user_id, instance_uuid, .*, read

    alt Access Allowed
        Casbin->>Backend: true (ALLOW)

        Backend->>S3Agent: generate_access_link()<br/>(instance_uuid, path, "read")

        S3Agent->>S3Agent: Load Instance Config<br/>(bucket, credentials, region)
        S3Agent->>S3Agent: Validate Path<br/>(no directory traversal)

        S3Agent->>S3Agent: Generate Presigned URL<br/>boto3.generate_presigned_url()<br/>TTL=3600s

        S3Agent->>Backend: {url, expires_in: 3600}

        Backend->>Frontend: 200 OK<br/>{download_url, expires_at}

        Frontend->>User: Trigger Download<br/>(window.location or fetch)

        User->>S3Storage: GET {presigned_url}

        S3Storage->>S3Storage: Validate Signature<br/>(AWS SDK verification)
        S3Storage->>S3Storage: Check Expiration

        S3Storage->>User: File Stream<br/>(Content-Type, Content-Length)

    else Access Denied
        Casbin->>Backend: false (DENY)
        Backend->>Frontend: 403 Forbidden<br/>Access denied
        Frontend->>User: Show Error Message
    end
```

## File Upload Flow (S3)

Complete flow for uploading a file to S3-compatible storage.

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant Backend
    participant Casbin
    participant S3Agent
    participant S3Storage

    User->>Frontend: Select File to Upload
    Frontend->>Backend: PUT /api/asset/upload<br/>Bearer {token}<br/>instance_name={name}&resource=data/newfile.txt

    Backend->>Backend: Validate JWT Token
    Backend->>Casbin: enforce(user_id, instance_uuid, write)

    alt Write Allowed
        Casbin->>Backend: true (ALLOW)

        Backend->>S3Agent: generate_upload_link()<br/>(instance_uuid, path, "write")

        S3Agent->>S3Agent: Load Instance Config
        S3Agent->>S3Agent: Validate Destination Path

        S3Agent->>S3Agent: Generate Presigned POST<br/>boto3.generate_presigned_post()<br/>TTL=900s<br/>max_size=100MB

        S3Agent->>Backend: {upload_url, fields, conditions}

        Backend->>Frontend: 200 OK<br/>{upload_url, fields}

        Frontend->>Frontend: Prepare FormData<br/>(file + fields)

        Frontend->>S3Storage: POST {upload_url}<br/>multipart/form-data

        S3Storage->>S3Storage: Validate Signature<br/>Check Conditions<br/>(size, content-type)

        alt Upload Valid
            S3Storage->>S3Storage: Store File
            S3Storage->>Frontend: 204 No Content<br/>ETag: {file_hash}

            Frontend->>Backend: POST /api/asset/upload/confirm<br/>{instance_uuid, path, etag}

            Backend->>Backend: Log Upload<br/>(audit trail)

            Backend->>Frontend: 200 OK<br/>Upload confirmed

            Frontend->>User: Upload Complete<br/>Success Message

        else Upload Invalid
            S3Storage->>Frontend: 400 Bad Request<br/>Invalid conditions
            Frontend->>User: Upload Failed
        end

    else Write Denied
        Casbin->>Backend: false (DENY)
        Backend->>Frontend: 403 Forbidden
        Frontend->>User: Access Denied
    end
```

## File Tree Loading

Loading directory structure from storage backend.

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant Backend
    participant Casbin
    participant S3Agent
    participant S3Storage

    User->>Frontend: Navigate to Storage Instance
    Frontend->>Backend: GET /api/asset/user-assets-data<br/>Bearer {token}

    Backend->>Backend: Validate JWT Token
    Backend->>Casbin: enforce(user_id, instance_uuid, list)

    alt List Allowed
        Casbin->>Backend: true (ALLOW)

        Backend->>S3Agent: load_file_tree()<br/>(instance_uuid)

        S3Agent->>S3Agent: Get Instance Config<br/>(bucket, prefix)

        loop Paginated Listing
            S3Agent->>S3Storage: list_objects_v2()<br/>Bucket={bucket}<br/>Prefix={prefix}<br/>MaxKeys=1000

            S3Storage->>S3Agent: Object List<br/>{objects[], is_truncated}

            S3Agent->>S3Agent: Build File Tree<br/>(parse keys, create hierarchy)

            alt More Objects
                S3Agent->>S3Agent: Store ContinuationToken
            end
        end

        S3Agent->>S3Agent: Apply Resource Filters<br/>(Casbin resource patterns)

        S3Agent->>Backend: FileTree<br/>{folders[], files[]}

        Backend->>Frontend: 200 OK<br/>{file_tree, metadata}

        Frontend->>Frontend: Render Tree View
        Frontend->>User: Display Files/Folders

    else List Denied
        Casbin->>Backend: false (DENY)
        Backend->>Frontend: 403 Forbidden
        Frontend->>User: Access Denied
    end
```

## Folder Download (ZIP)

Downloading an entire folder as a ZIP archive.

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant Backend
    participant Casbin
    participant S3Agent
    participant S3Storage

    User->>Frontend: Click Download Folder
    Frontend->>Backend: GET /api/asset/download-folder<br/>Bearer {token}<br/>instance_name={name}&resource=data/reports/

    Backend->>Backend: Validate JWT Token
    Backend->>Casbin: enforce(user_id, instance_uuid, read)

    alt Access Allowed
        Casbin->>Backend: true (ALLOW)

        Backend->>S3Agent: list_folder_contents()<br/>(instance_uuid, path)

        S3Agent->>S3Storage: list_objects_v2()<br/>Prefix=data/reports/

        S3Storage->>S3Agent: Object Keys[]

        S3Agent->>S3Agent: Filter Accessible Files<br/>(apply resource patterns)

        S3Agent->>Backend: File List[]

        loop For Each File
            Backend->>S3Agent: generate_access_link()<br/>(file_path)
            S3Agent->>Backend: Presigned URL
        end

        Backend->>Frontend: 200 OK<br/>{files: [{path, url}]}

        Frontend->>Frontend: Initialize ZIP Stream<br/>(JSZip library)

        loop For Each File URL
            Frontend->>S3Storage: GET {presigned_url}
            S3Storage->>Frontend: File Data Stream
            Frontend->>Frontend: Add to ZIP Archive
        end

        Frontend->>Frontend: Finalize ZIP
        Frontend->>User: Download folder.zip
    end
```

## Storage Instance Creation

Admin creating a new storage instance.

```mermaid
sequenceDiagram
    actor Admin
    participant Frontend
    participant Backend
    participant Casbin
    participant InstanceMgr
    participant S3Agent
    participant PolicyMgr

    Admin->>Frontend: Fill Instance Form<br/>(name, bucket, credentials)
    Frontend->>Backend: POST /api/admin/instances/<br/>Bearer {token}<br/>{flavour: "s3", config: {...}}

    Backend->>Backend: Validate Admin Token
    Backend->>Casbin: enforce(admin_id, admin, create_instance)
    Casbin->>Backend: true (ALLOW)

    Backend->>Backend: Generate instance_uuid<br/>uuid5(NAMESPACE_DNS, name)

    Backend->>S3Agent: Validate Configuration<br/>(test connection)

    S3Agent->>S3Storage: list_buckets()<br/>(test credentials)

    alt Connection Valid
        S3Storage->>S3Agent: Bucket List
        S3Agent->>Backend: Configuration Valid

        Backend->>InstanceMgr: create_instance()<br/>(uuid, name, config, agent)

        InstanceMgr->>InstanceMgr: Add to Instances List
        InstanceMgr->>InstanceMgr: Save Config JSON<br/>(configs/{uuid}.json)

        Backend->>PolicyMgr: add_policy()<br/>(admin_id, instance_uuid, .*, admin)

        PolicyMgr->>Casbin: Add Policy Rule
        Casbin->>PolicyMgr: Policy Added

        Backend->>Frontend: 201 Created<br/>{instance_uuid, name}
        Frontend->>Admin: Instance Created

    else Connection Invalid
        S3Storage->>S3Agent: 403 Forbidden
        S3Agent->>Backend: Invalid Credentials
        Backend->>Frontend: 400 Bad Request<br/>Invalid S3 configuration
        Frontend->>Admin: Error Message
    end
```

## Storage Instance Deletion

Admin deleting a storage instance and associated policies.

```mermaid
sequenceDiagram
    actor Admin
    participant Frontend
    participant Backend
    participant Casbin
    participant InstanceMgr
    participant PolicyMgr

    Admin->>Frontend: Click Delete Instance
    Frontend->>Backend: DELETE /api/admin/instances/{uuid}<br/>Bearer {token}

    Backend->>Backend: Validate Admin Token
    Backend->>Casbin: enforce(admin_id, admin, delete_instance)
    Casbin->>Backend: true (ALLOW)

    Backend->>InstanceMgr: get_instance_by_uuid(uuid)
    InstanceMgr->>Backend: Instance Details

    Backend->>PolicyMgr: get_instance_policies(uuid)
    PolicyMgr->>Backend: Policy List[]

    Note over Backend: Confirm policies will be removed

    Backend->>InstanceMgr: delete_instance(instance)
    InstanceMgr->>InstanceMgr: Remove from Instances List
    InstanceMgr->>InstanceMgr: Delete Config File<br/>(configs/{uuid}.json)

    Backend->>PolicyMgr: remove_policies(policy_list)
    PolicyMgr->>Casbin: Remove Policy Rules
    Casbin->>PolicyMgr: Policies Removed

    Backend->>Frontend: 200 OK<br/>Instance deleted
    Frontend->>Admin: Success Message
```

---

## Storage Agent Operations

### Supported Operations

| Operation | S3 Agent | Dummy Agent | Description |
|-----------|----------|-------------|-------------|
| `generate_access_link()` | ✅ Presigned GET URL | ✅ Mock URL | Get download URL |
| `generate_upload_link()` | ✅ Presigned POST | ✅ Mock URL | Get upload URL |
| `load_file_tree()` | ✅ S3 list_objects | ✅ Mock tree | List files/folders |
| `validate_config()` | ✅ Test credentials | ✅ Always valid | Check connection |

### Presigned URL Security

**S3 Presigned URLs include:**
- AWS Access Key ID (in query params)
- Signature (HMAC-SHA256 of request)
- Expiration timestamp
- Specific operation (GET/PUT/POST)
- Resource path (locked to specific object)

**Validation by S3:**
1. Check signature matches request
2. Verify not expired
3. Confirm operation matches
4. Validate resource path

---

## Access Control Patterns

### Pattern 1: User-Level Access
```
p, user_uuid, instance_uuid, .*, read
```
User can read all files in the instance.

### Pattern 2: Resource-Level Access
```
p, user_uuid, instance_uuid, data/project1/.*, read
```
User can only read files in `data/project1/` folder.

### Pattern 3: Operation-Level Access
```
p, user_uuid, instance_uuid, data/shared/.*, read
p, user_uuid, instance_uuid, data/uploads/.*, write
```
User can read from `shared` but only write to `uploads`.

### Pattern 4: Admin Access (Policy Management)
```
p, user_uuid, instance_uuid, .*, admin
```
User can manage policies for all resources in the instance.

**Note:** The "admin" action in Casbin is used for **policy management** only.
It grants the ability to view and modify access policies for the specified resources,
but does NOT grant file read/write/delete permissions.

**Separate from Keycloak Admin:** This is instance-level policy management permission,
distinct from the Keycloak realm "admin" role which grants system-wide admin operations.

---

**Last Updated:** 2025-10-23
