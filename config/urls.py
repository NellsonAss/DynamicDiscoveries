"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from accounts.views import debug_env
from django.utils import timezone

def test_view(request):
    from django.shortcuts import render
    return render(request, 'test_simple.html', {'current_time': timezone.now()})

urlpatterns = [
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('test/', test_view, name='test'),
    path('admin/', admin.site.urls),
    path('auth/', include(('allauth.urls', 'allauth'), namespace='auth')),  # django-allauth URLs under /auth/
    path('accounts/', include('accounts.urls')),  # Our custom accounts URLs
    path('communications/', include('communications.urls')),
    path('programs/', include('programs.urls')),
    path('', include('dashboard.urls')),
    path('admin-interface/', include('admin_interface.urls')),
    path('debug-env/', debug_env),
    path('captcha/', include('captcha.urls')),
]
