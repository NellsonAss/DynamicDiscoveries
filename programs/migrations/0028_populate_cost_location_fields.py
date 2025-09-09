# Generated data migration

from django.db import migrations


def populate_cost_location_fields(apps, schema_editor):
    """Populate new rate and frequency fields from override fields or defaults."""
    BuildoutBaseCostAssignment = apps.get_model('programs', 'BuildoutBaseCostAssignment')
    BuildoutLocationAssignment = apps.get_model('programs', 'BuildoutLocationAssignment')
    
    # Populate base cost assignments
    for assignment in BuildoutBaseCostAssignment.objects.all():
        if assignment.override_rate is not None:
            assignment.rate = assignment.override_rate
        else:
            assignment.rate = assignment.base_cost.rate
            
        if assignment.override_frequency:
            assignment.frequency = assignment.override_frequency
        else:
            assignment.frequency = assignment.base_cost.frequency
            
        assignment.save()
    
    # Populate location assignments
    for assignment in BuildoutLocationAssignment.objects.all():
        if assignment.override_rate is not None:
            assignment.rate = assignment.override_rate
        else:
            assignment.rate = assignment.location.default_rate
            
        if assignment.override_frequency:
            assignment.frequency = assignment.override_frequency
        else:
            assignment.frequency = assignment.location.default_frequency
            
        assignment.save()


def reverse_populate_cost_location_fields(apps, schema_editor):
    """Reverse the population by clearing the new fields."""
    BuildoutBaseCostAssignment = apps.get_model('programs', 'BuildoutBaseCostAssignment')
    BuildoutLocationAssignment = apps.get_model('programs', 'BuildoutLocationAssignment')
    
    BuildoutBaseCostAssignment.objects.update(rate=None, frequency=None)
    BuildoutLocationAssignment.objects.update(rate=None, frequency=None)


class Migration(migrations.Migration):

    dependencies = [
        ('programs', '0027_enhance_cost_location_fields'),
    ]

    operations = [
        migrations.RunPython(
            populate_cost_location_fields,
            reverse_populate_cost_location_fields
        ),
    ]
