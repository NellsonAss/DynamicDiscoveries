from django.core.management.base import BaseCommand
from decimal import Decimal
from programs.models import ProgramType, ProgramBuildout, Role, BuildoutResponsibility, BuildoutRoleAssignment


class Command(BaseCommand):
    help = 'Create a sample program buildout to demonstrate the system'

    def handle(self, *args, **options):
        # Create a sample program type
        program_type, created = ProgramType.objects.get_or_create(
            name="STEAM Summer Program",
            defaults={
                "description": "A fun and engaging STEAM program for elementary students",
                "scope": "Hands-on STEAM activities including robotics, coding, and science experiments",
                "target_grade_levels": "K-5",
                "rate_per_student": Decimal('100.00'),
                "default_num_facilitators": 2,
                "default_num_new_facilitators": 1,
                "default_workshops_per_facilitator_per_year": 4,
                "default_students_per_workshop": 12,
                "default_sessions_per_workshop": 8,
                "default_new_workshop_concepts_per_year": 1
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
            title="Standard STEAM Buildout",
            defaults={
                "num_facilitators": 2,
                "num_new_facilitators": 1,
                "workshops_per_facilitator_per_year": 4,
                "students_per_workshop": 12,
                "sessions_per_workshop": 8,
                "new_workshop_concepts_per_year": 1
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
        facilitator = Role.objects.get_or_create(
            name="Facilitator",
            defaults={"hourly_rate": Decimal('25.00'), "description": "Leads workshops and sessions"}
        )[0]
        curriculum_designer = Role.objects.get_or_create(
            name="Curriculum Designer",
            defaults={"hourly_rate": Decimal('30.00'), "description": "Designs curriculum and workshop concepts"}
        )[0]
        admin_support = Role.objects.get_or_create(
            name="Admin Support",
            defaults={"hourly_rate": Decimal('20.00'), "description": "Handles administrative tasks"}
        )[0]

        # Create responsibilities
        responsibilities = [
            {
                "role": facilitator,
                "name": "Session Facilitation",
                "frequency": "PER_SESSION",
                "base_hours": Decimal('2.0'),
                "description": "Facilitate each workshop session"
            },
            {
                "role": facilitator,
                "name": "New Facilitator Training",
                "frequency": "PER_NEW_FACILITATOR",
                "base_hours": Decimal('8.0'),
                "description": "Train new facilitators"
            },
            {
                "role": curriculum_designer,
                "name": "Program Concept Development",
                "frequency": "PER_PROGRAM_CONCEPT",
                "base_hours": Decimal('10.0'),
                "description": "Develop new workshop concepts"
            },
            {
                "role": curriculum_designer,
                "name": "Curriculum Planning",
                "frequency": "PER_WORKSHOP",
                "base_hours": Decimal('4.0'),
                "description": "Plan curriculum for each workshop"
            },
            {
                "role": admin_support,
                "name": "Administrative Support",
                "frequency": "PER_YEAR",
                "base_hours": Decimal('40.0'),
                "description": "Annual administrative support"
            },
        ]

        created_count = 0
        for resp in responsibilities:
            responsibility, created = BuildoutResponsibility.objects.get_or_create(
                buildout=buildout,
                role=resp["role"],
                name=resp["name"],
                defaults={
                    "frequency": resp["frequency"],
                    "base_hours": resp["base_hours"],
                    "description": resp["description"]
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created responsibility: {resp["role"].name} - {resp["name"]}'
                    )
                )

        # Create role assignments with revenue percentages
        role_assignments = [
            {
                "role": facilitator,
                "percent_of_revenue": Decimal('60.00')
            },
            {
                "role": curriculum_designer,
                "percent_of_revenue": Decimal('25.00')
            },
            {
                "role": admin_support,
                "percent_of_revenue": Decimal('15.00')
            },
        ]

        for assignment in role_assignments:
            role_assignment, created = BuildoutRoleAssignment.objects.get_or_create(
                buildout=buildout,
                role=assignment["role"],
                defaults={
                    "percent_of_revenue": assignment["percent_of_revenue"]
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created role assignment: {assignment["role"].name} - {assignment["percent_of_revenue"]}%'
                    )
                )

        # Display buildout summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write("BUILDOUT SUMMARY")
        self.stdout.write("="*50)
        self.stdout.write(f"Program: {buildout.program_type.name}")
        self.stdout.write(f"Buildout: {buildout.title}")
        self.stdout.write(f"Facilitators: {buildout.num_facilitators}")
        self.stdout.write(f"Workshops per year: {buildout.num_workshops_per_year}")
        self.stdout.write(f"Students per year: {buildout.total_students_per_year}")
        self.stdout.write(f"Sessions per year: {buildout.total_sessions_per_year}")
        self.stdout.write(f"Total Revenue: ${buildout.total_revenue_per_year}")
        self.stdout.write(f"Total Costs: ${buildout.total_yearly_costs}")
        self.stdout.write(f"Profit: ${buildout.yearly_profit}")
        self.stdout.write(f"Profit Margin: {buildout.profit_margin:.1f}%")
        
        self.stdout.write("\nROLE BREAKDOWN:")
        self.stdout.write("-" * 30)
        for role_assignment in buildout.role_assignments.all():
            hours = role_assignment.calculate_yearly_hours()
            cost = role_assignment.calculate_yearly_cost()
            percentage = role_assignment.calculate_percent_of_revenue()
            self.stdout.write(
                f"{role_assignment.role.name}: {percentage:.1f}% "
                f"(${cost:.2f}) - {hours:.1f} hours"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully created {created_count} responsibilities'
            )
        ) 