from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.forms import modelformset_factory
from django.db import transaction
import json

from .models import (
    ProgramType, ProgramInstance, RegistrationForm, FormQuestion,
    Child, Registration
)
from .forms import (
    ChildForm, RegistrationFormForm,
    FormQuestionForm, ProgramInstanceForm
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
        return redirect('dashboard')
    
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
    ).select_related('child', 'program_instance', 'program_instance__program_type')
    
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
    
    # Check if user is already registered
    user_registrations = []
    if user_is_parent(request.user):
        user_registrations = Registration.objects.filter(
            child__parent=request.user,
            program_instance=program_instance
        )
    
    context = {
        'program_instance': program_instance,
        'can_register': can_register,
        'user_registrations': user_registrations,
    }
    
    return render(request, 'programs/program_instance_detail.html', context)


@login_required
def register_child(request, program_instance_pk):
    """Register a child for a program instance."""
    if not user_is_parent(request.user):
        messages.error(request, "Access denied. Parent role required.")
        return redirect('programs:parent_dashboard')
    
    program_instance = get_object_or_404(ProgramInstance, pk=program_instance_pk, is_active=True)
    
    # Check if user has children
    children = request.user.children.all()
    if not children.exists():
        messages.error(request, "You must have at least one child registered to sign up for programs.")
        return redirect('programs:parent_dashboard')
    
    # Check if program is full
    if program_instance.is_full:
        messages.error(request, "This program is full.")
        return redirect('programs:program_instance_detail', pk=program_instance_pk)
    
    # Check if already registered
    existing_registration = Registration.objects.filter(
        child__parent=request.user,
        program_instance=program_instance
    ).first()
    
    if existing_registration:
        messages.error(request, "You are already registered for this program.")
        return redirect('programs:program_instance_detail', pk=program_instance_pk)
    
    if request.method == 'POST':
        child_id = request.POST.get('child')
        child = get_object_or_404(Child, pk=child_id, parent=request.user)
        
        # Create registration
        registration = Registration.objects.create(
            child=child,
            program_instance=program_instance,
            status='pending'
        )
        
        # If program has a form, redirect to form completion
        if program_instance.assigned_form:
            return redirect('programs:complete_registration_form', registration_pk=registration.pk)
        
        messages.success(request, f"Successfully registered {child.full_name} for {program_instance.program_type.name}")
        return redirect('programs:parent_dashboard')
    
    context = {
        'program_instance': program_instance,
        'children': children,
    }
    
    return render(request, 'programs/register_child.html', context)


@login_required
def complete_registration_form(request, registration_pk):
    """Complete registration form for a program."""
    registration = get_object_or_404(Registration, pk=registration_pk)
    
    # Check access
    if not (user_is_parent(registration.child.parent) or user_is_admin(request.user)):
        messages.error(request, "Access denied.")
        return redirect('programs:parent_dashboard')
    
    if not registration.program_instance.assigned_form:
        messages.error(request, "No form assigned to this program.")
        return redirect('programs:parent_dashboard')
    
    if request.method == 'POST':
        form_responses = {}
        form = registration.program_instance.assigned_form
        
        for question in form.questions.all():
            field_name = f"question_{question.pk}"
            value = request.POST.get(field_name)
            
            if question.is_required and not value:
                messages.error(request, f"Please answer all required questions.")
                break
            else:
                form_responses[str(question.pk)] = value
        else:
            # All questions answered
            registration.form_responses = form_responses
            registration.save()
            messages.success(request, "Registration form completed successfully!")
            return redirect('programs:parent_dashboard')
    
    context = {
        'registration': registration,
        'form': registration.program_instance.assigned_form,
    }
    
    return render(request, 'programs/complete_registration_form.html', context)


@login_required
def contractor_dashboard(request):
    """Contractor dashboard for managing programs and forms."""
    if not (user_is_contractor(request.user) or user_is_admin(request.user)):
        messages.error(request, "Access denied. Contractor or Admin role required.")
        return redirect('dashboard')
    
    # Get programs taught by this contractor
    if user_is_admin(request.user):
        program_instances = ProgramInstance.objects.all()
    else:
        program_instances = ProgramInstance.objects.filter(instructor=request.user)
    
    # Get forms created by this contractor
    if user_is_admin(request.user):
        forms = RegistrationForm.objects.all()
    else:
        forms = RegistrationForm.objects.filter(created_by=request.user)
    
    context = {
        'program_instances': program_instances,
        'forms': forms,
    }
    
    return render(request, 'programs/contractor_dashboard.html', context)


@login_required
def form_builder(request, form_pk=None):
    """Create or edit registration forms."""
    if not (user_is_contractor(request.user) or user_is_admin(request.user)):
        messages.error(request, "Access denied. Contractor or Admin role required.")
        return redirect('dashboard')
    
    form_instance = None
    if form_pk:
        form_instance = get_object_or_404(RegistrationForm, pk=form_pk)
        # Check if user can edit this form
        if not user_is_admin(request.user) and form_instance.created_by != request.user:
            messages.error(request, "Access denied.")
            return redirect('programs:contractor_dashboard')
    
    if request.method == 'POST':
        form = RegistrationFormForm(request.POST, instance=form_instance)
        if form.is_valid():
            form_instance = form.save(commit=False)
            form_instance.created_by = request.user
            form_instance.save()
            
            # Handle form questions via HTMX
            if request.headers.get('HX-Request'):
                return HttpResponse(
                    f'<div id="form-{form_instance.pk}" class="alert alert-success">Form saved!</div>'
                )
            
            messages.success(request, "Form saved successfully!")
            return redirect('programs:form_builder', form_pk=form_instance.pk)
    else:
        form = RegistrationFormForm(instance=form_instance)
    
    context = {
        'form': form,
        'form_instance': form_instance,
    }
    
    return render(request, 'programs/form_builder.html', context)


