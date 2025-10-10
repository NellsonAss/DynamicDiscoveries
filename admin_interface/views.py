from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.forms import ValidationError as FormValidationError
from decimal import Decimal
import decimal

from programs.models import (
    ProgramType, ProgramBuildout, ProgramInstance, Role, Responsibility,
    BuildoutRoleLine, BuildoutResponsibilityLine, BaseCost,
    BuildoutBaseCostAssignment, BuildoutLocationAssignment, Location, RegistrationForm, FormQuestion, Child,
    Registration, InstanceRoleAssignment, ProgramRequest
)
from communications.models import Contact
from people.models import Contractor, NDASignature
from programs.forms import (
    ProgramTypeForm, ProgramBuildoutForm, RoleForm, ResponsibilityForm,
    BaseCostForm, BuildoutRoleAssignmentForm, BuildoutResponsibilityAssignmentForm,
    BuildoutBaseCostAssignmentForm, BuildoutBaseCostAssignmentFormSet,
    BuildoutLocationAssignmentForm, BuildoutLocationAssignmentFormSet,
    RegistrationFormForm, FormQuestionForm
)
from admin_interface.forms import AdminProgramInstanceForm
from accounts.mixins import role_required

User = get_user_model()


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
    recent_programs = ProgramInstance.objects.select_related('buildout__program_type').prefetch_related('contractor_assignments__contractor').order_by('-created_at')[:5]
    
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
    users = User.objects.select_related('profile', 'contractor').prefetch_related('groups').order_by('-date_joined')
    
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
    
    # Get contractor profile if they're a contractor
    contractor = None
    if 'Contractor' in user.get_role_names():
        try:
            contractor = Contractor.objects.get(user=user)
        except Contractor.DoesNotExist:
            contractor = None
    
    context = {
        'user_detail': user,
        'children': children,
        'programs': programs,
        'contractor': contractor,
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
    program_types = ProgramType.objects.prefetch_related(
        'buildouts__role_lines__role',
        'buildouts__base_cost_assignments__base_cost'
    ).order_by('-created_at')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        program_types = program_types.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Add instance counts to each program type
    total_instances = 0
    total_buildouts = 0
    for program_type in program_types:
        instance_count = ProgramInstance.objects.filter(buildout__program_type=program_type).count()
        program_type.instance_count = instance_count
        total_instances += instance_count
        total_buildouts += program_type.buildouts.count()
    
    # Pagination
    paginator = Paginator(program_types, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'total_instances': total_instances,
        'total_buildouts': total_buildouts,
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
    
    # Get instances and buildouts
    instances = ProgramInstance.objects.filter(buildout__program_type=program_type)
    buildouts = program_type.buildouts.all()
    
    context = {
        'program_type': program_type,
        'instances': instances,
        'buildouts': buildouts,
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
    
    # Add instance count
    program_type.instance_count = ProgramInstance.objects.filter(buildout__program_type=program_type).count()
    
    context = {
        'program_type': program_type,
    }
    return render(request, 'admin_interface/program_type_confirm_delete.html', context)


@login_required
@role_required(['Admin'])
def program_type_manage_roles(request, program_type_id):
    """Manage roles for a program type - redirects to buildout management."""
    program_type = get_object_or_404(ProgramType, id=program_type_id)
    messages.info(request, f"Role management for '{program_type.name}' is now handled through buildouts. Redirecting to buildout management.")
    return redirect('admin_interface:buildout_management')





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
        'child', 'program_instance', 'program_instance__buildout', 'program_instance__buildout__program_type'
    ).order_by('-registered_at')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        registrations = registrations.filter(
            Q(child__first_name__icontains=search) |
            Q(child__last_name__icontains=search) |
            Q(child__parent__email__icontains=search) |
            Q(program_instance__buildout__program_type__name__icontains=search)
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
    roles = Role.objects.prefetch_related('user_assignments__user').order_by('title')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        roles = roles.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(default_responsibilities__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(roles, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
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
            messages.success(request, f"Role '{role.title}' created successfully!")
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
    
    # Get program types through buildouts
    program_types = ProgramType.objects.filter(
        buildouts__role_lines__role=role
    ).distinct()
    # Get users through role assignments
    users = role.get_assigned_users()
    # Get responsibilities for this role
    responsibilities = role.responsibilities.all()
    
    context = {
        'role': role,
        'program_types': program_types,
        'users': users,
        'responsibilities': responsibilities,
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
            messages.success(request, f"Role '{role.title}' updated successfully!")
            return redirect('admin_interface:role_detail', role_id=role.id)
    else:
        form = RoleForm(instance=role)
    
    context = {
        'form': form,
        'role': role,
        'title': f'Edit Role: {role.title}',
        'action': 'Update',
    }
    return render(request, 'admin_interface/role_form.html', context)


@login_required
@role_required(['Admin'])
def role_delete(request, role_id):
    """Delete a role."""
    role = get_object_or_404(Role, id=role_id)
    
    if request.method == 'POST':
        title = role.title
        role.delete()
        messages.success(request, f"Role '{title}' deleted successfully!")
        return redirect('admin_interface:role_management')
    
    context = {
        'role': role,
    }
    return render(request, 'admin_interface/role_confirm_delete.html', context)


@login_required
@role_required(['Admin'])
def role_manage_users(request, role_id):
    """Manage users for a role with individual add/remove actions."""
    from programs.models import RoleAssignment
    
    role = get_object_or_404(Role, id=role_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')
        
        if action and user_id:
            user = get_object_or_404(User, id=user_id)
            
            if action == 'add':
                assignment, created = RoleAssignment.objects.get_or_create(
                    user=user,
                    role=role,
                    defaults={'assigned_by': request.user}
                )
                if created:
                    messages.success(request, f"Added {user.get_full_name() or user.username} to role '{role.title}'.")
                else:
                    messages.info(request, f"{user.get_full_name() or user.username} is already assigned to this role.")
                    
            elif action == 'remove':
                deleted_count = RoleAssignment.objects.filter(
                    user=user,
                    role=role
                ).delete()[0]
                if deleted_count > 0:
                    messages.success(request, f"Removed {user.get_full_name() or user.username} from role '{role.title}'.")
                else:
                    messages.warning(request, f"{user.get_full_name() or user.username} was not assigned to this role.")
        
        return redirect('admin_interface:role_manage_users', role_id=role.id)
    
    # Get users
    all_users = User.objects.select_related('profile').order_by('first_name', 'last_name', 'email')
    selected_users = role.get_assigned_users()
    
    # Get unassigned users (all users minus selected users)
    selected_user_ids = set(selected_users.values_list('id', flat=True))
    unassigned_users = all_users.exclude(id__in=selected_user_ids)
    
    context = {
        'role': role,
        'selected_users': selected_users,
        'unassigned_users': unassigned_users,
    }
    return render(request, 'admin_interface/role_manage_users.html', context)


@login_required
@role_required(['Admin'])
def cost_management(request):
    """Base cost management interface."""
    if request.method == 'POST':
        # Handle cost creation
        name = request.POST.get('name')
        rate = request.POST.get('rate')
        frequency = request.POST.get('frequency')
        description = request.POST.get('description')
        
        if name and rate and frequency:
            try:
                BaseCost.objects.create(
                    name=name,
                    rate=rate,
                    frequency=frequency,
                    description=description or ''
                )
                messages.success(request, f"Base cost '{name}' created successfully!")
                return redirect('admin_interface:cost_management')
            except Exception as e:
                messages.error(request, f"Error creating cost: {str(e)}")
        else:
            messages.error(request, "Please fill in all required fields.")
    
    costs = BaseCost.objects.order_by('name')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        costs = costs.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Calculate statistics
    total_costs = costs.count()
    if total_costs > 0:
        average_cost = sum(cost.rate for cost in costs) / total_costs
    else:
        average_cost = 0
    
    context = {
        'costs': costs,
        'search': search,
        'total_costs': total_costs,
        'average_cost': average_cost,
    }
    
    return render(request, 'admin_interface/cost_management.html', context)


@login_required
@role_required(['Admin'])
def cost_create(request):
    """Create a new base cost."""
    if request.method == 'POST':
        form = BaseCostForm(request.POST)
        if form.is_valid():
            cost = form.save()
            messages.success(request, f"Base cost '{cost.name}' created successfully!")
            return redirect('admin_interface:cost_management')
    else:
        form = BaseCostForm()
    
    context = {
        'form': form,
        'action': 'Create',
    }
    return render(request, 'admin_interface/cost_form.html', context)


@login_required
@role_required(['Admin'])
def cost_detail(request, cost_id):
    """View cost details."""
    cost = get_object_or_404(BaseCost, id=cost_id)
    
    # Get buildout assignments
    buildout_assignments = cost.buildoutbasecost_set.select_related('buildout__program_type').all()
    
    context = {
        'cost': cost,
        'buildout_assignments': buildout_assignments,
    }
    return render(request, 'admin_interface/cost_detail.html', context)


@login_required
@role_required(['Admin'])
def cost_edit(request, cost_id):
    """Edit a base cost."""
    cost = get_object_or_404(BaseCost, id=cost_id)
    
    if request.method == 'POST':
        form = BaseCostForm(request.POST, instance=cost)
        if form.is_valid():
            cost = form.save()
            messages.success(request, f"Cost '{cost.name}' updated successfully!")
            return redirect('admin_interface:cost_management')
    else:
        form = BaseCostForm(instance=cost)
    
    context = {
        'form': form,
        'cost': cost,
        'action': 'Edit',
    }
    return render(request, 'admin_interface/cost_form.html', context)


@login_required
@role_required(['Admin'])
def cost_delete(request, cost_id):
    """Delete a base cost."""
    cost = get_object_or_404(BaseCost, id=cost_id)
    
    if request.method == 'POST':
        name = cost.name
        cost.delete()
        messages.success(request, f"Cost '{name}' deleted successfully!")
        return redirect('admin_interface:cost_management')
    
    context = {
        'cost': cost,
    }
    return render(request, 'admin_interface/cost_confirm_delete.html', context)


# ============================================================================
# LOCATION MANAGEMENT
# ============================================================================

@login_required
@role_required(['Admin'])
def location_management(request):
    """Location management interface."""
    if request.method == 'POST':
        # Handle location creation
        name = request.POST.get('name')
        address = request.POST.get('address')
        default_rate = request.POST.get('default_rate')
        default_frequency = request.POST.get('default_frequency')
        description = request.POST.get('description')
        max_capacity = request.POST.get('max_capacity')
        
        if name and default_rate and default_frequency:
            try:
                from programs.models import Location
                Location.objects.create(
                    name=name,
                    address=address or '',
                    default_rate=default_rate,
                    default_frequency=default_frequency,
                    description=description or '',
                    max_capacity=max_capacity if max_capacity else None
                )
                messages.success(request, f"Location '{name}' created successfully!")
                return redirect('admin_interface:location_management')
            except Exception as e:
                messages.error(request, f"Error creating location: {str(e)}")
        else:
            messages.error(request, "Please fill in all required fields.")
    
    from programs.models import Location
    locations = Location.objects.order_by('name')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        locations = locations.filter(
            Q(name__icontains=search) |
            Q(address__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Calculate statistics
    total_locations = locations.count()
    active_locations = locations.filter(is_active=True).count()
    if total_locations > 0:
        average_rate = sum(location.default_rate for location in locations) / total_locations
    else:
        average_rate = 0
    
    context = {
        'locations': locations,
        'search': search,
        'total_locations': total_locations,
        'active_locations': active_locations,
        'average_rate': average_rate,
    }
    
    return render(request, 'admin_interface/location_management.html', context)


@login_required
@role_required(['Admin'])
def location_create(request):
    """Create a new location."""
    if request.method == 'POST':
        from programs.forms import LocationForm
        form = LocationForm(request.POST)
        if form.is_valid():
            location = form.save()
            messages.success(request, f"Location '{location.name}' created successfully!")
            return redirect('admin_interface:location_management')
    else:
        from programs.forms import LocationForm
        form = LocationForm()
    
    context = {
        'form': form,
        'action': 'Create',
    }
    return render(request, 'admin_interface/location_form.html', context)


@login_required
@role_required(['Admin'])
def location_detail(request, location_id):
    """View location details."""
    from programs.models import Location
    location = get_object_or_404(Location, id=location_id)
    
    # Get buildout assignments
    buildout_assignments = location.buildoutlocationassignment_set.select_related('buildout__program_type').all()
    
    context = {
        'location': location,
        'buildout_assignments': buildout_assignments,
    }
    return render(request, 'admin_interface/location_detail.html', context)


@login_required
@role_required(['Admin'])
def location_edit(request, location_id):
    """Edit a location."""
    from programs.models import Location
    location = get_object_or_404(Location, id=location_id)
    
    if request.method == 'POST':
        from programs.forms import LocationForm
        form = LocationForm(request.POST, instance=location)
        if form.is_valid():
            location = form.save()
            messages.success(request, f"Location '{location.name}' updated successfully!")
            return redirect('admin_interface:location_management')
    else:
        from programs.forms import LocationForm
        form = LocationForm(instance=location)
    
    context = {
        'form': form,
        'location': location,
        'action': 'Edit',
    }
    return render(request, 'admin_interface/location_form.html', context)


@login_required
@role_required(['Admin'])
def location_delete(request, location_id):
    """Delete a location."""
    from programs.models import Location
    location = get_object_or_404(Location, id=location_id)
    
    if request.method == 'POST':
        name = location.name
        location.delete()
        messages.success(request, f"Location '{name}' deleted successfully!")
        return redirect('admin_interface:location_management')
    
    context = {
        'location': location,
    }
    return render(request, 'admin_interface/location_confirm_delete.html', context)


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
    """View buildout details with Excel-like role and responsibility breakdown."""
    buildout = get_object_or_404(ProgramBuildout, id=buildout_id)
    
    # Get related program instances
    instances = ProgramInstance.objects.filter(buildout=buildout)
    
    # Calculate summary statistics using the new model structure
    total_hours = sum(
        role_line.calculate_yearly_hours() 
        for role_line in buildout.role_lines.all()
    )
    total_revenue = buildout.total_revenue_per_year
    total_payouts = sum(
        role_line.calculate_payout() 
        for role_line in buildout.role_lines.all()
    )
    
    # Prepare detailed role data with responsibilities for Excel-like display
    roles_data = []
    for role_line in buildout.role_lines.all().order_by('role__title'):
        role = role_line.role
        # Get all responsibilities for this role
        responsibilities = role.responsibilities.all().order_by('name')
        
        # Calculate hours per scope for this role using the role line data
        hours_per_program_concept = sum(
            resp.default_hours for resp in responsibilities 
            if resp.frequency_type == 'PER_PROGRAM_CONCEPT'
        )
        hours_per_new_worker = sum(
            resp.default_hours for resp in responsibilities 
            if resp.frequency_type == 'PER_NEW_FACILITATOR'
        )
        hours_per_program = sum(
            resp.default_hours for resp in responsibilities 
            if resp.frequency_type == 'PER_PROGRAM'
        )
        hours_per_session = sum(
            resp.default_hours for resp in responsibilities 
            if resp.frequency_type == 'PER_SESSION'
        )
        
        # Calculate yearly totals using role line frequency and hours
        yearly_hours = role_line.calculate_yearly_hours()
        
        # Calculate financial data using role line
        payout = role_line.calculate_payout()
        percentage = (payout / total_revenue * 100) if total_revenue > 0 else 0
        
        roles_data.append({
            'role': role,
            'role_line': role_line,
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
        
        # Calculate cost per program for Excel-like display
        cost_per_program = yearly_cost / buildout.num_programs_per_year if buildout.num_programs_per_year > 0 else 0
        
        base_costs_data.append({
            'base_cost': base_cost_assignment.base_cost,
            'assignment': base_cost_assignment,
            'rate': base_cost_assignment.rate if hasattr(base_cost_assignment, 'rate') and base_cost_assignment.rate else base_cost_assignment.base_cost.rate,
            'frequency': base_cost_assignment.frequency if hasattr(base_cost_assignment, 'frequency') and base_cost_assignment.frequency else base_cost_assignment.base_cost.frequency,
            'multiplier': base_cost_assignment.multiplier,
            'cost_per_program': cost_per_program,
            'yearly_cost': yearly_cost,
            'percentage': (yearly_cost / total_revenue * 100) if total_revenue > 0 else 0
        })
    
    # Calculate location costs
    location_costs_data = []
    total_location_costs = 0
    for location_assignment in buildout.location_assignments.all():
        yearly_cost = location_assignment.calculate_yearly_cost()
        total_location_costs += yearly_cost
        
        # Calculate cost per program for Excel-like display
        cost_per_program = yearly_cost / buildout.num_programs_per_year if buildout.num_programs_per_year > 0 else 0
        
        location_costs_data.append({
            'location': location_assignment.location,
            'assignment': location_assignment,
            'rate': location_assignment.rate if hasattr(location_assignment, 'rate') and location_assignment.rate else location_assignment.location.default_rate,
            'frequency': location_assignment.frequency if hasattr(location_assignment, 'frequency') and location_assignment.frequency else location_assignment.location.default_frequency,
            'multiplier': location_assignment.multiplier,
            'cost_per_program': cost_per_program,
            'yearly_cost': yearly_cost,
            'percentage': (yearly_cost / total_revenue * 100) if total_revenue > 0 else 0
        })
    
    # Calculate total costs including base costs and location costs
    total_overhead_costs = total_base_costs + total_location_costs
    total_all_costs = total_payouts + total_overhead_costs
    total_profit = total_revenue - total_all_costs
    total_profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    
    # Calculate total sessions per year
    total_sessions_per_year = buildout.total_sessions_per_year
    
    context = {
        'buildout': buildout,
        'instances': instances,
        'total_sessions_per_year': total_sessions_per_year,
        'total_hours': total_hours,
        'total_revenue': total_revenue,
        'total_payouts': total_payouts,
        'total_base_costs': total_base_costs,
        'total_location_costs': total_location_costs,
        'total_overhead_costs': total_overhead_costs,
        'total_all_costs': total_all_costs,
        'total_profit': total_profit,
        'total_profit_margin': total_profit_margin,
        'roles_data': roles_data,
        'base_costs_data': base_costs_data,
        'location_costs_data': location_costs_data,
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
def delete_user(request, user_id):
    """Delete a user."""
    user = get_object_or_404(User, id=user_id)
    
    # Prevent deletion of superusers
    if user.is_superuser:
        messages.error(request, 'Cannot delete superuser accounts.')
        return redirect('admin_interface:user_detail', user_id=user_id)
    
    # Prevent deletion of the current user
    if user == request.user:
        messages.error(request, 'Cannot delete your own account.')
        return redirect('admin_interface:user_detail', user_id=user_id)
    
    # Store user email for success message
    user_email = user.email
    
    try:
        with transaction.atomic():
            # Delete related objects first
            # Delete profile if exists
            if hasattr(user, 'profile'):
                user.profile.delete()
            
            # Delete contractor if exists
            if hasattr(user, 'contractor'):
                user.contractor.delete()
            
            # Delete the user
            user.delete()
            
        messages.success(request, f'User {user_email} has been deleted successfully.')
        return redirect('admin_interface:user_management')
        
    except Exception as e:
        messages.error(request, f'Error deleting user: {str(e)}')
        return redirect('admin_interface:user_detail', user_id=user_id)


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


@login_required
@role_required(['Admin'])
def buildout_manage_responsibilities(request, buildout_id):
    """Manage responsibilities and hours for a buildout with Excel-like interface."""
    buildout = get_object_or_404(ProgramBuildout, id=buildout_id)
    
    if request.method == 'POST':
        # Handle responsibility hour updates
        for key, value in request.POST.items():
            if key.startswith('responsibility_'):
                responsibility_id = key.split('_')[1]
                try:
                    responsibility = Responsibility.objects.get(id=responsibility_id)
                    
                    # Safely convert hours to Decimal
                    hours_str = value.strip()
                    if not hours_str or hours_str == '':
                        hours_str = '0.00'
                    try:
                        new_hours = Decimal(hours_str)
                    except (ValueError, decimal.InvalidOperation):
                        messages.error(request, f"Invalid hours value for responsibility '{responsibility.name}'. Skipping update.")
                        continue
                    
                    if new_hours >= 0:
                        responsibility.default_hours = new_hours
                        responsibility.save()
                    else:
                        messages.error(request, f"Hours value for responsibility '{responsibility.name}' must be non-negative. Skipping update.")
                        
                except (Responsibility.DoesNotExist, ValueError):
                    continue
        
        messages.success(request, "Responsibility hours updated successfully!")
        return redirect('admin_interface:buildout_detail', buildout_id=buildout.id)
    
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
    
    return render(request, 'admin_interface/buildout_manage_responsibilities.html', context)


@login_required
@role_required(['Admin'])
def buildout_manage_roles(request, buildout_id):
    """Manage buildout role assignments with individual add/remove actions."""
    buildout = get_object_or_404(ProgramBuildout, id=buildout_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        role_id = request.POST.get('role_id')
        contractor_id = request.POST.get('contractor_id')
        
        if action and role_id and contractor_id:
            try:
                role = Role.objects.get(id=role_id)
                contractor = User.objects.get(id=contractor_id)
                
                if action == 'add':
                    # Check if this role-contractor combination already exists
                    existing_assignment = BuildoutRoleLine.objects.filter(
                        buildout=buildout,
                        role=role,
                        contractor=contractor
                    ).first()
                    
                    if existing_assignment:
                        messages.info(request, f"{contractor.get_full_name() or contractor.email} is already assigned to {role.title} for this buildout.")
                    else:
                        # Get pay overrides from form or use defaults
                        pay_type = request.POST.get('pay_type', 'HOURLY')
                        pay_value_str = request.POST.get('pay_value', '0.00').strip()
                        if not pay_value_str or pay_value_str == '':
                            pay_value_str = '0.00'
                        try:
                            pay_value = Decimal(pay_value_str)
                        except (ValueError, decimal.InvalidOperation):
                            pay_value = Decimal('0.00')
                        
                        hours_str = request.POST.get('hours', str(role.default_hours_per_frequency)).strip()
                        if not hours_str or hours_str == '':
                            hours_str = str(role.default_hours_per_frequency)
                        try:
                            hours_per_frequency = Decimal(hours_str)
                        except (ValueError, decimal.InvalidOperation):
                            hours_per_frequency = Decimal(str(role.default_hours_per_frequency))
                        
                        # Create role line with overrides
                        role_line = BuildoutRoleLine.objects.create(
                            buildout=buildout,
                            role=role,
                            contractor=contractor,
                            pay_type=pay_type,
                            pay_value=pay_value,
                            frequency_unit=role.default_frequency_unit,
                            frequency_count=1,
                            hours_per_frequency=hours_per_frequency
                        )
                        
                        # Create responsibility lines for this role if they don't exist
                        for responsibility in role.responsibilities.all():
                            if not BuildoutResponsibilityLine.objects.filter(
                                buildout=buildout,
                                responsibility=responsibility
                            ).exists():
                                BuildoutResponsibilityLine.objects.create(
                                    buildout=buildout,
                                    responsibility=responsibility,
                                    hours=responsibility.default_hours
                                )
                        
                        messages.success(request, f"Added {contractor.get_full_name() or contractor.email} to {role.title} for this buildout.")
                        
                elif action == 'remove':
                    deleted_count = BuildoutRoleLine.objects.filter(
                        buildout=buildout,
                        role=role,
                        contractor=contractor
                    ).delete()[0]
                    
                    if deleted_count > 0:
                        messages.success(request, f"Removed {contractor.get_full_name() or contractor.email} from {role.title} for this buildout.")
                    else:
                        messages.warning(request, f"{contractor.get_full_name() or contractor.email} was not assigned to {role.title} for this buildout.")
                        
            except (Role.DoesNotExist, User.DoesNotExist) as e:
                messages.error(request, "Invalid role or contractor selected.")
        
        return redirect('admin_interface:buildout_manage_roles', buildout_id=buildout.id)
    
    # Get assigned role lines
    assigned_role_lines = buildout.role_lines.select_related('role', 'contractor').all()
    
    # Get all available roles
    all_roles = Role.objects.all().order_by('title')
    
    # Get available contractors for each role
    contractors_by_role = {}
    for role in all_roles:
        contractors_by_role[role.id] = role.get_assigned_contractors()
    
    context = {
        'buildout': buildout,
        'assigned_role_lines': assigned_role_lines,
        'all_roles': all_roles,
        'contractors_by_role': contractors_by_role,
    }
    
    return render(request, 'admin_interface/buildout_manage_roles.html', context)


@login_required
@role_required(['Admin'])
def buildout_assign_roles(request, buildout_id):
    """Legacy view - redirect to new manage roles view."""
    return redirect('admin_interface:buildout_manage_roles', buildout_id=buildout_id)


@login_required
@role_required(['Admin'])
def buildout_assign_costs(request, buildout_id):
    """Assign costs to a buildout with rate and frequency configuration."""
    buildout = get_object_or_404(ProgramBuildout, id=buildout_id)
    
    if request.method == 'POST':
        # Get selected costs
        selected_costs = request.POST.getlist('costs')
        
        if not selected_costs:
            messages.error(request, "No costs were selected. Please select at least one cost.")
            return redirect('admin_interface:buildout_assign_costs', buildout_id=buildout_id)
        
        # Clear existing cost assignments
        buildout.base_cost_assignments.all().delete()
        
        # Add selected costs
        for cost_id in selected_costs:
            try:
                base_cost = BaseCost.objects.get(id=cost_id)
                
                # Get rate and frequency for this cost
                # Safely convert rate to Decimal
                rate_str = request.POST.get(f'rate_{cost_id}', str(base_cost.rate)).strip()
                if not rate_str or rate_str == '':
                    rate_str = str(base_cost.rate)
                try:
                    rate = Decimal(rate_str)
                except (ValueError, decimal.InvalidOperation):
                    messages.error(request, f"Invalid rate value for cost '{base_cost.name}'. Using default rate.")
                    rate = base_cost.rate
                
                frequency = request.POST.get(f'frequency_{cost_id}', base_cost.frequency)
                
                # Safely convert multiplier to Decimal
                multiplier_str = request.POST.get(f'multiplier_{cost_id}', '1.00').strip()
                if not multiplier_str or multiplier_str == '':
                    multiplier_str = '1.00'
                try:
                    multiplier = Decimal(multiplier_str)
                except (ValueError, decimal.InvalidOperation):
                    messages.error(request, f"Invalid multiplier value for cost '{base_cost.name}'. Using default multiplier.")
                    multiplier = Decimal('1.00')
                
                # Create cost assignment
                BuildoutBaseCostAssignment.objects.create(
                    buildout=buildout,
                    base_cost=base_cost,
                    rate=rate,
                    frequency=frequency,
                    multiplier=multiplier
                )
                
            except (BaseCost.DoesNotExist, ValueError) as e:
                continue
        
        messages.success(request, f"Assigned {len(selected_costs)} costs to buildout.")
        return redirect('admin_interface:buildout_detail', buildout_id=buildout.id)
    
    # Get all available costs
    all_costs = BaseCost.objects.all().order_by('name')
    assigned_costs = [assignment.base_cost for assignment in buildout.base_cost_assignments.all()]
    
    context = {
        'buildout': buildout,
        'all_costs': all_costs,
        'assigned_costs': assigned_costs,
    }
    
    return render(request, 'admin_interface/buildout_assign_costs.html', context)


@login_required
@role_required(['Admin'])
def buildout_manage_locations(request, buildout_id):
    """Manage buildout location assignments with individual add/remove actions."""
    buildout = get_object_or_404(ProgramBuildout, id=buildout_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        location_id = request.POST.get('location_id')
        
        if action and location_id:
            try:
                location = Location.objects.get(id=location_id)
                
                if action == 'add':
                    # Check if this location is already assigned
                    existing_assignment = BuildoutLocationAssignment.objects.filter(
                        buildout=buildout,
                        location=location
                    ).first()
                    
                    if existing_assignment:
                        messages.info(request, f"{location.name} is already assigned to this buildout.")
                    else:
                        # Get rate and frequency from form or use defaults
                        rate_str = request.POST.get('rate', str(location.default_rate)).strip()
                        if not rate_str or rate_str == '':
                            rate_str = str(location.default_rate)
                        try:
                            rate = Decimal(rate_str)
                        except (ValueError, decimal.InvalidOperation):
                            rate = location.default_rate
                        
                        frequency = request.POST.get('frequency', location.default_frequency)
                        
                        multiplier_str = request.POST.get('multiplier', '1.00').strip()
                        if not multiplier_str or multiplier_str == '':
                            multiplier_str = '1.00'
                        try:
                            multiplier = Decimal(multiplier_str)
                        except (ValueError, decimal.InvalidOperation):
                            multiplier = Decimal('1.00')
                        
                        # Create location assignment
                        BuildoutLocationAssignment.objects.create(
                            buildout=buildout,
                            location=location,
                            rate=rate,
                            frequency=frequency,
                            multiplier=multiplier
                        )
                        
                        messages.success(request, f"Added {location.name} to this buildout.")
                        
                elif action == 'remove':
                    deleted_count = BuildoutLocationAssignment.objects.filter(
                        buildout=buildout,
                        location=location
                    ).delete()[0]
                    
                    if deleted_count > 0:
                        messages.success(request, f"Removed {location.name} from this buildout.")
                    else:
                        messages.warning(request, f"{location.name} was not assigned to this buildout.")
                        
            except Location.DoesNotExist:
                messages.error(request, "Invalid location selected.")
        
        return redirect('admin_interface:buildout_manage_locations', buildout_id=buildout.id)
    
    # Get assigned location assignments
    assigned_location_assignments = buildout.location_assignments.select_related('location').all()
    
    # Get all available locations
    all_locations = Location.objects.all().order_by('name')
    
    # Get unassigned locations
    assigned_location_ids = set(assigned_location_assignments.values_list('location_id', flat=True))
    unassigned_locations = all_locations.exclude(id__in=assigned_location_ids)
    
    context = {
        'buildout': buildout,
        'assigned_location_assignments': assigned_location_assignments,
        'unassigned_locations': unassigned_locations,
    }
    
    return render(request, 'admin_interface/buildout_manage_locations.html', context)


@login_required
@role_required(['Admin'])
def buildout_assign_locations(request, buildout_id):
    """Legacy view - redirect to new manage locations view."""
    return redirect('admin_interface:buildout_manage_locations', buildout_id=buildout_id)


@login_required
@role_required(['Admin'])
def role_manage_responsibilities(request, role_id):
    """Manage responsibilities for a role with Excel-like interface."""
    role = get_object_or_404(Role, id=role_id)
    
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
        return redirect('admin_interface:role_detail', role_id=role.id)
    
    # Get all responsibilities for this role
    responsibilities = role.responsibilities.all().order_by('name')
    
    context = {
        'role': role,
        'responsibilities': responsibilities,
    }
    
    return render(request, 'admin_interface/role_manage_responsibilities.html', context)


@login_required
@role_required(['Admin'])
def role_add_responsibility(request, role_id):
    """Add a new responsibility to a role."""
    role = get_object_or_404(Role, id=role_id)
    
    if request.method == 'POST':
        form = ResponsibilityForm(request.POST)
        # Remove role field from form since we'll set it automatically
        if 'role' in form.fields:
            del form.fields['role']
        
        if form.is_valid():
            responsibility = form.save(commit=False)
            responsibility.role = role
            responsibility.save()
            messages.success(request, f"Responsibility '{responsibility.name}' added to role '{role.title}' successfully!")
            return redirect('admin_interface:role_detail', role_id=role.id)
    else:
        form = ResponsibilityForm()
        # Remove role field from form since we'll set it automatically
        if 'role' in form.fields:
            del form.fields['role']
    
    context = {
        'form': form,
        'role': role,
        'title': f'Add Responsibility to {role.title}',
        'action': 'Add',
    }
    
    return render(request, 'admin_interface/responsibility_form.html', context)


@login_required
@role_required(['Admin'])
def responsibility_edit(request, responsibility_id):
    """Edit an existing responsibility."""
    responsibility = get_object_or_404(Responsibility, id=responsibility_id)
    role = responsibility.role
    
    if request.method == 'POST':
        # Create form without role field for editing
        form = ResponsibilityForm(request.POST, instance=responsibility)
        # Remove role field from form since we don't want to change it
        if 'role' in form.fields:
            del form.fields['role']
        
        if form.is_valid():
            form.save()
            messages.success(request, f"Responsibility '{responsibility.name}' updated successfully!")
            return redirect('admin_interface:role_manage_responsibilities', role_id=role.id)
    else:
        form = ResponsibilityForm(instance=responsibility)
        # Remove role field from form since we don't want to change it
        if 'role' in form.fields:
            del form.fields['role']
    
    context = {
        'form': form,
        'role': role,
        'responsibility': responsibility,
        'title': f'Edit Responsibility: {responsibility.name}',
        'action': 'Update',
    }
    
    return render(request, 'admin_interface/responsibility_form.html', context)


@login_required
@role_required(['Admin'])
def responsibility_delete(request, responsibility_id):
    """Delete a responsibility."""
    responsibility = get_object_or_404(Responsibility, id=responsibility_id)
    role = responsibility.role
    
    if request.method == 'POST':
        responsibility_name = responsibility.name
        responsibility.delete()
        messages.success(request, f"Responsibility '{responsibility_name}' deleted successfully!")
        return redirect('admin_interface:role_manage_responsibilities', role_id=role.id)
    
    context = {
        'responsibility': responsibility,
        'role': role,
    }
    
    return render(request, 'admin_interface/responsibility_confirm_delete.html', context)


@login_required
@role_required(['Admin'])
def program_instance_create_from_buildout(request, buildout_id):
    """Create a new program instance from a specific buildout using a custom form."""
    buildout = get_object_or_404(ProgramBuildout, id=buildout_id)

    if request.method == 'POST':
        form = AdminProgramInstanceForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    instance = form.save(commit=False)
                    instance.buildout = buildout
                    instance.save()
                    
                    # Auto-assign contractors from buildout role lines
                    for role_line in buildout.role_lines.all():
                        InstanceRoleAssignment.objects.create(
                            program_instance=instance,
                            role=role_line.role,
                            contractor=role_line.contractor,
                            # Use buildout role line values as defaults
                            override_hours=role_line.hours_per_frequency,
                            override_rate=role_line.pay_value if role_line.pay_type == 'HOURLY' else None,
                            computed_payout=None  # Will be calculated later
                        )
                    
                    messages.success(request, f"Program instance '{instance.title}' created successfully with {buildout.role_lines.count()} contractors assigned!")
                    return redirect('admin_interface:program_instance_detail', instance_id=instance.id)
            except ValidationError as e:
                messages.error(request, f"Error creating program instance: {e}")
            except Exception as e:
                messages.error(request, f"An unexpected error occurred: {e}")
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = AdminProgramInstanceForm(initial={'buildout': buildout})

    context = {
        'form': form,
        'buildout': buildout,
        'title': 'Create Program Instance',
        'action': 'Create',
    }
    return render(request, 'admin_interface/program_instance_form.html', context)


@login_required
@role_required(['Admin'])
def program_instance_create(request):
    """Create a new program instance without a specific buildout using a custom form."""
    if request.method == 'POST':
        form = AdminProgramInstanceForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    instance = form.save()
                    messages.success(request, f"Program instance '{instance.title}' created successfully!")
                    return redirect('admin_interface:program_instance_detail', instance_id=instance.id)
            except ValidationError as e:
                messages.error(request, f"Error creating program instance: {e}")
            except Exception as e:
                messages.error(request, f"An unexpected error occurred: {e}")
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = AdminProgramInstanceForm()

    context = {
        'form': form,
        'title': 'Create Program Instance',
        'action': 'Create',
    }
    return render(request, 'admin_interface/program_instance_form.html', context)


@login_required
@role_required(['Admin'])
def program_instance_edit(request, instance_id):
    """Edit an existing program instance using a custom form."""
    instance = get_object_or_404(ProgramInstance, id=instance_id)

    if request.method == 'POST':
        form = AdminProgramInstanceForm(request.POST, instance=instance)
        if form.is_valid():
            try:
                with transaction.atomic():
                    instance = form.save()
                    messages.success(request, f"Program instance '{instance.title}' updated successfully!")
                    return redirect('admin_interface:program_instance_detail', instance_id=instance.id)
            except ValidationError as e:
                messages.error(request, f"Error updating program instance: {e}")
            except Exception as e:
                messages.error(request, f"An unexpected error occurred: {e}")
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = AdminProgramInstanceForm(instance=instance)

    context = {
        'form': form,
        'instance': instance,
        'title': f'Edit Program Instance: {instance.title}',
        'action': 'Edit',
    }
    return render(request, 'admin_interface/program_instance_form.html', context)


@login_required
@role_required(['Admin'])
def program_instance_detail(request, instance_id):
    """View program instance details."""
    instance = get_object_or_404(ProgramInstance, id=instance_id)
    
    context = {
        'instance': instance,
        'registrations': instance.registrations.all().order_by('-registered_at'),
    }
    return render(request, 'admin_interface/program_instance_detail.html', context)


@login_required
@role_required(['Admin'])
def program_instance_delete(request, instance_id):
    """Delete a program instance."""
    instance = get_object_or_404(ProgramInstance, id=instance_id)
    
    if request.method == 'POST':
        title = instance.title
        instance.delete()
        messages.success(request, f"Program instance '{title}' deleted successfully!")
        return redirect('admin_interface:program_instance_management')
    
    context = {
        'instance': instance,
    }
    return render(request, 'admin_interface/program_instance_confirm_delete.html', context)


# ============================================================================
# NDA AND W-9 MANAGEMENT
# ============================================================================

@login_required
@role_required(['Admin'])
def contractor_document_management(request):
    """Contractor document management interface for NDA and W-9."""
    contractors = Contractor.objects.select_related('user', 'nda_signature').all()
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        contractors = contractors.filter(
            Q(user__email__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'nda_pending':
        contractors = contractors.filter(nda_signed=True, nda_approved=False)
    elif status_filter == 'w9_pending':
        contractors = contractors.filter(w9_file__isnull=False, w9_approved=False)
    elif status_filter == 'both_pending':
        contractors = contractors.filter(
            Q(nda_signed=True, nda_approved=False) | 
            Q(w9_file__isnull=False, w9_approved=False)
        )
    elif status_filter == 'approved':
        contractors = contractors.filter(nda_approved=True, w9_approved=True)
    
    # Pagination
    paginator = Paginator(contractors, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
    }
    
    return render(request, 'admin_interface/contractor_document_management.html', context)


@login_required
@role_required(['Admin'])
def contractor_document_detail(request, contractor_id):
    """View contractor document details including NDA signature and W-9."""
    contractor = get_object_or_404(Contractor, id=contractor_id)
    
    # Get NDA signature if it exists
    nda_signature = None
    if hasattr(contractor, 'nda_signature'):
        nda_signature = contractor.nda_signature
    
    context = {
        'contractor': contractor,
        'nda_signature': nda_signature,
    }
    
    return render(request, 'admin_interface/contractor_document_detail.html', context)


@login_required
@role_required(['Admin'])
def approve_nda(request, contractor_id):
    """Approve contractor NDA signature."""
    contractor = get_object_or_404(Contractor, id=contractor_id)
    
    if not contractor.nda_signed:
        messages.error(request, "Contractor has not signed the NDA yet.")
        return redirect('admin_interface:contractor_document_detail', contractor_id=contractor.id)
    
    if contractor.nda_approved:
        messages.info(request, "NDA is already approved.")
        return redirect('admin_interface:contractor_document_detail', contractor_id=contractor.id)
    
    contractor.nda_approved = True
    contractor.nda_approved_by = request.user
    contractor.nda_approved_at = timezone.now()
    contractor.save()
    
    messages.success(request, f"NDA approved for {contractor.user.get_full_name() or contractor.user.email}")
    return redirect('admin_interface:contractor_document_detail', contractor_id=contractor.id)


@login_required
@role_required(['Admin'])
def approve_w9(request, contractor_id):
    """Approve contractor W-9 document."""
    contractor = get_object_or_404(Contractor, id=contractor_id)
    
    if not contractor.w9_file:
        messages.error(request, "Contractor has not uploaded W-9 yet.")
        return redirect('admin_interface:contractor_document_detail', contractor_id=contractor.id)
    
    if contractor.w9_approved:
        messages.info(request, "W-9 is already approved.")
        return redirect('admin_interface:contractor_document_detail', contractor_id=contractor.id)
    
    contractor.w9_approved = True
    contractor.w9_approved_by = request.user
    contractor.w9_approved_at = timezone.now()
    contractor.save()
    
    messages.success(request, f"W-9 approved for {contractor.user.get_full_name() or contractor.user.email}")
    return redirect('admin_interface:contractor_document_detail', contractor_id=contractor.id)


@login_required
@role_required(['Admin'])
def reset_nda(request, contractor_id):
    """Reset contractor NDA status (requires re-signing)."""
    contractor = get_object_or_404(Contractor, id=contractor_id)
    
    if request.method == 'POST':
        contractor.nda_signed = False
        contractor.nda_approved = False
        contractor.nda_approved_by = None
        contractor.nda_approved_at = None
        contractor.save()
        
        # Delete the NDA signature record
        if hasattr(contractor, 'nda_signature'):
            contractor.nda_signature.delete()
        
        messages.success(request, f"NDA status reset for {contractor.user.get_full_name() or contractor.user.email}. They will need to sign again.")
        return redirect('admin_interface:contractor_document_detail', contractor_id=contractor.id)
    
    context = {
        'contractor': contractor,
        'document_type': 'NDA',
    }
    
    return render(request, 'admin_interface/contractor_document_reset_confirm.html', context)


@login_required
@role_required(['Admin'])
def reset_w9(request, contractor_id):
    """Reset contractor W-9 status (requires re-uploading)."""
    contractor = get_object_or_404(Contractor, id=contractor_id)
    
    if request.method == 'POST':
        contractor.w9_file = None
        contractor.w9_approved = False
        contractor.w9_approved_by = None
        contractor.w9_approved_at = None
        contractor.save()
        
        messages.success(request, f"W-9 status reset for {contractor.user.get_full_name() or contractor.user.email}. They will need to upload again.")
        return redirect('admin_interface:contractor_document_detail', contractor_id=contractor.id)
    
    context = {
        'contractor': contractor,
        'document_type': 'W-9',
    }
    
    return render(request, 'admin_interface/contractor_document_reset_confirm.html', context)


@login_required
@role_required(['Admin'])
def view_nda_signature(request, contractor_id):
    """View NDA signature image."""
    contractor = get_object_or_404(Contractor, id=contractor_id)
    
    if not hasattr(contractor, 'nda_signature'):
        messages.error(request, "No NDA signature found for this contractor.")
        return redirect('admin_interface:contractor_document_detail', contractor_id=contractor.id)
    
    nda_signature = contractor.nda_signature
    
    context = {
        'contractor': contractor,
        'nda_signature': nda_signature,
    }
    
    return render(request, 'admin_interface/view_nda_signature.html', context)


@login_required
@role_required(['Admin'])
def download_w9(request, contractor_id):
    """Download contractor W-9 file."""
    contractor = get_object_or_404(Contractor, id=contractor_id)
    
    if not contractor.w9_file:
        messages.error(request, "No W-9 file found for this contractor.")
        return redirect('admin_interface:contractor_document_detail', contractor_id=contractor.id)
    
    from django.http import FileResponse
    from django.conf import settings
    import os
    
    file_path = os.path.join(settings.MEDIA_ROOT, contractor.w9_file.name)
    
    if os.path.exists(file_path):
        response = FileResponse(open(file_path, 'rb'), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="w9_{contractor.user.email}_{contractor.id}.pdf"'
        return response
    else:
        messages.error(request, "W-9 file not found on server.")
        return redirect('admin_interface:contractor_document_detail', contractor_id=contractor.id)
