# ===========================================
# AuraTask - Subtask CRUD Operations
# ===========================================

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.subtask import Subtask
from app.models.task import Task, TaskStatus
from app.services.notification_scheduler import revoke_notifications


MAX_SUBTASKS = 10


async def create_subtask(db: AsyncSession, task_id: int, title: str) -> Subtask:
    """
    Create a new subtask.
    
    Enforces maximum limit of 10 subtasks per task.
    """
    # Check limit
    count = await db.scalar(
        select(func.count(Subtask.id)).where(Subtask.task_id == task_id)
    )
    if count >= MAX_SUBTASKS:
        raise ValueError(f"Maximum {MAX_SUBTASKS} subtasks per task")
    
    # Get next order
    max_order = await db.scalar(
        select(func.max(Subtask.order)).where(Subtask.task_id == task_id)
    )
    next_order = (max_order or 0) + 1
    
    subtask = Subtask(task_id=task_id, title=title, order=next_order)
    db.add(subtask)
    await db.flush()
    return subtask


async def get_subtask_by_id(db: AsyncSession, subtask_id: int) -> Subtask | None:
    """Get subtask by ID."""
    return await db.get(Subtask, subtask_id)


async def toggle_subtask(db: AsyncSession, subtask: Subtask) -> Subtask:
    """
    Toggle subtask completion status.
    
    If all subtasks become completed, auto-complete the parent task.
    """
    subtask.is_completed = not subtask.is_completed
    await db.flush()
    
    # Check if all subtasks complete -> auto-complete parent
    await check_auto_complete_task(db, subtask.task_id)
    return subtask


async def check_auto_complete_task(db: AsyncSession, task_id: int):
    """
    Auto-complete parent task if all subtasks are done.
    """
    # Get all subtasks for this task
    result = await db.execute(select(Subtask).where(Subtask.task_id == task_id))
    subtasks_list = result.scalars().all()
    
    # Logic:
    # 1. Must have subtasks (don't auto-complete empty tasks)
    # 2. All must be completed
    if subtasks_list and all(s.is_completed for s in subtasks_list):
        task = await db.get(Task, task_id)
        
        # Only complete if not already completed/cancelled
        if task and task.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
            task.status = TaskStatus.COMPLETED
            # Revoke pending notifications as task is done
            revoke_notifications(task_id)
            await db.flush()
