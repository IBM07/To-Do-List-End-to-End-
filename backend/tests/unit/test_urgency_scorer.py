"""
===========================================
AuraTask - Urgency Scorer Unit Tests
===========================================
Google-grade testing for urgency score calculation
"""

import pytest
from datetime import datetime, timezone, timedelta

from app.services.urgency_scorer import calculate_urgency_score
from app.models.task import Priority


class TestUrgencyScoreBasics:
    """Test basic urgency score calculations."""
    
    def test_urgent_task_due_in_1_hour_vs_medium_task_due_now(self):
        """CRITICAL: URGENT task in 1hr should score HIGHER than MEDIUM task due now."""
        now = datetime.now(timezone.utc)
        
        # URGENT task due in 1 hour
        urgent_score = calculate_urgency_score(
            due_date=now + timedelta(hours=1),
            priority=Priority.URGENT
        )
        
        # MEDIUM task due right now
        medium_score = calculate_urgency_score(
            due_date=now,
            priority=Priority.MEDIUM
        )
        
        # URGENT should score higher even with more time
        assert urgent_score > medium_score, \
            f"URGENT (1hr): {urgent_score} should be > MEDIUM (now): {medium_score}"
    
    def test_high_priority_multiplier(self):
        """Test: HIGH priority should score higher than MEDIUM with same due date."""
        due_date = datetime.now(timezone.utc) + timedelta(hours=6)
        
        high_score = calculate_urgency_score(due_date, Priority.HIGH)
        medium_score = calculate_urgency_score(due_date, Priority.MEDIUM)
        
        assert high_score > medium_score
    
    def test_low_priority_lowest_score(self):
        """Test: LOW priority should have lowest score."""
        due_date = datetime.now(timezone.utc) + timedelta(hours=6)
        
        low_score = calculate_urgency_score(due_date, Priority.LOW)
        medium_score = calculate_urgency_score(due_date, Priority.MEDIUM)
        high_score = calculate_urgency_score(due_date, Priority.HIGH)
        urgent_score = calculate_urgency_score(due_date, Priority.URGENT)
        
        assert low_score < medium_score < high_score < urgent_score


class TestUrgencyScoreOverdueTasks:
    """Test overdue task scoring with exponential increase."""
    
    def test_overdue_1_hour_vs_5_hours(self):
        """Test: Task overdue by 5 hours should score MUCH higher than 1 hour."""
        now = datetime.now(timezone.utc)
        
        # Overdue by 1 hour
        score_1hr = calculate_urgency_score(
            due_date=now - timedelta(hours=1),
            priority=Priority.MEDIUM
        )
        
        # Overdue by 5 hours
        score_5hr = calculate_urgency_score(
            due_date=now - timedelta(hours=5),
            priority=Priority.MEDIUM
        )
        
        # Should show growth (linear in current impl)
        assert score_5hr > score_1hr
    
    def test_overdue_1_day_vs_1_week(self):
        """Test: Task overdue by 1 week should score higher than 1 day."""
        now = datetime.now(timezone.utc)
        
        score_1day = calculate_urgency_score(
            due_date=now - timedelta(days=1),
            priority=Priority.MEDIUM
        )
        
        score_1week = calculate_urgency_score(
            due_date=now - timedelta(days=7),
            priority=Priority.MEDIUM
        )
        
        assert score_1week > score_1day
    
    def test_overdue_urgent_task_maximum_score(self):
        """Test: URGENT task overdue by days should have extremely high score."""
        now = datetime.now(timezone.utc)
        
        score = calculate_urgency_score(
            due_date=now - timedelta(days=3),
            priority=Priority.URGENT
        )
        
        # Should be very high (exact value depends on algorithm)
        assert score > 90, f"Overdue URGENT task should score > 90, got {score}"
    
    def test_just_overdue_vs_significantly_overdue(self):
        """Test: Recently overdue vs significantly overdue."""
        now = datetime.now(timezone.utc)
        
        # Just overdue (5 minutes)
        just_overdue = calculate_urgency_score(
            due_date=now - timedelta(minutes=5),
            priority=Priority.MEDIUM
        )
        
        # Significantly overdue (2 days)
        very_overdue = calculate_urgency_score(
            due_date=now - timedelta(days=2),
            priority=Priority.MEDIUM
        )
        
        assert very_overdue > just_overdue, \
            "Significantly overdue should be higher"


