"""
Calendar utilities for generating month views and aggregating availability data.
"""
import calendar
from datetime import datetime, date, timedelta
from django.utils import timezone


def get_month_calendar_grid(year, month):
    """
    Generate a calendar grid for the specified month.
    
    Returns a list of weeks, where each week is a list of day numbers.
    Days from adjacent months are represented as 0.
    
    Args:
        year (int): The year
        month (int): The month (1-12)
        
    Returns:
        list: List of weeks, each week is a list of day numbers
    """
    cal = calendar.monthcalendar(year, month)
    return cal


def get_month_bounds(year, month):
    """
    Get the start and end datetime for a given month, with buffer for spillover days.
    
    Args:
        year (int): The year
        month (int): The month (1-12)
        
    Returns:
        tuple: (start_datetime, end_datetime) including 1 week before and after
    """
    # Get first and last day of the month
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    
    # Add buffer of 1 week before and after for spillover days
    start_date = first_day - timedelta(days=7)
    end_date = last_day + timedelta(days=7)
    
    # Convert to timezone-aware datetime
    start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    end_datetime = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
    
    return start_datetime, end_datetime


def get_availability_for_day(availability_list, target_date):
    """
    Filter availability items that overlap with a specific date.
    
    Args:
        availability_list: QuerySet or list of ContractorAvailability objects
        target_date: date object to check
        
    Returns:
        list: Availability items that overlap with target_date
    """
    # Convert date to datetime range for the full day
    start_of_day = timezone.make_aware(datetime.combine(target_date, datetime.min.time()))
    end_of_day = timezone.make_aware(datetime.combine(target_date, datetime.max.time()))
    
    # Filter availability that overlaps with this day
    day_availability = []
    for avail in availability_list:
        # Check if availability overlaps with this day
        if avail.start_datetime <= end_of_day and avail.end_datetime >= start_of_day:
            day_availability.append(avail)
    
    return day_availability


def build_calendar_data(year, month, availability_queryset):
    """
    Build a complete calendar data structure with availability information.
    
    Args:
        year (int): The year
        month (int): The month (1-12)
        availability_queryset: QuerySet of ContractorAvailability objects
        
    Returns:
        dict: Calendar data with structure:
            {
                'year': year,
                'month': month,
                'month_name': 'January',
                'weeks': [
                    {
                        'days': [
                            {
                                'day': 1,
                                'date': date(2025, 1, 1),
                                'is_current_month': True,
                                'is_today': False,
                                'availability': [...]
                            },
                            ...
                        ]
                    },
                    ...
                ]
            }
    """
    today = timezone.now().date()
    grid = get_month_calendar_grid(year, month)
    
    # Convert availability queryset to list for efficient filtering
    availability_list = list(availability_queryset)
    
    # Build weeks
    weeks = []
    for week in grid:
        days = []
        for day_num in week:
            if day_num == 0:
                # Day from adjacent month
                days.append({
                    'day': None,
                    'date': None,
                    'is_current_month': False,
                    'is_today': False,
                    'availability': []
                })
            else:
                day_date = date(year, month, day_num)
                day_availability = get_availability_for_day(availability_list, day_date)
                
                days.append({
                    'day': day_num,
                    'date': day_date,
                    'is_current_month': True,
                    'is_today': day_date == today,
                    'availability': day_availability
                })
        
        weeks.append({'days': days})
    
    return {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'weeks': weeks,
    }


def get_prev_month(year, month):
    """Get the previous month's year and month."""
    if month == 1:
        return year - 1, 12
    return year, month - 1


def get_next_month(year, month):
    """Get the next month's year and month."""
    if month == 12:
        return year + 1, 1
    return year, month + 1


def get_availability_display_label(availability):
    """
    Get a display label for an availability entry.
    
    Priority: availability.title → program instance short name → program type short code
    
    Args:
        availability: ContractorAvailability object
        
    Returns:
        str: Display label
    """
    # Check if availability has a notes field that could serve as title
    if hasattr(availability, 'notes') and availability.notes:
        # Use first line of notes as title if it's short
        first_line = availability.notes.split('\n')[0]
        if len(first_line) <= 50:
            return first_line
    
    # Try to get program from related offerings
    if hasattr(availability, 'program_offerings'):
        offerings = availability.program_offerings.all()
        if offerings:
            # Get the first program buildout title
            first_offering = offerings[0]
            if hasattr(first_offering, 'program_buildout'):
                buildout = first_offering.program_buildout
                if hasattr(buildout, 'title'):
                    return buildout.title
                if hasattr(buildout, 'program_type'):
                    return buildout.program_type.name
    
    # Default: show time range
    return f"{availability.start_datetime.strftime('%I:%M %p')}"

