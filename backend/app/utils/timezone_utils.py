"""
===========================================
AuraTask - Timezone Utilities
===========================================
Convert between UTC and user timezones
"""

from datetime import datetime, timezone
from typing import Union
from zoneinfo import ZoneInfo


def convert_to_utc(local_time: datetime) -> datetime:
    """
    Convert a timezone-aware datetime to UTC.
    
    Args:
        local_time: Timezone-aware datetime in any timezone
        
    Returns:
        Datetime in UTC timezone
        
    Raises:
        ValueError: If datetime is naive (no timezone info)
    """
    if local_time.tzinfo is None:
        raise ValueError("Cannot convert naive datetime to UTC. Datetime must be timezone-aware.")
    
    return local_time.astimezone(timezone.utc)


def convert_from_utc(utc_time: datetime, target_timezone: str) -> datetime:
    """
    Convert a UTC datetime to a target timezone.
    
    Args:
        utc_time: Datetime in UTC
        target_timezone: IANA timezone string (e.g., 'Asia/Kolkata', 'America/New_York')
        
    Returns:
        Datetime in the target timezone
    """
    if target_timezone == "UTC":
        return utc_time.replace(tzinfo=timezone.utc) if utc_time.tzinfo is None else utc_time.astimezone(timezone.utc)
    
    target_tz = ZoneInfo(target_timezone)
    
    # Ensure input is UTC
    if utc_time.tzinfo is None:
        utc_time = utc_time.replace(tzinfo=timezone.utc)
    elif utc_time.tzinfo != timezone.utc:
        utc_time = utc_time.astimezone(timezone.utc)
    
    return utc_time.astimezone(target_tz)


def get_user_local_time(user_timezone: str) -> datetime:
    """
    Get the current time in the user's timezone.
    
    Args:
        user_timezone: IANA timezone string
        
    Returns:
        Current datetime in user's timezone
    """
    now_utc = datetime.now(timezone.utc)
    
    if user_timezone == "UTC":
        return now_utc
    
    target_tz = ZoneInfo(user_timezone)
    return now_utc.astimezone(target_tz)


def format_datetime_for_user(
    utc_time: datetime, 
    user_timezone: str,
    format_str: str = "%Y-%m-%d %I:%M %p"
) -> str:
    """
    Format a UTC datetime for display in user's timezone.
    
    Args:
        utc_time: Datetime in UTC
        user_timezone: User's IANA timezone string
        format_str: strftime format string
        
    Returns:
        Formatted datetime string
    """
    local_time = convert_from_utc(utc_time, user_timezone)
    return local_time.strftime(format_str)


def get_timezone_offset(timezone_str: str) -> str:
    """
    Get the UTC offset for a timezone.
    
    Args:
        timezone_str: IANA timezone string
        
    Returns:
        Offset string like '+05:30' or '-05:00'
    """
    if timezone_str == "UTC":
        return "+00:00"
    
    tz = ZoneInfo(timezone_str)
    now = datetime.now(tz)
    offset = now.strftime("%z")
    
    # Format as +HH:MM
    return f"{offset[:3]}:{offset[3:]}"


def is_valid_timezone(timezone_str: str) -> bool:
    """
    Check if a timezone string is valid.
    
    Args:
        timezone_str: IANA timezone string to validate
        
    Returns:
        True if valid, False otherwise
    """
    if timezone_str == "UTC":
        return True
    
    try:
        ZoneInfo(timezone_str)
        return True
    except KeyError:
        return False