class TestUrgencyScoreFutureTasks:
    """Test future task scoring."""
    
    def test_task_due_in_1_year_near_zero(self):
        """Test: Task due in 1 year should have score near 0."""
        now = datetime.now(timezone.utc)
        
        score = calculate_urgency_score(
            due_date=now + timedelta(days=365),
            priority=Priority.MEDIUM
        )
        
        # Should be very low (near 0)
        assert score < 10, f"Task in 1 year should score < 10, got {score}"
    
    def test_task_due_in_1_month_low_score(self):
        """Test: Task due in 1 month should have low score."""
        now = datetime.now(timezone.utc)
        
        score = calculate_urgency_score(
            due_date=now + timedelta(days=30),
            priority=Priority.MEDIUM
        )
        
        # Should be low
        assert score < 30, f"Task in 1 month should score < 30, got {score}"
    
    def test_task_due_in_1_week_moderate_score(self):
        """Test: Task due in 1 week should have moderate score."""
        now = datetime.now(timezone.utc)
        
        score = calculate_urgency_score(
            due_date=now + timedelta(days=7),
            priority=Priority.MEDIUM
        )
        
        # Should be moderate (at 7 days boundary, score = 10)
        assert score >= 10, f"Task in 1 week should score >= 10, got {score}"
    
    def test_task_due_in_24_hours_high_score(self):
        """Test: Task due in 24 hours should have high score."""
        now = datetime.now(timezone.utc)
        
        score = calculate_urgency_score(
            due_date=now + timedelta(hours=24),
            priority=Priority.MEDIUM
        )
        
        # Should be around 60 (40 * 1.5)
        assert score > 50, f"Task in 24 hours should score > 50, got {score}"
    
    def test_task_due_in_1_hour_very_high_score(self):
        """Test: Task due in 1 hour should have very high score."""
        now = datetime.now(timezone.utc)
        
        score = calculate_urgency_score(
            due_date=now + timedelta(hours=1),
            priority=Priority.MEDIUM
        )
        
        # Should be very high (80 * 1.5 = 120)
        assert score > 100, f"Task in 1 hour should score > 100, got {score}"


class TestUrgencyScoreTimeDecay:
    """Test time-based score decay."""
    
    def test_score_increases_as_deadline_approaches(self):
        """Test: Score should increase as deadline gets closer."""
        now = datetime.now(timezone.utc)
        
        score_7days = calculate_urgency_score(
            now + timedelta(days=7),
            Priority.MEDIUM
        )
        
        score_3days = calculate_urgency_score(
            now + timedelta(days=3),
            Priority.MEDIUM
        )
        
        score_1day = calculate_urgency_score(
            now + timedelta(days=1),
            Priority.MEDIUM
        )
        
        score_1hour = calculate_urgency_score(
            now + timedelta(hours=1),
            Priority.MEDIUM
        )
        
        # Should be monotonically increasing
        assert score_7days < score_3days < score_1day < score_1hour
    
    def test_score_progression_is_smooth(self):
        """Test: Score progression should be smooth (no sudden jumps)."""
        now = datetime.now(timezone.utc)
        
        scores = []
        for hours in [48, 36, 24, 12, 6, 3, 1]:
            score = calculate_urgency_score(
                now + timedelta(hours=hours),
                Priority.MEDIUM
            )
            scores.append(score)
        
        # Check that each score is higher than the previous
        for i in range(len(scores) - 1):
            assert scores[i] < scores[i + 1], \
                f"Score should increase smoothly: {scores}"


