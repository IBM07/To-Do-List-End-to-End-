"""
===========================================
AuraTask - Test Configuration & Fixtures
===========================================
Pytest fixtures for integration testing
"""

import asyncio
from typing import AsyncGenerator, Generator
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.models.task import Task
from app.models.notification import NotificationSettings, NotificationLog


# ===========================================
# Test Database Configuration
# ===========================================
# Using SQLite in-memory for fast, isolated tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create async engine for tests
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

# Session factory for tests
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# ===========================================
# Event Loop Fixture
# ===========================================
@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ===========================================
# Database Fixtures
# ===========================================
@pytest_asyncio.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh database for each test.
    
    - Creates all tables before test
    - Drops all tables after test
    - Returns an async session
    """
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async with TestSessionLocal() as session:
        yield session
    
    # Drop tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def async_client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async HTTP client for testing FastAPI endpoints.
    
    Overrides the database dependency with test database.
    """
    # Override the database dependency
    async def override_get_db():
        yield test_db
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Create async client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    # Clear overrides
    app.dependency_overrides.clear()


# ===========================================
# User Fixtures
# ===========================================
@pytest_asyncio.fixture
async def test_user(async_client: AsyncClient) -> dict:
    """
    Create a test user and return user data with auth token.
    
    Returns:
        {
            "id": user_id,
            "email": "test@example.com",
            "password": "testpassword123",
            "token": "jwt_token..."
        }
    """
    user_data = {
        "email": "test@example.com",
        "password": "testpassword123",
        "timezone": "UTC"
    }
    
    # Register user
    response = await async_client.post("/api/auth/register", json=user_data)
    assert response.status_code == 201, f"Failed to create user: {response.text}"
    
    # Login to get token
    login_response = await async_client.post("/api/auth/login/json", json={
        "email": user_data["email"],
        "password": user_data["password"]
    })
    assert login_response.status_code == 200, f"Failed to login: {login_response.text}"
    
    token_data = login_response.json()
    
    return {
        "id": response.json()["id"],
        "email": user_data["email"],
        "password": user_data["password"],
        "token": token_data["access_token"]
    }


@pytest_asyncio.fixture
async def second_user(async_client: AsyncClient) -> dict:
    """Create a second test user for isolation tests."""
    user_data = {
        "email": "second@example.com",
        "password": "secondpassword123",
        "timezone": "America/New_York"
    }
    
    # Register user
    response = await async_client.post("/api/auth/register", json=user_data)
    assert response.status_code == 201
    
    # Login to get token
    login_response = await async_client.post("/api/auth/login/json", json={
        "email": user_data["email"],
        "password": user_data["password"]
    })
    
    token_data = login_response.json()
    
    return {
        "id": response.json()["id"],
        "email": user_data["email"],
        "password": user_data["password"],
        "token": token_data["access_token"]
    }


# ===========================================
# Auth Header Helper
# ===========================================
def auth_headers(token: str) -> dict:
    """Create authorization headers with Bearer token."""
    return {"Authorization": f"Bearer {token}"}


# ===========================================
# Task Fixtures
# ===========================================
@pytest_asyncio.fixture
async def test_task(async_client: AsyncClient, test_user: dict) -> dict:
    """Create a test task for the test user."""
    task_data = {
        "nlp_input": "Complete project report #High by tomorrow 5pm"
    }
    
    response = await async_client.post(
        "/api/tasks/",
        json=task_data,
        headers=auth_headers(test_user["token"])
    )
    
    assert response.status_code == 201, f"Failed to create task: {response.text}"
    return response.json()
