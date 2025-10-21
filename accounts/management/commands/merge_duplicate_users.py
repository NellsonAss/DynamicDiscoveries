from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from collections import defaultdict


class Command(BaseCommand):
    help = 'Merge duplicate user accounts with case-insensitive email matching'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Only process duplicates for this specific email (case-insensitive)',
        )

    def handle(self, *args, **options):
        User = get_user_model()
        dry_run = options['dry_run']
        specific_email = options['email']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        # Find all users and group by lowercase email
        email_groups = defaultdict(list)
        for user in User.objects.all().order_by('id'):
            email_lower = user.email.lower()
            
            # If specific email provided, only process that one
            if specific_email and email_lower != specific_email.lower():
                continue
                
            email_groups[email_lower].append(user)

        # Process duplicates
        duplicates_found = 0
        for email_lower, users in email_groups.items():
            if len(users) > 1:
                duplicates_found += 1
                self.merge_duplicate_users(users, dry_run)

        if duplicates_found == 0:
            self.stdout.write(self.style.SUCCESS('No duplicate users found.'))
        else:
            action = "Would merge" if dry_run else "Merged"
            self.stdout.write(
                self.style.SUCCESS(f'{action} {duplicates_found} sets of duplicate users.')
            )

    def merge_duplicate_users(self, users, dry_run=False):
        """Merge a list of duplicate users into the primary (oldest) user."""
        # Sort by ID to get the oldest user first
        users.sort(key=lambda u: u.id)
        primary_user = users[0]
        duplicate_users = users[1:]

        self.stdout.write(f'\nMerging duplicates for: {primary_user.email.lower()}')
        self.stdout.write(f'  Primary user (keeping): ID {primary_user.id} - "{primary_user.email}"')
        
        # Collect all roles from all users
        all_groups = set(primary_user.groups.all())
        for dup_user in duplicate_users:
            self.stdout.write(f'  Duplicate user: ID {dup_user.id} - "{dup_user.email}" - Roles: {[g.name for g in dup_user.groups.all()]}')
            all_groups.update(dup_user.groups.all())

        if not dry_run:
            with transaction.atomic():
                # Add all groups to primary user
                for group in all_groups:
                    primary_user.groups.add(group)

                # Transfer related objects to primary user
                self.transfer_related_objects(primary_user, duplicate_users)

                # Delete duplicate users
                for dup_user in duplicate_users:
                    self.stdout.write(f'    Deleting duplicate user ID {dup_user.id}')
                    dup_user.delete()

                self.stdout.write(f'  ✅ Merged into primary user ID {primary_user.id}')
                self.stdout.write(f'     Final roles: {[g.name for g in primary_user.groups.all()]}')
        else:
            self.stdout.write(f'  Would merge all roles: {[g.name for g in all_groups]}')
            for dup_user in duplicate_users:
                self.stdout.write(f'    Would delete duplicate user ID {dup_user.id}')

    def transfer_related_objects(self, primary_user, duplicate_users):
        """Transfer related objects from duplicate users to primary user."""
        # This method can be extended to handle specific related objects
        # For now, we'll handle the most common ones
        
        for dup_user in duplicate_users:
            # Transfer Profile if it exists and primary doesn't have one
            if hasattr(dup_user, 'profile') and not hasattr(primary_user, 'profile'):
                profile = dup_user.profile
                profile.user = primary_user
                profile.save()
                self.stdout.write(f'    Transferred profile from user {dup_user.id}')

            # Add more related object transfers here as needed
            # Example:
            # - Notes, comments, or other user-generated content
            # - Relationships with children, programs, etc.
            
        self.stdout.write(f'    Related objects transferred to user {primary_user.id}')
