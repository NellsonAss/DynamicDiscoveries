from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q, Count, F
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.forms import modelformset_factory
from django.db import transaction
import json
from decimal import Decimal

from .models import (
    ProgramType, ProgramInstance, RegistrationForm, FormQuestion,
    Child, Registration, Role, Responsibility, ProgramBuildout, 
    BuildoutResponsibilityAssignment, BuildoutRoleAssignment, BaseCost, 
    BuildoutBaseCostAssignment, InstanceRoleAssignment,
    ContractorAvailability, AvailabilityProgram, ProgramSession, SessionBooking,
    ProgramBuildoutScheduling, ContractorDayOffRequest
)
from .forms import (
    ChildForm, RegistrationFormForm,
    FormQuestionForm, ProgramInstanceForm,
    ContractorAvailabilityForm, AvailabilityProgramForm, SessionBookingForm,
    ProgramSessionForm, ProgramBuildoutSchedulingForm, AvailabilityProgramFormSet,
    ContractorDayOffRequestForm
)

User = get_user_model()


def user_has_role(user, role_name):
    """Check if user has a specific role."""
    return user.groups.filter(name=role_name).exists()


def user_is_parent(user):
    """Check if user is a parent."""
    return user_has_role(user, 'Parent')


def user_is_contractor(user):
    """Check if user is a contractor."""
    return user_has_role(user, 'Contractor')


def user_is_admin(user):
    """Check if user is an admin."""
    return user_has_role(user, 'Admin') or user.is_staff


@login_required
def parent_dashboard(request):
    """Parent dashboard showing programs and registrations."""
    if not user_is_parent(request.user):
        messages.error(request, "Access denied. Parent role required.")
        return redirect('dashboard:dashboard')
    
    # Get active/upcoming programs
    now = timezone.now()
    active_programs = ProgramInstance.objects.filter(
        is_active=True,
        start_date__gte=now
    ).order_by('start_date')
    
    # Get user's children
    children = request.user.children.all()
    
    # Get registrations for user's children
    registrations = Registration.objects.filter(
        child__parent=request.user
    ).select_related('child', 'program_instance', 'program_instance__buildout__program_type')
    
    # Separate current and past registrations
    current_registrations = registrations.filter(
        program_instance__end_date__gte=now,
        status__in=['pending', 'approved']
    )
    past_registrations = registrations.filter(
        program_instance__end_date__lt=now
    )
    
    context = {
        'active_programs': active_programs,
        'children': children,
        'current_registrations': current_registrations,
        'past_registrations': past_registrations,
    }
    
    return render(request, 'programs/parent_dashboard.html', context)


@login_required
def program_instance_detail(request, pk):
    """Show program instance details and registration form."""
    program_instance = get_object_or_404(ProgramInstance, pk=pk, is_active=True)
    
    # Check if user can register
    can_register = False
    if user_is_parent(request.user):
        can_register = (
            request.user.children.exists() and
            not program_instance.is_full and
            program_instance.start_date > timezone.now()
        )
    
    # Get existing registration if user is parent
    existing_registration = None
    if user_is_parent(request.user):
        existing_registration = Registration.objects.filter(
            child__parent=request.user,
            program_instance=program_instance
        ).first()
    
    context = {
        'program_instance': program_instance,
        'can_register': can_register,
        'existing_registration': existing_registration,
    }
    
    return render(request, 'programs/program_instance_detail.html', context)


@login_required
def register_child(request, program_instance_pk):
    """Register a child for a program instance."""
    if not user_is_parent(request.user):
        messages.error(request, "Access denied. Parent role required.")
        return redirect('dashboard:dashboard')
    
    program_instance = get_object_or_404(ProgramInstance, pk=program_instance_pk, is_active=True)
    
    # Check if program is full or past start date
    if program_instance.is_full:
        messages.error(request, "This program is full.")
        return redirect('programs:program_instance_detail', pk=program_instance_pk)
    
    if program_instance.start_date <= timezone.now():
        messages.error(request, "Registration is closed for this program.")
        return redirect('programs:program_instance_detail', pk=program_instance_pk)
    
    # Check if already registered
    existing_registration = Registration.objects.filter(
        child__parent=request.user,
        program_instance=program_instance
    ).first()
    
    if existing_registration:
        messages.warning(request, "You are already registered for this program.")
        return redirect('programs:program_instance_detail', pk=program_instance_pk)
    
    if request.method == 'POST':
        child_pk = request.POST.get('child')
        if child_pk:
            try:
                child = request.user.children.get(pk=child_pk)
                
                # Create registration
                registration = Registration.objects.create(
                    child=child,
                    program_instance=program_instance,
                    status='pending'
                )
                
                messages.success(request, f"Successfully registered {child.full_name} for {program_instance.buildout.program_type.name}.")
                
                # Redirect to form completion if form is assigned
                if program_instance.assigned_form:
                    return redirect('programs:complete_registration_form', registration_pk=registration.pk)
                else:
                    return redirect('programs:parent_dashboard')
                    
            except Child.DoesNotExist:
                messages.error(request, "Invalid child selected.")
        else:
            messages.error(request, "Please select a child to register.")
    
    # Get user's children
    children = request.user.children.all()
    
    context = {
        'program_instance': program_instance,
        'children': children,
    }
    
    return render(request, 'programs/register_child.html', context)


@login_required
def complete_registration_form(request, registration_pk):
    """Complete registration form for a registration."""
    if not user_is_parent(request.user):
        messages.error(request, "Access denied. Parent role required.")
        return redirect('dashboard')
    
    registration = get_object_or_404(
        Registration, 
        pk=registration_pk, 
        child__parent=request.user
    )
    
    if not registration.program_instance.assigned_form:
        messages.error(request, "No form assigned to this program.")
        return redirect('programs:parent_dashboard')
    
    if request.method == 'POST':
        form_data = {}
        for key, value in request.POST.items():
            if key.startswith('question_'):
                question_id = key.replace('question_', '')
                form_data[question_id] = value
        
        registration.form_responses = form_data
        registration.save()
        
        messages.success(request, "Registration form completed successfully!")
        return redirect('programs:parent_dashboard')
    
    # Get form questions
    form = registration.program_instance.assigned_form
    questions = form.questions.all()
    
    context = {
        'registration': registration,
        'form': form,
        'questions': questions,
    }
    
    return render(request, 'programs/complete_registration_form.html', context)


