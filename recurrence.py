"""RecurrenceGenerator for generating recurring lesson dates"""
from datetime import date, timedelta
from typing import Generator, Optional, Set
from dateutil.relativedelta import relativedelta
from models import RecurringPattern


class RecurrenceGenerator:
    """Generator for recurring lesson dates with lazy evaluation and memory optimization"""
    
    @staticmethod
    def generate_occurrences(
        pattern: RecurringPattern,
        start_date: date,
        end_date: date,
        exceptions: Set[date]
    ) -> Generator[date, None, None]:
        """Generate recurring lesson dates based on pattern.
        
        Uses lazy evaluation (yield) for memory efficiency - generates dates on-demand
        rather than creating a full list in memory.
        
        Args:
            pattern: RecurringPattern object with frequency, interval, weekday, etc.
            start_date: Start of the date range to generate
            end_date: End of the date range to generate
            exceptions: Set of dates to exclude (O(1) lookup)
        
        Yields:
            date: Each occurrence date in ascending order
        
        Preconditions:
            - pattern is valid RecurringPattern object
            - start_date <= end_date
            - exceptions is a Set of dates
        
        Postconditions:
            - Yields dates in ascending order
            - All yielded dates are within [start_date, end_date]
            - No yielded date is in exceptions Set
            - Dates follow the pattern's frequency and interval
        
        Memory Optimization:
            - Uses generator (yield) instead of building list
            - O(1) memory per iteration
        """
        # Determine the actual start date for generation
        # Use the later of pattern.start_date and start_date
        current = max(pattern.start_date, start_date)
        
        # Determine the actual end date for generation
        # Use the earlier of pattern.end_date (if set) and end_date
        actual_end = end_date
        if pattern.end_date is not None:
            actual_end = min(pattern.end_date, end_date)
        
        # Handle weekly and biweekly patterns
        if pattern.frequency in ('weekly', 'biweekly'):
            if pattern.weekday is None:
                raise ValueError(f"weekday is required for {pattern.frequency} frequency")
            
            # Calculate interval in days
            interval_days = 7 if pattern.frequency == 'weekly' else 14
            interval_days *= pattern.interval
            
            # Find the first occurrence on or after current date
            # that matches the target weekday
            days_ahead = (pattern.weekday - current.weekday()) % 7
            if days_ahead == 0 and current < pattern.start_date:
                days_ahead = 7
            current = current + timedelta(days=days_ahead)
            
            # Generate occurrences
            while current <= actual_end:
                if current >= start_date and current not in exceptions:
                    yield current
                current = current + timedelta(days=interval_days)
        
        # Handle monthly patterns
        elif pattern.frequency == 'monthly':
            if pattern.day_of_month is None:
                raise ValueError("day_of_month is required for monthly frequency")
            
            # Start from the month containing current date
            # Set to the target day of month
            year = current.year
            month = current.month
            
            # Find first valid occurrence
            while True:
                try:
                    candidate = date(year, month, pattern.day_of_month)
                    if candidate >= current:
                        current = candidate
                        break
                except ValueError:
                    # Day doesn't exist in this month (e.g., Feb 30)
                    # Skip to next month
                    pass
                
                # Move to next month
                month += 1
                if month > 12:
                    month = 1
                    year += 1
                
                # Safety check to prevent infinite loop
                if year > actual_end.year + 1:
                    return
            
            # Generate occurrences
            while current <= actual_end:
                if current >= start_date and current not in exceptions:
                    yield current
                
                # Move to next occurrence using relativedelta
                for _ in range(pattern.interval):
                    current = current + relativedelta(months=1)
                    
                    # Handle case where day_of_month doesn't exist in target month
                    # (e.g., Jan 31 -> Feb 31 doesn't exist)
                    # relativedelta handles this by clamping to last day of month
                    # But we need to ensure we're on the correct day
                    if current.day != pattern.day_of_month:
                        # Try to set to the correct day
                        try:
                            current = date(current.year, current.month, pattern.day_of_month)
                        except ValueError:
                            # Day doesn't exist in this month, skip it
                            pass
        
        else:
            raise ValueError(f"Unsupported frequency: {pattern.frequency}")
    
    @staticmethod
    def next_occurrence(
        pattern: RecurringPattern,
        after_date: date
    ) -> Optional[date]:
        """Calculate the next recurrence date after the given date.
        
        Args:
            pattern: RecurringPattern object
            after_date: Find the next occurrence after this date
        
        Returns:
            The next occurrence date, or None if no more occurrences
        
        Preconditions:
            - pattern is valid RecurringPattern object
        
        Postconditions:
            - Returns date > after_date, or None
            - Returned date respects pattern.end_date
        """
        # If pattern has ended, return None
        if pattern.end_date is not None and after_date >= pattern.end_date:
            return None
        
        # Start searching from the day after after_date
        search_start = after_date + timedelta(days=1)
        
        # Use a reasonable search window (e.g., 2 years)
        # to avoid infinite generation
        search_end = search_start + timedelta(days=730)
        if pattern.end_date is not None:
            search_end = min(search_end, pattern.end_date)
        
        # Generate occurrences and return the first one
        for occurrence in RecurrenceGenerator.generate_occurrences(
            pattern, search_start, search_end, set()
        ):
            return occurrence
        
        return None
