from django.urls import path
from . import views

app_name = 'communications'

urlpatterns = [
    # Existing contact form routes
    path('contact/old/', views.contact_form, name='contact_form_old'),
    path('contact/form/', views.contact_form, name='contact_form'),
    path('contacts/', views.contact_list, name='contact_list'),
    path('contacts/widget/', views.contact_list_widget, name='contact_list_widget'),
    path('contacts/<int:contact_id>/', views.contact_detail, name='contact_detail'),
    path('test-email/', views.test_email, name='test_email'),
    
    # New message system routes
    path('contact/', views.contact_entry_view, name='contact_entry'),
    path('contact/compose/', views.contact_compose_post_view, name='contact_compose'),
    path('contact/quick/', views.contact_quick_post_view, name='contact_quick'),
    
    # Parent message routes
    path('parent/messages/', views.parent_messages_list_view, name='parent_messages_list'),
    path('parent/messages/compose/', views.parent_messages_compose_view, name='parent_messages_compose'),
    path('parent/messages/compose/send/', views.parent_messages_compose_post_view, name='parent_messages_compose_send'),
    path('parent/messages/<int:pk>/', views.parent_messages_detail_view, name='parent_messages_detail'),
    path('parent/messages/<int:pk>/reply/', views.parent_messages_reply_post_view, name='parent_messages_reply'),
] 