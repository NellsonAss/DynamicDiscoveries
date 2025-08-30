from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from communications.models import Contact


class Command(BaseCommand):
    help = 'Seed sample contact form submissions for testing'

    def handle(self, *args, **options):
        self.stdout.write('Seeding contact form submissions...')

        # Sample contact submissions
        contacts_data = [
            {
                'parent_name': 'Sarah Johnson',
                'email': 'sarah.johnson@email.com',
                'phone': '(555) 234-5678',
                'interest': 'after_school',
                'message': 'Hi! I\'m interested in after-school enrichment programs for my 8-year-old daughter. She loves science and art. Do you have any programs starting soon?',
                'status': 'new',
                'created_at': timezone.now() - timedelta(days=2)
            },
            {
                'parent_name': 'Michael Chen',
                'email': 'michael.chen@email.com',
                'phone': '(555) 345-6789',
                'interest': 'small_group',
                'message': 'Looking for small group tutoring for my son who is struggling with reading. He\'s in 2nd grade. What options do you have?',
                'status': 'in_progress',
                'created_at': timezone.now() - timedelta(days=5)
            },
            {
                'parent_name': 'Emily Rodriguez',
                'email': 'emily.rodriguez@email.com',
                'phone': '(555) 456-7890',
                'interest': 'programs',
                'message': 'I heard about your signature programs from a friend. My twins are 6 and would love to participate in something creative and educational.',
                'status': 'contacted',
                'created_at': timezone.now() - timedelta(days=1)
            },
            {
                'parent_name': 'David Thompson',
                'email': 'david.thompson@email.com',
                'phone': '(555) 567-8901',
                'interest': 'assessments',
                'message': 'I\'m interested in educational assessments for my daughter. She seems to be ahead in some areas and I want to understand her learning needs better.',
                'status': 'completed',
                'created_at': timezone.now() - timedelta(days=10)
            },
            {
                'parent_name': 'Lisa Wang',
                'email': 'lisa.wang@email.com',
                'phone': '(555) 678-9012',
                'interest': 'other',
                'message': 'I\'m looking for summer programs for my 10-year-old son. He\'s very interested in technology and coding. Do you offer any STEM-focused summer camps?',
                'status': 'new',
                'created_at': timezone.now() - timedelta(hours=6)
            }
        ]

        created_count = 0
        for contact_data in contacts_data:
            contact, created = Contact.objects.get_or_create(
                email=contact_data['email'],
                parent_name=contact_data['parent_name'],
                defaults=contact_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created contact: {contact.parent_name} - {contact.interest}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠ Contact already exists: {contact.parent_name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\n🎉 Successfully created {created_count} contact submissions!')
        )
        self.stdout.write(f'\nYou can view these contacts at: /communications/contacts/') 