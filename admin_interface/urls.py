from django.urls import path
from . import views

app_name = 'admin_interface'

urlpatterns = [
    # Dashboard
    path('', views.admin_dashboard, name='dashboard'),
    
    # User Management
    path('users/', views.user_management, name='user_management'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('users/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    
    # Program Management
    path('program-types/', views.program_type_management, name='program_type_management'),
    path('program-types/create/', views.program_type_create, name='program_type_create'),
    path('program-types/<int:program_type_id>/', views.program_type_detail, name='program_type_detail'),
    path('program-types/<int:program_type_id>/edit/', views.program_type_edit, name='program_type_edit'),
    path('program-types/<int:program_type_id>/delete/', views.program_type_delete, name='program_type_delete'),


    path('program-instances/', views.program_instance_management, name='program_instance_management'),
    path('program-instances/create/', views.program_instance_create, name='program_instance_create'),
    path('program-instances/<int:instance_id>/', views.program_instance_detail, name='program_instance_detail'),
    path('program-instances/<int:instance_id>/edit/', views.program_instance_edit, name='program_instance_edit'),
    path('program-instances/<int:instance_id>/delete/', views.program_instance_delete, name='program_instance_delete'),
    path('program-instances/<int:instance_id>/toggle-status/', views.toggle_program_instance_status, name='toggle_program_instance_status'),
    
    # Buildout Management
    path('buildouts/', views.buildout_management, name='buildout_management'),
    path('buildouts/create/', views.buildout_create, name='buildout_create'),
    path('buildouts/<int:buildout_id>/', views.buildout_detail, name='buildout_detail'),
    path('buildouts/<int:buildout_id>/edit/', views.buildout_edit, name='buildout_edit'),
    path('buildouts/<int:buildout_id>/delete/', views.buildout_delete, name='buildout_delete'),
    path('buildouts/<int:buildout_id>/manage-responsibilities/', views.buildout_manage_responsibilities, name='buildout_manage_responsibilities'),
    path('buildouts/<int:buildout_id>/assign-roles/', views.buildout_assign_roles, name='buildout_assign_roles'),
    
    # Buildout Instance Creation
    path('buildouts/<int:buildout_id>/create-instance/', views.program_instance_create_from_buildout, name='buildout_create_instance'),
    
    # Registration Management
    path('registrations/', views.registration_management, name='registration_management'),
    path('registrations/<int:registration_id>/update-status/', views.update_registration_status, name='update_registration_status'),
    
    # Contact Management
    path('contacts/', views.contact_management, name='contact_management'),
    path('contacts/<int:contact_id>/update-status/', views.update_contact_status, name='update_contact_status'),
    
    # Child Management
    path('children/', views.child_management, name='child_management'),
    path('children/create/', views.child_create, name='child_create'),
    path('children/<int:child_id>/', views.child_detail, name='child_detail'),
    path('children/<int:child_id>/edit/', views.child_edit, name='child_edit'),
    path('children/<int:child_id>/delete/', views.child_delete, name='child_delete'),
    path('children/<int:child_id>/registrations/', views.child_registrations, name='child_registrations'),
    
    # Form Management
    path('forms/', views.form_management, name='form_management'),
    path('forms/create/', views.form_create, name='form_create'),
    path('forms/<int:form_id>/', views.form_detail, name='form_detail'),
    path('forms/<int:form_id>/edit/', views.form_edit, name='form_edit'),
    path('forms/<int:form_id>/delete/', views.form_delete, name='form_delete'),
    path('forms/<int:form_id>/duplicate/', views.form_duplicate, name='form_duplicate'),
    path('forms/<int:form_id>/manage-questions/', views.form_manage_questions, name='form_manage_questions'),
    
    # Role Management
    path('roles/', views.role_management, name='role_management'),
    path('roles/create/', views.role_create, name='role_create'),
    path('roles/<int:role_id>/', views.role_detail, name='role_detail'),
    path('roles/<int:role_id>/edit/', views.role_edit, name='role_edit'),
    path('roles/<int:role_id>/delete/', views.role_delete, name='role_delete'),
    path('roles/<int:role_id>/manage-users/', views.role_manage_users, name='role_manage_users'),
    path('roles/<int:role_id>/manage-responsibilities/', views.role_manage_responsibilities, name='role_manage_responsibilities'),
    path('roles/<int:role_id>/add-responsibility/', views.role_add_responsibility, name='role_add_responsibility'),
    
    # Responsibility Management
    path('responsibilities/<int:responsibility_id>/edit/', views.responsibility_edit, name='responsibility_edit'),
    path('responsibilities/<int:responsibility_id>/delete/', views.responsibility_delete, name='responsibility_delete'),
    
    # Cost Management
    path('costs/', views.cost_management, name='cost_management'),
    path('costs/create/', views.cost_create, name='cost_create'),
    path('costs/<int:cost_id>/', views.cost_detail, name='cost_detail'),
    path('costs/<int:cost_id>/edit/', views.cost_edit, name='cost_edit'),
    path('costs/<int:cost_id>/delete/', views.cost_delete, name='cost_delete'),
] 