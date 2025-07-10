"""
Step definitions for admin user automation tests.
"""

import json
import subprocess
import time
import requests
from behave import given, when, then
from unittest.mock import patch
import tempfile
import yaml


@given('Keycloak is running')
def step_keycloak_running(context):
    """Verify Keycloak is running."""
    try:
        # Check if Keycloak container is running
        result = subprocess.run(
            ['docker', 'ps', '--filter', 'name=ams-keycloak', '--format', '{{.Names}}'],
            capture_output=True, text=True, timeout=10
        )
        assert 'ams-keycloak' in result.stdout, "Keycloak container is not running"
        
        # Check if Keycloak is responsive
        response = requests.get('http://localhost:8080', timeout=5)
        assert response.status_code == 200, "Keycloak is not responding"
        
        context.keycloak_running = True
    except Exception as e:
        context.keycloak_running = False
        raise AssertionError(f"Keycloak is not available: {e}")


@given('the AMS realm is configured')
def step_ams_realm_configured(context):
    """Verify the AMS realm exists in Keycloak."""
    try:
        # Configure kcadm
        subprocess.run([
            'docker', 'exec', 'ams-keycloak',
            '/opt/keycloak/bin/kcadm.sh', 'config', 'credentials',
            '--server', 'http://localhost:8080',
            '--realm', 'master',
            '--user', 'admin',
            '--password', 'admin123'
        ], check=True, capture_output=True)
        
        # Check if realm exists
        result = subprocess.run([
            'docker', 'exec', 'ams-keycloak',
            '/opt/keycloak/bin/kcadm.sh', 'get', 'realms/ams-portal'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            realm_data = json.loads(result.stdout)
            assert realm_data['realm'] == 'ams-portal', "AMS realm not properly configured"
            context.realm_configured = True
        else:
            context.realm_configured = False
            
    except Exception as e:
        context.realm_configured = False
        raise AssertionError(f"AMS realm not available: {e}")


@given('I run the full automated setup')
def step_run_full_setup(context):
    """Run the full automated setup script."""
    try:
        # Run the setup script
        result = subprocess.run([
            'python3', 'scripts/setup.py', '--full-setup'
        ], capture_output=True, text=True, timeout=300, cwd=context.project_root)
        
        context.setup_result = result
        context.setup_stdout = result.stdout
        context.setup_stderr = result.stderr
        context.setup_returncode = result.returncode
        
    except subprocess.TimeoutExpired:
        raise AssertionError("Setup script timed out after 5 minutes")
    except Exception as e:
        raise AssertionError(f"Failed to run setup script: {e}")


@when('the Keycloak realm is imported')
def step_realm_imported(context):
    """Check that the realm import was successful."""
    assert hasattr(context, 'setup_stdout'), "Setup has not been run"
    assert "✓ Keycloak realm configured" in context.setup_stdout, "Realm was not configured successfully"


@then('the admin user should be automatically configured')
def step_admin_user_configured(context):
    """Verify admin user was configured automatically."""
    assert hasattr(context, 'setup_stdout'), "Setup has not been run"
    assert "✓ Admin user configured successfully" in context.setup_stdout, "Admin user was not configured"


@then('the admin user should have proper credentials set')
def step_admin_credentials_set(context):
    """Verify admin user credentials are properly set."""
    try:
        # Try to authenticate as admin user
        result = subprocess.run([
            'docker', 'exec', 'ams-keycloak',
            '/opt/keycloak/bin/kcadm.sh', 'config', 'credentials',
            '--server', 'http://localhost:8080',
            '--realm', 'ams-portal',
            '--user', 'admin',
            '--password', 'admin123'
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, f"Admin user authentication failed: {result.stderr}"
        
    except Exception as e:
        raise AssertionError(f"Failed to verify admin credentials: {e}")


@then('the admin user should have no required actions')
def step_no_required_actions(context):
    """Verify admin user has no required actions."""
    try:
        # Get admin user details
        result = subprocess.run([
            'docker', 'exec', 'ams-keycloak',
            '/opt/keycloak/bin/kcadm.sh', 'get', 'users',
            '--server', 'http://localhost:8080',
            '--realm', 'master',
            '--user', 'admin',
            '--password', 'admin123',
            '--target-realm', 'ams-portal',
            '--query', 'username=admin'
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, "Failed to get admin user details"
        
        users = json.loads(result.stdout)
        assert len(users) > 0, "Admin user not found"
        
        admin_user = users[0]
        required_actions = admin_user.get('requiredActions', [])
        assert len(required_actions) == 0, f"Admin user has required actions: {required_actions}"
        
    except Exception as e:
        raise AssertionError(f"Failed to verify required actions: {e}")


@then('the admin user should have admin role assigned')
def step_admin_role_assigned(context):
    """Verify admin user has admin role."""
    try:
        # Get admin user ID first
        result = subprocess.run([
            'docker', 'exec', 'ams-keycloak',
            '/opt/keycloak/bin/kcadm.sh', 'get', 'users',
            '--server', 'http://localhost:8080',
            '--realm', 'master',
            '--user', 'admin',
            '--password', 'admin123',
            '--target-realm', 'ams-portal',
            '--query', 'username=admin'
        ], capture_output=True, text=True)
        
        users = json.loads(result.stdout)
        admin_user_id = users[0]['id']
        
        # Get user's realm role mappings
        result = subprocess.run([
            'docker', 'exec', 'ams-keycloak',
            '/opt/keycloak/bin/kcadm.sh', 'get', f'users/{admin_user_id}/role-mappings/realm',
            '--server', 'http://localhost:8080',
            '--realm', 'master',
            '--user', 'admin',
            '--password', 'admin123',
            '--target-realm', 'ams-portal'
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, "Failed to get user role mappings"
        
        roles = json.loads(result.stdout)
        role_names = [role['name'] for role in roles]
        assert 'admin' in role_names, f"Admin role not assigned. User has roles: {role_names}"
        
    except Exception as e:
        raise AssertionError(f"Failed to verify admin role: {e}")


@then('the UI client should have protocol mappers configured')
def step_protocol_mappers_configured(context):
    """Verify UI client has protocol mappers."""
    assert hasattr(context, 'setup_stdout'), "Setup has not been run"
    assert "✓ Protocol mappers configured" in context.setup_stdout, "Protocol mappers were not configured"


@given('the automated setup has completed successfully')
def step_setup_completed(context):
    """Ensure automated setup completed successfully."""
    if not hasattr(context, 'setup_result'):
        # Run the setup if it hasn't been run
        step_run_full_setup(context)
    
    assert context.setup_returncode == 0, f"Setup failed with return code {context.setup_returncode}"
    assert "🎉 SETUP COMPLETE!" in context.setup_stdout, "Setup did not complete successfully"


@when('I navigate to the AMS Portal login page')
def step_navigate_to_login(context):
    """Navigate to the login page."""
    # This would typically use a web driver, but for now we'll simulate
    context.login_url = "http://localhost:8000/auth/login"


@when('I enter admin credentials "{username}" and "{password}"')
def step_enter_credentials(context, username, password):
    """Enter admin credentials."""
    context.test_username = username
    context.test_password = password


@then('I should be successfully authenticated')
def step_authenticated_successfully(context):
    """Verify successful authentication."""
    # This would require a full web driver test or API test
    # For now, we'll verify the credentials work with Keycloak directly
    try:
        result = subprocess.run([
            'docker', 'exec', 'ams-keycloak',
            '/opt/keycloak/bin/kcadm.sh', 'config', 'credentials',
            '--server', 'http://localhost:8080',
            '--realm', 'ams-portal',
            '--user', context.test_username,
            '--password', context.test_password
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, f"Authentication failed: {result.stderr}"
        
    except Exception as e:
        raise AssertionError(f"Authentication test failed: {e}")


@then('I should see the admin home template')
def step_see_admin_template(context):
    """Verify admin template is shown."""
    # This would require testing the actual application with a logged-in user
    # For now, we'll verify the admin role is properly assigned
    step_admin_role_assigned(context)


@then('the JWT token should contain preferred_username')
def step_jwt_contains_username(context):
    """Verify JWT token contains preferred_username."""
    # This would require testing an actual JWT token from the application
    # For now, we'll verify the protocol mapper exists
    step_protocol_mappers_configured(context)


@then('the JWT token should contain realm roles')
def step_jwt_contains_roles(context):
    """Verify JWT token contains realm roles."""
    # This would require testing an actual JWT token from the application
    # For now, we'll verify the protocol mapper exists
    step_protocol_mappers_configured(context)


@given('an admin user already exists in Keycloak')
def step_admin_user_exists(context):
    """Ensure admin user exists before setup."""
    # The admin user should already exist from realm import
    step_admin_user_configured(context)


@given('the admin user has required actions set')
def step_admin_has_required_actions(context):
    """Set required actions on admin user."""
    try:
        # Get admin user ID
        result = subprocess.run([
            'docker', 'exec', 'ams-keycloak',
            '/opt/keycloak/bin/kcadm.sh', 'get', 'users',
            '--server', 'http://localhost:8080',
            '--realm', 'master',
            '--user', 'admin',
            '--password', 'admin123',
            '--target-realm', 'ams-portal',
            '--query', 'username=admin'
        ], capture_output=True, text=True)
        
        users = json.loads(result.stdout)
        admin_user_id = users[0]['id']
        
        # Set required actions
        subprocess.run([
            'docker', 'exec', 'ams-keycloak',
            '/opt/keycloak/bin/kcadm.sh', 'update', f'users/{admin_user_id}',
            '--server', 'http://localhost:8080',
            '--realm', 'master',
            '--user', 'admin',
            '--password', 'admin123',
            '--target-realm', 'ams-portal',
            '-s', 'requiredActions=["UPDATE_PASSWORD"]'
        ], check=True, capture_output=True)
        
    except Exception as e:
        raise AssertionError(f"Failed to set required actions: {e}")


@when('I run the automated setup')
def step_run_automated_setup(context):
    """Run the automated setup."""
    step_run_full_setup(context)


@then('the existing admin user should be updated')
def step_existing_user_updated(context):
    """Verify existing user was updated."""
    step_admin_user_configured(context)


@then('the required actions should be removed')
def step_required_actions_removed(context):
    """Verify required actions were removed."""
    step_no_required_actions(context)


@then('the password should be set to "{password}"')
def step_password_set(context, password):
    """Verify password was set correctly."""
    context.test_password = password
    step_authenticated_successfully(context)


@then('the protocol mappers should be added or updated')
def step_protocol_mappers_updated(context):
    """Verify protocol mappers were added or updated."""
    step_protocol_mappers_configured(context)


@given('I run the automated setup multiple times')
def step_run_setup_multiple_times(context):
    """Run setup multiple times to test consistency."""
    context.setup_runs = []
    
    for i in range(2):  # Run twice to test consistency
        try:
            result = subprocess.run([
                'python3', 'scripts/setup.py', '--full-setup'
            ], capture_output=True, text=True, timeout=300, cwd=context.project_root)
            
            context.setup_runs.append({
                'run': i + 1,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            })
            
            # Small delay between runs
            time.sleep(5)
            
        except Exception as e:
            raise AssertionError(f"Setup run {i + 1} failed: {e}")


@when('the Keycloak realm is recreated each time')
def step_realm_recreated_each_time(context):
    """Verify realm was recreated in each setup run."""
    assert hasattr(context, 'setup_runs'), "Multiple setup runs have not been executed"
    
    for run in context.setup_runs:
        assert "✓ Cleaned up existing realm" in run['stdout'], f"Realm not cleaned up in run {run['run']}"
        assert "✓ Keycloak realm configured" in run['stdout'], f"Realm not configured in run {run['run']}"


@then('a fresh client secret should be generated each time')
def step_fresh_secret_each_time(context):
    """Verify fresh client secret was generated."""
    for run in context.setup_runs:
        assert "✓ Client secret retrieved successfully" in run['stdout'], f"Client secret not retrieved in run {run['run']}"
        assert "✓ Updated config.yaml with client secret" in run['stdout'], f"Config not updated in run {run['run']}"


@then('the admin user should be configured consistently')
def step_admin_configured_consistently(context):
    """Verify admin user configured in each run."""
    for run in context.setup_runs:
        assert "✓ Admin user configured successfully" in run['stdout'], f"Admin user not configured in run {run['run']}"


@then('the config.yaml should be updated with the new secret')
def step_config_updated_with_secret(context):
    """Verify config.yaml was updated."""
    for run in context.setup_runs:
        assert "✓ Updated config.yaml with client secret" in run['stdout'], f"Config not updated in run {run['run']}"


@then('the admin user authentication should work with each setup')
def step_auth_works_with_each_setup(context):
    """Verify admin authentication works after each setup."""
    # Test authentication after the last setup run
    context.test_username = "admin"
    context.test_password = "admin123"
    step_authenticated_successfully(context)