@login_required
def add_form_question(request, form_pk):
    """Add a question to a form via HTMX."""
    if not (user_is_contractor(request.user) or user_is_admin(request.user)):
        return HttpResponse("Access denied", status=403)
    
    form_instance = get_object_or_404(RegistrationForm, pk=form_pk)
    
    if not user_is_admin(request.user) and form_instance.created_by != request.user:
        return HttpResponse("Access denied", status=403)
    
    if request.method == 'POST':
        question_form = FormQuestionForm(request.POST)
        if question_form.is_valid():
            question = question_form.save(commit=False)
            question.form = form_instance
            question.save()
            
            return render(request, 'programs/partials/question_row.html', {
                'question': question
            })
    
    return HttpResponse("Invalid request", status=400)


@login_required
def delete_form_question(request, question_pk):
    """Delete a form question via HTMX."""
    if not (user_is_contractor(request.user) or user_is_admin(request.user)):
        return HttpResponse("Access denied", status=403)
    
    question = get_object_or_404(FormQuestion, pk=question_pk)
    
    if not user_is_admin(request.user) and question.form.created_by != request.user:
        return HttpResponse("Access denied", status=403)
    
    question.delete()
    return HttpResponse("Question deleted")


@login_required
def duplicate_form(request, form_pk):
    """Duplicate a registration form."""
    if not (user_is_contractor(request.user) or user_is_admin(request.user)):
        messages.error(request, "Access denied. Contractor or Admin role required.")
        return redirect('programs:contractor_dashboard')
    
    original_form = get_object_or_404(RegistrationForm, pk=form_pk)
    
    if not user_is_admin(request.user) and original_form.created_by != request.user:
        messages.error(request, "Access denied.")
        return redirect('programs:contractor_dashboard')
    
    new_form = original_form.duplicate()
    messages.success(request, f"Form '{original_form.title}' duplicated successfully!")
    
    return redirect('programs:form_builder', form_pk=new_form.pk)


@login_required
def manage_children(request):
    """Manage children for parents."""
    if not user_is_parent(request.user):
        messages.error(request, "Access denied. Parent role required.")
        return redirect('dashboard')
    
    children = request.user.children.all()
    
    if request.method == 'POST':
        form = ChildForm(request.POST)
        if form.is_valid():
            child = form.save(commit=False)
            child.parent = request.user
            child.save()
            messages.success(request, f"Child {child.full_name} added successfully!")
            return redirect('programs:manage_children')
    else:
        form = ChildForm()
    
    context = {
        'children': children,
        'form': form,
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
            messages.success(request, f"Child {child.full_name} updated successfully!")
            return redirect('programs:manage_children')
    else:
        form = ChildForm(instance=child)
    
    context = {
        'child': child,
        'form': form,
    }
    
    return render(request, 'programs/edit_child.html', context)


@login_required
def view_registrations(request, program_instance_pk):
    """View registrations for a program instance (contractors/admins)."""
    if not (user_is_contractor(request.user) or user_is_admin(request.user)):
        messages.error(request, "Access denied. Contractor or Admin role required.")
        return redirect('dashboard')
    
    program_instance = get_object_or_404(ProgramInstance, pk=program_instance_pk)
    
    # Check if user can view this program's registrations
    if not user_is_admin(request.user) and program_instance.instructor != request.user:
        messages.error(request, "Access denied.")
        return redirect('programs:contractor_dashboard')
    
    registrations = program_instance.registrations.all().select_related(
        'child', 'child__parent'
    )
    
    context = {
        'program_instance': program_instance,
        'registrations': registrations,
    }
    
    return render(request, 'programs/view_registrations.html', context)


@login_required
def update_registration_status(request, registration_pk):
    """Update registration status (contractors/admins)."""
    if not (user_is_contractor(request.user) or user_is_admin(request.user)):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    registration = get_object_or_404(Registration, pk=registration_pk)
    
    # Check if user can update this registration
    if not user_is_admin(request.user) and registration.program_instance.instructor != request.user:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Registration.STATUS_CHOICES):
            registration.status = new_status
            registration.save()
            return JsonResponse({'success': True, 'status': new_status})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def send_form_to_participants(request, program_instance_pk):
    """Send a form to all participants in a program."""
    if not (user_is_contractor(request.user) or user_is_admin(request.user)):
        messages.error(request, "Access denied. Contractor or Admin role required.")
        return redirect('dashboard')
    
    program_instance = get_object_or_404(ProgramInstance, pk=program_instance_pk)
    
    # Check if user can send forms for this program
    if not user_is_admin(request.user) and program_instance.instructor != request.user:
        messages.error(request, "Access denied.")
        return redirect('programs:contractor_dashboard')
    
    if request.method == 'POST':
        form_pk = request.POST.get('form')
        form = get_object_or_404(RegistrationForm, pk=form_pk)
        
        # Update program instance with assigned form
        program_instance.assigned_form = form
        program_instance.save()
        
        messages.success(request, f"Form '{form.title}' assigned to program successfully!")
        return redirect('programs:view_registrations', program_instance_pk=program_instance_pk)
    
    # Get available forms
    if user_is_admin(request.user):
        forms = RegistrationForm.objects.filter(is_active=True)
    else:
        forms = RegistrationForm.objects.filter(
            is_active=True,
            created_by=request.user
        )
    
    context = {
        'program_instance': program_instance,
        'forms': forms,
    }
    
    return render(request, 'programs/send_form_to_participants.html', context)
