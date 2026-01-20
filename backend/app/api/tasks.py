# ===========================================
# AuraTask - Tasks API
# ===========================================
# CRUD endpoints for task management

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.task import Task, TaskStatus, Priority
from app.models.notification import NotificationSettings
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskSnooze,
    TaskResponse,
    TaskListResponse,
)
from app.crud.task import (
    create_task,
    get_task_by_id,
    get_tasks_multi,
    update_task,
    update_task_status,
    complete_task,
    snooze_task,
    delete_task,
)
from app.api.auth import get_current_user
from app.api.utils import task_to_response, tasks_to_response
from app.api.websocket import broadcast_task_created, broadcast_task_updated, broadcast_task_deleted
from app.services.notification_scheduler import schedule_notifications, revoke_notifications, reschedule_notifications


router = APIRouter()


# ===========================================
# Helper Functions
# ===========================================

async def get_user_notification_settings(
    db: AsyncSession,
    user_id: int
) -> Optional[NotificationSettings]:
    """Get user's notification settings."""
    from sqlalchemy import select
    result = await db.execute(
        select(NotificationSettings).where(NotificationSettings.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def verify_task_ownership(
    task: Task,
    user: User
) -> None:
    """
    Verify user owns the task.
    
    Raises:
        HTTPException 404: If task doesn't belong to user
    """
    if task.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )


# ===========================================
# Task Endpoints
# ===========================================

@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_new_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new task.
    
    Supports two modes:
    - NLP Mode: Provide `nlp_input` like "Fix bug #Urgent by Friday 5pm"
    - Structured Mode: Provide `title`, `due_date`, and optionally `priority`
    """
    # Create the task
    task = await create_task(db, task_data, current_user)
    
    # Schedule notifications
    settings = await get_user_notification_settings(db, current_user.id)
    if settings:
        schedule_notifications(task, settings)
    
    # Prepare response with user's timezone
    response = task_to_response(task, current_user.timezone)
    
    # Broadcast to WebSocket
    await broadcast_task_created(current_user.id, response)
    
    return response


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[TaskStatus] = Query(None, alias="status"),
    priority_filter: Optional[Priority] = Query(None, alias="priority"),
    include_completed: bool = Query(False, description="Include completed tasks"),
):
    """
    List user's tasks with filtering and pagination.
    
    Tasks are sorted by urgency_score (desc) and due_date (asc).
    """
    skip = (page - 1) * per_page
    
    tasks, total = await get_tasks_multi(
        db,
        user_id=current_user.id,
        skip=skip,
        limit=per_page,
        status=status_filter,
        priority=priority_filter,
        include_completed=include_completed,
    )
    
    # Convert to responses with timezone
    task_responses = tasks_to_response(tasks, current_user.timezone)
    
    # Calculate pagination
    total_pages = (total + per_page - 1) // per_page
    
    return TaskListResponse(
        tasks=task_responses,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific task by ID.
    """
    task = await get_task_by_id(db, task_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Privacy enforcement
    await verify_task_ownership(task, current_user)
    
    return task_to_response(task, current_user.timezone)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_existing_task(
    task_id: int,
    updates: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a task.
    """
    task = await get_task_by_id(db, task_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    await verify_task_ownership(task, current_user)
    
    # Check if due_date is changing (need to reschedule notifications)
    due_date_changed = updates.due_date and updates.due_date != task.due_date
    
    # Update the task
    updated_task = await update_task(db, task, updates)
    
    # Reschedule notifications if due date changed
    if due_date_changed:
        settings = await get_user_notification_settings(db, current_user.id)
        if settings:
            reschedule_notifications(updated_task, settings)
    
    response = task_to_response(updated_task, current_user.timezone)
    
    # Broadcast update
    await broadcast_task_updated(current_user.id, response)
    
    return response


@router.patch("/{task_id}/status", response_model=TaskResponse)
async def change_task_status(
    task_id: int,
    new_status: TaskStatus,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Change a task's status.
    
    When completing or cancelling, pending notifications are automatically revoked.
    """
    task = await get_task_by_id(db, task_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    await verify_task_ownership(task, current_user)
    
    updated_task, should_cancel = await update_task_status(db, task, new_status)
    
    # Cancel notifications if task completed/cancelled
    if should_cancel:
        revoke_notifications(task_id)
    
    response = task_to_response(updated_task, current_user.timezone)
    await broadcast_task_updated(current_user.id, response)
    
    return response


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task_endpoint(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark a task as completed.
    """
    task = await get_task_by_id(db, task_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    await verify_task_ownership(task, current_user)
    
    updated_task, should_cancel = await complete_task(db, task)
    
    if should_cancel:
        revoke_notifications(task_id)
    
    response = task_to_response(updated_task, current_user.timezone)
    await broadcast_task_updated(current_user.id, response)
    
    return response


@router.post("/{task_id}/snooze", response_model=TaskResponse)
async def snooze_task_endpoint(
    task_id: int,
    snooze_data: TaskSnooze,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Snooze task notifications for a specified duration.
    """
    task = await get_task_by_id(db, task_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    await verify_task_ownership(task, current_user)
    
    snooze_until = datetime.now(timezone.utc) + timedelta(minutes=snooze_data.snooze_minutes)
    updated_task = await snooze_task(db, task, snooze_until)
    
    response = task_to_response(updated_task, current_user.timezone)
    await broadcast_task_updated(current_user.id, response)
    
    return response


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_endpoint(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a task.
    """
    task = await get_task_by_id(db, task_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    await verify_task_ownership(task, current_user)
    
    # Cancel any pending notifications
    revoke_notifications(task_id)
    
    # Delete the task
    await delete_task(db, task)
    
    # Broadcast deletion
    await broadcast_task_deleted(current_user.id, task_id)
    
    return None
