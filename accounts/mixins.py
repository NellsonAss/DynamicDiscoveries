from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from functools import wraps

class RoleRequiredMixin(UserPassesTestMixin):
    """Mixin to require specific user roles."""
    
    def __init__(self, required_roles=None, *args, **kwargs):
        self.required_roles = required_roles or []
        super().__init__(*args, **kwargs)
    
    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        
        user_roles = self.request.user.get_role_names()
        return any(role in user_roles for role in self.required_roles)
    
    def handle_no_permission(self):
        messages.error(self.request, "You don't have permission to access this page.")
        return redirect('home')

def role_required(required_roles):
    """Decorator to require specific user roles."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, "Please log in to access this page.")
                return redirect('home')
            
            user_roles = request.user.get_role_names()
            if not any(role in user_roles for role in required_roles):
                messages.error(request, "You don't have permission to access this page.")
                return redirect('home')
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator 