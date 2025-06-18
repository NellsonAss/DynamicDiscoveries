from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django_otp import devices_for_user
from django_otp.plugins.otp_totp.models import TOTPDevice
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.conf import settings
from django.urls import reverse
from .mixins import RoleRequiredMixin
from django.views.generic import ListView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
import random
import string
import logging
from communications.services import AzureEmailService

logger = logging.getLogger(__name__)
User = get_user_model()

def get_user_totp_device(user, confirmed=None):
    """Get the user's TOTP device."""
    devices = devices_for_user(user, confirmed=confirmed)
    for device in devices:
        if isinstance(device, TOTPDevice):
            return device

def generate_verification_code():
    """Generate a random 6-digit verification code."""
    return ''.join(random.choices(string.digits, k=6))

def get_email_service():
    """Get or create the email service instance."""
    try:
        service = AzureEmailService()
        if not service.client:
            logger.error("Azure Email Client not initialized. Check connection string and sender address.")
        return service
    except Exception as e:
        logger.error(f"Failed to initialize email service: {str(e)}")
        return None

@require_http_methods(['GET', 'POST'])
def login_view(request):
    """Handle the login process with email verification."""
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            # Generate verification code
            verification_code = generate_verification_code()
            
            # Store in session
            request.session['verification_email'] = email
            request.session['verification_code'] = verification_code
            
            # Send verification email
            email_service = get_email_service()
            if email_service:
                try:
                    logger.info(f"Attempting to send verification email to {email}")
                    email_service.send_templated_email(
                        to_email=email,
                        subject='Your Verification Code',
                        template_name='communications/verification_code_email.html',
                        context={'code': verification_code}
                    )
                    logger.info(f"Verification email sent successfully to {email}")
                    
                    # Check if this is an HTMX request
                    if request.headers.get('HX-Request'):
                        # Return the verification code form as a partial
                        return render(request, 'accounts/_verify_code_card.html', {'email': email})
                    return redirect('accounts:verify_code')
                except Exception as e:
                    logger.error(f"Failed to send verification email to {email}: {str(e)}")
                    if request.headers.get('HX-Request'):
                        return render(request, 'accounts/_login_form.html', {
                            'error': f"Failed to send verification email: {str(e)}"
                        })
                    messages.error(request, f"Failed to send verification email: {str(e)}")
            else:
                logger.error("Email service not available")
                if request.headers.get('HX-Request'):
                    return render(request, 'accounts/_login_form.html', {
                        'error': "Email service is currently unavailable. Please try again later."
                    })
                messages.error(request, "Email service is currently unavailable. Please try again later.")
    
    return render(request, 'accounts/login.html')

@require_http_methods(['GET', 'POST'])
def verify_code(request):
    """Handle the verification code submission."""
    email = request.session.get('verification_email')
    stored_code = request.session.get('verification_code')
    
    if not email or not stored_code:
        if request.headers.get('HX-Request'):
            return render(request, 'accounts/_login_form.html', {
                'error': "No verification code found. Please try logging in again."
            })
        messages.error(request, "No verification code found. Please try logging in again.")
        return redirect('accounts:login')
    
    if request.method == 'POST':
        submitted_code = request.POST.get('code')
        if submitted_code == stored_code:
            # Get or create user
            user, created = User.objects.get_or_create(email=email)
            
            # Explicitly create profile if user was just created
            if created:
                Profile.objects.create(user=user)
                # Add default 'User' role
                user_group, _ = Group.objects.get_or_create(name='User')
                user.groups.add(user_group)
            
            # Specify the authentication backend
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            
            # Clear session data
            request.session.pop('verification_email', None)
            request.session.pop('verification_code', None)
            
            if request.headers.get('HX-Request'):
                # Return a response that will trigger a full page reload
                response = HttpResponse()
                response['HX-Redirect'] = reverse('dashboard:dashboard')
                response['HX-Trigger'] = '{"pageReload": true}'
                return response
            return redirect('dashboard:dashboard')
        else:
            if request.headers.get('HX-Request'):
                return render(request, 'accounts/_verify_code_card.html', {
                    'email': email,
                    'error': "Invalid verification code. Please try again."
                })
            messages.error(request, "Invalid verification code. Please try again.")
    
    return render(request, 'accounts/verify_code.html', {'email': email})