@login_required
def contractor_dashboard(request):
    """Contractor dashboard showing programs and forms."""
    if not (user_is_contractor(request.user) or user_is_admin(request.user)):
        messages.error(request, "Access denied. Contractor or Admin role required.")
        return redirect('dashboard')
    # Load contractor for banner/gating on actions (no redirect)
    contractor = None
    if user_is_contractor(request.user):
        try:
            from people.models import Contractor as ContractorModel
            contractor = ContractorModel.objects.filter(user=request.user).first()
        except Exception:
            contractor = None
    
    # Get programs where user is assigned as a contractor
    if user_is_contractor(request.user):
        programs = ProgramInstance.objects.filter(
            contractor_assignments__contractor=request.user,
            is_active=True
        ).distinct().order_by('-start_date')
    else:
        # Admin can see all programs
        programs = ProgramInstance.objects.filter(
            is_active=True
        ).order_by('-start_date')
    
    # Get forms created by user
    forms = RegistrationForm.objects.filter(
        created_by=request.user,
        is_active=True
    ).order_by('-created_at')
    
    context = {
        'program_instances': programs,
        'forms': forms,
        'contractor': contractor,
    }
    
    return render(request, 'programs/contractor_dashboard.html', context)


@login_required
def buildout_mark_ready(request, buildout_pk):
    if request.method != 'POST':
        return redirect('programs:buildout_detail', buildout_pk=buildout_pk)
    buildout = get_object_or_404(ProgramBuildout, pk=buildout_pk)
    try:
        buildout.mark_ready()
        messages.success(request, 'Buildout marked as Ready.')
    except Exception as e:
        messages.error(request, f'Cannot mark Ready: {e}')
    return redirect('programs:buildout_detail', buildout_pk=buildout_pk)


@login_required
def present_to_contractor(request, buildout_pk):
    if request.method != 'POST':
        return redirect('programs:buildout_detail', buildout_pk=buildout_pk)
    buildout = get_object_or_404(ProgramBuildout, pk=buildout_pk)
    if not buildout.assigned_contractor_id:
        messages.error(request, 'Assign a contractor before presenting.')
        return redirect('programs:buildout_detail', buildout_pk=buildout_pk)
    from contracts.models import Contract, LegalDocumentTemplate
    from contracts.services.docusign import DocuSignService
    contractor = buildout.assigned_contractor
    try:
        template = LegalDocumentTemplate.objects.get(key='service_agreement')
    except LegalDocumentTemplate.DoesNotExist:
        messages.error(request, 'Service Agreement template is not configured.')
        return redirect('programs:buildout_detail', buildout_pk=buildout_pk)
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
            return_url=settings.DOCUSIGN_RETURN_URL,
            webhook_url=settings.DOCUSIGN_WEBHOOK_URL,
        )
        contract.envelope_id = envelope_id
        contract.status = 'sent'
        contract.save(update_fields=['envelope_id', 'status'])
        try:
            buildout.mark_awaiting_signatures()
        except Exception:
            buildout.status = buildout.Status.AWAITING_SIGNATURES
            buildout.save(update_fields=['status'])
        messages.success(request, 'Contract presented to contractor.')
    except Exception as e:
        messages.error(request, f'Failed to send contract: {e}')
    return redirect('programs:buildout_detail', buildout_pk=buildout_pk)


@login_required
def buildout_review(request, buildout_pk):
    buildout = get_object_or_404(ProgramBuildout, pk=buildout_pk)
    # Contractor must be assigned and match current user or be admin
    if user_is_contractor(request.user) and not user_is_admin(request.user):
        if not buildout.assigned_contractor or buildout.assigned_contractor.user != request.user:
            messages.error(request, 'You are not assigned to this buildout.')
            return redirect('programs:contractor_dashboard')
    return render(request, 'programs/partials/buildout_review.html', { 'buildout': buildout })


@login_required
def buildout_agree_and_sign(request, buildout_pk):
    if request.method != 'POST':
        return redirect('programs:buildout_review', buildout_pk=buildout_pk)
    buildout = get_object_or_404(ProgramBuildout, pk=buildout_pk)
    if not buildout.assigned_contractor_id:
        messages.error(request, 'No contractor assigned.')
        return redirect('programs:buildout_review', buildout_pk=buildout_pk)
    contractor_user = buildout.assigned_contractor.user
    if user_is_contractor(request.user) and not user_is_admin(request.user):
        if contractor_user != request.user:
            messages.error(request, 'You are not assigned to this buildout.')
            return redirect('programs:contractor_dashboard')

    # Simple ack fallback
    if getattr(settings, 'USE_SIMPLE_ACK', False):
        name = request.POST.get('typed_name')
        agreed = request.POST.get('agree') == 'on'
        if not (name and agreed):
            messages.error(request, 'Please type your name and check the agreement box.')
            return redirect('programs:buildout_review', buildout_pk=buildout_pk)
        try:
            buildout.mark_awaiting_signatures()
            buildout.mark_active()
        except Exception:
            buildout.status = buildout.Status.ACTIVE
            buildout.save(update_fields=['status'])
        messages.success(request, 'Agreement recorded. Buildout activated.')
        return redirect('programs:buildout_detail', buildout_pk=buildout_pk)

    # Normal DocuSign path
    from contracts.models import Contract, LegalDocumentTemplate
    from contracts.services.docusign import DocuSignService
    try:
        template = LegalDocumentTemplate.objects.get(key='service_agreement')
    except LegalDocumentTemplate.DoesNotExist:
        messages.error(request, 'Service Agreement template is not configured.')
        return redirect('programs:buildout_review', buildout_pk=buildout_pk)
    contract = Contract.objects.create(
        contractor=buildout.assigned_contractor,
        buildout=buildout,
        template_key='service_agreement',
        status='created',
    )
    service = DocuSignService()
    try:
        envelope_id = service.create_envelope(
            template_id=template.docusign_template_id,
            recipient_email=contractor_user.email,
            recipient_name=getattr(contractor_user, 'get_full_name', lambda: contractor_user.email)(),
            merge_fields={
                'BUILDOUT_TITLE': buildout.title,
                'CONTRACTOR_EMAIL': contractor_user.email,
            },
            return_url=settings.DOCUSIGN_RETURN_URL,
            webhook_url=settings.DOCUSIGN_WEBHOOK_URL,
        )
        contract.envelope_id = envelope_id
        contract.status = 'sent'
        contract.save(update_fields=['envelope_id', 'status'])
        try:
            buildout.mark_awaiting_signatures()
        except Exception:
            buildout.status = buildout.Status.AWAITING_SIGNATURES
            buildout.save(update_fields=['status'])
        messages.success(request, 'Agreement sent for signature.')
    except Exception as e:
        messages.error(request, f'Failed to send contract: {e}')
    return redirect('programs:buildout_detail', buildout_pk=buildout_pk)


