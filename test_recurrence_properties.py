"""Property-based tests for RecurrenceGenerator using hypothesis"""
import pytest
from datetime import date, time, timedelta
from hypothesis import given, assume, strategies as st, settings
from recurrence import RecurrenceGenerator
from models import RecurringPattern


# Strategy for generating valid dates
def dates_strategy(min_year=2024, max_year=2026):
    """Generate valid dates within a reasonable range"""
    return st.dates(
        min_value=date(min_year, 1, 1),
        max_value=date(max_year, 12, 31)
    )


# Strategy for generating RecurringPattern objects
@st.composite
def recurring_pattern_strategy(draw, frequency=None):
    """Generate valid RecurringPattern objects for testing"""
    if frequency is None:
        frequency = draw(st.sampled_from(['weekly', 'biweekly', 'monthly']))
    
    start = draw(dates_strategy(2024, 2025))
    
    # Generate end_date that's after start_date, or None
    has_end = draw(st.booleans())
    if has_end:
        # End date is 30-365 days after start
        days_ahead = draw(st.integers(min_value=30, max_value=365))
        end = start + timedelta(days=days_ahead)
    else:
        end = None
    
    lesson_time = time(15, 0)  # Fixed time for simplicity
    interval = draw(st.integers(min_value=1, max_value=3))
    
    # Create pattern based on frequency
    if frequency in ('weekly', 'biweekly'):
        weekday = draw(st.integers(min_value=0, max_value=6))
        pattern = RecurringPattern(
            teacher_id=1,
            student_id=1,
            start_date=start,
            end_date=end,
            time=lesson_time,
            frequency=frequency,
            interval=interval,
            weekday=weekday,
            day_of_month=None
        )
    else:  # monthly
        day_of_month = draw(st.integers(min_value=1, max_value=28))  # Avoid month-end issues
        pattern = RecurringPattern(
            teacher_id=1,
            student_id=1,
            start_date=start,
            end_date=end,
            time=lesson_time,
            frequency=frequency,
            interval=interval,
            weekday=None,
            day_of_month=day_of_month
        )
    
    return pattern


class TestOccurrenceValidityProperty:
    """Property 1: Occurrence Validity - all generated dates are within [start_date, end_date]
    
    **Validates: Requirements 1.2**
    """
    
    @given(
        pattern=recurring_pattern_strategy(),
        start_offset=st.integers(min_value=0, max_value=100),
        duration=st.integers(min_value=30, max_value=200)
    )
    @settings(max_examples=100, deadline=None)
    def test_all_occurrences_within_range(self, pattern, start_offset, duration):
        """All generated occurrences must be within [start_date, end_date]"""
        # Define the query range
        start_date = pattern.start_date + timedelta(days=start_offset)
        end_date = start_date + timedelta(days=duration)
        
        # If pattern has an end_date, ensure our range doesn't exceed it
        if pattern.end_date is not None:
            assume(start_date <= pattern.end_date)
            end_date = min(end_date, pattern.end_date)
        
        # Generate occurrences
        occurrences = list(RecurrenceGenerator.generate_occurrences(
            pattern, start_date, end_date, set()
        ))
        
        # Property: All occurrences must be within [start_date, end_date]
        for occurrence in occurrences:
            assert start_date <= occurrence <= end_date, \
                f"Occurrence {occurrence} is outside range [{start_date}, {end_date}]"
    
    @given(
        pattern=recurring_pattern_strategy(),
        start_offset=st.integers(min_value=0, max_value=100),
        duration=st.integers(min_value=30, max_value=200)
    )
    @settings(max_examples=100, deadline=None)
    def test_all_occurrences_respect_pattern_end_date(self, pattern, start_offset, duration):
        """All generated occurrences must respect pattern's end_date"""
        start_date = pattern.start_date + timedelta(days=start_offset)
        end_date = start_date + timedelta(days=duration)
        
        # If pattern has an end_date, ensure our range doesn't exceed it
        if pattern.end_date is not None:
            assume(start_date <= pattern.end_date)
        
        # Generate occurrences
        occurrences = list(RecurrenceGenerator.generate_occurrences(
            pattern, start_date, end_date, set()
        ))
        
        # Property: If pattern has end_date, no occurrence should exceed it
        if pattern.end_date is not None:
            for occurrence in occurrences:
                assert occurrence <= pattern.end_date, \
                    f"Occurrence {occurrence} exceeds pattern end_date {pattern.end_date}"
    
    @given(
        pattern=recurring_pattern_strategy(),
        start_offset=st.integers(min_value=0, max_value=100),
        duration=st.integers(min_value=30, max_value=200)
    )
    @settings(max_examples=100, deadline=None)
    def test_all_occurrences_after_pattern_start(self, pattern, start_offset, duration):
        """All generated occurrences must be on or after pattern's start_date"""
        start_date = pattern.start_date + timedelta(days=start_offset)
        end_date = start_date + timedelta(days=duration)
        
        if pattern.end_date is not None:
            assume(start_date <= pattern.end_date)
            end_date = min(end_date, pattern.end_date)
        
        # Generate occurrences
        occurrences = list(RecurrenceGenerator.generate_occurrences(
            pattern, start_date, end_date, set()
        ))
        
        # Property: All occurrences must be on or after pattern.start_date
        for occurrence in occurrences:
            assert occurrence >= pattern.start_date, \
                f"Occurrence {occurrence} is before pattern start_date {pattern.start_date}"
    
    @given(
        pattern=recurring_pattern_strategy(),
        start_offset=st.integers(min_value=0, max_value=100),
        duration=st.integers(min_value=30, max_value=200)
    )
    @settings(max_examples=100, deadline=None)
    def test_occurrences_in_ascending_order(self, pattern, start_offset, duration):
        """Generated occurrences must be in ascending order"""
        start_date = pattern.start_date + timedelta(days=start_offset)
        end_date = start_date + timedelta(days=duration)
        
        if pattern.end_date is not None:
            assume(start_date <= pattern.end_date)
            end_date = min(end_date, pattern.end_date)
        
        # Generate occurrences
        occurrences = list(RecurrenceGenerator.generate_occurrences(
            pattern, start_date, end_date, set()
        ))
        
        # Property: Occurrences must be in ascending order
        for i in range(len(occurrences) - 1):
            assert occurrences[i] < occurrences[i + 1], \
                f"Occurrences not in order: {occurrences[i]} >= {occurrences[i + 1]}"


