from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from accounts.models import User
from programs.models import ProgramType, ProgramInstance, Registration, Child, Role
from communications.models import Contact

User = get_user_model()

class AdminInterfaceTestCase(TestCase):
    def setUp(self):
        # Create admin user
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User'
        )
        
        # Create admin group and add user to it
        admin_group, created = Group.objects.get_or_create(name='Admin')
        self.admin_user.groups.add(admin_group)
        
        # Create test data
        self.contractor = User.objects.create_user(
            email='contractor@test.com',
            password='testpass123',
            first_name='Contractor',
            last_name='User'
        )
        contractor_group, created = Group.objects.get_or_create(name='Contractor')
        self.contractor.groups.add(contractor_group)
        
        # Create program type
        self.program_type = ProgramType.objects.create(
            name='Test Program',
            description='A test program',
            rate_per_student=100.00
        )
        
        # Create program instance
        self.program_instance = ProgramInstance.objects.create(
            program_type=self.program_type,
            instructor=self.contractor,
            location='Test Location',
            start_date='2024-01-01',
            end_date='2024-01-05',
            capacity=20,
            is_active=True
        )
        
        # Create parent and child
        self.parent = User.objects.create_user(
            email='parent@test.com',
            password='testpass123',
            first_name='Parent',
            last_name='User'
        )
        parent_group, created = Group.objects.get_or_create(name='Parent')
        self.parent.groups.add(parent_group)
        
        self.child = Child.objects.create(
            first_name='Test',
            last_name='Child',
            parent=self.parent,
            date_of_birth='2015-01-01'
        )
        
        # Create registration
        self.registration = Registration.objects.create(
            child=self.child,
            program_instance=self.program_instance,
            status='pending'
        )
        
        # Create contact
        self.contact = Contact.objects.create(
            parent_name='Test Contact',
            email='contact@test.com',
            message='Test message',
            interest='general',
            status='new'
        )
        
        self.client = Client()
    
    def test_admin_dashboard_access(self):
        """Test that admin users can access the admin dashboard."""
        self.client.login(email='admin@test.com', password='testpass123')
        response = self.client.get(reverse('admin_interface:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Dashboard')
    
    def test_user_management_access(self):
        """Test that admin users can access user management."""
        self.client.login(email='admin@test.com', password='testpass123')
        response = self.client.get(reverse('admin_interface:user_management'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User Management')
    
    def test_contact_management_access(self):
        """Test that admin users can access contact management."""
        self.client.login(email='admin@test.com', password='testpass123')
        response = self.client.get(reverse('admin_interface:contact_management'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Contact Management')
    
    def test_program_instance_management_access(self):
        """Test that admin users can access program instance management."""
        self.client.login(email='admin@test.com', password='testpass123')
        response = self.client.get(reverse('admin_interface:program_instance_management'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Program Instance Management')
    
    def test_registration_management_access(self):
        """Test that admin users can access registration management."""
        self.client.login(email='admin@test.com', password='testpass123')
        response = self.client.get(reverse('admin_interface:registration_management'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Registration Management')
    
    def test_non_admin_access_denied(self):
        """Test that non-admin users cannot access admin interface."""
        self.client.login(email='parent@test.com', password='testpass123')
        response = self.client.get(reverse('admin_interface:dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect instead of 403
    
    def test_contact_status_update(self):
        """Test updating contact status via AJAX."""
        self.client.login(email='admin@test.com', password='testpass123')
        
        # Get CSRF token
        response = self.client.get(reverse('admin_interface:dashboard'))
        csrf_token = response.cookies['csrftoken'].value
        
        response = self.client.post(
            reverse('admin_interface:update_contact_status', args=[self.contact.id]),
            data='status=completed',
            content_type='application/x-www-form-urlencoded',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        self.assertEqual(response.status_code, 200)
        
        # Check that the contact status was updated
        self.contact.refresh_from_db()
        self.assertEqual(self.contact.status, 'completed')
    
    def test_program_instance_status_toggle(self):
        """Test toggling program instance status via AJAX."""
        self.client.login(email='admin@test.com', password='testpass123')
        
        # Get CSRF token
        response = self.client.get(reverse('admin_interface:dashboard'))
        csrf_token = response.cookies['csrftoken'].value
        
        response = self.client.post(
            reverse('admin_interface:toggle_program_instance_status', args=[self.program_instance.id]),
            {},
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        self.assertEqual(response.status_code, 200)
        
        # Check that the program instance status was toggled
        self.program_instance.refresh_from_db()
        self.assertFalse(self.program_instance.is_active)
    
    def test_registration_status_update(self):
        """Test updating registration status via AJAX."""
        self.client.login(email='admin@test.com', password='testpass123')
        
        # Get CSRF token
        response = self.client.get(reverse('admin_interface:dashboard'))
        csrf_token = response.cookies['csrftoken'].value
        
        response = self.client.post(
            reverse('admin_interface:update_registration_status', args=[self.registration.id]),
            data='status=approved',
            content_type='application/x-www-form-urlencoded',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        self.assertEqual(response.status_code, 200)
        
        # Check that the registration status was updated
        self.registration.refresh_from_db()
        self.assertEqual(self.registration.status, 'approved')
    
    def test_user_status_toggle(self):
        """Test toggling user status via AJAX."""
        self.client.login(email='admin@test.com', password='testpass123')
        
        # Get CSRF token
        response = self.client.get(reverse('admin_interface:dashboard'))
        csrf_token = response.cookies['csrftoken'].value
        
        response = self.client.post(
            reverse('admin_interface:toggle_user_status', args=[self.parent.id]),
            {},
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        self.assertEqual(response.status_code, 200)
        
        # Check that the user status was toggled
        self.parent.refresh_from_db()
        self.assertFalse(self.parent.is_active) 