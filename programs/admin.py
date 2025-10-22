from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.conf import settings
from .models import (
    ProgramType, ProgramInstance, RegistrationForm, FormQuestion,
    Child, Registration, Role, ProgramBuildout, Responsibility, 
    BuildoutRoleLine, BuildoutResponsibilityLine, BaseCost, 
    BuildoutBaseCostAssignment, Location, BuildoutLocationAssignment,
    InstanceRoleAssignment, ContractorRoleRate,
    ContractorAvailability, AvailabilityProgram, ProgramSession, SessionBooking,
    ProgramBuildoutScheduling, Holiday, ContractorDayOffRequest, ProgramRequest,
    AvailabilityRule, AvailabilityException, RuleBooking
)
from contracts.services.assignment import assign_contractor_to_buildout


class FormQuestionInline(admin.TabularInline):
    model = FormQuestion
    extra = 1
    ordering = ['order']


class BuildoutResponsibilityLineInline(admin.TabularInline):
    model = BuildoutResponsibilityLine
    extra = 1
    fields = ['responsibility', 'hours', 'calculated_yearly_hours']
    readonly_fields = ['calculated_yearly_hours']

    def calculated_yearly_hours(self, obj):
        if obj.pk:
            return f"{obj.calculate_yearly_hours():.1f} hours"
        return "Save to calculate"
    calculated_yearly_hours.short_description = 'Yearly Hours'


class BuildoutRoleLineInline(admin.TabularInline):
    model = BuildoutRoleLine
    extra = 1
    fields = ['role', 'contractor', 'pay_type', 'pay_value', 'frequency_unit', 'frequency_count', 'hours_per_frequency', 'calculated_yearly_hours', 'calculated_payout']
    readonly_fields = ['calculated_yearly_hours', 'calculated_payout']

    def calculated_yearly_hours(self, obj):
        if obj.pk:
            return f"{obj.calculate_yearly_hours():.1f} hours"
        return "Save to calculate"
    calculated_yearly_hours.short_description = 'Yearly Hours'

    def calculated_payout(self, obj):
        if obj.pk:
            return f"${obj.calculate_payout():.2f}"
        return "Save to calculate"
    calculated_payout.short_description = 'Yearly Payout'


class BuildoutBaseCostAssignmentInline(admin.TabularInline):
    model = BuildoutBaseCostAssignment
    extra = 1
    fields = ['base_cost', 'override_rate', 'override_frequency', 'multiplier', 'calculated_yearly_cost']
    readonly_fields = ['calculated_yearly_cost']
    
    def get_formset(self, request, obj=None, **kwargs):
        from .forms import BuildoutBaseCostAssignmentForm
        kwargs['form'] = BuildoutBaseCostAssignmentForm
        return super().get_formset(request, obj, **kwargs)

    def calculated_yearly_cost(self, obj):
        if obj.pk:
            return f"${obj.calculate_yearly_cost():.2f}"
        return "Save to calculate"
    calculated_yearly_cost.short_description = 'Yearly Cost'


