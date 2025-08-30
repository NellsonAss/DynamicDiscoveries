from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from .services import AzureEmailService
from .models import Contact
from accounts.mixins import role_required
import logging

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
