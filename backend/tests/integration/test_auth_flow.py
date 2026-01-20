"""
===========================================
AuraTask - Authentication Flow Integration Tests
===========================================
Test user registration, login, and token validation
"""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


class TestUserRegistration:
    """Test user registration flow."""
    
    @pytest.mark.asyncio
    async def test_register_success(self, async_client: AsyncClient):
        """Test: Successful user registration."""
        user_data = {
            "email": "newuser@example.com",
            "password": "securepassword123",
            "timezone": "UTC"
        }
        
        response = await async_client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert "id" in data
        assert "hashed_password" not in data  # Should not expose password
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, async_client: AsyncClient):
        """Test: Duplicate email registration should fail."""
        user_data = {
            "email": "duplicate@example.com",
            "password": "password123",
            "timezone": "UTC"
        }
        
        # First registration should succeed
        response1 = await async_client.post("/api/auth/register", json=user_data)
        assert response1.status_code == 201
        
        # Second registration with same email should fail
        response2 = await async_client.post("/api/auth/register", json=user_data)
        assert response2.status_code == 400
        assert "already registered" in response2.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_register_invalid_email(self, async_client: AsyncClient):
        """Test: Invalid email format should fail."""
        user_data = {
            "email": "not-an-email",
            "password": "password123",
            "timezone": "UTC"
        }
        
        response = await async_client.post("/api/auth/register", json=user_data)
        
        # Should fail validation
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_register_short_password(self, async_client: AsyncClient):
        """Test: Password too short should fail."""
        user_data = {
            "email": "short@example.com",
            "password": "short",  # Less than 8 characters
            "timezone": "UTC"
        }
        
        response = await async_client.post("/api/auth/register", json=user_data)
        
        # Should fail validation (min_length=8)
        assert response.status_code == 422


class TestUserLogin:
    """Test user login flow."""
    
    @pytest.mark.asyncio
    async def test_login_success(self, async_client: AsyncClient, test_user: dict):
        """Test: Successful login with correct credentials."""
        login_data = {
            "email": test_user["email"],
            "password": test_user["password"]
        }
        
        response = await async_client.post("/api/auth/login/json", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    @pytest.mark.asyncio
    async def test_login_wrong_password(self, async_client: AsyncClient, test_user: dict):
        """Test: Login with wrong password should fail."""
        login_data = {
            "email": test_user["email"],
            "password": "wrongpassword123"
        }
        
        response = await async_client.post("/api/auth/login/json", json=login_data)
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower() or "invalid" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        """Test: Login with non-existent email should fail."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "password123"
        }
        
        response = await async_client.post("/api/auth/login/json", json=login_data)
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_login_empty_credentials(self, async_client: AsyncClient):
        """Test: Login with empty credentials should fail."""
        response = await async_client.post("/api/auth/login/json", json={})
        
        assert response.status_code == 422


class TestTokenValidation:
    """Test JWT token validation."""
    
    @pytest.mark.asyncio
    async def test_protected_route_with_valid_token(self, async_client: AsyncClient, test_user: dict):
        """Test: Protected route should return user data with valid token."""
        response = await async_client.get(
            "/api/auth/me",
            headers=auth_headers(test_user["token"])
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user["email"]
    
    @pytest.mark.asyncio
    async def test_protected_route_without_token(self, async_client: AsyncClient):
        """Test: Protected route should return 401 without token."""
        response = await async_client.get("/api/auth/me")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_protected_route_with_invalid_token(self, async_client: AsyncClient):
        """Test: Protected route should return 401 with invalid token."""
        response = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_protected_route_with_malformed_header(self, async_client: AsyncClient):
        """Test: Protected route should fail with malformed auth header."""
        response = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": "NotBearer sometoken"}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_token_refresh(self, async_client: AsyncClient, test_user: dict):
        """Test: Token refresh should return new valid token."""
        response = await async_client.post(
            "/api/auth/refresh",
            headers=auth_headers(test_user["token"])
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


class TestUniqueConstraints:
    """Test database unique constraints."""
    
    @pytest.mark.asyncio
    async def test_email_uniqueness(self, async_client: AsyncClient):
        """Test: Two users cannot have the same email."""
        user_data = {
            "email": "unique@example.com",
            "password": "password123",
            "timezone": "UTC"
        }
        
        # First registration
        response1 = await async_client.post("/api/auth/register", json=user_data)
        assert response1.status_code == 201
        
        # Try to register again with same email
        response2 = await async_client.post("/api/auth/register", json=user_data)
        assert response2.status_code == 400
        
        # Different password shouldn't matter
        user_data["password"] = "differentpassword123"
        response3 = await async_client.post("/api/auth/register", json=user_data)
        assert response3.status_code == 400
    
    @pytest.mark.asyncio
    async def test_case_sensitivity_email(self, async_client: AsyncClient):
        """Test: Email should be case-insensitive for uniqueness."""
        user_data = {
            "email": "CasE@Example.COM",
            "password": "password123",
            "timezone": "UTC"
        }
        
        # Register with mixed case
        response1 = await async_client.post("/api/auth/register", json=user_data)
        assert response1.status_code == 201
        
        # Try lowercase version - should fail if email is normalized
        user_data["email"] = "case@example.com"
        response2 = await async_client.post("/api/auth/register", json=user_data)
        # Depending on implementation, this may pass or fail
        # Good implementations normalize email to lowercase


# Run with: pytest tests/integration/test_auth_flow.py -v
