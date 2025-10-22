from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods, require_POST
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
import logging

logger = logging.getLogger(__name__)

from .models import (
    ProgramType, ProgramInstance, RegistrationForm, FormQuestion,
    Child, Registration, Role, Responsibility, ProgramBuildout, 
    BuildoutResponsibilityAssignment, BuildoutRoleAssignment, BaseCost, 
    BuildoutBaseCostAssignment, InstanceRoleAssignment,
    ContractorAvailability, AvailabilityProgram, ProgramSession, SessionBooking,
    ProgramBuildoutScheduling, ContractorDayOffRequest, ProgramRequest,
    AvailabilityRule, AvailabilityException
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
    """Enhanced Parent Landing Page with comprehensive sections and calendar."""
    logger.info(f"Parent dashboard called for user: {request.user}, is_parent: {user_is_parent(request.user)}")
    if not user_is_parent(request.user):
        logger.info(f"User {request.user} is not a parent, redirecting to general dashboard")
        messages.error(request, "This page is for parents. If you think this is a mistake, contact support.")
        return redirect('dashboard:dashboard')
    
    now = timezone.now()
    
    # Get user's children (sorted by first name)
    children = request.user.children.all().order_by('first_name')
    
    # Get current registrations/sign-ups for user's children
    current_registrations = Registration.objects.filter(
        child__parent=request.user,
        program_instance__end_date__gte=now,
        status__in=['pending', 'approved', 'waitlisted']
    ).select_related(
        'child', 
        'program_instance', 
        'program_instance__buildout__program_type'
    ).order_by('child__first_name', 'program_instance__start_date')
    
    # Get filters for calendar
    facilitator_ids = request.GET.getlist('facilitator_id')
    program_type_ids = request.GET.getlist('program_type_id')
    year = int(request.GET.get('year', now.year))
    month = int(request.GET.get('month', now.month))
    
    # Get running and pending program instances (public view) - KEPT FOR LEGACY
    running_pending_instances = ProgramInstance.objects.filter(
        is_active=True,
        start_date__gte=now,
        buildout__status__in=['active', 'ready']
    ).select_related(
        'buildout__program_type'
    ).prefetch_related(
        'contractor_assignments__role',
        'contractor_assignments__contractor'
    ).order_by('start_date')
    
    # Add enrollment info and facilitator data for each instance
    for instance in running_pending_instances:
        instance.enrolled_count = instance.current_enrollment
        instance.spots_left = instance.available_spots
        instance.is_nearly_full = instance.spots_left <= 3 and instance.spots_left > 0
        instance.user_already_enrolled = current_registrations.filter(program_instance=instance).exists()
        
        # Get visible facilitators
        instance.visible_facilitators = []
        for assignment in instance.contractor_assignments.all():
            if assignment.role.visible_to_parents:
                facilitator_name = assignment.contractor.get_full_name() or assignment.contractor.email
                instance.visible_facilitators.append(facilitator_name)
    
    # Get available program types for inquiry
    available_program_types = ProgramType.objects.filter(
        buildouts__is_active=True
    ).distinct().order_by('name')
    
    # Get facilitators (contractors with visible roles in active instances)
    facilitators = User.objects.filter(
        groups__name='Contractor',
        role_assignments__role__visible_to_parents=True,
        role_assignments__program_instance__is_active=True
    ).distinct().order_by('first_name', 'last_name')
    
    # Add program info for each facilitator
    for facilitator in facilitators:
        # Get program types this facilitator works with (through visible roles)
        facilitator.visible_program_types = ProgramType.objects.filter(
            buildouts__instances__contractor_assignments__contractor=facilitator,
            buildouts__instances__contractor_assignments__role__visible_to_parents=True
        ).distinct()
        
        # Get current instances this facilitator is assigned to
        facilitator.current_instances = running_pending_instances.filter(
            contractor_assignments__contractor=facilitator,
            contractor_assignments__role__visible_to_parents=True
        ).distinct()
    
    # Get recent conversations for messages section
    from communications.models import Conversation
    recent_conversations = Conversation.objects.filter(
        owner=request.user
    ).prefetch_related('messages').order_by('-updated_at')[:5]
    
    # Get all contractors for calendar filter
    all_contractors = User.objects.filter(
        groups__name='Contractor',
        availability_slots__is_archived=False,
        availability_slots__end_datetime__gte=now
    ).distinct().order_by('first_name', 'last_name')
    
    # Get all program types for calendar filter
    all_program_types = ProgramType.objects.filter(
        buildouts__availability_offerings__availability__is_archived=False,
        buildouts__availability_offerings__availability__end_datetime__gte=now
    ).distinct().order_by('name')
    
    context = {
        'children': children,
        'current_registrations': current_registrations,
        'running_pending_instances': running_pending_instances,
        'available_program_types': available_program_types,
        'facilitators': facilitators,
        'parent_name': request.user.get_full_name() or request.user.email.split('@')[0],
        'recent_conversations': recent_conversations,
        # Calendar data
        'year': year,
        'month': month,
        'facilitator_ids': facilitator_ids,
        'program_type_ids': program_type_ids,
        'all_contractors': all_contractors,
        'all_program_types': all_program_types,
    }
    
    return render(request, 'programs/parent_home.html', context)


@login_required
def send_program_inquiry(request):
    """Handle program inquiry submission from parent landing page."""
    if not user_is_parent(request.user):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        program_type_id = request.POST.get('program_type_id')
        child_id = request.POST.get('child_id')  # Optional
        note = request.POST.get('note', '').strip()
        
        if not program_type_id:
            return JsonResponse({'error': 'Program type is required'}, status=400)
        
        program_type = ProgramType.objects.get(id=program_type_id)
        
        # Validate child belongs to parent if provided
        child = None
        if child_id:
            try:
                child = Child.objects.get(id=child_id, parent=request.user)
            except Child.DoesNotExist:
                return JsonResponse({'error': 'Invalid child selection'}, status=400)
        
        # Check for recent duplicate inquiry (same program type + child combination within last hour)
        from datetime import timedelta
        recent_cutoff = timezone.now() - timedelta(hours=1)
        
        existing_inquiry = ProgramRequest.objects.filter(
            requester=request.user,
            program_type=program_type,
            created_at__gte=recent_cutoff
        )
        
        if child:
            # Check if we have a recent inquiry for this specific child
            existing_inquiry = existing_inquiry.filter(
                additional_notes__icontains=f"Child: {child.full_name}"
            )
        
        if existing_inquiry.exists():
            return JsonResponse({
                'success': True,
                'message': 'Inquiry already sent recently.'
            })
        
        # Create the inquiry
        inquiry_notes = note
        if child:
            inquiry_notes = f"Child: {child.full_name}\n{note}".strip()
        
        inquiry = ProgramRequest.objects.create(
            request_type='parent_request',
            program_type=program_type,
            requester=request.user,
            contact_name=request.user.get_full_name() or request.user.email,
            contact_email=request.user.email,
            additional_notes=inquiry_notes
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Thanks! We\'ll be in touch about {program_type.name}.'
        })
        
    except ProgramType.DoesNotExist:
        return JsonResponse({'error': 'Program type not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Something went wrong. Please try again.'}, status=500)