@login_required
def form_builder(request, form_pk=None):
    """Form builder for creating and editing registration forms."""
    if not (user_is_contractor(request.user) or user_is_admin(request.user)):
        messages.error(request, "Access denied. Contractor or Admin role required.")
        return redirect('dashboard')
    
    form_instance = None
    if form_pk:
        form_instance = get_object_or_404(RegistrationForm, pk=form_pk, created_by=request.user)
    
    if request.method == 'POST':
        form = RegistrationFormForm(request.POST, instance=form_instance)
        if form.is_valid():
            form_instance = form.save(commit=False)
            form_instance.created_by = request.user
            form_instance.save()
            
            messages.success(request, f"Form '{form_instance.title}' saved successfully!")
            return redirect('programs:form_builder', form_pk=form_instance.pk)
    else:
        form = RegistrationFormForm(instance=form_instance)
    
    # Get all forms by user
    forms = RegistrationForm.objects.filter(created_by=request.user).order_by('-created_at')
    
    context = {
        'form': form,
        'forms': forms,
        'current_form': form_instance,
    }
    
    return render(request, 'programs/form_builder.html', context)


@login_required
def add_form_question(request, form_pk):
    """Add a question to a form via HTMX."""
    if not (user_is_contractor(request.user) or user_is_admin(request.user)):
        return HttpResponse("Access denied", status=403)
    
    form = get_object_or_404(RegistrationForm, pk=form_pk, created_by=request.user)
    
    if request.method == 'POST':
        question_form = FormQuestionForm(request.POST)
        if question_form.is_valid():
            question = question_form.save(commit=False)
            question.form = form
            question.save()
            
            return render(request, 'programs/partials/question_item.html', {
                'question': question,
                'form': form
            })
    
    return HttpResponse("Invalid request", status=400)


@login_required
def delete_form_question(request, question_pk):
    """Delete a question from a form via HTMX."""
    if not (user_is_contractor(request.user) or user_is_admin(request.user)):
        return HttpResponse("Access denied", status=403)
    
    question = get_object_or_404(FormQuestion, pk=question_pk, form__created_by=request.user)
    question.delete()
    
    return HttpResponse("Question deleted")


@login_required
def duplicate_form(request, form_pk):
    """Duplicate a form."""
    if not (user_is_contractor(request.user) or user_is_admin(request.user)):
        messages.error(request, "Access denied. Contractor or Admin role required.")
        return redirect('programs:form_builder')
    
    original_form = get_object_or_404(RegistrationForm, pk=form_pk, created_by=request.user)
    new_form = original_form.duplicate()
    
    messages.success(request, f"Form '{original_form.title}' duplicated successfully!")
    return redirect('programs:form_builder', form_pk=new_form.pk)


