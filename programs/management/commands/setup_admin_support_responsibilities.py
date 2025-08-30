from django.core.management.base import BaseCommand
from programs.models import Role, Responsibility, ResponsibilityFrequency
from decimal import Decimal


class Command(BaseCommand):
    help = 'Setup responsibilities for Admin Support role based on typical administrative tasks'

    def handle(self, *args, **options):
        # Get or create Admin Support role
        role, created = Role.objects.get_or_create(
            title="Admin Support",
            defaults={
                "description": "Coordinates logistics, registration, email communication, and contractor setup",
                "default_responsibilities": "Registration management, logistics coordination, communication, contractor onboarding"
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created role: {role.title}')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Role already exists: {role.title}')
            )

        # Admin Support responsibilities based on typical administrative tasks
        ADMIN_SUPPORT_RESPONSIBILITIES = [
            {
                "name": "Registration Management",
                "description": "Manage student registrations, process applications, and maintain enrollment records",
                "frequency": "PER_WORKSHOP",
                "hours": Decimal("2.00")
            },
            {
                "name": "Email Communication",
                "description": "Send confirmation emails, reminders, and respond to parent inquiries",
                "frequency": "PER_WORKSHOP",
                "hours": Decimal("1.50")
            },
            {
                "name": "Contractor Onboarding",
                "description": "Process new contractor paperwork, set up accounts, and provide initial training",
                "frequency": "PER_NEW_FACILITATOR",
                "hours": Decimal("4.00")
            },
            {
                "name": "Logistics Coordination",
                "description": "Coordinate venue bookings, material delivery, and equipment setup",
                "frequency": "PER_WORKSHOP",
                "hours": Decimal("1.00")
            },
            {
                "name": "Financial Record Keeping",
                "description": "Track payments, process refunds, and maintain financial records",
                "frequency": "PER_WORKSHOP",
                "hours": Decimal("1.50")
            },
            {
                "name": "Parent Communication",
                "description": "Handle parent concerns, provide program information, and manage feedback",
                "frequency": "PER_WORKSHOP",
                "hours": Decimal("1.00")
            },
            {
                "name": "Data Entry and Reporting",
                "description": "Enter attendance data, generate reports, and maintain program statistics",
                "frequency": "PER_WORKSHOP",
                "hours": Decimal("0.75")
            },
            {
                "name": "Website and Social Media",
                "description": "Update program information, post announcements, and manage online presence",
                "frequency": "PER_WORKSHOP_CONCEPT",
                "hours": Decimal("3.00")
            },
            {
                "name": "Insurance and Compliance",
                "description": "Ensure proper insurance coverage, maintain compliance records, and handle permits",
                "frequency": "PER_WORKSHOP_CONCEPT",
                "hours": Decimal("2.00")
            },
            {
                "name": "Emergency Response",
                "description": "Handle emergency situations, contact parents, and coordinate with emergency services",
                "frequency": "PER_WORKSHOP",
                "hours": Decimal("0.25")
            },
            {
                "name": "Inventory Management",
                "description": "Track supplies, order materials, and maintain equipment inventory",
                "frequency": "PER_WORKSHOP",
                "hours": Decimal("0.50")
            },
            {
                "name": "Staff Scheduling",
                "description": "Coordinate facilitator schedules, handle substitutions, and manage availability",
                "frequency": "PER_WORKSHOP",
                "hours": Decimal("1.00")
            },
            {
                "name": "Quality Assurance",
                "description": "Monitor program quality, collect feedback, and implement improvements",
                "frequency": "PER_WORKSHOP",
                "hours": Decimal("0.75")
            },
            {
                "name": "Documentation",
                "description": "Maintain program documentation, update procedures, and create training materials",
                "frequency": "PER_WORKSHOP_CONCEPT",
                "hours": Decimal("2.50")
            },
            {
                "name": "Customer Service",
                "description": "Provide excellent customer service, handle complaints, and ensure satisfaction",
                "frequency": "PER_WORKSHOP",
                "hours": Decimal("1.00")
            }
        ]

        # Process responsibilities
        responsibility_created_count = 0
        responsibility_updated_count = 0

        for resp_data in ADMIN_SUPPORT_RESPONSIBILITIES:
            responsibility, created = Responsibility.objects.get_or_create(
                role=role,
                name=resp_data["name"],
                defaults={
                    "description": resp_data["description"],
                    "frequency_type": resp_data["frequency"],
                    "default_hours": resp_data["hours"]
                }
            )
            
            if created:
                responsibility_created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  Created responsibility: {responsibility.name} ({responsibility.default_hours}h/{responsibility.frequency_type})')
                )
            else:
                # Update existing responsibility
                responsibility.description = resp_data["description"]
                responsibility.frequency_type = resp_data["frequency"]
                responsibility.default_hours = resp_data["hours"]
                responsibility.save()
                responsibility_updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'  Updated responsibility: {responsibility.name} ({responsibility.default_hours}h/{responsibility.frequency_type})')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed Admin Support responsibilities:\n'
                f'  Responsibilities: {responsibility_created_count} created, {responsibility_updated_count} updated\n'
                f'  Total responsibilities for {role.title}: {role.responsibilities.count()}'
            )
        )
