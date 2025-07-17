#!/usr/bin/env python3
"""
AMS Data Portal Setup Script

This script helps initialize the AMS Data Portal for local development or production deployment.
It handles configuration file creation, secret generation, and environment validation.
"""

import argparse
import os
import shutil
import sys
import yaml
import time
import subprocess
from pathlib import Path

def find_project_root():
    """Find the project root by looking for key files."""
    current_dir = Path(__file__).parent
    
    # Look for key files that indicate project root
    key_files = ['requirements.txt', 'frontend', 'deployment']
    
    # Search up the directory tree
    for parent in [current_dir] + list(current_dir.parents):
        if all((parent / key).exists() for key in key_files):
            return parent
    
    # Fallback to current backend directory if we can't find project root
    return current_dir.parent

# Find the actual project root dynamically
project_root = find_project_root()
backend_root = project_root / 'backend'
sys.path.insert(0, str(backend_root))

from core.settings.security._generate_secrets import _generate_secrets


def create_config_files(environment='development'):
    """Create configuration files from templates."""
    print(f"Setting up {environment} configuration...")
    
    # Create config.yaml from template
    config_template = backend_root / 'config' / 'config.template.yaml'
    config_file = backend_root / 'config.yaml'
    
    if not config_file.exists():
        shutil.copy(config_template, config_file)
        print(f"✓ Created {config_file}")
        
        # Update config for environment
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        if environment == 'production':
            config['uvicorn']['reload'] = False
            config['uvicorn']['host'] = '0.0.0.0'
            config['system']['reset'] = False
        
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
            
        print(f"✓ Configured for {environment} environment")
    else:
        print(f"⚠ {config_file} already exists, skipping")
    
    # Create .env file
    env_template = backend_root / 'config' / '.env.template'
    env_file = backend_root / 'core' / 'settings' / '.env'
    
    if not env_file.exists():
        # Ensure directory exists
        env_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(env_template, env_file)
        print(f"✓ Created {env_file}")
    else:
        print(f"⚠ {env_file} already exists, skipping")


def create_directory_structure():
    """Create required directory structure."""
    print("Creating directories...")
    
    # Create logs directory
    logs_dir = backend_root / 'loggers' / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    print(f"✓ Created {logs_dir}")
    
    # Create other required directories
    required_dirs = [
        'core/settings/security',
        'core/settings/managers/endpoints/configs',
        'core/settings/managers/policies/casbin',
        'core/settings/managers/policies/user_policies'
    ]
    
    for dir_path in required_dirs:
        full_path = backend_root / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Ensured {full_path} exists")
    
    # Create user policies directory from .env configuration
    try:
        from dotenv import load_dotenv
        env_file = backend_root / 'core' / 'settings' / '.env'
        if env_file.exists():
            load_dotenv(env_file)
            user_policies_path = os.getenv('USER_POLICIES')
            if user_policies_path:
                # Convert relative path to absolute
                if user_policies_path.startswith('./'):
                    user_policies_path = user_policies_path[2:]
                user_policies_dir = backend_root / user_policies_path
                user_policies_dir.mkdir(parents=True, exist_ok=True)
                print(f"✓ Created user policies directory: {user_policies_dir}")
    except Exception as e:
        print(f"⚠ Could not create user policies directory: {e}")


def generate_secrets():
    """Generate cryptographic secrets."""
    print("Generating secrets...")
    secrets_file = backend_root / 'core' / 'settings' / 'security' / '.secrets'
    
    if not secrets_file.exists():
        # Ensure directory exists
        secrets_file.parent.mkdir(parents=True, exist_ok=True)
        # Create empty secrets file first
        secrets_file.touch()
    
    # Generate secrets
    _generate_secrets()
    print("✓ Generated cryptographic secrets")


