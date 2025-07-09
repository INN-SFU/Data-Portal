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
    print(f"Setting up configuration for {environment} environment...")
    
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
    print("Creating required directory structure...")
    
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
    print("Generating cryptographic secrets...")
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
    print("Validating environment configuration...")
    
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
    print("Starting Keycloak service...")
    
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
        # Import the realm configuration
        realm_file = project_root / 'config' / 'keycloak-realm-export.json'
        if not realm_file.exists():
            print("✗ Keycloak realm export file not found")
            return None
        
        # Copy realm file to container root first (avoid directory issues)
        subprocess.run([
            'docker', 'cp', str(realm_file), 
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
        if result.returncode == 0 or 'already exists' in result.stderr:
            print("✓ Keycloak realm configured")
            
            # Get the client secret
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


def get_keycloak_client_secret():
    """Get the admin client secret from Keycloak."""
    try:
        # Use Keycloak admin CLI to get client secret
        secret_cmd = [
            'docker', 'exec', 'ams-keycloak',
            '/opt/keycloak/bin/kcadm.sh', 'get', 'clients',
            '--server', 'http://localhost:8080',
            '--realm', 'ams-portal',
            '--user', 'admin',
            '--password', 'admin123',
            '--query', 'clientId=ams-portal-admin'
        ]
        
        result = subprocess.run(secret_cmd, capture_output=True, text=True, cwd=project_root)
        if result.returncode == 0:
            import json
            clients = json.loads(result.stdout)
            if clients and len(clients) > 0:
                client_id = clients[0]['id']
                
                # Get client secret
                secret_cmd = [
                    'docker', 'exec', 'ams-keycloak',
                    '/opt/keycloak/bin/kcadm.sh', 'get', f'clients/{client_id}/client-secret',
                    '--server', 'http://localhost:8080',
                    '--realm', 'ams-portal',
                    '--user', 'admin',
                    '--password', 'admin123'
                ]
                
                secret_result = subprocess.run(secret_cmd, capture_output=True, text=True, cwd=project_root)
                if secret_result.returncode == 0:
                    secret_data = json.loads(secret_result.stdout)
                    return secret_data.get('value')
        
        print("⚠ Could not retrieve client secret automatically")
        return None
        
    except Exception as e:
        print(f"✗ Error getting client secret: {e}")
        return None


def update_config_with_secret(client_secret):
    """Update config.yaml with the client secret."""
    try:
        config_file = project_root / 'config.yaml'
        
        with open(config_file, 'r') as f:
            content = f.read()
        
        # Replace the placeholder with actual secret
        content = content.replace('your-admin-client-secret', client_secret)
        
        with open(config_file, 'w') as f:
            f.write(content)
            
        print("✓ Updated config.yaml with client secret")
        
    except Exception as e:
        print(f"✗ Error updating config with secret: {e}")


def create_admin_user():
    """Create the initial admin user."""
    print("Creating initial admin user...")
    
    # Default admin credentials
    admin_credentials = {
        'username': 'admin',
        'email': 'admin@localhost',
        'password': 'admin123',
        'first_name': 'Admin',
        'last_name': 'User'
    }
    
    try:
        # Import the user manager and creation logic directly
        from core.settings.managers.users import user_manager
        from core.management.users.models import UserCreate
        
        print(f"   Creating user: {admin_credentials['username']}")
        
        # Create user with admin role
        user_create = UserCreate(
            username=admin_credentials['username'],
            email=admin_credentials['email'],
            roles=['admin']  # Assign admin role during creation
        )
        
        # Create user via UserManager (this handles role assignment)
        new_user = user_manager.create_user(user_create)
        print(f"✓ Admin user created successfully!")
        print(f"   Username: {new_user.username}")
        print(f"   Email: {new_user.email}")
        print(f"   Roles: {', '.join(new_user.roles)}")
        
        # Verify admin role was assigned
        if 'admin' in new_user.roles:
            print("✓ Admin role assigned successfully")
        else:
            print("⚠ Admin role not found in user roles")
        
        return admin_credentials
        
    except Exception as e:
        print(f"✗ Failed to create admin user: {e}")
        print("   Possible issues:")
        print("   - Keycloak may not be ready yet")
        print("   - Configuration may be incorrect")
        print("   - Network connectivity issues")
        print("   You can create one manually with: python scripts/create_admin_user.py")
        return admin_credentials  # Return credentials anyway for display


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
                       help='Create initial admin user')
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
        print("🚀 Running FULL AUTOMATED SETUP for new developers")
        print("=" * 50)
        
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
                    # Step 4: Create admin user
                    admin_credentials = create_admin_user()
                else:
                    print("⚠ Continuing without client secret - you may need to configure manually")
                    admin_credentials = create_admin_user()
        
        # Step 5: Validate everything
        validation_success = validate_environment()
        
        # Step 6: Run tests (optional, don't fail setup if tests fail)
        if validation_success:
            print("\n🧪 Running validation tests...")
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
        # Individual options
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
            admin_credentials = create_admin_user()
        if args.run_tests:
            run_tests()
        if args.validate:
            validate_environment()
        if args.docker:
            create_docker_files()
    
    # Print completion message
    print("\n" + "=" * 70)
    if args.full_setup and admin_credentials:
        print("🎉 SETUP COMPLETE! Your AMS Data Portal is ready for development!")
        print("=" * 70)
        print("\n📋 ADMIN CREDENTIALS (save these!):")
        print(f"   Username: {admin_credentials['username']}")
        print(f"   Password: {admin_credentials['password']}")
        print(f"   Email:    {admin_credentials['email']}")
        
        print("\n🌐 ACCESS POINTS:")
        print("   📱 AMS Data Portal:  http://localhost:8000  (start with command below)")
        print("   📊 API Docs:         http://localhost:8000/docs")
        print("   🔐 Keycloak Admin:   http://localhost:8080 (admin/admin123)")
        
        print("\n🚀 NEXT STEPS:")
        print("   1. START THE APPLICATION: python main.py config.yaml")
        print("   2. Go to http://localhost:8000 and login with admin credentials above")
        print("   3. Start developing!")
        
        print("\n💻 DEVELOPMENT WORKFLOW:")
        print("   • Activate virtual environment: source .venv/bin/activate")
        print("   • Start application: python main.py config.yaml")  
        print("   • Run tests: behave tests/features/")
        print("   • Keycloak is already running and configured!")
        print("   • Admin user is already created and ready to use!")
        
    else:
        print("✅ Setup completed!")
        print("\nNext steps:")
        if not args.full_setup:
            print("1. Run full setup: python scripts/setup.py --full-setup")
            print("2. Or manually: start Keycloak, create admin user, run application")
        print("3. Install dependencies: pip install -r requirements.txt")
        print("4. Run application: python main.py config.yaml")


if __name__ == '__main__':
    main()