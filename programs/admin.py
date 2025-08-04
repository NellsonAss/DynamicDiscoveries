from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    ProgramType, ProgramInstance, RegistrationForm, FormQuestion,
    Child, Registration
)


class FormQuestionInline(admin.TabularInline):
    model = FormQuestion
    extra = 1
    ordering = ['order']


@admin.register(RegistrationForm)
class RegistrationFormAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_by', 'question_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at', 'created_by__groups__name']
    search_fields = ['title', 'description', 'created_by__email']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [FormQuestionInline]
    actions = ['duplicate_form']

    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = 'Questions'

    def duplicate_form(self, request, queryset):
        for form in queryset:
            form.duplicate()
        self.message_user(request, f"Duplicated {queryset.count()} form(s)")
    duplicate_form.short_description = "Duplicate selected forms"


@admin.register(FormQuestion)
class FormQuestionAdmin(admin.ModelAdmin):
    list_display = ['form', 'question_text', 'question_type', 'is_required', 'order']
    list_filter = ['question_type', 'is_required', 'form']
    search_fields = ['question_text', 'form__title']
    ordering = ['form', 'order']


@admin.register(ProgramType)
class ProgramTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'target_grade_levels', 'instance_count', 'default_form']
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']

    def instance_count(self, obj):
        return obj.instances.count()
    instance_count.short_description = 'Instances'

    def default_form(self, obj):
        if obj.default_registration_form:
            return format_html(
                '<a href="{}">{}</a>',
                reverse('admin:programs_registrationform_change', args=[obj.default_registration_form.pk]),
                obj.default_registration_form.title
            )
        return '-'
    default_form.short_description = 'Default Form'


class RegistrationInline(admin.TabularInline):
    model = Registration
    extra = 0
    readonly_fields = ['registered_at', 'updated_at']
    fields = ['child', 'status', 'registered_at']


@admin.register(ProgramInstance)
class ProgramInstanceAdmin(admin.ModelAdmin):
    list_display = [
        'program_type', 'instructor', 'start_date', 'end_date',
        'location', 'enrollment_status', 'is_active'
    ]
    list_filter = [
        'is_active', 'start_date', 'end_date', 'instructor__groups__name',
        'program_type'
    ]
    search_fields = [
        'program_type__name', 'location', 'instructor__email'
    ]
    readonly_fields = ['created_at', 'updated_at', 'current_enrollment', 'available_spots']
    inlines = [RegistrationInline]
    date_hierarchy = 'start_date'

    def enrollment_status(self, obj):
        return f"{obj.current_enrollment}/{obj.capacity}"
    enrollment_status.short_description = 'Enrollment'

    fieldsets = (
        ('Program Details', {
            'fields': ('program_type', 'instructor', 'location')
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date')
        }),
        ('Capacity & Forms', {
            'fields': ('capacity', 'assigned_form')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Enrollment Info', {
            'fields': ('current_enrollment', 'available_spots'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'parent', 'age', 'grade_level', 'registration_count']
    list_filter = ['grade_level', 'date_of_birth', 'parent__groups__name']
    search_fields = ['first_name', 'last_name', 'parent__email']
    readonly_fields = ['created_at', 'updated_at', 'age']

    def registration_count(self, obj):
        return obj.registrations.count()
    registration_count.short_description = 'Registrations'

    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Full Name'


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = [
        'child', 'program_instance', 'status', 'registered_at',
        'has_form_responses'
    ]
    list_filter = [
        'status', 'registered_at', 'program_instance__program_type',
        'child__parent__groups__name'
    ]
    search_fields = [
        'child__first_name', 'child__last_name', 'child__parent__email',
        'program_instance__program_type__name'
    ]
    readonly_fields = ['registered_at', 'updated_at']
    date_hierarchy = 'registered_at'

    def has_form_responses(self, obj):
        return bool(obj.form_responses)
    has_form_responses.boolean = True
    has_form_responses.short_description = 'Form Completed'

    fieldsets = (
        ('Registration Details', {
            'fields': ('child', 'program_instance', 'status')
        }),
        ('Form Responses', {
            'fields': ('form_responses', 'notes'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('registered_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
