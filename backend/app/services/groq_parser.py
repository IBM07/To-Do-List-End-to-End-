"""
===========================================
AuraTask - Groq AI NLP Parser
===========================================
Uses Groq's fast LLM API to intelligently parse task input
Only called when creating tasks - not running in background
"""

import json
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
import logging

from groq import Groq

from app.config import settings

logger = logging.getLogger(__name__)


def _parse_relative_time(text: str, user_timezone: str) -> Tuple[Optional[datetime], str]:
    """
    Parse relative time expressions like 'in 62 minutes', 'in 2 hours'.
    Returns (due_date in UTC, cleaned_text).
    
    SIMPLIFIED APPROACH: For relative times like "in X minutes", 
    we don't care about timezones - we just add X minutes to NOW.
    The result is the same regardless of timezone.
    """
    # Get current time in UTC - simple and accurate
    now_utc = datetime.now(timezone.utc)
    
    # Pattern: "in X minutes" or "after X minutes"
    minutes_match = re.search(r'(?:in|after)\s+(\d+)\s*(?:min(?:ute)?s?|mins?)', text, re.IGNORECASE)
    if minutes_match:
        minutes = int(minutes_match.group(1))
        due_utc = now_utc + timedelta(minutes=minutes)
        # Clean the relative time from text  
        cleaned = re.sub(r'(?:in|after)\s+\d+\s*(?:min(?:ute)?s?|mins?)\s*!*', '', text, flags=re.IGNORECASE).strip()
        print(f"[RELATIVE_TIME] '{text}' -> NOW({now_utc.strftime('%H:%M UTC')}) + {minutes} min = {due_utc.strftime('%H:%M UTC')}")
        return due_utc, cleaned
    
    # Pattern: "in X hours" or "after X hours"
    hours_match = re.search(r'(?:in|after)\s+(\d+)\s*(?:hour?s?|hrs?)', text, re.IGNORECASE)
    if hours_match:
        hours = int(hours_match.group(1))
        due_utc = now_utc + timedelta(hours=hours)
        cleaned = re.sub(r'(?:in|after)\s+\d+\s*(?:hour?s?|hrs?)\s*!*', '', text, flags=re.IGNORECASE).strip()
        print(f"[RELATIVE_TIME] '{text}' -> NOW({now_utc.strftime('%H:%M UTC')}) + {hours} hours = {due_utc.strftime('%H:%M UTC')}")
        return due_utc, cleaned
    
    return None, text