@login_required
def manage_children(request):
    """Manage children for parent users."""
    if not user_is_parent(request.user):
        messages.error(request, "Access denied. Parent role required.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = ChildForm(request.POST)
        if form.is_valid():
            child = form.save(commit=False)
            child.parent = request.user
            child.save()
            
            messages.success(request, f"Child '{child.full_name}' added successfully!")
            return redirect('programs:manage_children')
    else:
        form = ChildForm()
    
    children = request.user.children.all()
    
    context = {
        'form': form,
        'children': children,
    }
    
    return render(request, 'programs/manage_children.html', context)


@login_required
def edit_child(request, child_pk):
    """Edit a child's information."""
    if not user_is_parent(request.user):
        messages.error(request, "Access denied. Parent role required.")
        return redirect('dashboard')
    
    child = get_object_or_404(Child, pk=child_pk, parent=request.user)
    
    if request.method == 'POST':
        form = ChildForm(request.POST, instance=child)
        if form.is_valid():
            form.save()
            messages.success(request, f"Child '{child.full_name}' updated successfully!")
            return redirect('programs:manage_children')
    else:
        form = ChildForm(instance=child)
    
    context = {
        'form': form,
        'child': child,
    }
    
    return render(request, 'programs/edit_child.html', context)


@login_required
def view_registrations(request, program_instance_pk):
    """View registrations for a program instance."""
    if not (user_is_contractor(request.user) or user_is_admin(request.user)):
        messages.error(request, "Access denied. Contractor or Admin role required.")
        return redirect('dashboard')
    
    program_instance = get_object_or_404(ProgramInstance, pk=program_instance_pk)
    
    # Check if user is assigned to this program or is admin
    if user_is_contractor(request.user) and not program_instance.contractor_assignments.filter(contractor=request.user).exists():
        messages.error(request, "Access denied. You can only view registrations for programs you are assigned to.")
        return redirect('programs:contractor_dashboard')
    
    registrations = program_instance.registrations.all().select_related(
        'child', 'child__parent'
    ).order_by('registered_at')
    
    context = {
        'program_instance': program_instance,
        'registrations': registrations,
    }
    
    return render(request, 'programs/view_registrations.html', context)


@login_required
def update_registration_status(request, registration_pk):
    """Update registration status via HTMX."""
    if not (user_is_contractor(request.user) or user_is_admin(request.user)):
        return HttpResponse("Access denied", status=403)
    
    registration = get_object_or_404(Registration, pk=registration_pk)
    
    # Check if user is instructor or admin
    if user_is_contractor(request.user) and registration.program_instance.instructor != request.user:
        return HttpResponse("Access denied", status=403)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['pending', 'approved', 'rejected', 'cancelled']:
            registration.status = new_status
            registration.save()
            
            return render(request, 'programs/partials/registration_status.html', {
                'registration': registration
            })
    
    return HttpResponse("Invalid request", status=400)


@login_required
def send_form_to_participants(request, program_instance_pk):
    """Send registration form to participants."""
    if not (user_is_contractor(request.user) or user_is_admin(request.user)):
        messages.error(request, "Access denied. Contractor or Admin role required.")
        return redirect('programs:contractor_dashboard')
    
    program_instance = get_object_or_404(ProgramInstance, pk=program_instance_pk)
    
    # Check if user is assigned to this program or is admin
    if user_is_contractor(request.user) and not program_instance.contractor_assignments.filter(contractor=request.user).exists():
        messages.error(request, "Access denied. You can only send forms for programs you are assigned to.")
        return redirect('programs:contractor_dashboard')
    
    if not program_instance.assigned_form:
        messages.error(request, "No form assigned to this program.")
        return redirect('programs:view_registrations', program_instance_pk=program_instance_pk)
    
    # Get registrations that need form completion
    registrations = program_instance.registrations.filter(
        status='approved',
        form_responses__isnull=True
    )
    
    if not registrations.exists():
        messages.info(request, "All approved registrations have completed their forms.")
        return redirect('programs:view_registrations', program_instance_pk=program_instance_pk)
    
    # Here you would typically send emails to participants
    # For now, we'll just show a success message
    messages.success(request, f"Form sent to {registrations.count()} participants.")
    
    return redirect('programs:view_registrations', program_instance_pk=program_instance_pk)


# Program Buildout Views

@login_required
def role_list(request):
    """List all roles for Admin users."""
    if not user_is_admin(request.user):
        messages.error(request, "Access denied. Admin role required.")
        return redirect('dashboard')
    
    roles = Role.objects.all().order_by('title')  # Changed from 'name' to 'title'
    
    context = {
        'roles': roles,
    }
    
    return render(request, 'programs/role_list.html', context)


@login_required
def buildout_list(request):
    """List program buildouts for Admin and Contractor users."""
    if not (user_is_admin(request.user) or user_is_contractor(request.user)):
        messages.error(request, "Access denied. Admin or Contractor role required.")
        return redirect('dashboard')
    
    if user_is_admin(request.user):
        # Admins see all buildouts
        buildouts = ProgramBuildout.objects.select_related('program_type').all().order_by('program_type__name', 'title')
    else:
        # Contractors see only buildouts they're assigned to
        buildouts = ProgramBuildout.objects.filter(
            role_lines__contractor=request.user
        ).select_related('program_type').distinct().order_by('program_type__name', 'title')
    
    context = {
        'buildouts': buildouts,
        'is_contractor_view': user_is_contractor(request.user) and not user_is_admin(request.user),
    }
    
    return render(request, 'programs/buildout_list.html', context)


@login_required
def buildout_detail(request, buildout_pk):
    """Show detailed view of a program buildout with Excel-like structure."""
    if not (user_is_admin(request.user) or user_is_contractor(request.user)):
        messages.error(request, "Access denied. Admin or Contractor role required.")
        return redirect('dashboard')
    
    buildout = get_object_or_404(ProgramBuildout, pk=buildout_pk)
    
    # Check if contractor has access to this buildout
    if user_is_contractor(request.user) and not user_is_admin(request.user):
        if not buildout.role_lines.filter(contractor=request.user).exists():
            messages.error(request, "Access denied. You are not assigned to this buildout.")
            return redirect('programs:buildout_list')
    
    # Calculate summary statistics using the new model structure
    total_hours = sum(
        buildout.calculate_total_hours_per_role(role) 
        for role in buildout.roles.all()
    )
    total_revenue = buildout.total_revenue_per_year
    total_payouts = buildout.total_yearly_costs
    profit = buildout.expected_profit
    profit_margin = buildout.profit_margin
    
    # Prepare detailed role data with responsibilities for Excel-like display
    roles_data = []
    for role in buildout.roles.all().order_by('title'):
        # Get all responsibilities for this role
        responsibilities = role.responsibilities.all().order_by('name')
        
        # Calculate hours per scope for this role
        hours_per_program_concept = sum(
            resp.hours for resp in buildout.responsibility_lines.all()
            if resp.responsibility.frequency_type == 'PER_PROGRAM_CONCEPT'
        )
        hours_per_new_worker = sum(
            resp.hours for resp in buildout.responsibility_lines.all()
            if resp.responsibility.frequency_type == 'PER_NEW_FACILITATOR'
        )
        hours_per_program = sum(
            resp.hours for resp in buildout.responsibility_lines.all()
            if resp.responsibility.frequency_type == 'PER_PROGRAM'
        )
        hours_per_session = sum(
            resp.hours for resp in buildout.responsibility_lines.all()
            if resp.responsibility.frequency_type == 'PER_SESSION'
        )
        
        # Calculate yearly totals
        yearly_hours = (
            hours_per_program_concept * buildout.new_program_concepts_per_year +
            hours_per_new_worker * buildout.num_new_facilitators +
            hours_per_program * buildout.num_programs_per_year +
            hours_per_session * buildout.total_sessions_per_year
        )
        
        # Calculate financial data
        payout = buildout.calculate_payout_per_role(role)
        percentage = buildout.calculate_percent_of_revenue_per_role(role)
        
        roles_data.append({
            'role': role,
            'responsibilities': responsibilities,
            'hours_per_program_concept': hours_per_program_concept,
            'hours_per_new_worker': hours_per_new_worker,
            'hours_per_program': hours_per_program,
            'hours_per_session': hours_per_session,
            'yearly_hours': yearly_hours,
            'payout': payout,
            'percentage': percentage
        })
    
    # Calculate base costs and overhead
    base_costs_data = []
    total_base_costs = 0
    for base_cost_assignment in buildout.base_cost_assignments.all():
        yearly_cost = base_cost_assignment.calculate_yearly_cost()
        total_base_costs += yearly_cost
        
        base_costs_data.append({
            'base_cost': base_cost_assignment.base_cost,
            'assignment': base_cost_assignment,
            'multiplier': base_cost_assignment.multiplier,
            'yearly_cost': yearly_cost,
            'percentage': (yearly_cost / total_revenue * 100) if total_revenue > 0 else 0
        })
    
    # Calculate location costs
    location_costs_data = []
    total_location_costs = 0
    for location_assignment in buildout.location_assignments.all():
        yearly_cost = location_assignment.calculate_yearly_cost()
        total_location_costs += yearly_cost
        
        location_costs_data.append({
            'location': location_assignment.location,
            'assignment': location_assignment,
            'multiplier': location_assignment.multiplier,
            'yearly_cost': yearly_cost,
            'percentage': (yearly_cost / total_revenue * 100) if total_revenue > 0 else 0
        })
    
    # Calculate total costs including base costs and location costs
    total_all_costs = total_payouts + total_base_costs + total_location_costs
    total_profit = total_revenue - total_all_costs
    total_profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    
    # Get instances for this buildout
    if user_is_admin(request.user):
        # Admins see all instances
        instances = buildout.instances.all().order_by('-created_at')
    else:
        # Contractors see only instances they're assigned to
        instances = buildout.instances.filter(
            contractor_assignments__contractor=request.user
        ).distinct().order_by('-created_at')

    context = {
        'buildout': buildout,
        'total_hours': total_hours,
        'total_revenue': total_revenue,
        'total_payouts': total_payouts,
        'total_base_costs': total_base_costs,
        'total_location_costs': total_location_costs,
        'total_all_costs': total_all_costs,
        'profit': profit,
        'total_profit': total_profit,
        'profit_margin': profit_margin,
        'total_profit_margin': total_profit_margin,
        'roles_data': roles_data,
        'base_costs_data': base_costs_data,
        'location_costs_data': location_costs_data,
        'instances': instances,
        'is_contractor_view': user_is_contractor(request.user) and not user_is_admin(request.user),
        'contractor_roles': buildout.role_lines.filter(contractor=request.user) if user_is_contractor(request.user) else None,
    }
    
    return render(request, 'programs/buildout_detail.html', context)


@login_required
def buildout_manage_responsibilities(request, buildout_pk):
    """Manage responsibilities and hours for a buildout with Excel-like interface."""
    if not (user_is_admin(request.user) or user_is_contractor(request.user)):
        messages.error(request, "Access denied. Admin or Contractor role required.")
        return redirect('dashboard')
    
    buildout = get_object_or_404(ProgramBuildout, pk=buildout_pk)
    
    if request.method == 'POST':
        # Handle responsibility hour updates
        for key, value in request.POST.items():
            if key.startswith('responsibility_'):
                responsibility_id = key.split('_')[1]
                try:
                    responsibility = Responsibility.objects.get(id=responsibility_id)
                    new_hours = Decimal(value)
                    if new_hours >= 0:
                        responsibility.default_hours = new_hours
                        responsibility.save()
                except (Responsibility.DoesNotExist, ValueError):
                    continue
        
        messages.success(request, "Responsibility hours updated successfully!")
        return redirect('programs:buildout_detail', buildout_pk=buildout_pk)
    
    # Get all roles with their responsibilities
    roles_data = []
    for role in Role.objects.all().order_by('title'):
        responsibilities = role.responsibilities.all().order_by('name')
        roles_data.append({
            'role': role,
            'responsibilities': responsibilities,
            'is_assigned': buildout.roles.filter(id=role.id).exists()
        })
    
    context = {
        'buildout': buildout,
        'roles_data': roles_data,
    }
    
    return render(request, 'programs/buildout_manage_responsibilities.html', context)


@login_required
def buildout_assign_roles(request, buildout_pk):
    """Assign roles to a buildout."""
    if not (user_is_admin(request.user) or user_is_contractor(request.user)):
        messages.error(request, "Access denied. Admin or Contractor role required.")
        return redirect('dashboard')
    
    buildout = get_object_or_404(ProgramBuildout, pk=buildout_pk)
    
    if request.method == 'POST':
        # Get selected roles
        selected_roles = request.POST.getlist('roles')
        
        # Clear existing assignments
        buildout.roles.clear()
        
        # Add selected roles
        for role_id in selected_roles:
            try:
                role = Role.objects.get(id=role_id)
                buildout.roles.add(role)
            except Role.DoesNotExist:
                continue
        
        messages.success(request, f"Assigned {len(selected_roles)} roles to buildout.")
        return redirect('programs:buildout_detail', buildout_pk=buildout_pk)
    
    # Get all available roles
    all_roles = Role.objects.all().order_by('title')
    assigned_roles = buildout.roles.all()
    
    context = {
        'buildout': buildout,
        'all_roles': all_roles,
        'assigned_roles': assigned_roles,
    }
    
    return render(request, 'programs/buildout_assign_roles.html', context)


@login_required
def program_type_buildouts(request, program_type_pk):
    """Show buildouts for a specific program type."""
    if not (user_is_admin(request.user) or user_is_contractor(request.user)):
        messages.error(request, "Access denied. Admin or Contractor role required.")
        return redirect('dashboard')
    
    program_type = get_object_or_404(ProgramType, pk=program_type_pk)
    buildouts = program_type.buildouts.all().order_by('title')
    
    context = {
        'program_type': program_type,
        'buildouts': buildouts,
    }
    
    return render(request, 'programs/program_type_buildouts.html', context)


# ============================================================================
# ENHANCED SCHEDULING VIEWS
# ============================================================================

@login_required
def contractor_availability_list(request):
    """List contractor's availability slots."""
    if not user_is_contractor(request.user) and not user_is_admin(request.user):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    # Get contractor's availability slots
    availability_slots = ContractorAvailability.objects.filter(
        contractor=request.user
    ).prefetch_related('program_offerings__program_buildout', 'program_offerings__sessions')
    
    context = {
        'availability_slots': availability_slots,
        'can_add': True,
    }
    
    return render(request, 'programs/contractor_availability_list.html', context)


@login_required
def contractor_availability_create(request):
    """Create new availability slot for contractor."""
    if not user_is_contractor(request.user) and not user_is_admin(request.user):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    # Enforce onboarding gate
    if user_is_contractor(request.user) and not user_is_admin(request.user):
        try:
            from people.models import Contractor
            contractor = Contractor.objects.filter(user=request.user).first()
            if not contractor or contractor.needs_onboarding:
                return HttpResponse("Onboarding required", status=403)
        except Exception:
            return HttpResponse("Onboarding required", status=403)
    
    if request.method == 'POST':
        form = ContractorAvailabilityForm(request.POST)
        if form.is_valid():
            # Set contractor before saving
            form.instance.contractor = request.user
            availability = form.save()
            
            # Handle different availability types
            availability_type = form.cleaned_data.get('availability_type')
            if availability_type == 'single':
                messages.success(request, "Availability slot created successfully!")
                return redirect('programs:contractor_availability_detail', pk=availability.pk)
            elif availability_type == 'range':
                start_date = form.cleaned_data.get('start_date')
                end_date = form.cleaned_data.get('end_date')
                days_count = (end_date - start_date).days + 1
                messages.success(request, f"Created {days_count} availability slots from {start_date} to {end_date}!")
                return redirect('programs:contractor_availability_list')
            elif availability_type == 'recurring':
                weekdays = form.cleaned_data.get('recurring_weekdays')
                until_date = form.cleaned_data.get('recurring_until')
                weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                selected_days = [weekday_names[int(day)] for day in weekdays]
                messages.success(request, f"Created recurring availability for {', '.join(selected_days)} until {until_date}!")
                return redirect('programs:contractor_availability_list')
    else:
        form = ContractorAvailabilityForm()
    
    context = {
        'form': form,
        'title': 'Set New Availability',
    }
    
    return render(request, 'programs/contractor_availability_form.html', context)


@login_required
def contractor_availability_detail(request, pk):
    """Detail view for contractor availability with program offerings."""
    availability = get_object_or_404(ContractorAvailability, pk=pk)
    
    # Check permissions
    if not (user_is_admin(request.user) or availability.contractor == request.user):
        messages.error(request, "You don't have permission to access this availability.")
        return redirect('programs:contractor_availability_list')
    
    program_offerings = availability.program_offerings.all().select_related('program_buildout')
    # Get sessions through program offerings
    sessions = ProgramSession.objects.filter(
        availability_program__availability=availability
    ).order_by('start_datetime')
    
    context = {
        'availability': availability,
        'program_offerings': program_offerings,
        'sessions': sessions,
        'can_edit': availability.contractor == request.user or user_is_admin(request.user),
    }
    
    return render(request, 'programs/contractor_availability_detail.html', context)


@login_required
def contractor_availability_edit(request, pk):
    """Edit contractor availability slot."""
    availability = get_object_or_404(ContractorAvailability, pk=pk)
    
    # Check permissions
    if not (user_is_admin(request.user) or availability.contractor == request.user):
        messages.error(request, "You don't have permission to edit this availability.")
        return redirect('programs:contractor_availability_list')
    # Enforce onboarding gate for contractors
    if user_is_contractor(request.user) and not user_is_admin(request.user):
        try:
            from people.models import Contractor
            contractor = Contractor.objects.filter(user=request.user).first()
            if not contractor or contractor.needs_onboarding:
                return HttpResponse("Onboarding required", status=403)
        except Exception:
            return HttpResponse("Onboarding required", status=403)
    
    if request.method == 'POST':
        form = ContractorAvailabilityForm(request.POST, instance=availability)
        if form.is_valid():
            form.save()
            messages.success(request, "Availability updated successfully!")
            return redirect('programs:contractor_availability_detail', pk=availability.pk)
    else:
        form = ContractorAvailabilityForm(instance=availability)
    
    context = {
        'form': form,
        'availability': availability,
        'title': 'Edit Availability',
    }
    
    return render(request, 'programs/contractor_availability_form.html', context)


@login_required
def add_program_to_availability(request, availability_pk):
    """Add a program offering to an availability slot."""
    availability = get_object_or_404(ContractorAvailability, pk=availability_pk)
    
    # Check permissions
    if not (user_is_admin(request.user) or availability.contractor == request.user):
        messages.error(request, "You don't have permission to modify this availability.")
        return redirect('programs:contractor_availability_list')
    
    if request.method == 'POST':
        form = AvailabilityProgramForm(
            contractor=availability.contractor,
            data=request.POST
        )
        if form.is_valid():
            program_offering = form.save(commit=False)
            program_offering.availability = availability
            
            # Validate that the total time doesn't exceed availability
            total_hours_needed = program_offering.session_duration_hours * program_offering.max_sessions
            if total_hours_needed > availability.remaining_hours:
                messages.error(
                    request, 
                    f"Cannot add program: would require {total_hours_needed} hours but only "
                    f"{availability.remaining_hours} hours remaining in this slot."
                )
            else:
                program_offering.save()
                messages.success(request, f"Added {program_offering.program_buildout.title} to availability!")
                return redirect('programs:contractor_availability_detail', pk=availability.pk)
    else:
        form = AvailabilityProgramForm(contractor=availability.contractor)
    
    context = {
        'form': form,
        'availability': availability,
        'title': f'Add Program to {availability}',
    }
    
    return render(request, 'programs/add_program_to_availability.html', context)


def _get_available_sessions():
    """
    Get intelligently filtered available sessions.
    
    This method implements the complex logic to show only sessions that can actually
    be booked, considering contractor time conflicts and overlapping availability.
    """
    from django.utils import timezone
    from datetime import timedelta
    
    # Start with all future sessions that have capacity
    base_sessions = ProgramSession.objects.filter(
        start_datetime__gt=timezone.now(),
        status__in=['scheduled', 'confirmed']
    ).exclude(
        enrolled_count__gte=F('max_capacity')
    ).select_related(
        'program_instance__buildout__program_type',
        'availability_program__availability__contractor',
        'availability_program__program_buildout'
    ).order_by('start_datetime')
    
    available_sessions = []
    
    for session in base_sessions:
        contractor = session.availability_program.availability.contractor
        session_start = session.start_datetime
        session_end = session.end_datetime
        
        # Check if this contractor has any conflicting confirmed bookings
        # that would prevent them from teaching this session
        conflicting_sessions = ProgramSession.objects.filter(
            availability_program__availability__contractor=contractor,
            status__in=['scheduled', 'confirmed']
        ).exclude(pk=session.pk).filter(
            # Check for time overlaps
            start_datetime__lt=session_end,
            end_datetime__gt=session_start
        ).filter(
            # Only consider sessions with confirmed bookings
            bookings__status='confirmed'
        ).distinct()
        
        # If there are no conflicting sessions with confirmed bookings,
        # this session is available
        if not conflicting_sessions.exists():
            available_sessions.append(session)
    
    return available_sessions


@login_required
def available_sessions_list(request):
    """List all intelligently filtered available sessions for parent booking."""
    if not user_is_parent(request.user) and not user_is_admin(request.user):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    # Get intelligently filtered available sessions
    available_sessions = _get_available_sessions()
    
    # Filter by program type if specified
    program_type_filter = request.GET.get('program_type')
    if program_type_filter:
        try:
            program_type_id = int(program_type_filter)
            available_sessions = [
                session for session in available_sessions 
                if session.program_instance.buildout.program_type.id == program_type_id
            ]
        except (ValueError, TypeError):
            pass
    
    # Group by program type for better organization
    sessions_by_program = {}
    sessions_by_date = {}
    
    for session in available_sessions:
        # Group by program type
        program_name = session.program_instance.buildout.program_type.name
        if program_name not in sessions_by_program:
            sessions_by_program[program_name] = []
        sessions_by_program[program_name].append(session)
        
        # Also group by date for better display
        date_key = session.start_datetime.date()
        if date_key not in sessions_by_date:
            sessions_by_date[date_key] = []
        sessions_by_date[date_key].append(session)
    
    # Sort dates
    sorted_dates = sorted(sessions_by_date.keys())
    
    # Get program type name for display
    filtered_program_type = None
    if program_type_filter:
        try:
            program_type_id = int(program_type_filter)
            filtered_program_type = ProgramType.objects.get(id=program_type_id)
        except (ValueError, TypeError, ProgramType.DoesNotExist):
            pass
    
    context = {
        'sessions_by_program': sessions_by_program,
        'sessions_by_date': sessions_by_date,
        'sorted_dates': sorted_dates,
        'available_sessions': available_sessions,
        'total_sessions': len(available_sessions),
        'filtered_program_type': filtered_program_type,
    }
    
    return render(request, 'programs/available_sessions_list.html', context)


@login_required
def book_session(request, session_pk):
    """Book a child into a specific session."""
    if not user_is_parent(request.user) and not user_is_admin(request.user):
        messages.error(request, "You don't have permission to book sessions.")
        return redirect('dashboard')
    
    session = get_object_or_404(ProgramSession, pk=session_pk)
    
    if not session.can_book():
        messages.error(request, "This session is not available for booking.")
        return redirect('programs:available_sessions_list')
    
    # Get parent's children
    children = Child.objects.filter(parent=request.user)
    if not children.exists():
        messages.error(request, "You need to add children to your account before booking sessions.")
        return redirect('programs:manage_children')
    
    if request.method == 'POST':
        child_id = request.POST.get('child')
        child = get_object_or_404(Child, pk=child_id, parent=request.user)
        
        # Check if child is already booked for this session
        existing_booking = SessionBooking.objects.filter(
            session=session,
            child=child
        ).first()
        
        if existing_booking:
            messages.error(request, f"{child.full_name} is already booked for this session.")
        else:
            # Create booking
            booking_form = SessionBookingForm(request.POST)
            if booking_form.is_valid():
                booking = booking_form.save(commit=False)
                booking.session = session
                booking.child = child
                booking.save()
                
                # Try to confirm booking immediately if there's space
                if booking.confirm_booking():
                    messages.success(
                        request, 
                        f"Successfully booked {child.full_name} for {session.program_instance.title}!"
                    )
                else:
                    messages.info(
                        request, 
                        f"Added {child.full_name} to waitlist for {session.program_instance.title}."
                    )
                
                return redirect('programs:parent_bookings')
    else:
        booking_form = SessionBookingForm()
    
    context = {
        'session': session,
        'children': children,
        'booking_form': booking_form,
    }
    
    return render(request, 'programs/book_session.html', context)


@login_required
def parent_bookings(request):
    """List parent's current bookings."""
    if not user_is_parent(request.user) and not user_is_admin(request.user):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    # Get all bookings for parent's children
    bookings = SessionBooking.objects.filter(
        child__parent=request.user
    ).select_related(
        'child', 'session__program_instance__buildout__program_type',
        'session__availability_program__availability__contractor'
    ).order_by('-booked_at')
    
    context = {
        'bookings': bookings,
    }
    
    return render(request, 'programs/parent_bookings.html', context)


@login_required
def contractor_buildout_instance_schedule(request, instance_pk):
    """Allow contractors to create availability for their assigned program instances."""
    if not user_is_contractor(request.user):
        messages.error(request, "Access denied. Contractor role required.")
        return redirect('dashboard')
    
    instance = get_object_or_404(
        ProgramInstance.objects.select_related('buildout'),
        pk=instance_pk
    )
    
    # Check if contractor is assigned to this instance
    if not instance.contractor_assignments.filter(contractor=request.user).exists():
        messages.error(request, "Access denied. You are not assigned to this program instance.")
        return redirect('programs:contractor_dashboard')
    
    # Get contractor's role assignments for this instance
    contractor_assignments = instance.contractor_assignments.filter(contractor=request.user)
    
    # Get existing availability for this instance
    from programs.models import ContractorAvailability, AvailabilityProgram
    
    availability_programs = AvailabilityProgram.objects.filter(
        availability__contractor=request.user,
        buildout=instance.buildout
    ).select_related('availability').order_by('availability__start_datetime')
    
    context = {
        'instance': instance,
        'contractor_assignments': contractor_assignments,
        'availability_programs': availability_programs,
        'can_create_availability': True,
    }
    
    return render(request, 'programs/contractor_instance_schedule.html', context)


@login_required
def program_catalog(request):
    """Public catalog of available program types for parents and contractors."""
    program_types = ProgramType.objects.all().order_by('name')
    
    # Add active buildouts and instances for each program type
    total_active_programs = 0
    for program_type in program_types:
        program_type.active_buildouts = program_type.buildouts.filter(is_active=True)
        program_type.active_instances = ProgramInstance.objects.filter(
            buildout__program_type=program_type,
            is_active=True,
            start_date__gte=timezone.now()
        ).order_by('start_date')
        
        # Count total active programs
        total_active_programs += program_type.active_instances.count()
        
        # Add visible contractor info for each instance
        for instance in program_type.active_instances:
            instance.visible_contractors = []
            for assignment in instance.contractor_assignments.all():
                if assignment.role.visible_to_parents:
                    instance.visible_contractors.append({
                        'role': assignment.role.title,
                        'contractor': assignment.contractor.get_full_name() or assignment.contractor.email
                    })
    
    context = {
        'program_types': program_types,
        'total_active_sessions': total_active_programs,
        'is_parent': user_is_parent(request.user),
        'is_contractor': user_is_contractor(request.user),
    }
    
    return render(request, 'programs/program_catalog.html', context)


@login_required
def program_type_instances(request, program_type_id):
    """Show all active instances for a specific program type."""
    program_type = get_object_or_404(ProgramType, id=program_type_id)
    
    # Get active instances for this program type
    instances = ProgramInstance.objects.filter(
        buildout__program_type=program_type,
        is_active=True,
        start_date__gte=timezone.now()
    ).order_by('start_date')
    
    # Add visible contractor info for each instance and calculate totals
    total_available_spots = 0
    for instance in instances:
        instance.visible_contractors = []
        for assignment in instance.contractor_assignments.all():
            if assignment.role.visible_to_parents:
                instance.visible_contractors.append({
                    'role': assignment.role.title,
                    'contractor': assignment.contractor.get_full_name() or assignment.contractor.email
                })
        
        # Calculate available spots
        total_available_spots += instance.available_spots
    
    context = {
        'program_type': program_type,
        'instances': instances,
        'total_available_spots': total_available_spots,
        'is_parent': user_is_parent(request.user),
        'is_contractor': user_is_contractor(request.user),
    }
    
    return render(request, 'programs/program_type_instances.html', context)


def program_request_create(request, program_type_id):
    """Create a new program request (for parents and contractors)."""
    program_type = get_object_or_404(ProgramType, id=program_type_id)
    
    if request.method == 'POST':
        from programs.forms import ProgramRequestForm
        form = ProgramRequestForm(request.POST)
        if form.is_valid():
            program_request = form.save(commit=False)
            program_request.program_type = program_type
            if request.user.is_authenticated:
                program_request.requester = request.user
                program_request.contact_email = request.user.email
                program_request.contact_name = request.user.get_full_name() or request.user.email
            program_request.save()
            
            # Create corresponding Contact record for admin tracking
            from communications.models import Contact
            Contact.objects.create(
                name=program_request.contact_name,
                email=program_request.contact_email,
                phone=program_request.contact_phone,
                message=f"Program Request: {program_type.name}\n\n"
                       f"Request Type: {program_request.get_request_type_display()}\n"
                       f"Preferred Location: {program_request.preferred_location}\n"
                       f"Preferred Dates: {program_request.preferred_dates}\n"
                       f"Expected Participants: {program_request.expected_participants}\n"
                       f"Additional Notes: {program_request.additional_notes}\n"
                       f"Experience: {program_request.contractor_experience}",
                interest_categories='program_request',
                status='new'
            )
            
            messages.success(request, f"Your request for {program_type.name} has been submitted successfully!")
            return redirect('programs:program_catalog')
    else:
        from programs.forms import ProgramRequestForm
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'contact_name': request.user.get_full_name() or request.user.email,
                'contact_email': request.user.email,
                'request_type': 'contractor_buildout' if user_is_contractor(request.user) else 'parent_request'
            }
        form = ProgramRequestForm(initial=initial_data)
    
    context = {
        'form': form,
        'program_type': program_type,
    }
    
    return render(request, 'programs/program_request_form.html', context)


