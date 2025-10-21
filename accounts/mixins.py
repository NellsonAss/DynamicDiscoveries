from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from functools import wraps


def get_effective_user_and_roles(request):
    """
    Get the effective user and their roles, considering impersonation.
    
    Returns:
        tuple: (effective_user, role_names_list)
        - During impersonation: returns (impersonated_user, their_roles)
        - Otherwise: returns (request.user, their_roles)
    """
    # Check for impersonation
    impersonate_user_id = request.session.get('impersonate_user_id')
    if impersonate_user_id:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            impersonated_user = User.objects.get(id=impersonate_user_id)
            return impersonated_user, impersonated_user.get_role_names()
        except User.DoesNotExist:
            # Invalid impersonation, clean up
            request.session.pop('impersonate_user_id', None)
            request.session.pop('impersonate_readonly', None)
            request.session.pop('effective_role', None)
    
    # No impersonation, return actual user
    return request.user, request.user.get_role_names()


class RoleRequiredMixin(UserPassesTestMixin):
    """
    Mixin to require specific user roles.
    
    Considers effective_role during role preview and impersonation:
    - For self role preview: checks if user has the role AND is previewing it
    - For impersonation: checks the impersonated user's actual roles
    - Never grants more permissions than the real user (or impersonated user) actually has
    """
    
    def __init__(self, required_roles=None, *args, **kwargs):
        self.required_roles = required_roles or []
        super().__init__(*args, **kwargs)
    
    def get_required_roles(self):
        """Get the required roles for this view."""
        return getattr(self, 'required_roles', [])
    
    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        
        # Get effective user and roles (considering impersonation)
        effective_user, user_roles = get_effective_user_and_roles(self.request)
        required_roles = self.get_required_roles()
        
        # Check if effective user has any of the required roles
        has_role = any(role in user_roles for role in required_roles)
        
        # For impersonation: also verify the REAL user (admin) has permission to view
        # This prevents privilege escalation through impersonation
        if self.request.session.get('impersonate_user_id'):
            # Admin must be superuser or have admin role to impersonate
            admin_can_impersonate = (
                self.request.user.is_superuser or 
                self.request.user.groups.filter(name='Admin').exists()
            )
            return has_role and admin_can_impersonate
        
        return has_role
    
    def handle_no_permission(self):
        messages.error(self.request, "You don't have permission to access this page.")
        return redirect('home')


def role_required(required_roles):
    """
    Decorator to require specific user roles.
    
    Considers effective_role during role preview and impersonation.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, "Please log in to access this page.")
                return redirect('home')
            
            # Get effective user and roles (considering impersonation)
            effective_user, user_roles = get_effective_user_and_roles(request)
            
            # Check if effective user has any of the required roles
            has_role = any(role in user_roles for role in required_roles)
            
            # For impersonation: also verify the REAL user (admin) has permission
            if request.session.get('impersonate_user_id'):
                admin_can_impersonate = (
                    request.user.is_superuser or 
                    request.user.groups.filter(name='Admin').exists()
                )
                if not (has_role and admin_can_impersonate):
                    messages.error(request, "You don't have permission to access this page.")
                    return redirect('home')
            elif not has_role:
                messages.error(request, "You don't have permission to access this page.")
                return redirect('home')
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator 