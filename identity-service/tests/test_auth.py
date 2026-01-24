import pytest
import logging
from fastapi import status

logger = logging.getLogger(__name__)

def test_register_user(client, test_user_data):
    """Test user registration"""
    logger.info(f"Registering user: {test_user_data['email']}")
    response = client.post("/api/v1/identity/register", json=test_user_data)
    logger.info(f"Response status: {response.status_code}")
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["user"]["email"] == test_user_data["email"]
    assert "access_token" in data
    assert "refresh_token" in data
    logger.info("User registration successful")

def test_login_user(client, test_user_data):
    """Test user login"""
    # First register
    logger.info(f"Registering user for login: {test_user_data['email']}")
    client.post("/api/v1/identity/register", json=test_user_data)

    # Then login
    login_data = {
        "email": test_user_data["email"],
        "password": test_user_data["password"]
    }
    logger.info(f"Logging in user: {login_data['email']}")
    response = client.post("/api/v1/identity/login", json=login_data)
    logger.info(f"Response status: {response.status_code}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    logger.info("User login successful")

def test_refresh_token(client, test_user_data):
    """Test token refresh"""
    # Register and get refresh token
    logger.info("Registering user for token refresh")
    resp = client.post("/api/v1/identity/register", json=test_user_data)
    refresh_token = resp.json()["refresh_token"]

    # Refresh
    logger.info("Refreshing access token")
    response = client.post(
        "/api/v1/identity/refresh",
        json={"refresh_token": refresh_token}
    )
    logger.info(f"Response status: {response.status_code}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    logger.info("Token refresh successful")

def test_logout_user(client, test_user_data):
    """Test user logout"""
    # Register and get refresh token
    logger.info("Registering user for logout")
    resp = client.post("/api/v1/identity/register", json=test_user_data)
    refresh_token = resp.json()["refresh_token"]

    # Logout
    logger.info("Logging out user")
    response = client.post(
        "/api/v1/identity/logout",
        json={"refresh_token": refresh_token}
    )
    logger.info(f"Response status: {response.status_code}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Successfully logged out"
    logger.info("User logout successful")

def test_logout_invalid_token(client):
    """Test logout with invalid token"""
    logger.info("Testing logout with invalid token")
    response = client.post(
        "/api/v1/identity/logout",
        json={"refresh_token": "invalid_token"}
    )
    logger.info(f"Response status: {response.status_code}")
    # Should return 404 as per our implementation in auth.py
    assert response.status_code == status.HTTP_404_NOT_FOUND
    logger.info("Invalid token logout handled correctly")

def test_register_duplicate_email(client, test_user_data):
    """Test user registration with duplicate email"""
    logger.info(f"Registering user first time: {test_user_data['email']}")
    client.post("/api/v1/identity/register", json=test_user_data)

    logger.info(f"Registering user second time: {test_user_data['email']}")
    response = client.post("/api/v1/identity/register", json=test_user_data)

    logger.info(f"Response status: {response.status_code}")
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "already registered" in response.json()["detail"]
    logger.info("Duplicate email registration handled correctly")
