from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_migrate
from django.dispatch import receiver

class User(AbstractUser):
    """Custom user model that uses email as the username."""
    email = models.EmailField(_('email address'), unique=True)
    username = None  # Disable username field
    
    # Add related_name to resolve reverse accessor clashes
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name='custom_user_set',
        related_query_name='custom_user'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name='custom_user_set',
        related_query_name='custom_user'
    )
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Email is already required by AbstractUser
    
    def __str__(self):
        return self.email

class Profile(models.Model):
    """Extended user profile with additional information."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email}'s profile"

    @property
    def roles(self):
        """Return a list of the user's role names."""
        return [group.name for group in self.user.groups.all()]

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