import pytest
from fastapi import status

def test_register_user(client, test_user_data):
    """Test user registration"""
    response = client.post("/api/v1/identity/register", json=test_user_data)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["user"]["email"] == test_user_data["email"]
    assert "access_token" in data
    assert "refresh_token" in data

def test_login_user(client, test_user_data):
    """Test user login"""
    # First register
    client.post("/api/v1/identity/register", json=test_user_data)
    
    # Then login
    login_data = {
        "email": test_user_data["email"],
        "password": test_user_data["password"]
    }
    response = client.post("/api/v1/identity/login", json=login_data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data

def test_refresh_token(client, test_user_data):
    """Test token refresh"""
    # Register and get refresh token
    resp = client.post("/api/v1/identity/register", json=test_user_data)
    refresh_token = resp.json()["refresh_token"]
    
    # Refresh
    response = client.post(
        "/api/v1/identity/refresh",
        json={"refresh_token": refresh_token}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data

def test_logout_user(client, test_user_data):
    """Test user logout"""
    # Register and get refresh token
    resp = client.post("/api/v1/identity/register", json=test_user_data)
    refresh_token = resp.json()["refresh_token"]
    
    # Logout
    response = client.post(
        "/api/v1/identity/logout",
        json={"refresh_token": refresh_token}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Successfully logged out"

def test_logout_invalid_token(client):
    """Test logout with invalid token"""
    response = client.post(
        "/api/v1/identity/logout",
        json={"refresh_token": "invalid_token"}
    )
    # Should return 404 as per our implementation in auth.py
    assert response.status_code == status.HTTP_404_NOT_FOUND
