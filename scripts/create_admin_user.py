#!/usr/bin/env python3
"""
Create initial admin user for AMS Data Portal

This script creates an admin user in Keycloak for new developers
getting started with the AMS Data Portal.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def create_admin_user():
    """Create an admin user interactively."""
    print("🚀 AMS Data Portal - Admin User Setup")
    print("=" * 40)
    
    # Get user input
    print("\nEnter details for the admin user:")
    username = input("Username: ").strip()
    if not username:
        print("❌ Username cannot be empty")
        return False
    
    email = input("Email: ").strip()
    if not email:
        print("❌ Email cannot be empty")
        return False
    
    first_name = input("First Name: ").strip() or "Admin"
    last_name = input("Last Name: ").strip() or "User"
    
    password = input("Password: ").strip()
    if not password:
        print("❌ Password cannot be empty")
        return False
    
    confirm_password = input("Confirm Password: ").strip()
    if password != confirm_password:
        print("❌ Passwords do not match")
        return False
    
    print(f"\n📝 Creating user: {username} ({email})")
    
    try:
        # Import the user manager (this will trigger Keycloak connection)
        from core.settings.managers.users import user_manager
        
        # Create the user
        user_data = {
            'username': username,
            'email': email,
            'firstName': first_name,
            'lastName': last_name,
            'enabled': True,
            'credentials': [{
                'type': 'password',
                'value': password,
                'temporary': False
            }]
        }
        
        # Create user via Keycloak
        user_id = user_manager.create_user(user_data)
        print(f"✅ User created successfully with ID: {user_id}")
        
        # Assign admin role if available
        try:
            user_manager.assign_role(user_id, 'admin')
            print("✅ Admin role assigned successfully")
        except Exception as e:
            print(f"⚠️  Could not assign admin role: {e}")
            print("   You can assign roles manually in Keycloak Admin Console")
        
        print(f"\n🎉 Admin user '{username}' created successfully!")
        print(f"📍 You can now login at: http://localhost:8000")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        print("\n💡 Troubleshooting:")
        print("   - Ensure Keycloak is running (http://localhost:8080)")
        print("   - Check your configuration in config.yaml")
        print("   - Verify the realm 'ams-portal' exists")
        return False

def check_prerequisites():
    """Check if prerequisites are met."""
    print("🔍 Checking prerequisites...")
    
    # Check if config file exists
    config_file = project_root / "config.yaml"
    if not config_file.exists():
        print("❌ config.yaml not found. Please create it from config.template.yaml")
        return False
    
    # Check environment setup
    try:
        from core.settings.managers.users import user_manager
        print("✅ User manager available")
        return True
    except Exception as e:
        print(f"❌ Cannot import user manager: {e}")
        print("   Make sure the application dependencies are installed")
        return False

def main():
    """Main function."""
    print("AMS Data Portal - Admin User Creation Script")
    print("=" * 50)
    
    if not check_prerequisites():
        print("\n❌ Prerequisites not met. Please fix the issues above.")
        sys.exit(1)
    
    if not create_admin_user():
        print("\n❌ Failed to create admin user.")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("✅ Setup complete! You can now access the AMS Data Portal.")

if __name__ == "__main__":
    main()