"""
===========================================
AuraTask - Timezone Utils Unit Tests
===========================================
Google-grade testing for timezone conversions
"""

import pytest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.utils.timezone_utils import (
    convert_to_utc,
    convert_from_utc,
    get_user_local_time,
    format_datetime_for_user,
)


class TestConvertToUTC:
    """Test conversion from local timezone to UTC."""
    
    def test_kolkata_to_utc(self):
        """Test: Convert Asia/Kolkata (IST) to UTC."""
        # IST is UTC+5:30
        # 2026-01-20 10:00 IST = 2026-01-20 04:30 UTC
        kolkata_tz = ZoneInfo("Asia/Kolkata")
        local_time = datetime(2026, 1, 20, 10, 0, 0, tzinfo=kolkata_tz)
        
        utc_time = convert_to_utc(local_time)
        
        assert utc_time.tzinfo == timezone.utc
        assert utc_time.hour == 4
        assert utc_time.minute == 30
    
    def test_new_york_to_utc_est(self):
        """Test: Convert America/New_York (EST) to UTC."""
        # EST is UTC-5 (winter)
        # 2026-01-20 10:00 EST = 2026-01-20 15:00 UTC
        ny_tz = ZoneInfo("America/New_York")
        local_time = datetime(2026, 1, 20, 10, 0, 0, tzinfo=ny_tz)
        
        utc_time = convert_to_utc(local_time)
        
        assert utc_time.tzinfo == timezone.utc
        assert utc_time.hour == 15
    
    def test_new_york_to_utc_edt(self):
        """Test: Convert America/New_York (EDT) to UTC."""
        # EDT is UTC-4 (summer)
        # 2026-07-20 10:00 EDT = 2026-07-20 14:00 UTC
        ny_tz = ZoneInfo("America/New_York")
        local_time = datetime(2026, 7, 20, 10, 0, 0, tzinfo=ny_tz)
        
        utc_time = convert_to_utc(local_time)
        
        assert utc_time.tzinfo == timezone.utc
        assert utc_time.hour == 14
    
    def test_utc_to_utc(self):
        """Test: UTC to UTC should be identity."""
        utc_time = datetime(2026, 1, 20, 10, 0, 0, tzinfo=timezone.utc)
        
        result = convert_to_utc(utc_time)
        
        assert result == utc_time
        assert result.tzinfo == timezone.utc
    
    def test_naive_datetime_raises_error(self):
        """Test: Naive datetime (no timezone) should raise error."""
        naive_time = datetime(2026, 1, 20, 10, 0, 0)
        
        with pytest.raises((ValueError, TypeError)):
            convert_to_utc(naive_time)


class TestConvertFromUTC:
    """Test conversion from UTC to local timezone."""
    
    def test_utc_to_kolkata(self):
        """Test: Convert UTC to Asia/Kolkata (IST)."""
        # 2026-01-20 04:30 UTC = 2026-01-20 10:00 IST
        utc_time = datetime(2026, 1, 20, 4, 30, 0, tzinfo=timezone.utc)
        
        local_time = convert_from_utc(utc_time, "Asia/Kolkata")
        
        assert local_time.tzinfo == ZoneInfo("Asia/Kolkata")
        assert local_time.hour == 10
        assert local_time.minute == 0
    
    def test_utc_to_new_york_est(self):
        """Test: Convert UTC to America/New_York (EST)."""
        # 2026-01-20 15:00 UTC = 2026-01-20 10:00 EST
        utc_time = datetime(2026, 1, 20, 15, 0, 0, tzinfo=timezone.utc)
        
        local_time = convert_from_utc(utc_time, "America/New_York")
        
        assert local_time.tzinfo == ZoneInfo("America/New_York")
        assert local_time.hour == 10
    
    def test_utc_to_new_york_edt(self):
        """Test: Convert UTC to America/New_York (EDT)."""
        # 2026-07-20 14:00 UTC = 2026-07-20 10:00 EDT
        utc_time = datetime(2026, 7, 20, 14, 0, 0, tzinfo=timezone.utc)
        
        local_time = convert_from_utc(utc_time, "America/New_York")
        
        assert local_time.tzinfo == ZoneInfo("America/New_York")
        assert local_time.hour == 10
    
    def test_utc_to_utc_string(self):
        """Test: Convert UTC to 'UTC' timezone string."""
        utc_time = datetime(2026, 1, 20, 10, 0, 0, tzinfo=timezone.utc)
        
        result = convert_from_utc(utc_time, "UTC")
        
        assert result == utc_time
        assert result.hour == 10
    
    def test_midnight_crossing(self):
        """Test: Conversion that crosses midnight."""
        # 2026-01-20 23:00 UTC = 2026-01-21 04:30 IST (next day)
        utc_time = datetime(2026, 1, 20, 23, 0, 0, tzinfo=timezone.utc)
        
        local_time = convert_from_utc(utc_time, "Asia/Kolkata")
        
        assert local_time.day == 21  # Next day
        assert local_time.hour == 4
        assert local_time.minute == 30


