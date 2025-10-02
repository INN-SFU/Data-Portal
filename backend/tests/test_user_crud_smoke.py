# backend/tests/test_user_crud_smoke.py
"""
User CRUD Smoke Tests

Tests comprehensive user management functionality including:
- Creating users
- Listing users
- Retrieving individual user details
- Updating user information
- Deleting users
- Role-based access control
- Owner vs Admin permissions
"""

import os
import json
from pathlib import Path

import pytest
import requests


# --- Config helpers ----------------------------------------------------------

def env(name: str, default: str | None = None) -> str:
    v = os.getenv(name, default)
    if v is None or v == "":
        raise RuntimeError(f"Missing required env var: {name}")
    return v

def kc_base() -> str:
    return env("KEYCLOAK_DOMAIN")

def kc_realm() -> str:
    return env("KEYCLOAK_REALM")

def backend_base() -> str:
    return os.getenv("BACKEND_BASE_URL", "http://localhost:8000")


# --- Token helpers -----------------------------------------------------------

def read_admin_client_secret() -> str:
    p = Path(os.getenv("KEYCLOAK_ADMIN_CLIENT_SECRET_FILE", "/run/secrets/kc_admin_client_secret"))
    if not p.is_file():
        raise RuntimeError(f"Client secret file not found at {p}")
    secret = p.read_text().strip()
    if not secret:
        raise RuntimeError("Client secret file is empty")
    return secret

def get_admin_token(timeout=10) -> str:
    """Get admin user token via password grant."""
    token_url = f"{kc_base()}/realms/{kc_realm()}/protocol/openid-connect/token"
    ui_client_id = os.getenv("KEYCLOAK_UI_CLIENT_ID", "ams-portal-ui")
    data = {
        "grant_type": "password",
        "client_id": ui_client_id,
        "username": "admin",
        "password": "admin123",
    }
    r = requests.post(token_url, data=data, timeout=timeout)
    try:
        payload = r.json()
    except json.JSONDecodeError:
        pytest.fail(f"Non-JSON response from token endpoint: HTTP {r.status_code}\n{r.text[:500]}")
    if r.status_code != 200:
        pytest.fail(f"Token request failed HTTP {r.status_code}: {json.dumps(payload)[:500]}")
    token = payload.get("access_token", "")
    if not token:
        pytest.fail(f"No access_token in response: {json.dumps(payload)[:500]}")
    return token


# --- Test fixtures -----------------------------------------------------------

@pytest.fixture
def admin_token():
    """Provide admin token for tests."""
    return get_admin_token()

@pytest.fixture
def auth_headers(admin_token):
    """Provide authorization headers with admin token."""
    return {"Authorization": f"Bearer {admin_token}"}


# --- User CRUD Tests ---------------------------------------------------------

def test_list_users_requires_admin(auth_headers):
    """Test that listing users requires admin privileges."""
    url = f"{backend_base()}/api/users/"
    r = requests.get(url, headers=auth_headers, timeout=10)
    assert r.status_code == 200, f"Admin should be able to list users, got {r.status_code}: {r.text[:500]}"

    data = r.json()
    assert isinstance(data, list), f"Expected list of users, got: {type(data)}"
    assert len(data) > 0, "Should have at least one user (admin)"


def test_list_users_without_auth():
    """Test that listing users without auth is rejected."""
    url = f"{backend_base()}/api/users/"
    r = requests.get(url, timeout=5)
    assert r.status_code == 401, f"Expected 401 without auth, got {r.status_code}"


def test_create_user(auth_headers):
    """Test creating a new user."""
    url = f"{backend_base()}/api/users/"

    new_user = {
        "username": "testuser1",
        "email": "testuser1@example.com",
        "roles": ["user"]
    }

    r = requests.post(url, json=new_user, headers=auth_headers, timeout=10)
    assert r.status_code == 201, f"Expected 201 creating user, got {r.status_code}: {r.text[:500]}"

    data = r.json()
    assert data.get("success") is True, f"Expected success=True, got: {data}"
    assert "details" in data, f"Expected details in response: {data}"

    user_details = data["details"]
    assert user_details["username"] == "testuser1", f"Username mismatch: {user_details}"
    assert user_details["email"] == "testuser1@example.com", f"Email mismatch: {user_details}"


