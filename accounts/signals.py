from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import Group

@receiver(post_migrate)
def create_default_groups(sender, **kwargs):
    """Create default groups if they don't exist."""
    default_groups = [
        'Contractor',
        'Consultant',
        'User',
        'Parent',
        'Child',
        'Money Manager',
        'Program Designer',
        'Admin'  # Adding Admin group for user management
    ]
    
    for group_name in default_groups:
        Group.objects.get_or_create(name=group_name) 