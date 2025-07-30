from django.contrib import admin
from .models import Contact

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['parent_name', 'email', 'interest', 'status', 'created_at', 'days_old_display']
    list_filter = ['status', 'interest', 'created_at']
    search_fields = ['parent_name', 'email', 'message']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Contact Information', {
            'fields': ('parent_name', 'email', 'phone', 'interest', 'message')
        }),
        ('Status & Notes', {
            'fields': ('status', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def days_old_display(self, obj):
        days = obj.days_old
        if days == 0:
            return "Today"
        elif days == 1:
            return "Yesterday"
        else:
            return f"{days} days ago"
    days_old_display.short_description = 'Age'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related()
