"""
===========================================
AuraTask - Groq AI NLP Parser
===========================================
Uses Groq's fast LLM API to intelligently parse task input
Only called when creating tasks - not running in background
"""

import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import logging

from groq import Groq

from app.config import settings

logger = logging.getLogger(__name__)


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
    
    if not settings.GROQ_API_KEY:
        print("[GROQ] No API key configured, using fallback parser")
        return _fallback_parse(nlp_input, user_timezone)
    
    try:
        # Create client only when needed (not in background)
        client = Groq(api_key=settings.GROQ_API_KEY)
        
        # Get current time for reference
        now = datetime.now(timezone.utc)
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M")
        current_day = now.strftime("%A")
        
        prompt = f"""You are a task parser. Extract task details from the input.

Current date: {current_date} ({current_day})
Current time: {current_time} UTC
User timezone: {user_timezone}

Input: "{nlp_input}"

Extract:
1. title: The task title (remove any priority markers like #Urgent, #High, etc.)
2. priority: One of URGENT, HIGH, MEDIUM, LOW
3. due_date: ISO format datetime in UTC if mentioned

IMPORTANT PRIORITY RULES:
- "#Urgent" or "#urgent" or "!!" or "asap" or "immediately" = "URGENT"
- "#High" or "#high" or "!" or "important" = "HIGH"
- "#Low" or "#low" or "whenever" or "no rush" = "LOW"
- Otherwise = "MEDIUM"

Return ONLY valid JSON (no markdown, no explanation):
{{"title": "task title here", "priority": "URGENT", "due_date": "2026-01-20T17:00:00Z"}}

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
        
        # Parse due date
        due_date_str = parsed.get("due_date")
        if due_date_str and due_date_str != "null":
            try:
                if due_date_str.endswith("Z"):
                    due_date_str = due_date_str[:-1] + "+00:00"
                result["due_date"] = datetime.fromisoformat(due_date_str)
                if result["due_date"].tzinfo is None:
                    result["due_date"] = result["due_date"].replace(tzinfo=timezone.utc)
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
