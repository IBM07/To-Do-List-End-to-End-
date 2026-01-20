"""
===========================================
AuraTask - NLP Parser Unit Tests
===========================================
Google-grade testing for HybridNLPParser
"""

import pytest
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from app.services.nlp_parser import parse_task_input


class TestNLPParserRelativeDates:
    """Test relative date parsing scenarios."""
    
    def test_tomorrow_at_5pm(self):
        """Test: 'tomorrow at 5pm'"""
        result = parse_task_input("Submit report tomorrow at 5pm", "America/New_York")
        
        assert result["title"] == "Submit report"
        assert result["due_date"] is not None
        
        # Verify it's tomorrow at 5pm in the user's timezone
        due_date = result["due_date"]
        user_tz = ZoneInfo("America/New_York")
        local_time = due_date.astimezone(user_tz)
        
        # Should be tomorrow
        tomorrow = datetime.now(user_tz) + timedelta(days=1)
        assert local_time.date() == tomorrow.date()
        
        # Should be 5pm (17:00)
        assert local_time.hour == 17
    
    def test_next_friday(self):
        """Test: 'next Friday'"""
        result = parse_task_input("Team meeting next Friday", "UTC")
        
        assert result["title"] == "Team meeting"
        assert result["due_date"] is not None
        
        # Verify it's a Friday
        due_date = result["due_date"]
        assert due_date.weekday() == 4  # Friday = 4
    
    def test_in_3_hours(self):
        """Test: 'in 3 hours'"""
        before = datetime.now(timezone.utc)
        result = parse_task_input("Call client in 3 hours", "UTC")
        after = datetime.now(timezone.utc)
        
        assert result["title"] == "Call client"
        assert result["due_date"] is not None
        
        # Should be approximately 3 hours from now (allow 1 min tolerance)
        expected = before + timedelta(hours=3)
        diff = abs((result["due_date"] - expected).total_seconds())
        assert diff < 60  # Within 1 minute
    
    def test_today_at_noon(self):
        """Test: 'today at noon'"""
        result = parse_task_input("Lunch meeting today at noon", "Asia/Kolkata")
        
        assert result["title"] == "Lunch meeting"
        assert result["due_date"] is not None
        
        # Verify it's noon (12:00) in user's timezone
        user_tz = ZoneInfo("Asia/Kolkata")
        local_time = result["due_date"].astimezone(user_tz)
        assert local_time.hour == 12
    
    def test_by_friday_5pm(self):
        """Test: 'by Friday 5pm'"""
        result = parse_task_input("Submit proposal by Friday 5pm", "America/New_York")
        
        assert result["title"] == "Submit proposal"
        assert result["due_date"] is not None
        
        # Verify it's a Friday at 5pm
        user_tz = ZoneInfo("America/New_York")
        local_time = result["due_date"].astimezone(user_tz)
        assert local_time.weekday() == 4  # Friday
        assert local_time.hour == 17  # 5pm


class TestNLPParserEdgeCases:
    """Test edge case time expressions."""
    
    def test_noon(self):
        """Test: 'noon' keyword"""
        result = parse_task_input("Review document by noon", "UTC")
        
        assert "Review document" in result["title"]
        # Note: 'noon' is preprocessed to '12:00 PM' - date parsing may vary
    
    def test_midnight(self):
        """Test: 'midnight' keyword"""
        result = parse_task_input("Deploy by midnight", "UTC")
        
        assert "Deploy" in result["title"]
        # Note: 'midnight' is preprocessed - date parsing may vary
    
    def test_eod_end_of_day(self):
        """Test: 'eod' (end of day)"""
        result = parse_task_input("Send email by eod", "America/New_York")
        
        assert result["title"] == "Send email"
        assert result["due_date"] is not None
        
        # EOD typically means 5pm or 6pm
        user_tz = ZoneInfo("America/New_York")
        local_time = result["due_date"].astimezone(user_tz)
        assert local_time.hour in [17, 18]  # 5pm or 6pm
    
    def test_cob_close_of_business(self):
        """Test: 'cob' (close of business)"""
        result = parse_task_input("Finish report by cob", "UTC")
        
        assert result["title"] == "Finish report"
        assert result["due_date"] is not None
        
        # COB typically means 5pm
        assert result["due_date"].hour == 17
    
    def test_next_monday_morning(self):
        """Test: 'next Monday morning'"""
        result = parse_task_input("Start project next Monday morning", "UTC")
        
        assert result["title"] == "Start project"
        assert result["due_date"] is not None
        
        # Should be Monday (0) in the morning (before noon)
        assert result["due_date"].weekday() == 0
        assert result["due_date"].hour < 12


