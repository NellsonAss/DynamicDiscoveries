from django.core.management.base import BaseCommand
from programs.models import Role, BaseCost


class Command(BaseCommand):
    help = 'Seed initial roles and base costs for program buildouts'

    def handle(self, *args, **options):
        # Seed data for roles with hourly rates
        SEED_ROLES = [
            {
                "name": "Facilitator",
                "hourly_rate": 25.00,
                "responsibilities": "Run sessions, manage materials, implement lessons, prepare/clean up, provide feedback, engage with parents, update records."
            },
            {
                "name": "Curriculum Designer",
                "hourly_rate": 35.00,
                "responsibilities": "Create, adapt, and improve lesson plans and curriculum content."
            },
            {
                "name": "Admin Support",
                "hourly_rate": 20.00,
                "responsibilities": "Coordinate logistics, registration, email communication, and contractor setup."
            },
            {
                "name": "Owner Oversight",
                "hourly_rate": 40.00,
                "responsibilities": "Leadership, quality control, policy, contractor management, process improvement."
            },
            {
                "name": "Float Support",
                "hourly_rate": 18.00,
                "responsibilities": "Assist facilitators with behavior support, logistics, and material readiness."
            },
        ]

        # Seed data for base costs
        SEED_BASE_COSTS = [
            {
                "name": "Materials & Supplies",
                "cost_per_student": 15.00,
                "description": "Covers materials like printed handouts, manipulatives, STEM kits, art supplies."
            },
            {
                "name": "Location",
                "cost_per_student": 25.00,
                "description": "Site rental or partner facility share for in-person delivery."
            },
            {
                "name": "Platform & Insurance",
                "cost_per_student": 10.00,
                "description": "Business infrastructure, web platform, liability coverage."
            },
        ]

        # Process roles
        role_created_count = 0
        role_updated_count = 0

        for role_data in SEED_ROLES:
            role, created = Role.objects.get_or_create(
                name=role_data["name"],
                defaults={
                    "hourly_rate": role_data["hourly_rate"],
                    "responsibilities": role_data["responsibilities"]
                }
            )
            
            if created:
                role_created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created role: {role.name} (${role.hourly_rate}/hr)')
                )
            else:
                # Update existing role with new data
                role.hourly_rate = role_data["hourly_rate"]
                role.responsibilities = role_data["responsibilities"]
                role.save()
                role_updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated role: {role.name} (${role.hourly_rate}/hr)')
                )

        # Process base costs
        cost_created_count = 0
        cost_updated_count = 0

        for cost_data in SEED_BASE_COSTS:
            base_cost, created = BaseCost.objects.get_or_create(
                name=cost_data["name"],
                defaults={
                    "cost_per_student": cost_data["cost_per_student"],
                    "description": cost_data["description"]
                }
            )
            
            if created:
                cost_created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created base cost: {base_cost.name} (${base_cost.cost_per_student}/student)')
                )
            else:
                # Update existing base cost with new data
                base_cost.cost_per_student = cost_data["cost_per_student"]
                base_cost.description = cost_data["description"]
                base_cost.save()
                cost_updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated base cost: {base_cost.name} (${base_cost.cost_per_student}/student)')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed:\n'
                f'  Roles: {role_created_count} created, {role_updated_count} updated\n'
                f'  Base Costs: {cost_created_count} created, {cost_updated_count} updated'
            )
        ) 