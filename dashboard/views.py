from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

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