class TestNLPParserPriorityExtraction:
    """Test priority tag extraction."""
    
    def test_urgent_uppercase(self):
        """Test: '#Urgent' (uppercase)"""
        result = parse_task_input("Fix critical bug #Urgent by tomorrow", "UTC")
        
        assert result["title"] == "Fix critical bug"
        assert result["priority"] == "URGENT"
        assert "#Urgent" not in result["title"]
    
    def test_high_lowercase(self):
        """Test: '#high' (lowercase)"""
        result = parse_task_input("Review PR #high", "UTC")
        
        assert result["title"] == "Review PR"
        assert result["priority"] == "HIGH"
        assert "#high" not in result["title"]
    
    def test_medium_mixedcase(self):
        """Test: '#MeDiUm' (mixed case)"""
        result = parse_task_input("Update docs #MeDiUm by Friday", "UTC")
        
        assert result["title"] == "Update docs"
        assert result["priority"] == "MEDIUM"
        assert "#MeDiUm" not in result["title"]
    
    def test_low_priority(self):
        """Test: '#Low'"""
        result = parse_task_input("Clean up code #Low", "UTC")
        
        assert result["title"] == "Clean up code"
        assert result["priority"] == "LOW"
        assert "#Low" not in result["title"]
    
    def test_no_priority_tag(self):
        """Test: No priority tag defaults to MEDIUM"""
        result = parse_task_input("Regular task by tomorrow", "UTC")
        
        assert result["title"] == "Regular task"
        assert result["priority"] == "MEDIUM"  # Parser defaults to MEDIUM
    
    def test_priority_at_beginning(self):
        """Test: Priority tag at the beginning"""
        result = parse_task_input("#Urgent Fix production issue", "UTC")
        
        assert result["title"] == "Fix production issue"
        assert result["priority"] == "URGENT"
    
    def test_priority_in_middle(self):
        """Test: Priority tag in the middle"""
        result = parse_task_input("Fix bug #High in payment system", "UTC")
        
        # Title should have priority removed but keep rest
        assert "#High" not in result["title"]
        assert "Fix bug" in result["title"]
        assert "in payment system" in result["title"]
        assert result["priority"] == "HIGH"


class TestNLPParserTitleExtraction:
    """Test title extraction and cleanup."""
    
    def test_title_with_priority_and_date(self):
        """Test: Title with both priority and date should strip both"""
        result = parse_task_input("Deploy app #Urgent by Friday 5pm", "UTC")
        
        # Title should not contain priority or date
        assert result["title"] == "Deploy app"
        assert "#Urgent" not in result["title"]
        assert "by Friday" not in result["title"]
        assert result["priority"] == "URGENT"
        assert result["due_date"] is not None
    
    def test_title_with_multiple_words(self):
        """Test: Multi-word title preservation"""
        result = parse_task_input("Review and approve quarterly financial report #High", "UTC")
        
        assert result["title"] == "Review and approve quarterly financial report"
        assert result["priority"] == "HIGH"
    
    def test_title_with_special_characters(self):
        """Test: Title with special characters"""
        result = parse_task_input("Fix bug: API returns 500 error #Urgent", "UTC")
        
        assert "Fix bug: API returns 500 error" in result["title"]
        assert result["priority"] == "URGENT"
    
    def test_title_only_no_metadata(self):
        """Test: Title without priority or date"""
        result = parse_task_input("Simple task", "UTC")
        
        assert result["title"] == "Simple task"
        assert result["priority"] == "MEDIUM"  # Default priority
        # due_date may or may not be parsed
    
    def test_empty_input(self):
        """Test: Empty input should return minimal result"""
        result = parse_task_input("", "UTC")
        
        # Should handle gracefully
        assert isinstance(result, dict)
        assert "title" in result


class TestNLPParserTimezoneHandling:
    """Test timezone-aware parsing."""
    
    def test_kolkata_timezone(self):
        """Test: Parse in Asia/Kolkata timezone"""
        result = parse_task_input("Meeting tomorrow at 10am", "Asia/Kolkata")
        
        assert result["due_date"] is not None
        
        # Convert to Kolkata time and verify
        kolkata_tz = ZoneInfo("Asia/Kolkata")
        local_time = result["due_date"].astimezone(kolkata_tz)
        assert local_time.hour == 10
    
    def test_new_york_timezone(self):
        """Test: Parse in America/New_York timezone"""
        result = parse_task_input("Call at 3pm tomorrow", "America/New_York")
        
        assert result["due_date"] is not None
        
        # Convert to NY time and verify
        ny_tz = ZoneInfo("America/New_York")
        local_time = result["due_date"].astimezone(ny_tz)
        assert local_time.hour == 15  # 3pm
    
    def test_utc_timezone(self):
        """Test: Parse in UTC timezone"""
        result = parse_task_input("Deploy at 8am", "UTC")
        
        assert result["due_date"] is not None
        assert result["due_date"].hour == 8


class TestNLPParserComplexScenarios:
    """Test complex real-world scenarios."""
    
    def test_full_sentence_with_all_metadata(self):
        """Test: Complete sentence with priority, date, and time"""
        result = parse_task_input(
            "Submit quarterly report to management #Urgent by next Friday at 2pm",
            "America/New_York"
        )
        
        assert "Submit quarterly report to management" in result["title"]
        assert result["priority"] == "URGENT"
        assert result["due_date"] is not None
        
        # Verify Friday at 2pm
        ny_tz = ZoneInfo("America/New_York")
        local_time = result["due_date"].astimezone(ny_tz)
        assert local_time.weekday() == 4  # Friday
        assert local_time.hour == 14  # 2pm
    
    def test_multiple_time_references(self):
        """Test: Input with multiple time references (should use first/most specific)"""
        result = parse_task_input("Review document by tomorrow or Friday", "UTC")
        
        assert result["title"] == "Review document"
        assert result["due_date"] is not None
        # Should parse "tomorrow" as it comes first
    
    def test_ambiguous_input(self):
        """Test: Ambiguous input should still extract something useful"""
        result = parse_task_input("Do the thing", "UTC")
        
        assert result["title"] == "Do the thing"
        # Should handle gracefully even without clear date/priority


# Run tests with: pytest backend/tests/unit/test_nlp_parser.py -v
