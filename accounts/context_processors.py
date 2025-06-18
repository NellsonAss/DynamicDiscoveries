def user_roles(request):
    """Add user roles to the template context."""
    if request.user.is_authenticated:
        return {
            'user_roles': request.user.groups.all(),
            'is_admin': request.user.groups.filter(name='Admin').exists(),
            'can_access_django_admin': request.user.is_staff or request.user.is_superuser,
            'can_manage_users': request.user.groups.filter(name='Admin').exists() or request.user.is_superuser
        }
    return {
        'user_roles': [],
        'is_admin': False,
        'can_access_django_admin': False,
        'can_manage_users': False
    } 