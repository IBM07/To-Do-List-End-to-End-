# ===========================================
# AuraTask - API Utilities
# ===========================================
# Helper functions for timezone conversion and response formatting

from datetime import datetime, timezone as tz
from typing import List, Optional

import pytz

from app.models.task import Task
from app.schemas.task import TaskResponse


def convert_utc_to_local(
    utc_datetime: datetime,
    user_timezone: str
) -> datetime:
    """
    Convert a UTC datetime to user's local timezone.
    
    Args:
        utc_datetime: Datetime in UTC
        user_timezone: User's timezone string (e.g., 'Asia/Kolkata')
        
    Returns:
        Datetime in user's local timezone
    """
    if utc_datetime is None:
        return None
    
    # Ensure UTC timezone is set
    if utc_datetime.tzinfo is None:
        utc_datetime = utc_datetime.replace(tzinfo=tz.utc)
    
    try:
        local_tz = pytz.timezone(user_timezone)
        return utc_datetime.astimezone(local_tz)
    except Exception:
        # Fallback to UTC if timezone is invalid
        return utc_datetime


def format_datetime_for_user(
    utc_datetime: datetime,
    user_timezone: str,
    format_str: str = "%b %d, %Y at %I:%M %p"
) -> str:
    """
    Format a UTC datetime for display in user's timezone.
    
    Args:
        utc_datetime: Datetime in UTC
        user_timezone: User's timezone string
        format_str: strftime format string
        
    Returns:
        Formatted datetime string
    """
    if utc_datetime is None:
        return ""
    
    local_dt = convert_utc_to_local(utc_datetime, user_timezone)
    return local_dt.strftime(format_str)


def datetime_to_iso_local(
    utc_datetime: datetime,
    user_timezone: str
) -> str:
    """
    Convert UTC datetime to ISO format string in user's timezone.
    
    Args:
        utc_datetime: Datetime in UTC
        user_timezone: User's timezone string
        
    Returns:
        ISO format string with timezone info
    """
    if utc_datetime is None:
        return ""
    
    local_dt = convert_utc_to_local(utc_datetime, user_timezone)
    return local_dt.isoformat()


def task_to_response(
    task: Task,
    user_timezone: str = "UTC"
) -> TaskResponse:
    """
    Convert a Task model to TaskResponse with timezone-aware fields.
    
    Args:
        task: Task model instance
        user_timezone: User's timezone for date formatting
        
    Returns:
        TaskResponse with computed timezone fields
    """
    response = TaskResponse.model_validate(task)
    response.set_user_timezone(user_timezone)
    return response


def tasks_to_response(
    tasks: List[Task],
    user_timezone: str = "UTC"
) -> List[TaskResponse]:
    """
    Convert multiple Task models to TaskResponse list.
    
    Args:
        tasks: List of Task model instances
        user_timezone: User's timezone
        
    Returns:
        List of TaskResponse objects
    """
    return [task_to_response(task, user_timezone) for task in tasks]


def get_relative_time(
    utc_datetime: datetime,
    reference_time: Optional[datetime] = None
) -> str:
    """
    Get human-readable relative time string.
    
    Args:
        utc_datetime: Target datetime in UTC
        reference_time: Reference time (default: now)
        
    Returns:
        Relative time string like "in 2 hours", "3 days ago"
    """
    if reference_time is None:
        reference_time = datetime.now(tz.utc)
    
    if utc_datetime.tzinfo is None:
        utc_datetime = utc_datetime.replace(tzinfo=tz.utc)
    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=tz.utc)
    
    diff = utc_datetime - reference_time
    total_seconds = diff.total_seconds()
    
    is_past = total_seconds < 0
    total_seconds = abs(total_seconds)
    
    # Calculate units
    minutes = total_seconds / 60
    hours = minutes / 60
    days = hours / 24
    
    # Generate string
    if days >= 1:
        value = int(days)
        unit = "day" if value == 1 else "days"
    elif hours >= 1:
        value = int(hours)
        unit = "hour" if value == 1 else "hours"
    elif minutes >= 1:
        value = int(minutes)
        unit = "minute" if value == 1 else "minutes"
    else:
        return "just now" if is_past else "now"
    
    if is_past:
        return f"{value} {unit} ago"
    else:
        return f"in {value} {unit}"