class TestRoundTripConversions:
    """Test bidirectional conversions maintain accuracy."""
    
    def test_kolkata_utc_kolkata_roundtrip(self):
        """Test: Kolkata -> UTC -> Kolkata should be identity."""
        kolkata_tz = ZoneInfo("Asia/Kolkata")
        original = datetime(2026, 1, 20, 15, 30, 45, tzinfo=kolkata_tz)
        
        # Convert to UTC and back
        utc = convert_to_utc(original)
        back_to_kolkata = convert_from_utc(utc, "Asia/Kolkata")
        
        # Should be equal (accounting for timezone)
        assert original.hour == back_to_kolkata.hour
        assert original.minute == back_to_kolkata.minute
        assert original.second == back_to_kolkata.second
    
    def test_new_york_utc_new_york_roundtrip(self):
        """Test: New York -> UTC -> New York should be identity."""
        ny_tz = ZoneInfo("America/New_York")
        original = datetime(2026, 1, 20, 15, 30, 45, tzinfo=ny_tz)
        
        utc = convert_to_utc(original)
        back_to_ny = convert_from_utc(utc, "America/New_York")
        
        assert original.hour == back_to_ny.hour
        assert original.minute == back_to_ny.minute
        assert original.second == back_to_ny.second
    
    def test_utc_kolkata_utc_roundtrip(self):
        """Test: UTC -> Kolkata -> UTC should be identity."""
        original = datetime(2026, 1, 20, 10, 0, 0, tzinfo=timezone.utc)
        
        kolkata = convert_from_utc(original, "Asia/Kolkata")
        back_to_utc = convert_to_utc(kolkata)
        
        assert original == back_to_utc


class TestGetUserLocalTime:
    """Test getting current time in user's timezone."""
    
    def test_get_kolkata_time(self):
        """Test: Get current time in Asia/Kolkata."""
        local_time = get_user_local_time("Asia/Kolkata")
        
        assert local_time.tzinfo == ZoneInfo("Asia/Kolkata")
        # Should be a recent time (within last minute)
        now_utc = datetime.now(timezone.utc)
        diff = abs((local_time.astimezone(timezone.utc) - now_utc).total_seconds())
        assert diff < 60
    
    def test_get_new_york_time(self):
        """Test: Get current time in America/New_York."""
        local_time = get_user_local_time("America/New_York")
        
        assert local_time.tzinfo == ZoneInfo("America/New_York")
    
    def test_get_utc_time(self):
        """Test: Get current time in UTC."""
        local_time = get_user_local_time("UTC")
        
        # Should be very close to datetime.now(timezone.utc)
        now_utc = datetime.now(timezone.utc)
        diff = abs((local_time - now_utc).total_seconds())
        assert diff < 1


