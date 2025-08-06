from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('stats/', views.dashboard_stats, name='stats'),
    path('activity/', views.dashboard_activity, name='activity'),
] 