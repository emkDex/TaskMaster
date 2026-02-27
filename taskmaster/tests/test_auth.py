"""
Authentication endpoint tests.
Covers: register, login, refresh, logout, duplicate email/username.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestRegister:
    async def test_register_success(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "NewPass1",
                "full_name": "New User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert "hashed_password" not in data
        assert "id" in data

    async def test_register_duplicate_email(
        self, client: AsyncClient, registered_user: dict
    ) -> None:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "testuser@example.com",  # already registered
                "username": "differentuser",
                "password": "TestPass1",
            },
        )
        assert response.status_code == 409

    async def test_register_duplicate_username(
        self, client: AsyncClient, registered_user: dict
    ) -> None:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "different@example.com",
                "username": "testuser",  # already registered
                "password": "TestPass1",
            },
        )
        assert response.status_code == 409

    async def test_register_weak_password(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@example.com",
                "username": "weakuser",
                "password": "short",  # too short, no uppercase, no digit
            },
        )
        assert response.status_code == 422

    async def test_register_invalid_email(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "username": "someuser",
                "password": "ValidPass1",
            },
        )
        assert response.status_code == 422


class TestLogin:
    async def test_login_success(
        self, client: AsyncClient, registered_user: dict
    ) -> None:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "testuser@example.com", "password": "TestPass1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(
        self, client: AsyncClient, registered_user: dict
    ) -> None:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "testuser@example.com", "password": "WrongPass1"},
        )
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "TestPass1"},
        )
        assert response.status_code == 401


class TestRefresh:
    async def test_refresh_success(
        self, client: AsyncClient, registered_user: dict
    ) -> None:
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "testuser@example.com", "password": "TestPass1"},
        )
        refresh_token = login_resp.json()["refresh_token"]

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_invalid_token(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "this.is.invalid"},
        )
        assert response.status_code == 401


class TestLogout:
    async def test_logout_success(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        response = await client.post("/api/v1/auth/logout", headers=auth_headers)
        assert response.status_code == 204

    async def test_logout_unauthenticated(self, client: AsyncClient) -> None:
        response = await client.post("/api/v1/auth/logout")
        assert response.status_code == 401


class TestGetMe:
    async def test_get_me_success(
        self, client: AsyncClient, auth_headers: dict, registered_user: dict
    ) -> None:
        response = await client.get("/api/v1/users/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == registered_user["email"]

    async def test_get_me_unauthenticated(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401
