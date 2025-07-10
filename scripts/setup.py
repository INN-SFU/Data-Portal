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

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.settings.security._generate_secrets import _generate_secrets


def create_config_files(environment='development'):
    """Create configuration files from templates."""
    print(f"Setting up {environment} configuration...")
    
    # Create config.yaml from template
    config_template = project_root / 'config' / 'config.template.yaml'
    config_file = project_root / 'config.yaml'
    
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
    env_template = project_root / 'config' / '.env.template'
    env_file = project_root / 'core' / 'settings' / '.env'
    
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
    logs_dir = project_root / 'loggers' / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    print(f"✓ Created {logs_dir}")
    
    # Create other required directories
    required_dirs = [
        'core/settings/security',
        'core/settings/managers/endpoints/configs',
        'core/settings/managers/policies/casbin'
    ]
    
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Ensured {full_path} exists")


def generate_secrets():
    """Generate cryptographic secrets."""
    print("Generating secrets...")
    secrets_file = project_root / 'core' / 'settings' / 'security' / '.secrets'
    
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
        full_path = project_root / file_path
        if not full_path.exists():
            missing_files.append(file_path)
    
    missing_dirs = []
    for dir_path in required_dirs:
        full_path = project_root / dir_path
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
    secrets_file = project_root / 'core' / 'settings' / 'security' / '.secrets'
    with open(secrets_file, 'r') as f:
        content = f.read()
        if 'REPLACE_WITH_GENERATED_VALUE' in content:
            print("✗ Secrets contain template values - run with --generate-secrets")
            return False
    
    print("✓ Secrets have been generated")
    return True


def start_keycloak():
    """Start Keycloak service."""
    print("Starting Keycloak...")
    
    try:
        # Check if Keycloak is already running
        result = subprocess.run(['docker', 'ps', '--filter', 'name=ams-keycloak', '--format', '{{.Names}}'], 
                              capture_output=True, text=True, cwd=project_root)
        if 'ams-keycloak' in result.stdout:
            print("✓ Keycloak is already running")
        else:
            # Start Keycloak
            subprocess.run(['docker', 'compose', '-f', 'deployment/docker-compose.yml', 'up', 'keycloak', '-d'], 
                         check=True, cwd=project_root)
            print("✓ Keycloak service started")
            
            # Wait for Keycloak to be ready
            print("⏳ Waiting for Keycloak to be ready...")
            time.sleep(30)  # Give Keycloak time to start
            
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to start Keycloak: {e}")
        return False


def wait_for_keycloak():
    """Wait for Keycloak to be ready."""
    import requests
    
    print("⏳ Waiting for Keycloak to be fully ready...")
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            response = requests.get('http://localhost:8080', timeout=5)
            if response.status_code == 200:
                print("✓ Keycloak is ready")
                time.sleep(5)  # Extra wait for full initialization
                return True
        except requests.RequestException:
            pass
        
        if attempt < max_attempts - 1:
            time.sleep(10)
            print(f"   Still waiting... (attempt {attempt + 1}/{max_attempts})")
    
    print("✗ Keycloak failed to become ready")
    return False