@login_required
def cancel_booking(request, booking_pk):
    """Cancel a session booking."""
    booking = get_object_or_404(SessionBooking, pk=booking_pk)
    
    # Check permissions
    if not (user_is_admin(request.user) or booking.parent == request.user):
        messages.error(request, "You don't have permission to cancel this booking.")
        return redirect('programs:parent_bookings')
    
    if request.method == 'POST':
        if booking.cancel_booking():
            messages.success(request, f"Cancelled booking for {booking.child.full_name}.")
        else:
            messages.error(request, "This booking cannot be cancelled.")
        return redirect('programs:parent_bookings')
    
    context = {
        'booking': booking,
    }
    
    return render(request, 'programs/cancel_booking_confirm.html', context)


@login_required
def contractor_sessions_list(request):
    """List sessions for contractor to manage."""
    if not user_is_contractor(request.user) and not user_is_admin(request.user):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    # Get contractor's sessions
    sessions = ProgramSession.objects.filter(
        availability_program__availability__contractor=request.user
    ).select_related(
        'program_instance__buildout__program_type',
        'availability_program__program_buildout'
    ).prefetch_related('bookings__child').order_by('start_datetime')
    
    context = {
        'sessions': sessions,
    }
    
    return render(request, 'programs/contractor_sessions_list.html', context)