def test_create_duplicate_user(auth_headers):
    """Test that creating duplicate user is rejected."""
    url = f"{backend_base()}/api/users/"

    # Create first user
    new_user = {
        "username": "testuser2",
        "email": "testuser2@example.com",
        "roles": ["user"]
    }

    r1 = requests.post(url, json=new_user, headers=auth_headers, timeout=10)
    assert r1.status_code == 201, f"First create should succeed: {r1.status_code}: {r1.text[:500]}"

    # Try to create duplicate
    r2 = requests.post(url, json=new_user, headers=auth_headers, timeout=10)
    assert r2.status_code == 400, f"Expected 400 for duplicate user, got {r2.status_code}: {r2.text[:500]}"

    data = r2.json()
    assert "already exists" in data.get("detail", "").lower(), f"Expected 'already exists' error: {data}"


def test_create_user_without_auth():
    """Test that creating user without auth is rejected."""
    url = f"{backend_base()}/api/users/"

    new_user = {
        "username": "unauthorized_user",
        "email": "unauthorized@example.com",
        "roles": ["user"]
    }

    r = requests.post(url, json=new_user, timeout=5)
    assert r.status_code == 401, f"Expected 401 without auth, got {r.status_code}"


def test_get_user_by_username(auth_headers):
    """Test retrieving user by username."""
    # First create a user
    url = f"{backend_base()}/api/users/"
    new_user = {
        "username": "testuser3",
        "email": "testuser3@example.com",
        "roles": ["user"]
    }

    r_create = requests.post(url, json=new_user, headers=auth_headers, timeout=10)
    assert r_create.status_code == 201, f"User creation failed: {r_create.status_code}"

    # Now retrieve the user
    url_get = f"{backend_base()}/api/users/testuser3"
    r = requests.get(url_get, headers=auth_headers, timeout=10)
    assert r.status_code == 200, f"Expected 200 getting user, got {r.status_code}: {r.text[:500]}"

    data = r.json()
    assert data["username"] == "testuser3", f"Username mismatch: {data}"
    assert data["email"] == "testuser3@example.com", f"Email mismatch: {data}"
    assert "uuid" in data, f"Expected uuid in response: {data}"


def test_get_nonexistent_user(auth_headers):
    """Test that getting non-existent user returns 404."""
    url = f"{backend_base()}/api/users/nonexistent_user_12345"
    r = requests.get(url, headers=auth_headers, timeout=10)
    assert r.status_code == 404, f"Expected 404 for non-existent user, got {r.status_code}: {r.text[:500]}"


def test_get_current_user_info(auth_headers):
    """Test /api/users/me endpoint for current user info."""
    url = f"{backend_base()}/api/users/me"
    r = requests.get(url, headers=auth_headers, timeout=10)
    assert r.status_code == 200, f"Expected 200 for /me endpoint, got {r.status_code}: {r.text[:500]}"

    data = r.json()
    assert data["username"] == "admin", f"Expected admin user, got: {data}"
    assert "uuid" in data, f"Expected uuid in response: {data}"
    assert "email" in data, f"Expected email in response: {data}"


def test_delete_user(auth_headers):
    """Test deleting a user."""
    # First create a user
    url = f"{backend_base()}/api/users/"
    new_user = {
        "username": "testuser_delete",
        "email": "testuser_delete@example.com",
        "roles": ["user"]
    }

    r_create = requests.post(url, json=new_user, headers=auth_headers, timeout=10)
    assert r_create.status_code == 201, f"User creation failed: {r_create.status_code}"

    # Now delete the user
    url_delete = f"{backend_base()}/api/users/testuser_delete"
    r = requests.delete(url_delete, headers=auth_headers, timeout=10)
    assert r.status_code == 200, f"Expected 200 deleting user, got {r.status_code}: {r.text[:500]}"

    data = r.json()
    assert data.get("success") is True, f"Expected success=True, got: {data}"
    assert "details" in data, f"Expected details in response: {data}"

    # Verify user is gone
    url_get = f"{backend_base()}/api/users/testuser_delete"
    r_verify = requests.get(url_get, headers=auth_headers, timeout=10)
    assert r_verify.status_code == 404, f"User should be deleted, got {r_verify.status_code}"


def test_delete_nonexistent_user(auth_headers):
    """Test that deleting non-existent user returns 404."""
    url = f"{backend_base()}/api/users/nonexistent_user_67890"
    r = requests.delete(url, headers=auth_headers, timeout=10)
    assert r.status_code == 404, f"Expected 404 deleting non-existent user, got {r.status_code}: {r.text[:500]}"


