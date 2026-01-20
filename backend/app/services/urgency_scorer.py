# ===========================================
# AuraTask - Urgency Score Calculator
# ===========================================
# Mathematical algorithm for task priority sorting

from datetime import datetime, timezone
from enum import Enum
from typing import Union

from app.models.task import Priority


# Priority weight multipliers
PRIORITY_WEIGHTS = {
    Priority.LOW: 1.0,
    Priority.MEDIUM: 1.5,
    Priority.HIGH: 2.0,
    Priority.URGENT: 2.5,
}

# Also support string values
PRIORITY_WEIGHTS_STR = {
    "LOW": 1.0,
    "MEDIUM": 1.5,
    "HIGH": 2.0,
    "URGENT": 2.5,
}


def calculate_urgency_score(
    due_date: datetime,
    priority: Union[Priority, str],
    current_time: datetime = None
) -> float:
    """
    Calculate urgency score for task sorting.
    
    Formula: Score = Priority_Weight × Time_Factor
    
    Time Factor ranges:
    - Overdue: 100 + (hours_overdue × 2) - exponential increase
    - Due within 1 hour: 80-100
    - Due within 24 hours: 40-80
    - Due within 7 days: 10-40
    - Due later: 0-10
    
    Args:
        due_date: Task due date (should be timezone-aware)
        priority: Task priority level
        current_time: Optional current time for testing
        
    Returns:
        Urgency score (higher = more urgent)
    """
    # Ensure we have current time in UTC
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    # Handle naive datetimes by assuming UTC
    if due_date.tzinfo is None:
        due_date = due_date.replace(tzinfo=timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    
    # Calculate hours until due
    time_diff = due_date - current_time
    hours_until_due = time_diff.total_seconds() / 3600
    
    # Calculate time factor (0-100+ scale)
    if hours_until_due < 0:
        # OVERDUE - Score increases exponentially
        hours_overdue = abs(hours_until_due)
        time_factor = 100 + (hours_overdue * 2)
        # Cap at 200 to prevent extreme values
        time_factor = min(time_factor, 200)
    elif hours_until_due <= 1:
        # Due within 1 hour: 80-100
        time_factor = 80 + (20 * (1 - hours_until_due))
    elif hours_until_due <= 24:
        # Due within 24 hours: 40-80
        time_factor = 40 + (40 * (1 - hours_until_due / 24))
    elif hours_until_due <= 168:  # 7 days
        # Due within 7 days: 10-40
        time_factor = 10 + (30 * (1 - hours_until_due / 168))
    else:
        # Due later than 7 days: 0-10
        # Gradually decreases to 0 over 30 days
        days_until_due = hours_until_due / 24
        time_factor = max(0, 10 - (days_until_due / 30) * 10)
    
    # Get priority weight
    if isinstance(priority, str):
        priority_weight = PRIORITY_WEIGHTS_STR.get(priority.upper(), 1.5)
    else:
        priority_weight = PRIORITY_WEIGHTS.get(priority, 1.5)
    
    # Calculate final score
    score = time_factor * priority_weight
    
    return round(score, 2)


def get_urgency_level(score: float) -> str:
    """
    Get human-readable urgency level from score.
    
    Args:
        score: Calculated urgency score
        
    Returns:
        Urgency level string
    """
    if score >= 200:
        return "CRITICAL"
    elif score >= 150:
        return "OVERDUE"
    elif score >= 100:
        return "DUE_NOW"
    elif score >= 60:
        return "DUE_SOON"
    elif score >= 30:
        return "UPCOMING"
    else:
        return "LATER"


def batch_update_scores(tasks: list) -> list:
    """
    Update urgency scores for a batch of tasks.
    
    Used by Celery Beat to periodically recalculate scores.
    
    Args:
        tasks: List of Task objects
        
    Returns:
        List of (task_id, new_score) tuples
    """
    current_time = datetime.now(timezone.utc)
    updates = []
    
    for task in tasks:
        new_score = calculate_urgency_score(
            task.due_date,
            task.priority,
            current_time
        )
        updates.append((task.id, new_score))
    
    return updates