@login_required  
def session_detail(request, session_pk):
    """Detailed view of a session with bookings."""
    session = get_object_or_404(ProgramSession, pk=session_pk)
    
    # Check permissions
    is_contractor = session.availability_program.availability.contractor == request.user
    if not (user_is_admin(request.user) or is_contractor):
        messages.error(request, "You don't have permission to view this session.")
        return redirect('dashboard')
    
    bookings = session.bookings.all().select_related('child__parent').order_by('booked_at')
    
    context = {
        'session': session,
        'bookings': bookings,
        'can_manage': is_contractor or user_is_admin(request.user),
    }
    
    return render(request, 'programs/session_detail.html', context)


# ============================================================================
# CONTRACTOR DAY-OFF REQUEST VIEWS
# ============================================================================

@login_required
def contractor_day_off_requests(request):
    """List contractor's day-off requests."""
    if not user_is_contractor(request.user) and not user_is_admin(request.user):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    # Get contractor's day-off requests
    if user_is_admin(request.user):
        # Admins can see all requests
        day_off_requests = ContractorDayOffRequest.objects.all().select_related('contractor').order_by('-created_at')
    else:
        # Contractors see only their own requests
        day_off_requests = ContractorDayOffRequest.objects.filter(
            contractor=request.user
        ).order_by('-created_at')
    
    context = {
        'day_off_requests': day_off_requests,
        'can_create': user_is_contractor(request.user),
        'is_admin': user_is_admin(request.user),
    }
    
    return render(request, 'programs/contractor_day_off_requests.html', context)


