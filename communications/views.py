from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from .services import AzureEmailService
import logging

logger = logging.getLogger(__name__)

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
                if not email_service.client:
                    logger.error("Azure Email Client not initialized")
                    messages.error(request, "Azure Email Client not initialized. Check your settings.")
                    return render(request, 'communications/test_email.html')
                
                # Send a test email
                logger.info(f"Attempting to send test email to {to_email}")
                email_service.send_templated_email(
                    to_email=to_email,
                    subject='Test Email from Azure Communication Service',
                    template_name='communications/verification_code_email.html',
                    context={'code': '123456'}  # Test code
                )
                logger.info(f"Test email sent successfully to {to_email}")
                messages.success(request, f'Test email sent successfully to {to_email}')
            except Exception as e:
                logger.error(f"Failed to send test email: {str(e)}", exc_info=True)
                messages.error(request, f'Failed to send email: {str(e)}')
    
    return render(request, 'communications/test_email.html')
