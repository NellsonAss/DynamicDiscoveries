"""
Management command to populate holidays for the next 5 years.

This command creates standard US holidays that will be used by the
availability system when contractors select "except for holidays".
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from programs.models import Holiday
import datetime


class Command(BaseCommand):
    help = 'Populate holidays for the next 5 years'

    def add_arguments(self, parser):
        parser.add_argument(
            '--years',
            type=int,
            default=5,
            help='Number of years to populate holidays for (default: 5)'
        )
        parser.add_argument(
            '--start-year',
            type=int,
            default=None,
            help='Starting year (default: current year)'
        )

    def handle(self, *args, **options):
        years = options['years']
        start_year = options['start_year'] or timezone.now().year
        
        self.stdout.write(f'Populating holidays for {years} years starting from {start_year}...')
        
        created_count = 0
        skipped_count = 0
        
        for year in range(start_year, start_year + years):
            holidays = self.get_holidays_for_year(year)
            
            for holiday_name, holiday_date, is_recurring, description in holidays:
                holiday, created = Holiday.objects.get_or_create(
                    name=holiday_name,
                    date=holiday_date,
                    defaults={
                        'is_recurring': is_recurring,
                        'description': description
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(f'  Created: {holiday}')
                else:
                    skipped_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully populated holidays. Created: {created_count}, Skipped: {skipped_count}'
            )
        )

    def get_holidays_for_year(self, year):
        """Get list of holidays for a specific year."""
        holidays = []
        
        # New Year's Day
        holidays.append((
            "New Year's Day",
            datetime.date(year, 1, 1),
            True,
            "First day of the year"
        ))
        
        # Martin Luther King Jr. Day (3rd Monday in January)
        jan_first = datetime.date(year, 1, 1)
        days_to_monday = (7 - jan_first.weekday()) % 7
        first_monday = jan_first + datetime.timedelta(days=days_to_monday)
        mlk_day = first_monday + datetime.timedelta(days=14)  # 3rd Monday
        holidays.append((
            "Martin Luther King Jr. Day",
            mlk_day,
            True,
            "Federal holiday honoring Martin Luther King Jr."
        ))
        
        # Presidents' Day (3rd Monday in February)
        feb_first = datetime.date(year, 2, 1)
        days_to_monday = (7 - feb_first.weekday()) % 7
        first_monday = feb_first + datetime.timedelta(days=days_to_monday)
        presidents_day = first_monday + datetime.timedelta(days=14)  # 3rd Monday
        holidays.append((
            "Presidents' Day",
            presidents_day,
            True,
            "Federal holiday honoring US Presidents"
        ))
        
        # Memorial Day (last Monday in May)
        may_last = datetime.date(year, 5, 31)
        days_back_to_monday = (may_last.weekday() + 1) % 7
        memorial_day = may_last - datetime.timedelta(days=days_back_to_monday)
        holidays.append((
            "Memorial Day",
            memorial_day,
            True,
            "Federal holiday honoring military personnel who died in service"
        ))
        
        # Independence Day
        holidays.append((
            "Independence Day",
            datetime.date(year, 7, 4),
            True,
            "US Independence Day"
        ))
        
        # Labor Day (1st Monday in September)
        sep_first = datetime.date(year, 9, 1)
        days_to_monday = (7 - sep_first.weekday()) % 7
        labor_day = sep_first + datetime.timedelta(days=days_to_monday)
        holidays.append((
            "Labor Day",
            labor_day,
            True,
            "Federal holiday celebrating workers"
        ))
        
        # Columbus Day (2nd Monday in October)
        oct_first = datetime.date(year, 10, 1)
        days_to_monday = (7 - oct_first.weekday()) % 7
        first_monday = oct_first + datetime.timedelta(days=days_to_monday)
        columbus_day = first_monday + datetime.timedelta(days=7)  # 2nd Monday
        holidays.append((
            "Columbus Day",
            columbus_day,
            True,
            "Federal holiday commemorating Christopher Columbus"
        ))
        
        # Veterans Day
        holidays.append((
            "Veterans Day",
            datetime.date(year, 11, 11),
            True,
            "Federal holiday honoring military veterans"
        ))
        
        # Thanksgiving (4th Thursday in November)
        nov_first = datetime.date(year, 11, 1)
        days_to_thursday = (3 - nov_first.weekday()) % 7
        first_thursday = nov_first + datetime.timedelta(days=days_to_thursday)
        thanksgiving = first_thursday + datetime.timedelta(days=21)  # 4th Thursday
        holidays.append((
            "Thanksgiving Day",
            thanksgiving,
            True,
            "Federal holiday for giving thanks"
        ))
        
        # Black Friday (day after Thanksgiving)
        black_friday = thanksgiving + datetime.timedelta(days=1)
        holidays.append((
            "Black Friday",
            black_friday,
            True,
            "Day after Thanksgiving, often a school holiday"
        ))
        
        # Christmas Eve
        holidays.append((
            "Christmas Eve",
            datetime.date(year, 12, 24),
            True,
            "Day before Christmas"
        ))
        
        # Christmas Day
        holidays.append((
            "Christmas Day",
            datetime.date(year, 12, 25),
            True,
            "Christmas holiday"
        ))
        
        # New Year's Eve
        holidays.append((
            "New Year's Eve",
            datetime.date(year, 12, 31),
            True,
            "Last day of the year"
        ))
        
        return holidays
