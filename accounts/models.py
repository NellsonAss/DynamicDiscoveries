from django.contrib.auth.models import AbstractUser, Group, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_migrate
from django.dispatch import receiver

class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a user with the given email and password."""
        if not email:
            raise ValueError('The Email field must be set')
        # Only normalize the domain part (standard Django behavior)
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def get_by_email_case_insensitive(self, email):
        """Get user by email using case-insensitive lookup."""
        try:
            return self.get(email__iexact=email)
        except self.model.DoesNotExist:
            return None
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    """Custom user model that uses email as the username."""
    email = models.EmailField(_('email address'), unique=True)
    username = None  # Disable username field
    
    objects = UserManager()
    
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
    
    @property
    def is_app_admin(self):
        """Check if user has admin role in the application."""
        return self.groups.filter(name='Admin').exists()
    
    @property
    def can_access_django_admin(self):
        """Check if user can access Django admin interface."""
        return self.is_staff or self.is_superuser
    
    @property
    def can_manage_users(self):
        """Check if user can manage other users in the application."""
        return self.is_app_admin or self.is_superuser
    
    def get_role_names(self):
        """Get a list of role names for the user."""
        return [group.name for group in self.groups.all()]

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