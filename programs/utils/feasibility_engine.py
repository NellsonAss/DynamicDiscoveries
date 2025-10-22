"""
Feasibility Engine for Availability Rules with Booking Subtraction

This module computes which programs are feasible on given days by:
1. Getting all active rules for a contractor on a date
2. Computing the union of rule windows (handling overlaps)
3. Subtracting existing bookings to find free gaps
4. Checking which programs can fit in the remaining gaps

No external dependencies - pure Python stdlib.
"""

from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass


@dataclass
class TimeInterval:
    """Represents a time interval on a specific date."""
    start_time: time
    end_time: time
    
    def to_minutes(self) -> Tuple[int, int]:
        """Convert to minutes since midnight for easier computation."""
        start_mins = self.start_time.hour * 60 + self.start_time.minute
        end_mins = self.end_time.hour * 60 + self.end_time.minute
        return (start_mins, end_mins)
    
    @classmethod
    def from_minutes(cls, start_mins: int, end_mins: int) -> 'TimeInterval':
        """Create from minutes since midnight."""
        start_hour, start_min = divmod(start_mins, 60)
        end_hour, end_min = divmod(end_mins, 60)
        return cls(
            start_time=time(start_hour, start_min),
            end_time=time(end_hour, end_min)
        )
    
    def duration_minutes(self) -> int:
        """Return duration in minutes."""
        start_mins, end_mins = self.to_minutes()
        return end_mins - start_mins
    
    def overlaps(self, other: 'TimeInterval') -> bool:
        """Check if this interval overlaps with another."""
        s1, e1 = self.to_minutes()
        s2, e2 = other.to_minutes()
        return s1 < e2 and s2 < e1


@dataclass
class DayFeasibility:
    """Represents feasibility analysis for a single day."""
    date: date
    contractor_id: int
    
    # Rule windows active on this day (before bookings)
    rule_windows: List[TimeInterval]
    
    # Bookings that occupy time
    bookings: List[Dict[str, Any]]  # List of {start_time, end_time, program, child}
    
    # Free gaps after subtracting bookings (computed)
    free_gaps: List[TimeInterval]
    
    # Programs feasible in any of the gaps
    feasible_programs: List[Dict[str, Any]]  # List of {program_id, title, duration_minutes, fits_in_gap}
    
    # Summary time ranges for display
    summary_ranges: List[str]  # e.g., ["1-6p", "7-9p"]


