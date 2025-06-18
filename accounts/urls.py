from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup, name='signup'),
    path('verify-code/', views.verify_code, name='verify_code'),
    path('profile/', views.profile, name='profile'),
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/<int:pk>/roles/', views.UserRoleUpdateView.as_view(), name='user_role_update'),
] 