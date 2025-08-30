from django.contrib import admin
from .models import StudentNote, ParentNote


@admin.register(StudentNote)
class StudentNoteAdmin(admin.ModelAdmin):
    list_display = ['student', 'title_preview', 'created_by', 'is_public', 'created_at', 'soft_deleted']
    list_filter = ['is_public', 'visibility_scope', 'created_at', 'soft_deleted', 'created_by']
    search_fields = ['title', 'body', 'student__first_name', 'student__last_name', 'student__parent__email']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('student', 'title', 'body')
        }),
        ('Visibility', {
            'fields': ('visibility_scope', 'is_public')
        }),
        ('Metadata', {
            'fields': ('created_by', 'edited_by_last', 'created_at', 'updated_at', 'soft_deleted')
        }),
    )
    
    def title_preview(self, obj):
        if obj.title:
            return obj.title
        return obj.body[:50] + "..." if len(obj.body) > 50 else obj.body
    title_preview.short_description = "Title/Preview"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'student', 'student__parent', 'created_by', 'edited_by_last'
        )


@admin.register(ParentNote)
class ParentNoteAdmin(admin.ModelAdmin):
    list_display = ['parent', 'title_preview', 'created_by', 'is_public', 'created_at', 'soft_deleted']
    list_filter = ['is_public', 'visibility_scope', 'created_at', 'soft_deleted', 'created_by']
    search_fields = ['title', 'body', 'parent__email', 'parent__first_name', 'parent__last_name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('parent', 'title', 'body')
        }),
        ('Visibility', {
            'fields': ('visibility_scope', 'is_public')
        }),
        ('Metadata', {
            'fields': ('created_by', 'edited_by_last', 'created_at', 'updated_at', 'soft_deleted')
        }),
    )
    
    def title_preview(self, obj):
        if obj.title:
            return obj.title
        return obj.body[:50] + "..." if len(obj.body) > 50 else obj.body
    title_preview.short_description = "Title/Preview"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'parent', 'created_by', 'edited_by_last'
        )