class BuildoutLocationAssignmentInline(admin.TabularInline):
    model = BuildoutLocationAssignment
    extra = 1
    fields = ['location', 'override_rate', 'override_frequency', 'multiplier', 'calculated_yearly_cost']
    readonly_fields = ['calculated_yearly_cost']
    
    def get_formset(self, request, obj=None, **kwargs):
        from .forms import BuildoutLocationAssignmentForm
        kwargs['form'] = BuildoutLocationAssignmentForm
        return super().get_formset(request, obj, **kwargs)

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
    list_display = ['role', 'name', 'frequency_type', 'default_hours', 'description_short']
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


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'default_frequency', 'default_rate', 'max_capacity', 'contact_name', 'is_active']
    list_filter = ['default_frequency', 'is_active', 'max_capacity', 'created_at']
    search_fields = ['name', 'address', 'contact_name', 'contact_email', 'features']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'address', 'description', 'is_active')
        }),
        ('Default Cost Information', {
            'fields': ('default_rate', 'default_frequency')
        }),
        ('Capacity & Features', {
            'fields': ('max_capacity', 'features')
        }),
        ('Contact Information', {
            'fields': ('contact_name', 'contact_phone', 'contact_email'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(ProgramBuildout)
class ProgramBuildoutAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'program_type', 'version_number', 'status', 'assigned_contractor', 'present_to_contractor_button', 'is_active', 'num_facilitators', 
        'total_students_per_year', 'total_revenue_per_year', 'total_yearly_costs'
    ]
    list_filter = ['program_type', 'status', 'is_active', 'is_new_program', 'num_facilitators', 'created_at']
    search_fields = ['title', 'program_type__name', 'assigned_contractor__user__email']
    readonly_fields = [
        'total_students_per_year', 'total_sessions_per_year',
        'total_revenue_per_year', 'total_yearly_costs',
        'created_at', 'updated_at'
    ]
    inlines = [BuildoutResponsibilityLineInline, BuildoutRoleLineInline, BuildoutBaseCostAssignmentInline, BuildoutLocationAssignmentInline]
    actions = ['clone_buildout']

    def total_revenue_per_year(self, obj):
        return f"${obj.total_revenue_per_year:.2f}"
    total_revenue_per_year.short_description = 'Yearly Revenue'

    def total_yearly_costs(self, obj):
        return f"${obj.total_yearly_costs:.2f}"
    total_yearly_costs.short_description = 'Yearly Costs'

    def clone_buildout(self, request, queryset):
        for buildout in queryset:
            buildout.clone()
        self.message_user(request, f"Cloned {queryset.count()} buildout(s)")
    clone_buildout.short_description = "Clone selected buildouts"

    def save_model(self, request, obj, form, change):
        # Enforce assignment gate via service layer if assigned_contractor changed
        if change and 'assigned_contractor' in form.changed_data and obj.assigned_contractor_id:
            contractor = obj.assigned_contractor
            # Clear to avoid direct save bypassing service gate
            obj.assigned_contractor = None
            super().save_model(request, obj, form, change)
            # Now apply via service
            assign_contractor_to_buildout(obj, contractor)
        else:
            super().save_model(request, obj, form, change)

    fieldsets = (
        ('Basic Information', {
            'fields': ('program_type', 'title', 'version_number', 'status', 'assigned_contractor', 'is_active')
        }),
        ('Scoping Parameters', {
            'fields': (
                'is_new_program', 'num_facilitators', 'num_new_facilitators',
                'students_per_program', 'sessions_per_program', 'new_program_concepts_per_year',
                'rate_per_student'
            )
        }),
        ('Calculated Values', {
            'fields': (
                'total_students_per_year', 'total_sessions_per_year',
                'total_revenue_per_year', 'total_yearly_costs'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # --- Custom per-row action to present contract ---
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:buildout_id>/present/',
                self.admin_site.admin_view(self.present_to_contractor_admin),
                name='programbuildout_present_to_contractor',
            ),
        ]
        return custom_urls + urls

    def present_to_contractor_button(self, obj):
        if obj.status == 'ready' and obj.assigned_contractor_id:
            url = reverse('admin:programbuildout_present_to_contractor', args=[obj.id])
            return format_html('<a class="button btn btn-sm btn-success" href="{}">Present</a>', url)
        elif obj.status == 'ready':
            return format_html('<span class="text-muted">Assign contractor</span>')
        return format_html('<span class="text-muted">N/A</span>')
    present_to_contractor_button.short_description = 'Present to Contractor'

    def present_to_contractor_admin(self, request, buildout_id):
        from django.shortcuts import redirect, get_object_or_404
        from django.contrib import messages
        from contracts.models import Contract, LegalDocumentTemplate
        from contracts.services.docusign import DocuSignService

        buildout = get_object_or_404(ProgramBuildout, pk=buildout_id)
        if not request.user.is_staff:
            messages.error(request, 'Permission denied.')
            return redirect('admin:programs_programbuildout_changelist')
        if buildout.status != ProgramBuildout.Status.READY:
            messages.error(request, 'Buildout must be READY to present.')
            return redirect('admin:programs_programbuildout_changelist')
        if not buildout.assigned_contractor_id:
            messages.error(request, 'Assign a contractor before presenting.')
            return redirect('admin:programs_programbuildout_changelist')

        try:
            template = LegalDocumentTemplate.objects.get(key='service_agreement')
        except LegalDocumentTemplate.DoesNotExist:
            messages.error(request, 'Service Agreement template is not configured.')
            return redirect('admin:programs_programbuildout_changelist')

        contractor = buildout.assigned_contractor
        contract = Contract.objects.create(
            contractor=contractor,
            buildout=buildout,
            template_key='service_agreement',
            status='created',
        )
        service = DocuSignService()
        try:
            envelope_id = service.create_envelope(
                template_id=template.docusign_template_id,
                recipient_email=contractor.user.email,
                recipient_name=getattr(contractor.user, 'get_full_name', lambda: contractor.user.email)(),
                merge_fields={
                    'BUILDOUT_TITLE': buildout.title,
                    'CONTRACTOR_EMAIL': contractor.user.email,
                },
                return_url=getattr(settings, 'DOCUSIGN_RETURN_URL', ''),
                webhook_url=getattr(settings, 'DOCUSIGN_WEBHOOK_URL', ''),
            )
            contract.envelope_id = envelope_id
            contract.status = 'sent'
            contract.save(update_fields=['envelope_id', 'status'])
            try:
                buildout.mark_awaiting_signatures()
            except Exception:
                buildout.status = ProgramBuildout.Status.AWAITING_SIGNATURES
                buildout.save(update_fields=['status'])
            messages.success(request, 'Contract presented to contractor.')
        except Exception as e:
            messages.error(request, f'Failed to send contract: {e}')

        return redirect('admin:programs_programbuildout_changelist')


@admin.register(BuildoutResponsibilityLine)
class BuildoutResponsibilityLineAdmin(admin.ModelAdmin):
    list_display = [
        'buildout', 'responsibility', 'hours', 'calculated_yearly_hours'
    ]
    list_filter = ['responsibility__frequency_type', 'responsibility__role', 'buildout__program_type']
    search_fields = ['responsibility__name', 'responsibility__role__title', 'buildout__title']
    readonly_fields = ['calculated_yearly_hours', 'created_at', 'updated_at']

    def calculated_yearly_hours(self, obj):
        if obj.pk:
            return f"{obj.calculate_yearly_hours():.1f} hours"
        return "Save to calculate"
    calculated_yearly_hours.short_description = 'Yearly Hours'


@admin.register(BuildoutRoleLine)
class BuildoutRoleLineAdmin(admin.ModelAdmin):
    list_display = [
        'buildout', 'role', 'contractor', 'pay_type', 'pay_value', 'calculated_yearly_hours', 'calculated_payout'
    ]
    list_filter = ['role', 'buildout__program_type', 'pay_type', 'contractor']
    search_fields = ['role__title', 'buildout__title', 'contractor__email']
    readonly_fields = ['calculated_yearly_hours', 'calculated_payout', 'created_at', 'updated_at']

    def calculated_yearly_hours(self, obj):
        if obj.pk:
            return f"{obj.calculate_yearly_hours():.1f} hours"
        return "Save to calculate"
    calculated_yearly_hours.short_description = 'Yearly Hours'

    def calculated_payout(self, obj):
        if obj.pk:
            return f"${obj.calculate_payout():.2f}"
        return "Save to calculate"
    calculated_payout.short_description = 'Yearly Payout'


@admin.register(ContractorRoleRate)
class ContractorRoleRateAdmin(admin.ModelAdmin):
    list_display = ['contractor', 'role', 'pay_type', 'pay_value']
    list_filter = ['pay_type', 'role', 'contractor']
    search_fields = ['contractor__email', 'role__title']
    ordering = ['contractor__email', 'role__title']
    readonly_fields = ['created_at', 'updated_at']


# Legacy models are no longer registered in admin - they are kept for backward compatibility only


@admin.register(BuildoutBaseCostAssignment)
class BuildoutBaseCostAssignmentAdmin(admin.ModelAdmin):
    list_display = ['buildout', 'base_cost', 'effective_rate', 'effective_frequency', 'multiplier', 'calculated_yearly_cost']
    list_filter = ['base_cost__frequency', 'override_frequency', 'buildout__program_type']
    search_fields = ['base_cost__name', 'buildout__title']
    readonly_fields = ['calculated_yearly_cost', 'created_at']

    def effective_rate(self, obj):
        if obj.override_rate is not None:
            return format_html('<span style="color: #856404; font-weight: bold;">${:.2f}</span>', obj.override_rate)
        else:
            return format_html('<span style="color: #6c757d;">${:.2f}</span>', obj.base_cost.rate)
    effective_rate.short_description = 'Rate'

    def effective_frequency(self, obj):
        if obj.override_frequency:
            display_value = dict(obj._meta.get_field('override_frequency').choices)[obj.override_frequency]
            return format_html('<span style="color: #856404; font-weight: bold;">{}</span>', display_value)
        else:
            return format_html('<span style="color: #6c757d;">{}</span>', obj.base_cost.get_frequency_display())
    effective_frequency.short_description = 'Frequency'

    def calculated_yearly_cost(self, obj):
        if obj.pk:
            return f"${obj.calculate_yearly_cost():.2f}"
        return "Save to calculate"
    calculated_yearly_cost.short_description = 'Yearly Cost'


@admin.register(BuildoutLocationAssignment)
class BuildoutLocationAssignmentAdmin(admin.ModelAdmin):
    list_display = ['buildout', 'location', 'effective_rate', 'effective_frequency', 'multiplier', 'calculated_yearly_cost']
    list_filter = ['location__default_frequency', 'override_frequency', 'buildout__program_type']
    search_fields = ['location__name', 'buildout__title']
    readonly_fields = ['calculated_yearly_cost', 'created_at']

    def effective_rate(self, obj):
        if obj.override_rate is not None:
            return format_html('<span style="color: #856404; font-weight: bold;">${:.2f}</span>', obj.override_rate)
        else:
            return format_html('<span style="color: #6c757d;">${:.2f}</span>', obj.location.default_rate)
    effective_rate.short_description = 'Rate'

    def effective_frequency(self, obj):
        if obj.override_frequency:
            display_value = dict(obj._meta.get_field('override_frequency').choices)[obj.override_frequency]
            return format_html('<span style="color: #856404; font-weight: bold;">{}</span>', display_value)
        else:
            return format_html('<span style="color: #6c757d;">{}</span>', obj.location.get_default_frequency_display())
    effective_frequency.short_description = 'Frequency'

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


# ============================================================================
# ENHANCED SCHEDULING ADMIN
# ============================================================================

class AvailabilityProgramInline(admin.TabularInline):
    model = AvailabilityProgram
    extra = 1
    fields = ['program_buildout', 'session_duration_hours', 'max_sessions']


class ProgramSessionInline(admin.TabularInline):
    model = ProgramSession
    extra = 0
    fields = ['start_datetime', 'end_datetime', 'duration_hours', 'max_capacity', 'enrolled_count', 'status']
    readonly_fields = ['enrolled_count']


class SessionBookingInline(admin.TabularInline):
    model = SessionBooking
    extra = 0
    fields = ['child', 'status', 'booked_at', 'parent_notes']
    readonly_fields = ['booked_at']


@admin.register(ContractorAvailability)
class ContractorAvailabilityAdmin(admin.ModelAdmin):
    list_display = [
        'contractor', 'start_datetime', 'end_datetime', 'duration_hours', 
        'remaining_hours', 'status', 'program_count'
    ]
    list_filter = ['status', 'start_datetime', 'contractor']
    search_fields = ['contractor__email', 'contractor__first_name', 'contractor__last_name', 'notes']
    readonly_fields = ['duration_hours', 'remaining_hours', 'created_at', 'updated_at']
    inlines = [AvailabilityProgramInline]
    date_hierarchy = 'start_datetime'

    def program_count(self, obj):
        return obj.program_offerings.count()
    program_count.short_description = 'Programs'

    fieldsets = (
        ('Availability Details', {
            'fields': ('contractor', 'start_datetime', 'end_datetime', 'status')
        }),
        ('Calculated Values', {
            'fields': ('duration_hours', 'remaining_hours'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(AvailabilityProgram)
class AvailabilityProgramAdmin(admin.ModelAdmin):
    list_display = [
        'availability', 'program_buildout', 'session_duration_hours', 
        'max_sessions', 'total_possible_hours', 'session_count'
    ]
    list_filter = ['session_duration_hours', 'max_sessions', 'availability__contractor', 'program_buildout__program_type']
    search_fields = ['program_buildout__title', 'availability__contractor__email']
    readonly_fields = ['total_possible_hours', 'created_at']

    def session_count(self, obj):
        return obj.sessions.count()
    session_count.short_description = 'Sessions'


@admin.register(ProgramSession)
class ProgramSessionAdmin(admin.ModelAdmin):
    list_display = [
        'program_instance', 'contractor', 'start_datetime', 'duration_hours',
        'enrollment_status', 'status', 'available_spots'
    ]
    list_filter = ['status', 'start_datetime', 'availability_program__availability__contractor']
    search_fields = [
        'program_instance__title', 'availability_program__availability__contractor__email',
        'availability_program__program_buildout__title'
    ]
    readonly_fields = ['available_spots', 'contractor', 'created_at', 'updated_at']
    inlines = [SessionBookingInline]
    date_hierarchy = 'start_datetime'

    def contractor(self, obj):
        return obj.availability_program.availability.contractor
    contractor.short_description = 'Contractor'

    def enrollment_status(self, obj):
        return f"{obj.enrolled_count}/{obj.max_capacity}"
    enrollment_status.short_description = 'Enrollment'

    fieldsets = (
        ('Session Details', {
            'fields': ('program_instance', 'availability_program', 'status')
        }),
        ('Schedule', {
            'fields': ('start_datetime', 'end_datetime', 'duration_hours')
        }),
        ('Capacity', {
            'fields': ('max_capacity', 'enrolled_count', 'available_spots')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(SessionBooking)
class SessionBookingAdmin(admin.ModelAdmin):
    list_display = [
        'child', 'session_title', 'session_datetime', 'contractor', 
        'status', 'booked_at', 'can_cancel'
    ]
    list_filter = ['status', 'booked_at', 'session__start_datetime']
    search_fields = [
        'child__first_name', 'child__last_name', 'child__parent__email',
        'session__program_instance__title'
    ]
    readonly_fields = ['booked_at', 'updated_at', 'can_cancel', 'parent']
    date_hierarchy = 'booked_at'

    def session_title(self, obj):
        return obj.session.program_instance.title
    session_title.short_description = 'Session'

    def session_datetime(self, obj):
        return obj.session.start_datetime.strftime('%Y-%m-%d %H:%M')
    session_datetime.short_description = 'Date & Time'

    def contractor(self, obj):
        return obj.session.contractor
    contractor.short_description = 'Contractor'

    def parent(self, obj):
        return obj.child.parent.email
    parent.short_description = 'Parent Email'

    fieldsets = (
        ('Booking Details', {
            'fields': ('session', 'child', 'status')
        }),
        ('Additional Info', {
            'fields': ('parent_notes', 'form_responses'),
            'classes': ('collapse',)
        }),
        ('Booking Status', {
            'fields': ('can_cancel', 'parent'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('booked_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


# ============================================================================
# HOLIDAY AND TIME-OFF ADMIN
# ============================================================================

@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ['name', 'date', 'is_recurring', 'description']
    list_filter = ['is_recurring']
    search_fields = ['name', 'description']
    date_hierarchy = 'date'
    ordering = ['date']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'date', 'is_recurring')
        }),
        ('Details', {
            'fields': ('description',),
            'classes': ('collapse',)
        })
    )


@admin.register(ContractorDayOffRequest)
class ContractorDayOffRequestAdmin(admin.ModelAdmin):
    list_display = [
        'contractor', 'start_date', 'end_date', 'status', 'affected_sessions_count', 
        'affected_bookings_count', 'reviewed_by', 'created_at'
    ]
    list_filter = ['status', 'start_date', 'created_at']
    search_fields = ['contractor__first_name', 'contractor__last_name', 'contractor__email', 'reason']
    date_hierarchy = 'start_date'
    readonly_fields = ['affected_sessions_count', 'affected_bookings_count', 'reviewed_at', 'created_at', 'updated_at']
    
    actions = ['approve_requests', 'deny_requests', 'check_conflicts']
    
    fieldsets = (
        ('Request Details', {
            'fields': ('contractor', 'start_date', 'end_date', 'reason', 'status')
        }),
        ('Admin Review', {
            'fields': ('reviewed_by', 'reviewed_at', 'admin_notes'),
            'classes': ('collapse',)
        }),
        ('Conflict Information', {
            'fields': ('affected_sessions_count', 'affected_bookings_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def approve_requests(self, request, queryset):
        """Admin action to approve selected day-off requests."""
        approved_count = 0
        for day_off_request in queryset.filter(status='pending'):
            day_off_request.approve(request.user, "Approved via admin action")
            approved_count += 1
        
        self.message_user(
            request,
            f"Successfully approved {approved_count} day-off requests."
        )
    approve_requests.short_description = "Approve selected requests"
    
    def deny_requests(self, request, queryset):
        """Admin action to deny selected day-off requests."""
        denied_count = 0
        for day_off_request in queryset.filter(status='pending'):
            day_off_request.status = 'denied'
            day_off_request.reviewed_by = request.user
            day_off_request.reviewed_at = timezone.now()
            day_off_request.save()
            denied_count += 1
        
        self.message_user(
            request,
            f"Successfully denied {denied_count} day-off requests."
        )
    deny_requests.short_description = "Deny selected requests"
    
    def check_conflicts(self, request, queryset):
        """Admin action to check conflicts for selected requests."""
        for day_off_request in queryset:
            day_off_request.check_conflicts()
        
        self.message_user(
            request,
            f"Updated conflict information for {queryset.count()} requests."
        )
    check_conflicts.short_description = "Check conflicts for selected requests"

    actions = ['confirm_bookings', 'cancel_bookings']

    def confirm_bookings(self, request, queryset):
        confirmed = 0
        for booking in queryset:
            if booking.confirm_booking():
                confirmed += 1
        self.message_user(request, f"Confirmed {confirmed} booking(s)")
    confirm_bookings.short_description = "Confirm selected bookings"

    def cancel_bookings(self, request, queryset):
        cancelled = 0
        for booking in queryset:
            if booking.cancel_booking():
                cancelled += 1
        self.message_user(request, f"Cancelled {cancelled} booking(s)")
    cancel_bookings.short_description = "Cancel selected bookings"


@admin.register(ProgramBuildoutScheduling)
class ProgramBuildoutSchedulingAdmin(admin.ModelAdmin):
    list_display = [
        'buildout', 'default_session_duration', 'max_students_per_session',
        'requires_advance_booking', 'advance_booking_hours'
    ]
    list_filter = ['requires_advance_booking', 'default_session_duration', 'max_students_per_session']
    search_fields = ['buildout__title', 'buildout__program_type__name']

    fieldsets = (
        ('Program Reference', {
            'fields': ('buildout',)
        }),
        ('Session Duration Settings', {
            'fields': ('default_session_duration', 'min_session_duration', 'max_session_duration')
        }),
        ('Capacity Settings', {
            'fields': ('max_students_per_session',)
        }),
        ('Booking Requirements', {
            'fields': ('requires_advance_booking', 'advance_booking_hours')
        })
    )


@admin.register(ProgramRequest)
class ProgramRequestAdmin(admin.ModelAdmin):
    """Admin interface for program requests."""
    list_display = [
        'program_type', 'contact_name', 'request_type', 'status', 
        'created_at', 'reviewed_by'
    ]
    list_filter = ['request_type', 'status', 'created_at', 'program_type']
    search_fields = ['contact_name', 'contact_email', 'program_type__name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Request Information', {
            'fields': ('request_type', 'program_type', 'status')
        }),
        ('Contact Details', {
            'fields': ('contact_name', 'contact_email', 'contact_phone', 'requester')
        }),
        ('Program Details', {
            'fields': ('preferred_location', 'preferred_dates', 'expected_participants', 'additional_notes')
        }),
        ('Contractor Information', {
            'fields': ('contractor_experience', 'proposed_location'),
            'classes': ('collapse',)
        }),
        ('Administration', {
            'fields': ('admin_notes', 'reviewed_by', 'reviewed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Make certain fields readonly based on status and user permissions."""
        readonly = ['created_at', 'updated_at']
        if obj and obj.status in ['approved', 'completed', 'rejected']:
            # Lock down key fields once processed
            readonly.extend(['request_type', 'program_type', 'contact_name', 'contact_email'])
        return readonly
    
    def save_model(self, request, obj, form, change):
        """Auto-set reviewed_by and reviewed_at when status changes."""
        if change and 'status' in form.changed_data:
            if obj.status != 'pending':
                obj.reviewed_by = request.user
                obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(RuleBooking)
class RuleBookingAdmin(admin.ModelAdmin):
    """Admin interface for rule-based bookings."""
    list_display = [
        'id', 'rule', 'program', 'booking_date', 'time_range', 
        'child', 'booked_by', 'status', 'created_at'
    ]
    list_filter = ['status', 'booking_date', 'rule__contractor']
    search_fields = [
        'program__title', 'child__first_name', 'child__last_name',
        'booked_by__email', 'rule__title'
    ]
    readonly_fields = ['duration_minutes', 'created_at', 'updated_at']
    date_hierarchy = 'booking_date'
    
    def time_range(self, obj):
        return f"{obj.start_time.strftime('%H:%M')} - {obj.end_time.strftime('%H:%M')}"
    time_range.short_description = 'Time'
    
    fieldsets = (
        ('Booking Details', {
            'fields': ('rule', 'program', 'booking_date', 'start_time', 'end_time')
        }),
        ('Participant', {
            'fields': ('booked_by', 'child', 'status')
        }),
        ('Additional Info', {
            'fields': ('notes', 'duration_minutes')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
