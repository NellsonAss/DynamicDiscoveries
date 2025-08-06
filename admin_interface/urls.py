from django.urls import path
from . import views

app_name = 'admin_interface'

urlpatterns = [
    # Dashboard
    path('', views.admin_dashboard, name='dashboard'),
    
    # User Management
    path('users/', views.user_management, name='user_management'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    
    # Program Management
    path('program-types/', views.program_type_management, name='program_type_management'),
    path('program-instances/', views.program_instance_management, name='program_instance_management'),
    path('program-instances/<int:instance_id>/toggle-status/', views.toggle_program_instance_status, name='toggle_program_instance_status'),
    path('buildouts/', views.buildout_management, name='buildout_management'),
    
    # Registration Management
    path('registrations/', views.registration_management, name='registration_management'),
    path('registrations/<int:registration_id>/update-status/', views.update_registration_status, name='update_registration_status'),
    
    # Contact Management
    path('contacts/', views.contact_management, name='contact_management'),
    path('contacts/<int:contact_id>/update-status/', views.update_contact_status, name='update_contact_status'),
    
    # Child Management
    path('children/', views.child_management, name='child_management'),
    
    # Form Management
    path('forms/', views.form_management, name='form_management'),
    
    # Role Management
    path('roles/', views.role_management, name='role_management'),
    
    # Cost Management
    path('costs/', views.cost_management, name='cost_management'),
] 