def validate_environment():
    """Validate that the environment is properly configured."""
    print("Validating configuration...")
    
    required_files = [
        'config.yaml',
        'core/settings/.env',
        'core/settings/security/.secrets'
    ]
    
    required_dirs = [
        'loggers/logs',
        'core/settings/security',
        'core/settings/managers/endpoints/configs',
        'core/settings/managers/policies/casbin'
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = backend_root / file_path
        if not full_path.exists():
            missing_files.append(file_path)
    
    missing_dirs = []
    for dir_path in required_dirs:
        full_path = backend_root / dir_path
        if not full_path.exists():
            missing_dirs.append(dir_path)
    
    if missing_files:
        print("✗ Missing required configuration files:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        return False
    
    if missing_dirs:
        print("✗ Missing required directories:")
        for dir_path in missing_dirs:
            print(f"  - {dir_path}")
        return False
    
    print("✓ All required configuration files and directories present")
    
    # Check if secrets have been generated
    secrets_file = backend_root / 'core' / 'settings' / 'security' / '.secrets'
    with open(secrets_file, 'r') as f:
        content = f.read()
        if 'REPLACE_WITH_GENERATED_VALUE' in content:
            print("✗ Secrets contain template values - run with --generate-secrets")
            return False
    
    print("✓ Secrets have been generated")
    return True


def start_keycloak(force_rebuild=False):
    """Start Keycloak service."""
    print("Starting Keycloak...")
    
    try:
        # Check if Keycloak is already running
        result = subprocess.run(['docker', 'ps', '--filter', 'name=ams-keycloak', '--format', '{{.Names}}'], 
                              capture_output=True, text=True, cwd=project_root)
        
        if force_rebuild or 'ams-keycloak' not in result.stdout:
            if force_rebuild and 'ams-keycloak' in result.stdout:
                print("🔄 Force rebuilding Keycloak...")
                # Stop and remove existing container
                subprocess.run(['docker', 'stop', 'ams-keycloak'], check=False, cwd=project_root)
                subprocess.run(['docker', 'rm', 'ams-keycloak'], check=False, cwd=project_root)
                
                # Remove data volume to ensure fresh import
                subprocess.run(['docker', 'volume', 'rm', 'deployment_keycloak_data'], check=False, cwd=project_root)
                print("✓ Cleaned up existing Keycloak resources")
            
            # Start Keycloak
            docker_compose_path = project_root / 'deployment' / 'docker-compose.yml'
            subprocess.run(['docker', 'compose', '-f', str(docker_compose_path), 'up', 'keycloak', '-d'], 
                         check=True, cwd=project_root)
            print("✓ Keycloak service started")
            
            # Wait for Keycloak to be ready
            print("⏳ Waiting for Keycloak to be ready...")
            time.sleep(60)  # Give Keycloak more time to start
        else:
            print("✓ Keycloak is already running")
            
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to start Keycloak: {e}")
        return False


def wait_for_keycloak():
    """Wait for Keycloak to be ready."""
    import requests
    
    print("⏳ Waiting for Keycloak HTTP service...")
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            response = requests.get('http://localhost:8080', timeout=5)
            if response.status_code == 200:
                print("✓ Keycloak HTTP service is ready")
                # Give extra time for admin user initialization
                time.sleep(30)
                return True
                    
        except requests.RequestException:
            pass
        
        if attempt < max_attempts - 1:
            time.sleep(10)
            print(f"   Still waiting for HTTP service... (attempt {attempt + 1}/{max_attempts})")
    
    print("✗ Keycloak HTTP service failed to become available")
    return False


def verify_keycloak_admin():
    """Verify Keycloak admin credentials work before proceeding."""
    print("Verifying Keycloak admin access...")
    
    try:
        test_cmd = [
            'docker', 'exec', 'ams-keycloak',
            '/opt/keycloak/bin/kcadm.sh', 'get', 'realms',
            '--server', 'http://localhost:8080',
            '--realm', 'master',
            '--user', 'admin',
            '--password', 'admin123'
        ]
        
        result = subprocess.run(test_cmd, capture_output=True, text=True, cwd=project_root)
        if result.returncode == 0:
            print("✓ Keycloak admin access verified")
            return True
        else:
            print(f"✗ Keycloak admin access failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Error verifying Keycloak admin: {e}")
        return False


def configure_keycloak_realm():
    """Verify Keycloak realm auto-import and get client secret."""
    print("Verifying Keycloak realm auto-import...")
    
    try:
        import requests
        import time
        
        # Keycloak should auto-import the realm on startup via --import-realm
        # Let's just verify it worked and get the client secret
        
        # Try to get admin token 
        max_attempts = 10
        access_token = None
        
        print("Attempting admin authentication...")
        for attempt in range(max_attempts):
            try:
                token_url = 'http://localhost:8080/realms/master/protocol/openid-connect/token'
                token_data = {
                    'grant_type': 'password',
                    'client_id': 'admin-cli',
                    'username': 'admin',
                    'password': 'admin123'
                }
                
                token_response = requests.post(token_url, data=token_data, timeout=10)
                if token_response.status_code == 200:
                    access_token = token_response.json()['access_token']
                    print("✓ Successfully authenticated with Keycloak admin")
                    break
                else:
                    if attempt == 0:
                        print(f"   ⚠ Auth failed: {token_response.status_code} - {token_response.text}")
                    
            except Exception as e:
                if attempt == 0:
                    print(f"   ⚠ Auth error: {e}")
            
            if attempt < max_attempts - 1:
                time.sleep(15)  # Wait longer between attempts
                print(f"   Retrying authentication... ({attempt + 2}/{max_attempts})")
        
        if not access_token:
            print("✗ Failed to authenticate with Keycloak admin")
            print("   Check container logs: docker logs ams-keycloak")
            return None
            
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Check if ams-portal realm exists (should be auto-imported)
        realm_check_url = 'http://localhost:8080/admin/realms/ams-portal'
        realm_response = requests.get(realm_check_url, headers=headers)
        
        if realm_response.status_code == 200:
            print("✓ ams-portal realm found (auto-imported successfully)")
            
            # Configure service account permissions
            configure_service_account_permissions(access_token)
            
            # Configure client scopes for service account tokens
            configure_client_scopes(access_token)
            
            # Get client secret using REST API
            secret = get_keycloak_client_secret_via_rest_api(access_token)
            if secret:
                update_config_with_secret(secret)
                print("✓ Retrieved and updated client secret")
                return secret
            else:
                print("⚠ Could not retrieve client secret")
                return None
        else:
            print(f"✗ ams-portal realm not found (auto-import may have failed)")
            print(f"   Check container logs: docker logs ams-keycloak")
            return None
            
    except Exception as e:
        print(f"✗ Error verifying Keycloak realm: {e}")
        return None


def configure_admin_user():
    """Verify app admin user exists (created during realm import)."""
    print("Verifying app admin user from realm import...")
    
    try:
        import requests
        import time
        
        # Get admin token for verification
        token_url = 'http://localhost:8080/realms/master/protocol/openid-connect/token'
        token_data = {
            'grant_type': 'password',
            'client_id': 'admin-cli',
            'username': 'admin',
            'password': 'admin123'
        }
        
        token_response = requests.post(token_url, data=token_data, timeout=10)
        if token_response.status_code != 200:
            print("✗ Cannot authenticate to verify app admin user")
            return False
            
        access_token = token_response.json()['access_token']
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Check if app admin user exists in ams-portal realm
        users_url = 'http://localhost:8080/admin/realms/ams-portal/users'
        params = {'username': 'admin'}
        
        users_response = requests.get(users_url, headers=headers, params=params)
        if users_response.status_code == 200:
            users = users_response.json()
            if users and len(users) > 0:
                user = users[0]
                print(f"   ✓ Found app admin user: {user['username']}")
                print(f"   ✓ Email: {user.get('email', 'N/A')}")
                print(f"   ✓ Enabled: {user.get('enabled', False)}")
                print("✓ App admin user successfully imported with realm")
                return True
            else:
                print("   ✗ App admin user not found in ams-portal realm")
                return False
        else:
            print(f"   ✗ Failed to query users: {users_response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error verifying app admin user: {e}")
        return False



def configure_protocol_mappers():
    """Add protocol mappers to UI client for proper JWT token content."""
    print("   Adding protocol mappers for JWT tokens...")
    
    try:
        # Add username mapper
        username_mapper_cmd = [
            'docker', 'exec', 'ams-keycloak',
            '/opt/keycloak/bin/kcadm.sh', 'create', 'clients/ui-client-id/protocol-mappers/models',
            '--server', 'http://localhost:8080',
            '--realm', 'master',
            '--user', 'admin',
            '--password', 'admin123',
            '--target-realm', 'ams-portal',
            '-s', 'name=username',
            '-s', 'protocol=openid-connect',
            '-s', 'protocolMapper=oidc-usermodel-property-mapper',
            '-s', 'config."userinfo.token.claim"=true',
            '-s', 'config."user.attribute"=username',
            '-s', 'config."id.token.claim"=true',
            '-s', 'config."access.token.claim"=true',
            '-s', 'config."claim.name"=preferred_username',
            '-s', 'config."jsonType.label"=String'
        ]
        
        result = subprocess.run(username_mapper_cmd, capture_output=True, text=True, cwd=project_root)
        if result.returncode == 0:
            print("   ✓ Added username protocol mapper")
        else:
            print(f"   ⚠ Username mapper may already exist: {result.stderr}")
        
        # Add realm roles mapper
        roles_mapper_cmd = [
            'docker', 'exec', 'ams-keycloak',
            '/opt/keycloak/bin/kcadm.sh', 'create', 'clients/ui-client-id/protocol-mappers/models',
            '--server', 'http://localhost:8080',
            '--realm', 'master',
            '--user', 'admin',
            '--password', 'admin123',
            '--target-realm', 'ams-portal',
            '-s', 'name=realm roles',
            '-s', 'protocol=openid-connect',
            '-s', 'protocolMapper=oidc-usermodel-realm-role-mapper',
            '-s', 'config."userinfo.token.claim"=true',
            '-s', 'config."id.token.claim"=true',
            '-s', 'config."access.token.claim"=true',
            '-s', 'config."claim.name"=realm_access.roles',
            '-s', 'config."jsonType.label"=String',
            '-s', 'config."multivalued"=true'
        ]
        
        result = subprocess.run(roles_mapper_cmd, capture_output=True, text=True, cwd=project_root)
        if result.returncode == 0:
            print("   ✓ Added realm roles protocol mapper")
        else:
            print(f"   ⚠ Roles mapper may already exist: {result.stderr}")
            
        print("   ✓ Protocol mappers configured")
        return True
        
    except Exception as e:
        print(f"   ⚠ Error configuring protocol mappers: {e}")
        return False


def configure_keycloak_via_rest_api():
    """Alternative method to configure Keycloak using REST API."""
    print("Trying alternative Keycloak configuration method...")
    
    try:
        import requests
        import json
        
        # Load the realm configuration
        realm_file = backend_root / 'config' / 'keycloak-realm-export.json'
        if not realm_file.exists():
            print("✗ Keycloak realm export file not found")
            return None
            
        with open(realm_file, 'r') as f:
            realm_data = json.load(f)
        
        # Get admin token
        token_url = 'http://localhost:8080/realms/master/protocol/openid-connect/token'
        token_data = {
            'grant_type': 'password',
            'client_id': 'admin-cli',
            'username': 'admin',
            'password': 'admin123'
        }
        
        token_response = requests.post(token_url, data=token_data)
        if token_response.status_code != 200:
            print(f"✗ Failed to get admin token: {token_response.status_code}")
            return None
            
        access_token = token_response.json()['access_token']
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Import realm
        realm_url = 'http://localhost:8080/admin/realms'
        realm_response = requests.post(realm_url, headers=headers, json=realm_data)
        
        if realm_response.status_code in [201, 409]:  # Created or already exists
            print("✓ Keycloak realm configured via REST API")
            
            # Configure admin user automation
            admin_user_configured = configure_admin_user()
            
            # Get client secret using REST API
            secret = get_keycloak_client_secret_via_rest_api(access_token)
            if secret:
                update_config_with_secret(secret)
                return secret
            else:
                print("⚠ Could not retrieve client secret via REST API")
                return None
        else:
            print(f"⚠ Realm import via REST API failed: {realm_response.status_code}")
            return None
            
    except Exception as e:
        print(f"✗ Error configuring Keycloak via REST API: {e}")
        return None


def configure_service_account_permissions(access_token):
    """Configure service account permissions for the admin client."""
    try:
        import requests
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        print("   Configuring service account permissions...")
        
        # Get the service account user ID
        users_url = 'http://localhost:8080/admin/realms/ams-portal/users'
        params = {'username': 'service-account-ams-portal-admin'}
        
        users_response = requests.get(users_url, headers=headers, params=params)
        if users_response.status_code != 200:
            print(f"   ⚠ Could not find service account user: {users_response.status_code}")
            return False
            
        users = users_response.json()
        if not users:
            print("   ⚠ Service account user not found")
            return False
            
        service_account_id = users[0]['id']
        print(f"   Found service account user: {service_account_id}")
        
        # Get realm-management client ID
        clients_url = 'http://localhost:8080/admin/realms/ams-portal/clients'
        clients_params = {'clientId': 'realm-management'}
        
        clients_response = requests.get(clients_url, headers=headers, params=clients_params)
        if clients_response.status_code != 200:
            print(f"   ⚠ Could not find realm-management client: {clients_response.status_code}")
            return False
            
        clients = clients_response.json()
        if not clients:
            print("   ⚠ realm-management client not found")
            return False
            
        realm_mgmt_client_id = clients[0]['id']
        print(f"   Found realm-management client: {realm_mgmt_client_id}")
        
        # Get available realm-management roles
        roles_url = f'http://localhost:8080/admin/realms/ams-portal/clients/{realm_mgmt_client_id}/roles'
        roles_response = requests.get(roles_url, headers=headers)
        
        if roles_response.status_code != 200:
            print(f"   ⚠ Could not get realm-management roles: {roles_response.status_code}")
            return False
            
        all_roles = roles_response.json()
        
        # Find the roles we need
        required_role_names = ['view-users', 'manage-users', 'query-users', 'view-realm', 'manage-realm']
        roles_to_assign = []
        
        for role_name in required_role_names:
            role = next((r for r in all_roles if r['name'] == role_name), None)
            if role:
                roles_to_assign.append(role)
                print(f"   Found role: {role_name}")
            else:
                print(f"   ⚠ Role not found: {role_name}")
        
        if not roles_to_assign:
            print("   ⚠ No roles found to assign")
            return False
        
        # Assign roles to service account
        assign_url = f'http://localhost:8080/admin/realms/ams-portal/users/{service_account_id}/role-mappings/clients/{realm_mgmt_client_id}'
        
        assign_response = requests.post(assign_url, headers=headers, json=roles_to_assign)
        
        if assign_response.status_code in [204, 200]:
            print(f"   ✓ Assigned {len(roles_to_assign)} realm-management roles to service account")
            return True
        else:
            print(f"   ⚠ Failed to assign roles: {assign_response.status_code} - {assign_response.text}")
            return False
            
    except Exception as e:
        print(f"   ⚠ Error configuring service account permissions: {e}")
        return False


def configure_client_scopes(access_token):
    """Configure client scopes for service account tokens to include roles."""
    try:
        import requests
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        print("   Configuring client scopes for service account...")
        
        # First, create the 'roles' client scope if it doesn't exist
        roles_scope_data = {
            "name": "roles",
            "description": "OpenID Connect scope for add user roles to the access token",
            "protocol": "openid-connect",
            "attributes": {
                "include.in.token.scope": "true",
                "display.on.consent.screen": "true"
            },
            "protocolMappers": [
                {
                    "name": "client roles",
                    "protocol": "openid-connect",
                    "protocolMapper": "oidc-usermodel-client-role-mapper",
                    "consentRequired": False,
                    "config": {
                        "userinfo.token.claim": "true",
                        "id.token.claim": "true",
                        "access.token.claim": "true",
                        "claim.name": "resource_access.${client_id}.roles",
                        "jsonType.label": "String",
                        "multivalued": "true"
                    }
                },
                {
                    "name": "realm roles",
                    "protocol": "openid-connect", 
                    "protocolMapper": "oidc-usermodel-realm-role-mapper",
                    "consentRequired": False,
                    "config": {
                        "userinfo.token.claim": "true",
                        "id.token.claim": "true",
                        "access.token.claim": "true",
                        "claim.name": "realm_access.roles",
                        "jsonType.label": "String",
                        "multivalued": "true"
                    }
                }
            ]
        }
        
        # Create the roles client scope
        create_scope_url = 'http://localhost:8080/admin/realms/ams-portal/client-scopes'
        create_response = requests.post(create_scope_url, headers=headers, json=roles_scope_data)
        
        if create_response.status_code in [201, 409]:  # Created or already exists
            print("   ✓ 'roles' client scope configured")
        else:
            print(f"   ⚠ Failed to create roles scope: {create_response.status_code}")
        
        # Get the admin client ID
        clients_url = 'http://localhost:8080/admin/realms/ams-portal/clients'
        clients_params = {'clientId': 'ams-portal-admin'}
        
        clients_response = requests.get(clients_url, headers=headers, params=clients_params)
        if clients_response.status_code != 200:
            print(f"   ⚠ Could not find admin client: {clients_response.status_code}")
            return False
            
        clients = clients_response.json()
        if not clients:
            print("   ⚠ Admin client not found")
            return False
            
        admin_client_id = clients[0]['id']
        
        # Get the roles client scope ID
        scopes_response = requests.get('http://localhost:8080/admin/realms/ams-portal/client-scopes', headers=headers)
        if scopes_response.status_code != 200:
            print(f"   ⚠ Could not get client scopes: {scopes_response.status_code}")
            return False
            
        scopes = scopes_response.json()
        roles_scope = next((s for s in scopes if s['name'] == 'roles'), None)
        
        if not roles_scope:
            print("   ⚠ Roles scope not found")
            return False
            
        roles_scope_id = roles_scope['id']
        
        # Add the roles scope to the admin client's default scopes
        add_scope_url = f'http://localhost:8080/admin/realms/ams-portal/clients/{admin_client_id}/default-client-scopes/{roles_scope_id}'
        add_scope_response = requests.put(add_scope_url, headers=headers)
        
        if add_scope_response.status_code in [204, 200]:
            print("   ✓ Added 'roles' scope to admin client")
            return True
        else:
            print(f"   ⚠ Failed to add scope to client: {add_scope_response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ⚠ Error configuring client scopes: {e}")
        return False


def get_keycloak_client_secret_via_rest_api(access_token):
    """Get client secret using REST API."""
    try:
        import requests
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Get client ID
        clients_url = 'http://localhost:8080/admin/realms/ams-portal/clients'
        params = {'clientId': 'ams-portal-admin'}
        
        clients_response = requests.get(clients_url, headers=headers, params=params)
        if clients_response.status_code != 200:
            return None
            
        clients = clients_response.json()
        if not clients:
            return None
            
        client_uuid = clients[0]['id']
        
        # Get client secret
        secret_url = f'http://localhost:8080/admin/realms/ams-portal/clients/{client_uuid}/client-secret'
        secret_response = requests.get(secret_url, headers=headers)
        
        if secret_response.status_code == 200:
            return secret_response.json()['value']
        else:
            return None
            
    except Exception as e:
        print(f"✗ Error getting client secret via REST API: {e}")
        return None


def regenerate_client_secret():
    """Regenerate the client secret for the admin client."""
    try:
        print("   Regenerating client secret for fresh setup...")
        
        # First, get the client UUID
        client_query_cmd = [
            'docker', 'exec', 'ams-keycloak',
            '/opt/keycloak/bin/kcadm.sh', 'get', 'clients',
            '--server', 'http://localhost:8080',
            '--realm', 'master',
            '--user', 'admin',
            '--password', 'admin123',
            '--target-realm', 'ams-portal',
            '--query', 'clientId=ams-portal-admin'
        ]
        
        result = subprocess.run(client_query_cmd, capture_output=True, text=True, cwd=project_root)
        if result.returncode == 0:
            import json
            clients = json.loads(result.stdout)
            if clients and len(clients) > 0:
                client_uuid = clients[0]['id']
                
                # Regenerate the client secret
                regenerate_cmd = [
                    'docker', 'exec', 'ams-keycloak',
                    '/opt/keycloak/bin/kcadm.sh', 'create', f'clients/{client_uuid}/client-secret',
                    '--server', 'http://localhost:8080',
                    '--realm', 'master',
                    '--user', 'admin',
                    '--password', 'admin123',
                    '--target-realm', 'ams-portal'
                ]
                
                regen_result = subprocess.run(regenerate_cmd, capture_output=True, text=True, cwd=project_root)
                if regen_result.returncode == 0:
                    print("   ✓ Client secret regenerated successfully")
                    return True
                else:
                    print(f"   ⚠ Failed to regenerate secret: {regen_result.stderr}")
                    return False
            else:
                print("   ⚠ Admin client not found")
                return False
        else:
            print(f"   ⚠ Failed to query clients: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"   ⚠ Error regenerating client secret: {e}")
        return False


def get_keycloak_client_secret():
    """Get the admin client secret from Keycloak."""
    try:
        # Use Keycloak admin CLI to get client secret
        # Note: authenticate against master realm, but query ams-portal realm
        secret_cmd = [
            'docker', 'exec', 'ams-keycloak',
            '/opt/keycloak/bin/kcadm.sh', 'get', 'clients',
            '--server', 'http://localhost:8080',
            '--realm', 'master',  # Auth against master realm
            '--user', 'admin',
            '--password', 'admin123',
            '--target-realm', 'ams-portal',  # Query ams-portal realm
            '--query', 'clientId=ams-portal-admin'
        ]
        
        print("   Querying Keycloak for admin client...")
        result = subprocess.run(secret_cmd, capture_output=True, text=True, cwd=project_root)
        
        if result.returncode == 0:
            print("   ✓ Client query successful")
            import json
            try:
                clients = json.loads(result.stdout)
                if clients and len(clients) > 0:
                    client_id = clients[0]['id']
                    print(f"   Found client with ID: {client_id}")
                    
                    # Get client secret
                    secret_cmd = [
                        'docker', 'exec', 'ams-keycloak',
                        '/opt/keycloak/bin/kcadm.sh', 'get', f'clients/{client_id}/client-secret',
                        '--server', 'http://localhost:8080',
                        '--realm', 'master',  # Auth against master realm
                        '--user', 'admin',
                        '--password', 'admin123',
                        '--target-realm', 'ams-portal'  # Query ams-portal realm
                    ]
                    
                    print("   Retrieving client secret...")
                    secret_result = subprocess.run(secret_cmd, capture_output=True, text=True, cwd=project_root)
                    
                    if secret_result.returncode == 0:
                        try:
                            secret_data = json.loads(secret_result.stdout)
                            secret_value = secret_data.get('value')
                            if secret_value:
                                print("   ✓ Client secret retrieved successfully")
                                return secret_value
                            else:
                                print("   ⚠ Client secret value is empty")
                        except json.JSONDecodeError as e:
                            print(f"   ⚠ Failed to parse secret JSON: {e}")
                            print(f"   Raw output: {secret_result.stdout}")
                    else:
                        print(f"   ⚠ Client secret query failed (return code {secret_result.returncode})")
                        print(f"   Error: {secret_result.stderr}")
                        print(f"   Output: {secret_result.stdout}")
                else:
                    print("   ⚠ No clients found with clientId=ams-portal-admin")
                    print(f"   Raw response: {result.stdout}")
            except json.JSONDecodeError as e:
                print(f"   ⚠ Failed to parse clients JSON: {e}")
                print(f"   Raw output: {result.stdout}")
        else:
            print(f"   ⚠ Client query failed (return code {result.returncode})")
            print(f"   Error: {result.stderr}")
            print(f"   Output: {result.stdout}")
        
        print("⚠ Could not retrieve client secret automatically")
        return None
        
    except Exception as e:
        print(f"✗ Error getting client secret: {e}")
        return None


def update_config_with_secret(client_secret):
    """Update config.yaml with the client secret."""
    try:
        config_file = backend_root / 'config.yaml'
        
        # Ensure config file exists
        if not config_file.exists():
            create_config_files()
        
        with open(config_file, 'r') as f:
            content = f.read()
        
        # Use regex to replace the admin_client_secret value regardless of what it currently is
        import re
        
        # Match the admin_client_secret line and replace the value after the |
        pattern = r'(admin_client_secret:\s*\$KEYCLOAK_ADMIN_CLIENT_SECRET\|)[^|\n]+'
        replacement = f'\\1{client_secret}'
        
        updated_content = re.sub(pattern, replacement, content)
        
        # If the regex didn't match, try the simpler placeholder replacement
        if updated_content == content:
            updated_content = content.replace('your-admin-client-secret', client_secret)
        
        with open(config_file, 'w') as f:
            f.write(updated_content)
            
        print("✓ Updated config.yaml with client secret")
        
    except Exception as e:
        print(f"✗ Error updating config with secret: {e}")


def get_admin_user_credentials():
    """Return admin user credentials without displaying instructions."""
    # Return credentials for display purposes
    return {
        'username': 'admin',
        'email': 'admin@localhost',
        'password': 'admin123',
        'first_name': 'Admin',
        'last_name': 'User'
    }


def run_tests():
    """Run the test suite to validate setup."""
    print("Running tests to validate setup...")
    
    try:
        # Run BDD tests
        result = subprocess.run(['behave', 'tests/features/', '-v'], 
                              capture_output=True, text=True, cwd=backend_root)
        
        if result.returncode == 0:
            print("✓ All tests passed")
            return True
        else:
            print(f"⚠ Some tests failed:\n{result.stdout}\n{result.stderr}")
            return False
            
    except FileNotFoundError:
        print("⚠ behave not found, skipping tests (install with: pip install behave)")
        return False
    except Exception as e:
        print(f"⚠ Error running tests: {e}")
        return False


def create_application_admin_policy():
    """Create policy file for the application admin user."""
    print("Creating application admin user policy file...")
    
    try:
        # Load environment variables from .env file
        from dotenv import load_dotenv
        env_file = backend_root / 'core' / 'settings' / '.env'
        load_dotenv(env_file)
        
        # Load configuration to get paths
        from envyaml import EnvYAML
        config_file = backend_root / 'config.yaml'
        config = EnvYAML(str(config_file), strict=False)
        
        # Get the admin user details from Keycloak
        from core.settings.managers.users.keycloak.KeycloakUserManager import KeycloakUserManager
        keycloak_config = config['keycloak']
        
        user_manager = KeycloakUserManager(
            realm_name=keycloak_config['realm'],
            client_id=keycloak_config['admin_client_id'],
            client_secret=keycloak_config['admin_client_secret'],
            base_url=keycloak_config['domain']
        )
        
        # Get the admin user UUID from Keycloak
        try:
            admin_uuid = user_manager.get_user_uuid('admin')
            print(f"   Found admin user UUID: {admin_uuid}")
        except KeyError:
            print("   ⚠ Admin user not found in Keycloak - ensure Keycloak is configured first")
            return False
        
        # Get user policies directory from environment
        user_policies_path = os.getenv('USER_POLICIES')
        if not user_policies_path:
            print("   ⚠ USER_POLICIES environment variable not set")
            return False
        if user_policies_path.startswith('./'):
            user_policies_path = user_policies_path[2:]
        user_policies_dir = backend_root / user_policies_path
        
        # Create the admin user's policy file
        admin_policy_file = user_policies_dir / f"{admin_uuid}.policies"
        
        if admin_policy_file.exists():
            print(f"   ✓ Admin policy file already exists: {admin_policy_file}")
            return True
        
        # Create empty policy file (similar to create_user_policy_store)
        with open(admin_policy_file, 'w') as f:
            f.write("")
        
        print(f"   ✓ Created admin policy file: {admin_policy_file}")
        return True
        
    except Exception as e:
        print(f"   ✗ Error creating admin policy file: {e}")
        return False


def create_docker_files():
    """Create Docker configuration files."""
    print("Creating Docker configuration files...")
    
    # This will be implemented in the next step
    print("⚠ Docker files creation not yet implemented")


def main():
    parser = argparse.ArgumentParser(description='AMS Data Portal Setup Script')
    parser.add_argument('--environment', choices=['development', 'production'], 
                       default='development', help='Environment to configure for')
    parser.add_argument('--create-dirs', action='store_true', 
                       help='Create required directory structure')
    parser.add_argument('--generate-secrets', action='store_true', 
                       help='Generate new cryptographic secrets')
    parser.add_argument('--validate', action='store_true', 
                       help='Validate environment configuration')
    parser.add_argument('--docker', action='store_true', 
                       help='Create Docker configuration files')
    parser.add_argument('--start-keycloak', action='store_true',
                       help='Start Keycloak service')
    parser.add_argument('--force-keycloak-rebuild', action='store_true',
                       help='Force rebuild Keycloak with fresh configuration (removes existing data)')
    parser.add_argument('--configure-keycloak', action='store_true',
                       help='Configure Keycloak realm and get client secret')
    parser.add_argument('--create-admin', action='store_true',
                       help='Verify and configure app admin user (created during realm import)')
    parser.add_argument('--create-admin-policy', action='store_true',
                       help='Create policy file for application admin user')
    parser.add_argument('--run-tests', action='store_true',
                       help='Run test suite to validate setup')
    parser.add_argument('--full-setup', action='store_true',
                       help='Run complete automated setup (recommended for new developers)')
    parser.add_argument('--all', action='store_true', 
                       help='Run all setup steps (legacy, use --full-setup instead)')
    
    args = parser.parse_args()
    
    print("AMS Data Portal Setup")
    print("=" * 50)
    
    admin_credentials = None
    
    if args.full_setup:
        print("🚀 Running automated setup...")
        
        # Step 1: Directory structure and config
        create_directory_structure()
        create_config_files(args.environment)
        generate_secrets()
        
        # Step 2: Start Keycloak
        if start_keycloak():
            if wait_for_keycloak():
                # Step 3: Configure Keycloak realm and get client secret
                client_secret = configure_keycloak_realm()
                if client_secret:
                    # Step 4: Create admin user policy file
                    create_application_admin_policy()
                    # Step 5: Get admin user credentials  
                    admin_credentials = get_admin_user_credentials()
                else:
                    print("⚠ Continuing without client secret - you may need to configure manually")
                    admin_credentials = get_admin_user_credentials()
        
        # Step 6: Validate everything
        validation_success = validate_environment()
        
        # Step 7: Run tests (optional, don't fail setup if tests fail)
        if validation_success:
            pass
            #run_tests()
        
    elif args.all or not any([args.create_dirs, args.generate_secrets, args.validate, args.docker, 
                             args.start_keycloak, args.configure_keycloak, args.create_admin, args.create_admin_policy, args.run_tests]):
        # Legacy setup mode
        create_directory_structure()
        create_config_files(args.environment)
        generate_secrets()
        if args.docker or args.all:
            create_docker_files()
        validate_environment()
    else:
        # Individual options - ensure basic setup first
        setup_needed = any([args.start_keycloak, args.configure_keycloak, args.create_admin, args.create_admin_policy, args.validate])
        
        if setup_needed:
            # Ensure basic files exist for individual commands
            create_directory_structure()
            create_config_files(args.environment)
            generate_secrets()
        
        if args.create_dirs:
            create_directory_structure()
        if args.generate_secrets:
            generate_secrets()
        if args.start_keycloak or args.force_keycloak_rebuild:
            start_keycloak(force_rebuild=args.force_keycloak_rebuild)
            wait_for_keycloak()
        if args.configure_keycloak:
            configure_keycloak_realm()
        if args.create_admin:
            admin_configured = configure_admin_user()
            
            if admin_configured:
                print("✅ App admin user verified successfully!")
                print("   Username: admin")
                print("   Password: admin123")
                print("   Roles: admin, user (from realm import)")
                print("   Ready to login at: http://localhost:8000")
            else:
                print("❌ App admin user verification failed!")
                print("   Check realm import - user should be created automatically")
        if args.create_admin_policy:
            if create_application_admin_policy():
                print("✅ Application admin policy file created successfully!")
            else:
                print("❌ Failed to create application admin policy file!")
        if args.run_tests:
            run_tests()
        if args.validate:
            validate_environment()
        if args.docker:
            create_docker_files()
    
    # Print completion message
    if args.full_setup and admin_credentials:
        print("\n🎉 SETUP COMPLETE!")
        print("\n📋 APP ADMIN CREDENTIALS (for AMS Data Portal login):")
        print(f"   Username: {admin_credentials['username']}")
        print(f"   Password: {admin_credentials['password']}")
        print("   Roles: admin, user")
        
        print("\n🚀 NEXT STEPS:")
        print("   1. Activate virtual environment: source .venv/bin/activate")
        print("   2. Start application: python main.py config.yaml")
        print("   3. Open: http://localhost:8000")
        print("   4. Login with app admin credentials above")
        
    elif not any([args.create_dirs, args.generate_secrets, args.validate, args.docker, 
                 args.start_keycloak, args.configure_keycloak, args.create_admin, args.run_tests]):
        print("\n✅ Setup completed!")
        print("Next steps:")
        print("1. Activate virtual environment: source .venv/bin/activate")
        print("2. Run application: python main.py config.yaml")


if __name__ == '__main__':
    main()