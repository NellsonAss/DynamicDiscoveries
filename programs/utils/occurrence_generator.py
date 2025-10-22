"""
Occurrence Generator for Availability Rules

This utility generates dynamic occurrences from AvailabilityRule objects for a given date range.
Occurrences are computed on-the-fly and not persisted to the database.

Uses stdlib datetime/calendar only - no external dependencies.
"""

from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any, Optional
from django.utils import timezone


class Occurrence:
    """Represents a single computed occurrence of an availability rule."""
    
    def __init__(
        self,
        rule_id: int,
        rule_title: str,
        contractor_id: int,
        contractor_name: str,
        date: date,
        start_time: time,
        end_time: time,
        programs_offered: List[Dict[str, Any]],
        is_exception: bool = False,
        exception_note: str = ''
    ):
        self.rule_id = rule_id
        self.rule_title = rule_title
        self.contractor_id = contractor_id
        self.contractor_name = contractor_name
        self.date = date
        self.start_time = start_time
        self.end_time = end_time
        self.programs_offered = programs_offered
        self.is_exception = is_exception
        self.exception_note = exception_note
    
    @property
    def start_datetime(self):
        """Combine date and start_time into datetime."""
        return datetime.combine(self.date, self.start_time)
    
    @property
    def end_datetime(self):
        """Combine date and end_time into datetime."""
        return datetime.combine(self.date, self.end_time)
    
    def to_dict(self):
        """Convert to dictionary representation."""
        return {
            'rule_id': self.rule_id,
            'rule_title': self.rule_title,
            'contractor_id': self.contractor_id,
            'contractor_name': self.contractor_name,
            'date': self.date,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'start_datetime': self.start_datetime,
            'end_datetime': self.end_datetime,
            'programs_offered': self.programs_offered,
            'is_exception': self.is_exception,
            'exception_note': self.exception_note,
        }


def generate_occurrences_for_rules(
    rules_queryset,
    start_date: date,
    end_date: date,
    include_time_off: bool = True,
    time_off_queryset=None
) -> List[Occurrence]:
    """
    Generate all occurrences for the given rules within the date range.
    
    Args:
        rules_queryset: QuerySet of AvailabilityRule objects (should prefetch exceptions and programs)
        start_date: Start of visible date range
        end_date: End of visible date range (inclusive)
        include_time_off: Whether to filter out dates covered by approved time-off
        time_off_queryset: Optional queryset of ContractorDayOffRequest objects (approved only)
    
    Returns:
        List of Occurrence objects sorted by date and start_time
    """
    all_occurrences = []
    
    for rule in rules_queryset:
        # Get exceptions for this rule as a dict keyed by date
        exceptions_dict = {}
        for exc in rule.exceptions.all():
            exceptions_dict[exc.date] = exc
        
        # Get time-off dates for this contractor if applicable
        time_off_dates = set()
        if include_time_off and time_off_queryset:
            for time_off in time_off_queryset.filter(
                contractor=rule.contractor,
                status='approved'
            ):
                # Generate all dates in the time-off range
                current_date = time_off.start_date or time_off.date
                end = time_off.end_date or time_off.date
                while current_date <= end:
                    time_off_dates.add(current_date)
                    current_date += timedelta(days=1)
        
        # Generate occurrences based on rule kind
        if rule.kind == 'WEEKLY_RECURRING':
            occurrences = _generate_weekly_recurring_occurrences(
                rule, start_date, end_date, exceptions_dict, time_off_dates
            )
        elif rule.kind == 'DATE_RANGE':
            occurrences = _generate_date_range_occurrences(
                rule, start_date, end_date, exceptions_dict, time_off_dates
            )
        else:
            occurrences = []
        
        all_occurrences.extend(occurrences)
    
    # Sort by date, then start_time
    all_occurrences.sort(key=lambda occ: (occ.date, occ.start_time))
    
    return all_occurrences


def _generate_weekly_recurring_occurrences(
    rule,
    start_date: date,
    end_date: date,
    exceptions_dict: Dict[date, Any],
    time_off_dates: set
) -> List[Occurrence]:
    """Generate occurrences for WEEKLY_RECURRING rules."""
    occurrences = []
    
    # Get selected weekdays (0=Monday, 6=Sunday)
    selected_weekdays = rule.get_weekdays_list()
    
    if not selected_weekdays:
        return occurrences
    
    # Determine the actual date range to scan (intersection of rule bounds and visible range)
    scan_start = max(start_date, rule.date_start)
    scan_end = min(end_date, rule.date_end)
    
    if scan_start > scan_end:
        return occurrences
    
    # Get programs offered
    programs = _get_programs_list(rule)
    
    # Iterate through each day in the range
    current_date = scan_start
    while current_date <= scan_end:
        # Check if this day of week is selected
        if current_date.weekday() in selected_weekdays:
            # Check for time-off
            if current_date in time_off_dates:
                current_date += timedelta(days=1)
                continue
            
            # Check for exceptions
            if current_date in exceptions_dict:
                exception = exceptions_dict[current_date]
                if exception.type == 'SKIP':
                    # Skip this occurrence
                    current_date += timedelta(days=1)
                    continue
                elif exception.type == 'TIME_OVERRIDE':
                    # Use override times
                    occurrence = Occurrence(
                        rule_id=rule.id,
                        rule_title=rule.title,
                        contractor_id=rule.contractor.id,
                        contractor_name=rule.contractor.get_full_name(),
                        date=current_date,
                        start_time=exception.override_start_time,
                        end_time=exception.override_end_time,
                        programs_offered=programs,
                        is_exception=True,
                        exception_note=exception.note
                    )
                    occurrences.append(occurrence)
                    current_date += timedelta(days=1)
                    continue
            
            # Normal occurrence
            occurrence = Occurrence(
                rule_id=rule.id,
                rule_title=rule.title,
                contractor_id=rule.contractor.id,
                contractor_name=rule.contractor.get_full_name(),
                date=current_date,
                start_time=rule.start_time,
                end_time=rule.end_time,
                programs_offered=programs,
                is_exception=False,
                exception_note=''
            )
            occurrences.append(occurrence)
        
        current_date += timedelta(days=1)
    
    return occurrences


