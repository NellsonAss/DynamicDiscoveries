def user_roles(request):
    """Add user roles to the template context."""
    if request.user.is_authenticated:
        return {
            'user_roles': request.user.groups.all(),
            'is_admin': request.user.groups.filter(name='Admin').exists()
        }
    return {
        'user_roles': [],
        'is_admin': False
    } 