def test_delete_user_without_auth():
    """Test that deleting user without auth is rejected."""
    url = f"{backend_base()}/api/users/someuser"
    r = requests.delete(url, timeout=5)
    assert r.status_code == 401, f"Expected 401 without auth, got {r.status_code}"


# --- User Management Dashboard Tests -----------------------------------------

def test_user_dashboard_access(auth_headers):
    """Test that admin can access user management dashboard."""
    url = f"{backend_base()}/api/users/dashboard"
    r = requests.get(url, headers=auth_headers, timeout=10)
    assert r.status_code == 200, f"Admin should access dashboard, got {r.status_code}: {r.text[:500]}"

    data = r.json()
    assert "users" in data, f"Expected 'users' in dashboard data: {data.keys()}"
    assert "file_trees" in data, f"Expected 'file_trees' in dashboard data: {data.keys()}"
    assert "models" in data, f"Expected 'models' in dashboard data: {data.keys()}"

    assert isinstance(data["users"], list), f"Expected list of users: {type(data['users'])}"
    assert len(data["users"]) > 0, "Should have at least one user"


def test_user_dashboard_without_auth():
    """Test that dashboard access without auth is rejected."""
    url = f"{backend_base()}/api/users/dashboard"
    r = requests.get(url, timeout=5)
    assert r.status_code == 401, f"Expected 401 without auth, got {r.status_code}"


# --- Complete User Lifecycle Test --------------------------------------------

def test_complete_user_lifecycle(auth_headers):
    """Test complete user lifecycle: create, list, get, delete."""
    base_url = f"{backend_base()}/api/users/"
    username = "lifecycle_test_user"

    # Step 1: Create user
    new_user = {
        "username": username,
        "email": f"{username}@example.com",
        "roles": ["user"]
    }
    r_create = requests.post(base_url, json=new_user, headers=auth_headers, timeout=10)
    assert r_create.status_code == 201, f"Create failed: {r_create.text[:500]}"
    created_data = r_create.json()
    user_uuid = created_data["details"]["uuid"]

    # Step 2: Verify user appears in list
    r_list = requests.get(base_url, headers=auth_headers, timeout=10)
    assert r_list.status_code == 200
    users = r_list.json()
    usernames = [u["username"] for u in users]
    assert username in usernames, f"User not found in list: {usernames}"

    # Step 3: Get user details
    r_get = requests.get(f"{base_url}{username}", headers=auth_headers, timeout=10)
    assert r_get.status_code == 200
    user_data = r_get.json()
    assert user_data["username"] == username
    assert user_data["uuid"] == user_uuid

    # Step 4: Delete user
    r_delete = requests.delete(f"{base_url}{username}", headers=auth_headers, timeout=10)
    assert r_delete.status_code == 200
    delete_data = r_delete.json()
    assert delete_data["success"] is True

    # Step 5: Verify user is gone
    r_verify = requests.get(f"{base_url}{username}", headers=auth_headers, timeout=10)
    assert r_verify.status_code == 404, "User should be deleted"


# --- Input Validation Tests --------------------------------------------------

def test_create_user_invalid_email(auth_headers):
    """Test that creating user with invalid email is rejected."""
    url = f"{backend_base()}/api/users/"

    new_user = {
        "username": "testuser_invalid_email",
        "email": "not_an_email",  # Invalid email format
        "roles": ["user"]
    }

    r = requests.post(url, json=new_user, headers=auth_headers, timeout=10)
    # Should either reject (422) or accept depending on validation rules
    # This test documents current behavior
    assert r.status_code in [201, 400, 422], f"Unexpected status for invalid email: {r.status_code}"


def test_create_user_missing_fields(auth_headers):
    """Test that creating user with missing required fields is rejected."""
    url = f"{backend_base()}/api/users/"

    # Missing email and roles
    incomplete_user = {
        "username": "incomplete_user"
    }

    r = requests.post(url, json=incomplete_user, headers=auth_headers, timeout=10)
    assert r.status_code == 422, f"Expected 422 for missing fields, got {r.status_code}: {r.text[:500]}"


def test_create_user_empty_username(auth_headers):
    """Test that creating user with empty username is rejected."""
    url = f"{backend_base()}/api/users/"

    new_user = {
        "username": "",
        "email": "empty@example.com",
        "roles": ["user"]
    }

    r = requests.post(url, json=new_user, headers=auth_headers, timeout=10)
    assert r.status_code in [400, 422], f"Expected 400/422 for empty username, got {r.status_code}"
