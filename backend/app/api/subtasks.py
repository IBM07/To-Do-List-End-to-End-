# ===========================================
# AuraTask - Subtasks API
# ===========================================
# CRUD endpoints for subtasks management

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.task import Task
from app.models.subtask import Subtask
from app.schemas.subtask import SubtaskCreate, SubtaskUpdate, SubtaskResponse
from app.crud.subtasks import create_subtask, toggle_subtask, get_subtask_by_id
from app.crud.task import get_task_by_id
from app.api.auth import get_current_user
from app.api.tasks import verify_task_ownership
from app.api.websocket import broadcast_task_updated


router = APIRouter()


async def verify_subtask_ownership(
    db: AsyncSession,
    subtask_id: int,
    user: User
) -> Subtask:
    """
    Verify user owns the subtask (via parent task).
    Returns the subtask if valid.
    """
    subtask = await get_subtask_by_id(db, subtask_id)
    if not subtask:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subtask not found"
        )
    
    # Check parent task ownership
    # We need to fetch the task to verify ownership
    task = await get_task_by_id(db, subtask.task_id)
    if not task or task.user_id != user.id:
         raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subtask not found"
        )
        
    return subtask


@router.post("/tasks/{task_id}/subtasks", response_model=SubtaskResponse, status_code=status.HTTP_201_CREATED)
async def add_subtask_endpoint(
    task_id: int,
    data: SubtaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add a subtask to a task.
    Max 10 subtasks per task.
    """
    # Verify parent task ownership
    task = await get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    await verify_task_ownership(task, current_user)
    
    try:
        subtask = await create_subtask(db, task_id, data.title)
        await db.commit()
        await db.refresh(subtask)
        
        # Broadcast task update (as progress changed)
        # We need to refresh task to get updated subtasks list/progress
        await db.refresh(task, ["subtasks"])
        # Use existing broadcast function but convert task to response first
        from app.api.utils import task_to_response
        response = task_to_response(task, current_user.timezone)
        await broadcast_task_updated(current_user.id, response)
        
        return subtask
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/tasks/{task_id}/subtasks", response_model=List[SubtaskResponse])
async def list_subtasks_endpoint(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all subtasks for a task."""
    # Verify parent task ownership
    task = await get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    await verify_task_ownership(task, current_user)
    
    result = await db.scalars(
        select(Subtask)
        .where(Subtask.task_id == task_id)
        .order_by(Subtask.order)
    )
    return result.all()


@router.patch("/subtasks/{subtask_id}/toggle", response_model=SubtaskResponse)
async def toggle_subtask_endpoint(
    subtask_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Toggle subtask completion status.
    May auto-complete parent task.
    """
    subtask = await verify_subtask_ownership(db, subtask_id, current_user)
    
    updated_subtask = await toggle_subtask(db, subtask)
    await db.commit()
    await db.refresh(updated_subtask)
    
    # Broadcast parent task update
    task = await get_task_by_id(db, subtask.task_id)
    from app.api.utils import task_to_response
    response = task_to_response(task, current_user.timezone)
    await broadcast_task_updated(current_user.id, response)
    
    return updated_subtask


@router.put("/subtasks/{subtask_id}", response_model=SubtaskResponse)
async def update_subtask_endpoint(
    subtask_id: int,
    data: SubtaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update subtask title or order."""
    subtask = await verify_subtask_ownership(db, subtask_id, current_user)
    
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(subtask, key, value)
    
    await db.commit()
    await db.refresh(subtask)
    
    # Broadcast parent task update (title change doesn't affect progress but order might affect display)
    task = await get_task_by_id(db, subtask.task_id)
    from app.api.utils import task_to_response
    response = task_to_response(task, current_user.timezone)
    await broadcast_task_updated(current_user.id, response)
    
    return subtask


@router.delete("/subtasks/{subtask_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subtask_endpoint(
    subtask_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a subtask."""
    subtask = await verify_subtask_ownership(db, subtask_id, current_user)
    task_id = subtask.task_id
    
    await db.delete(subtask)
    await db.commit()
    
    # Broadcast parent task update (progress changed)
    task = await get_task_by_id(db, task_id)
    if task:
        from app.api.utils import task_to_response
        response = task_to_response(task, current_user.timezone)
        await broadcast_task_updated(current_user.id, response)
    
    return None
