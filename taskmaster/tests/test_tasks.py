"""
Task endpoint tests.
Covers: create, read, update, delete (archive), filter, pagination, unauthorized access.
"""
from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _create_task(
    client: AsyncClient,
    headers: dict,
    title: str = "Test Task",
    **kwargs: Any,
) -> dict:
    payload = {
        "title": title,
        "description": "A test task description",
        "status": "pending",
        "priority": "medium",
        **kwargs,
    }
    response = await client.post("/api/v1/tasks/", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


class TestCreateTask:
    async def test_create_task_success(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        response = await client.post(
            "/api/v1/tasks/",
            json={
                "title": "My First Task",
                "description": "Do something important",
                "status": "pending",
                "priority": "high",
                "tags": ["urgent", "backend"],
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "My First Task"
        assert data["priority"] == "high"
        assert data["status"] == "pending"
        assert data["is_archived"] is False
        assert "id" in data

    async def test_create_task_unauthenticated(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/tasks/",
            json={"title": "Unauthorized Task", "status": "pending", "priority": "low"},
        )
        assert response.status_code == 401

    async def test_create_task_missing_title(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        response = await client.post(
            "/api/v1/tasks/",
            json={"status": "pending", "priority": "low"},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestGetTask:
    async def test_get_task_success(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        task = await _create_task(client, auth_headers, title="Readable Task")
        response = await client.get(
            f"/api/v1/tasks/{task['id']}", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["id"] == task["id"]

    async def test_get_task_not_found(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/v1/tasks/{fake_id}", headers=auth_headers)
        assert response.status_code == 404


class TestUpdateTask:
    async def test_update_task_success(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        task = await _create_task(client, auth_headers, title="Update Me")
        response = await client.put(
            f"/api/v1/tasks/{task['id']}",
            json={"title": "Updated Title", "status": "in_progress"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["status"] == "in_progress"

    async def test_update_task_unauthorized(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """A second user should not be able to update another user's task."""
        task = await _create_task(client, auth_headers, title="Owner Task")

        # Register a second user
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "other@example.com",
                "username": "otheruser",
                "password": "OtherPass1",
            },
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "other@example.com", "password": "OtherPass1"},
        )
        other_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

        response = await client.put(
            f"/api/v1/tasks/{task['id']}",
            json={"title": "Hijacked"},
            headers=other_headers,
        )
        assert response.status_code == 403


class TestDeleteTask:
    async def test_archive_task_success(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        task = await _create_task(client, auth_headers, title="Archive Me")
        response = await client.delete(
            f"/api/v1/tasks/{task['id']}", headers=auth_headers
        )
        assert response.status_code == 204

        # Verify it's archived (not returned in default list)
        list_resp = await client.get("/api/v1/tasks/", headers=auth_headers)
        ids = [t["id"] for t in list_resp.json()["items"]]
        assert task["id"] not in ids


class TestListTasks:
    async def test_list_tasks_pagination(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        # Create 3 tasks
        for i in range(3):
            await _create_task(client, auth_headers, title=f"Paginated Task {i}")

        response = await client.get(
            "/api/v1/tasks/?page=1&size=2", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "pages" in data
        assert len(data["items"]) <= 2

    async def test_list_tasks_filter_by_status(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        await _create_task(client, auth_headers, title="Pending Task", status="pending")
        await _create_task(
            client, auth_headers, title="Completed Task", status="completed"
        )

        response = await client.get(
            "/api/v1/tasks/?status=completed", headers=auth_headers
        )
        assert response.status_code == 200
        items = response.json()["items"]
        assert all(t["status"] == "completed" for t in items)

    async def test_list_tasks_search(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        await _create_task(client, auth_headers, title="Unique Searchable Title XYZ")
        await _create_task(client, auth_headers, title="Another Task")

        response = await client.get(
            "/api/v1/tasks/?search=XYZ", headers=auth_headers
        )
        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) >= 1
        assert any("XYZ" in t["title"] for t in items)

    async def test_list_tasks_filter_by_priority(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        await _create_task(client, auth_headers, title="Critical Task", priority="critical")

        response = await client.get(
            "/api/v1/tasks/?priority=critical", headers=auth_headers
        )
        assert response.status_code == 200
        items = response.json()["items"]
        assert all(t["priority"] == "critical" for t in items)
