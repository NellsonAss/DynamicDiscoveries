from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    ProgramType, ProgramInstance, RegistrationForm, FormQuestion,
    Child, Registration, Role, ProgramBuildout, ProgramRole, BaseCost, ProgramBaseCost
)


class FormQuestionInline(admin.TabularInline):
    model = FormQuestion
    extra = 1
    ordering = ['order']


class ProgramRoleInline(admin.TabularInline):
    model = ProgramRole
    extra = 1
    fields = ['role', 'hour_frequency', 'hour_multiplier', 'override_hours', 'calculated_hours', 'calculated_payout', 'calculated_percentage']
    readonly_fields = ['calculated_hours', 'calculated_payout', 'calculated_percentage']

    def calculated_hours(self, obj):
        if obj.pk:
            return f"{obj.calculate_total_hours(12, 4):.1f} hours"
        return "Save to calculate"
    calculated_hours.short_description = 'Total Hours'

    def calculated_payout(self, obj):
        if obj.pk:
            return f"${obj.calculate_payout(12, 4):.2f}"
        return "Save to calculate"
    calculated_payout.short_description = 'Payout'

    def calculated_percentage(self, obj):
        if obj.pk:
            return f"{obj.calculate_percentage_of_revenue(12, 4):.1f}%"
        return "Save to calculate"
    calculated_percentage.short_description = '% of Revenue'


class ProgramBaseCostInline(admin.TabularInline):
    model = ProgramBaseCost
    extra = 1
    fields = ['base_cost', 'multiplier', 'calculated_cost']
    readonly_fields = ['calculated_cost']

    def calculated_cost(self, obj):
        if obj.pk:
            return f"${obj.calculate_cost(12):.2f}"
        return "Save to calculate"
    calculated_cost.short_description = 'Total Cost'


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'hourly_rate', 'responsibilities_short']
    list_filter = ['hourly_rate']
    search_fields = ['name', 'responsibilities']
    ordering = ['name']

    def responsibilities_short(self, obj):
        return obj.responsibilities[:100] + "..." if len(obj.responsibilities) > 100 else obj.responsibilities
    responsibilities_short.short_description = 'Responsibilities'


@admin.register(BaseCost)
class BaseCostAdmin(admin.ModelAdmin):
    list_display = ['name', 'cost_per_student', 'description_short']
    list_filter = ['cost_per_student']
    search_fields = ['name', 'description']
    ordering = ['name']

    def description_short(self, obj):
        return obj.description[:100] + "..." if len(obj.description) > 100 else obj.description
    description_short.short_description = 'Description'


