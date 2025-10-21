from django.contrib import admin
from .models import Contact, Conversation, Message

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


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['subject', 'owner_email', 'status', 'message_count', 'created_at', 'updated_at']
    list_filter = ['status', 'created_at', 'updated_at']
    search_fields = ['subject', 'owner__email', 'owner__first_name', 'owner__last_name']
    readonly_fields = ['created_at', 'updated_at', 'message_count']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Conversation Details', {
            'fields': ('owner', 'subject', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'message_count'),
            'classes': ('collapse',)
        }),
    )
    
    def owner_email(self, obj):
        return obj.owner.email
    owner_email.short_description = 'Owner Email'
    owner_email.admin_order_field = 'owner__email'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('owner').prefetch_related('messages')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['conversation_subject', 'author_email', 'role', 'body_preview', 'created_at']
    list_filter = ['role', 'created_at', 'conversation__status']
    search_fields = ['body', 'conversation__subject', 'author__email', 'conversation__owner__email']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Message Details', {
            'fields': ('conversation', 'author', 'role', 'body')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def conversation_subject(self, obj):
        return obj.conversation.subject
    conversation_subject.short_description = 'Conversation'
    conversation_subject.admin_order_field = 'conversation__subject'
    
    def author_email(self, obj):
        return obj.author.email if obj.author else 'System'
    author_email.short_description = 'Author'
    author_email.admin_order_field = 'author__email'
    
    def body_preview(self, obj):
        return obj.body[:100] + '...' if len(obj.body) > 100 else obj.body
    body_preview.short_description = 'Message Preview'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('conversation', 'author')
