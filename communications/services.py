from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from azure.communication.email import EmailClient
import logging

logger = logging.getLogger(__name__)

class AzureEmailService:
    def __init__(self):
        self.connection_string = getattr(settings, 'AZURE_COMMUNICATION_CONNECTION_STRING', None)
        self.sender_address = getattr(settings, 'AZURE_COMMUNICATION_SENDER_ADDRESS', None)
        self.client = None
        
        if not self.connection_string:
            logger.error("AZURE_COMMUNICATION_CONNECTION_STRING is not set in settings")
            return
            
        if not self.sender_address:
            logger.error("AZURE_COMMUNICATION_SENDER_ADDRESS is not set in settings")
            return
            
        try:
            logger.info("Initializing Azure Email Client")
            self.client = EmailClient.from_connection_string(self.connection_string)
            logger.info("Azure Email Client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Azure Email Client: {str(e)}")
            self.client = None

    def send_email(self, to_email, subject, html_content):
        """Send an email using Azure Communication Service with fallback to Django's email backend."""
        if self.client:
            try:
                logger.info(f"Attempting to send email via Azure to {to_email}")
                message = {
                    "senderAddress": self.sender_address,
                    "recipients": {
                        "to": [{"address": to_email}]
                    },
                    "content": {
                        "subject": subject,
                        "html": html_content
                    }
                }
                
                poller = self.client.begin_send(message)
                result = poller.result()
                logger.info(f"Email sent successfully via Azure to {to_email}")
                return True
            except Exception as e:
                logger.error(f"Azure email sending failed for {to_email}: {str(e)}")
                logger.info("Falling back to Django email backend")
                # Fall back to Django's email backend
                return send_mail(
                    subject=subject,
                    message='',  # Plain text version
                    html_message=html_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[to_email],
                    fail_silently=False
                )
        else:
            logger.info(f"Azure client not available, using Django email backend for {to_email}")
            # Use Django's email backend if Azure client is not available
            return send_mail(
                subject=subject,
                message='',  # Plain text version
                html_message=html_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                fail_silently=False
            )

    def send_templated_email(self, to_email, subject, template_name, context):
        """Send an email using a template."""
        logger.info(f"Rendering email template {template_name} for {to_email}")
        html_content = render_to_string(template_name, context)
        return self.send_email(to_email, subject, html_content) 