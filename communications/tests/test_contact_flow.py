from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.cache import cache
from django.test.utils import override_settings
from unittest.mock import patch, MagicMock

from communications.models import Conversation, Message
from communications.forms import ContactComposeForm, ContactQuickForm, MessageReplyForm

User = get_user_model()


class ContactFlowTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        # Clear cache for rate limiting tests
        cache.clear()
        
        # Create test user with Parent role
        from django.contrib.auth.models import Group
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        # Add user to Parent group
        parent_group, created = Group.objects.get_or_create(name='Parent')
        self.user.groups.add(parent_group)
        
        # Create another user for existing email tests
        self.existing_user = User.objects.create_user(
            email='existing@example.com',
            password='testpass123'
        )

    def test_contact_entry_view_authenticated(self):
        """Test contact entry view for authenticated users shows compose form."""
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.get(reverse('communications:contact_entry'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Signed in as test@example.com')
        self.assertContains(response, 'Send Message')

    def test_contact_entry_view_anonymous(self):
        """Test contact entry view for anonymous users shows quick create form."""
        response = self.client.get(reverse('communications:contact_entry'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Quick Start')
        self.assertContains(response, 'Create Account & Send Message')

    @patch('communications.views.AzureEmailService')
    def test_authenticated_compose_flow(self, mock_email_service):
        """Test authenticated user compose flow creates conversation and message."""
        # Mock email service
        mock_email_instance = MagicMock()
        mock_email_service.return_value = mock_email_instance
        
        self.client.login(email='test@example.com', password='testpass123')
        
        form_data = {
            'subject': 'Test Subject',
            'message': 'Test message body',
            'honeypot': ''  # Empty honeypot
        }
        
        response = self.client.post(reverse('communications:contact_compose'), form_data)
        
        # Check redirect
        self.assertEqual(response.status_code, 302)
        self.assertIn('/programs/parent/dashboard/?show=messages', response.url)
        
        # Check conversation created
        conversation = Conversation.objects.get(owner=self.user)
        self.assertEqual(conversation.subject, 'Test Subject')
        self.assertEqual(conversation.status, 'open')
        
        # Check message created
        message = conversation.messages.first()
        self.assertEqual(message.body, 'Test message body')
        self.assertEqual(message.role, 'parent')
        self.assertEqual(message.author, self.user)
        
        # Check emails were attempted to be sent
        self.assertEqual(mock_email_instance.send_templated_email.call_count, 2)

    def test_honeypot_protection(self):
        """Test honeypot field blocks bot submissions."""
        self.client.login(email='test@example.com', password='testpass123')
        
        form_data = {
            'subject': 'Test Subject',
            'message': 'Test message body',
            'honeypot': 'bot_content'  # Non-empty honeypot
        }
        
        response = self.client.post(reverse('communications:contact_compose'), form_data)
        
        # Should redirect back to form
        self.assertEqual(response.status_code, 302)
        
        # No conversation should be created
        self.assertEqual(Conversation.objects.count(), 0)

    @patch('communications.views.AzureEmailService')
    def test_quick_create_new_user(self, mock_email_service):
        """Test quick create flow for new email creates user, logs in, and creates conversation."""
        mock_email_instance = MagicMock()
        mock_email_service.return_value = mock_email_instance
        
        form_data = {
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'subject': 'Quick Test Subject',
            'message': 'Quick test message',
            'honeypot': ''
        }
        
        response = self.client.post(reverse('communications:contact_quick'), form_data)
        
        # Check redirect
        self.assertEqual(response.status_code, 302)
        self.assertIn('/programs/parent/dashboard/?show=messages', response.url)
        
        # Check user created
        new_user = User.objects.get(email='newuser@example.com')
        self.assertEqual(new_user.first_name, 'New')
        self.assertEqual(new_user.last_name, 'User')
        self.assertFalse(new_user.has_usable_password())
        
        # Check user is logged in
        self.assertIn('_auth_user_id', self.client.session)
        
        # Check conversation created
        conversation = Conversation.objects.get(owner=new_user)
        self.assertEqual(conversation.subject, 'Quick Test Subject')
        
        # Check message created
        message = conversation.messages.first()
        self.assertEqual(message.body, 'Quick test message')
        self.assertEqual(message.role, 'parent')

    def test_quick_create_existing_email(self):
        """Test quick create flow with existing email shows error and doesn't create user."""
        form_data = {
            'email': 'existing@example.com',  # This email already exists
            'first_name': 'Should',
            'last_name': 'Fail',
            'subject': 'Test Subject',
            'message': 'Test message',
            'honeypot': ''
        }
        
        response = self.client.post(reverse('communications:contact_quick'), form_data)
        
        # Should render the entry page with error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Account exists. Please sign in.')
        self.assertContains(response, 'Sign In')
        
        # No new user should be created
        self.assertEqual(User.objects.filter(email='existing@example.com').count(), 1)
        
        # No conversation should be created
        self.assertEqual(Conversation.objects.count(), 0)

    def test_parent_messages_list_view(self):
        """Test parent messages list view shows user's conversations."""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Create test conversations
        conv1 = Conversation.objects.create(
            owner=self.user,
            subject='First Conversation',
            status='open'
        )
        conv2 = Conversation.objects.create(
            owner=self.user,
            subject='Second Conversation',
            status='closed'
        )
        
        # Create messages
        Message.objects.create(
            conversation=conv1,
            author=self.user,
            role='parent',
            body='First message'
        )
        Message.objects.create(
            conversation=conv2,
            author=self.user,
            role='parent',
            body='Second message'
        )
        
        response = self.client.get(reverse('communications:parent_messages_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'First Conversation')
        self.assertContains(response, 'Second Conversation')
        self.assertContains(response, 'Open')
        self.assertContains(response, 'Closed')

    def test_parent_messages_detail_view(self):
        """Test parent messages detail view shows conversation thread."""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Create test conversation
        conversation = Conversation.objects.create(
            owner=self.user,
            subject='Test Conversation',
            status='open'
        )
        
        # Create messages
        Message.objects.create(
            conversation=conversation,
            author=self.user,
            role='parent',
            body='Parent message'
        )
        Message.objects.create(
            conversation=conversation,
            author=None,  # Staff message
            role='staff',
            body='Staff response'
        )
        
        response = self.client.get(
            reverse('communications:parent_messages_detail', kwargs={'pk': conversation.pk})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Conversation')
        self.assertContains(response, 'Parent message')
        self.assertContains(response, 'Staff response')
        self.assertContains(response, 'You')  # Parent message indicator
        self.assertContains(response, 'Dynamic Discoveries Staff')  # Staff message indicator

    def test_parent_messages_detail_permission(self):
        """Test parent can only view their own conversations."""
        # Create another user and their conversation
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )
        other_conversation = Conversation.objects.create(
            owner=other_user,
            subject='Other User Conversation'
        )
        
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.get(
            reverse('communications:parent_messages_detail', kwargs={'pk': other_conversation.pk})
        )
        
        # Should return 404 since user doesn't own this conversation
        self.assertEqual(response.status_code, 404)

    def test_parent_messages_reply(self):
        """Test parent can reply to conversations."""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Create test conversation
        conversation = Conversation.objects.create(
            owner=self.user,
            subject='Test Conversation',
            status='closed'  # Test that reply reopens closed conversations
        )
        
        form_data = {
            'body': 'This is my reply',
            'honeypot': ''
        }
        
        response = self.client.post(
            reverse('communications:parent_messages_reply', kwargs={'pk': conversation.pk}),
            form_data
        )
        
        # Should redirect back to detail view
        self.assertEqual(response.status_code, 302)
        
        # Check reply message created
        reply = conversation.messages.last()
        self.assertEqual(reply.body, 'This is my reply')
        self.assertEqual(reply.role, 'parent')
        self.assertEqual(reply.author, self.user)
        
        # Check conversation status reopened
        conversation.refresh_from_db()
        self.assertEqual(conversation.status, 'open')

    @override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
    def test_rate_limiting(self):
        """Test rate limiting prevents too many requests."""
        self.client.login(email='test@example.com', password='testpass123')
        
        form_data = {
            'subject': 'Test Subject',
            'message': 'Test message',
            'honeypot': ''
        }
        
        # Make requests up to the limit (5 by default)
        for i in range(5):
            response = self.client.post(reverse('communications:contact_compose'), form_data)
            self.assertEqual(response.status_code, 302)
        
        # 6th request should be rate limited
        response = self.client.post(reverse('communications:contact_compose'), form_data)
        self.assertEqual(response.status_code, 302)
        
        # Check for rate limit message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Too many attempts' in str(m) for m in messages))

    def test_form_validation(self):
        """Test form validation works correctly."""
        # Test ContactComposeForm
        form = ContactComposeForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('subject', form.errors)
        self.assertIn('message', form.errors)
        
        # Test ContactQuickForm
        form = ContactQuickForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertIn('subject', form.errors)
        self.assertIn('message', form.errors)
        
        # Test MessageReplyForm
        form = MessageReplyForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('body', form.errors)

    def test_parent_dashboard_messages_section(self):
        """Test parent dashboard includes messages section with recent conversations."""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Create test conversation
        conversation = Conversation.objects.create(
            owner=self.user,
            subject='Dashboard Test Conversation',
            status='open'
        )
        Message.objects.create(
            conversation=conversation,
            author=self.user,
            role='parent',
            body='Dashboard test message'
        )
        
        response = self.client.get(reverse('programs:parent_dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your Messages')
        self.assertContains(response, 'Dashboard Test Conversation')
        self.assertContains(response, 'New Message')
        self.assertContains(response, 'View All')

    def test_parent_dashboard_no_messages(self):
        """Test parent dashboard shows empty state when no messages exist."""
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.get(reverse('programs:parent_dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No messages yet')
        self.assertContains(response, 'Send Your First Message')

    def test_contact_entry_htmx_request(self):
        """Test HTMX requests return partial templates."""
        headers = {'HTTP_HX_REQUEST': 'true'}
        
        # Test authenticated user
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('communications:contact_entry'), **headers)
        
        self.assertEqual(response.status_code, 200)
        # Should not contain full page structure for HTMX requests
        self.assertNotContains(response, '{% extends "base.html" %}')
        self.assertContains(response, 'Signed in as')
        
        # Test anonymous user
        self.client.logout()
        response = self.client.get(reverse('communications:contact_entry'), **headers)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Quick Start')