@admin.register(ProgramBuildout)
class ProgramBuildoutAdmin(admin.ModelAdmin):
    list_display = ['title', 'program_type', 'expected_students', 'num_days', 'total_revenue', 'total_payouts', 'profit', 'profit_margin']
    list_filter = ['program_type', 'num_days']
    search_fields = ['title', 'program_type__name']
    readonly_fields = ['total_revenue', 'total_payouts', 'profit', 'profit_margin']

    def total_revenue(self, obj):
        return f"${obj.total_revenue:.2f}"
    total_revenue.short_description = 'Revenue'

    def total_payouts(self, obj):
        return f"${obj.total_payouts:.2f}"
    total_payouts.short_description = 'Payouts'

    def profit(self, obj):
        return f"${obj.profit:.2f}"
    profit.short_description = 'Profit'

    def profit_margin(self, obj):
        return f"{obj.profit_margin:.1f}%"
    profit_margin.short_description = 'Margin'

    fieldsets = (
        ('Basic Information', {
            'fields': ('program_type', 'title')
        }),
        ('Program Details', {
            'fields': ('expected_students', 'num_days', 'sessions_per_day')
        }),
        ('Financial Summary', {
            'fields': ('total_revenue', 'total_payouts', 'profit', 'profit_margin'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProgramRole)
class ProgramRoleAdmin(admin.ModelAdmin):
    list_display = ['program_type', 'role', 'hour_frequency', 'hour_multiplier', 'calculated_hours', 'calculated_payout']
    list_filter = ['hour_frequency', 'role', 'program_type']
    search_fields = ['role__name', 'program_type__name']
    readonly_fields = ['calculated_hours', 'calculated_payout', 'calculated_percentage']

    def calculated_hours(self, obj):
        if obj.pk:
            return f"{obj.calculate_total_hours(12, 4):.1f} hours"
        return "Save to calculate"
    calculated_hours.short_description = 'Total Hours'

    def calculated_payout(self, obj):
        if obj.pk:
            return f"${obj.calculate_payout(12, 4):.2f}"
        return "Save to calculate"
    calculated_payout.short_description = 'Payout'

    def calculated_percentage(self, obj):
        if obj.pk:
            return f"{obj.calculate_percentage_of_revenue(12, 4):.1f}%"
        return "Save to calculate"
    calculated_percentage.short_description = '% of Revenue'


@admin.register(ProgramBaseCost)
class ProgramBaseCostAdmin(admin.ModelAdmin):
    list_display = ['program_type', 'base_cost', 'multiplier', 'calculated_cost']
    list_filter = ['base_cost', 'program_type']
    search_fields = ['base_cost__name', 'program_type__name']
    readonly_fields = ['calculated_cost']

    def calculated_cost(self, obj):
        if obj.pk:
            return f"${obj.calculate_cost(12):.2f}"
        return "Save to calculate"
    calculated_cost.short_description = 'Total Cost'


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
    list_display = ['name', 'rate_per_student', 'target_grade_levels', 'instance_count', 'buildout_count', 'default_form']
    list_filter = ['created_at', 'rate_per_student']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [ProgramRoleInline, ProgramBaseCostInline]

    def instance_count(self, obj):
        return obj.instances.count()
    instance_count.short_description = 'Instances'

    def buildout_count(self, obj):
        return obj.buildouts.count()
    buildout_count.short_description = 'Buildouts'

    def default_form(self, obj):
        if obj.default_registration_form:
            return format_html(
                '<a href="{}">{}</a>',
                reverse('admin:programs_registrationform_change', args=[obj.default_registration_form.pk]),
                obj.default_registration_form.title
            )
        return '-'
    default_form.short_description = 'Default Form'

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'target_grade_levels')
        }),
        ('Pricing', {
            'fields': ('rate_per_student',)
        }),
        ('Forms', {
            'fields': ('default_registration_form',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


class RegistrationInline(admin.TabularInline):
    model = Registration
    extra = 0
    readonly_fields = ['registered_at', 'updated_at']
    fields = ['child', 'status', 'registered_at']


@admin.register(ProgramInstance)
class ProgramInstanceAdmin(admin.ModelAdmin):
    list_display = [
        'program_type', 'instructor', 'start_date', 'end_date',
        'location', 'enrollment_status', 'expected_revenue', 'expected_profit', 'is_active'
    ]
    list_filter = [
        'is_active', 'start_date', 'end_date', 'instructor__groups__name',
        'program_type'
    ]
    search_fields = [
        'program_type__name', 'location', 'instructor__email'
    ]
    readonly_fields = ['created_at', 'updated_at', 'current_enrollment', 'available_spots', 'expected_revenue', 'expected_payouts', 'expected_profit']
    inlines = [RegistrationInline]
    date_hierarchy = 'start_date'

    def enrollment_status(self, obj):
        return f"{obj.current_enrollment}/{obj.capacity}"
    enrollment_status.short_description = 'Enrollment'

    def expected_revenue(self, obj):
        return f"${obj.expected_revenue:.2f}"
    expected_revenue.short_description = 'Revenue'

    def expected_profit(self, obj):
        return f"${obj.expected_profit:.2f}"
    expected_profit.short_description = 'Profit'

    fieldsets = (
        ('Program Details', {
            'fields': ('program_type', 'buildout', 'instructor', 'location')
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
        ('Financial Projections', {
            'fields': ('expected_revenue', 'expected_payouts', 'expected_profit'),
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
