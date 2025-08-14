from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    ProgramType, ProgramInstance, RegistrationForm, FormQuestion,
    Child, Registration, Role, ProgramBuildout, Responsibility, 
    BuildoutRoleAssignment, BuildoutResponsibilityAssignment, BaseCost, 
    BuildoutBaseCostAssignment, InstanceRoleAssignment
)


class FormQuestionInline(admin.TabularInline):
    model = FormQuestion
    extra = 1
    ordering = ['order']


class BuildoutResponsibilityAssignmentInline(admin.TabularInline):
    model = BuildoutResponsibilityAssignment
    extra = 1
    fields = ['responsibility', 'calculated_yearly_hours']
    readonly_fields = ['calculated_yearly_hours']

    def calculated_yearly_hours(self, obj):
        if obj.pk:
            return f"{obj.calculate_yearly_hours():.1f} hours"
        return "Save to calculate"
    calculated_yearly_hours.short_description = 'Yearly Hours'


class BuildoutRoleAssignmentInline(admin.TabularInline):
    model = BuildoutRoleAssignment
    extra = 1
    fields = ['role', 'calculated_yearly_hours', 'calculated_payout', 'calculated_percent_of_revenue']
    readonly_fields = ['calculated_yearly_hours', 'calculated_payout', 'calculated_percent_of_revenue']

    def calculated_yearly_hours(self, obj):
        if obj.pk:
            return f"{obj.buildout.calculate_total_hours_per_role(obj.role):.1f} hours"
        return "Save to calculate"
    calculated_yearly_hours.short_description = 'Yearly Hours'

    def calculated_payout(self, obj):
        if obj.pk:
            return f"${obj.buildout.calculate_payout_per_role(obj.role):.2f}"
        return "Save to calculate"
    calculated_payout.short_description = 'Yearly Payout'

    def calculated_percent_of_revenue(self, obj):
        if obj.pk:
            return f"{obj.buildout.calculate_percent_of_revenue_per_role(obj.role):.1f}%"
        return "Save to calculate"
    calculated_percent_of_revenue.short_description = '% of Revenue'


class BuildoutBaseCostAssignmentInline(admin.TabularInline):
    model = BuildoutBaseCostAssignment
    extra = 1
    fields = ['base_cost', 'multiplier', 'calculated_yearly_cost']
    readonly_fields = ['calculated_yearly_cost']

    def calculated_yearly_cost(self, obj):
        if obj.pk:
            return f"${obj.calculate_yearly_cost():.2f}"
        return "Save to calculate"
    calculated_yearly_cost.short_description = 'Yearly Cost'


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['title', 'description_short', 'responsibility_count']
    list_filter = ['created_at']
    search_fields = ['title', 'description', 'default_responsibilities']
    ordering = ['title']
    readonly_fields = ['created_at', 'updated_at']

    def description_short(self, obj):
        return obj.description[:100] + "..." if len(obj.description) > 100 else obj.description
    description_short.short_description = 'Description'

    def responsibility_count(self, obj):
        return obj.responsibilities.count()
    responsibility_count.short_description = 'Responsibilities'


@admin.register(Responsibility)
class ResponsibilityAdmin(admin.ModelAdmin):
    list_display = ['role', 'name', 'frequency_type', 'hours', 'description_short']
    list_filter = ['frequency_type', 'role', 'created_at']
    search_fields = ['name', 'description', 'role__title']
    ordering = ['role__title', 'name']
    readonly_fields = ['created_at', 'updated_at']

    def description_short(self, obj):
        return obj.description[:100] + "..." if len(obj.description) > 100 else obj.description
    description_short.short_description = 'Description'


