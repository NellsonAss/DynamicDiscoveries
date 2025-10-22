"""
Management command to clear all availability data for a specific contractor.
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from programs.models import ContractorAvailability, AvailabilityRule

User = get_user_model()


class Command(BaseCommand):
    help = 'Clear all availability data for a specific contractor by email'

    def add_arguments(self, parser):
        parser.add_argument(
            'email',
            type=str,
            help='Email address of the contractor'
        )

    def handle(self, *args, **options):
        email = options['email']
        
        try:
            contractor = User.objects.get(email=email)
        except User.DoesNotExist:
            raise CommandError(f'User with email "{email}" does not exist')
        
        # Count existing availability data
        availability_count = ContractorAvailability.objects.filter(contractor=contractor).count()
        rules_count = AvailabilityRule.objects.filter(contractor=contractor).count()
        
        if availability_count == 0 and rules_count == 0:
            self.stdout.write(
                self.style.WARNING(f'No availability data found for {email}')
            )
            return
        
        # Delete ContractorAvailability records
        if availability_count > 0:
            ContractorAvailability.objects.filter(contractor=contractor).delete()
            self.stdout.write(
                self.style.SUCCESS(f'✓ Deleted {availability_count} ContractorAvailability record(s)')
            )
        
        # Delete AvailabilityRule records (exceptions will cascade)
        if rules_count > 0:
            AvailabilityRule.objects.filter(contractor=contractor).delete()
            self.stdout.write(
                self.style.SUCCESS(f'✓ Deleted {rules_count} AvailabilityRule record(s)')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✓ All availability data cleared for {email}')
        )

