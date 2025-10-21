from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.core.paginator import Paginator
from django.db.models import Q
from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from .services import AzureEmailService
from .models import Contact, Conversation, Message
from .forms import ContactComposeForm, ContactQuickForm, MessageReplyForm
from accounts.mixins import role_required
from programs.views import user_has_role
import logging
import secrets
import string

User = get_user_model()

logger = logging.getLogger(__name__)

@require_http_methods(['GET', 'POST'])
def contact_form(request):
    """Handle contact form submissions."""
    if request.method == 'POST':
        try:
            # Extract form data
            parent_name = request.POST.get('parent_name')
            email = request.POST.get('email')
            phone = request.POST.get('phone', '')
            interest = request.POST.get('interest')
            message = request.POST.get('message')
            
            # Validate required fields
            if not all([parent_name, email, interest, message]):
                messages.error(request, "Please fill in all required fields.")
                return render(request, 'home.html', {
                    'contact_form_data': request.POST
                })
            
            # Create contact inquiry
            contact = Contact.objects.create(
                parent_name=parent_name,
                email=email,
                phone=phone,
                interest=interest,
                message=message
            )
            
            # If user is authenticated, also create a conversation for user messaging
            if request.user.is_authenticated:
                try:
                    # Ensure user has Parent role
                    from django.contrib.auth.models import Group
                    parent_group, created = Group.objects.get_or_create(name='Parent')
                    if not request.user.groups.filter(name='Parent').exists():
                        request.user.groups.add(parent_group)
                        request.user.save()
                    
                    # Create conversation and first message
                    conversation = Conversation.objects.create(
                        owner=request.user,
                        subject=f"Contact Inquiry: {dict(Contact.INTEREST_CHOICES).get(interest, interest)}"
                    )
                    
                    Message.objects.create(
                        conversation=conversation,
                        author=request.user,
                        role='parent',
                        body=message
                    )
                    
                    logger.info(f"Created conversation {conversation.id} for authenticated user {request.user.email}")
                    
                except Exception as e:
                    logger.error(f"Failed to create conversation for authenticated user: {str(e)}")
                    # Don't fail the contact form if conversation creation fails
            
            # Send email notification
            try:
                logger.info(f"Attempting to send contact notification email to DynamicDiscoveries@nellson.net")
                email_service = AzureEmailService()
                result =                 email_service.send_templated_email(
                    to_email='DynamicDiscoveries@nellson.net',
                    subject=f'New Contact Inquiry from {parent_name}',
                    template_name='communications/contact_notification_email.html',
                    context={
                        'contact': contact,
                        'interest_display': dict(Contact.INTEREST_CHOICES)[interest]
                    }
                )
                if result:
                    logger.info(f"Contact notification email sent successfully for inquiry {contact.id}")
                else:
                    logger.error(f"Contact notification email failed for inquiry {contact.id}")
            except Exception as e:
                logger.error(f"Failed to send contact notification email: {str(e)}")
                logger.error(f"Exception details: {type(e).__name__}: {e}")
                # Don't fail the form submission if email fails
            
            # Send confirmation email to the parent
            try:
                logger.info(f"Attempting to send confirmation email to {email}")
                email_service = AzureEmailService()
                result = email_service.send_templated_email(
                    to_email=email,
                    subject='Thank you for contacting Dynamic Discoveries',
                    template_name='communications/contact_confirmation_email.html',
                    context={'contact': contact}
                )
                if result:
                    logger.info(f"Contact confirmation email sent successfully to {email}")
                else:
                    logger.error(f"Contact confirmation email failed for {email}")
            except Exception as e:
                logger.error(f"Failed to send contact confirmation email: {str(e)}")
                logger.error(f"Exception details: {type(e).__name__}: {e}")
            
            messages.success(request, "Thank you for your message! We'll get back to you soon.")
            return redirect('/')
            
        except Exception as e:
            logger.error(f"Error processing contact form: {str(e)}")
            messages.error(request, "Sorry, there was an error processing your request. Please try again.")
    
    return render(request, 'home.html')

@login_required
@role_required(['Admin', 'Consultant'])
def contact_list(request):
    """View for staff to see and manage contact inquiries."""
    # Get search parameters
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    interest_filter = request.GET.get('interest', '')
    
    # Build queryset
    contacts = Contact.objects.all()
    
    if search:
        contacts = contacts.filter(
            Q(parent_name__icontains=search) |
            Q(email__icontains=search) |
            Q(message__icontains=search)
        )
    
    if status_filter:
        contacts = contacts.filter(status=status_filter)
    
    if interest_filter:
        contacts = contacts.filter(interest=interest_filter)
    
    # Pagination
    paginator = Paginator(contacts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
        'interest_filter': interest_filter,
        'status_choices': Contact.STATUS_CHOICES,
        'interest_choices': Contact.INTEREST_CHOICES,
        'new_count': Contact.objects.filter(status='new').count(),
    }
    
    return render(request, 'communications/contact_list.html', context)


