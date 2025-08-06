from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.contrib.auth.models import Group

from accounts.models import User, Profile
from programs.models import (
    ProgramType, ProgramInstance, RegistrationForm, FormQuestion,
    Child, Registration, Role, ProgramBuildout, BuildoutResponsibility, 
    BuildoutRoleAssignment, BaseCost, BuildoutBaseCost, InstanceRoleAssignment
)
from communications.models import Contact
from accounts.mixins import role_required
from programs.forms import (
    ProgramTypeForm, ChildForm, RegistrationFormForm, RoleForm, ProgramBuildoutForm
)


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
    recent_programs = ProgramInstance.objects.select_related('buildout__program_type').order_by('-created_at')[:5]
    
    # Financial overview
    active_programs = ProgramInstance.objects.filter(is_active=True)
    total_revenue = sum(program.actual_revenue for program in active_programs)
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
    programs = ProgramInstance.objects.filter(contractor_assignments__contractor=user) if 'Contractor' in user.get_role_names() else None
    
    context = {
        'user_detail': user,
        'children': children,
        'programs': programs,
    }
    
    return render(request, 'admin_interface/user_detail.html', context)


@login_required
@role_required(['Admin'])
def user_edit(request, user_id):
    """Edit user information."""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        # Handle form submission
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        email = request.POST.get('email', '')
        is_active = request.POST.get('is_active') == 'on'
        is_staff = request.POST.get('is_staff') == 'on'
        
        # Update user fields
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.is_active = is_active
        user.is_staff = is_staff
        
        # Handle groups/roles
        selected_groups = request.POST.getlist('groups')
        user.groups.clear()
        for group_name in selected_groups:
            group, created = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)
        
        user.save()
        messages.success(request, f"User '{user.get_full_name()}' updated successfully!")
        return redirect('admin_interface:user_detail', user_id=user.id)
    
    # Get available groups
    available_groups = Group.objects.all()
    user_groups = user.groups.all()
    
    context = {
        'user_detail': user,
        'available_groups': available_groups,
        'user_groups': user_groups,
    }
    return render(request, 'admin_interface/user_edit.html', context)


@login_required
@role_required(['Admin'])
def program_type_management(request):
    """Program type management interface."""
    program_types = ProgramType.objects.prefetch_related('buildouts').order_by('-created_at')
    
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
def program_type_create(request):
    """Create a new program type."""
    if request.method == 'POST':
        form = ProgramTypeForm(request.POST)
        if form.is_valid():
            program_type = form.save()
            messages.success(request, f"Program type '{program_type.name}' created successfully!")
            return redirect('admin_interface:program_type_detail', program_type_id=program_type.id)
    else:
        form = ProgramTypeForm()
    
    context = {
        'form': form,
        'title': 'Create Program Type',
        'action': 'Create',
    }
    return render(request, 'admin_interface/program_type_form.html', context)


@login_required
@role_required(['Admin'])
def program_type_detail(request, program_type_id):
    """View program type details."""
    program_type = get_object_or_404(ProgramType, id=program_type_id)
    
    context = {
        'program_type': program_type,
        'instances': program_type.instances.all(),
        'buildouts': program_type.buildouts.all(),
        'roles': program_type.roles.all(),
    }
    return render(request, 'admin_interface/program_type_detail.html', context)


@login_required
@role_required(['Admin'])
def program_type_edit(request, program_type_id):
    """Edit a program type."""
    program_type = get_object_or_404(ProgramType, id=program_type_id)
    
    if request.method == 'POST':
        form = ProgramTypeForm(request.POST, instance=program_type)
        if form.is_valid():
            form.save()
            messages.success(request, f"Program type '{program_type.name}' updated successfully!")
            return redirect('admin_interface:program_type_detail', program_type_id=program_type.id)
    else:
        form = ProgramTypeForm(instance=program_type)
    
    context = {
        'form': form,
        'program_type': program_type,
        'title': f'Edit Program Type: {program_type.name}',
        'action': 'Update',
    }
    return render(request, 'admin_interface/program_type_form.html', context)


@login_required
@role_required(['Admin'])
def program_type_delete(request, program_type_id):
    """Delete a program type."""
    program_type = get_object_or_404(ProgramType, id=program_type_id)
    
    if request.method == 'POST':
        name = program_type.name
        program_type.delete()
        messages.success(request, f"Program type '{name}' deleted successfully!")
        return redirect('admin_interface:program_type_management')
    
    context = {
        'program_type': program_type,
    }
    return render(request, 'admin_interface/program_type_confirm_delete.html', context)