def compute_day_feasibility(
    contractor_id: int,
    target_date: date,
    rules_queryset,
    bookings_queryset,
    programs_queryset,
    exceptions_dict: Optional[Dict[date, Any]] = None
) -> DayFeasibility:
    """
    Compute feasibility for a single day.
    
    Args:
        contractor_id: ID of the contractor
        target_date: Date to analyze
        rules_queryset: QuerySet of AvailabilityRule (filtered for this contractor, active)
        bookings_queryset: QuerySet of RuleBooking (filtered for relevant date)
        programs_queryset: QuerySet of ProgramInstance (with scheduling_config)
        exceptions_dict: Optional dict mapping date -> AvailabilityException
    
    Returns:
        DayFeasibility object with analysis results
    """
    
    # Step 1: Get rule windows for this day
    rule_windows = []
    for rule in rules_queryset:
        # Check if rule applies to this date
        if not (rule.date_start <= target_date <= rule.date_end):
            continue
        
        # For WEEKLY_RECURRING, check day of week
        if rule.kind == 'WEEKLY_RECURRING':
            weekday = target_date.weekday()
            if weekday not in rule.get_weekdays_list():
                continue
        
        # Check for exceptions
        if exceptions_dict and target_date in exceptions_dict:
            exception = exceptions_dict[target_date]
            if exception.type == 'SKIP':
                continue  # Skip this date
            elif exception.type == 'TIME_OVERRIDE':
                # Use override times
                rule_windows.append(TimeInterval(
                    start_time=exception.override_start_time,
                    end_time=exception.override_end_time
                ))
                continue
        
        # Add normal rule window
        rule_windows.append(TimeInterval(
            start_time=rule.start_time,
            end_time=rule.end_time
        ))
    
    # Step 2: Merge overlapping rule windows into union
    merged_windows = _merge_overlapping_intervals(rule_windows)
    
    # Step 3: Get bookings for this day
    booking_intervals = []
    booking_details = []
    for booking in bookings_queryset:
        if booking.booking_date == target_date and booking.status in ['confirmed', 'pending']:
            booking_intervals.append(TimeInterval(
                start_time=booking.start_time,
                end_time=booking.end_time
            ))
            booking_details.append({
                'id': booking.id,
                'start_time': booking.start_time,
                'end_time': booking.end_time,
                'program': booking.program.title if booking.program else 'Unknown',
                'child': booking.child.first_name if booking.child else 'Unknown',
                'duration_minutes': booking.duration_minutes
            })
    
    # Step 4: Subtract bookings from merged windows to get free gaps
    free_gaps = _subtract_intervals(merged_windows, booking_intervals)
    
    # Step 5: Determine which programs can fit
    feasible_programs = []
    for program in programs_queryset:
        # Get program duration
        duration_minutes = _get_program_duration_minutes(program)
        if duration_minutes is None:
            continue
        
        # Check if any free gap can accommodate this program
        fits = any(gap.duration_minutes() >= duration_minutes for gap in free_gaps)
        
        if fits:
            feasible_programs.append({
                'program_id': program.id,
                'title': program.title,
                'duration_minutes': duration_minutes,
                'fits_in_gap': True
            })
    
    # Step 6: Create summary ranges for display
    summary_ranges = [_format_time_range(gap.start_time, gap.end_time) for gap in merged_windows]
    
    return DayFeasibility(
        date=target_date,
        contractor_id=contractor_id,
        rule_windows=merged_windows,
        bookings=booking_details,
        free_gaps=free_gaps,
        feasible_programs=feasible_programs,
        summary_ranges=summary_ranges
    )


def compute_month_feasibility(
    contractor_id: int,
    year: int,
    month: int,
    rules_queryset,
    bookings_queryset,
    programs_queryset
) -> Dict[date, DayFeasibility]:
    """
    Compute feasibility for all days in a month.
    
    Returns dict mapping date -> DayFeasibility
    """
    import calendar as cal
    
    # Get date range for month
    first_day = date(year, month, 1)
    last_day_num = cal.monthrange(year, month)[1]
    last_day = date(year, month, last_day_num)
    
    # Collect all exceptions once
    exceptions_by_date = {}
    for rule in rules_queryset:
        for exc in rule.exceptions.all():
            if first_day <= exc.date <= last_day:
                exceptions_by_date[exc.date] = exc
    
    # Compute feasibility for each day
    result = {}
    current_date = first_day
    while current_date <= last_day:
        day_feasibility = compute_day_feasibility(
            contractor_id,
            current_date,
            rules_queryset,
            bookings_queryset.filter(booking_date=current_date),
            programs_queryset,
            exceptions_by_date
        )
        
        # Only include days with rule windows
        if day_feasibility.rule_windows:
            result[current_date] = day_feasibility
        
        current_date += timedelta(days=1)
    
    return result


def _merge_overlapping_intervals(intervals: List[TimeInterval]) -> List[TimeInterval]:
    """Merge overlapping time intervals to create union of windows."""
    if not intervals:
        return []
    
    # Convert to minutes for easier manipulation
    mins_intervals = [(i.to_minutes()[0], i.to_minutes()[1]) for i in intervals]
    
    # Sort by start time
    mins_intervals.sort()
    
    # Merge overlapping
    merged = []
    current_start, current_end = mins_intervals[0]
    
    for start, end in mins_intervals[1:]:
        if start <= current_end:
            # Overlapping, extend current
            current_end = max(current_end, end)
        else:
            # No overlap, save current and start new
            merged.append((current_start, current_end))
            current_start, current_end = start, end
    
    # Don't forget last one
    merged.append((current_start, current_end))
    
    # Convert back to TimeInterval objects
    return [TimeInterval.from_minutes(s, e) for s, e in merged]


