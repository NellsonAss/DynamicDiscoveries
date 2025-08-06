from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta

from accounts.models import User, Profile
from programs.models import (
    ProgramType, ProgramInstance, RegistrationForm, FormQuestion,
    Child, Registration, Role, ProgramBuildout, ProgramRole, BaseCost, ProgramBaseCost
)
from communications.models import Contact
from accounts.mixins import role_required


@login_required
@role_required(['Admin'])
def admin_dashboard(request):
    """Main admin dashboard with overview statistics."""
    # Get statistics
    total_users = User.objects.count()
    total_programs = ProgramType.objects.count()
    total_instances = ProgramInstance.objects.count()
    total_registrations = Registration.objects.count()
    total_contacts = Contact.objects.count()
    
    # Recent activity
    recent_registrations = Registration.objects.select_related('child', 'program_instance').order_by('-registered_at')[:5]
    recent_contacts = Contact.objects.order_by('-created_at')[:5]
    recent_programs = ProgramInstance.objects.select_related('program_type', 'instructor').order_by('-created_at')[:5]
    
    # Financial overview
    active_programs = ProgramInstance.objects.filter(is_active=True)
    total_revenue = sum(program.expected_revenue for program in active_programs)
    total_profit = sum(program.expected_profit for program in active_programs)
    
    context = {
        'total_users': total_users,
        'total_programs': total_programs,
        'total_instances': total_instances,
        'total_registrations': total_registrations,
        'total_contacts': total_contacts,
        'total_revenue': total_revenue,
        'total_profit': total_profit,
        'recent_registrations': recent_registrations,
        'recent_contacts': recent_contacts,
        'recent_programs': recent_programs,
        'today': timezone.now(),
    }
    
    return render(request, 'admin_interface/dashboard.html', context)


@login_required
@role_required(['Admin'])
def user_management(request):
    """User management interface."""
    users = User.objects.select_related('profile').prefetch_related('groups').order_by('-date_joined')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        users = users.filter(
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    # Filter by role
    role_filter = request.GET.get('role', '')
    if role_filter:
        users = users.filter(groups__name=role_filter)
    
    # Pagination
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get available roles for filter
    roles = User.objects.values_list('groups__name', flat=True).distinct()
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'role_filter': role_filter,
        'roles': roles,
    }
    
    return render(request, 'admin_interface/user_management.html', context)


@login_required
@role_required(['Admin'])
def user_detail(request, user_id):
    """User detail view."""
    user = get_object_or_404(User, id=user_id)
    
    # Get user's children if they're a parent
    children = Child.objects.filter(parent=user) if 'Parent' in user.get_role_names() else None
    
    # Get user's programs if they're a contractor
    programs = ProgramInstance.objects.filter(instructor=user) if 'Contractor' in user.get_role_names() else None
    
    context = {
        'user_detail': user,
        'children': children,
        'programs': programs,
    }
    
    return render(request, 'admin_interface/user_detail.html', context)


@login_required
@role_required(['Admin'])
def program_type_management(request):
    """Program type management interface."""
    program_types = ProgramType.objects.prefetch_related('roles', 'base_costs').order_by('-created_at')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        program_types = program_types.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(program_types, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
    }
    
    return render(request, 'admin_interface/program_type_management.html', context)


