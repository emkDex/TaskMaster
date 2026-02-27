"""
Team endpoint tests.
Covers: create team, add/remove member, team task access, role enforcement.
"""
from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register_and_login(
    client: AsyncClient, email: str, username: str, password: str = "TestPass1"
) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_team(
    client: AsyncClient, headers: dict, name: str = "Test Team"
) -> dict[str, Any]:
    resp = await client.post(
        "/api/v1/teams/",
        json={"name": name, "description": "A test team"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestCreateTeam:
    async def test_create_team_success(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        response = await client.post(
            "/api/v1/teams/",
            json={"name": "Engineering", "description": "Backend team"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Engineering"
        assert "id" in data

    async def test_create_team_unauthenticated(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/teams/",
            json={"name": "Unauthorized Team"},
        )
        assert response.status_code == 401


class TestGetTeam:
    async def test_get_team_success(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        team = await _create_team(client, auth_headers, name="Visible Team")
        response = await client.get(
            f"/api/v1/teams/{team['id']}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == team["id"]
        assert "members" in data

    async def test_get_team_not_member(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        team = await _create_team(client, auth_headers, name="Private Team")

        # Register a non-member
        other_headers = await _register_and_login(
            client, "nonmember@example.com", "nonmember"
        )
        response = await client.get(
            f"/api/v1/teams/{team['id']}", headers=other_headers
        )
        assert response.status_code == 403


class TestAddMember:
    async def test_add_member_success(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        team = await _create_team(client, auth_headers, name="Growing Team")

        # Register a second user to add
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "member2@example.com",
                "username": "member2",
                "password": "MemberPass1",
            },
        )
        # Get the user ID
        me_resp = await client.get("/api/v1/users/me", headers=auth_headers)
        # We need the second user's ID — get it via admin or by registering and logging in
        member_headers = await _register_and_login(
            client, "member3@example.com", "member3"
        )
        member_me = await client.get("/api/v1/users/me", headers=member_headers)
        member_id = member_me.json()["id"]

        response = await client.post(
            f"/api/v1/teams/{team['id']}/members",
            json={"user_id": member_id, "role": "member"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == member_id
        assert data["role"] == "member"

    async def test_add_duplicate_member(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        team = await _create_team(client, auth_headers, name="Duplicate Test Team")

        member_headers = await _register_and_login(
            client, "dup_member@example.com", "dup_member"
        )
        member_me = await client.get("/api/v1/users/me", headers=member_headers)
        member_id = member_me.json()["id"]

        # Add once
        await client.post(
            f"/api/v1/teams/{team['id']}/members",
            json={"user_id": member_id, "role": "member"},
            headers=auth_headers,
        )
        # Add again — should conflict
        response = await client.post(
            f"/api/v1/teams/{team['id']}/members",
            json={"user_id": member_id, "role": "member"},
            headers=auth_headers,
        )
        assert response.status_code == 409


class TestRemoveMember:
    async def test_remove_member_success(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        team = await _create_team(client, auth_headers, name="Shrinking Team")

        member_headers = await _register_and_login(
            client, "removable@example.com", "removable"
        )
        member_me = await client.get("/api/v1/users/me", headers=member_headers)
        member_id = member_me.json()["id"]

        await client.post(
            f"/api/v1/teams/{team['id']}/members",
            json={"user_id": member_id, "role": "member"},
            headers=auth_headers,
        )

        response = await client.delete(
            f"/api/v1/teams/{team['id']}/members/{member_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204


class TestListMyTeams:
    async def test_list_my_teams(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        await _create_team(client, auth_headers, name="My Team A")
        await _create_team(client, auth_headers, name="My Team B")

        response = await client.get("/api/v1/teams/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] >= 2


class TestUpdateTeam:
    async def test_update_team_success(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        team = await _create_team(client, auth_headers, name="Old Name")
        response = await client.put(
            f"/api/v1/teams/{team['id']}",
            json={"name": "New Name"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    async def test_update_team_non_owner_forbidden(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        team = await _create_team(client, auth_headers, name="Protected Team")

        other_headers = await _register_and_login(
            client, "intruder@example.com", "intruder"
        )
        response = await client.put(
            f"/api/v1/teams/{team['id']}",
            json={"name": "Hijacked"},
            headers=other_headers,
        )
        assert response.status_code == 403
