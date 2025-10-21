"""
Admin views for viewing impersonation logs.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from accounts.mixins import role_required
from audit.models import ImpersonationLog


@login_required
@role_required(['Admin'])
def impersonation_log_list(request):
    """View all impersonation logs with filtering and pagination."""
    logs = ImpersonationLog.objects.select_related(
        'admin_user', 'target_user'
    ).order_by('-started_at')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        logs = logs.filter(
            Q(admin_user__email__icontains=search) |
            Q(target_user__email__icontains=search) |
            Q(reason_note__icontains=search)
        )
    
    # Filter by active/closed
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        logs = logs.filter(ended_at__isnull=True)
    elif status_filter == 'closed':
        logs = logs.filter(ended_at__isnull=False)
    
    # Pagination
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
    }
    
    return render(request, 'admin_interface/impersonation_logs.html', context)

