from django.urls import path
from . import views

app_name = 'programs'

urlpatterns = [
    # Parent views
    path('parent/dashboard/', views.parent_dashboard, name='parent_dashboard'),
    path('parent/home/', views.parent_dashboard, name='parent_home'),  # Alias for new parent landing page
    path('parent/inquiry/', views.send_program_inquiry, name='send_program_inquiry'),
    path('parent/children/', views.manage_children, name='manage_children'),
    path('parent/children/<int:child_pk>/edit/', views.edit_child, name='edit_child'),
    # HTMX partials for parent dashboard
    path('parent/dashboard/calendar-partial/', views.parent_dashboard_calendar_partial, name='parent_dashboard_calendar_partial'),
    
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
    path('buildouts/<int:buildout_pk>/mark-ready/', views.buildout_mark_ready, name='buildout_mark_ready'),
    path('buildouts/<int:buildout_pk>/present/', views.present_to_contractor, name='present_to_contractor'),
    path('buildouts/<int:buildout_pk>/review/', views.buildout_review, name='buildout_review'),
    path('buildouts/<int:buildout_pk>/agree-sign/', views.buildout_agree_and_sign, name='buildout_agree_and_sign'),
    path('buildouts/<int:buildout_pk>/manage-responsibilities/', views.buildout_manage_responsibilities, name='buildout_manage_responsibilities'),
    path('buildouts/<int:buildout_pk>/assign-roles/', views.buildout_assign_roles, name='buildout_assign_roles'),
    path('program-types/<int:program_type_pk>/buildouts/', views.program_type_buildouts, name='program_type_buildouts'),
    
    # Contractor instance scheduling
    path('instances/<int:instance_pk>/schedule/', views.contractor_buildout_instance_schedule, name='contractor_instance_schedule'),
    
    # Program catalog and requests
    path('catalog/', views.program_catalog, name='program_catalog'),
    path('catalog/<int:program_type_id>/programs/', views.program_type_instances, name='program_type_instances'),
    path('catalog/<int:program_type_id>/request/', views.program_request_create, name='program_request_create'),
    
    # Enhanced Scheduling URLs
    # Contractor availability management
    path('contractor/availability/', views.contractor_availability_list, name='contractor_availability_list'),
    path('contractor/availability/new/', views.contractor_availability_create, name='contractor_availability_create'),
    path('contractor/availability/<int:pk>/', views.contractor_availability_detail, name='contractor_availability_detail'),
    path('contractor/availability/<int:pk>/edit/', views.contractor_availability_edit, name='contractor_availability_edit'),
    path('contractor/availability/<int:pk>/delete/', views.contractor_availability_delete, name='contractor_availability_delete'),
    path('contractor/availability/<int:availability_pk>/add-program/', views.add_program_to_availability, name='add_program_to_availability'),
    # HTMX partials for contractor availability
    path('contractor/availability/list-partial/', views.contractor_availability_list_partial, name='contractor_availability_list_partial'),
    path('contractor/availability/calendar-partial/', views.contractor_availability_calendar_partial, name='contractor_availability_calendar_partial'),
    path('contractor/availability/archive/', views.contractor_availability_archive, name='contractor_availability_archive'),
    
    # Session management for contractors
    path('contractor/sessions/', views.contractor_sessions_list, name='contractor_sessions_list'),
    path('sessions/<int:session_pk>/', views.session_detail, name='session_detail'),
    
    # Parent booking system
    path('parent/available-sessions/', views.available_sessions_list, name='available_sessions_list'),
    path('parent/book-session/<int:session_pk>/', views.book_session, name='book_session'),
    path('parent/bookings/', views.parent_bookings, name='parent_bookings'),
    path('parent/bookings/<int:booking_pk>/cancel/', views.cancel_booking, name='cancel_booking'),
    
    # Contractor day-off requests
    path('contractor/day-off-requests/', views.contractor_day_off_requests, name='contractor_day_off_requests'),
    path('contractor/day-off-requests/new/', views.contractor_day_off_request_create, name='contractor_day_off_request_create'),
    path('contractor/day-off-requests/<int:pk>/', views.contractor_day_off_request_detail, name='contractor_day_off_request_detail'),
    path('contractor/day-off-requests/<int:pk>/approve/', views.contractor_day_off_request_approve, name='contractor_day_off_request_approve'),
    path('contractor/day-off-requests/<int:pk>/deny/', views.contractor_day_off_request_deny, name='contractor_day_off_request_deny'),
    
    # Availability Rules System (Dynamic Occurrences)
    path('contractor/availability-rules/', views.availability_rules_index, name='availability_rules_index'),
    path('contractor/availability-rules/new/', views.availability_rule_create, name='availability_rule_create'),
    path('contractor/availability-rules/<int:pk>/', views.availability_rule_detail, name='availability_rule_detail'),
    path('contractor/availability-rules/<int:pk>/toggle/', views.availability_rule_toggle, name='availability_rule_toggle'),
    path('contractor/availability-rules/<int:pk>/archive/', views.availability_rule_archive, name='availability_rule_archive'),
    path('contractor/availability-rules/<int:pk>/delete/', views.availability_rule_delete, name='availability_rule_delete'),
    # HTMX partials for availability rules
    path('contractor/availability-rules/calendar-partial/', views.availability_rules_calendar_partial, name='availability_rules_calendar_partial'),
    path('contractor/availability-rules/list-partial/', views.availability_rules_list_partial, name='availability_rules_list_partial'),
    # Exception management
    path('contractor/availability-rules/<int:rule_pk>/exceptions/new/', views.availability_exception_create, name='availability_exception_create'),
    path('contractor/availability-exceptions/<int:pk>/delete/', views.availability_exception_delete, name='availability_exception_delete'),
    # Day details and booking
    path('contractor/availability-rules/day-details/', views.availability_day_details, name='availability_day_details'),
    path('contractor/availability-rules/create-booking/', views.create_rule_booking, name='create_rule_booking'),
] 