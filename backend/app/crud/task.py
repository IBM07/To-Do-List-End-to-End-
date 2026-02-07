# ===========================================
# AuraTask - Task CRUD Operations
# ===========================================

from datetime import datetime, timezone as tz, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import Task, Priority, TaskStatus
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.groq_parser import parse_task_with_groq
from app.services.urgency_scorer import calculate_urgency_score


async def create_task(
    db: AsyncSession,
    task_data: TaskCreate,
    user: User,
) -> Task:
    """
    Create a new task for a user.
    
    Handles both NLP mode (nlp_input) and structured mode (title + due_date).
    
    Args:
        db: Async database session
        task_data: Task creation data (may contain nlp_input OR title/due_date)
        user: User creating the task
        
    Returns:
        Newly created Task object with calculated urgency score
    """
    # Determine title, due_date, and priority
    if task_data.nlp_input:
        # NLP Mode: Parse natural language input
        parsed = parse_task_with_groq(task_data.nlp_input, user.timezone)
        title = parsed["title"]
        due_date = parsed["due_date"]
        
        # Parse priority from NLP result
        parsed_priority = parsed.get("priority", "MEDIUM")
        print(f"[TASK] NLP returned priority: {parsed_priority}")
        
        try:
            priority = Priority(parsed_priority)
        except ValueError:
            print(f"[TASK] Invalid priority '{parsed_priority}', defaulting to MEDIUM")
            priority = Priority.MEDIUM
        
        print(f"[TASK] Final priority: {priority}")
        
        # If NLP didn't extract a due date, use explicit one or default to 24h
        if not due_date and task_data.due_date:
            due_date = task_data.due_date
        elif not due_date:
            due_date = datetime.now(tz.utc) + timedelta(hours=24)
            
        # Only override priority if NLP failed AND explicit priority provided
        # (Don't override NLP-parsed priority!)
    else:
        # Structured Mode: Use provided fields
        title = task_data.title
        due_date = task_data.due_date
        priority = task_data.priority or Priority.MEDIUM
    
    # Ensure due_date is timezone-aware
    if due_date.tzinfo is None:
        due_date = due_date.replace(tzinfo=tz.utc)
    
    # Calculate initial urgency score
    urgency_score = calculate_urgency_score(due_date, priority)
    
    # Create task
    task = Task(
        user_id=user.id,
        title=title,
        description=task_data.description,
        priority=priority,
        status=TaskStatus.PENDING,
        due_date=due_date,
        urgency_score=urgency_score,
    )
    
    db.add(task)
    await db.flush()
    await db.refresh(task)
    # Explicitly set empty list for subtasks to avoid lazy load error
    # or refresh it if needed, but since it's new, it's empty.
    # We can just set it to empty list to satisfy Pydantic
    # However, SQLAlchemy models usually default relationships to empty list in memory if not loaded?
    # No, we must be careful. Let's trying refreshing it.
    # Actually, for a new object, we usually don't need to load relationships if they are empty?
    # But let's be safe.
    await db.refresh(task, attribute_names=["subtasks"])
    
    return task


