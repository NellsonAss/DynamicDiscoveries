from django.core.management.base import BaseCommand
from decimal import Decimal
from programs.models import ProgramType, ProgramBuildout, Role, ProgramRole


class Command(BaseCommand):
    help = 'Create a sample program buildout to demonstrate the system'

    def handle(self, *args, **options):
        # Create a sample program type
        program_type, created = ProgramType.objects.get_or_create(
            name="STEAM Summer 4-Day",
            defaults={
                "description": "A fun and engaging 4-day STEAM program for elementary students",
                "target_grade_levels": "K-5",
                "rate_per_student": Decimal('400.00')
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created program type: {program_type.name}')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Using existing program type: {program_type.name}')
            )

        # Create a sample buildout
        buildout, created = ProgramBuildout.objects.get_or_create(
            program_type=program_type,
            title="12 Students - 4 Days",
            defaults={
                "expected_students": 12,
                "num_days": 4,
                "sessions_per_day": 1
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created buildout: {buildout.title}')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Using existing buildout: {buildout.title}')
            )

        # Get or create roles
        facilitator = Role.objects.get_or_create(name="Facilitator")[0]
        curriculum_designer = Role.objects.get_or_create(name="Curriculum Designer")[0]
        admin_support = Role.objects.get_or_create(name="Admin Support")[0]
        owner_oversight = Role.objects.get_or_create(name="Owner Oversight")[0]
        float_support = Role.objects.get_or_create(name="Float Support")[0]

        # Define role assignments for the program type
        role_assignments = [
            {
                "role": facilitator,
                "hour_frequency": "PER_SESSION",
                "hour_multiplier": Decimal('4.0'),
                "description": "4 hours per session"
            },
            {
                "role": curriculum_designer,
                "hour_frequency": "PER_PROGRAM",
                "hour_multiplier": Decimal('8.0'),
                "description": "8 hours total for curriculum"
            },
            {
                "role": admin_support,
                "hour_frequency": "PER_PROGRAM",
                "hour_multiplier": Decimal('4.0'),
                "description": "4 hours total for admin"
            },
            {
                "role": owner_oversight,
                "hour_frequency": "PER_PROGRAM",
                "hour_multiplier": Decimal('6.0'),
                "description": "6 hours total for oversight"
            },
            {
                "role": float_support,
                "hour_frequency": "PER_SESSION",
                "hour_multiplier": Decimal('1.0'),
                "description": "1 hour per session"
            },
        ]

        created_count = 0
        for assignment in role_assignments:
            program_role, created = ProgramRole.objects.get_or_create(
                program_type=program_type,
                role=assignment["role"],
                defaults={
                    "hour_frequency": assignment["hour_frequency"],
                    "hour_multiplier": assignment["hour_multiplier"]
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created role assignment: {assignment["role"].name} - {assignment["description"]}'
                    )
                )

        # Display buildout summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write("BUILDOUT SUMMARY")
        self.stdout.write("="*50)
        self.stdout.write(f"Program: {buildout.program_type.name}")
        self.stdout.write(f"Buildout: {buildout.title}")
        self.stdout.write(f"Students: {buildout.expected_students}")
        self.stdout.write(f"Days: {buildout.num_days}")
        self.stdout.write(f"Sessions per day: {buildout.sessions_per_day}")
        self.stdout.write(f"Total Revenue: ${buildout.total_revenue}")
        self.stdout.write(f"Total Payouts: ${buildout.total_payouts}")
        self.stdout.write(f"Profit: ${buildout.profit}")
        self.stdout.write(f"Profit Margin: {buildout.profit_margin:.1f}%")
        
        self.stdout.write("\nROLE BREAKDOWN:")
        self.stdout.write("-" * 30)
        for program_role in buildout.program_type.roles.all():
            hours = program_role.calculate_total_hours(
                buildout.expected_students, 
                buildout.num_days, 
                buildout.sessions_per_day
            )
            payout = program_role.calculate_payout(
                buildout.expected_students, 
                buildout.num_days, 
                buildout.sessions_per_day
            )
            percentage = program_role.calculate_percentage_of_revenue(
                buildout.expected_students, 
                buildout.num_days, 
                buildout.sessions_per_day
            )
            self.stdout.write(
                f"{program_role.role.name}: {percentage:.1f}% "
                f"(${payout:.2f}) - {hours:.1f} hours"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully created {created_count} role assignments'
            )
        ) 