@login_required
def contractor_day_off_request_create(request):
    """Create a new day-off request."""
    if not user_is_contractor(request.user):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = ContractorDayOffRequestForm(contractor=request.user, data=request.POST)
        if form.is_valid():
            day_off_request = form.save()
            if day_off_request.start_date == day_off_request.end_date:
                messages.success(request, f"Day off request for {day_off_request.start_date} has been submitted for approval.")
            else:
                messages.success(request, f"Day off request for {day_off_request.start_date} to {day_off_request.end_date} has been submitted for approval.")
            return redirect('programs:contractor_day_off_requests')
    else:
        form = ContractorDayOffRequestForm(contractor=request.user)
    
    context = {
        'form': form,
        'title': 'Request Day Off',
    }
    
    return render(request, 'programs/contractor_day_off_request_form.html', context)


@login_required
def contractor_day_off_request_detail(request, pk):
    """Detail view for a day-off request."""
    day_off_request = get_object_or_404(ContractorDayOffRequest, pk=pk)
    
    # Check permissions
    if not (user_is_admin(request.user) or day_off_request.contractor == request.user):
        messages.error(request, "You don't have permission to view this request.")
        return redirect('programs:contractor_day_off_requests')
    
    # Get conflict information if not already checked
    if day_off_request.status == 'pending' and (day_off_request.affected_sessions_count == 0 and day_off_request.affected_bookings_count == 0):
        conflicts = day_off_request.check_conflicts()
    else:
        # Get the actual conflicts for display
        conflicts = {
            'sessions': ProgramSession.objects.filter(
                availability_program__availability__contractor=day_off_request.contractor,
                start_datetime__date__gte=day_off_request.start_date,
                start_datetime__date__lte=day_off_request.end_date,
                status__in=['scheduled', 'confirmed']
            ),
            'bookings': SessionBooking.objects.filter(
                session__availability_program__availability__contractor=day_off_request.contractor,
                session__start_datetime__date__gte=day_off_request.start_date,
                session__start_datetime__date__lte=day_off_request.end_date,
                status__in=['pending', 'confirmed']
            )
        }
    
    context = {
        'day_off_request': day_off_request,
        'conflicts': conflicts,
        'can_approve': user_is_admin(request.user) and day_off_request.status == 'pending',
        'can_cancel': day_off_request.contractor == request.user and day_off_request.status == 'pending',
    }
    
    return render(request, 'programs/contractor_day_off_request_detail.html', context)