@login_required
@role_required(['Admin'])
def program_type_manage_roles(request, program_type_id):
    """Manage roles for a program type."""
    program_type = get_object_or_404(ProgramType, id=program_type_id)
    
    if request.method == 'POST':
        role_ids = request.POST.getlist('roles')
        # Note: In the new model structure, roles are managed through buildouts
        # This function now just shows which roles are available for the program type
        messages.success(request, f"Role management is now handled through buildouts for '{program_type.name}'")
        return redirect('admin_interface:program_type_detail', program_type_id=program_type.id)
    
    all_roles = Role.objects.all()
    # Get roles that are used in any buildouts for this program type
    selected_roles = Role.objects.filter(
        buildoutroleassignment__buildout__program_type=program_type
    ).distinct()
    
    context = {
        'program_type': program_type,
        'all_roles': all_roles,
        'selected_roles': selected_roles,
    }
    return render(request, 'admin_interface/program_type_manage_roles.html', context)


@login_required
@role_required(['Admin'])
def program_type_manage_costs(request, program_type_id):
    """Manage costs for a program type."""
    program_type = get_object_or_404(ProgramType, id=program_type_id)
    
    if request.method == 'POST':
        cost_ids = request.POST.getlist('costs')
        # Note: In the new model structure, costs are managed through buildouts
        # This function now just shows which costs are available for the program type
        messages.success(request, f"Cost management is now handled through buildouts for '{program_type.name}'")
        return redirect('admin_interface:program_type_detail', program_type_id=program_type.id)
    
    all_costs = BaseCost.objects.all()
    # Get costs that are used in any buildouts for this program type
    selected_costs = BaseCost.objects.filter(
        buildoutbasecost__buildout__program_type=program_type
    ).distinct()
    
    context = {
        'program_type': program_type,
        'all_costs': all_costs,
        'selected_costs': selected_costs,
    }
    return render(request, 'admin_interface/program_type_manage_costs.html', context)