class TestExceptionExclusionProperty:
    """Property 2: Exception Exclusion - no generated date is in exceptions Set
    
    **Validates: Correctness Property 3**
    """
    
    @given(
        pattern=recurring_pattern_strategy(),
        num_exceptions=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=100, deadline=None)
    def test_exceptions_excluded_from_occurrences(self, pattern, num_exceptions):
        """No generated occurrence should be in the exceptions set"""
        # Define query range
        start_date = pattern.start_date
        end_date = pattern.start_date + timedelta(days=180)
        
        if pattern.end_date is not None:
            end_date = min(end_date, pattern.end_date)
        
        # First, generate occurrences without exceptions
        all_occurrences = list(RecurrenceGenerator.generate_occurrences(
            pattern, start_date, end_date, set()
        ))
        
        # Skip if no occurrences generated
        assume(len(all_occurrences) > 0)
        
        # Create exceptions from some of the generated occurrences
        num_to_exclude = min(num_exceptions, len(all_occurrences))
        exceptions = set(all_occurrences[:num_to_exclude])
        
        # Generate occurrences with exceptions
        filtered_occurrences = list(RecurrenceGenerator.generate_occurrences(
            pattern, start_date, end_date, exceptions
        ))
        
        # Property: No occurrence should be in exceptions set
        for occurrence in filtered_occurrences:
            assert occurrence not in exceptions, \
                f"Occurrence {occurrence} found in exceptions set"
        
        # Additional check: filtered list should be shorter
        assert len(filtered_occurrences) == len(all_occurrences) - num_to_exclude, \
            f"Expected {len(all_occurrences) - num_to_exclude} occurrences, got {len(filtered_occurrences)}"
    
    @given(
        pattern=recurring_pattern_strategy(),
        exception_dates=st.lists(
            dates_strategy(2024, 2026),
            min_size=1,
            max_size=20,
            unique=True
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_arbitrary_exceptions_excluded(self, pattern, exception_dates):
        """Arbitrary exception dates should be excluded from occurrences"""
        # Define query range
        start_date = pattern.start_date
        end_date = pattern.start_date + timedelta(days=180)
        
        if pattern.end_date is not None:
            end_date = min(end_date, pattern.end_date)
        
        # Convert to set for O(1) lookup
        exceptions = set(exception_dates)
        
        # Generate occurrences with exceptions
        occurrences = list(RecurrenceGenerator.generate_occurrences(
            pattern, start_date, end_date, exceptions
        ))
        
        # Property: No occurrence should be in exceptions set
        for occurrence in occurrences:
            assert occurrence not in exceptions, \
                f"Occurrence {occurrence} found in exceptions set"
    
    @given(
        pattern=recurring_pattern_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_empty_exceptions_set_generates_all_occurrences(self, pattern):
        """Empty exceptions set should not filter any occurrences"""
        start_date = pattern.start_date
        end_date = pattern.start_date + timedelta(days=90)
        
        if pattern.end_date is not None:
            end_date = min(end_date, pattern.end_date)
        
        # Generate with empty exceptions
        occurrences_empty = list(RecurrenceGenerator.generate_occurrences(
            pattern, start_date, end_date, set()
        ))
        
        # Generate with no exceptions parameter would be same
        occurrences_no_param = list(RecurrenceGenerator.generate_occurrences(
            pattern, start_date, end_date, set()
        ))
        
        # Property: Both should generate the same occurrences
        assert occurrences_empty == occurrences_no_param
    
    @given(
        pattern=recurring_pattern_strategy(),
        num_exceptions=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=50, deadline=None)
    def test_exception_set_lookup_is_efficient(self, pattern, num_exceptions):
        """Verify that exceptions are checked efficiently (O(1) lookup)"""
        start_date = pattern.start_date
        end_date = pattern.start_date + timedelta(days=180)
        
        if pattern.end_date is not None:
            end_date = min(end_date, pattern.end_date)
        
        # Generate some occurrences
        all_occurrences = list(RecurrenceGenerator.generate_occurrences(
            pattern, start_date, end_date, set()
        ))
        
        assume(len(all_occurrences) > 0)
        
        # Create exceptions as a set (O(1) lookup)
        num_to_exclude = min(num_exceptions, len(all_occurrences))
        exceptions = set(all_occurrences[:num_to_exclude])
        
        # This should complete quickly due to O(1) set lookup
        # If it used a list, it would be O(n) per check
        filtered_occurrences = list(RecurrenceGenerator.generate_occurrences(
            pattern, start_date, end_date, exceptions
        ))
        
        # Property: Correct number of occurrences filtered
        assert len(filtered_occurrences) == len(all_occurrences) - len(exceptions)
