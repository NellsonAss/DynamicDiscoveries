from django.urls import path
from . import views

app_name = 'communications'

urlpatterns = [
    path('test-email/', views.test_email, name='test_email'),
] 