@login_required
@role_required(['Admin'])
def program_instance_management(request):
    """Program instance management interface."""
    instances = ProgramInstance.objects.select_related(
        'buildout__program_type'
    ).prefetch_related('registrations').order_by('-created_at')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        instances = instances.filter(
            Q(buildout__program_type__name__icontains=search) |
            Q(location__icontains=search) |
            Q(title__icontains=search)
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
def role_create(request):
    """Create a new role."""
    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            role = form.save()
            messages.success(request, f"Role '{role.name}' created successfully!")
            return redirect('admin_interface:role_detail', role_id=role.id)
    else:
        form = RoleForm()
    
    context = {
        'form': form,
        'title': 'Create Role',
        'action': 'Create',
    }
    return render(request, 'admin_interface/role_form.html', context)


@login_required
@role_required(['Admin'])
def role_detail(request, role_id):
    """View role details."""
    role = get_object_or_404(Role, id=role_id)
    
    # Get program types through ProgramRole
    program_types = [pr.program_type for pr in ProgramRole.objects.filter(role=role)]
    # Get users through groups (since Role doesn't have direct user relationship)
    users = User.objects.filter(groups__name=role.name)
    
    context = {
        'role': role,
        'program_types': program_types,
        'users': users,
    }
    return render(request, 'admin_interface/role_detail.html', context)


@login_required
@role_required(['Admin'])
def role_edit(request, role_id):
    """Edit a role."""
    role = get_object_or_404(Role, id=role_id)
    
    if request.method == 'POST':
        form = RoleForm(request.POST, instance=role)
        if form.is_valid():
            form.save()
            messages.success(request, f"Role '{role.name}' updated successfully!")
            return redirect('admin_interface:role_detail', role_id=role.id)
    else:
        form = RoleForm(instance=role)
    
    context = {
        'form': form,
        'role': role,
        'title': f'Edit Role: {role.name}',
        'action': 'Update',
    }
    return render(request, 'admin_interface/role_form.html', context)


@login_required
@role_required(['Admin'])
def role_delete(request, role_id):
    """Delete a role."""
    role = get_object_or_404(Role, id=role_id)
    
    if request.method == 'POST':
        name = role.name
        role.delete()
        messages.success(request, f"Role '{name}' deleted successfully!")
        return redirect('admin_interface:role_management')
    
    context = {
        'role': role,
    }
    return render(request, 'admin_interface/role_confirm_delete.html', context)


@login_required
@role_required(['Admin'])
def role_manage_program_types(request, role_id):
    """Manage program types for a role."""
    role = get_object_or_404(Role, id=role_id)
    
    if request.method == 'POST':
        program_type_ids = request.POST.getlist('program_types')
        # Note: In the new model structure, role-program type relationships are managed through buildouts
        # This function now just shows which program types use this role
        messages.success(request, f"Role-program type management is now handled through buildouts for '{role.name}'")
        return redirect('admin_interface:role_detail', role_id=role.id)
    
    all_program_types = ProgramType.objects.all()
    # Get program types that use this role in any buildouts
    selected_program_types = ProgramType.objects.filter(
        buildouts__role_assignments__role=role
    ).distinct()
    
    context = {
        'role': role,
        'all_program_types': all_program_types,
        'selected_program_types': selected_program_types,
    }
    return render(request, 'admin_interface/role_manage_program_types.html', context)


@login_required
@role_required(['Admin'])
def role_manage_users(request, role_id):
    """Manage users for a role."""
    role = get_object_or_404(Role, id=role_id)
    
    if request.method == 'POST':
        user_ids = request.POST.getlist('users')
        # Note: Since Role doesn't have a direct many-to-many with User,
        # we'll need to handle this through groups or a different mechanism
        # For now, we'll just show a message that this needs to be implemented
        messages.success(request, f"User management for roles needs to be implemented through groups.")
        return redirect('admin_interface:role_detail', role_id=role.id)
    
    all_users = User.objects.all()
    # Since there's no direct relationship, we'll show all users for now
    selected_users = []
    
    context = {
        'role': role,
        'all_users': all_users,
        'selected_users': selected_users,
    }
    return render(request, 'admin_interface/role_manage_users.html', context)


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
def buildout_create(request):
    """Create a new buildout."""
    if request.method == 'POST':
        form = ProgramBuildoutForm(request.POST)
        if form.is_valid():
            buildout = form.save()
            messages.success(request, f"Buildout '{buildout.title}' created successfully!")
            return redirect('admin_interface:buildout_detail', buildout_id=buildout.id)
    else:
        form = ProgramBuildoutForm()
    
    context = {
        'form': form,
        'action': 'Create',
    }
    return render(request, 'admin_interface/buildout_form.html', context)


@login_required
@role_required(['Admin'])
def buildout_detail(request, buildout_id):
    """View buildout details."""
    buildout = get_object_or_404(ProgramBuildout, id=buildout_id)
    
    # Get related program instances
    instances = ProgramInstance.objects.filter(buildout=buildout)
    
    # Calculate total sessions per year
    total_sessions_per_year = buildout.total_sessions_per_year
    
    context = {
        'buildout': buildout,
        'instances': instances,
        'total_sessions_per_year': total_sessions_per_year,
    }
    return render(request, 'admin_interface/buildout_detail.html', context)


@login_required
@role_required(['Admin'])
def buildout_edit(request, buildout_id):
    """Edit a buildout."""
    buildout = get_object_or_404(ProgramBuildout, id=buildout_id)
    
    if request.method == 'POST':
        form = ProgramBuildoutForm(request.POST, instance=buildout)
        if form.is_valid():
            buildout = form.save()
            messages.success(request, f"Buildout '{buildout.title}' updated successfully!")
            return redirect('admin_interface:buildout_detail', buildout_id=buildout.id)
    else:
        form = ProgramBuildoutForm(instance=buildout)
    
    context = {
        'form': form,
        'buildout': buildout,
        'action': 'Edit',
    }
    return render(request, 'admin_interface/buildout_form.html', context)


@login_required
@role_required(['Admin'])
def buildout_delete(request, buildout_id):
    """Delete a buildout."""
    buildout = get_object_or_404(ProgramBuildout, id=buildout_id)
    
    if request.method == 'POST':
        name = buildout.title
        buildout.delete()
        messages.success(request, f"Buildout '{name}' deleted successfully!")
        return redirect('admin_interface:buildout_management')
    
    context = {
        'buildout': buildout,
    }
    return render(request, 'admin_interface/buildout_confirm_delete.html', context)


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
def form_create(request):
    """Create a new form."""
    if request.method == 'POST':
        form = RegistrationFormForm(request.POST)
        if form.is_valid():
            form_instance = form.save(commit=False)
            form_instance.created_by = request.user
            form_instance.save()
            messages.success(request, f"Form '{form_instance.title}' created successfully!")
            return redirect('admin_interface:form_detail', form_id=form_instance.id)
    else:
        form = RegistrationFormForm()
    
    context = {
        'form': form,
        'title': 'Create Form',
        'action': 'Create',
    }
    return render(request, 'admin_interface/form_form.html', context)


@login_required
@role_required(['Admin'])
def form_detail(request, form_id):
    """View form details."""
    form_instance = get_object_or_404(RegistrationForm, id=form_id)
    
    context = {
        'form_instance': form_instance,
        'questions': form_instance.questions.all().order_by('order'),
    }
    return render(request, 'admin_interface/form_detail.html', context)


@login_required
@role_required(['Admin'])
def form_edit(request, form_id):
    """Edit a form."""
    form_instance = get_object_or_404(RegistrationForm, id=form_id)
    
    if request.method == 'POST':
        form = RegistrationFormForm(request.POST, instance=form_instance)
        if form.is_valid():
            form.save()
            messages.success(request, f"Form '{form_instance.title}' updated successfully!")
            return redirect('admin_interface:form_detail', form_id=form_instance.id)
    else:
        form = RegistrationFormForm(instance=form_instance)
    
    context = {
        'form': form,
        'form_instance': form_instance,
        'title': f'Edit Form: {form_instance.title}',
        'action': 'Update',
    }
    return render(request, 'admin_interface/form_form.html', context)


@login_required
@role_required(['Admin'])
def form_delete(request, form_id):
    """Delete a form."""
    form_instance = get_object_or_404(RegistrationForm, id=form_id)
    
    if request.method == 'POST':
        title = form_instance.title
        form_instance.delete()
        messages.success(request, f"Form '{title}' deleted successfully!")
        return redirect('admin_interface:form_management')
    
    context = {
        'form_instance': form_instance,
    }
    return render(request, 'admin_interface/form_confirm_delete.html', context)


@login_required
@role_required(['Admin'])
def form_duplicate(request, form_id):
    """Duplicate a form."""
    form_instance = get_object_or_404(RegistrationForm, id=form_id)
    new_form = form_instance.duplicate()
    
    messages.success(request, f"Form '{form_instance.title}' duplicated successfully!")
    return redirect('admin_interface:form_detail', form_id=new_form.id)


@login_required
@role_required(['Admin'])
def form_manage_questions(request, form_id):
    """Manage questions for a form."""
    form_instance = get_object_or_404(RegistrationForm, id=form_id)
    
    if request.method == 'POST':
        # Handle question reordering or other question management
        messages.success(request, f"Questions updated for '{form_instance.title}' successfully!")
        return redirect('admin_interface:form_detail', form_id=form_instance.id)
    
    questions = form_instance.questions.all().order_by('order')
    
    context = {
        'form_instance': form_instance,
        'questions': questions,
    }
    return render(request, 'admin_interface/form_manage_questions.html', context)


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


@login_required
@role_required(['Admin'])
def child_create(request):
    """Create a new child."""
    if request.method == 'POST':
        form = ChildForm(request.POST)
        if form.is_valid():
            child = form.save()
            messages.success(request, f"Child '{child.full_name}' created successfully!")
            return redirect('admin_interface:child_detail', child_id=child.id)
    else:
        form = ChildForm()
    
    context = {
        'form': form,
        'title': 'Create Child',
        'action': 'Create',
    }
    return render(request, 'admin_interface/child_form.html', context)


@login_required
@role_required(['Admin'])
def child_detail(request, child_id):
    """View child details."""
    child = get_object_or_404(Child, id=child_id)
    
    context = {
        'child': child,
        'registrations': child.registrations.all(),
    }
    return render(request, 'admin_interface/child_detail.html', context)


@login_required
@role_required(['Admin'])
def child_edit(request, child_id):
    """Edit a child."""
    child = get_object_or_404(Child, id=child_id)
    
    if request.method == 'POST':
        form = ChildForm(request.POST, instance=child)
        if form.is_valid():
            form.save()
            messages.success(request, f"Child '{child.full_name}' updated successfully!")
            return redirect('admin_interface:child_detail', child_id=child.id)
    else:
        form = ChildForm(instance=child)
    
    context = {
        'form': form,
        'child': child,
        'title': f'Edit Child: {child.full_name}',
        'action': 'Update',
    }
    return render(request, 'admin_interface/child_form.html', context)


@login_required
@role_required(['Admin'])
def child_delete(request, child_id):
    """Delete a child."""
    child = get_object_or_404(Child, id=child_id)
    
    if request.method == 'POST':
        name = child.full_name
        child.delete()
        messages.success(request, f"Child '{name}' deleted successfully!")
        return redirect('admin_interface:child_management')
    
    context = {
        'child': child,
    }
    return render(request, 'admin_interface/child_confirm_delete.html', context)


@login_required
@role_required(['Admin'])
def child_registrations(request, child_id):
    """View child registrations."""
    child = get_object_or_404(Child, id=child_id)
    registrations = child.registrations.all().order_by('-registered_at')
    
    context = {
        'child': child,
        'registrations': registrations,
    }
    return render(request, 'admin_interface/child_registrations.html', context)


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