@login_required
@role_required(['Admin', 'Consultant'])
@require_http_methods(['GET'])
def contact_list_widget(request):
    """HTMX-friendly partial (no base include) for dashboard widget."""
    contacts = Contact.objects.order_by('-created_at')[:5]
    return render(request, 'communications/partials/contact_list_widget.html', {
        'contacts': contacts,
        'new_count': Contact.objects.filter(status='new').count(),
    })

@login_required
@role_required(['Admin', 'Consultant'])
def contact_detail(request, contact_id):
    """View for staff to see and update contact inquiry details."""
    try:
        contact = Contact.objects.get(id=contact_id)
    except Contact.DoesNotExist:
        messages.error(request, "Contact inquiry not found.")
        return redirect('communications:contact_list')
    
    if request.method == 'POST':
        # Update contact status and notes
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        
        if new_status and new_status != contact.status:
            contact.status = new_status
            contact.notes = notes
            contact.save()
            
            # Send follow-up email if status changed to 'contacted'
            if new_status == 'contacted':
                try:
                    email_service = AzureEmailService()
                    email_service.send_templated_email(
                        to_email=contact.email,
                        subject='We\'re reaching out about your inquiry',
                        template_name='communications/contact_followup_email.html',
                        context={'contact': contact}
                    )
                    logger.info(f"Follow-up email sent to {contact.email}")
                except Exception as e:
                    logger.error(f"Failed to send follow-up email: {str(e)}")
            
            messages.success(request, "Contact inquiry updated successfully.")
            return redirect('communications:contact_detail', contact_id=contact.id)
    
    context = {
        'contact': contact,
        'status_choices': Contact.STATUS_CHOICES,
        'interest_choices': dict(Contact.INTEREST_CHOICES),
    }
    
    return render(request, 'communications/contact_detail.html', context)

@require_http_methods(['GET', 'POST'])
def test_email(request):
    """Test view for sending emails via Azure Communication Service."""
    if request.method == 'POST':
        to_email = request.POST.get('email')
        if to_email:
            logger.info(f"Starting email test to {to_email}")
            
            # Log Azure settings (without sensitive data)
            from django.conf import settings
            has_connection_string = bool(getattr(settings, 'AZURE_COMMUNICATION_CONNECTION_STRING', None))
            has_sender_address = bool(getattr(settings, 'AZURE_COMMUNICATION_SENDER_ADDRESS', None))
            logger.info(f"Azure settings - Connection string present: {has_connection_string}, Sender address present: {has_sender_address}")
            
            try:
                # Initialize email service
                email_service = AzureEmailService()
                
                # Send test email
                email_service.send_templated_email(
                    to_email=to_email,
                    subject='Test Email from Dynamic Discoveries',
                    template_name='communications/test_email.html',
                    context={'test_message': 'This is a test email from the Dynamic Discoveries system.'}
                )
                
                messages.success(request, f"Test email sent successfully to {to_email}")
                logger.info(f"Test email sent successfully to {to_email}")
                
            except Exception as e:
                error_msg = f"Failed to send test email: {str(e)}"
                messages.error(request, error_msg)
                logger.error(error_msg)
    
    return render(request, 'communications/test_email.html')


# ============================================================================
# NEW MESSAGE SYSTEM VIEWS
# ============================================================================

