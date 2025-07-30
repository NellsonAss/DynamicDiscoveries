from django.urls import path
from . import views

app_name = 'dynamic_discoveries'

urlpatterns = [
    path('', views.home, name='home'),
    path('programs/', views.programs, name='programs'),
    path('tutoring/', views.tutoring, name='tutoring'),
    path('assessments/', views.assessments, name='assessments'),
    path('about/', views.about, name='about'),
] 