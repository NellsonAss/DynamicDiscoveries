"""
Test unified communication system - messages from logged-in users should create both Contact and Conversation records.
"""
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from communications.models import Contact, Conversation, Message

User = get_user_model()


class UnifiedCommunicationTestCase(TestCase):
    """Test that logged-in users create both Contact and Conversation records."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.client.login(email='test@example.com', password='testpass123')
    
    def test_contact_form_creates_both_records(self):
        """Test that contact form from authenticated user creates both Contact and Conversation."""
        # Count initial records
        initial_contacts = Contact.objects.count()
        initial_conversations = Conversation.objects.count()
        initial_messages = Message.objects.count()
        
        # Submit contact form
        response = self.client.post('/communications/contact/form/', {
            'parent_name': 'Test User',
            'email': 'test@example.com',
            'phone': '555-1234',
            'interest': 'after_school',
            'message': 'Test message from contact form'
        })
        
        # Should redirect to home page
        self.assertEqual(response.status_code, 302)
        
        # Check that both Contact and Conversation records were created
        self.assertEqual(Contact.objects.count(), initial_contacts + 1)
        self.assertEqual(Conversation.objects.count(), initial_conversations + 1)
        self.assertEqual(Message.objects.count(), initial_messages + 1)
        
        # Verify Contact record
        contact = Contact.objects.latest('created_at')
        self.assertEqual(contact.parent_name, 'Test User')
        self.assertEqual(contact.email, 'test@example.com')
        self.assertEqual(contact.interest, 'after_school')
        self.assertEqual(contact.message, 'Test message from contact form')
        
        # Verify Conversation record
        conversation = Conversation.objects.latest('created_at')
        self.assertEqual(conversation.owner, self.user)
        self.assertEqual(conversation.subject, 'Contact Inquiry: After-School Enrichment')
        
        # Verify Message record
        message = Message.objects.latest('created_at')
        self.assertEqual(message.conversation, conversation)
        self.assertEqual(message.author, self.user)
        self.assertEqual(message.role, 'parent')
        self.assertEqual(message.body, 'Test message from contact form')
    
    def test_compose_message_creates_both_records(self):
        """Test that compose message creates both Contact and Conversation records."""
        # Count initial records
        initial_contacts = Contact.objects.count()
        initial_conversations = Conversation.objects.count()
        initial_messages = Message.objects.count()
        
        # Submit compose message form
        response = self.client.post(reverse('communications:contact_compose'), {
            'subject': 'Test Subject',
            'message': 'Test message from compose form'
        })
        
        # Should redirect to parent dashboard
        self.assertEqual(response.status_code, 302)
        
        # Check that both Contact and Conversation records were created
        self.assertEqual(Contact.objects.count(), initial_contacts + 1)
        self.assertEqual(Conversation.objects.count(), initial_conversations + 1)
        self.assertEqual(Message.objects.count(), initial_messages + 1)
        
        # Verify Contact record
        contact = Contact.objects.latest('created_at')
        self.assertEqual(contact.parent_name, 'Test User')
        self.assertEqual(contact.email, 'test@example.com')
        self.assertEqual(contact.interest, 'other')  # Default for compose messages
        self.assertEqual(contact.message, 'Test message from compose form')
        
        # Verify Conversation record
        conversation = Conversation.objects.latest('created_at')
        self.assertEqual(conversation.owner, self.user)
        self.assertEqual(conversation.subject, 'Test Subject')
        
        # Verify Message record
        message = Message.objects.latest('created_at')
        self.assertEqual(message.conversation, conversation)
        self.assertEqual(message.author, self.user)
        self.assertEqual(message.role, 'parent')
        self.assertEqual(message.body, 'Test message from compose form')
    
    def test_anonymous_quick_form_creates_both_records(self):
        """Test that anonymous quick form creates both Contact and Conversation records."""
        # Logout user
        self.client.logout()
        
        # Count initial records
        initial_contacts = Contact.objects.count()
        initial_conversations = Conversation.objects.count()
        initial_messages = Message.objects.count()
        initial_users = User.objects.count()
        
        # Mock the form validation to bypass CAPTCHA for testing
        from unittest.mock import patch
        with patch('communications.views.ContactQuickForm') as mock_form_class:
            mock_form = mock_form_class.return_value
            mock_form.is_valid.return_value = True
            mock_form.cleaned_data = {
                'email': 'anonymous@example.com',
                'first_name': 'Anonymous',
                'last_name': 'User',
                'subject': 'Test Subject',
                'message': 'Test message from anonymous user'
            }
            
            # Submit quick form (creates user account + message)
            response = self.client.post('/communications/contact/quick/', {
                'email': 'anonymous@example.com',
                'first_name': 'Anonymous',
                'last_name': 'User',
                'subject': 'Test Subject',
                'message': 'Test message from anonymous user',
                'captcha_0': 'dummy-captcha-0',
                'captcha_1': 'PASSED',
                'honeypot': ''
            })
        
        # Should redirect
        self.assertEqual(response.status_code, 302)
        
        # Check that both Contact and Conversation records were created, plus new user
        self.assertEqual(Contact.objects.count(), initial_contacts + 1)
        self.assertEqual(Conversation.objects.count(), initial_conversations + 1)
        self.assertEqual(Message.objects.count(), initial_messages + 1)
        self.assertEqual(User.objects.count(), initial_users + 1)
        
        # Verify Contact record
        contact = Contact.objects.latest('created_at')
        self.assertEqual(contact.parent_name, 'Anonymous User')
        self.assertEqual(contact.email, 'anonymous@example.com')
        self.assertEqual(contact.interest, 'other')  # Default for quick form
        self.assertEqual(contact.message, 'Test message from anonymous user')
        
        # Verify Conversation record
        conversation = Conversation.objects.latest('created_at')
        self.assertEqual(conversation.subject, 'Test Subject')
        
        # Verify Message record
        message = Message.objects.latest('created_at')
        self.assertEqual(message.conversation, conversation)
        self.assertEqual(message.role, 'parent')
        self.assertEqual(message.body, 'Test message from anonymous user')