def get_client_ip(request):
    """Get client IP address for rate limiting."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def check_rate_limit(request, key_suffix='', limit=5, window=600):
    """Simple rate limiting using cache."""
    client_ip = get_client_ip(request)
    cache_key = f"rate_limit:{client_ip}:{key_suffix}"
    
    attempts = cache.get(cache_key, 0)
    if attempts >= limit:
        return False
    
    cache.set(cache_key, attempts + 1, window)
    return True


def contact_entry_view(request):
    """Entry point for contact system - shows appropriate form based on auth status."""
    logger.info(f"Contact entry view called for user: {request.user}, authenticated: {request.user.is_authenticated}")
    logger.info(f"User groups: {list(request.user.groups.values_list('name', flat=True)) if request.user.is_authenticated else 'N/A'}")
    
    # If user is authenticated and has Parent role, redirect to parent dashboard
    if request.user.is_authenticated and user_has_role(request.user, 'Parent'):
        logger.info("Authenticated parent user, redirecting to parent dashboard")
        messages.info(request, "You can send messages from your Parent Dashboard.")
        return redirect('programs:parent_dashboard')
    
    if request.user.is_authenticated:
        form = ContactComposeForm()
        template = 'communications/contact/_compose_form.html'
        logger.info("Showing compose form for authenticated user")
    else:
        form = ContactQuickForm()
        template = 'communications/contact/_quick_form.html'
        logger.info("Showing quick form for anonymous user")
    
    context = {
        'form': form,
        'user_authenticated': request.user.is_authenticated
    }
    
    # If this is an HTMX request, return just the partial
    if request.headers.get('HX-Request'):
        logger.info("Returning HTMX partial")
        return render(request, template, context)
    
    # Otherwise return the full page
    logger.info("Returning full contact entry page")
    logger.info(f"Template: communications/contact/entry.html, Context keys: {list(context.keys())}")
    return render(request, 'communications/contact/entry.html', context)


@require_POST
@login_required
def contact_compose_post_view(request):
    """Handle authenticated user compose form submission."""
    if not check_rate_limit(request, 'compose'):
        messages.error(request, "Too many attempts. Please wait a few minutes before trying again.")
        return redirect('communications:contact_entry')
    
    form = ContactComposeForm(request.POST)
    if form.is_valid():
        try:
            # Ensure user has Parent role
            from django.contrib.auth.models import Group
            parent_group, created = Group.objects.get_or_create(name='Parent')
            if not request.user.groups.filter(name='Parent').exists():
                request.user.groups.add(parent_group)
                request.user.save()
            
            # Create conversation and first message
            conversation = Conversation.objects.create(
                owner=request.user,
                subject=form.cleaned_data['subject']
            )
            
            Message.objects.create(
                conversation=conversation,
                author=request.user,
                role='parent',
                body=form.cleaned_data['message']
            )
            
            # Also create a Contact record for admin tracking
            try:
                Contact.objects.create(
                    parent_name=request.user.get_full_name() or request.user.email.split('@')[0],
                    email=request.user.email,
                    phone=getattr(request.user, 'phone', ''),
                    interest='other',  # Default since this is a general message
                    message=form.cleaned_data['message'],
                    status='new'
                )
                logger.info(f"Created Contact record for user message from {request.user.email}")
            except Exception as e:
                logger.error(f"Failed to create Contact record for user message: {str(e)}")
                # Don't fail the message if Contact creation fails
            
            # Send internal notification email
            try:
                from django.conf import settings
                notify_email = getattr(settings, 'CONTACT_NOTIFY_EMAIL', 'DynamicDiscoveries@nellson.net')
                
                email_service = AzureEmailService()
                email_service.send_templated_email(
                    to_email=notify_email,
                    subject=f'New Message from {request.user.email}',
                    template_name='communications/internal_notification_email.html',
                    context={
                        'conversation': conversation,
                        'user': request.user,
                        'admin_url': request.build_absolute_uri(
                            reverse('admin:communications_conversation_change', args=[conversation.id])
                        )
                    }
                )
                
                # Note: Parent acknowledgment removed for authenticated users
                # They can see their message in the dashboard immediately
                
            except Exception as e:
                logger.error(f"Failed to send notification emails: {str(e)}")
            
            messages.success(
                request, 
                f"Thanks—your message was sent. We'll email {request.user.email} when we reply."
            )
            
            # Redirect to Parent Dashboard with messages focus
            # Handle HTMX requests with proper redirect
            if request.headers.get('HX-Request'):
                from django.http import HttpResponse
                response = HttpResponse()
                response['HX-Redirect'] = '/programs/parent/dashboard/?show=messages'
                return response
            
            return redirect('/programs/parent/dashboard/?show=messages')
            
        except Exception as e:
            logger.error(f"Error creating conversation: {str(e)}")
            messages.error(request, "An error occurred. Please try again.")
    
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
    
    return redirect('communications:contact_entry')


@require_POST
def contact_quick_post_view(request):
    """Handle anonymous user quick create form submission."""
    if not check_rate_limit(request, 'quick'):
        messages.error(request, "Too many attempts. Please wait a few minutes before trying again.")
        return redirect('communications:contact_entry')
    
    form = ContactQuickForm(request.POST)
    if form.is_valid():
        logger.info(f"ContactQuickForm is valid for email: {form.cleaned_data.get('email')}")
        try:
            email = form.cleaned_data['email']
            
            # Check if user already exists (case insensitive)
            existing_user = User.objects.filter(email__iexact=email).first()
            if existing_user:
                messages.error(
                    request, 
                    "Account exists. Please sign in."
                )
                # Add login CTA context
                context = {
                    'show_login_cta': True,
                    'form': form,
                    'user_authenticated': False
                }
                return render(request, 'communications/contact/entry.html', context)
            
            # Create new user with transaction to ensure all operations complete
            from django.contrib.auth.models import Group
            from django.db import transaction
            
            with transaction.atomic():
                # Create new user
                user = User.objects.create_user(
                    email=email,
                    first_name=form.cleaned_data.get('first_name', ''),
                    last_name=form.cleaned_data.get('last_name', ''),
                    is_active=True
                )
                
                # Set unusable password - they'll need to use password reset
                user.set_unusable_password()
                user.save()
                
                # Add user to Parent group
                parent_group, created = Group.objects.get_or_create(name='Parent')
                user.groups.add(parent_group)
                
                # Refresh user from database to ensure group is loaded
                user.refresh_from_db()
            
            # Don't auto-login - user should verify email like normal login process
            
            # Create conversation and first message
            conversation = Conversation.objects.create(
                owner=user,
                subject=form.cleaned_data['subject']
            )
            
            Message.objects.create(
                conversation=conversation,
                author=user,
                role='parent',
                body=form.cleaned_data['message']
            )
            
            # Also create a Contact record for admin tracking
            try:
                Contact.objects.create(
                    parent_name=f"{user.first_name} {user.last_name}".strip() or user.email.split('@')[0],
                    email=user.email,
                    phone='',  # Not collected in quick form
                    interest='other',  # Default since this is a general message
                    message=form.cleaned_data['message'],
                    status='new'
                )
                logger.info(f"Created Contact record for new user message from {user.email}")
            except Exception as e:
                logger.error(f"Failed to create Contact record for new user message: {str(e)}")
                # Don't fail the message if Contact creation fails
            
            # Send account verification email
            try:
                from accounts.views import generate_verification_code
                
                email_service = AzureEmailService()
                
                # Generate verification code for the new user
                verification_code = generate_verification_code()
                
                # Store verification code in user's session data or a temporary model
                # For now, we'll just send a welcome email with instructions
                email_service.send_templated_email(
                    to_email=user.email,
                    subject='Welcome to Dynamic Discoveries - Account Created',
                    template_name='communications/welcome_email.html',
                    context={
                        'user': user,
                        'verification_code': verification_code,
                        'login_url': request.build_absolute_uri(reverse('accounts:login'))
                    }
                )
                
            except Exception as e:
                logger.error(f"Failed to send welcome email: {str(e)}")
            
            # Send internal notification email
            try:
                from django.conf import settings
                notify_email = getattr(settings, 'CONTACT_NOTIFY_EMAIL', 'DynamicDiscoveries@nellson.net')
                
                email_service = AzureEmailService()
                email_service.send_templated_email(
                    to_email=notify_email,
                    subject=f'New Account + Message from {user.email}',
                    template_name='communications/internal_notification_email.html',
                    context={
                        'conversation': conversation,
                        'user': user,
                        'new_account': True,
                        'admin_url': request.build_absolute_uri(
                            reverse('admin:communications_conversation_change', args=[conversation.id])
                        )
                    }
                )
                
            except Exception as e:
                logger.error(f"Failed to send internal notification: {str(e)}")
            
            messages.success(
                request,
                f"Account created and message sent! Please check {user.email} for your welcome email, then log in to access your account and view responses."
            )
            
            # Redirect to login page so user can verify their email
            logger.info(f"Redirecting user {user.email} to login page for email verification")
            
            # Handle HTMX requests with proper redirect
            if request.headers.get('HX-Request'):
                from django.http import HttpResponse
                response = HttpResponse()
                response['HX-Redirect'] = reverse('accounts:login')
                return response
            
            return redirect('accounts:login')
            
        except Exception as e:
            logger.error(f"Error in quick create: {str(e)}")
            logger.error(f"Exception details: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            messages.error(request, "An error occurred. Please try again.")
    
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
    
    return redirect('communications:contact_entry')


@login_required
def parent_messages_list_view(request):
    """List all conversations for the authenticated parent."""
    conversations = Conversation.objects.filter(
        owner=request.user
    ).prefetch_related('messages').order_by('-updated_at')
    
    paginator = Paginator(conversations, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'conversations': page_obj,
        'total_conversations': conversations.count()
    }
    
    return render(request, 'communications/parent/messages/list.html', context)


@login_required
def parent_messages_detail_view(request, pk):
    """Show detailed conversation thread with reply form."""
    conversation = get_object_or_404(Conversation, pk=pk, owner=request.user)
    
    messages_list = conversation.messages.select_related('author').order_by('created_at')
    reply_form = MessageReplyForm()
    
    context = {
        'conversation': conversation,
        'messages': messages_list,
        'reply_form': reply_form
    }
    
    return render(request, 'communications/parent/messages/detail.html', context)


@login_required
def parent_messages_compose_view(request):
    """Compose a new message from the Parent Dashboard."""
    if not user_has_role(request.user, 'Parent'):
        messages.error(request, "This page is for parents. If you think this is a mistake, contact support.")
        return redirect('dashboard:dashboard')
    
    form = ContactComposeForm()
    context = {
        'form': form,
        'user_authenticated': True
    }
    
    # If this is an HTMX request, return just the form
    if request.headers.get('HX-Request'):
        return render(request, 'communications/contact/_compose_form.html', context)
    
    # Otherwise return the full page
    return render(request, 'communications/parent/messages/compose.html', context)


@require_POST
@login_required
def parent_messages_compose_post_view(request):
    """Handle message composition from Parent Dashboard."""
    if not user_has_role(request.user, 'Parent'):
        messages.error(request, "This page is for parents. If you think this is a mistake, contact support.")
        return redirect('dashboard:dashboard')
    
    if not check_rate_limit(request, 'compose'):
        messages.error(request, "Too many attempts. Please wait a few minutes before trying again.")
        return redirect('programs:parent_dashboard')
    
    form = ContactComposeForm(request.POST)
    if form.is_valid():
        try:
            # Create conversation and first message
            conversation = Conversation.objects.create(
                owner=request.user,
                subject=form.cleaned_data['subject']
            )
            
            Message.objects.create(
                conversation=conversation,
                author=request.user,
                role='parent',
                body=form.cleaned_data['message']
            )
            
            # Send internal notification email
            try:
                from django.conf import settings
                notify_email = getattr(settings, 'CONTACT_NOTIFY_EMAIL', 'DynamicDiscoveries@nellson.net')
                
                email_service = AzureEmailService()
                email_service.send_templated_email(
                    to_email=notify_email,
                    subject=f'New Message from {request.user.email}',
                    template_name='communications/internal_notification_email.html',
                    context={
                        'conversation': conversation,
                        'user': request.user,
                        'admin_url': request.build_absolute_uri(
                            reverse('admin:communications_conversation_change', args=[conversation.id])
                        )
                    }
                )
                
            except Exception as e:
                logger.error(f"Failed to send notification emails: {str(e)}")
            
            messages.success(
                request,
                f"Message sent! We'll email you at {request.user.email} when we reply."
            )
            
            # Redirect back to Parent Dashboard with messages focus
            return redirect('/programs/parent/dashboard/?show=messages')
            
        except Exception as e:
            logger.error(f"Error in compose: {str(e)}")
            messages.error(request, "An error occurred. Please try again.")
    
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
    
    return redirect('programs:parent_dashboard')


@require_POST
@login_required
def parent_messages_reply_post_view(request, pk):
    """Handle reply to conversation."""
    conversation = get_object_or_404(Conversation, pk=pk, owner=request.user)
    
    if not check_rate_limit(request, f'reply_{pk}'):
        messages.error(request, "Too many attempts. Please wait a few minutes before trying again.")
        return redirect('communications:parent_messages_detail', pk=pk)
    
    form = MessageReplyForm(request.POST)
    if form.is_valid():
        try:
            # Create reply message
            Message.objects.create(
                conversation=conversation,
                author=request.user,
                role='parent',
                body=form.cleaned_data['body']
            )
            
            # Update conversation timestamp and reopen if closed
            if conversation.status == 'closed':
                conversation.status = 'open'
            conversation.updated_at = timezone.now()
            conversation.save()
            
            messages.success(request, "Reply sent successfully.")
            
            # If HTMX request, re-render the detail thread
            if request.headers.get('HX-Request'):
                messages_list = conversation.messages.select_related('author').order_by('created_at')
                reply_form = MessageReplyForm()  # Fresh form
                context = {
                    'conversation': conversation,
                    'messages': messages_list,
                    'reply_form': reply_form
                }
                return render(request, 'communications/parent/messages/detail.html', context)
            
        except Exception as e:
            logger.error(f"Error creating reply: {str(e)}")
            messages.error(request, "An error occurred. Please try again.")
    
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
    
    return redirect('communications:parent_messages_detail', pk=pk)
