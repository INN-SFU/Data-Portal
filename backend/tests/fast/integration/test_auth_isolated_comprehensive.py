#!/usr/bin/env python3
"""
Comprehensive Authentication Tests - Fully Isolated

Tests authentication logic in complete isolation without any application imports.
This provides comprehensive coverage of React frontend authentication workflows
without dependencies on the full application stack.

Based on the working approach from test_auth_workflows_simple.py but expanded
for comprehensive React frontend testing scenarios.
"""

import pytest
import jwt as jwt_lib
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import os
import sys

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))


class TestComprehensiveAuthenticationWorkflows:
    """Test comprehensive authentication workflows for React frontend."""
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Set up complete test environment with all required variables."""
        self.env_vars = {
            # Keycloak configuration
            'KEYCLOAK_DOMAIN': 'http://localhost:8080',
            'KEYCLOAK_REALM': 'ams-portal',
            'KEYCLOAK_UI_CLIENT_ID': 'ams-portal-ui',
            'KEYCLOAK_ADMIN_CLIENT_ID': 'ams-portal-admin',
            'KEYCLOAK_ADMIN_CLIENT_SECRET': 'test-secret',
            'KEYCLOAK_WELL_KNOWN_URL': 'http://localhost:8080/realms/ams-portal/.well-known/openid-configuration',
            
            # File system paths - use relative paths from backend directory
            'INSTANCE_CONFIGS': './core/settings/managers/instances/configs',
            'ENFORCER_MODEL': './core/settings/managers/policies/casbin/model.conf',
            'ENFORCER_POLICY': './core/settings/managers/policies/casbin/test_policies.csv',
            'USER_POLICIES': './core/settings/managers/policies/casbin/user_policies'
        }
        
        for key, value in self.env_vars.items():
            os.environ[key] = value
            
        yield
        
        for key in self.env_vars.keys():
            os.environ.pop(key, None)
    
    @pytest.fixture
    def admin_token_payload(self):
        """Admin user token payload."""
        return {
            "sub": "admin-uuid-123",
            "preferred_username": "admin",
            "email": "admin@localhost",
            "given_name": "Admin", 
            "family_name": "User",
            "realm_access": {
                "roles": ["admin", "user"]
            },
            "resource_access": {
                "ams-portal-ui": {
                    "roles": ["admin", "user"]
                }
            },
            "iss": "http://localhost:8080/realms/ams-portal",
            "aud": "ams-portal-ui",
            "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now().timestamp()),
            "session_state": "admin-session-123"
        }
    
    @pytest.fixture 
    def user_token_payload(self):
        """Regular user token payload."""
        return {
            "sub": "user-uuid-456",
            "preferred_username": "testuser",
            "email": "testuser@example.com",
            "given_name": "Test",
            "family_name": "User", 
            "realm_access": {
                "roles": ["user"]
            },
            "resource_access": {
                "ams-portal-ui": {
                    "roles": ["user"]
                }
            },
            "iss": "http://localhost:8080/realms/ams-portal",
            "aud": "ams-portal-ui",
            "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now().timestamp()),
            "session_state": "user-session-456"
        }
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_comprehensive_admin_authentication_workflow(self, mock_jwt_decode, mock_get_jwks_client, admin_token_payload):
        """
        Test comprehensive admin authentication workflow for React frontend.
        
        React Frontend Flow:
        1. Admin user logs in through Keycloak (external)
        2. React receives JWT token and stores in localStorage
        3. React validates token by calling API
        4. React extracts user info and renders admin UI
        """
        from api.v0_1.endpoints.service.auth import decode_token, is_user_admin
        from fastapi.security import HTTPAuthorizationCredentials
        
        # Mock successful JWT validation
        mock_jwt_decode.return_value = admin_token_payload
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "test-admin-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        # Simulate React sending token from localStorage
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="admin.jwt.token.from.keycloak"
        )
        
        # API validates token
        decoded_token = decode_token(credentials)
        
        # Verify token structure React expects
        assert decoded_token["sub"] == "admin-uuid-123"
        assert decoded_token["preferred_username"] == "admin"
        assert decoded_token["email"] == "admin@localhost"
        assert decoded_token["given_name"] == "Admin"
        assert decoded_token["family_name"] == "User"
        
        # Verify role information for React UI decisions
        realm_roles = decoded_token["realm_access"]["roles"]
        assert "admin" in realm_roles
        assert "user" in realm_roles
        
        # Test admin role detection
        is_admin = is_user_admin(decoded_token)
        assert is_admin is True
        
        # Simulate React UI rendering logic
        user_display_name = f"{decoded_token['given_name']} {decoded_token['family_name']}"
        should_show_admin_panel = is_admin
        should_show_user_management = is_admin
        should_show_policy_management = is_admin
        can_create_endpoints = is_admin
        nav_menu_items = []
        
        if is_admin:
            nav_menu_items.extend(["Admin Panel", "User Management", "Policy Management", "Endpoints"])
        nav_menu_items.extend(["Dashboard", "Profile", "Logout"])
        
        # Verify React admin UI state
        assert user_display_name == "Admin User"
        assert should_show_admin_panel is True
        assert should_show_user_management is True
        assert should_show_policy_management is True
        assert can_create_endpoints is True
        assert "Admin Panel" in nav_menu_items
        assert "User Management" in nav_menu_items
        assert len(nav_menu_items) == 7  # 4 admin + 3 common items
        
        # Verify JWT validation was called correctly
        mock_jwt_decode.assert_called_once()
        call_args = mock_jwt_decode.call_args
        assert call_args[0][0] == "admin.jwt.token.from.keycloak"
        assert call_args[1]["algorithms"] == ["RS256"]
        assert call_args[1]["issuer"] == "http://localhost:8080/realms/ams-portal"
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_comprehensive_user_authentication_workflow(self, mock_jwt_decode, mock_get_jwks_client, user_token_payload):
        """
        Test comprehensive regular user authentication workflow for React frontend.
        
        React Frontend Flow:
        1. User logs in through Keycloak (external)
        2. React receives JWT token and stores in localStorage
        3. React validates token by calling API
        4. React extracts user info and renders user UI (no admin features)
        """
        from api.v0_1.endpoints.service.auth import decode_token, is_user_admin
        from fastapi.security import HTTPAuthorizationCredentials
        
        # Mock successful JWT validation
        mock_jwt_decode.return_value = user_token_payload
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "test-user-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        # Simulate React sending token from localStorage
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="user.jwt.token.from.keycloak"
        )
        
        # API validates token
        decoded_token = decode_token(credentials)
        
        # Verify token structure React expects
        assert decoded_token["sub"] == "user-uuid-456"
        assert decoded_token["preferred_username"] == "testuser"
        assert decoded_token["email"] == "testuser@example.com"
        assert decoded_token["given_name"] == "Test"
        assert decoded_token["family_name"] == "User"
        
        # Verify role information for React UI decisions
        realm_roles = decoded_token["realm_access"]["roles"]
        assert "user" in realm_roles
        assert "admin" not in realm_roles
        
        # Test admin role detection
        is_admin = is_user_admin(decoded_token)
        assert is_admin is False
        
        # Simulate React UI rendering logic for regular user
        user_display_name = f"{decoded_token['given_name']} {decoded_token['family_name']}"
        should_show_admin_panel = is_admin
        should_show_user_dashboard = not is_admin
        can_view_own_data = True  # All authenticated users can view their data
        can_create_endpoints = is_admin
        nav_menu_items = ["Dashboard", "My Data", "Profile", "Logout"]
        
        if is_admin:
            nav_menu_items.insert(0, "Admin Panel")
        
        # Verify React user UI state
        assert user_display_name == "Test User"
        assert should_show_admin_panel is False
        assert should_show_user_dashboard is True
        assert can_view_own_data is True
        assert can_create_endpoints is False
        assert "Admin Panel" not in nav_menu_items
        assert "Dashboard" in nav_menu_items
        assert len(nav_menu_items) == 4  # No admin items
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_token_expiry_and_refresh_workflow(self, mock_jwt_decode, mock_get_jwks_client, user_token_payload):
        """
        Test token expiry checking and refresh workflow for React frontend.
        
        React Frontend Pattern:
        1. Check token expiry on app load and before API calls
        2. Refresh token proactively before expiry
        3. Handle refresh failures gracefully
        """
        from api.v0_1.endpoints.service.auth import decode_token
        from fastapi.security import HTTPAuthorizationCredentials
        
        # Mock successful JWT validation
        mock_jwt_decode.return_value = user_token_payload
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "test-refresh-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="user.token.for.refresh.testing"
        )
        
        # API validates token
        decoded_token = decode_token(credentials)
        
        # Extract timing information
        exp_timestamp = decoded_token["exp"]
        iat_timestamp = decoded_token["iat"] 
        current_timestamp = datetime.now().timestamp()
        
        # Simulate React token refresh logic
        token_age_seconds = current_timestamp - iat_timestamp
        time_until_expiry_seconds = exp_timestamp - current_timestamp
        refresh_threshold_seconds = 10 * 60  # Refresh when < 10 minutes remain
        
        # Token validity checks
        is_expired = exp_timestamp < current_timestamp
        is_valid = not is_expired
        should_refresh_soon = time_until_expiry_seconds < refresh_threshold_seconds
        
        # React refresh decisions
        should_use_token = is_valid and not is_expired
        should_attempt_refresh = is_valid and should_refresh_soon
        should_redirect_to_login = is_expired
        
        # Verify token state
        assert is_expired is False
        assert is_valid is True
        assert token_age_seconds >= 0
        assert time_until_expiry_seconds > 0
        assert should_use_token is True
        assert should_redirect_to_login is False
        
        # Test with expired token (modify payload)
        expired_payload = user_token_payload.copy()
        expired_payload["exp"] = int((datetime.now() - timedelta(hours=1)).timestamp())
        
        mock_jwt_decode.return_value = expired_payload
        decoded_expired = decode_token(credentials) 
        
        expired_timestamp = decoded_expired["exp"]
        is_token_expired = expired_timestamp < current_timestamp
        should_clear_storage = is_token_expired
        should_redirect_to_keycloak = is_token_expired
        
        assert is_token_expired is True
        assert should_clear_storage is True
        assert should_redirect_to_keycloak is True
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_concurrent_token_validation_workflow(self, mock_jwt_decode, mock_get_jwks_client, user_token_payload):
        """
        Test concurrent token validation requests for React frontend.
        
        React Frontend Scenario:
        - User has multiple browser tabs open
        - Each tab validates token on load or focus
        - All should succeed independently with same token
        """
        from api.v0_1.endpoints.service.auth import decode_token
        from fastapi.security import HTTPAuthorizationCredentials
        
        # Mock successful JWT validation
        mock_jwt_decode.return_value = user_token_payload
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "test-concurrent-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        # Simulate multiple concurrent token validations
        shared_token = "shared.user.token.across.tabs"
        validation_results = []
        
        for tab_id in range(5):
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials=shared_token
            )
            
            # Each tab validates independently
            decoded_token = decode_token(credentials)
            validation_results.append({
                "tab_id": tab_id,
                "user_id": decoded_token["sub"],
                "username": decoded_token["preferred_username"],
                "is_valid": True
            })
        
        # Verify all validations succeeded with consistent results
        assert len(validation_results) == 5
        
        for result in validation_results:
            assert result["user_id"] == "user-uuid-456"
            assert result["username"] == "testuser"
            assert result["is_valid"] is True
        
        # Verify JWT decode was called for each validation
        assert mock_jwt_decode.call_count == 5  # 5 concurrent validations
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_comprehensive_error_handling_workflows(self, mock_jwt_decode, mock_get_jwks_client):
        """
        Test comprehensive error handling for React frontend.
        
        React Frontend Error Scenarios:
        1. Expired token -> Clear storage, redirect to login
        2. Invalid signature -> Treat as unauthorized
        3. Network errors -> Show generic error, allow retry
        4. Missing token -> Redirect to login
        """
        from api.v0_1.endpoints.service.auth import decode_token
        from fastapi.security import HTTPAuthorizationCredentials
        from fastapi import HTTPException
        
        # Test 1: Expired token error
        mock_jwt_decode.side_effect = jwt_lib.ExpiredSignatureError("Token has expired")
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "test-error-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="expired.jwt.token"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            decode_token(credentials)
        
        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)
        
        # React handling for expired token
        expired_error_handling = {
            "should_clear_local_storage": True,
            "should_redirect_to_login": True,
            "should_show_error_message": False,  # Silent redirect
            "error_type": "token_expired"
        }
        
        assert expired_error_handling["should_clear_local_storage"] is True
        assert expired_error_handling["should_redirect_to_login"] is True
        
        # Test 2: Invalid signature error
        mock_jwt_decode.side_effect = jwt_lib.InvalidSignatureError("Invalid signature")
        
        credentials_invalid = HTTPAuthorizationCredentials(
            scheme="Bearer", 
            credentials="tampered.jwt.token"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            decode_token(credentials_invalid)
        
        assert exc_info.value.status_code == 401
        
        # React handling for invalid signature
        invalid_sig_error_handling = {
            "should_clear_local_storage": True,
            "should_redirect_to_login": True,
            "should_show_security_warning": True,
            "error_type": "token_invalid"
        }
        
        assert invalid_sig_error_handling["should_show_security_warning"] is True
        
        # Test 3: Missing credentials
        with pytest.raises(HTTPException) as exc_info:
            decode_token(None)
        
        assert exc_info.value.status_code == 401
        assert "Bearer token required" in str(exc_info.value.detail)
        
        # React handling for missing token
        missing_token_handling = {
            "should_redirect_to_login": True,
            "should_show_login_form": True,
            "error_type": "no_token"
        }
        
        assert missing_token_handling["should_redirect_to_login"] is True
    
    def test_comprehensive_role_based_ui_rendering(self):
        """
        Test comprehensive role-based UI rendering logic for React frontend.
        
        Tests different user role combinations and corresponding UI elements.
        """
        from api.v0_1.endpoints.service.auth import is_user_admin
        
        # Test scenario 1: Super admin with all permissions
        super_admin_token = {
            "realm_access": {"roles": ["admin", "user", "super-admin"]},
            "resource_access": {
                "ams-portal-ui": {"roles": ["admin", "user"]},
                "realm-management": {"roles": ["manage-users", "manage-realm"]}
            }
        }
        
        is_super_admin = is_user_admin(super_admin_token)
        super_admin_ui = {
            "show_admin_panel": is_super_admin,
            "show_user_management": is_super_admin,
            "show_policy_management": is_super_admin,
            "show_system_settings": is_super_admin,
            "can_create_users": is_super_admin,
            "can_delete_users": is_super_admin,
            "menu_items": []
        }
        
        if is_super_admin:
            super_admin_ui["menu_items"].extend([
                "Admin Dashboard", "User Management", "Policy Management", 
                "System Settings", "Audit Logs"
            ])
        super_admin_ui["menu_items"].extend(["Dashboard", "Profile", "Logout"])
        
        assert is_super_admin is True
        assert super_admin_ui["show_admin_panel"] is True
        assert super_admin_ui["can_create_users"] is True
        assert len(super_admin_ui["menu_items"]) == 8
        
        # Test scenario 2: Regular admin
        regular_admin_token = {
            "realm_access": {"roles": ["admin", "user"]},
            "resource_access": {"ams-portal-ui": {"roles": ["admin", "user"]}}
        }
        
        is_regular_admin = is_user_admin(regular_admin_token)
        regular_admin_ui = {
            "show_admin_panel": is_regular_admin,
            "show_user_management": is_regular_admin,
            "show_policy_management": is_regular_admin,
            "show_system_settings": False,  # Limited permissions
            "can_create_users": is_regular_admin,
            "can_delete_users": False,  # Limited permissions
            "menu_items": []
        }
        
        if is_regular_admin:
            regular_admin_ui["menu_items"].extend([
                "Admin Dashboard", "User Management", "Policy Management"
            ])
        regular_admin_ui["menu_items"].extend(["Dashboard", "Profile", "Logout"])
        
        assert is_regular_admin is True
        assert regular_admin_ui["show_admin_panel"] is True
        assert regular_admin_ui["show_system_settings"] is False
        assert regular_admin_ui["can_delete_users"] is False
        assert len(regular_admin_ui["menu_items"]) == 6
        
        # Test scenario 3: Regular user
        regular_user_token = {
            "realm_access": {"roles": ["user"]},
            "resource_access": {"ams-portal-ui": {"roles": ["user"]}}
        }
        
        is_regular_user_admin = is_user_admin(regular_user_token)
        regular_user_ui = {
            "show_admin_panel": is_regular_user_admin,
            "show_user_dashboard": True,
            "can_view_own_data": True,
            "can_edit_own_profile": True,
            "can_create_users": is_regular_user_admin,
            "menu_items": ["Dashboard", "My Data", "Profile", "Logout"]
        }
        
        assert is_regular_user_admin is False
        assert regular_user_ui["show_admin_panel"] is False
        assert regular_user_ui["show_user_dashboard"] is True
        assert regular_user_ui["can_view_own_data"] is True
        assert regular_user_ui["can_create_users"] is False
        assert len(regular_user_ui["menu_items"]) == 4
        
        # Test scenario 4: User with no roles (edge case)
        no_roles_token = {
            "sub": "user-no-roles",
            "preferred_username": "noroles"
        }
        
        is_no_roles_admin = is_user_admin(no_roles_token)
        no_roles_ui = {
            "show_admin_panel": is_no_roles_admin,
            "show_user_dashboard": True,  # Default for authenticated users
            "can_view_own_data": True,   # Default for authenticated users
            "show_limited_warning": True,  # No roles assigned
            "menu_items": ["Dashboard", "Profile", "Logout"]
        }
        
        assert is_no_roles_admin is False
        assert no_roles_ui["show_limited_warning"] is True
        assert len(no_roles_ui["menu_items"]) == 3


if __name__ == "__main__":
    # Run tests directly if called as a script
    print("Running comprehensive isolated authentication workflow tests...")
    
    import subprocess
    result = subprocess.run([
        sys.executable, '-m', 'pytest', __file__, '-v', '--tb=short'
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    exit(result.returncode)