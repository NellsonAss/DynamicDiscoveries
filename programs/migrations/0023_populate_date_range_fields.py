# Generated manually to populate date range fields

from django.db import migrations


def populate_date_range_fields(apps, schema_editor):
    """Populate start_date and end_date from existing date field."""
    ContractorDayOffRequest = apps.get_model('programs', 'ContractorDayOffRequest')
    
    for request in ContractorDayOffRequest.objects.all():
        if request.date and not request.start_date:
            request.start_date = request.date
            request.end_date = request.date
            request.save()


def reverse_populate_date_range_fields(apps, schema_editor):
    """Reverse: populate date from start_date if start_date equals end_date."""
    ContractorDayOffRequest = apps.get_model('programs', 'ContractorDayOffRequest')
    
    for request in ContractorDayOffRequest.objects.all():
        if request.start_date and request.end_date and request.start_date == request.end_date and not request.date:
            request.date = request.start_date
            request.save()


class Migration(migrations.Migration):

    dependencies = [
        ('programs', '0022_update_day_off_request_to_date_range'),
    ]

    operations = [
        migrations.RunPython(
            populate_date_range_fields,
            reverse_populate_date_range_fields,
        ),
    ]
