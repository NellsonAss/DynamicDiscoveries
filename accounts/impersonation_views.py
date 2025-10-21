"""
Views for role preview and user impersonation.

Provides "View As" functionality for admins to:
1. Preview the site as different roles they have (role preview)
2. Impersonate other users for testing/support (with audit logging)
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model
from django.utils import timezone
from audit.models import ImpersonationLog
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


def get_client_ip(request):
    """Get the client's IP address from the request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@login_required
@require_http_methods(["POST"])
def role_switch(request):
    """
    Switch the effective role for the current user (self role preview).
    
    Allows multi-role users to preview how the site appears for different roles.
    Does not change actual permissions or identity.
    """
    role = request.POST.get('role', 'Auto')
    
    # Check if currently impersonating - can't role switch while impersonating
    if request.session.get('impersonate_user_id'):
        return HttpResponse(
            '<div class="alert alert-warning">Cannot switch roles while impersonating. Stop impersonation first.</div>',
            status=400
        )
    
    if role == 'Auto':
        # Clear role preview
        request.session.pop('effective_role', None)
        messages.success(request, 'Role preview cleared. Using automatic role detection.')
        
        # Redirect to user's default dashboard
        from accounts.views import get_user_redirect_url
        from django.urls import reverse
        redirect_url = reverse(get_user_redirect_url(request.user))
        
        return HttpResponse(
            status=200,
            headers={'HX-Redirect': redirect_url}
        )
    
    # Validate user has this role
    if not request.user.groups.filter(name=role).exists():
        logger.warning(
            f"User {request.user.email} attempted to preview role '{role}' which they don't have"
        )
        return HttpResponse(
            f'<div class="alert alert-danger">You do not have the {role} role.</div>',
            status=403
        )
    
    # Set effective role in session
    request.session['effective_role'] = role
    messages.success(request, f'Now viewing as: {role}')
    
    logger.info(f"User {request.user.email} switched to role preview: {role}")
    
    # Redirect to appropriate landing page for the selected role
    from django.urls import reverse
    
    # Map roles to their landing pages
    role_landing_pages = {
        'Parent': 'programs:parent_dashboard',
        'Contractor': 'programs:contractor_dashboard',
        'Admin': 'admin_interface:dashboard',
        'Consultant': 'communications:contact_list',
    }
    
    redirect_url = role_landing_pages.get(role)
    if redirect_url:
        redirect_url = reverse(redirect_url)
    else:
        # Default to dashboard if role not in map
        redirect_url = reverse('dashboard:dashboard')
    
    return HttpResponse(
        status=200,
        headers={'HX-Redirect': redirect_url}
    )


@login_required
@require_http_methods(["POST"])
def impersonate_start(request):
    """
    Start impersonating another user.
    
    Only superusers or users with can_impersonate_users permission can use this.
    Creates an audit log entry and sets session variables.
    """
    # Permission check
    if not (request.user.is_superuser or request.user.has_perm('auth.can_impersonate_users')):
        messages.error(request, 'You do not have permission to impersonate users.')
        return redirect('admin_interface:user_management')
    
    # Get target user
    user_id = request.POST.get('user_id')
    if not user_id:
        messages.error(request, 'No user specified for impersonation.')
        return redirect('admin_interface:user_management')
    
    target_user = get_object_or_404(User, id=user_id)
    
    # Prevent impersonating yourself
    if target_user.id == request.user.id:
        messages.error(request, 'Cannot impersonate yourself. Use role preview instead.')
        return redirect('admin_interface:user_management')
    
    # Prevent non-superusers from impersonating superusers
    if target_user.is_superuser and not request.user.is_superuser:
        messages.error(request, 'Cannot impersonate superuser accounts.')
        logger.warning(
            f"User {request.user.email} attempted to impersonate superuser {target_user.email}"
        )
        return redirect('admin_interface:user_management')
    
    # Prevent impersonating inactive users
    if not target_user.is_active:
        messages.error(request, 'Cannot impersonate inactive users.')
        return redirect('admin_interface:user_management')
    
    # Get optional parameters
    readonly = request.POST.get('readonly', 'true').lower() == 'true'
    reason = request.POST.get('reason', '').strip()
    
    # Create audit log
    log = ImpersonationLog.objects.create(
        admin_user=request.user,
        target_user=target_user,
        readonly=readonly,
        reason_note=reason,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )
    
    # Set session variables
    request.session['impersonate_user_id'] = target_user.id
    request.session['impersonate_readonly'] = readonly
    request.session['impersonate_log_id'] = log.id
    
    # Auto-detect effective role for impersonated user
    user_roles = target_user.get_role_names()
    if user_roles:
        if 'Parent' in user_roles:
            effective_role = 'Parent'
        elif 'Contractor' in user_roles:
            effective_role = 'Contractor'
        elif 'Admin' in user_roles:
            effective_role = 'Admin'
        else:
            effective_role = user_roles[0]
        request.session['effective_role'] = effective_role
    
    logger.info(
        f"Impersonation started: {request.user.email} → {target_user.email} "
        f"(readonly={readonly}, log_id={log.id})"
    )
    
    messages.success(
        request,
        f'Now impersonating {target_user.email} ({target_user.get_full_name() or target_user.email}). '
        f'{"Read-only mode active." if readonly else "Full access mode active."}'
    )
    
    # Redirect to target user's appropriate dashboard
    from accounts.views import get_user_redirect_url
    redirect_url = get_user_redirect_url(target_user)
    return redirect(redirect_url)


