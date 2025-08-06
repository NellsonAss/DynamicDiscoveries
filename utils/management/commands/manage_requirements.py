"""
Django management command for managing project requirements.

Usage:
    python manage.py manage_requirements --list
    python manage.py manage_requirements --add REQ-003 "Feature Title" "Description"
    python manage.py manage_requirements --update REQ-003 implemented
    python manage.py manage_requirements --validate
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.requirements_tracker import RequirementsTracker


class Command(BaseCommand):
    help = 'Manage project requirements tracking'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all requirements',
        )
        parser.add_argument(
            '--add',
            nargs=3,
            metavar=('ID', 'TITLE', 'DESCRIPTION'),
            help='Add a new requirement (ID TITLE DESCRIPTION)',
        )
        parser.add_argument(
            '--update',
            nargs=2,
            metavar=('ID', 'STATUS'),
            help='Update requirement status (ID STATUS)',
        )
        parser.add_argument(
            '--validate',
            action='store_true',
            help='Validate that all requirements are implemented',
        )

    def handle(self, *args, **options):
        tracker = RequirementsTracker()

        if options['list']:
            self.list_requirements(tracker)
        elif options['add']:
            self.add_requirement(tracker, options['add'])
        elif options['update']:
            self.update_requirement(tracker, options['update'])
        elif options['validate']:
            self.validate_requirements(tracker)
        else:
            self.stdout.write(
                self.style.ERROR('Please specify an action: --list, --add, --update, or --validate')
            )

    def list_requirements(self, tracker):
        """List all requirements."""
        requirements = tracker.get_all_requirements()
        
        if not requirements:
            self.stdout.write(self.style.WARNING('No requirements found.'))
            return

        self.stdout.write(self.style.SUCCESS(f'Found {len(requirements)} requirements:'))
        self.stdout.write('')
        
        for req in requirements:
            status_color = self.style.SUCCESS if req['status'] == 'implemented' else self.style.WARNING
            self.stdout.write(f"  {req['id']}: {req['title']}")
            self.stdout.write(f"    Status: {status_color(req['status'])}")
            self.stdout.write(f"    Description: {req['description']}")
            self.stdout.write('')

    def add_requirement(self, tracker, args):
        """Add a new requirement."""
        req_id, title, description = args
        
        try:
            req = tracker.add_requirement(req_id, title, description, 'required')
            self.stdout.write(
                self.style.SUCCESS(f'Successfully added requirement {req_id}: {title}')
            )
        except ValueError as e:
            raise CommandError(f'Error adding requirement: {e}')

    def update_requirement(self, tracker, args):
        """Update requirement status."""
        req_id, status = args
        
        try:
            req = tracker.update_requirement_status(req_id, status)
            self.stdout.write(
                self.style.SUCCESS(f'Successfully updated {req_id} status to: {status}')
            )
        except ValueError as e:
            raise CommandError(f'Error updating requirement: {e}')

    def validate_requirements(self, tracker):
        """Validate that all requirements are implemented."""
        try:
            if tracker.validate_all_implemented():
                self.stdout.write(
                    self.style.SUCCESS('All requirements are implemented! ✅')
                )
            else:
                requirements = tracker.get_requirements_by_status('required')
                self.stdout.write(
                    self.style.ERROR(f'❌ {len(requirements)} requirements are not implemented:')
                )
                for req in requirements:
                    self.stdout.write(f"  - {req['id']}: {req['title']}")
        except Exception as e:
            raise CommandError(f'Error validating requirements: {e}') 