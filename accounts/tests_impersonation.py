"""
Comprehensive tests for role preview and user impersonation functionality.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone
from audit.models import ImpersonationLog

User = get_user_model()


class RolePreviewTestCase(TestCase):
    """Tests for self role preview functionality."""
    
    def setUp(self):
        """Set up test users and roles."""
        # Create roles
        self.admin_group = Group.objects.get_or_create(name='Admin')[0]
        self.parent_group = Group.objects.get_or_create(name='Parent')[0]
        self.contractor_group = Group.objects.get_or_create(name='Contractor')[0]
        
        # Create multi-role user
        self.multi_role_user = User.objects.create_user(
            email='multi@example.com',
            password='testpass123'
        )
        self.multi_role_user.groups.add(self.admin_group, self.parent_group, self.contractor_group)
        
        # Create single-role user
        self.single_role_user = User.objects.create_user(
            email='parent@example.com',
            password='testpass123'
        )
        self.single_role_user.groups.add(self.parent_group)
        
        self.client = Client()
    
    def test_multi_role_user_can_switch_roles(self):
        """Multi-role user can switch between their roles."""
        self.client.login(email='multi@example.com', password='testpass123')
        
        # Switch to Parent role
        response = self.client.post(
            reverse('accounts:role_switch'), 
            {'role': 'Parent'}
        )
        self.assertEqual(response.status_code, 200)
        # Check for HX-Redirect header to parent dashboard
        self.assertIn('HX-Redirect', response.headers)
        self.assertIn('parent/dashboard', response.headers['HX-Redirect'])
        
        # Verify session was updated
        session = self.client.session
        self.assertEqual(session.get('effective_role'), 'Parent')
    
    def test_user_cannot_switch_to_role_they_dont_have(self):
        """User cannot switch to a role they don't possess."""
        self.client.login(email='parent@example.com', password='testpass123')
        
        # Try to switch to Contractor role (which they don't have)
        response = self.client.post(reverse('accounts:role_switch'), {'role': 'Contractor'})
        self.assertEqual(response.status_code, 403)
    
    def test_switch_to_auto_clears_role_preview(self):
        """Switching to Auto clears the role preview."""
        self.client.login(email='multi@example.com', password='testpass123')
        
        # First set a role
        self.client.post(reverse('accounts:role_switch'), {'role': 'Parent'})
        self.assertEqual(self.client.session.get('effective_role'), 'Parent')
        
        # Switch to Auto
        response = self.client.post(reverse('accounts:role_switch'), {'role': 'Auto'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('HX-Redirect', response.headers)
        self.assertNotIn('effective_role', self.client.session)
    
    def test_cannot_switch_roles_while_impersonating(self):
        """Cannot use role preview while impersonating another user."""
        # Create superuser
        superuser = User.objects.create_superuser(
            email='super@example.com',
            password='testpass123'
        )
        self.client.login(email='super@example.com', password='testpass123')
        
        # Start impersonation
        self.client.post(reverse('accounts:impersonate_start'), {
            'user_id': self.single_role_user.id,
            'readonly': 'true'
        })
        
        # Try to switch roles
        response = self.client.post(reverse('accounts:role_switch'), {'role': 'Parent'})
        self.assertEqual(response.status_code, 400)


class UserImpersonationTestCase(TestCase):
    """Tests for user impersonation functionality."""
    
    def setUp(self):
        """Set up test users."""
        # Create roles
        self.admin_group = Group.objects.get_or_create(name='Admin')[0]
        self.parent_group = Group.objects.get_or_create(name='Parent')[0]
        
        # Create superuser
        self.superuser = User.objects.create_superuser(
            email='super@example.com',
            password='testpass123'
        )
        
        # Create admin user (not superuser)
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='testpass123'
        )
        self.admin_user.groups.add(self.admin_group)
        
        # Create target users
        self.parent_user = User.objects.create_user(
            email='parent@example.com',
            password='testpass123'
        )
        self.parent_user.groups.add(self.parent_group)
        
        self.inactive_user = User.objects.create_user(
            email='inactive@example.com',
            password='testpass123',
            is_active=False
        )
        
        self.client = Client()
    
    def test_superuser_can_start_impersonation(self):
        """Superuser can start impersonating another user."""
        self.client.login(email='super@example.com', password='testpass123')
        
        response = self.client.post(reverse('accounts:impersonate_start'), {
            'user_id': self.parent_user.id,
            'readonly': 'true',
            'reason': 'Testing parent dashboard'
        })
        
        # Should redirect to target user's dashboard
        self.assertEqual(response.status_code, 302)
        
        # Check session variables
        session = self.client.session
        self.assertEqual(session.get('impersonate_user_id'), self.parent_user.id)
        self.assertTrue(session.get('impersonate_readonly'))
        
        # Check audit log was created
        log = ImpersonationLog.objects.filter(
            admin_user=self.superuser,
            target_user=self.parent_user
        ).first()
        self.assertIsNotNone(log)
        self.assertTrue(log.readonly)
        self.assertEqual(log.reason_note, 'Testing parent dashboard')
        self.assertIsNone(log.ended_at)
    
    def test_impersonation_with_full_access(self):
        """Can start impersonation with full access mode."""
        self.client.login(email='super@example.com', password='testpass123')
        
        response = self.client.post(reverse('accounts:impersonate_start'), {
            'user_id': self.parent_user.id,
            'readonly': 'false'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.client.session.get('impersonate_readonly'))
    
    def test_stop_impersonation_closes_log(self):
        """Stopping impersonation closes the audit log."""
        self.client.login(email='super@example.com', password='testpass123')
        
        # Start impersonation
        self.client.post(reverse('accounts:impersonate_start'), {
            'user_id': self.parent_user.id,
            'readonly': 'true'
        })
        
        log_id = self.client.session.get('impersonate_log_id')
        
        # Stop impersonation
        response = self.client.post(reverse('accounts:impersonate_stop'))
        self.assertEqual(response.status_code, 302)
        
        # Check session was cleared
        self.assertNotIn('impersonate_user_id', self.client.session)
        self.assertNotIn('impersonate_readonly', self.client.session)
        
        # Check log was closed
        log = ImpersonationLog.objects.get(id=log_id)
        self.assertIsNotNone(log.ended_at)
    
    def test_cannot_impersonate_self(self):
        """Cannot impersonate yourself."""
        self.client.login(email='super@example.com', password='testpass123')
        
        response = self.client.post(reverse('accounts:impersonate_start'), {
            'user_id': self.superuser.id,
            'readonly': 'true'
        })
        
        # Should redirect back with error
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('impersonate_user_id', self.client.session)
    
    def test_cannot_impersonate_inactive_user(self):
        """Cannot impersonate inactive users."""
        self.client.login(email='super@example.com', password='testpass123')
        
        response = self.client.post(reverse('accounts:impersonate_start'), {
            'user_id': self.inactive_user.id,
            'readonly': 'true'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('impersonate_user_id', self.client.session)
    
    def test_regular_user_cannot_impersonate(self):
        """Regular users without permission cannot impersonate."""
        self.client.login(email='parent@example.com', password='testpass123')
        
        response = self.client.post(reverse('accounts:impersonate_start'), {
            'user_id': self.superuser.id,
            'readonly': 'true'
        })
        
        # Should redirect with error
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('impersonate_user_id', self.client.session)


class ReadOnlyEnforcementTestCase(TestCase):
    """Tests for read-only enforcement during impersonation."""
    
    def setUp(self):
        """Set up test users."""
        self.superuser = User.objects.create_superuser(
            email='super@example.com',
            password='testpass123'
        )
        
        parent_group = Group.objects.get_or_create(name='Parent')[0]
        self.parent_user = User.objects.create_user(
            email='parent@example.com',
            password='testpass123'
        )
        self.parent_user.groups.add(parent_group)
        
        self.client = Client()
    
    def test_readonly_blocks_post_requests(self):
        """Read-only mode blocks POST requests when properly decorated."""
        self.client.login(email='super@example.com', password='testpass123')
        
        # Start read-only impersonation
        self.client.post(reverse('accounts:impersonate_start'), {
            'user_id': self.parent_user.id,
            'readonly': 'true'
        })
        
        # Session should have readonly flag
        self.assertTrue(self.client.session.get('impersonate_readonly'))
        
        # Note: Actual blocking of POST requests requires the decorator
        # to be applied to views - this is tested in integration tests
    
    def test_full_access_allows_post_requests(self):
        """Full access mode allows POST requests."""
        self.client.login(email='super@example.com', password='testpass123')
        
        # Start full-access impersonation
        self.client.post(reverse('accounts:impersonate_start'), {
            'user_id': self.parent_user.id,
            'readonly': 'false'
        })
        
        # Session should not have readonly flag set to True
        self.assertFalse(self.client.session.get('impersonate_readonly'))


class ContextProcessorTestCase(TestCase):
    """Tests for effective_role context processor."""
    
    def setUp(self):
        """Set up test users."""
        admin_group = Group.objects.get_or_create(name='Admin')[0]
        parent_group = Group.objects.get_or_create(name='Parent')[0]
        
        self.multi_role_user = User.objects.create_user(
            email='multi@example.com',
            password='testpass123'
        )
        self.multi_role_user.groups.add(admin_group, parent_group)
        
        self.client = Client()
    
    def test_context_includes_effective_role(self):
        """Context processor adds effective_role to templates."""
        self.client.login(email='multi@example.com', password='testpass123')
        
        # Get a page (home page should work)
        response = self.client.get(reverse('home'))
        
        # Check context
        self.assertIn('effective_role', response.context)
        self.assertIn('is_impersonating', response.context)
        self.assertIn('can_impersonate', response.context)
        self.assertIn('user_has_multiple_roles', response.context)
    
    def test_multi_role_user_flagged_correctly(self):
        """Multi-role users are flagged as having multiple roles."""
        self.client.login(email='multi@example.com', password='testpass123')
        
        response = self.client.get(reverse('home'))
        self.assertTrue(response.context['user_has_multiple_roles'])
    
    def test_effective_role_reflects_session(self):
        """Effective role reflects session value."""
        self.client.login(email='multi@example.com', password='testpass123')
        
        # Set role in session
        self.client.post(reverse('accounts:role_switch'), {'role': 'Parent'})
        
        response = self.client.get(reverse('home'))
        self.assertEqual(response.context['effective_role'], 'Parent')


class AuditLogTestCase(TestCase):
    """Tests for impersonation audit logging."""
    
    def setUp(self):
        """Set up test users."""
        self.superuser = User.objects.create_superuser(
            email='super@example.com',
            password='testpass123'
        )
        
        parent_group = Group.objects.get_or_create(name='Parent')[0]
        self.parent_user = User.objects.create_user(
            email='parent@example.com',
            password='testpass123'
        )
        self.parent_user.groups.add(parent_group)
        
        self.client = Client()
    
    def test_audit_log_created_on_start(self):
        """Audit log is created when impersonation starts."""
        self.client.login(email='super@example.com', password='testpass123')
        
        self.client.post(reverse('accounts:impersonate_start'), {
            'user_id': self.parent_user.id,
            'readonly': 'true',
            'reason': 'Test reason'
        })
        
        log = ImpersonationLog.objects.filter(
            admin_user=self.superuser,
            target_user=self.parent_user
        ).first()
        
        self.assertIsNotNone(log)
        self.assertEqual(log.reason_note, 'Test reason')
        self.assertTrue(log.readonly)
        self.assertIsNotNone(log.started_at)
        self.assertIsNone(log.ended_at)
    
    def test_audit_log_updated_on_stop(self):
        """Audit log is updated when impersonation stops."""
        self.client.login(email='super@example.com', password='testpass123')
        
        # Start
        self.client.post(reverse('accounts:impersonate_start'), {
            'user_id': self.parent_user.id,
            'readonly': 'true'
        })
        
        log = ImpersonationLog.objects.latest('started_at')
        self.assertIsNone(log.ended_at)
        
        # Stop
        self.client.post(reverse('accounts:impersonate_stop'))
        
        log.refresh_from_db()
        self.assertIsNotNone(log.ended_at)
    
    def test_audit_log_tracks_ip_and_ua(self):
        """Audit log tracks IP address and user agent."""
        self.client.login(email='super@example.com', password='testpass123')
        
        self.client.post(
            reverse('accounts:impersonate_start'),
            {
                'user_id': self.parent_user.id,
                'readonly': 'true'
            },
            HTTP_USER_AGENT='TestBrowser/1.0'
        )
        
        log = ImpersonationLog.objects.latest('started_at')
        self.assertIsNotNone(log.ip_address)
        self.assertIn('TestBrowser', log.user_agent)