@admin.register(BaseCost)
class BaseCostAdmin(admin.ModelAdmin):
    list_display = ['name', 'frequency', 'rate', 'description_short']
    list_filter = ['frequency', 'rate', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at']

    def description_short(self, obj):
        return obj.description[:100] + "..." if len(obj.description) > 100 else obj.description
    description_short.short_description = 'Description'


@admin.register(ProgramBuildout)
class ProgramBuildoutAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'program_type', 'version_number', 'is_active', 'num_facilitators', 
        'total_students_per_year', 'total_revenue_per_year', 'total_yearly_costs', 
        'expected_profit', 'profit_margin'
    ]
    list_filter = ['program_type', 'is_active', 'is_new_workshop', 'num_facilitators', 'created_at']
    search_fields = ['title', 'program_type__name']
    readonly_fields = [
        'num_workshops_per_year', 'total_students_per_year', 'total_sessions_per_year',
        'total_revenue_per_year', 'total_yearly_costs', 'expected_profit', 'profit_margin',
        'created_at', 'updated_at'
    ]
    inlines = [BuildoutResponsibilityAssignmentInline, BuildoutRoleAssignmentInline, BuildoutBaseCostAssignmentInline]
    actions = ['clone_buildout']

    def total_revenue_per_year(self, obj):
        return f"${obj.total_revenue_per_year:.2f}"
    total_revenue_per_year.short_description = 'Yearly Revenue'

    def total_yearly_costs(self, obj):
        return f"${obj.total_yearly_costs:.2f}"
    total_yearly_costs.short_description = 'Yearly Costs'

    def expected_profit(self, obj):
        return f"${obj.expected_profit:.2f}"
    expected_profit.short_description = 'Expected Profit'

    def profit_margin(self, obj):
        return f"{obj.profit_margin:.1f}%"
    profit_margin.short_description = 'Margin'

    def clone_buildout(self, request, queryset):
        for buildout in queryset:
            buildout.clone()
        self.message_user(request, f"Cloned {queryset.count()} buildout(s)")
    clone_buildout.short_description = "Clone selected buildouts"

    fieldsets = (
        ('Basic Information', {
            'fields': ('program_type', 'title', 'version_number', 'is_active')
        }),
        ('Scoping Parameters', {
            'fields': (
                'is_new_workshop', 'num_facilitators', 'num_new_facilitators',
                'students_per_workshop', 'sessions_per_workshop', 'new_workshop_concepts_per_year',
                'rate_per_student'
            )
        }),
        ('Calculated Values', {
            'fields': (
                'num_workshops_per_year', 'total_students_per_year', 'total_sessions_per_year',
                'total_revenue_per_year', 'total_yearly_costs', 'expected_profit', 'profit_margin'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(BuildoutResponsibilityAssignment)
class BuildoutResponsibilityAssignmentAdmin(admin.ModelAdmin):
    list_display = [
        'buildout', 'responsibility', 'calculated_yearly_hours'
    ]
    list_filter = ['responsibility__frequency_type', 'responsibility__role', 'buildout__program_type']
    search_fields = ['responsibility__name', 'responsibility__role__title', 'buildout__title']
    readonly_fields = ['calculated_yearly_hours', 'created_at']

    def calculated_yearly_hours(self, obj):
        if obj.pk:
            return f"{obj.calculate_yearly_hours():.1f} hours"
        return "Save to calculate"
    calculated_yearly_hours.short_description = 'Yearly Hours'


@admin.register(BuildoutRoleAssignment)
class BuildoutRoleAssignmentAdmin(admin.ModelAdmin):
    list_display = [
        'buildout', 'role', 'calculated_yearly_hours', 'calculated_payout', 'calculated_percent_of_revenue'
    ]
    list_filter = ['role', 'buildout__program_type']
    search_fields = ['role__title', 'buildout__title']
    readonly_fields = ['calculated_yearly_hours', 'calculated_payout', 'calculated_percent_of_revenue', 'created_at']

    def calculated_yearly_hours(self, obj):
        if obj.pk:
            return f"{obj.buildout.calculate_total_hours_per_role(obj.role):.1f} hours"
        return "Save to calculate"
    calculated_yearly_hours.short_description = 'Yearly Hours'

    def calculated_payout(self, obj):
        if obj.pk:
            return f"${obj.buildout.calculate_payout_per_role(obj.role):.2f}"
        return "Save to calculate"
    calculated_payout.short_description = 'Yearly Payout'

    def calculated_percent_of_revenue(self, obj):
        if obj.pk:
            return f"{obj.buildout.calculate_percent_of_revenue_per_role(obj.role):.1f}%"
        return "Save to calculate"
    calculated_percent_of_revenue.short_description = '% of Revenue'


@admin.register(BuildoutBaseCostAssignment)
class BuildoutBaseCostAssignmentAdmin(admin.ModelAdmin):
    list_display = ['buildout', 'base_cost', 'frequency', 'multiplier', 'calculated_yearly_cost']
    list_filter = ['base_cost__frequency', 'buildout__program_type']
    search_fields = ['base_cost__name', 'buildout__title']
    readonly_fields = ['calculated_yearly_cost', 'created_at']

    def frequency(self, obj):
        return obj.base_cost.frequency
    frequency.short_description = 'Frequency'

    def calculated_yearly_cost(self, obj):
        if obj.pk:
            return f"${obj.calculate_yearly_cost():.2f}"
        return "Save to calculate"
    calculated_yearly_cost.short_description = 'Yearly Cost'


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
    list_display = [
        'name', 'buildout_count', 'description_short', 'created_at'
    ]
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']

    def buildout_count(self, obj):
        return obj.buildouts.count()
    buildout_count.short_description = 'Buildouts'

    def description_short(self, obj):
        return obj.description[:100] + "..." if len(obj.description) > 100 else obj.description
    description_short.short_description = 'Description'

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description')
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


class InstanceRoleAssignmentInline(admin.TabularInline):
    model = InstanceRoleAssignment
    extra = 1
    fields = ['role', 'contractor', 'override_hours', 'override_rate', 'computed_payout']
    readonly_fields = ['computed_payout']


@admin.register(ProgramInstance)
class ProgramInstanceAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'buildout', 'start_date', 'end_date', 'location',
        'enrollment_status', 'actual_revenue', 'expected_profit', 'is_active'
    ]
    list_filter = [
        'is_active', 'start_date', 'end_date', 'buildout__program_type'
    ]
    search_fields = [
        'title', 'buildout__title', 'location'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'current_enrollment', 'available_spots', 
        'actual_revenue', 'expected_profit'
    ]
    inlines = [RegistrationInline, InstanceRoleAssignmentInline]
    date_hierarchy = 'start_date'

    def enrollment_status(self, obj):
        return f"{obj.current_enrollment}/{obj.capacity}"
    enrollment_status.short_description = 'Enrollment'

    def actual_revenue(self, obj):
        return f"${obj.actual_revenue:.2f}"
    actual_revenue.short_description = 'Revenue'

    def expected_profit(self, obj):
        return f"${obj.expected_profit:.2f}"
    expected_profit.short_description = 'Profit'

    fieldsets = (
        ('Program Details', {
            'fields': ('buildout', 'title', 'location')
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date')
        }),
        ('Capacity & Forms', {
            'fields': ('capacity', 'assigned_form')
        }),
        ('Overrides', {
            'fields': ('override_counts',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Enrollment Info', {
            'fields': ('current_enrollment', 'available_spots'),
            'classes': ('collapse',)
        }),
        ('Financial Projections', {
            'fields': ('actual_revenue', 'expected_profit'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(InstanceRoleAssignment)
class InstanceRoleAssignmentAdmin(admin.ModelAdmin):
    list_display = [
        'program_instance', 'role', 'contractor', 'computed_payout',
        'override_hours', 'override_rate'
    ]
    list_filter = ['role', 'program_instance__buildout__program_type']
    search_fields = [
        'contractor__email', 'role__title', 'program_instance__title'
    ]
    readonly_fields = ['computed_payout', 'created_at', 'updated_at']

    actions = ['update_computed_payouts']

    def update_computed_payouts(self, request, queryset):
        for assignment in queryset:
            assignment.update_computed_payout()
        self.message_user(request, f"Updated computed payouts for {queryset.count()} assignment(s)")
    update_computed_payouts.short_description = "Update computed payouts"


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
        'status', 'registered_at', 'program_instance__buildout__program_type',
        'child__parent__groups__name'
    ]
    search_fields = [
        'child__first_name', 'child__last_name', 'child__parent__email',
        'program_instance__buildout__program_type__name'
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
