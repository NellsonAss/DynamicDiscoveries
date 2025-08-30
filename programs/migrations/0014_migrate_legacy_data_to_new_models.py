# Generated manually for data migration

from django.db import migrations
from decimal import Decimal

def migrate_legacy_data_to_new_models(apps, schema_editor):
    """Migrate data from legacy models to new models."""
    User = apps.get_model('accounts', 'User')
    ProgramBuildout = apps.get_model('programs', 'ProgramBuildout')
    BuildoutRoleLine = apps.get_model('programs', 'BuildoutRoleLine')
    BuildoutResponsibilityLine = apps.get_model('programs', 'BuildoutResponsibilityLine')
    ContractorRoleRate = apps.get_model('programs', 'ContractorRoleRate')
    
    # Create or get "Unassigned" contractor
    unassigned_contractor, created = User.objects.get_or_create(
        email='unassigned@dynamicdiscoveries.com',
        defaults={
            'first_name': 'Unassigned',
            'last_name': 'Contractor',
            'is_active': False,  # Mark as inactive since it's a placeholder
        }
    )
    
    if created:
        print(f"Created placeholder contractor: {unassigned_contractor.email}")
    
    # Migrate existing role assignments to new BuildoutRoleLine
    for buildout in ProgramBuildout.objects.all():
        # Get legacy role assignments
        legacy_role_assignments = buildout.role_assignments_legacy.all()
        
        for legacy_assignment in legacy_role_assignments:
            # Create new role line with default values
            role_line, created = BuildoutRoleLine.objects.get_or_create(
                buildout=buildout,
                role=legacy_assignment.role,
                defaults={
                    'contractor': unassigned_contractor,
                    'pay_type': 'HOURLY',
                    'pay_value': Decimal('0.00'),
                    'frequency_unit': legacy_assignment.role.default_frequency_unit,
                    'frequency_count': 1,
                    'hours_per_frequency': legacy_assignment.role.default_hours_per_frequency,
                }
            )
            
            if created:
                print(f"Created role line for {buildout.title} - {legacy_assignment.role.title}")
        
        # Get legacy responsibility assignments
        legacy_resp_assignments = buildout.responsibility_assignments_legacy.all()
        
        for legacy_resp in legacy_resp_assignments:
            # Create new responsibility line
            resp_line, created = BuildoutResponsibilityLine.objects.get_or_create(
                buildout=buildout,
                responsibility=legacy_resp.responsibility,
                defaults={
                    'hours': legacy_resp.responsibility.default_hours,
                }
            )
            
            if created:
                print(f"Created responsibility line for {buildout.title} - {legacy_resp.responsibility.name}")
    
    print("Migration completed successfully!")

def reverse_migrate_legacy_data_to_new_models(apps, schema_editor):
    """Reverse migration - remove new model data."""
    BuildoutRoleLine = apps.get_model('programs', 'BuildoutRoleLine')
    BuildoutResponsibilityLine = apps.get_model('programs', 'BuildoutResponsibilityLine')
    
    # Remove all new model data
    BuildoutRoleLine.objects.all().delete()
    BuildoutResponsibilityLine.objects.all().delete()
    
    print("Reverse migration completed - removed new model data")


class Migration(migrations.Migration):

    dependencies = [
        ('programs', '0013_add_contractor_role_rates_and_version_control'),
        ('accounts', '0001_initial'),  # Add dependency on accounts app
    ]

    operations = [
        migrations.RunPython(
            migrate_legacy_data_to_new_models,
            reverse_migrate_legacy_data_to_new_models
        ),
    ]
