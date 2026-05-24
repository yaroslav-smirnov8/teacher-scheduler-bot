"""Unit tests for RecurrenceGenerator"""
import pytest
from datetime import date, time, timedelta
from recurrence import RecurrenceGenerator
from models import RecurringPattern


class TestWeeklyPattern:
    """Tests for weekly recurring patterns"""
    
    def test_weekly_every_monday(self):
        """Test weekly pattern generating every Monday"""
        pattern = RecurringPattern(
            teacher_id=1,
            student_id=1,
            start_date=date(2024, 1, 8),  # Monday
            end_date=date(2024, 2, 5),    # 4 weeks later
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0  # Monday
        )
        
        occurrences = list(RecurrenceGenerator.generate_occurrences(
            pattern, pattern.start_date, pattern.end_date, set()
        ))
        
        # Should generate 5 Mondays: Jan 8, 15, 22, 29, Feb 5
        assert len(occurrences) == 5
        assert occurrences[0] == date(2024, 1, 8)
        assert occurrences[1] == date(2024, 1, 15)
        assert occurrences[2] == date(2024, 1, 22)
        assert occurrences[3] == date(2024, 1, 29)
        assert occurrences[4] == date(2024, 2, 5)
        
        # All should be Mondays
        for occ in occurrences:
            assert occ.weekday() == 0
    
    def test_weekly_every_friday(self):
        """Test weekly pattern generating every Friday"""
        pattern = RecurringPattern(
            teacher_id=1,
            student_id=1,
            start_date=date(2024, 1, 5),  # Friday
            end_date=date(2024, 1, 26),   # 3 weeks later
            time=time(14, 30),
            frequency='weekly',
            interval=1,
            weekday=4  # Friday
        )
        
        occurrences = list(RecurrenceGenerator.generate_occurrences(
            pattern, pattern.start_date, pattern.end_date, set()
        ))
        
        # Should generate 4 Fridays: Jan 5, 12, 19, 26
        assert len(occurrences) == 4
        assert all(occ.weekday() == 4 for occ in occurrences)
    
    def test_weekly_with_exceptions(self):
        """Test weekly pattern with exception dates"""
        pattern = RecurringPattern(
            teacher_id=1,
            student_id=1,
            start_date=date(2024, 1, 8),
            end_date=date(2024, 2, 5),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        
        # Exclude Jan 15 and Jan 29
        exceptions = {date(2024, 1, 15), date(2024, 1, 29)}
        
        occurrences = list(RecurrenceGenerator.generate_occurrences(
            pattern, pattern.start_date, pattern.end_date, exceptions
        ))
        
        # Should generate 3 Mondays: Jan 8, 22, Feb 5 (15 and 29 excluded)
        assert len(occurrences) == 3
        assert date(2024, 1, 15) not in occurrences
        assert date(2024, 1, 29) not in occurrences
    
    def test_weekly_start_mid_week(self):
        """Test weekly pattern when start_date is not on the target weekday"""
        pattern = RecurringPattern(
            teacher_id=1,
            student_id=1,
            start_date=date(2024, 1, 10),  # Wednesday
            end_date=date(2024, 2, 5),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0  # Monday
        )
        
        occurrences = list(RecurrenceGenerator.generate_occurrences(
            pattern, pattern.start_date, pattern.end_date, set()
        ))
        
        # Should start from first Monday after Jan 10, which is Jan 15
        assert occurrences[0] == date(2024, 1, 15)
        assert all(occ.weekday() == 0 for occ in occurrences)
    
    def test_weekly_query_range_subset(self):
        """Test querying a subset of the pattern's date range"""
        pattern = RecurringPattern(
            teacher_id=1,
            student_id=1,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        
        # Query only February
        query_start = date(2024, 2, 1)
        query_end = date(2024, 2, 29)
        
        occurrences = list(RecurrenceGenerator.generate_occurrences(
            pattern, query_start, query_end, set()
        ))
        
        # Should only get Mondays in February
        assert all(query_start <= occ <= query_end for occ in occurrences)
        assert all(occ.weekday() == 0 for occ in occurrences)


class TestBiweeklyPattern:
    """Tests for biweekly (every 2 weeks) recurring patterns"""
    
    def test_biweekly_every_other_monday(self):
        """Test biweekly pattern generating every other Monday"""
        pattern = RecurringPattern(
            teacher_id=1,
            student_id=1,
            start_date=date(2024, 1, 8),  # Monday
            end_date=date(2024, 3, 4),    # 8 weeks later
            time=time(15, 0),
            frequency='biweekly',
            interval=1,
            weekday=0
        )
        
        occurrences = list(RecurrenceGenerator.generate_occurrences(
            pattern, pattern.start_date, pattern.end_date, set()
        ))
        
        # Should generate every other Monday: Jan 8, 22, Feb 5, 19, Mar 4
        assert len(occurrences) == 5
        assert occurrences[0] == date(2024, 1, 8)
        assert occurrences[1] == date(2024, 1, 22)
        assert occurrences[2] == date(2024, 2, 5)
        assert occurrences[3] == date(2024, 2, 19)
        assert occurrences[4] == date(2024, 3, 4)
        
        # Check 14-day intervals
        for i in range(len(occurrences) - 1):
            delta = (occurrences[i + 1] - occurrences[i]).days
            assert delta == 14
    
    def test_biweekly_with_interval_2(self):
        """Test biweekly pattern with interval=2 (every 4 weeks)"""
        pattern = RecurringPattern(
            teacher_id=1,
            student_id=1,
            start_date=date(2024, 1, 8),
            end_date=date(2024, 5, 6),
            time=time(15, 0),
            frequency='biweekly',
            interval=2,  # Every 4 weeks
            weekday=0
        )
        
        occurrences = list(RecurrenceGenerator.generate_occurrences(
            pattern, pattern.start_date, pattern.end_date, set()
        ))
        
        # Should generate every 4 weeks: Jan 8, Feb 5, Mar 4, Apr 1, Apr 29
        assert len(occurrences) == 5
        
        # Check 28-day intervals
        for i in range(len(occurrences) - 1):
            delta = (occurrences[i + 1] - occurrences[i]).days
            assert delta == 28


class TestMonthlyPattern:
    """Tests for monthly recurring patterns"""
    
    def test_monthly_15th_of_each_month(self):
        """Test monthly pattern on the 15th of each month"""
        pattern = RecurringPattern(
            teacher_id=1,
            student_id=1,
            start_date=date(2024, 1, 15),
            end_date=date(2024, 6, 15),
            time=time(16, 0),
            frequency='monthly',
            interval=1,
            day_of_month=15
        )
        
        occurrences = list(RecurrenceGenerator.generate_occurrences(
            pattern, pattern.start_date, pattern.end_date, set()
        ))
        
        # Should generate 6 occurrences: Jan 15 through Jun 15
        assert len(occurrences) == 6
        assert occurrences[0] == date(2024, 1, 15)
        assert occurrences[1] == date(2024, 2, 15)
        assert occurrences[2] == date(2024, 3, 15)
        assert occurrences[3] == date(2024, 4, 15)
        assert occurrences[4] == date(2024, 5, 15)
        assert occurrences[5] == date(2024, 6, 15)
        
        # All should be on the 15th
        for occ in occurrences:
            assert occ.day == 15
    
    def test_monthly_first_of_month(self):
        """Test monthly pattern on the 1st of each month"""
        pattern = RecurringPattern(
            teacher_id=1,
            student_id=1,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 4, 1),
            time=time(10, 0),
            frequency='monthly',
            interval=1,
            day_of_month=1
        )
        
        occurrences = list(RecurrenceGenerator.generate_occurrences(
            pattern, pattern.start_date, pattern.end_date, set()
        ))
        
        assert len(occurrences) == 4
        assert all(occ.day == 1 for occ in occurrences)
    
    def test_monthly_with_interval_2(self):
        """Test monthly pattern with interval=2 (every 2 months)"""
        pattern = RecurringPattern(
            teacher_id=1,
            student_id=1,
            start_date=date(2024, 1, 10),
            end_date=date(2024, 12, 10),
            time=time(15, 0),
            frequency='monthly',
            interval=2,
            day_of_month=10
        )
        
        occurrences = list(RecurrenceGenerator.generate_occurrences(
            pattern, pattern.start_date, pattern.end_date, set()
        ))
        
        # Should generate every 2 months: Jan, Mar, May, Jul, Sep, Nov
        assert len(occurrences) == 6
        assert occurrences[0] == date(2024, 1, 10)
        assert occurrences[1] == date(2024, 3, 10)
        assert occurrences[2] == date(2024, 5, 10)
        assert occurrences[3] == date(2024, 7, 10)
        assert occurrences[4] == date(2024, 9, 10)
        assert occurrences[5] == date(2024, 11, 10)
    
    def test_monthly_with_exceptions(self):
        """Test monthly pattern with exception dates"""
        pattern = RecurringPattern(
            teacher_id=1,
            student_id=1,
            start_date=date(2024, 1, 15),
            end_date=date(2024, 6, 15),
            time=time(16, 0),
            frequency='monthly',
            interval=1,
            day_of_month=15
        )
        
        # Exclude March and May
        exceptions = {date(2024, 3, 15), date(2024, 5, 15)}
        
        occurrences = list(RecurrenceGenerator.generate_occurrences(
            pattern, pattern.start_date, pattern.end_date, exceptions
        ))
        
        # Should generate 4 occurrences (6 - 2 exceptions)
        assert len(occurrences) == 4
        assert date(2024, 3, 15) not in occurrences
        assert date(2024, 5, 15) not in occurrences


class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""
    
    def test_month_end_february_non_leap_year(self):
        """Test monthly pattern on day 28 in February (non-leap year)"""
        pattern = RecurringPattern(
            teacher_id=1,
            student_id=1,
            start_date=date(2023, 1, 28),  # 2023 is not a leap year
            end_date=date(2023, 4, 28),
            time=time(15, 0),
            frequency='monthly',
            interval=1,
            day_of_month=28
        )
        
        occurrences = list(RecurrenceGenerator.generate_occurrences(
            pattern, pattern.start_date, pattern.end_date, set()
        ))
        
        # Should generate Jan 28, Feb 28, Mar 28, Apr 28
        assert len(occurrences) == 4
        assert date(2023, 2, 28) in occurrences
    
    def test_month_end_february_leap_year(self):
        """Test monthly pattern on day 28 in February (leap year)"""
        pattern = RecurringPattern(
            teacher_id=1,
            student_id=1,
            start_date=date(2024, 1, 28),  # 2024 is a leap year
            end_date=date(2024, 4, 28),
            time=time(15, 0),
            frequency='monthly',
            interval=1,
            day_of_month=28
        )
        
        occurrences = list(RecurrenceGenerator.generate_occurrences(
            pattern, pattern.start_date, pattern.end_date, set()
        ))
        
        # Should generate Jan 28, Feb 28, Mar 28, Apr 28
        assert len(occurrences) == 4
        assert date(2024, 2, 28) in occurrences
    
    def test_pattern_with_no_end_date(self):
        """Test pattern without end_date (infinite pattern)"""
        pattern = RecurringPattern(
            teacher_id=1,
            student_id=1,
            start_date=date(2024, 1, 8),
            end_date=None,  # Infinite
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        
        # Query a specific range
        query_start = date(2024, 1, 8)
        query_end = date(2024, 2, 5)
        
        occurrences = list(RecurrenceGenerator.generate_occurrences(
            pattern, query_start, query_end, set()
        ))
        
        # Should generate occurrences within query range
        assert len(occurrences) == 5
        assert all(query_start <= occ <= query_end for occ in occurrences)
    
    def test_empty_range_no_occurrences(self):
        """Test that no occurrences are generated when range is before pattern start"""
        pattern = RecurringPattern(
            teacher_id=1,
            student_id=1,
            start_date=date(2024, 6, 1),
            end_date=date(2024, 12, 31),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        
        # Query range before pattern starts
        query_start = date(2024, 1, 1)
        query_end = date(2024, 5, 31)
        
        occurrences = list(RecurrenceGenerator.generate_occurrences(
            pattern, query_start, query_end, set()
        ))
        
        # Should generate no occurrences
        assert len(occurrences) == 0
    
    def test_single_day_range(self):
        """Test querying a single day that matches a pattern"""
        pattern = RecurringPattern(
            teacher_id=1,
            student_id=1,
            start_date=date(2024, 1, 8),
            end_date=date(2024, 12, 31),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        
        # Query exactly one Monday
        query_date = date(2024, 1, 15)  # Monday
        
        occurrences = list(RecurrenceGenerator.generate_occurrences(
            pattern, query_date, query_date, set()
        ))
        
        # Should generate exactly one occurrence
        assert len(occurrences) == 1
        assert occurrences[0] == query_date


class TestNextOccurrence:
    """Tests for next_occurrence method"""
    
    def test_next_occurrence_weekly(self):
        """Test finding next occurrence for weekly pattern"""
        pattern = RecurringPattern(
            teacher_id=1,
            student_id=1,
            start_date=date(2024, 1, 8),
            end_date=date(2024, 12, 31),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0  # Monday
        )
        
        # Find next occurrence after Jan 10 (Wednesday)
        next_occ = RecurrenceGenerator.next_occurrence(pattern, date(2024, 1, 10))
        
        # Should be Jan 15 (next Monday)
        assert next_occ == date(2024, 1, 15)
    
    def test_next_occurrence_monthly(self):
        """Test finding next occurrence for monthly pattern"""
        pattern = RecurringPattern(
            teacher_id=1,
            student_id=1,
            start_date=date(2024, 1, 15),
            end_date=date(2024, 12, 15),
            time=time(15, 0),
            frequency='monthly',
            interval=1,
            day_of_month=15
        )
        
        # Find next occurrence after Jan 20
        next_occ = RecurrenceGenerator.next_occurrence(pattern, date(2024, 1, 20))
        
        # Should be Feb 15
        assert next_occ == date(2024, 2, 15)
    
    def test_next_occurrence_after_pattern_end(self):
        """Test that next_occurrence returns None after pattern ends"""
        pattern = RecurringPattern(
            teacher_id=1,
            student_id=1,
            start_date=date(2024, 1, 8),
            end_date=date(2024, 2, 5),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        
        # Find next occurrence after pattern ends
        next_occ = RecurrenceGenerator.next_occurrence(pattern, date(2024, 2, 10))
        
        # Should be None
        assert next_occ is None
    
    def test_next_occurrence_no_end_date(self):
        """Test next_occurrence with infinite pattern"""
        pattern = RecurringPattern(
            teacher_id=1,
            student_id=1,
            start_date=date(2024, 1, 8),
            end_date=None,
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=0
        )
        
        # Find next occurrence far in the future
        next_occ = RecurrenceGenerator.next_occurrence(pattern, date(2025, 6, 15))
        
        # Should find a Monday after June 15, 2025
        assert next_occ is not None
        assert next_occ > date(2025, 6, 15)
        assert next_occ.weekday() == 0


class TestErrorHandling:
    """Tests for error handling"""
    
    def test_weekly_without_weekday_raises_error(self):
        """Test that weekly pattern without weekday raises ValueError"""
        pattern = RecurringPattern(
            teacher_id=1,
            student_id=1,
            start_date=date(2024, 1, 8),
            end_date=date(2024, 2, 5),
            time=time(15, 0),
            frequency='weekly',
            interval=1,
            weekday=None  # Missing weekday
        )
        
        with pytest.raises(ValueError, match="weekday is required"):
            list(RecurrenceGenerator.generate_occurrences(
                pattern, pattern.start_date, pattern.end_date, set()
            ))
    
    def test_monthly_without_day_of_month_raises_error(self):
        """Test that monthly pattern without day_of_month raises ValueError"""
        pattern = RecurringPattern(
            teacher_id=1,
            student_id=1,
            start_date=date(2024, 1, 15),
            end_date=date(2024, 6, 15),
            time=time(15, 0),
            frequency='monthly',
            interval=1,
            day_of_month=None  # Missing day_of_month
        )
        
        with pytest.raises(ValueError, match="day_of_month is required"):
            list(RecurrenceGenerator.generate_occurrences(
                pattern, pattern.start_date, pattern.end_date, set()
            ))
    
    def test_unsupported_frequency_raises_error(self):
        """Test that unsupported frequency raises ValueError"""
        # The model validation will catch invalid frequency first
        with pytest.raises(ValueError, match="Frequency must be one of"):
            pattern = RecurringPattern(
                teacher_id=1,
                student_id=1,
                start_date=date(2024, 1, 8),
                end_date=date(2024, 2, 5),
                time=time(15, 0),
                frequency='daily',  # Unsupported
                interval=1,
                weekday=0
            )
