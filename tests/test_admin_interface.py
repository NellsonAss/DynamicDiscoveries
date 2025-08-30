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
            description='A test program'
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
        # Create instance and registration for AJAX tests
        from programs.models import ProgramBuildout, ProgramInstance
        buildout = ProgramBuildout.objects.create(
            program_type=self.program_type,
            title='BO',
            num_facilitators=1,
            num_new_facilitators=0,
            students_per_program=10,
            sessions_per_program=5,
            rate_per_student=10.0,
        )
        from django.utils import timezone
        from datetime import timedelta
        self.program_instance = ProgramInstance.objects.create(
            buildout=buildout,
            title='Inst',
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=1),
            location='X',
            capacity=10,
        )
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
    
    def test_responsibility_edit_functionality(self):
        """Test that admin users can edit responsibilities."""
        from programs.models import Responsibility
        
        # Create a test role and responsibility
        role = Role.objects.create(
            title='Test Role',
            description='A test role'
        )
        
        responsibility = Responsibility.objects.create(
            role=role,
            name='Test Responsibility',
            description='A test responsibility',
            frequency_type='PER_WORKSHOP',
            default_hours=2.50
        )
        
        self.client.login(email='admin@test.com', password='testpass123')
        
        # Test GET request to edit form
        response = self.client.get(reverse('admin_interface:responsibility_edit', args=[responsibility.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Edit Responsibility: Test Responsibility')
        self.assertContains(response, 'Test Responsibility')
        self.assertContains(response, '2.50')
        
        # Test POST request to update responsibility
        response = self.client.post(reverse('admin_interface:responsibility_edit', args=[responsibility.id]), {
            'name': 'Updated Responsibility',
            'description': 'An updated description',
            'frequency_type': 'PER_SESSION',
            'default_hours': '3.75'
        })
        
        # Debug: print response content if it's not a redirect
        if response.status_code != 302:
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.content.decode()}")
        
        # Should redirect to role manage responsibilities
        self.assertRedirects(response, reverse('admin_interface:role_manage_responsibilities', args=[role.id]))
        
        # Check that the responsibility was updated
        responsibility.refresh_from_db()
        self.assertEqual(responsibility.name, 'Updated Responsibility')
        self.assertEqual(responsibility.description, 'An updated description')
        self.assertEqual(responsibility.frequency_type, 'PER_SESSION')
        self.assertEqual(float(responsibility.default_hours), 3.75)
    
    def test_responsibility_delete_functionality(self):
        """Test that admin users can delete responsibilities."""
        from programs.models import Responsibility
        
        # Create a test role and responsibility
        role = Role.objects.create(
            title='Test Role',
            description='A test role'
        )
        
        responsibility = Responsibility.objects.create(
            role=role,
            name='Test Responsibility',
            description='A test responsibility',
            frequency_type='PER_WORKSHOP',
            default_hours=2.50
        )
        
        self.client.login(email='admin@test.com', password='testpass123')
        
        # Test GET request to delete confirmation page
        response = self.client.get(reverse('admin_interface:responsibility_delete', args=[responsibility.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Delete Responsibility')
        self.assertContains(response, 'Test Responsibility')
        
        # Test POST request to delete responsibility
        response = self.client.post(reverse('admin_interface:responsibility_delete', args=[responsibility.id]))
        
        # Should redirect to role manage responsibilities
        self.assertRedirects(response, reverse('admin_interface:role_manage_responsibilities', args=[role.id]))
        
        # Check that the responsibility was deleted
        self.assertFalse(Responsibility.objects.filter(id=responsibility.id).exists())
    
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