@login_required
def parent_dashboard_calendar_partial(request):
    """
    HTMX partial: Return calendar month view for parents.
    
    Shows all contractors' non-archived, active+future availability.
    Filters by facilitator (contractor) and program type.
    """
    if not user_is_parent(request.user):
        return HttpResponse("Permission denied", status=403)
    
    from .utils.calendar_utils import build_calendar_data, get_prev_month, get_next_month, get_month_bounds
    
    now = timezone.now()
    year = int(request.GET.get('year', now.year))
    month = int(request.GET.get('month', now.month))
    facilitator_ids = request.GET.getlist('facilitator_id')
    program_type_ids = request.GET.getlist('program_type_id')
    
    # Get availability for the month (with buffer)
    start_datetime, end_datetime = get_month_bounds(year, month)
    
    # Base queryset: all non-archived, future/active availability
    # that overlaps with the visible month
    availability_qs = ContractorAvailability.objects.filter(
        is_archived=False,
        end_datetime__gte=now,  # Hide past entries
        start_datetime__lte=end_datetime  # Within month bounds
    ).select_related('contractor').prefetch_related(
        'program_offerings__program_buildout__program_type'
    )
    
    # Apply facilitator filter
    if facilitator_ids:
        availability_qs = availability_qs.filter(
            contractor__id__in=facilitator_ids
        )
    
    # Apply program type filter
    if program_type_ids:
        availability_qs = availability_qs.filter(
            program_offerings__program_buildout__program_type__id__in=program_type_ids
        ).distinct()
    
    # Build calendar data
    calendar_data = build_calendar_data(year, month, availability_qs)
    
    # Get prev/next month
    prev_year, prev_month = get_prev_month(year, month)
    next_year, next_month = get_next_month(year, month)
    
    context = {
        'calendar': calendar_data,
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
        'current_year': year,
        'current_month': month,
        'facilitator_ids': facilitator_ids,
        'program_type_ids': program_type_ids,
        'view_type': 'parent',
    }
    
    return render(request, 'programs/partials/_availability_calendar.html', context)


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
    
    # Get existing registrations if user is parent
    existing_registrations = []
    available_children = []
    if user_is_parent(request.user):
        existing_registrations = Registration.objects.filter(
            child__parent=request.user,
            program_instance=program_instance
        ).select_related('child')
        
        # Get children who aren't already registered for this program
        registered_child_ids = existing_registrations.values_list('child_id', flat=True)
        available_children = request.user.children.exclude(id__in=registered_child_ids)
    
    context = {
        'program_instance': program_instance,
        'can_register': can_register,
        'existing_registrations': existing_registrations,
        'available_children': available_children,
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
    
    if request.method == 'POST':
        child_pk = request.POST.get('child')
        if child_pk:
            try:
                child = request.user.children.get(pk=child_pk)
                
                # Check if this specific child is already registered
                existing_registration = Registration.objects.filter(
                    child=child,
                    program_instance=program_instance
                ).first()
                
                if existing_registration:
                    messages.warning(request, f"{child.full_name} is already registered for this program.")
                    return redirect('programs:program_instance_detail', pk=program_instance_pk)
                
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
        # Allow admins to edit any form, contractors can only edit their own
        if user_is_admin(request.user):
            form_instance = get_object_or_404(RegistrationForm, pk=form_pk)
        else:
            form_instance = get_object_or_404(RegistrationForm, pk=form_pk, created_by=request.user)
    
    if request.method == 'POST':
        form = RegistrationFormForm(request.POST, instance=form_instance)
        if form.is_valid():
            form_instance = form.save(commit=False)
            # Only set created_by for new forms, preserve original creator for existing forms
            if not form_instance.pk:
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
    
    # Allow admins to add questions to any form, contractors can only add to their own
    if user_is_admin(request.user):
        form = get_object_or_404(RegistrationForm, pk=form_pk)
    else:
        form = get_object_or_404(RegistrationForm, pk=form_pk, created_by=request.user)
    
    if request.method == 'POST':
        question_form = FormQuestionForm(request.POST)
        if question_form.is_valid():
            question = question_form.save(commit=False)
            question.form = form
            question.save()
            
            return render(request, 'programs/partials/question_row.html', {
                'question': question,
                'form': form
            })
    
    return HttpResponse("Invalid request", status=400)


@login_required
def delete_form_question(request, question_pk):
    """Delete a question from a form via HTMX."""
    if not (user_is_contractor(request.user) or user_is_admin(request.user)):
        return HttpResponse("Access denied", status=403)
    
    # Allow admins to delete questions from any form, contractors can only delete from their own
    if user_is_admin(request.user):
        question = get_object_or_404(FormQuestion, pk=question_pk)
    else:
        question = get_object_or_404(FormQuestion, pk=question_pk, form__created_by=request.user)
    question.delete()
    
    return HttpResponse("Question deleted")


@login_required
def duplicate_form(request, form_pk):
    """Duplicate a form."""
    if not (user_is_contractor(request.user) or user_is_admin(request.user)):
        messages.error(request, "Access denied. Contractor or Admin role required.")
        return redirect('programs:form_builder')
    
    # Allow admins to duplicate any form, contractors can only duplicate their own
    if user_is_admin(request.user):
        original_form = get_object_or_404(RegistrationForm, pk=form_pk)
    else:
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
    """
    List contractor's availability slots with calendar and filtering.
    
    Shows:
    - Grouped list (Active, Future, Past)
    - Calendar month view
    - Filters by Program Instance
    - Archive functionality
    """
    if not user_is_contractor(request.user) and not user_is_admin(request.user):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    now = timezone.now()
    
    # Auto-inactivate past availability
    ContractorAvailability.objects.filter(
        end_datetime__lt=now,
        is_active=True
    ).update(is_active=False)
    
    # Get filters from request
    program_buildout_ids = request.GET.getlist('program_buildout_id')
    year = int(request.GET.get('year', now.year))
    month = int(request.GET.get('month', now.month))
    
    # Base queryset: non-archived availability for this contractor
    base_qs = ContractorAvailability.objects.filter(
        contractor=request.user,
        is_archived=False
    ).select_related('contractor').prefetch_related(
        'program_offerings__program_buildout__program_type',
        'program_offerings__sessions'
    )
    
    # Apply program buildout filter if provided
    if program_buildout_ids:
        base_qs = base_qs.filter(
            program_offerings__program_buildout__id__in=program_buildout_ids
        ).distinct()
    
    # Get all program buildouts this contractor has availability for (for filter dropdown)
    from django.db.models import Q
    contractor_buildouts = ProgramBuildout.objects.filter(
        availability_offerings__availability__contractor=request.user,
        availability_offerings__availability__is_archived=False
    ).distinct().order_by('title')
    
    context = {
        'year': year,
        'month': month,
        'program_buildout_ids': program_buildout_ids,
        'contractor_buildouts': contractor_buildouts,
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
            # Set contractor on form instance before saving
            form.instance.contractor = request.user
            
            # Handle different availability types
            availability_type = form.cleaned_data.get('availability_type')
            
            # Save with commit=True to create all instances (single, range, or recurring)
            availability = form.save(commit=True)
            
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
@require_http_methods(["POST"])
def contractor_availability_delete(request, pk):
    """
    Delete contractor availability entry.
    
    Allows contractors to delete their own availability entries.
    """
    availability = get_object_or_404(ContractorAvailability, pk=pk)
    
    # Check permissions - contractor must own this availability or be admin
    if not (user_is_admin(request.user) or availability.contractor == request.user):
        messages.error(request, "You don't have permission to delete this availability.")
        return redirect('programs:contractor_availability_list')
    
    # Check if there are any confirmed sessions linked to this availability
    from django.db.models import Q
    linked_sessions = ProgramSession.objects.filter(
        availability_program__availability=availability,
        status__in=['scheduled', 'confirmed']
    )
    
    if linked_sessions.exists():
        messages.error(
            request, 
            "Cannot delete availability with scheduled or confirmed sessions. "
            "Please cancel the sessions first or archive this availability instead."
        )
        # Check if this is an HTMX request
        if request.headers.get('HX-Request'):
            # Return the updated list partial
            return contractor_availability_list_partial(request)
        return redirect('programs:contractor_availability_detail', pk=pk)
    
    # Delete the availability
    availability.delete()
    messages.success(request, "Availability deleted successfully.")
    
    # Check if this is an HTMX request
    if request.headers.get('HX-Request'):
        # Return the updated list partial
        return contractor_availability_list_partial(request)
    
    return redirect('programs:contractor_availability_list')


@login_required
def contractor_availability_list_partial(request):
    """HTMX partial: Return availability list grouped by status."""
    if not user_is_contractor(request.user) and not user_is_admin(request.user):
        return HttpResponse("Permission denied", status=403)
    
    now = timezone.now()
    
    # Get filters
    program_buildout_ids = request.GET.getlist('program_buildout_id')
    
    # Base queryset
    base_qs = ContractorAvailability.objects.filter(
        contractor=request.user,
        is_archived=False
    ).select_related('contractor').prefetch_related(
        'program_offerings__program_buildout__program_type',
        'program_offerings__sessions'
    )
    
    # Apply filters
    if program_buildout_ids:
        base_qs = base_qs.filter(
            program_offerings__program_buildout__id__in=program_buildout_ids
        ).distinct()
    
    # Group by status
    active_qs = base_qs.filter(
        start_datetime__lte=now,
        end_datetime__gte=now
    ).order_by('start_datetime')
    
    future_qs = base_qs.filter(
        start_datetime__gt=now
    ).order_by('start_datetime')
    
    past_qs = base_qs.filter(
        end_datetime__lt=now
    ).order_by('-start_datetime')
    
    context = {
        'active_availability': active_qs,
        'future_availability': future_qs,
        'past_availability': past_qs,
    }
    
    return render(request, 'programs/partials/_availability_list.html', context)


@login_required
def contractor_availability_calendar_partial(request):
    """HTMX partial: Return calendar month view."""
    if not user_is_contractor(request.user) and not user_is_admin(request.user):
        return HttpResponse("Permission denied", status=403)
    
    from .utils.calendar_utils import build_calendar_data, get_prev_month, get_next_month, get_month_bounds
    
    now = timezone.now()
    year = int(request.GET.get('year', now.year))
    month = int(request.GET.get('month', now.month))
    program_buildout_ids = request.GET.getlist('program_buildout_id')
    
    # Get availability for the month (with buffer)
    start_datetime, end_datetime = get_month_bounds(year, month)
    
    availability_qs = ContractorAvailability.objects.filter(
        contractor=request.user,
        is_archived=False,
        start_datetime__lte=end_datetime,
        end_datetime__gte=start_datetime
    ).select_related('contractor').prefetch_related(
        'program_offerings__program_buildout__program_type'
    )
    
    # Apply program buildout filter
    if program_buildout_ids:
        availability_qs = availability_qs.filter(
            program_offerings__program_buildout__id__in=program_buildout_ids
        ).distinct()
    
    # Build calendar data
    calendar_data = build_calendar_data(year, month, availability_qs)
    
    # Get prev/next month
    prev_year, prev_month = get_prev_month(year, month)
    next_year, next_month = get_next_month(year, month)
    
    context = {
        'calendar': calendar_data,
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
        'current_year': year,
        'current_month': month,
        'program_buildout_ids': program_buildout_ids,
        'view_type': 'contractor',
    }
    
    return render(request, 'programs/partials/_availability_calendar.html', context)


@login_required
@require_http_methods(["POST"])
def contractor_availability_archive(request):
    """
    Archive availability entries (per-row or bulk).
    
    POST params:
        - availability_id: single ID to archive
        - bulk_archive_past: if 'true', archive all past entries
    """
    if not user_is_contractor(request.user) and not user_is_admin(request.user):
        return HttpResponse("Permission denied", status=403)
    
    now = timezone.now()
    availability_id = request.POST.get('availability_id')
    bulk_archive_past = request.POST.get('bulk_archive_past') == 'true'
    
    if availability_id:
        # Archive single entry
        availability = get_object_or_404(
            ContractorAvailability,
            pk=availability_id,
            contractor=request.user
        )
        availability.is_archived = True
        availability.save(update_fields=['is_archived'])
        messages.success(request, "Availability archived successfully.")
    
    elif bulk_archive_past:
        # Bulk archive all past entries
        count = ContractorAvailability.objects.filter(
            contractor=request.user,
            end_datetime__lt=now,
            is_archived=False
        ).update(is_archived=True)
        messages.success(request, f"Archived {count} past availability entries.")
    
    # Return updated list partial
    return contractor_availability_list_partial(request)


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


# ============================================================================
# AVAILABILITY RULES VIEWS
# ============================================================================

@login_required
def availability_rules_index(request):
    """
    Main page showing contractor's availability rules and calendar.
    
    Shows:
    - Compact rules list (not daily instances)
    - Calendar (month or week toggle) with dynamic occurrences from rules
    - Filters by program instance and active/inactive
    """
    if not user_is_contractor(request.user) and not user_is_admin(request.user):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    # Enforce onboarding gate for contractors
    if user_is_contractor(request.user) and not user_is_admin(request.user):
        try:
            from people.models import Contractor
            contractor = Contractor.objects.filter(user=request.user).first()
            if not contractor or contractor.needs_onboarding:
                messages.warning(request, "Please complete onboarding (NDA and W-9) before managing availability.")
                return redirect('people:contractor_onboarding')
        except Exception:
            messages.error(request, "Unable to verify onboarding status.")
            return redirect('dashboard')
    
    # Get query parameters
    from datetime import date
    from dateutil.relativedelta import relativedelta
    
    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    view_mode = request.GET.get('view', 'month')  # 'month' or 'week'
    show_inactive = request.GET.get('show_inactive', 'false') == 'true'
    program_instance_ids = request.GET.getlist('program_instance')
    
    # Base queryset: rules for this contractor
    rules_qs = AvailabilityRule.objects.filter(
        contractor=request.user
    ).prefetch_related(
        'exceptions',
        'programs_offered__buildout__program_type'
    )
    
    # Filter by active/inactive
    if not show_inactive:
        rules_qs = rules_qs.filter(is_active=True)
    
    # Filter by program instance
    if program_instance_ids:
        rules_qs = rules_qs.filter(programs_offered__id__in=program_instance_ids).distinct()
    
    # Get all program instances the contractor is assigned to (for filter dropdown)
    from .models import InstanceRoleAssignment
    assigned_instance_ids = InstanceRoleAssignment.objects.filter(
        contractor=request.user
    ).values_list('instance_id', flat=True)
    program_instances = ProgramInstance.objects.filter(
        id__in=assigned_instance_ids
    ).select_related('buildout__program_type').order_by('buildout__program_type__name', 'title')
    
    context = {
        'rules': rules_qs,
        'year': year,
        'month': month,
        'view_mode': view_mode,
        'show_inactive': show_inactive,
        'program_instance_ids': program_instance_ids,
        'program_instances': program_instances,
        'can_create': True,
    }
    
    return render(request, 'programs/availability_rules/index.html', context)


@login_required
def availability_rules_calendar_partial(request):
    """HTMX partial: Render calendar grid with dynamic occurrences."""
    if not user_is_contractor(request.user) and not user_is_admin(request.user):
        return HttpResponse("Permission denied", status=403)
    
    from datetime import date
    from calendar import monthrange
    from .utils.occurrence_generator import generate_occurrences_for_rules
    from .models import ContractorDayOffRequest
    
    year = int(request.GET.get('year', date.today().year))
    month = int(request.GET.get('month', date.today().month))
    show_inactive = request.GET.get('show_inactive', 'false') == 'true'
    program_instance_ids = request.GET.getlist('program_instance')
    
    # Get rules
    rules_qs = AvailabilityRule.objects.filter(
        contractor=request.user
    ).prefetch_related(
        'exceptions',
        'programs_offered__buildout__program_type'
    )
    
    if not show_inactive:
        rules_qs = rules_qs.filter(is_active=True)
    
    if program_instance_ids:
        rules_qs = rules_qs.filter(programs_offered__id__in=program_instance_ids).distinct()
    
    # Calculate date range for the month
    first_day = date(year, month, 1)
    last_day_num = monthrange(year, month)[1]
    last_day = date(year, month, last_day_num)
    
    # Generate occurrences
    time_off_qs = ContractorDayOffRequest.objects.filter(contractor=request.user)
    occurrences = generate_occurrences_for_rules(
        rules_qs,
        first_day,
        last_day,
        include_time_off=True,
        time_off_queryset=time_off_qs
    )
    
    # Build calendar grid (using calendar_utils if available, or custom)
    import calendar as cal
    month_calendar = cal.monthcalendar(year, month)
    
    # Group occurrences by date
    occurrences_by_date = {}
    for occ in occurrences:
        if occ.date not in occurrences_by_date:
            occurrences_by_date[occ.date] = []
        occurrences_by_date[occ.date].append(occ)
    
    context = {
        'year': year,
        'month': month,
        'month_name': cal.month_name[month],
        'month_calendar': month_calendar,
        'occurrences_by_date': occurrences_by_date,
        'show_inactive': show_inactive,
        'program_instance_ids': program_instance_ids,
    }
    
    return render(request, 'programs/availability_rules/_calendar_month.html', context)


@login_required
def availability_rules_list_partial(request):
    """HTMX partial: Render rules list."""
    if not user_is_contractor(request.user) and not user_is_admin(request.user):
        return HttpResponse("Permission denied", status=403)
    
    show_inactive = request.GET.get('show_inactive', 'false') == 'true'
    program_instance_ids = request.GET.getlist('program_instance')
    
    rules_qs = AvailabilityRule.objects.filter(
        contractor=request.user
    ).prefetch_related('exceptions', 'programs_offered')
    
    if not show_inactive:
        rules_qs = rules_qs.filter(is_active=True)
    
    if program_instance_ids:
        rules_qs = rules_qs.filter(programs_offered__id__in=program_instance_ids).distinct()
    
    context = {
        'rules': rules_qs,
        'show_inactive': show_inactive,
    }
    
    return render(request, 'programs/availability_rules/_rules_list.html', context)


@login_required
def availability_rule_create(request):
    """Create new availability rule."""
    if not user_is_contractor(request.user) and not user_is_admin(request.user):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    # Enforce onboarding gate
    if user_is_contractor(request.user) and not user_is_admin(request.user):
        try:
            from people.models import Contractor
            contractor = Contractor.objects.filter(user=request.user).first()
            if not contractor or contractor.needs_onboarding:
                messages.warning(request, "Please complete onboarding before creating availability rules.")
                return redirect('people:contractor_onboarding')
        except Exception:
            messages.error(request, "Unable to verify onboarding status.")
            return redirect('dashboard')
    
    if request.method == 'POST':
        from .forms import AvailabilityRuleForm
        form = AvailabilityRuleForm(request.POST, contractor=request.user)
        if form.is_valid():
            rule = form.save(commit=False)
            rule.contractor = request.user
            rule.save()
            form.save_m2m()  # Save programs_offered
            
            messages.success(
                request,
                f"Availability rule '{rule.title or 'Untitled'}' created successfully!"
            )
            return redirect('programs:availability_rule_detail', pk=rule.pk)
    else:
        from .forms import AvailabilityRuleForm
        form = AvailabilityRuleForm(contractor=request.user)
    
    context = {
        'form': form,
        'action': 'Create',
    }
    
    return render(request, 'programs/availability_rules/form.html', context)


@login_required
def availability_rule_detail(request, pk):
    """View and edit availability rule with exceptions."""
    rule = get_object_or_404(AvailabilityRule, pk=pk)
    
    # Permission check: only owner or admin
    if rule.contractor != request.user and not user_is_admin(request.user):
        messages.error(request, "You don't have permission to view this rule.")
        return redirect('programs:availability_rules_index')
    
    if request.method == 'POST':
        from .forms import AvailabilityRuleForm, AvailabilityExceptionFormSet
        form = AvailabilityRuleForm(request.POST, instance=rule, contractor=request.user)
        exception_formset = AvailabilityExceptionFormSet(request.POST, instance=rule)
        
        if form.is_valid() and exception_formset.is_valid():
            rule = form.save()
            exception_formset.save()
            messages.success(request, "Availability rule updated successfully!")
            return redirect('programs:availability_rule_detail', pk=rule.pk)
    else:
        from .forms import AvailabilityRuleForm, AvailabilityExceptionFormSet
        form = AvailabilityRuleForm(instance=rule, contractor=request.user)
        exception_formset = AvailabilityExceptionFormSet(instance=rule)
    
    # Generate sample occurrences for preview (next 30 days)
    from datetime import date, timedelta
    from .utils.occurrence_generator import generate_occurrences_for_rules
    from .models import ContractorDayOffRequest
    
    today = date.today()
    end_date = today + timedelta(days=30)
    time_off_qs = ContractorDayOffRequest.objects.filter(contractor=request.user)
    occurrences = generate_occurrences_for_rules(
        AvailabilityRule.objects.filter(pk=rule.pk).prefetch_related('exceptions', 'programs_offered'),
        today,
        end_date,
        include_time_off=True,
        time_off_queryset=time_off_qs
    )
    
    context = {
        'rule': rule,
        'form': form,
        'exception_formset': exception_formset,
        'action': 'Edit',
        'occurrences_preview': occurrences[:10],  # Show first 10
    }
    
    return render(request, 'programs/availability_rules/detail.html', context)


@login_required
@require_POST
def availability_rule_toggle(request, pk):
    """Toggle is_active status of a rule."""
    rule = get_object_or_404(AvailabilityRule, pk=pk)
    
    # Permission check
    if rule.contractor != request.user and not user_is_admin(request.user):
        messages.error(request, "You don't have permission to modify this rule.")
        return redirect('programs:availability_rules_index')
    
    rule.is_active = not rule.is_active
    rule.save(update_fields=['is_active'])
    
    status = "activated" if rule.is_active else "deactivated"
    messages.success(request, f"Availability rule '{rule.title or 'Untitled'}' {status}.")
    
    return redirect('programs:availability_rules_index')


@login_required
@require_POST
def availability_rule_archive(request, pk):
    """Archive a rule (set is_active=False)."""
    rule = get_object_or_404(AvailabilityRule, pk=pk)
    
    # Permission check
    if rule.contractor != request.user and not user_is_admin(request.user):
        messages.error(request, "You don't have permission to modify this rule.")
        return redirect('programs:availability_rules_index')
    
    rule.is_active = False
    rule.save(update_fields=['is_active'])
    
    messages.success(request, f"Availability rule '{rule.title or 'Untitled'}' archived.")
    
    return redirect('programs:availability_rules_index')


@login_required
def availability_rule_delete(request, pk):
    """Delete a rule (with confirmation)."""
    rule = get_object_or_404(AvailabilityRule, pk=pk)
    
    # Permission check
    if rule.contractor != request.user and not user_is_admin(request.user):
        messages.error(request, "You don't have permission to delete this rule.")
        return redirect('programs:availability_rules_index')
    
    if request.method == 'POST':
        rule_title = rule.title or 'Untitled'
        rule.delete()
        messages.success(request, f"Availability rule '{rule_title}' deleted.")
        return redirect('programs:availability_rules_index')
    
    context = {
        'rule': rule,
    }
    
    return render(request, 'programs/availability_rules/confirm_delete.html', context)


@login_required
@require_POST
def availability_exception_create(request, rule_pk):
    """Create an exception for a rule (HTMX endpoint)."""
    rule = get_object_or_404(AvailabilityRule, pk=rule_pk)
    
    # Permission check
    if rule.contractor != request.user and not user_is_admin(request.user):
        return HttpResponse("Permission denied", status=403)
    
    from .forms import AvailabilityExceptionForm
    form = AvailabilityExceptionForm(request.POST)
    
    if form.is_valid():
        exception = form.save(commit=False)
        exception.rule = rule
        exception.save()
        
        # Return updated exceptions list partial
        context = {'rule': rule}
        return render(request, 'programs/availability_rules/_exceptions_list.html', context)
    
    # Return form with errors
    context = {'form': form, 'rule': rule}
    return render(request, 'programs/availability_rules/_exception_form.html', context)


@login_required
@require_POST
def availability_exception_delete(request, pk):
    """Delete an exception (HTMX endpoint)."""
    exception = get_object_or_404(AvailabilityException, pk=pk)
    rule = exception.rule
    
    # Permission check
    if rule.contractor != request.user and not user_is_admin(request.user):
        return HttpResponse("Permission denied", status=403)
    
    exception.delete()
    
    # Return updated exceptions list partial
    context = {'rule': rule}
    return render(request, 'programs/availability_rules/_exceptions_list.html', context)