def configure_keycloak_realm():
    """Configure Keycloak realm and get client secret."""
    print("Configuring Keycloak realm...")
    
    try:
        # Delete existing realm first to ensure fresh setup
        delete_cmd = [
            'docker', 'exec', 'ams-keycloak',
            '/opt/keycloak/bin/kcadm.sh', 'delete', 'realms/ams-portal',
            '--server', 'http://localhost:8080',
            '--realm', 'master',
            '--user', 'admin',
            '--password', 'admin123'
        ]
        
        # Try to delete - ignore errors if realm doesn't exist
        subprocess.run(delete_cmd, capture_output=True, text=True, cwd=project_root)
        print("✓ Cleaned up existing realm (if any)")
        
        # Import the realm configuration
        realm_file = project_root / 'config' / 'keycloak-realm-export.json'
        if not realm_file.exists():
            print("✗ Keycloak realm export file not found")
            return None
        
        # Load and modify the realm file to ensure fresh client secret
        import json
        with open(realm_file, 'r') as f:
            realm_data = json.load(f)
        
        # Find the admin client and remove any secret field to force regeneration
        for client in realm_data.get('clients', []):
            if client.get('clientId') == 'ams-portal-admin':
                # Remove any existing secret to force fresh generation
                client.pop('secret', None)
                client.pop('clientSecret', None)
                # Ensure it's a confidential client
                client['publicClient'] = False
                print("   ✓ Prepared admin client for fresh secret generation")
                break
        
        # Write modified realm file to container
        modified_realm_file = '/tmp/keycloak-realm-export-modified.json'
        with open(modified_realm_file, 'w') as f:
            json.dump(realm_data, f, indent=2)
        
        subprocess.run([
            'docker', 'cp', modified_realm_file, 
            'ams-keycloak:/tmp/keycloak-realm-export.json'
        ], check=True, cwd=project_root)
        
        # Use Keycloak admin CLI to import realm
        import_cmd = [
            'docker', 'exec', 'ams-keycloak', 
            '/opt/keycloak/bin/kcadm.sh', 'create', 'realms',
            '-f', '/tmp/keycloak-realm-export.json',
            '--server', 'http://localhost:8080',
            '--realm', 'master',
            '--user', 'admin',
            '--password', 'admin123'
        ]
        
        # Import the realm
        result = subprocess.run(import_cmd, capture_output=True, text=True, cwd=project_root)
        if result.returncode == 0:
            print("✓ Keycloak realm configured with fresh setup")
            
            # Configure admin user automation
            admin_user_configured = configure_admin_user()
            
            # Get the client secret from the freshly imported realm
            secret = get_keycloak_client_secret()
            if secret:
                # Update config.yaml with the secret
                update_config_with_secret(secret)
                return secret
            else:
                print("⚠ Could not retrieve client secret")
                return None
        else:
            print(f"⚠ Realm import failed (stdout): {result.stdout}")
            print(f"⚠ Realm import failed (stderr): {result.stderr}")
            # Try alternative method using REST API
            return configure_keycloak_via_rest_api()
            
    except Exception as e:
        print(f"✗ Error configuring Keycloak realm: {e}")
        # Try alternative method using REST API
        return configure_keycloak_via_rest_api()


