from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import timedelta
from programs.models import Registration, ProgramInstance
from accounts.models import User

@login_required
def dashboard(request):
    """Main dashboard view."""
    return render(request, 'dashboard/dashboard.html')

@login_required
@require_http_methods(['GET'])
def dashboard_stats(request):
    """HTMX endpoint for dashboard statistics."""
    # In a real app, you would fetch actual statistics here
    stats = {
        'total_users': 100,
        'active_users': 75,
        'new_users_today': 5
    }
    return render(request, 'dashboard/partials/stats.html', {'stats': stats})

@login_required
@require_http_methods(['GET'])
def dashboard_activity(request):
    """HTMX endpoint for dashboard activity feed."""
    # Get recent activity based on user role
    user = request.user
    activities = []
    
    # Get recent program registrations
    recent_registrations = Registration.objects.select_related(
        'child', 'program_instance', 'program_instance__program_type'
    ).order_by('-registered_at')[:5]
    
    for registration in recent_registrations:
        activities.append({
            'type': 'registration',
            'title': f'New registration for {registration.program_instance.name}',
            'description': f'{registration.child.first_name} {registration.child.last_name} registered',
            'time': registration.registered_at,
            'icon': 'bi-person-plus'
        })
    
    # Get recent program instances
    recent_programs = ProgramInstance.objects.select_related('program_type').order_by('-created_at')[:3]
    
    for program in recent_programs:
        activities.append({
            'type': 'program',
            'title': f'New program: {program.name}',
            'description': f'{program.program_type.name} program created',
            'time': program.created_at,
            'icon': 'bi-calendar-event'
        })
    
    # Sort activities by time (most recent first)
    activities.sort(key=lambda x: x['time'], reverse=True)
    
    return render(request, 'dashboard/partials/activity_feed.html', {'activities': activities[:10]}) 