def parse_task_with_groq(nlp_input: str, user_timezone: str = "UTC") -> Dict[str, Any]:
    """
    Parse natural language task input using Groq AI.
    Called only when creating a task - not running in background.
    
    Args:
        nlp_input: Natural language task description
                   e.g., "Submit report #Urgent by tomorrow 5pm"
        user_timezone: User's timezone for date calculations
        
    Returns:
        {
            "title": "Submit report",
            "priority": "URGENT",
            "due_date": datetime (UTC),
            "parse_success": True/False
        }
    """
    result = { 
        "title": nlp_input,
        "priority": "MEDIUM",
        "due_date": None,
        "parse_success": False,
    }
    
    if not nlp_input or not nlp_input.strip():
        return result
    
    # FIRST: Try to parse relative times ourselves (LLMs are bad at math)
    relative_due_date, cleaned_input = _parse_relative_time(nlp_input, user_timezone)
    if relative_due_date:
        result["due_date"] = relative_due_date
        result["title"] = cleaned_input if cleaned_input else nlp_input.split()[0]
        result["parse_success"] = True
        # Still call Groq for priority extraction
        if settings.GROQ_API_KEY:
            try:
                priority_result = _extract_priority_with_groq(nlp_input)
                result["priority"] = priority_result
                result["title"] = _clean_title(cleaned_input, priority_result)
            except Exception as e:
                print(f"[GROQ] Priority extraction failed: {e}")
                result["priority"] = _extract_priority_simple(nlp_input)
        else:
            result["priority"] = _extract_priority_simple(nlp_input)
        print(f"[PARSER] ✅ Relative time parsed: title='{result['title']}', priority={result['priority']}, due={result['due_date']}")
        return result
    
    if not settings.GROQ_API_KEY:
        print("[GROQ] No API key configured, using fallback parser")
        return _fallback_parse(nlp_input, user_timezone)
    
    try:
        # Create client only when needed (not in background)
        client = Groq(api_key=settings.GROQ_API_KEY)
        
        # Get current time in USER's timezone for proper context
        import pytz
        now_utc = datetime.now(timezone.utc)
        
        try:
            user_tz = pytz.timezone(user_timezone)
            now_local = now_utc.astimezone(user_tz)
        except Exception:
            user_tz = pytz.UTC
            now_local = now_utc
        
        # Format for Groq - include full timestamp for accurate relative calculations
        current_date = now_local.strftime("%Y-%m-%d")
        current_time_12h = now_local.strftime("%I:%M %p")
        current_time_24h = now_local.strftime("%H:%M")
        current_day = now_local.strftime("%A")
        current_iso = now_local.strftime("%Y-%m-%dT%H:%M:%S")
        
        prompt = f"""You are a task parser. Extract task details from the input.

CURRENT DATETIME (VERY IMPORTANT): 
- Date: {current_date} ({current_day})
- Time: {current_time_12h} ({current_time_24h})
- Full ISO: {current_iso}
- Timezone: {user_timezone}

Input: "{nlp_input}"

Extract:
1. title: The task title (remove any priority markers like #Urgent, #High, etc.)
2. priority: One of URGENT, HIGH, MEDIUM, LOW
3. due_date: ISO format datetime. IMPORTANT: Calculate relative times correctly!

CRITICAL TIME CALCULATION RULES:
- "in 62 minutes" = Add exactly 62 minutes to {current_time_12h}
  Example: If current is 10:12 PM, then "in 62 minutes" = 11:14 PM (same day if before midnight)
- "in 1 hour" = Add 60 minutes to current time
- "tomorrow at 9am" = {current_date} + 1 day at 09:00:00
- "at 10:42 PM" = Today ({current_date}) at 22:42:00

IMPORTANT PRIORITY RULES:
- "#Urgent" or "#urgent" or "!!" or "asap" or "immediately" = "URGENT"
- "#High" or "#high" or "!" or "important" = "HIGH"
- "#Low" or "#low" or "whenever" or "no rush" = "LOW"
- Otherwise = "MEDIUM"

Return ONLY valid JSON (no markdown, no explanation):
{{"title": "task title here", "priority": "MEDIUM", "due_date": "2026-01-21T23:14:00"}}

NOTE: Return due_date WITHOUT 'Z' suffix - it's in {user_timezone}. I will convert to UTC.

If no due date mentioned, set due_date to null."""

        print(f"[GROQ] Parsing: '{nlp_input}'")
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a task parser. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=200,
        )
        
        response_text = response.choices[0].message.content.strip()
        print(f"[GROQ] Response: {response_text}")
        
        # Parse JSON (handle markdown code blocks if present)
        json_str = response_text
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0].strip()
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0].strip()
        
        parsed = json.loads(json_str)
        
        # Update result
        result["title"] = parsed.get("title", nlp_input)
        result["priority"] = parsed.get("priority", "MEDIUM").upper()
        
        # Validate priority
        if result["priority"] not in ["URGENT", "HIGH", "MEDIUM", "LOW"]:
            result["priority"] = "MEDIUM"
        
        # Parse due date (now in user's local timezone, need to convert to UTC)
        due_date_str = parsed.get("due_date")
        if due_date_str and due_date_str != "null":
            try:
                import pytz
                
                # Remove Z suffix if present (shouldn't be, but handle it)
                if due_date_str.endswith("Z"):
                    due_date_str = due_date_str[:-1]
                
                # Parse as naive datetime (it's in user's local timezone)
                local_dt = datetime.fromisoformat(due_date_str)
                
                # If it already has timezone info, use it
                if local_dt.tzinfo is not None:
                    result["due_date"] = local_dt.astimezone(timezone.utc)
                else:
                    # It's naive, assume it's in user's local timezone
                    try:
                        user_tz = pytz.timezone(user_timezone)
                        # Localize the naive datetime to user's timezone
                        local_dt = user_tz.localize(local_dt)
                        # Convert to UTC
                        result["due_date"] = local_dt.astimezone(timezone.utc)
                    except Exception:
                        # Fallback: assume it's UTC
                        result["due_date"] = local_dt.replace(tzinfo=timezone.utc)
                
                print(f"[GROQ] Converted '{due_date_str}' ({user_timezone}) -> {result['due_date']} (UTC)")
                
            except Exception as e:
                print(f"[GROQ] Date parse error: {e}")
                result["due_date"] = None
        
        result["parse_success"] = True
        print(f"[GROQ] ✅ Parsed: title='{result['title']}', priority={result['priority']}, due_date={result['due_date']}")
            
    except json.JSONDecodeError as e:
        print(f"[GROQ] ❌ JSON parse error: {e}")
        # Return basic result with title only
        result["title"] = nlp_input
        result["priority"] = "MEDIUM"
        result["due_date"] = None
        result["parse_success"] = False
    except Exception as e:
        print(f"[GROQ] ❌ Error: {e}")
        logger.error(f"Groq parse error: {e}")
        # Return basic result with title only
        result["title"] = nlp_input
        result["priority"] = "MEDIUM"
        result["due_date"] = None
        result["parse_success"] = False
    
    return result


def _extract_priority_simple(text: str) -> str:
    """
    Simple regex-based priority extraction.
    Used as fallback when Groq is not available.
    """
    text_lower = text.lower()
    
    if any(x in text_lower for x in ['#urgent', '!!', 'asap', 'immediately', 'urgent']):
        return "URGENT"
    elif any(x in text_lower for x in ['#high', '!', 'important', 'high priority']):
        return "HIGH"
    elif any(x in text_lower for x in ['#low', 'no rush', 'whenever', 'low priority']):
        return "LOW"
    else:
        return "MEDIUM"


def _extract_priority_with_groq(text: str) -> str:
    """
    Use Groq to extract priority from text.
    Only extracts priority, not dates (faster).
    """
    client = Groq(api_key=settings.GROQ_API_KEY)
    
    prompt = f"""Extract the priority level from this task:

"{text}"

Priority levels:
- URGENT: "#Urgent", "!!", "asap", "immediately"
- HIGH: "#High", "!", "important"
- LOW: "#Low", "no rush", "whenever"
- MEDIUM: default

Return ONLY one word: URGENT, HIGH, MEDIUM, or LOW"""
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You extract task priority. Reply with ONE word only."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=10,
    )
    
    priority = response.choices[0].message.content.strip().upper()
    if priority in ["URGENT", "HIGH", "MEDIUM", "LOW"]:
        return priority
    return "MEDIUM"


def _clean_title(text: str, priority: str) -> str:
    """
    Clean task title by removing priority markers and extra whitespace.
    """
    if not text:
        return text
    
    # Remove priority hashtags
    cleaned = re.sub(r'#(?:urgent|high|medium|low)', '', text, flags=re.IGNORECASE)
    # Remove !! and !
    cleaned = re.sub(r'!{1,2}', '', cleaned)
    # Remove extra whitespace
    cleaned = ' '.join(cleaned.split())
    
    return cleaned.strip() or text

