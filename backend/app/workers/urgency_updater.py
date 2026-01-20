# ===========================================
# AuraTask - Urgency Score Updater Worker
# ===========================================
# Celery task for periodic urgency score recalculation

from datetime import datetime, timezone

from celery import shared_task

from app.database import get_sync_session
from app.models.task import Task, TaskStatus
from app.services.urgency_scorer import calculate_urgency_score


@shared_task
def update_all_urgency_scores():
    """
    Recalculate urgency scores for all active tasks.
    
    Runs every 5 minutes via Celery Beat to keep dashboard
    sorting accurate as deadlines approach.
    
    Returns:
        Dict with update statistics
    """
    with get_sync_session() as db:
        # Get all non-completed tasks
        tasks = db.query(Task).filter(
            Task.status.not_in([TaskStatus.COMPLETED, TaskStatus.CANCELLED])
        ).all()
        
        current_time = datetime.now(timezone.utc)
        updated_count = 0
        
        for task in tasks:
            new_score = calculate_urgency_score(
                task.due_date,
                task.priority,
                current_time
            )
            
            # Only update if score changed significantly
            if abs(task.urgency_score - new_score) > 0.01:
                task.urgency_score = new_score
                updated_count += 1
        
        db.commit()
    
    return {
        "status": "completed",
        "total_tasks": len(tasks),
        "updated": updated_count,
    }


@shared_task
def update_single_task_score(task_id: int):
    """
    Update urgency score for a single task.
    
    Called after task creation or update.
    
    Args:
        task_id: Database ID of the task
        
    Returns:
        Dict with new score or error
    """
    with get_sync_session() as db:
        task = db.query(Task).filter(Task.id == task_id).first()
        
        if not task:
            return {"status": "error", "reason": "task_not_found"}
        
        if task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
            return {"status": "skipped", "reason": "task_completed"}
        
        new_score = calculate_urgency_score(task.due_date, task.priority)
        task.urgency_score = new_score
        db.commit()
        
        return {
            "status": "updated",
            "task_id": task_id,
            "new_score": new_score,
        }
