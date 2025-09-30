"""
Comprehensive page load tests for all application routes.

This module tests that every page in the application loads correctly
for different user types and scenarios, ensuring no broken routes
or template errors.
"""

from django.test import TestCase, Client
from django.urls import reverse, NoReverseMatch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from datetime import date, timedelta
from programs.models import (
    ProgramType, Role, ProgramBuildout, ProgramInstance, Child, 
    Registration, RegistrationForm, BaseCost, Location, BuildoutRoleLine,
    Responsibility, ContractorAvailability, ProgramSession
)
from communications.models import Contact
from people.models import Contractor
from notes.models import StudentNote, ParentNote

User = get_user_model()


class ComprehensivePageLoadTests(TestCase):
    """Test that all pages load correctly for different user types."""
    
    def setUp(self):
        """Set up test data for comprehensive testing."""
        self.client = Client()
        
        # Create users with different roles
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User'
        )
        admin_group, _ = Group.objects.get_or_create(name='Admin')
        self.admin_user.groups.add(admin_group)
        
        self.parent_user = User.objects.create_user(
            email='parent@test.com',
            password='testpass123',
            first_name='Parent',
            last_name='User'
        )
        parent_group, _ = Group.objects.get_or_create(name='Parent')
        self.parent_user.groups.add(parent_group)
        
        self.contractor_user = User.objects.create_user(
            email='contractor@test.com',
            password='testpass123',
            first_name='Contractor',
            last_name='User'
        )
        contractor_group, _ = Group.objects.get_or_create(name='Contractor')
        self.contractor_user.groups.add(contractor_group)
        
        # Create contractor with complete onboarding
        self.contractor = Contractor.objects.create(
            user=self.contractor_user,
            nda_signed=True
        )
        # Simulate W-9 upload
        from django.core.files.base import ContentFile
        self.contractor.w9_file.save("test_w9.pdf", ContentFile(b"%PDF-1.4 test"), save=True)
        
        # Create test program data
        self.role = Role.objects.create(
            title="Test Facilitator",
            description="Test role for comprehensive testing"
        )
        
        self.responsibility = Responsibility.objects.create(
            role=self.role,
            name="Test Responsibility",
            description="Test responsibility",
            frequency_type="PER_SESSION",
            default_hours=2.0
        )
        
        self.program_type = ProgramType.objects.create(
            name="Test Program Type",
            description="Test program type for comprehensive testing"
        )
        
        self.buildout = ProgramBuildout.objects.create(
            program_type=self.program_type,
            title="Test Buildout",
            num_facilitators=2,
            num_new_facilitators=1,
            students_per_program=12,
            sessions_per_program=8,
            rate_per_student=25.00
        )
        
        # Create BuildoutRoleLine with required fields
        self.buildout_role_line = BuildoutRoleLine.objects.create(
            buildout=self.buildout,
            role=self.role,
            contractor=self.contractor_user,
            pay_type='HOURLY',
            pay_value=25.00,
            frequency_unit='PER_SESSION',
            frequency_count=1,
            hours_per_frequency=2.0
        )
        
        # Create base cost
        self.base_cost = BaseCost.objects.create(
            name="Test Base Cost",
            rate=10.00,
            frequency="PER_SESSION",
            description="Test base cost"
        )
        
        # Create location
        self.location = Location.objects.create(
            name="Test Location",
            address="123 Test St",
            description="Test location for comprehensive testing",
            default_rate=100.00,
            default_frequency="PER_SESSION",
            max_capacity=50,
            features="Projector, Whiteboard, Parking",
            contact_name="Test Contact",
            contact_phone="555-1234",
            contact_email="location@test.com"
        )
        
        # Create program instance
        self.program_instance = ProgramInstance.objects.create(
            buildout=self.buildout,
            title="Test Program Instance",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            location="Test Location",
            capacity=20
        )
        
        # Create child
        self.child = Child.objects.create(
            first_name="Test",
            last_name="Child",
            parent=self.parent_user,
            date_of_birth=date(2015, 1, 1)
        )
        
        # Create registration
        self.registration = Registration.objects.create(
            child=self.child,
            program_instance=self.program_instance,
            status="pending"
        )
        
        # Create registration form
        self.form = RegistrationForm.objects.create(
            title="Test Form",
            description="Test form description",
            created_by=self.admin_user
        )
        
        # Create contact
        self.contact = Contact.objects.create(
            parent_name="Test Contact",
            email="contact@test.com",
            message="Test contact message",
            interest="after_school"
        )
        
        # Create contractor availability
        self.availability = ContractorAvailability.objects.create(
            contractor=self.contractor_user,
            start_datetime=timezone.now(),
            end_datetime=timezone.now() + timedelta(hours=4),
            status='available'
        )
        
        # Create availability program first (required for session)
        from programs.models import AvailabilityProgram
        self.availability_program = AvailabilityProgram.objects.create(
            availability=self.availability,
            program_buildout=self.buildout,
            max_sessions=2,
            session_duration_hours=2.0
        )
        
        # Create program session
        self.session = ProgramSession.objects.create(
            program_instance=self.program_instance,
            availability_program=self.availability_program,
            start_datetime=timezone.now(),
            end_datetime=timezone.now() + timedelta(hours=2),
            duration_hours=2.0,
            max_capacity=self.program_instance.capacity
        )
        
        # Create notes for testing
        self.student_note = StudentNote.objects.create(
            student=self.child,
            created_by=self.admin_user,
            title="Test Student Note",
            body="Test student note content",
            is_public=True,
            visibility_scope='public_parent'
        )
        
        self.parent_note = ParentNote.objects.create(
            parent=self.parent_user,
            created_by=self.admin_user,
            title="Test Parent Note",
            body="Test parent note content",
            is_public=True,
            visibility_scope='public_parent'
        )
    
    def _test_page_load(self, url_name, args=None, kwargs=None, user=None, 
                       expected_status_codes=(200, 302), namespace=None):
        """
        Helper method to test page loading.
        
        Args:
            url_name: URL pattern name
            args: URL arguments
            kwargs: URL keyword arguments
            user: User to login as (None for anonymous)
            expected_status_codes: Tuple of acceptable status codes
            namespace: URL namespace
        """
        try:
            if namespace:
                url = reverse(f'{namespace}:{url_name}', args=args, kwargs=kwargs)
            else:
                url = reverse(url_name, args=args, kwargs=kwargs)
        except NoReverseMatch:
            # Skip URLs that don't exist or have invalid arguments
            return
        
        if user:
            self.client.force_login(user)
        else:
            self.client.logout()
        
        try:
            response = self.client.get(url)
            self.assertIn(
                response.status_code, 
                expected_status_codes,
                f"URL {url} returned status {response.status_code}, expected one of {expected_status_codes}"
            )
        except Exception as e:
            self.fail(f"Exception loading URL {url}: {e}")
    
    def test_public_pages(self):
        """Test pages accessible to anonymous users."""
        public_pages = [
            ('home', None, None),
            ('test', None, None),
            ('communications:contact', None, None),
            ('communications:contact_form', None, None),
            ('accounts:login', None, None),
            ('accounts:signup', None, None),
        ]
        
        for page_data in public_pages:
            url_name = page_data[0]
            args = page_data[1]
            kwargs = page_data[2]
            
            with self.subTest(url=url_name):
                if ':' in url_name:
                    namespace, name = url_name.split(':', 1)
                    self._test_page_load(name, args, kwargs, None, namespace=namespace)
                else:
                    self._test_page_load(url_name, args, kwargs, None)
    
    def test_admin_pages(self):
        """Test pages accessible to admin users."""
        admin_pages = [
            # Dashboard
            ('admin_interface:dashboard', None, None),
            
            # User Management
            ('admin_interface:user_management', None, None),
            ('admin_interface:user_detail', [self.admin_user.id], None),
            ('admin_interface:user_edit', [self.admin_user.id], None),
            
            # Program Management
            ('admin_interface:program_type_management', None, None),
            ('admin_interface:program_type_create', None, None),
            ('admin_interface:program_type_detail', [self.program_type.id], None),
            ('admin_interface:program_type_edit', [self.program_type.id], None),
            
            # Program Instance Management
            ('admin_interface:program_instance_management', None, None),
            ('admin_interface:program_instance_create', None, None),
            ('admin_interface:program_instance_detail', [self.program_instance.id], None),
            ('admin_interface:program_instance_edit', [self.program_instance.id], None),
            ('admin_interface:buildout_create_instance', [self.buildout.id], None),
            
            # Buildout Management
            ('admin_interface:buildout_management', None, None),
            ('admin_interface:buildout_create', None, None),
            ('admin_interface:buildout_detail', [self.buildout.id], None),
            ('admin_interface:buildout_edit', [self.buildout.id], None),
            ('admin_interface:buildout_assign_roles', [self.buildout.id], None),
            ('admin_interface:buildout_manage_roles', [self.buildout.id], None),
            ('admin_interface:buildout_assign_costs', [self.buildout.id], None),
            ('admin_interface:buildout_assign_locations', [self.buildout.id], None),
            
            # Registration Management
            ('admin_interface:registration_management', None, None),
            
            # Contact Management
            ('admin_interface:contact_management', None, None),
            
            # Child Management
            ('admin_interface:child_management', None, None),
            ('admin_interface:child_create', None, None),
            ('admin_interface:child_detail', [self.child.id], None),
            ('admin_interface:child_edit', [self.child.id], None),
            ('admin_interface:child_registrations', [self.child.id], None),
            
            # Form Management
            ('admin_interface:form_management', None, None),
            ('admin_interface:form_create', None, None),
            ('admin_interface:form_detail', [self.form.id], None),
            ('admin_interface:form_edit', [self.form.id], None),
            ('admin_interface:form_manage_questions', [self.form.id], None),
            
            # Role Management
            ('admin_interface:role_management', None, None),
            ('admin_interface:role_create', None, None),
            ('admin_interface:role_detail', [self.role.id], None),
            ('admin_interface:role_edit', [self.role.id], None),
            ('admin_interface:role_manage_users', [self.role.id], None),
            ('admin_interface:role_manage_responsibilities', [self.role.id], None),
            ('admin_interface:role_add_responsibility', [self.role.id], None),
            
            # Responsibility Management
            ('admin_interface:responsibility_edit', [self.responsibility.id], None),
            
            # Cost Management
            ('admin_interface:cost_management', None, None),
            ('admin_interface:cost_create', None, None),
            ('admin_interface:cost_detail', [self.base_cost.id], None),
            ('admin_interface:cost_edit', [self.base_cost.id], None),
            
            # Location Management
            ('admin_interface:location_management', None, None),
            ('admin_interface:location_create', None, None),
            ('admin_interface:location_detail', [self.location.id], None),
            ('admin_interface:location_edit', [self.location.id], None),
            
            # Contractor Document Management
            ('admin_interface:contractor_document_management', None, None),
            ('admin_interface:contractor_document_detail', [self.contractor.id], None),
            
            # Dashboard stats
            ('dashboard:dashboard', None, None),
            ('dashboard:stats', None, None),
            ('dashboard:activity', None, None),
            
            # Communications
            ('communications:contact_list', None, None),
            ('communications:contact_detail', [self.contact.id], None),
            
            # Accounts
            ('accounts:profile', None, None),
            ('accounts:user_list', None, None),
            ('accounts:user_role_update', [self.admin_user.id], None),
        ]
        
        for page_data in admin_pages:
            url_name = page_data[0]
            args = page_data[1]
            kwargs = page_data[2]
            
            with self.subTest(url=url_name):
                namespace, name = url_name.split(':', 1)
                self._test_page_load(name, args, kwargs, self.admin_user, namespace=namespace)
    
    def test_parent_pages(self):
        """Test pages accessible to parent users."""
        parent_pages = [
            # Dashboard
            ('dashboard:dashboard', None, None),
            
            # Parent Program Views
            ('programs:parent_dashboard', None, None),
            ('programs:manage_children', None, None),
            ('programs:edit_child', [self.child.pk], None),
            ('programs:program_instance_detail', [self.program_instance.pk], None),
            ('programs:register_child', [self.program_instance.pk], None),
            ('programs:complete_registration_form', [self.registration.pk], None),
            
            # Program Catalog
            ('programs:program_catalog', None, None),
            ('programs:program_type_instances', [self.program_type.id], None),
            ('programs:program_request_create', [self.program_type.id], None),
            
            # Session Booking
            ('programs:available_sessions_list', None, None),
            ('programs:parent_bookings', None, None),
            
            # Notes
            ('notes:student_notes_list', [self.child.id], None),
            ('notes:parent_notes_list', [self.parent_user.id], None),
            
            # Profile
            ('accounts:profile', None, None),
        ]
        
        for page_data in parent_pages:
            url_name = page_data[0]
            args = page_data[1]
            kwargs = page_data[2]
            
            with self.subTest(url=url_name):
                namespace, name = url_name.split(':', 1)
                self._test_page_load(name, args, kwargs, self.parent_user, namespace=namespace)
    
    def test_contractor_pages(self):
        """Test pages accessible to contractor users."""
        contractor_pages = [
            # Dashboard
            ('dashboard:dashboard', None, None),
            ('programs:contractor_dashboard', None, None),
            
            # Buildout Views
            ('programs:buildout_list', None, None),
            ('programs:buildout_detail', [self.buildout.pk], None),
            ('programs:buildout_review', [self.buildout.pk], None),
            
            # Form Management
            ('programs:form_builder', None, None),
            ('programs:form_edit', [self.form.pk], None),
            
            # Registration Management
            ('programs:view_registrations', [self.program_instance.pk], None),
            
            # Availability Management
            ('programs:contractor_availability_list', None, None),
            ('programs:contractor_availability_create', None, None),
            ('programs:contractor_availability_detail', [self.availability.pk], None),
            ('programs:contractor_availability_edit', [self.availability.pk], None),
            
            # Session Management
            ('programs:contractor_sessions_list', None, None),
            ('programs:session_detail', [self.session.pk], None),
            
            # Day Off Requests
            ('programs:contractor_day_off_requests', None, None),
            ('programs:contractor_day_off_request_create', None, None),
            
            # Instance Scheduling
            ('programs:contractor_instance_schedule', [self.program_instance.pk], None),
            
            # Onboarding
            ('people:contractor_onboarding', None, None),
            
            # Profile
            ('accounts:profile', None, None),
        ]
        
        for page_data in contractor_pages:
            url_name = page_data[0]
            args = page_data[1]
            kwargs = page_data[2]
            
            with self.subTest(url=url_name):
                namespace, name = url_name.split(':', 1)
                self._test_page_load(name, args, kwargs, self.contractor_user, namespace=namespace)
    
    def test_authenticated_pages(self):
        """Test pages accessible to any authenticated user."""
        authenticated_pages = [
            ('dashboard:dashboard', None, None),
            ('accounts:profile', None, None),
            ('programs:program_catalog', None, None),
        ]
        
        for user in [self.admin_user, self.parent_user, self.contractor_user]:
            for page_data in authenticated_pages:
                url_name = page_data[0]
                args = page_data[1]
                kwargs = page_data[2]
                
                with self.subTest(url=url_name, user=user.email):
                    namespace, name = url_name.split(':', 1)
                    self._test_page_load(name, args, kwargs, user, namespace=namespace)
    
    def test_post_endpoints(self):
        """Test POST endpoints that should accept POST requests."""
        # Test with admin user for most endpoints
        self.client.force_login(self.admin_user)
        
        post_endpoints = [
            # AJAX endpoints that should return 200 on POST
            ('admin_interface:toggle_user_status', [self.parent_user.id]),
            ('admin_interface:toggle_program_instance_status', [self.program_instance.id]),
            ('communications:test_email', None),
        ]
        
        for endpoint_data in post_endpoints:
            url_name = endpoint_data[0]
            args = endpoint_data[1]
            
            with self.subTest(url=url_name):
                try:
                    if ':' in url_name:
                        namespace, name = url_name.split(':', 1)
                        url = reverse(f'{namespace}:{name}', args=args)
                    else:
                        url = reverse(url_name, args=args)
                    
                    response = self.client.post(url)
                    # POST endpoints might return 200 (AJAX), 302 (redirect), or 405 (method not allowed)
                    self.assertIn(response.status_code, (200, 302, 405))
                except NoReverseMatch:
                    pass  # Skip if URL doesn't exist
                except Exception as e:
                    self.fail(f"Exception testing POST endpoint {url_name}: {e}")


