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


def effective_role(request):
    """
    Add effective role and impersonation context to templates.
    
    This allows admins to preview the site as different roles and
    impersonate other users for testing/support purposes.
    """
    context = {
        'effective_role': 'Auto',
        'is_impersonating': False,
        'impersonated_user': None,
        'impersonation_readonly': True,
        'can_impersonate': False,
        'user_has_multiple_roles': False,
    }
    
    if not request.user.is_authenticated:
        return context
    
    # Check if user can impersonate (superuser or has permission)
    context['can_impersonate'] = (
        request.user.is_superuser or 
        request.user.has_perm('auth.can_impersonate_users')
    )
    
    # Check if user has multiple roles (for role preview)
    user_role_count = request.user.groups.count()
    context['user_has_multiple_roles'] = user_role_count >= 2
    
    # Check for active impersonation
    impersonate_user_id = request.session.get('impersonate_user_id')
    if impersonate_user_id:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            impersonated_user = User.objects.get(id=impersonate_user_id)
            context['is_impersonating'] = True
            context['impersonated_user'] = impersonated_user
            context['impersonation_readonly'] = request.session.get('impersonate_readonly', True)
            
            # Effective role is based on impersonated user's primary role
            # or explicitly set in session
            session_role = request.session.get('effective_role')
            if session_role:
                context['effective_role'] = session_role
            else:
                # Auto-detect from impersonated user's roles
                user_roles = impersonated_user.get_role_names()
                if user_roles:
                    # Prioritize: Parent > Contractor > Admin > Others
                    if 'Parent' in user_roles:
                        context['effective_role'] = 'Parent'
                    elif 'Contractor' in user_roles:
                        context['effective_role'] = 'Contractor'
                    elif 'Admin' in user_roles:
                        context['effective_role'] = 'Admin'
                    else:
                        context['effective_role'] = user_roles[0]
        except User.DoesNotExist:
            # Clean up invalid impersonation session
            request.session.pop('impersonate_user_id', None)
            request.session.pop('impersonate_readonly', None)
            request.session.pop('effective_role', None)
    else:
        # Not impersonating - check for self role preview
        session_role = request.session.get('effective_role')
        if session_role and session_role != 'Auto':
            # Verify user actually has this role
            if request.user.groups.filter(name=session_role).exists():
                context['effective_role'] = session_role
            else:
                # User lost this role, revert to Auto
                request.session.pop('effective_role', None)
    
    return context