@login_required
@require_http_methods(["POST"])
def impersonate_stop(request):
    """
    Stop the current impersonation session.
    
    Closes the audit log and clears session variables.
    """
    # Get impersonation log
    log_id = request.session.get('impersonate_log_id')
    impersonate_user_id = request.session.get('impersonate_user_id')
    
    if not impersonate_user_id:
        messages.info(request, 'You are not currently impersonating anyone.')
        return redirect('dashboard:dashboard')
    
    # Close the audit log
    if log_id:
        try:
            log = ImpersonationLog.objects.get(id=log_id)
            log.ended_at = timezone.now()
            log.save()
            logger.info(
                f"Impersonation ended: {request.user.email} stopped impersonating "
                f"user_id={impersonate_user_id} (duration={log.duration})"
            )
        except ImpersonationLog.DoesNotExist:
            logger.error(f"Impersonation log {log_id} not found when stopping impersonation")
    
    # Clear session variables
    request.session.pop('impersonate_user_id', None)
    request.session.pop('impersonate_readonly', None)
    request.session.pop('impersonate_log_id', None)
    request.session.pop('effective_role', None)
    
    messages.success(request, 'Stopped impersonating. Back to your own account.')
    
    # Redirect to safe admin landing
    return redirect('dashboard:dashboard')


def readonly_enforcement_required(view_func):
    """
    Decorator to block write operations during read-only impersonation.
    
    Should be applied to any view that modifies data (POST/PUT/PATCH/DELETE).
    Allows GET/HEAD/OPTIONS to pass through.
    """
    def wrapper(request, *args, **kwargs):
        # Allow read-only methods
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return view_func(request, *args, **kwargs)
        
        # Check if in read-only impersonation mode
        is_impersonating = request.session.get('impersonate_user_id') is not None
        is_readonly = request.session.get('impersonate_readonly', True)
        
        if is_impersonating and is_readonly:
            # Log the blocked action
            logger.warning(
                f"Blocked write action during read-only impersonation: "
                f"{request.user.email} attempted {request.method} on {request.path}"
            )
            
            # Return appropriate response
            if request.headers.get('HX-Request'):
                # HTMX request - return alert fragment
                return HttpResponse(
                    '<div class="alert alert-warning">'
                    '<i class="bi bi-exclamation-triangle me-2"></i>'
                    'Write actions are disabled in read-only preview mode.'
                    '</div>',
                    status=403
                )
            else:
                # Regular request - show message and redirect
                messages.error(request, 'Write actions are disabled in read-only preview mode.')
                return redirect(request.META.get('HTTP_REFERER', 'dashboard:dashboard'))
        
        # Not in read-only mode, proceed normally
        return view_func(request, *args, **kwargs)
    
    return wrapper