def _generate_date_range_occurrences(
    rule,
    start_date: date,
    end_date: date,
    exceptions_dict: Dict[date, Any],
    time_off_dates: set
) -> List[Occurrence]:
    """Generate occurrences for DATE_RANGE rules (daily occurrences)."""
    occurrences = []
    
    # Determine the actual date range to scan (intersection of rule bounds and visible range)
    scan_start = max(start_date, rule.date_start)
    scan_end = min(end_date, rule.date_end)
    
    if scan_start > scan_end:
        return occurrences
    
    # Get programs offered
    programs = _get_programs_list(rule)
    
    # Generate occurrence for every day in the range
    current_date = scan_start
    while current_date <= scan_end:
        # Check for time-off
        if current_date in time_off_dates:
            current_date += timedelta(days=1)
            continue
        
        # Check for exceptions
        if current_date in exceptions_dict:
            exception = exceptions_dict[current_date]
            if exception.type == 'SKIP':
                # Skip this occurrence
                current_date += timedelta(days=1)
                continue
            elif exception.type == 'TIME_OVERRIDE':
                # Use override times
                occurrence = Occurrence(
                    rule_id=rule.id,
                    rule_title=rule.title,
                    contractor_id=rule.contractor.id,
                    contractor_name=rule.contractor.get_full_name(),
                    date=current_date,
                    start_time=exception.override_start_time,
                    end_time=exception.override_end_time,
                    programs_offered=programs,
                    is_exception=True,
                    exception_note=exception.note
                )
                occurrences.append(occurrence)
                current_date += timedelta(days=1)
                continue
        
        # Normal occurrence
        occurrence = Occurrence(
            rule_id=rule.id,
            rule_title=rule.title,
            contractor_id=rule.contractor.id,
            contractor_name=rule.contractor.get_full_name(),
            date=current_date,
            start_time=rule.start_time,
            end_time=rule.end_time,
            programs_offered=programs,
            is_exception=False,
            exception_note=''
        )
        occurrences.append(occurrence)
        
        current_date += timedelta(days=1)
    
    return occurrences


def _get_programs_list(rule) -> List[Dict[str, Any]]:
    """Extract programs offered as a list of dicts."""
    programs = []
    for program in rule.programs_offered.all():
        programs.append({
            'id': program.id,
            'title': program.title,
            'program_type': program.buildout.program_type.name if program.buildout else None,
        })
    return programs


def detect_overlapping_rules(
    rules_queryset,
    start_date: date,
    end_date: date
) -> Dict[int, List[Dict[str, Any]]]:
    """
    Detect overlapping occurrences for the same contractor.
    
    Returns a dict mapping contractor_id to list of overlapping occurrence pairs.
    Each pair includes dates and times that overlap.
    """
    # Generate all occurrences
    occurrences = generate_occurrences_for_rules(
        rules_queryset, start_date, end_date, include_time_off=False
    )
    
    # Group by contractor and date
    contractor_date_map = {}
    for occ in occurrences:
        key = (occ.contractor_id, occ.date)
        if key not in contractor_date_map:
            contractor_date_map[key] = []
        contractor_date_map[key].append(occ)
    
    # Find overlaps
    overlaps = {}
    for (contractor_id, occ_date), occs in contractor_date_map.items():
        if len(occs) > 1:
            # Check for time overlaps
            for i, occ1 in enumerate(occs):
                for occ2 in occs[i+1:]:
                    # Check if time ranges overlap
                    if _times_overlap(
                        occ1.start_time, occ1.end_time,
                        occ2.start_time, occ2.end_time
                    ):
                        if contractor_id not in overlaps:
                            overlaps[contractor_id] = []
                        overlaps[contractor_id].append({
                            'date': occ_date,
                            'rule1_id': occ1.rule_id,
                            'rule1_title': occ1.rule_title,
                            'rule1_time': f"{occ1.start_time}-{occ1.end_time}",
                            'rule2_id': occ2.rule_id,
                            'rule2_title': occ2.rule_title,
                            'rule2_time': f"{occ2.start_time}-{occ2.end_time}",
                        })
    
    return overlaps


def _times_overlap(start1: time, end1: time, start2: time, end2: time) -> bool:
    """Check if two time ranges overlap."""
    # Convert to minutes for easier comparison
    start1_mins = start1.hour * 60 + start1.minute
    end1_mins = end1.hour * 60 + end1.minute
    start2_mins = start2.hour * 60 + start2.minute
    end2_mins = end2.hour * 60 + end2.minute
    
    # Check overlap: start1 < end2 and start2 < end1
    return start1_mins < end2_mins and start2_mins < end1_mins