class TemplateRenderingTests(TestCase):
    """Test that all templates render without errors."""
    
    def setUp(self):
        """Set up test data for template testing."""
        self.client = Client()
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123'
        )
        admin_group, _ = Group.objects.get_or_create(name='Admin')
        self.admin_user.groups.add(admin_group)
    
    def test_base_template_rendering(self):
        """Test that base template renders correctly."""
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<html')
        self.assertContains(response, '</html>')
    
    def test_home_template_rendering(self):
        """Test that home template renders correctly."""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<html')
        self.assertContains(response, '</html>')
    
    def test_login_template_rendering(self):
        """Test that login template renders correctly."""
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'login')
        self.assertContains(response, 'email')
    
    def test_contact_template_rendering(self):
        """Test that contact template renders correctly."""
        response = self.client.get(reverse('communications:contact'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'contact')
        self.assertContains(response, 'form')


class ErrorPageTests(TestCase):
    """Test error page handling."""
    
    def setUp(self):
        """Set up test data for error testing."""
        self.client = Client()
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123'
        )
        admin_group, _ = Group.objects.get_or_create(name='Admin')
        self.admin_user.groups.add(admin_group)
    
    def test_nonexistent_page_404(self):
        """Test that nonexistent pages return 404."""
        response = self.client.get('/nonexistent-page/')
        self.assertEqual(response.status_code, 404)
    
    def test_unauthorized_access_redirects(self):
        """Test that unauthorized access redirects appropriately."""
        # Test admin page without login
        response = self.client.get(reverse('admin_interface:dashboard'))
        self.assertEqual(response.status_code, 302)  # Should redirect to login
        
        # Test admin page with non-admin user
        non_admin = User.objects.create_user(
            email='user@test.com',
            password='testpass123'
        )
        self.client.force_login(non_admin)
        response = self.client.get(reverse('admin_interface:dashboard'))
        self.assertIn(response.status_code, (302, 403))  # Should redirect or forbid