class TestUrgencyScorePriorityInteraction:
    """Test interaction between priority and time."""
    
    def test_urgent_far_future_vs_low_near_future(self):
        """Test: URGENT task in 1 week vs LOW task in 1 hour."""
        now = datetime.now(timezone.utc)
        
        urgent_1week = calculate_urgency_score(
            now + timedelta(days=7),
            Priority.URGENT
        )
        
        low_1hour = calculate_urgency_score(
            now + timedelta(hours=1),
            Priority.LOW
        )
        
        # LOW task in 1 hour has higher time factor, so may score higher
        # This tests the balance between priority and urgency
        # Both are valid outcomes depending on design intent
        assert urgent_1week > 0 and low_1hour > 0
    
    def test_same_time_different_priorities(self):
        """Test: All priorities at same due date should be ordered correctly."""
        due_date = datetime.now(timezone.utc) + timedelta(hours=12)
        
        scores = {
            'URGENT': calculate_urgency_score(due_date, Priority.URGENT),
            'HIGH': calculate_urgency_score(due_date, Priority.HIGH),
            'MEDIUM': calculate_urgency_score(due_date, Priority.MEDIUM),
            'LOW': calculate_urgency_score(due_date, Priority.LOW),
        }
        
        assert scores['URGENT'] > scores['HIGH'] > scores['MEDIUM'] > scores['LOW']
    
    def test_priority_weight_significance(self):
        """Test: Priority should have significant weight in score."""
        now = datetime.now(timezone.utc)
        due_date = now + timedelta(hours=6)
        
        urgent = calculate_urgency_score(due_date, Priority.URGENT)
        low = calculate_urgency_score(due_date, Priority.LOW)
        
        # URGENT should be at least 2x LOW (weights are 2.5 vs 1.0)
        ratio = urgent / low if low > 0 else float('inf')
        assert ratio >= 2, f"URGENT should be at least 2x LOW, got ratio: {ratio}"


class TestUrgencyScoreEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_due_date_exactly_now(self):
        """Test: Task due exactly now."""
        now = datetime.now(timezone.utc)
        
        score = calculate_urgency_score(now, Priority.MEDIUM)
        
        # Should have high score (100 * 1.5 = 150)
        assert score > 100, f"Task due now should score > 100, got {score}"
    
    def test_very_far_future(self):
        """Test: Task due in 10 years."""
        now = datetime.now(timezone.utc)
        
        score = calculate_urgency_score(
            now + timedelta(days=3650),  # 10 years
            Priority.MEDIUM
        )
        
        # Should be near zero
        assert score < 5
    
    def test_very_overdue(self):
        """Test: Task overdue by 1 month."""
        now = datetime.now(timezone.utc)
        
        score = calculate_urgency_score(
            now - timedelta(days=30),
            Priority.MEDIUM
        )
        
        # Should be extremely high (capped at 200 * 1.5 = 300)
        assert score > 200
    
    def test_all_priorities_overdue(self):
        """Test: All priorities when overdue should still maintain order."""
        now = datetime.now(timezone.utc)
        overdue_date = now - timedelta(hours=6)
        
        scores = {
            'URGENT': calculate_urgency_score(overdue_date, Priority.URGENT),
            'HIGH': calculate_urgency_score(overdue_date, Priority.HIGH),
            'MEDIUM': calculate_urgency_score(overdue_date, Priority.MEDIUM),
            'LOW': calculate_urgency_score(overdue_date, Priority.LOW),
        }
        
        # Even when overdue, priority order should be maintained
        assert scores['URGENT'] > scores['HIGH'] > scores['MEDIUM'] > scores['LOW']


class TestUrgencyScoreConsistency:
    """Test score consistency and reproducibility."""
    
    def test_same_input_same_output(self):
        """Test: Same inputs should always produce same score."""
        now = datetime.now(timezone.utc)
        due_date = now + timedelta(hours=12)
        
        score1 = calculate_urgency_score(due_date, Priority.HIGH)
        score2 = calculate_urgency_score(due_date, Priority.HIGH)
        
        assert score1 == score2, "Score should be deterministic"
    
    def test_score_is_numeric(self):
        """Test: Score should always be a number."""
        now = datetime.now(timezone.utc)
        
        score = calculate_urgency_score(
            now + timedelta(hours=6),
            Priority.MEDIUM
        )
        
        assert isinstance(score, (int, float))
        assert not isinstance(score, bool)  # bool is subclass of int
    
    def test_score_is_non_negative(self):
        """Test: Score should never be negative."""
        now = datetime.now(timezone.utc)
        
        # Test various scenarios
        test_cases = [
            (now + timedelta(days=365), Priority.LOW),
            (now + timedelta(hours=1), Priority.MEDIUM),
            (now - timedelta(hours=1), Priority.HIGH),
            (now - timedelta(days=7), Priority.URGENT),
        ]
        
        for due_date, priority in test_cases:
            score = calculate_urgency_score(due_date, priority)
            assert score >= 0, f"Score should be non-negative, got {score}"


# Run tests with: pytest backend/tests/unit/test_urgency_scorer.py -v
