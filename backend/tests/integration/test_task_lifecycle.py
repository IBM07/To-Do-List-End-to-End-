"""
===========================================
AuraTask - Task Lifecycle Integration Tests
===========================================
Test full CRUD flow and user isolation
"""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


class TestTaskCreation:
    """Test task creation functionality."""
    
    @pytest.mark.asyncio
    async def test_create_task_with_nlp(self, async_client: AsyncClient, test_user: dict):
        """Test: Create task using NLP input."""
        task_data = {
            "nlp_input": "Complete project report #Urgent by tomorrow 5pm"
        }
        
        response = await async_client.post(
            "/api/tasks/",
            json=task_data,
            headers=auth_headers(test_user["token"])
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify NLP parsing
        assert "Complete project report" in data["title"]
        assert data["priority"] == "URGENT"
        assert data["due_date"] is not None
        assert data["user_id"] == test_user["id"]
    
    @pytest.mark.asyncio
    async def test_create_task_structured(self, async_client: AsyncClient, test_user: dict):
        """Test: Create task with structured input."""
        task_data = {
            "title": "Structured task",
            "description": "This is a test task",
            "priority": "HIGH",
            "due_date": "2026-12-31T17:00:00Z"
        }
        
        response = await async_client.post(
            "/api/tasks/",
            json=task_data,
            headers=auth_headers(test_user["token"])
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Structured task"
        assert data["priority"] == "HIGH"
    
    @pytest.mark.asyncio
    async def test_create_task_without_auth(self, async_client: AsyncClient):
        """Test: Creating task without auth should fail."""
        task_data = {
            "nlp_input": "Unauthorized task"
        }
        
        response = await async_client.post("/api/tasks/", json=task_data)
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_create_task_minimal(self, async_client: AsyncClient, test_user: dict):
        """Test: Create task with minimal input."""
        task_data = {
            "nlp_input": "Simple task"
        }
        
        response = await async_client.post(
            "/api/tasks/",
            json=task_data,
            headers=auth_headers(test_user["token"])
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Simple task"
        # Default priority should be MEDIUM
        assert data["priority"] in ["MEDIUM", "LOW", "HIGH"]


class TestTaskRead:
    """Test task read operations and user isolation."""
    
    @pytest.mark.asyncio
    async def test_read_own_tasks(self, async_client: AsyncClient, test_user: dict, test_task: dict):
        """Test: User can read their own tasks."""
        response = await async_client.get(
            "/api/tasks/",
            headers=auth_headers(test_user["token"])
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert len(data["tasks"]) >= 1
        
        # Verify the task is in the list
        task_ids = [t["id"] for t in data["tasks"]]
        assert test_task["id"] in task_ids
    
    @pytest.mark.asyncio
    async def test_read_single_task(self, async_client: AsyncClient, test_user: dict, test_task: dict):
        """Test: User can read a single task by ID."""
        response = await async_client.get(
            f"/api/tasks/{test_task['id']}",
            headers=auth_headers(test_user["token"])
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_task["id"]
    
    @pytest.mark.asyncio
    async def test_user_isolation_cannot_see_other_users_tasks(
        self, 
        async_client: AsyncClient, 
        test_user: dict, 
        second_user: dict
    ):
        """Test: User A cannot see User B's tasks."""
        # Create task for user A
        task_data = {"nlp_input": "User A's private task"}
        create_response = await async_client.post(
            "/api/tasks/",
            json=task_data,
            headers=auth_headers(test_user["token"])
        )
        assert create_response.status_code == 201
        task_a_id = create_response.json()["id"]
        
        # User B tries to list tasks - should not see User A's task
        list_response = await async_client.get(
            "/api/tasks/",
            headers=auth_headers(second_user["token"])
        )
        assert list_response.status_code == 200
        
        task_ids = [t["id"] for t in list_response.json()["tasks"]]
        assert task_a_id not in task_ids
    
    @pytest.mark.asyncio
    async def test_user_cannot_access_other_users_task_directly(
        self, 
        async_client: AsyncClient, 
        test_user: dict, 
        second_user: dict
    ):
        """Test: User B cannot access User A's task by ID."""
        # Create task for user A
        task_data = {"nlp_input": "User A's secret task"}
        create_response = await async_client.post(
            "/api/tasks/",
            json=task_data,
            headers=auth_headers(test_user["token"])
        )
        assert create_response.status_code == 201
        task_a_id = create_response.json()["id"]
        
        # User B tries to access User A's task directly
        access_response = await async_client.get(
            f"/api/tasks/{task_a_id}",
            headers=auth_headers(second_user["token"])
        )
        
        # Should be 404 (not found) or 403 (forbidden)
        assert access_response.status_code in [403, 404]


class TestTaskUpdate:
    """Test task update operations."""
    
    @pytest.mark.asyncio
    async def test_update_task_status(self, async_client: AsyncClient, test_user: dict, test_task: dict):
        """Test: Update task status from PENDING to COMPLETED."""
        update_data = {
            "status": "COMPLETED"
        }
        
        response = await async_client.put(
            f"/api/tasks/{test_task['id']}",
            json=update_data,
            headers=auth_headers(test_user["token"])
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "COMPLETED"
    
    @pytest.mark.asyncio
    async def test_update_task_priority(self, async_client: AsyncClient, test_user: dict, test_task: dict):
        """Test: Update task priority."""
        update_data = {
            "priority": "LOW"
        }
        
        response = await async_client.put(
            f"/api/tasks/{test_task['id']}",
            json=update_data,
            headers=auth_headers(test_user["token"])
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == "LOW"
    
    @pytest.mark.asyncio
    async def test_update_task_title(self, async_client: AsyncClient, test_user: dict, test_task: dict):
        """Test: Update task title."""
        update_data = {
            "title": "Updated Task Title"
        }
        
        response = await async_client.put(
            f"/api/tasks/{test_task['id']}",
            json=update_data,
            headers=auth_headers(test_user["token"])
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Task Title"
    
    @pytest.mark.asyncio
    async def test_user_cannot_update_other_users_task(
        self, 
        async_client: AsyncClient, 
        test_user: dict, 
        second_user: dict
    ):
        """Test: User B cannot update User A's task."""
        # Create task for user A
        task_data = {"nlp_input": "User A's task to protect"}
        create_response = await async_client.post(
            "/api/tasks/",
            json=task_data,
            headers=auth_headers(test_user["token"])
        )
        task_a_id = create_response.json()["id"]
        
        # User B tries to update User A's task
        update_response = await async_client.put(
            f"/api/tasks/{task_a_id}",
            json={"title": "Hacked by User B"},
            headers=auth_headers(second_user["token"])
        )
        
        # Should be forbidden
        assert update_response.status_code in [403, 404]
    
    @pytest.mark.asyncio
    async def test_complete_task_endpoint(self, async_client: AsyncClient, test_user: dict):
        """Test: Complete task via dedicated endpoint."""
        # Create a task first
        task_data = {"nlp_input": "Task to complete"}
        create_response = await async_client.post(
            "/api/tasks/",
            json=task_data,
            headers=auth_headers(test_user["token"])
        )
        task_id = create_response.json()["id"]
        
        # Complete the task
        response = await async_client.post(
            f"/api/tasks/{task_id}/complete",
            headers=auth_headers(test_user["token"])
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "COMPLETED"


class TestTaskDelete:
    """Test task deletion."""
    
    @pytest.mark.asyncio
    async def test_delete_own_task(self, async_client: AsyncClient, test_user: dict):
        """Test: User can delete their own task."""
        # Create a task to delete
        task_data = {"nlp_input": "Task to delete"}
        create_response = await async_client.post(
            "/api/tasks/",
            json=task_data,
            headers=auth_headers(test_user["token"])
        )
        task_id = create_response.json()["id"]
        
        # Delete the task
        delete_response = await async_client.delete(
            f"/api/tasks/{task_id}",
            headers=auth_headers(test_user["token"])
        )
        
        assert delete_response.status_code in [200, 204]
        
        # Verify it's gone
        get_response = await async_client.get(
            f"/api/tasks/{task_id}",
            headers=auth_headers(test_user["token"])
        )
        assert get_response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_user_cannot_delete_other_users_task(
        self, 
        async_client: AsyncClient, 
        test_user: dict, 
        second_user: dict
    ):
        """Test: User B cannot delete User A's task."""
        # Create task for user A
        task_data = {"nlp_input": "User A's task to protect"}
        create_response = await async_client.post(
            "/api/tasks/",
            json=task_data,
            headers=auth_headers(test_user["token"])
        )
        task_a_id = create_response.json()["id"]
        
        # User B tries to delete User A's task
        delete_response = await async_client.delete(
            f"/api/tasks/{task_a_id}",
            headers=auth_headers(second_user["token"])
        )
        
        # Should be forbidden
        assert delete_response.status_code in [403, 404]
        
        # Verify task still exists for user A
        get_response = await async_client.get(
            f"/api/tasks/{task_a_id}",
            headers=auth_headers(test_user["token"])
        )
        assert get_response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_task(self, async_client: AsyncClient, test_user: dict):
        """Test: Deleting non-existent task returns 404."""
        response = await async_client.delete(
            "/api/tasks/99999",
            headers=auth_headers(test_user["token"])
        )
        
        assert response.status_code == 404


class TestTaskSnooze:
    """Test task snooze functionality."""
    
    @pytest.mark.asyncio
    async def test_snooze_task(self, async_client: AsyncClient, test_user: dict):
        """Test: Snooze a task."""
        # Create a task first
        task_data = {"nlp_input": "Task to snooze"}
        create_response = await async_client.post(
            "/api/tasks/",
            json=task_data,
            headers=auth_headers(test_user["token"])
        )
        task_id = create_response.json()["id"]
        
        # Snooze the task
        response = await async_client.post(
            f"/api/tasks/{task_id}/snooze",
            json={"snooze_minutes": 60},
            headers=auth_headers(test_user["token"])
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["snoozed_until"] is not None


class TestTaskFiltering:
    """Test task filtering and pagination."""
    
    @pytest.mark.asyncio
    async def test_get_tasks_with_pagination(self, async_client: AsyncClient, test_user: dict):
        """Test: Get tasks with pagination parameters."""
        # Create multiple tasks
        for i in range(5):
            await async_client.post(
                "/api/tasks/",
                json={"nlp_input": f"Task {i}"},
                headers=auth_headers(test_user["token"])
            )
        
        # Get first page
        response = await async_client.get(
            "/api/tasks/?page=1&per_page=2",
            headers=auth_headers(test_user["token"])
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert len(data["tasks"]) <= 2
    
    @pytest.mark.asyncio
    async def test_get_tasks_include_completed(self, async_client: AsyncClient, test_user: dict):
        """Test: Get tasks with include_completed filter."""
        response = await async_client.get(
            "/api/tasks/?include_completed=true",
            headers=auth_headers(test_user["token"])
        )
        
        assert response.status_code == 200


# Run with: pytest tests/integration/test_task_lifecycle.py -v
