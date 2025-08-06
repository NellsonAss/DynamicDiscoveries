from django.urls import path
from . import views

app_name = 'programs'

urlpatterns = [
    # Parent views
    path('parent/dashboard/', views.parent_dashboard, name='parent_dashboard'),
    path('parent/children/', views.manage_children, name='manage_children'),
    path('parent/children/<int:child_pk>/edit/', views.edit_child, name='edit_child'),
    
    # Program views
    path('programs/<int:pk>/', views.program_instance_detail, name='program_instance_detail'),
    path('programs/<int:program_instance_pk>/register/', views.register_child, name='register_child'),
    path('registration/<int:registration_pk>/form/', views.complete_registration_form, name='complete_registration_form'),
    
    # Contractor/Admin views
    path('contractor/dashboard/', views.contractor_dashboard, name='contractor_dashboard'),
    path('forms/', views.form_builder, name='form_builder'),
    path('forms/<int:form_pk>/', views.form_builder, name='form_edit'),
    path('forms/<int:form_pk>/duplicate/', views.duplicate_form, name='duplicate_form'),
    
    # HTMX endpoints for form builder
    path('forms/<int:form_pk>/questions/add/', views.add_form_question, name='add_form_question'),
    path('questions/<int:question_pk>/delete/', views.delete_form_question, name='delete_form_question'),
    
    # Registration management
    path('programs/<int:program_instance_pk>/registrations/', views.view_registrations, name='view_registrations'),
    path('registrations/<int:registration_pk>/status/', views.update_registration_status, name='update_registration_status'),
    path('programs/<int:program_instance_pk>/send-form/', views.send_form_to_participants, name='send_form_to_participants'),
    
    # Program Buildout views
    path('roles/', views.role_list, name='role_list'),
    path('buildouts/', views.buildout_list, name='buildout_list'),
    path('buildouts/<int:buildout_pk>/', views.buildout_detail, name='buildout_detail'),
    path('program-types/<int:program_type_pk>/buildouts/', views.program_type_buildouts, name='program_type_buildouts'),
] 