@login_required
@role_required(['Admin'])
def program_instance_management(request):
    """Program instance management interface."""
    instances = ProgramInstance.objects.select_related(
        'program_type', 'instructor', 'buildout'
    ).prefetch_related('registrations').order_by('-created_at')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        instances = instances.filter(
            Q(program_type__name__icontains=search) |
            Q(location__icontains=search) |
            Q(instructor__email__icontains=search)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        instances = instances.filter(is_active=True)
    elif status_filter == 'inactive':
        instances = instances.filter(is_active=False)
    
    # Pagination
    paginator = Paginator(instances, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
    }
    
    return render(request, 'admin_interface/program_instance_management.html', context)


@login_required
@role_required(['Admin'])
def registration_management(request):
    """Registration management interface."""
    registrations = Registration.objects.select_related(
        'child', 'program_instance', 'program_instance__program_type'
    ).order_by('-registered_at')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        registrations = registrations.filter(
            Q(child__first_name__icontains=search) |
            Q(child__last_name__icontains=search) |
            Q(child__parent__email__icontains=search) |
            Q(program_instance__program_type__name__icontains=search)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        registrations = registrations.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(registrations, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
    }
    
    return render(request, 'admin_interface/registration_management.html', context)


@login_required
@role_required(['Admin'])
def contact_management(request):
    """Contact management interface."""
    contacts = Contact.objects.order_by('-created_at')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        contacts = contacts.filter(
            Q(parent_name__icontains=search) |
            Q(email__icontains=search) |
            Q(message__icontains=search)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        contacts = contacts.filter(status=status_filter)
    
    # Filter by interest
    interest_filter = request.GET.get('interest', '')
    if interest_filter:
        contacts = contacts.filter(interest=interest_filter)
    
    # Pagination
    paginator = Paginator(contacts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
        'interest_filter': interest_filter,
    }
    
    return render(request, 'admin_interface/contact_management.html', context)


@login_required
@role_required(['Admin'])
def role_management(request):
    """Role management interface."""
    roles = Role.objects.order_by('name')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        roles = roles.filter(
            Q(name__icontains=search) |
            Q(responsibilities__icontains=search)
        )
    
    context = {
        'roles': roles,
        'search': search,
    }
    
    return render(request, 'admin_interface/role_management.html', context)


@login_required
@role_required(['Admin'])
def cost_management(request):
    """Base cost management interface."""
    costs = BaseCost.objects.order_by('name')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        costs = costs.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    context = {
        'costs': costs,
        'search': search,
    }
    
    return render(request, 'admin_interface/cost_management.html', context)


@login_required
@role_required(['Admin'])
def buildout_management(request):
    """Program buildout management interface."""
    buildouts = ProgramBuildout.objects.select_related('program_type').order_by('program_type__name', 'title')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        buildouts = buildouts.filter(
            Q(title__icontains=search) |
            Q(program_type__name__icontains=search)
        )
    
    # Filter by program type
    program_type_filter = request.GET.get('program_type', '')
    if program_type_filter:
        buildouts = buildouts.filter(program_type_id=program_type_filter)
    
    # Pagination
    paginator = Paginator(buildouts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get program types for filter
    program_types = ProgramType.objects.all()
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'program_type_filter': program_type_filter,
        'program_types': program_types,
    }
    
    return render(request, 'admin_interface/buildout_management.html', context)


@login_required
@role_required(['Admin'])
def form_management(request):
    """Registration form management interface."""
    forms = RegistrationForm.objects.select_related('created_by').prefetch_related('questions').order_by('-created_at')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        forms = forms.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(created_by__email__icontains=search)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        forms = forms.filter(is_active=True)
    elif status_filter == 'inactive':
        forms = forms.filter(is_active=False)
    
    # Pagination
    paginator = Paginator(forms, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
    }
    
    return render(request, 'admin_interface/form_management.html', context)


@login_required
@role_required(['Admin'])
def child_management(request):
    """Child management interface."""
    children = Child.objects.select_related('parent').prefetch_related('registrations').order_by('-created_at')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        children = children.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(parent__email__icontains=search)
        )
    
    # Filter by grade level
    grade_filter = request.GET.get('grade', '')
    if grade_filter:
        children = children.filter(grade_level=grade_filter)
    
    # Pagination
    paginator = Paginator(children, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'grade_filter': grade_filter,
    }
    
    return render(request, 'admin_interface/child_management.html', context)


# AJAX endpoints for quick actions
@login_required
@role_required(['Admin'])
@require_http_methods(['POST'])
def toggle_user_status(request, user_id):
    """Toggle user active status."""
    user = get_object_or_404(User, id=user_id)
    user.is_active = not user.is_active
    user.save()
    
    return JsonResponse({
        'success': True,
        'is_active': user.is_active,
        'message': f"User {'activated' if user.is_active else 'deactivated'} successfully"
    })


@login_required
@role_required(['Admin'])
@require_http_methods(['POST'])
def update_contact_status(request, contact_id):
    """Update contact status."""
    contact = get_object_or_404(Contact, id=contact_id)
    new_status = request.POST.get('status')
    

    
    if new_status in dict(Contact.STATUS_CHOICES):
        contact.status = new_status
        contact.save()
        
        return JsonResponse({
            'success': True,
            'status': contact.get_status_display(),
            'message': f"Contact status updated to {contact.get_status_display()}"
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid status'}, status=400)


@login_required
@role_required(['Admin'])
@require_http_methods(['POST'])
def toggle_program_instance_status(request, instance_id):
    """Toggle program instance active status."""
    instance = get_object_or_404(ProgramInstance, id=instance_id)
    instance.is_active = not instance.is_active
    instance.save()
    
    return JsonResponse({
        'success': True,
        'is_active': instance.is_active,
        'message': f"Program instance {'activated' if instance.is_active else 'deactivated'} successfully"
    })


@login_required
@role_required(['Admin'])
@require_http_methods(['POST'])
def update_registration_status(request, registration_id):
    """Update registration status."""
    registration = get_object_or_404(Registration, id=registration_id)
    new_status = request.POST.get('status')
    
    if new_status in dict(Registration.STATUS_CHOICES):
        registration.status = new_status
        registration.save()
        
        return JsonResponse({
            'success': True,
            'status': registration.get_status_display(),
            'message': f"Registration status updated to {registration.get_status_display()}"
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid status'}, status=400)
