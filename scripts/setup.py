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
    
    missing_files = []
    for file_path in required_files:
        full_path = project_root / file_path
        if not full_path.exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("✗ Missing required configuration files:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        return False
    
    print("✓ All required configuration files present")
    
    # Check if secrets have been generated
    secrets_file = project_root / 'core' / 'settings' / 'security' / '.secrets'
    with open(secrets_file, 'r') as f:
        content = f.read()
        if 'REPLACE_WITH_GENERATED_VALUE' in content:
            print("✗ Secrets contain template values - run with --generate-secrets")
            return False
    
    print("✓ Secrets have been generated")
    return True


def create_docker_files():
    """Create Docker configuration files."""
    print("Creating Docker configuration files...")
    
    # This will be implemented in the next step
    print("⚠ Docker files creation not yet implemented")


def main():
    parser = argparse.ArgumentParser(description='AMS Data Portal Setup Script')
    parser.add_argument('--environment', choices=['development', 'production'], 
                       default='development', help='Environment to configure for')
    parser.add_argument('--generate-secrets', action='store_true', 
                       help='Generate new cryptographic secrets')
    parser.add_argument('--validate', action='store_true', 
                       help='Validate environment configuration')
    parser.add_argument('--docker', action='store_true', 
                       help='Create Docker configuration files')
    parser.add_argument('--all', action='store_true', 
                       help='Run all setup steps')
    
    args = parser.parse_args()
    
    print("AMS Data Portal Setup")
    print("=" * 50)
    
    if args.all or not any([args.generate_secrets, args.validate, args.docker]):
        create_config_files(args.environment)
        generate_secrets()
        if args.docker or args.all:
            create_docker_files()
        validate_environment()
    else:
        if args.generate_secrets:
            generate_secrets()
        if args.validate:
            validate_environment()
        if args.docker:
            create_docker_files()
    
    print("\nSetup completed! Next steps:")
    print("1. Review and update config.yaml with your specific settings")
    print("2. Update Keycloak configuration in config.yaml")
    print("3. Install dependencies: pip install -r requirements.txt")
    print("4. Run the application: python main.py config.yaml")


if __name__ == '__main__':
    main()