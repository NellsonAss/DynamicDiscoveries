from django.core.management.base import BaseCommand
from decimal import Decimal
from programs.models import ProgramType, ProgramBuildout, Role, Responsibility, BuildoutResponsibilityLine, BuildoutRoleLine


class Command(BaseCommand):
    help = 'Create a sample program buildout to demonstrate the system'

    def handle(self, *args, **options):
        # Create a sample program type
        program_type, created = ProgramType.objects.get_or_create(
            name="STEAM Summer Program",
            defaults={
                "description": "A fun and engaging STEAM program for elementary students with hands-on activities including robotics, coding, and science experiments. Perfect for grades K-5."
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
                "students_per_program": 12,
                "sessions_per_program": 8,
                "rate_per_student": Decimal('100.00'),
                "is_new_program": True,
                "status": "ready"
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

        # Display buildout summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write("BUILDOUT SUMMARY")
        self.stdout.write("="*50)
        self.stdout.write(f"Program: {buildout.program_type.name}")
        self.stdout.write(f"Buildout: {buildout.title}")
        self.stdout.write(f"Facilitators: {buildout.num_facilitators}")
        self.stdout.write(f"Students per program: {buildout.students_per_program}")
        self.stdout.write(f"Sessions per program: {buildout.sessions_per_program}")
        self.stdout.write(f"Rate per student: ${buildout.rate_per_student}")
        self.stdout.write(f"Total Revenue: ${buildout.total_revenue_per_year}")
        self.stdout.write(f"Total Costs: ${buildout.total_yearly_costs}")
        self.stdout.write(f"Expected Profit: ${buildout.expected_profit}")
        self.stdout.write(f"Profit Margin: {buildout.profit_margin:.1f}%")

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully created sample buildout: {buildout.title}'
            )
        ) 