from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied

class RoleRequiredMixin(UserPassesTestMixin):
    """Mixin to restrict access based on user roles."""
    required_roles = []

    def test_func(self):
        """Check if user has any of the required roles."""
        if not self.request.user.is_authenticated:
            return False
        
        # Allow superusers to access everything
        if self.request.user.is_superuser:
            return True
            
        if not self.required_roles:
            return True
            
        return any(
            self.request.user.groups.filter(name=role).exists()
            for role in self.required_roles
        )

    def handle_no_permission(self):
        """Handle unauthorized access."""
        raise PermissionDenied("You don't have permission to access this page.") 