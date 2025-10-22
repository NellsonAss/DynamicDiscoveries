"""
Management command to migrate legacy ContractorAvailability entries to AvailabilityRule system.

Usage:
    python manage.py migrate_legacy_availability --dry-run  # Preview without changes
    python manage.py migrate_legacy_availability            # Actually migrate
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta
from collections import defaultdict
from programs.models import ContractorAvailability, AvailabilityRule
import json


class Command(BaseCommand):
    help = 'Migrate legacy per-day ContractorAvailability entries to rule-based AvailabilityRule system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview migration without making changes',
        )
        parser.add_argument(
            '--contractor',
            type=str,
            help='Migrate only for specific contractor (email address)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        contractor_email = options.get('contractor')
        
        self.stdout.write(self.style.WARNING(
            '=' * 70
        ))
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        else:
            self.stdout.write(self.style.WARNING('MIGRATION MODE - Changes will be saved'))
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write('')
        
        # Get legacy entries (not already migrated)
        legacy_entries = ContractorAvailability.objects.filter(legacy=False)
        if contractor_email:
            legacy_entries = legacy_entries.filter(contractor__email=contractor_email)
        
        if not legacy_entries.exists():
            self.stdout.write(self.style.SUCCESS('No legacy entries found to migrate.'))
            return
        
        self.stdout.write(f'Found {legacy_entries.count()} legacy entries to analyze.')
        self.stdout.write('')
        
        # Group by contractor
        contractors = legacy_entries.values_list('contractor', flat=True).distinct()
        
        total_rules_created = 0
        total_entries_migrated = 0
        migration_log = []
        
        for contractor_id in contractors:
            contractor_entries = legacy_entries.filter(contractor_id=contractor_id).order_by('start_datetime')
            contractor = contractor_entries.first().contractor
            
            self.stdout.write(self.style.HTTP_INFO(f'\nAnalyzing contractor: {contractor.get_full_name()} ({contractor.email})'))
            self.stdout.write(f'  {contractor_entries.count()} entries to process')
            
            # Analyze patterns
            rules, entry_mapping = self._analyze_and_create_rules(contractor, contractor_entries)
            
            self.stdout.write(f'  Detected {len(rules)} potential rules:')
            for rule_data in rules:
                self.stdout.write(f'    - {rule_data["title"]}: {rule_data["kind"]}')
                self.stdout.write(f'      Dates: {rule_data["date_start"]} to {rule_data["date_end"]}')
                self.stdout.write(f'      Time: {rule_data["start_time"]} - {rule_data["end_time"]}')
                if rule_data["kind"] == "WEEKLY_RECURRING":
                    weekdays = []
                    if rule_data["weekdays_monday"]: weekdays.append("Mon")
                    if rule_data["weekdays_tuesday"]: weekdays.append("Tue")
                    if rule_data["weekdays_wednesday"]: weekdays.append("Wed")
                    if rule_data["weekdays_thursday"]: weekdays.append("Thu")
                    if rule_data["weekdays_friday"]: weekdays.append("Fri")
                    if rule_data["weekdays_saturday"]: weekdays.append("Sat")
                    if rule_data["weekdays_sunday"]: weekdays.append("Sun")
                    self.stdout.write(f'      Weekdays: {", ".join(weekdays)}')
                self.stdout.write(f'      Covers {len(rule_data["entry_ids"])} legacy entries')
            
            if not dry_run:
                # Actually create the rules
                with transaction.atomic():
                    for rule_data in rules:
                        entry_ids = rule_data.pop('entry_ids')
                        
                        # Create the rule
                        rule = AvailabilityRule.objects.create(**rule_data)
                        total_rules_created += 1
                        
                        # Mark legacy entries
                        ContractorAvailability.objects.filter(id__in=entry_ids).update(legacy=True)
                        total_entries_migrated += len(entry_ids)
                        
                        # Log mapping
                        migration_log.append({
                            'rule_id': rule.id,
                            'contractor_email': contractor.email,
                            'legacy_entry_ids': entry_ids,
                        })
                
                self.stdout.write(self.style.SUCCESS(f'  Created {len(rules)} rules for {contractor.get_full_name()}'))
        
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('=' * 70))
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN COMPLETE - No changes made'))
            self.stdout.write(f'Would create: {sum(len(r["entry_ids"]) for rules in [self._analyze_and_create_rules(c.contractor, c)[0] for c in [ContractorAvailability.objects.filter(contractor_id=cid, legacy=False) for cid in contractors]])} rules')
        else:
            self.stdout.write(self.style.SUCCESS('MIGRATION COMPLETE'))
            self.stdout.write(f'Created {total_rules_created} rules')
            self.stdout.write(f'Migrated {total_entries_migrated} legacy entries')
            self.stdout.write(f'Migration log: {len(migration_log)} entries')
        self.stdout.write(self.style.WARNING('=' * 70))

    def _analyze_and_create_rules(self, contractor, entries):
        """Analyze entries and generate rule definitions."""
        rules = []
        entry_mapping = {}
        processed_entry_ids = set()
        
        # Try to detect weekly recurring patterns
        weekly_patterns = self._detect_weekly_patterns(entries)
        for pattern in weekly_patterns:
            if pattern['confidence'] > 0.7:  # High confidence threshold
                rules.append(pattern)
                for entry_id in pattern['entry_ids']:
                    processed_entry_ids.add(entry_id)
        
        # Try to detect date range patterns (consecutive days)
        remaining_entries = entries.exclude(id__in=processed_entry_ids).order_by('start_datetime')
        date_range_patterns = self._detect_date_range_patterns(remaining_entries)
        for pattern in date_range_patterns:
            rules.append(pattern)
            for entry_id in pattern['entry_ids']:
                processed_entry_ids.add(entry_id)
        
        # For remaining entries, create one-day date range rules
        remaining_entries = entries.exclude(id__in=processed_entry_ids)
        for entry in remaining_entries:
            rules.append({
                'contractor': contractor,
                'title': f"Single day: {entry.start_datetime.date()}",
                'kind': 'DATE_RANGE',
                'start_time': entry.start_datetime.time(),
                'end_time': entry.end_datetime.time(),
                'date_start': entry.start_datetime.date(),
                'date_end': entry.start_datetime.date(),
                'weekdays_monday': False,
                'weekdays_tuesday': False,
                'weekdays_wednesday': False,
                'weekdays_thursday': False,
                'weekdays_friday': False,
                'weekdays_saturday': False,
                'weekdays_sunday': False,
                'timezone': 'America/New_York',  # Default
                'is_active': entry.is_active,
                'notes': f'Migrated from legacy entry #{entry.id}',
                'entry_ids': [entry.id],
            })
        
        return rules, entry_mapping

    def _detect_weekly_patterns(self, entries):
        """Detect weekly recurring patterns."""
        patterns = []
        
        # Group by time window
        by_time = defaultdict(list)
        for entry in entries:
            time_key = (entry.start_datetime.time(), entry.end_datetime.time())
            by_time[time_key].append(entry)
        
        for (start_time, end_time), time_entries in by_time.items():
            if len(time_entries) < 3:  # Need at least 3 occurrences
                continue
            
            # Group by weekday
            by_weekday = defaultdict(list)
            for entry in time_entries:
                weekday = entry.start_datetime.weekday()
                by_weekday[weekday].append(entry)
            
            # Check if we have consistent weekday pattern
            active_weekdays = [wd for wd, entries_list in by_weekday.items() if len(entries_list) >= 2]
            if not active_weekdays:
                continue
            
            # Calculate date range
            all_dates = sorted([e.start_datetime.date() for e in time_entries])
            date_start = all_dates[0]
            date_end = all_dates[-1]
            
            # Calculate confidence (percentage of expected occurrences present)
            expected_occurrences = 0
            current_date = date_start
            while current_date <= date_end:
                if current_date.weekday() in active_weekdays:
                    expected_occurrences += 1
                current_date += timedelta(days=1)
            
            actual_occurrences = len(time_entries)
            confidence = actual_occurrences / expected_occurrences if expected_occurrences > 0 else 0
            
            weekdays_display = []
            if 0 in active_weekdays: weekdays_display.append("Mon")
            if 1 in active_weekdays: weekdays_display.append("Tue")
            if 2 in active_weekdays: weekdays_display.append("Wed")
            if 3 in active_weekdays: weekdays_display.append("Thu")
            if 4 in active_weekdays: weekdays_display.append("Fri")
            if 5 in active_weekdays: weekdays_display.append("Sat")
            if 6 in active_weekdays: weekdays_display.append("Sun")
            
            patterns.append({
                'contractor': time_entries[0].contractor,
                'title': f"{', '.join(weekdays_display)} {start_time.strftime('%I:%M%p')}",
                'kind': 'WEEKLY_RECURRING',
                'start_time': start_time,
                'end_time': end_time,
                'date_start': date_start,
                'date_end': date_end,
                'weekdays_monday': 0 in active_weekdays,
                'weekdays_tuesday': 1 in active_weekdays,
                'weekdays_wednesday': 2 in active_weekdays,
                'weekdays_thursday': 3 in active_weekdays,
                'weekdays_friday': 4 in active_weekdays,
                'weekdays_saturday': 5 in active_weekdays,
                'weekdays_sunday': 6 in active_weekdays,
                'timezone': 'America/New_York',
                'is_active': True,
                'notes': f'Migrated from {actual_occurrences} legacy entries (confidence: {confidence:.1%})',
                'entry_ids': [e.id for e in time_entries],
                'confidence': confidence,
            })
        
        return patterns

    def _detect_date_range_patterns(self, entries):
        """Detect consecutive day patterns with same time."""
        patterns = []
        
        # Group by time window
        by_time = defaultdict(list)
        for entry in entries:
            time_key = (entry.start_datetime.time(), entry.end_datetime.time())
            by_time[time_key].append(entry)
        
        for (start_time, end_time), time_entries in by_time.items():
            # Sort by date
            sorted_entries = sorted(time_entries, key=lambda e: e.start_datetime.date())
            
            # Find consecutive sequences
            sequences = []
            current_seq = [sorted_entries[0]]
            
            for i in range(1, len(sorted_entries)):
                prev_date = sorted_entries[i-1].start_datetime.date()
                curr_date = sorted_entries[i].start_datetime.date()
                
                if (curr_date - prev_date).days == 1:
                    # Consecutive
                    current_seq.append(sorted_entries[i])
                else:
                    # Not consecutive, start new sequence
                    if len(current_seq) >= 2:  # At least 2 consecutive days
                        sequences.append(current_seq)
                    current_seq = [sorted_entries[i]]
            
            # Don't forget the last sequence
            if len(current_seq) >= 2:
                sequences.append(current_seq)
            
            # Create rules for sequences
            for seq in sequences:
                date_start = seq[0].start_datetime.date()
                date_end = seq[-1].start_datetime.date()
                
                patterns.append({
                    'contractor': seq[0].contractor,
                    'title': f"Daily {date_start} to {date_end}",
                    'kind': 'DATE_RANGE',
                    'start_time': start_time,
                    'end_time': end_time,
                    'date_start': date_start,
                    'date_end': date_end,
                    'weekdays_monday': False,
                    'weekdays_tuesday': False,
                    'weekdays_wednesday': False,
                    'weekdays_thursday': False,
                    'weekdays_friday': False,
                    'weekdays_saturday': False,
                    'weekdays_sunday': False,
                    'timezone': 'America/New_York',
                    'is_active': True,
                    'notes': f'Migrated from {len(seq)} consecutive legacy entries',
                    'entry_ids': [e.id for e in seq],
                })
        
        return patterns

