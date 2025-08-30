from django.urls import path
from . import views

app_name = 'communications'

urlpatterns = [
    path('contact/', views.contact_form, name='contact'),
    path('contact/form/', views.contact_form, name='contact_form'),
    path('contacts/', views.contact_list, name='contact_list'),
    path('contacts/widget/', views.contact_list_widget, name='contact_list_widget'),
    path('contacts/<int:contact_id>/', views.contact_detail, name='contact_detail'),
    path('test-email/', views.test_email, name='test_email'),
] 