from django.core.management.base import BaseCommand
from programs.models import Role, BaseCost
from decimal import Decimal


class Command(BaseCommand):
    help = 'Seed initial roles and base costs for program buildouts'

    def handle(self, *args, **options):
        # Seed data for roles
        SEED_ROLES = [
            {
                "title": "Facilitator",
                "description": "Leads workshops and sessions, manages materials, implements lessons",
                "default_responsibilities": "Session facilitation, lesson preparation, material management, cleanup, parent communication, record keeping"
            },
            {
                "title": "Curriculum Designer", 
                "description": "Creates, adapts, and improves lesson plans and curriculum content",
                "default_responsibilities": "Curriculum development, lesson planning, content creation, assessment design"
            },
            {
                "title": "Admin Support",
                "description": "Coordinates logistics, registration, email communication, and contractor setup",
                "default_responsibilities": "Registration management, logistics coordination, communication, contractor onboarding"
            },
            {
                "title": "Owner Oversight",
                "description": "Provides leadership, quality control, policy management, and process improvement",
                "default_responsibilities": "Leadership, quality control, policy development, contractor management, process improvement"
            },
            {
                "title": "Float Support",
                "description": "Assists facilitators with behavior support, logistics, and material readiness",
                "default_responsibilities": "Behavior support, logistics assistance, material preparation, backup facilitation"
            },
        ]

        # Seed data for base costs
        SEED_BASE_COSTS = [
            {
                "name": "Materials & Supplies",
                "description": "Covers materials like printed handouts, manipulatives, STEM kits, art supplies",
                "rate": Decimal('15.00'),
                "frequency": "PER_WORKSHOP"
            },
            {
                "name": "Location",
                "description": "Site rental or partner facility share for in-person delivery",
                "rate": Decimal('25.00'),
                "frequency": "PER_WORKSHOP"
            },
            {
                "name": "Platform & Insurance",
                "description": "Business infrastructure, web platform, liability coverage",
                "rate": Decimal('10.00'),
                "frequency": "PER_WORKSHOP"
            },
        ]

        # Process roles
        role_created_count = 0
        role_updated_count = 0

        for role_data in SEED_ROLES:
            role, created = Role.objects.get_or_create(
                title=role_data["title"],
                defaults={
                    "description": role_data["description"],
                    "default_responsibilities": role_data["default_responsibilities"]
                }
            )
            
            if created:
                role_created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created role: {role.title}')
                )
            else:
                # Update existing role with new data
                role.description = role_data["description"]
                role.default_responsibilities = role_data["default_responsibilities"]
                role.save()
                role_updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated role: {role.title}')
                )

        # Process base costs
        cost_created_count = 0
        cost_updated_count = 0

        for cost_data in SEED_BASE_COSTS:
            base_cost, created = BaseCost.objects.get_or_create(
                name=cost_data["name"],
                defaults={
                    "description": cost_data["description"],
                    "rate": cost_data["rate"],
                    "frequency": cost_data["frequency"]
                }
            )
            
            if created:
                cost_created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created base cost: {base_cost.name} (${base_cost.rate}/{cost_data["frequency"].lower()})')
                )
            else:
                # Update existing base cost with new data
                base_cost.description = cost_data["description"]
                base_cost.rate = cost_data["rate"]
                base_cost.frequency = cost_data["frequency"]
                base_cost.save()
                cost_updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated base cost: {base_cost.name} (${base_cost.rate}/{cost_data["frequency"].lower()})')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed:\n'
                f'  Roles: {role_created_count} created, {role_updated_count} updated\n'
                f'  Base Costs: {cost_created_count} created, {cost_updated_count} updated'
            )
        ) 