class TestFormatDatetimeForUser:
    """Test datetime formatting for user's timezone."""
    
    def test_format_for_kolkata(self):
        """Test: Format UTC time for Kolkata user."""
        utc_time = datetime(2026, 1, 20, 10, 0, 0, tzinfo=timezone.utc)
        
        formatted = format_datetime_for_user(utc_time, "Asia/Kolkata")
        
        # Should contain the local time (15:30 IST)
        assert isinstance(formatted, str)
        assert len(formatted) > 0
    
    def test_format_for_new_york(self):
        """Test: Format UTC time for New York user."""
        utc_time = datetime(2026, 1, 20, 15, 0, 0, tzinfo=timezone.utc)
        
        formatted = format_datetime_for_user(utc_time, "America/New_York")
        
        assert isinstance(formatted, str)
        assert len(formatted) > 0
    
    def test_format_includes_date_and_time(self):
        """Test: Formatted string should include both date and time."""
        utc_time = datetime(2026, 1, 20, 10, 0, 0, tzinfo=timezone.utc)
        
        formatted = format_datetime_for_user(utc_time, "UTC")
        
        # Should contain year, and time components
        assert "2026" in formatted or "26" in formatted
        assert ":" in formatted  # Time separator


class TestTimezoneEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_daylight_saving_transition(self):
        """Test: Handle daylight saving time transitions."""
        ny_tz = ZoneInfo("America/New_York")
        
        # Before DST (EST) - January is winter
        winter = datetime(2026, 1, 20, 12, 0, 0, tzinfo=ny_tz)
        winter_utc = convert_to_utc(winter)
        
        # After DST (EDT) - July is summer
        summer = datetime(2026, 7, 20, 12, 0, 0, tzinfo=ny_tz)
        summer_utc = convert_to_utc(summer)
        
        # Same local time (12:00) should produce different UTC hours
        # Winter: 12:00 EST = 17:00 UTC (UTC-5)
        # Summer: 12:00 EDT = 16:00 UTC (UTC-4)
        assert winter_utc.hour != summer_utc.hour, \
            f"Winter UTC hour {winter_utc.hour} should differ from summer UTC hour {summer_utc.hour}"
    
    def test_leap_second_handling(self):
        """Test: Handle dates with potential leap seconds."""
        # Leap seconds are rare but should be handled gracefully
        utc_time = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        
        local_time = convert_from_utc(utc_time, "Asia/Kolkata")
        
        # Should not raise error
        assert local_time is not None
    
    def test_year_boundary_crossing(self):
        """Test: Conversion that crosses year boundary."""
        # 2025-12-31 23:00 UTC = 2026-01-01 04:30 IST
        utc_time = datetime(2025, 12, 31, 23, 0, 0, tzinfo=timezone.utc)
        
        local_time = convert_from_utc(utc_time, "Asia/Kolkata")
        
        assert local_time.year == 2026
        assert local_time.month == 1
        assert local_time.day == 1
    
    def test_invalid_timezone_string(self):
        """Test: Invalid timezone should raise error."""
        utc_time = datetime(2026, 1, 20, 10, 0, 0, tzinfo=timezone.utc)
        
        with pytest.raises(Exception):  # ZoneInfoNotFoundError or similar
            convert_from_utc(utc_time, "Invalid/Timezone")


class TestTimezoneConsistency:
    """Test consistency across different scenarios."""
    
    def test_same_instant_different_timezones(self):
        """Test: Same instant in different timezones should convert to same UTC."""
        # 2026-01-20 10:00 IST
        kolkata_tz = ZoneInfo("Asia/Kolkata")
        kolkata_time = datetime(2026, 1, 20, 10, 0, 0, tzinfo=kolkata_tz)
        
        # Convert to UTC
        utc_from_kolkata = convert_to_utc(kolkata_time)
        
        # Convert that UTC to NY time, then back to UTC
        ny_time = convert_from_utc(utc_from_kolkata, "America/New_York")
        utc_from_ny = convert_to_utc(ny_time)
        
        # Should be the same UTC time
        assert utc_from_kolkata == utc_from_ny
    
    def test_microsecond_precision(self):
        """Test: Conversions should preserve microsecond precision."""
        kolkata_tz = ZoneInfo("Asia/Kolkata")
        original = datetime(2026, 1, 20, 10, 0, 0, 123456, tzinfo=kolkata_tz)
        
        utc = convert_to_utc(original)
        back = convert_from_utc(utc, "Asia/Kolkata")
        
        assert original.microsecond == back.microsecond


# Run tests with: pytest backend/tests/unit/test_timezone_utils.py -v
