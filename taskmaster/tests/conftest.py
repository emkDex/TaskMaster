"""
Test configuration and shared fixtures.
Uses an in-memory SQLite database for fast, isolated tests.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db
from app.main import app

# ── Test database ─────────────────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Create all tables once per test session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional test database session that rolls back after each test."""
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.rollback()
        finally:
            await session.close()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP test client with the test DB injected."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Helper fixtures ───────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def registered_user(client: AsyncClient) -> dict[str, Any]:
    """Register and return a standard user."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "testuser@example.com",
            "username": "testuser",
            "password": "TestPass1",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, registered_user: dict) -> dict[str, str]:
    """Return Authorization headers for the registered test user."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@example.com", "password": "TestPass1"},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def registered_admin(client: AsyncClient, db: AsyncSession) -> dict[str, Any]:
    """Register an admin user directly via the DB."""
    from app.core.security import hash_password
    from app.models.user import User

    admin = User(
        email="admin@example.com",
        username="adminuser",
        hashed_password=hash_password("AdminPass1"),
        full_name="Admin User",
        role="admin",
        is_active=True,
        is_verified=True,
    )
    db.add(admin)
    await db.flush()
    await db.refresh(admin)
    return {"id": str(admin.id), "email": admin.email, "username": admin.username}


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, registered_admin: dict) -> dict[str, str]:
    """Return Authorization headers for the admin user."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass1"},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
