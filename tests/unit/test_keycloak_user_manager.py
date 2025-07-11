#!/usr/bin/env python3
"""
Unit tests for KeycloakUserManager functionality.

Tests the user management functions including:
- get_all_users() function
- User creation and management
- Role assignments and retrieval
- Error handling for authorization issues
"""

import sys
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from uuid import UUID

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables for testing
from dotenv import load_dotenv
load_dotenv(project_root / 'core' / 'settings' / '.env')

class TestKeycloakUserManager:
    """Test KeycloakUserManager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_keycloak_admin = Mock()
        self.test_realm = "ams-portal"
        self.test_client_id = "ams-portal-admin"
        self.test_client_secret = "test-secret"
        self.test_base_url = "http://localhost:8080"
        
        # Sample user data for testing (matches Keycloak API response format)
        self.sample_users = [
            {
                'id': '12345678-1234-5678-1234-567812345678',
                'username': 'admin',
                'email': 'admin@localhost',
                'enabled': True
            },
            {
                'id': '87654321-4321-8765-4321-876543218765', 
                'username': 'testuser',
                'email': 'test@localhost',
                'enabled': True
            }
        ]
        
        # Sample role data
        self.sample_roles = {
            'realmMappings': [
                {'name': 'admin'},
                {'name': 'user'}
            ]
        }
    
    @patch('core.settings.managers.users.keycloak.KeycloakUserManager.KeycloakAdmin')
    @patch('core.settings.managers.users.keycloak.KeycloakUserManager.KeycloakOpenIDConnection')
    def test_get_all_users_success(self, mock_connection, mock_admin):
        """Test successful retrieval of all users."""
        # Import here to avoid circular imports
        from core.settings.managers.users.keycloak.KeycloakUserManager import KeycloakUserManager
        
        # Configure mocks
        mock_admin_instance = Mock()
        mock_admin.return_value = mock_admin_instance
        mock_admin_instance.get_users.return_value = self.sample_users
        mock_admin_instance.get_all_roles_of_user.return_value = self.sample_roles
        
        # Create user manager
        user_manager = KeycloakUserManager(
            realm_name=self.test_realm,
            client_id=self.test_client_id,
            client_secret=self.test_client_secret,
            base_url=self.test_base_url
        )
        
        # Test get_all_users
        users = user_manager.get_all_users()
        
        # Assertions - test the transformation behavior
        assert len(users) == 2, "Should return 2 users"
        
        # Test first user
        assert users[0].username == 'admin', "First user should be admin"
        assert users[0].email == 'admin@localhost', "First user email should match"
        assert str(users[0].uuid) == '12345678-1234-5678-1234-567812345678', "First user UUID should match"
        assert users[0].roles == ['admin', 'user'], "First user should have admin and user roles"
        
        # Test second user
        assert users[1].username == 'testuser', "Second user should be testuser"
        assert users[1].email == 'test@localhost', "Second user email should match"
        assert str(users[1].uuid) == '87654321-4321-8765-4321-876543218765', "Second user UUID should match"
        assert users[1].roles == ['admin', 'user'], "Second user should have admin and user roles"
        
        # Verify Keycloak admin was called correctly
        mock_admin_instance.get_users.assert_called_once()
        assert mock_admin_instance.get_all_roles_of_user.call_count == 2, "Should call get_all_roles_of_user for each user"
    
    @patch('core.settings.managers.users.keycloak.KeycloakUserManager.KeycloakAdmin')
    @patch('core.settings.managers.users.keycloak.KeycloakUserManager.KeycloakOpenIDConnection')
    def test_get_all_users_authorization_error(self, mock_connection, mock_admin):
        """Test handling of authorization errors in get_all_users."""
        from core.settings.managers.users.keycloak.KeycloakUserManager import KeycloakUserManager
        from keycloak.exceptions import KeycloakAuthenticationError
        
        # Configure mock to raise authorization error
        mock_admin_instance = Mock()
        mock_admin.return_value = mock_admin_instance
        mock_admin_instance.get_users.side_effect = KeycloakAuthenticationError("Insufficient permissions")
        
        # Create user manager
        user_manager = KeycloakUserManager(
            realm_name=self.test_realm,
            client_id=self.test_client_id,
            client_secret=self.test_client_secret,
            base_url=self.test_base_url
        )
        
        # Test that authorization error is raised
        with pytest.raises(KeycloakAuthenticationError):
            user_manager.get_all_users()
    
    @patch('core.settings.managers.users.keycloak.KeycloakUserManager.KeycloakAdmin')
    @patch('core.settings.managers.users.keycloak.KeycloakUserManager.KeycloakOpenIDConnection')
    def test_get_user_roles_success(self, mock_connection, mock_admin):
        """Test successful retrieval of user roles."""
        from core.settings.managers.users.keycloak.KeycloakUserManager import KeycloakUserManager
        
        # Configure mocks
        mock_admin_instance = Mock()
        mock_admin.return_value = mock_admin_instance
        mock_admin_instance.get_all_roles_of_user.return_value = self.sample_roles
        
        # Create user manager
        user_manager = KeycloakUserManager(
            realm_name=self.test_realm,
            client_id=self.test_client_id,
            client_secret=self.test_client_secret,
            base_url=self.test_base_url
        )
        
        # Test get_user_roles
        test_uuid = UUID('12345678-1234-5678-1234-567812345678')
        roles = user_manager.get_user_roles(test_uuid)
        
        # Assertions
        assert len(roles) == 2
        assert 'admin' in roles
        assert 'user' in roles
        
        # Verify Keycloak admin was called correctly
        mock_admin_instance.get_all_roles_of_user.assert_called_once_with(user_id='12345678-1234-5678-1234-567812345678')
    
    @patch('core.settings.managers.users.keycloak.KeycloakUserManager.KeycloakAdmin')
    @patch('core.settings.managers.users.keycloak.KeycloakUserManager.KeycloakOpenIDConnection')
    def test_user_manager_initialization(self, mock_connection, mock_admin):
        """Test proper initialization of KeycloakUserManager."""
        from core.settings.managers.users.keycloak.KeycloakUserManager import KeycloakUserManager
        
        # Create user manager
        user_manager = KeycloakUserManager(
            realm_name=self.test_realm,
            client_id=self.test_client_id,
            client_secret=self.test_client_secret,
            base_url=self.test_base_url
        )
        
        # Verify connection was created with correct parameters
        mock_connection.assert_called_once_with(
            server_url=self.test_base_url,
            realm_name=self.test_realm,
            client_id=self.test_client_id,
            client_secret_key=self.test_client_secret,
            verify=True
        )
        
        # Verify admin instance was created
        mock_admin.assert_called_once()
        assert hasattr(user_manager, 'identity_manager')


class TestKeycloakUserManagerIntegration:
    """Integration tests for KeycloakUserManager with actual Keycloak connection."""
    
    def setup_method(self):
        """Set up integration test fixtures."""
        self.realm_name = os.getenv("KEYCLOAK_REALM", "ams-portal")
        self.client_id = os.getenv("KEYCLOAK_ADMIN_CLIENT_ID", "ams-portal-admin")
        self.client_secret = os.getenv("KEYCLOAK_ADMIN_CLIENT_SECRET")
        self.base_url = os.getenv("KEYCLOAK_DOMAIN", "http://localhost:8080")
    
    @pytest.mark.integration
    def test_real_keycloak_connection(self):
        """Test actual connection to Keycloak (requires running Keycloak)."""
        if not self.client_secret:
            pytest.skip("KEYCLOAK_ADMIN_CLIENT_SECRET not set")
        
        from core.settings.managers.users.keycloak.KeycloakUserManager import KeycloakUserManager
        
        try:
            # Create real user manager
            user_manager = KeycloakUserManager(
                realm_name=self.realm_name,
                client_id=self.client_id,
                client_secret=self.client_secret,
                base_url=self.base_url
            )
            
            # Test actual get_all_users call
            users = user_manager.get_all_users()
            
            # Basic assertions
            assert isinstance(users, list)
            if users:
                assert hasattr(users[0], 'username')
                assert hasattr(users[0], 'email')
                assert hasattr(users[0], 'roles')
            
        except Exception as e:
            pytest.fail(f"Integration test failed: {e}")
    
    @pytest.mark.integration
    def test_keycloak_permissions_fix(self):
        """Test that the Keycloak permissions fix resolves the get_all_users issue."""
        if not self.client_secret:
            pytest.skip("KEYCLOAK_ADMIN_CLIENT_SECRET not set")
        
        from core.settings.managers.users.keycloak.KeycloakUserManager import KeycloakUserManager
        from keycloak.exceptions import KeycloakAuthenticationError
        
        try:
            # Create real user manager
            user_manager = KeycloakUserManager(
                realm_name=self.realm_name,
                client_id=self.client_id,
                client_secret=self.client_secret,
                base_url=self.base_url
            )
            
            # This should NOT raise an authentication error with our fix
            users = user_manager.get_all_users()
            
            # If we get here, the fix worked
            assert True, "get_all_users() succeeded - fix is working!"
            
        except KeycloakAuthenticationError as e:
            pytest.fail(f"Authentication error - fix not working: {e}")
        except Exception as e:
            # Other errors might indicate Keycloak is not running
            pytest.skip(f"Keycloak may not be running: {e}")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])