def _subtract_intervals(
    available: List[TimeInterval],
    occupied: List[TimeInterval]
) -> List[TimeInterval]:
    """
    Subtract occupied intervals from available intervals to get free gaps.
    
    This is the core of the feasibility engine - it computes what time is left
    after subtracting bookings from available windows.
    """
    if not available:
        return []
    
    if not occupied:
        return available
    
    # Convert all to minutes
    free_segments = [i.to_minutes() for i in available]
    occupied_segments = sorted([i.to_minutes() for i in occupied])
    
    # For each occupied segment, carve it out of free segments
    result = []
    for free_start, free_end in free_segments:
        current_free = [(free_start, free_end)]
        
        for occ_start, occ_end in occupied_segments:
            new_free = []
            for seg_start, seg_end in current_free:
                # No overlap
                if occ_end <= seg_start or occ_start >= seg_end:
                    new_free.append((seg_start, seg_end))
                # Occupied completely covers this segment
                elif occ_start <= seg_start and occ_end >= seg_end:
                    pass  # Nothing left
                # Occupied in the middle, split into two
                elif occ_start > seg_start and occ_end < seg_end:
                    new_free.append((seg_start, occ_start))
                    new_free.append((occ_end, seg_end))
                # Occupied overlaps start
                elif occ_start <= seg_start < occ_end < seg_end:
                    new_free.append((occ_end, seg_end))
                # Occupied overlaps end
                elif seg_start < occ_start < seg_end <= occ_end:
                    new_free.append((seg_start, occ_start))
            
            current_free = new_free
        
        result.extend(current_free)
    
    # Convert back to TimeInterval objects, filtering out tiny gaps
    return [
        TimeInterval.from_minutes(s, e) 
        for s, e in result 
        if e - s >= 15  # Minimum 15-minute gap
    ]


def _get_program_duration_minutes(program) -> Optional[int]:
    """Get program duration in minutes from ProgramBuildoutScheduling."""
    try:
        if hasattr(program.buildout, 'scheduling_config'):
            duration_hours = program.buildout.scheduling_config.default_session_duration
            return int(float(duration_hours) * 60)
    except Exception:
        pass
    
    # Fallback: assume 60 minutes
    return 60


def _format_time_range(start_time: time, end_time: time) -> str:
    """Format time range for display (e.g., '1-6p', '9a-12p')."""
    def format_time(t: time) -> str:
        hour = t.hour
        if hour == 0:
            return '12a'
        elif hour < 12:
            return f'{hour}a'
        elif hour == 12:
            return '12p'
        else:
            return f'{hour-12}p'
    
    return f'{format_time(start_time)}-{format_time(end_time)}'


def find_valid_start_times(
    free_gaps: List[TimeInterval],
    duration_minutes: int,
    interval_minutes: int = 15
) -> List[time]:
    """
    Find all valid start times for a program within free gaps.
    
    Args:
        free_gaps: List of free time intervals
        duration_minutes: Required program duration
        interval_minutes: Time increments (default 15 mins)
    
    Returns:
        List of valid start times where program can fit entirely in a gap
    """
    valid_starts = []
    
    for gap in free_gaps:
        gap_start_mins, gap_end_mins = gap.to_minutes()
        
        # Try every interval start time in this gap
        current_mins = gap_start_mins
        while current_mins + duration_minutes <= gap_end_mins:
            # This start time works - program fits in gap
            hour, minute = divmod(current_mins, 60)
            valid_starts.append(time(hour, minute))
            current_mins += interval_minutes
    
    return valid_starts

