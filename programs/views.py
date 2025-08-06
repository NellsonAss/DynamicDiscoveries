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
    Child, Registration, Role, ProgramBuildout, BuildoutResponsibility, 
    BuildoutRoleAssignment, BaseCost, BuildoutBaseCost, InstanceRoleAssignment
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
                
                messages.success(request, f"Successfully registered {child.full_name} for {program_instance.program_type.name}.")
                
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
    
    # Get programs where user is instructor
    if user_is_contractor(request.user):
        programs = ProgramInstance.objects.filter(
            instructor=request.user,
            is_active=True
        ).order_by('-start_date')
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
        'programs': programs,
        'forms': forms,
    }
    
    return render(request, 'programs/contractor_dashboard.html', context)


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
    
    # Check if user is instructor or admin
    if user_is_contractor(request.user) and program_instance.instructor != request.user:
        messages.error(request, "Access denied. You can only view registrations for your own programs.")
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
    
    # Check if user is instructor or admin
    if user_is_contractor(request.user) and program_instance.instructor != request.user:
        messages.error(request, "Access denied. You can only send forms for your own programs.")
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
    
    roles = Role.objects.all().order_by('name')
    
    context = {
        'roles': roles,
    }
    
    return render(request, 'programs/role_list.html', context)


@login_required
def buildout_list(request):
    """List all program buildouts for Admin and Contractor users."""
    if not (user_is_admin(request.user) or user_is_contractor(request.user)):
        messages.error(request, "Access denied. Admin or Contractor role required.")
        return redirect('dashboard')
    
    buildouts = ProgramBuildout.objects.select_related('program_type').all().order_by('program_type__name', 'title')
    
    context = {
        'buildouts': buildouts,
    }
    
    return render(request, 'programs/buildout_list.html', context)


@login_required
def buildout_detail(request, buildout_pk):
    """Show detailed view of a program buildout."""
    if not (user_is_admin(request.user) or user_is_contractor(request.user)):
        messages.error(request, "Access denied. Admin or Contractor role required.")
        return redirect('dashboard')
    
    buildout = get_object_or_404(ProgramBuildout, pk=buildout_pk)
    
    # Calculate summary statistics using the new model structure
    total_hours = sum(
        role.calculate_total_hours(
            buildout.expected_students, 
            buildout.num_days, 
            buildout.sessions_per_day
        ) for role in buildout.program_type.roles.all()
    )
    total_revenue = buildout.total_revenue
    total_payouts = buildout.total_payouts
    profit = buildout.profit
    profit_margin = buildout.profit_margin
    
    # Prepare role data for template
    roles_data = []
    for role in buildout.program_type.roles.all():
        hours = role.calculate_total_hours(
            buildout.expected_students, 
            buildout.num_days, 
            buildout.sessions_per_day
        )
        payout = role.calculate_payout(
            buildout.expected_students, 
            buildout.num_days, 
            buildout.sessions_per_day
        )
        percentage = role.calculate_percentage_of_revenue(
            buildout.expected_students, 
            buildout.num_days, 
            buildout.sessions_per_day
        )
        roles_data.append({
            'role': role,
            'hours': hours,
            'payout': payout,
            'percentage': percentage
        })
    
    context = {
        'buildout': buildout,
        'total_hours': total_hours,
        'total_revenue': total_revenue,
        'total_payouts': total_payouts,
        'profit': profit,
        'profit_margin': profit_margin,
        'roles_data': roles_data,
    }
    
    return render(request, 'programs/buildout_detail.html', context)


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