def configure_admin_user():
    """Configure admin user with proper credentials and roles."""
    print("Configuring admin user...")
    
    try:
        # First, check if admin user exists
        check_user_cmd = [
            'docker', 'exec', 'ams-keycloak',
            '/opt/keycloak/bin/kcadm.sh', 'get', 'users',
            '--server', 'http://localhost:8080',
            '--realm', 'master',
            '--user', 'admin',
            '--password', 'admin123',
            '--target-realm', 'ams-portal',
            '--query', 'username=admin'
        ]
        
        result = subprocess.run(check_user_cmd, capture_output=True, text=True, cwd=project_root)
        if result.returncode == 0:
            import json
            users = json.loads(result.stdout)
            
            if users and len(users) > 0:
                user_id = users[0]['id']
                print(f"   ✓ Found existing admin user with ID: {user_id}")
                
                # Remove required actions
                update_user_cmd = [
                    'docker', 'exec', 'ams-keycloak',
                    '/opt/keycloak/bin/kcadm.sh', 'update', f'users/{user_id}',
                    '--server', 'http://localhost:8080',
                    '--realm', 'master',
                    '--user', 'admin',
                    '--password', 'admin123',
                    '--target-realm', 'ams-portal',
                    '-s', 'requiredActions=[]'
                ]
                
                subprocess.run(update_user_cmd, capture_output=True, text=True, cwd=project_root)
                print("   ✓ Removed required actions")
                
                # Set password
                set_password_cmd = [
                    'docker', 'exec', 'ams-keycloak',
                    '/opt/keycloak/bin/kcadm.sh', 'set-password',
                    '--server', 'http://localhost:8080',
                    '--realm', 'master',
                    '--user', 'admin',
                    '--password', 'admin123',
                    '--target-realm', 'ams-portal',
                    '--username', 'admin',
                    '--new-password', 'admin123'
                ]
                
                subprocess.run(set_password_cmd, capture_output=True, text=True, cwd=project_root)
                print("   ✓ Set admin password")
                
                # Add protocol mappers for JWT tokens
                configure_protocol_mappers()
                
                print("✓ Admin user configured successfully")
                return True
            else:
                print("   ⚠ Admin user not found in realm export")
                return False
        else:
            print(f"   ⚠ Failed to check for admin user: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Error configuring admin user: {e}")
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
        realm_file = project_root / 'config' / 'keycloak-realm-export.json'
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
        config_file = project_root / 'config.yaml'
        
        # Ensure config file exists
        if not config_file.exists():
            create_config_files()
        
        with open(config_file, 'r') as f:
            content = f.read()
        
        # Replace the placeholder with actual secret
        content = content.replace('your-admin-client-secret', client_secret)
        
        with open(config_file, 'w') as f:
            f.write(content)
            
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
                              capture_output=True, text=True, cwd=project_root)
        
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
    parser.add_argument('--configure-keycloak', action='store_true',
                       help='Configure Keycloak realm and get client secret')
    parser.add_argument('--create-admin', action='store_true',
                       help='Automatically configure initial admin user in Keycloak')
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
                    # Step 4: Get admin user credentials  
                    admin_credentials = get_admin_user_credentials()
                else:
                    print("⚠ Continuing without client secret - you may need to configure manually")
                    admin_credentials = get_admin_user_credentials()
        
        # Step 5: Validate everything
        validation_success = validate_environment()
        
        # Step 6: Run tests (optional, don't fail setup if tests fail)
        if validation_success:
            run_tests()
        
    elif args.all or not any([args.create_dirs, args.generate_secrets, args.validate, args.docker, 
                             args.start_keycloak, args.configure_keycloak, args.create_admin, args.run_tests]):
        # Legacy setup mode
        create_directory_structure()
        create_config_files(args.environment)
        generate_secrets()
        if args.docker or args.all:
            create_docker_files()
        validate_environment()
    else:
        # Individual options - ensure basic setup first
        setup_needed = any([args.start_keycloak, args.configure_keycloak, args.create_admin, args.validate])
        
        if setup_needed:
            # Ensure basic files exist for individual commands
            create_directory_structure()
            create_config_files(args.environment)
            generate_secrets()
        
        if args.create_dirs:
            create_directory_structure()
        if args.generate_secrets:
            generate_secrets()
        if args.start_keycloak:
            start_keycloak()
            wait_for_keycloak()
        if args.configure_keycloak:
            configure_keycloak_realm()
        if args.create_admin:
            admin_configured = configure_admin_user()
            
            if admin_configured:
                print("✅ Admin user configured successfully!")
                print("   Username: admin")
                print("   Password: admin123")
                print("   Ready to login at: http://localhost:8000")
            else:
                print("❌ Admin user configuration failed!")
                print("   Ensure Keycloak is running and realm is configured")
        if args.run_tests:
            run_tests()
        if args.validate:
            validate_environment()
        if args.docker:
            create_docker_files()
    
    # Print completion message
    if args.full_setup and admin_credentials:
        print("\n🎉 SETUP COMPLETE!")
        print("\n📋 ADMIN CREDENTIALS:")
        print(f"   Username: {admin_credentials['username']}")
        print(f"   Password: {admin_credentials['password']}")
        
        print("\n🚀 NEXT STEPS:")
        print("   1. Start application: python main.py config.yaml")
        print("   2. Open: http://localhost:8000")
        print("   3. Login with admin credentials above")
        
    elif not any([args.create_dirs, args.generate_secrets, args.validate, args.docker, 
                 args.start_keycloak, args.configure_keycloak, args.create_admin, args.run_tests]):
        print("\n✅ Setup completed!")
        print("Next steps:")
        print("1. Run application: python main.py config.yaml")


if __name__ == '__main__':
    main()