@login_required
def contractor_day_off_request_approve(request, pk):
    """Approve a day-off request (admin only)."""
    if not user_is_admin(request.user):
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('dashboard')
    
    day_off_request = get_object_or_404(ContractorDayOffRequest, pk=pk)
    
    if day_off_request.status != 'pending':
        messages.error(request, "This request has already been processed.")
        return redirect('programs:contractor_day_off_request_detail', pk=pk)
    
    if request.method == 'POST':
        admin_notes = request.POST.get('admin_notes', '')
        day_off_request.approve(request.user, admin_notes)
        
        if day_off_request.start_date == day_off_request.end_date:
            messages.success(
                request, 
                f"Day off request for {day_off_request.contractor.get_full_name()} on {day_off_request.start_date} has been approved."
            )
        else:
            messages.success(
                request, 
                f"Day off request for {day_off_request.contractor.get_full_name()} from {day_off_request.start_date} to {day_off_request.end_date} has been approved."
            )
        
        # TODO: Send notification to contractor
        
        return redirect('programs:contractor_day_off_request_detail', pk=pk)
    
    return redirect('programs:contractor_day_off_request_detail', pk=pk)


@login_required
def contractor_day_off_request_deny(request, pk):
    """Deny a day-off request (admin only)."""
    if not user_is_admin(request.user):
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('dashboard')
    
    day_off_request = get_object_or_404(ContractorDayOffRequest, pk=pk)
    
    if day_off_request.status != 'pending':
        messages.error(request, "This request has already been processed.")
        return redirect('programs:contractor_day_off_request_detail', pk=pk)
    
    if request.method == 'POST':
        admin_notes = request.POST.get('admin_notes', '')
        day_off_request.status = 'denied'
        day_off_request.reviewed_by = request.user
        day_off_request.reviewed_at = timezone.now()
        day_off_request.admin_notes = admin_notes
        day_off_request.save()
        
        messages.success(
            request, 
            f"Day off request for {day_off_request.contractor.get_full_name()} on {day_off_request.date} has been denied."
        )
        
        # TODO: Send notification to contractor
        
        return redirect('programs:contractor_day_off_request_detail', pk=pk)
    
    return redirect('programs:contractor_day_off_request_detail', pk=pk)