@login_required
def profile(request):
    """User profile view."""
    return render(request, 'accounts/profile.html', {
        'user_roles': request.user.groups.all()
    })

def debug_env(request):
    return HttpResponse(f"AZURE_COMMUNICATION_CONNECTION_STRING: {getattr(settings, 'AZURE_COMMUNICATION_CONNECTION_STRING', 'NOT SET')}")

@require_http_methods(['GET', 'POST'])
def signup(request):
    """Handle user registration."""
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            # Generate verification code
            verification_code = generate_verification_code()
            
            # Store in session
            request.session['verification_email'] = email
            request.session['verification_code'] = verification_code
            
            # Send verification email
            email_service = get_email_service()
            if email_service:
                try:
                    logger.info(f"Attempting to send verification email to {email}")
                    email_service.send_templated_email(
                        to_email=email,
                        subject='Your Verification Code',
                        template_name='communications/verification_code_email.html',
                        context={'code': verification_code}
                    )
                    logger.info(f"Verification email sent successfully to {email}")
                    
                    # Check if this is an HTMX request
                    if request.headers.get('HX-Request'):
                        return render(request, 'accounts/_verify_code_card.html', {'email': email})
                    return redirect('accounts:verify_code')
                except Exception as e:
                    logger.error(f"Failed to send verification email to {email}: {str(e)}")
                    if request.headers.get('HX-Request'):
                        return render(request, 'accounts/_signup_form.html', {
                            'error': f"Failed to send verification email: {str(e)}"
                        })
                    messages.error(request, f"Failed to send verification email: {str(e)}")
            else:
                logger.error("Email service not available")
                if request.headers.get('HX-Request'):
                    return render(request, 'accounts/_signup_form.html', {
                        'error': "Email service is currently unavailable. Please try again later."
                    })
                messages.error(request, "Email service is currently unavailable. Please try again later.")
    
    return render(request, 'accounts/signup.html')

class UserListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    """View for listing users (admin only)."""
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    required_roles = ['Admin']
    
    def get_queryset(self):
        return User.objects.all().prefetch_related('groups')

class UserRoleUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    """View for updating user roles (admin only)."""
    model = User
    template_name = 'accounts/user_role_update.html'
    fields = []
    required_roles = ['Admin']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get all roles including Admin
        context['available_roles'] = Group.objects.all()
        context['user_roles'] = self.object.groups.all()
        return context
    
    def post(self, request, *args, **kwargs):
        user = self.get_object()
        role_id = request.POST.get('role_id')
        action = request.POST.get('action')
        
        if role_id and action:
            role = get_object_or_404(Group, id=role_id)
            
            # Prevent removing Admin role from the last admin
            if role.name == 'Admin' and action == 'remove':
                admin_count = User.objects.filter(groups__name='Admin').count()
                if admin_count <= 1:
                    messages.error(request, 'Cannot remove the last admin user')
                    if request.headers.get('HX-Request'):
                        return render(request, 'accounts/_user_roles.html', {
                            'user': user,
                            'user_roles': user.groups.all(),
                            'available_roles': Group.objects.all()
                        })
                    return redirect('accounts:user_role_update', pk=user.pk)
            
            if action == 'add':
                user.groups.add(role)
                messages.success(request, f'Added {role.name} role to {user.email}')
            elif action == 'remove':
                user.groups.remove(role)
                messages.success(request, f'Removed {role.name} role from {user.email}')
        
        if request.headers.get('HX-Request'):
            return render(request, 'accounts/_user_roles.html', {
                'user': user,
                'user_roles': user.groups.all(),
                'available_roles': Group.objects.all()
            })
        return redirect('accounts:user_role_update', pk=user.pk) 