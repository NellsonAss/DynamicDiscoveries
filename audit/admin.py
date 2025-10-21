from django.contrib import admin
from .models import ImpersonationLog


@admin.register(ImpersonationLog)
class ImpersonationLogAdmin(admin.ModelAdmin):
    """Admin interface for viewing impersonation logs."""
    list_display = ['admin_user', 'target_user', 'started_at', 'ended_at', 'readonly', 'is_active']
    list_filter = ['readonly', 'started_at', 'ended_at']
    search_fields = ['admin_user__email', 'target_user__email', 'reason_note']
    readonly_fields = ['admin_user', 'target_user', 'started_at', 'ended_at', 
                       'readonly', 'reason_note', 'ip_address', 'user_agent', 'duration']
    date_hierarchy = 'started_at'
    
    def has_add_permission(self, request):
        """Prevent manual creation of impersonation logs."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of audit logs."""
        return False
    
    def is_active(self, obj):
        """Display active status."""
        return obj.is_active
    is_active.boolean = True
    is_active.short_description = 'Active'

