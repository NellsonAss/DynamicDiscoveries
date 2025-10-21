from django.urls import path
from . import views
from . import impersonation_views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup, name='signup'),
    path('verify-code/', views.verify_code, name='verify_code'),
    path('profile/', views.profile, name='profile'),
    path('redirect/', views.role_based_redirect, name='role_based_redirect'),
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/<int:pk>/roles/', views.UserRoleUpdateView.as_view(), name='user_role_update'),
    path('debug/', views.debug_user, name='debug_user'),
    
    # Role Preview & Impersonation
    path('role/switch/', impersonation_views.role_switch, name='role_switch'),
    path('impersonate/start/', impersonation_views.impersonate_start, name='impersonate_start'),
    path('impersonate/stop/', impersonation_views.impersonate_stop, name='impersonate_stop'),
] 