async def get_task_by_id(
    db: AsyncSession,
    task_id: int,
    user_id: Optional[int] = None
) -> Optional[Task]:
    """
    Retrieve a task by ID, optionally filtering by user.
    
    Args:
        db: Async database session
        task_id: Task ID
        user_id: Optional user ID for ownership check
        
    Returns:
        Task object if found, None otherwise
    """
    query = select(Task).where(Task.id == task_id).options(selectinload(Task.subtasks))
    
    if user_id is not None:
        query = query.where(Task.user_id == user_id)
    
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_tasks_multi(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 50,
    status: Optional[TaskStatus] = None,
    priority: Optional[Priority] = None,
    include_completed: bool = False,
    order_by_urgency: bool = True,
) -> tuple[List[Task], int]:
    """
    Retrieve multiple tasks for a user with filtering and pagination.
    
    Args:
        db: Async database session
        user_id: User's ID
        skip: Number of records to skip (pagination)
        limit: Maximum records to return
        status: Filter by status
        priority: Filter by priority
        include_completed: Include completed/cancelled tasks
        order_by_urgency: Sort by urgency score (desc)
        
    Returns:
        Tuple of (list of tasks, total count)
    """
    # Base query
    query = select(Task).where(Task.user_id == user_id).options(selectinload(Task.subtasks))
    
    # Apply filters
    if status is not None:
        query = query.where(Task.status == status)
    elif not include_completed:
        # Exclude completed and cancelled by default
        query = query.where(
            Task.status.not_in([TaskStatus.COMPLETED, TaskStatus.CANCELLED])
        )
    
    if priority is not None:
        query = query.where(Task.priority == priority)
    
    # Count total before pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply ordering
    if order_by_urgency:
        query = query.order_by(Task.urgency_score.desc(), Task.due_date.asc())
    else:
        query = query.order_by(Task.due_date.asc())
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    # Execute
    result = await db.execute(query)
    tasks = list(result.scalars().all())
    
    return tasks, total


async def update_task(
    db: AsyncSession,
    task: Task,
    updates: TaskUpdate
) -> Task:
    """
    Update an existing task.
    
    Args:
        db: Async database session
        task: Task object to update
        updates: Fields to update
        
    Returns:
        Updated Task object
    """
    update_data = updates.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(task, field, value)
    
    await db.flush()
    await db.refresh(task, attribute_names=["subtasks"])
    
    return task


async def update_task_status(
    db: AsyncSession,
    task: Task,
    new_status: TaskStatus
) -> Tuple[Task, bool]:
    """
    Update a task's status with proper transition handling.
    
    Args:
        db: Async database session
        task: Task to update
        new_status: New status to set
        
    Returns:
        Tuple of (updated Task, should_cancel_notifications)
        - should_cancel_notifications is True when status changes to COMPLETED/CANCELLED
    """
    old_status = task.status
    task.status = new_status
    
    await db.flush()
    await db.refresh(task, attribute_names=["subtasks"])
    
    # Determine if we need to cancel pending notifications
    should_cancel_notifications = (
        new_status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]
        and old_status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]
    )
    
    return task, should_cancel_notifications


async def complete_task(db: AsyncSession, task: Task) -> Tuple[Task, bool]:
    """
    Mark a task as completed.
    
    Args:
        db: Async database session
        task: Task to complete
        
    Returns:
        Tuple of (updated Task, should_cancel_notifications)
    """
    return await update_task_status(db, task, TaskStatus.COMPLETED)


async def snooze_task(
    db: AsyncSession,
    task: Task,
    snooze_until: datetime
) -> Task:
    """
    Snooze notifications for a task until a specified time.
    
    Args:
        db: Async database session
        task: Task to snooze
        snooze_until: DateTime (UTC) until which to snooze
        
    Returns:
        Updated Task object
    """
    task.snoozed_until = snooze_until
    await db.flush()
    await db.refresh(task, attribute_names=["subtasks"])
    return task


async def delete_task(db: AsyncSession, task: Task) -> None:
    """
    Delete a task.
    
    Args:
        db: Async database session
        task: Task to delete
    """
    await db.delete(task)
    await db.flush()


async def get_tasks_due_soon(
    db: AsyncSession,
    within_hours: int = 24
) -> List[Task]:
    """
    Get all pending tasks due within a specified time window.
    Used by the notification scheduler.
    
    Args:
        db: Async database session
        within_hours: Hours from now to check
        
    Returns:
        List of tasks due soon
    """
    now = datetime.now(tz.utc)
    cutoff = datetime.now(tz.utc).replace(
        hour=now.hour + within_hours
    )
    
    query = select(Task).where(
        and_(
            Task.status == TaskStatus.PENDING,
            Task.due_date >= now,
            Task.due_date <= cutoff,
            or_(
                Task.snoozed_until.is_(None),
                Task.snoozed_until < now
            )
        )
    ).options(selectinload(Task.user))
    
    result = await db.execute(query)
    return list(result.scalars().all())
