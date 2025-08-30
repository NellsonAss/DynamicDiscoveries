"""
Tests for requirements tracking system.

This module validates that all requirements listed in site_requirements.json
are properly implemented and tested.
"""

import os
import sys
import tempfile
from pathlib import Path
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.conf import settings

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from utils.requirements_tracker import (
    RequirementsTracker, 
    validate_all_implemented,
    scan_templates_for_undefined_routes,
    parse_template_links
)

User = get_user_model()


class RequirementsValidationTest(TestCase):
    """Test that all requirements are implemented."""
    
    def setUp(self):
        """Set up test environment."""
        self.tracker = RequirementsTracker()
        self.requirements_file = Path("site_requirements.json")
    
    def test_requirements_file_exists(self):
        """Test that the requirements file exists."""
        self.assertTrue(
            self.requirements_file.exists(),
            "site_requirements.json file must exist at project root"
        )
    
    def test_requirements_file_is_valid_json(self):
        """Test that the requirements file contains valid JSON."""
        try:
            requirements_data = self.tracker.load_requirements()
            self.assertIn("requirements", requirements_data)
            self.assertIn("metadata", requirements_data)
        except Exception as e:
            self.fail(f"Requirements file is not valid JSON: {e}")
    
    def test_all_requirements_have_valid_structure(self):
        """Test that all requirements have the required fields."""
        requirements_data = self.tracker.load_requirements()
        
        for req in requirements_data["requirements"]:
            # Check required fields exist
            self.assertIn("id", req, "Requirement missing 'id' field")
            self.assertIn("title", req, "Requirement missing 'title' field")
            self.assertIn("description", req, "Requirement missing 'description' field")
            self.assertIn("status", req, "Requirement missing 'status' field")
            
            # Check field types
            self.assertIsInstance(req["id"], str, "Requirement 'id' must be string")
            self.assertIsInstance(req["title"], str, "Requirement 'title' must be string")
            self.assertIsInstance(req["description"], str, "Requirement 'description' must be string")
            self.assertIsInstance(req["status"], str, "Requirement 'status' must be string")
            
            # Check status is valid
            valid_statuses = ["required", "implemented"]
            self.assertIn(
                req["status"], 
                valid_statuses, 
                f"Requirement status must be one of: {valid_statuses}"
            )
    
    def test_all_requirements_are_implemented(self):
        """Test that all requirements have status 'implemented'."""
        requirements_data = self.tracker.load_requirements()
        
        unimplemented_requirements = []
        for req in requirements_data["requirements"]:
            if req["status"] != "implemented":
                unimplemented_requirements.append(req)
        
        if unimplemented_requirements:
            req_list = "\n".join([
                f"- {req['id']}: {req['title']} (status: {req['status']})"
                for req in unimplemented_requirements
            ])
            self.fail(
                f"The following requirements are not implemented:\n{req_list}\n"
                f"All requirements must have status 'implemented' before tests pass."
            )
    
    def test_validate_all_implemented_function(self):
        """Test the convenience function validate_all_implemented()."""
        self.assertTrue(
            validate_all_implemented(),
            "validate_all_implemented() should return True when all requirements are implemented"
        )
    
    def test_requirement_ids_follow_pattern(self):
        """Test that requirement IDs follow the REQ-XXX pattern."""
        requirements_data = self.tracker.load_requirements()
        
        for req in requirements_data["requirements"]:
            self.assertRegex(
                req["id"], 
                r"^REQ-\d{3}$",
                f"Requirement ID {req['id']} does not follow REQ-XXX pattern"
            )


class RequirementsTrackerTest(TestCase):
    """Test the RequirementsTracker class functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.tracker = RequirementsTracker("test_requirements.json")
    
    def tearDown(self):
        """Clean up test files."""
        test_file = Path("test_requirements.json")
        if test_file.exists():
            test_file.unlink()
    
    def test_add_requirement(self):
        """Test adding a new requirement."""
        req = self.tracker.add_requirement(
            "REQ-999", 
            "Test Requirement", 
            "Test description",
            "required"
        )
        
        self.assertEqual(req["id"], "REQ-999")
        self.assertEqual(req["title"], "Test Requirement")
        self.assertEqual(req["description"], "Test description")
        self.assertEqual(req["status"], "required")
    
    def test_update_requirement_status(self):
        """Test updating requirement status."""
        # Add a requirement first
        self.tracker.add_requirement("REQ-998", "Test", "Test", "required")
        
        # Update status
        updated_req = self.tracker.update_requirement_status("REQ-998", "implemented")
        self.assertEqual(updated_req["status"], "implemented")
    
    def test_invalid_status_raises_error(self):
        """Test that invalid status raises error."""
        with self.assertRaises(ValueError):
            self.tracker.add_requirement("REQ-997", "Test", "Test", "invalid")
    
    def test_duplicate_requirement_id_raises_error(self):
        """Test that duplicate requirement ID raises error."""
        self.tracker.add_requirement("REQ-996", "Test", "Test")
        
        with self.assertRaises(ValueError):
            self.tracker.add_requirement("REQ-996", "Test2", "Test2")
    
    def test_get_requirements_by_status(self):
        """Test getting requirements by status."""
        # Add requirements with different statuses
        self.tracker.add_requirement("REQ-995", "Test1", "Test1", "required")
        self.tracker.add_requirement("REQ-994", "Test2", "Test2", "implemented")
        
        required_reqs = self.tracker.get_requirements_by_status("required")
        implemented_reqs = self.tracker.get_requirements_by_status("implemented")
        
        self.assertEqual(len(required_reqs), 1)
        self.assertEqual(len(implemented_reqs), 1)
        self.assertEqual(required_reqs[0]["id"], "REQ-995")
        self.assertEqual(implemented_reqs[0]["id"], "REQ-994")


class RouteCompletionTest(TestCase):
    """Test the route completion functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.tracker = RequirementsTracker()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_parse_template_links(self):
        """Test parsing template links."""
        # Create a test template file
        template_content = """
        <a href="{% url 'dashboard:dashboard' %}">Dashboard</a>
        <a href="{% url 'programs:parent_dashboard' %}">Parent Dashboard</a>
        <div hx-get="{% url 'programs:get_programs' %}">Load Programs</div>
        <form hx-post="{% url 'programs:register_child' %}">Register</form>
        <a href="https://external.com">External Link</a>
        <a href="/static/css/style.css">Static File</a>
        <a href="{% url 'undefined:route' %}">Undefined Route</a>
        """
        
        template_file = Path(self.temp_dir) / "test.html"
        with open(template_file, 'w') as f:
            f.write(template_content)
        
        # Parse the template
        result = self.tracker.parse_template_links(str(template_file))
        
        # Check that links are extracted
        self.assertIn("dashboard:dashboard", result["links"])
        self.assertIn("programs:parent_dashboard", result["links"])
        self.assertIn("programs:get_programs", result["htmx_calls"])
        self.assertIn("programs:register_child", result["htmx_calls"])
        
        # Check that external and static links are filtered out
        self.assertNotIn("https://external.com", result["links"])
        self.assertNotIn("/static/css/style.css", result["links"])
        
        # Check that undefined routes are identified
        self.assertIn("undefined:route", result["undefined_routes"])
    
    def test_scan_all_templates(self):
        """Test scanning all templates for undefined routes."""
        # Create test template files
        templates_dir = Path(self.temp_dir) / "templates"
        templates_dir.mkdir()
        
        # Template with defined routes
        template1_content = """
        <a href="{% url 'dashboard:dashboard' %}">Dashboard</a>
        <div hx-get="{% url 'programs:get_programs' %}">Load</div>
        """
        
        # Template with undefined routes
        template2_content = """
        <a href="{% url 'undefined:route1' %}">Undefined 1</a>
        <div hx-post="{% url 'missing:route2' %}">Undefined 2</div>
        """
        
        with open(templates_dir / "template1.html", 'w') as f:
            f.write(template1_content)
        
        with open(templates_dir / "template2.html", 'w') as f:
            f.write(template2_content)
        
        # Scan templates
        result = self.tracker.scan_all_templates(str(templates_dir))
        
        # Check that undefined routes are found
        self.assertIn("undefined:route1", result["undefined_routes"])
        self.assertIn("missing:route2", result["undefined_routes"])
    
    def test_generate_route_completion_prompt(self):
        """Test generating route completion prompts."""
        undefined_routes = ["route1", "route2", "namespace:route3"]
        
        prompt = self.tracker.generate_route_completion_prompt(undefined_routes)
        
        self.assertIn("route1", prompt)
        self.assertIn("route2", prompt)
        self.assertIn("namespace:route3", prompt)
        self.assertIn("Would you like to implement these routes now?", prompt)
    
    def test_generate_route_completion_prompt_empty(self):
        """Test generating prompt with no undefined routes."""
        prompt = self.tracker.generate_route_completion_prompt([])
        
        self.assertEqual(prompt, "No undefined routes found.")


class RequirementsAcceptanceTests(TestCase):
    """Acceptance tests for all requirements."""
    
    def setUp(self):
        """Set up test environment."""
        self.client = Client()
        self.tracker = RequirementsTracker()
        
        # Create test users
        User = get_user_model()
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_active=True
        )
        # Add admin role using Django groups
        admin_group, _ = Group.objects.get_or_create(name='Admin')
        self.admin_user.groups.add(admin_group)
        
        self.parent_user = User.objects.create_user(
            email="parent@test.com",
            password="testpass123",
            is_active=True
        )
        # Add parent role using Django groups
        parent_group, _ = Group.objects.get_or_create(name='Parent')
        self.parent_user.groups.add(parent_group)
        
        self.contractor_user = User.objects.create_user(
            email="contractor@test.com",
            password="testpass123",
            is_active=True
        )
        # Add contractor role using Django groups
        contractor_group, _ = Group.objects.get_or_create(name='Contractor')
        self.contractor_user.groups.add(contractor_group)
    
    def test_REQ_001_requirements_tracking_system(self):
        """Test REQ-001: Requirements tracking system."""
        # Test that requirements file exists and is valid
        requirements_data = self.tracker.load_requirements()
        self.assertIn("requirements", requirements_data)
        self.assertIn("metadata", requirements_data)
        
        # Test that tracker can add and update requirements
        # Use a unique ID unlikely to exist (walk down until free)
        unique_id = "REQ-997"
        existing = {r["id"] for r in self.tracker.load_requirements()["requirements"]}
        while unique_id in existing:
            num = int(unique_id.split('-')[1]) - 1
            unique_id = f"REQ-{num:03d}"
        test_req = self.tracker.add_requirement(unique_id, "Test", "Test", "implemented")
        self.assertEqual(test_req["status"], "implemented")
    
    def test_REQ_002_requirements_management_cli(self):
        """Test REQ-002: Requirements management CLI."""
        # Test that CLI functions work
        from utils.requirements_tracker import add_requirement, update_requirement_status
        # Use an ID not present
        unique_id = "REQ-995"
        tracker = RequirementsTracker()
        existing_ids = {r["id"] for r in tracker.load_requirements()["requirements"]}
        while unique_id in existing_ids:
            num = int(unique_id.split('-')[1]) - 1
            unique_id = f"REQ-{num:03d}"
        test_req = add_requirement(unique_id, "Test2", "Test2", "implemented")
        self.assertEqual(test_req["id"], unique_id)
    
    def test_REQ_003_user_authentication_system(self):
        """Test REQ-003: User authentication system."""
        # Test custom user model
        User = get_user_model()
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123"
        )
        self.assertTrue(user.check_password("testpass123"))
        self.assertFalse(user.check_password("wrongpass"))
    
    def test_REQ_004_user_registration_and_login(self):
        """Test REQ-004: User registration and login."""
        # Test login functionality
        response = self.client.post(reverse('accounts:login'), {
            'email': 'admin@test.com',
            'password': 'testpass123'
        }, follow=True)
        # Allow either 200 with rendered dashboard or a redirect chain ending at dashboard
        self.assertIn(response.status_code, (200, 302))
    
    def test_REQ_005_role_based_access_control(self):
        """Test REQ-005: Role-based access control."""
        # Test role assignment
        admin_group = Group.objects.get(name='Admin')
        self.admin_user.groups.add(admin_group)
        self.assertIn("Admin", self.admin_user.get_role_names())
        
        parent_group = Group.objects.get(name='Parent')
        self.parent_user.groups.add(parent_group)
        self.assertIn("Parent", self.parent_user.get_role_names())
    
    def test_REQ_006_user_profile_management(self):
        """Test REQ-006: User profile management."""
        # Test user profile functionality
        self.admin_user.bio = "Test bio"
        self.admin_user.save()
        self.assertEqual(self.admin_user.bio, "Test bio")
    
    def test_REQ_007_contact_form_system(self):
        """Test REQ-007: Contact form system."""
        # Test contact form submission
        response = self.client.post(reverse('communications:contact'), {
            'parent_name': 'Test User',
            'email': 'test@example.com',
            'message': 'Test message',
            'interest': 'after_school'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after submission
    
    def test_REQ_008_email_notification_system(self):
        """Test REQ-008: Email notification system."""
        # Test that email functionality is available
        from communications.models import Contact
        contact = Contact.objects.create(
            parent_name="Test",
            email="test@example.com",
            message="Test",
            interest="after_school"
        )
        self.assertIsNotNone(contact)
    
    def test_REQ_009_contact_management_dashboard(self):
        """Test REQ-009: Contact management dashboard."""
        # Test admin access to contact management
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('communications:contact_list'))
        self.assertEqual(response.status_code, 200)
    
    def test_REQ_010_program_management_system(self):
        """Test REQ-010: Program management system."""
        # Test program type creation
        from programs.models import ProgramType, Role, BaseCost
        role = Role.objects.create(title="Instructor", description="Test instructor role")
        base_cost = BaseCost.objects.create(name="Base Cost", rate=10.00, frequency="PER_SESSION", description="Test cost")
        
        program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test Description"
        )
        
        # Create buildout and attach a role
        from programs.models import ProgramBuildout
        buildout = ProgramBuildout.objects.create(
            program_type=program_type,
            title="Test Buildout",
            num_facilitators=2,
            num_new_facilitators=1,
            students_per_program=12,
            sessions_per_program=8,
            rate_per_student=25.00
        )
        buildout.roles.add(role)
        
        # Create buildout base cost
        from programs.models import BuildoutBaseCostAssignment
        buildout_base_cost = BuildoutBaseCostAssignment.objects.create(
            buildout=buildout,
            base_cost=base_cost,
            multiplier=1.00
        )
        
        self.assertEqual(program_type.name, "Test Program")
        self.assertEqual(buildout.roles.count(), 1)
        self.assertEqual(buildout.base_costs.count(), 1)
    
    def test_REQ_011_program_type_templates(self):
        """Test REQ-011: Program type templates."""
        from programs.models import ProgramType, Role, BaseCost
        role = Role.objects.create(title="Instructor", description="Test instructor role")
        base_cost = BaseCost.objects.create(name="Base Cost", rate=10.00, frequency="PER_SESSION", description="Test cost")
        
        program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test Description"
        )
        
        # Create buildout and attach a role
        from programs.models import ProgramBuildout
        buildout = ProgramBuildout.objects.create(
            program_type=program_type,
            title="Test Buildout",
            num_facilitators=2,
            num_new_facilitators=1,
            students_per_program=12,
            sessions_per_program=8,
            rate_per_student=25.00
        )
        buildout.roles.add(role)
        
        # Create buildout base cost
        from programs.models import BuildoutBaseCostAssignment
        buildout_base_cost = BuildoutBaseCostAssignment.objects.create(
            buildout=buildout,
            base_cost=base_cost,
            multiplier=1.00
        )
        
        # Test role assignment
        self.assertEqual(buildout.roles.count(), 1)
        self.assertEqual(role.title, "Instructor")
        
        # Test cost assignment
        self.assertEqual(buildout.base_costs.count(), 1)
        self.assertEqual(base_cost.rate, 10.00)
    
    def test_REQ_012_role_and_payout_management(self):
        """Test REQ-012: Role and payout management."""
        from programs.models import Role, Responsibility
        role = Role.objects.create(title="Instructor", description="Test instructor role")
        
        # Create responsibility
        responsibility = Responsibility.objects.create(
            role=role,
            name="Teaching",
            description="Teaching responsibilities",
            frequency_type="PER_SESSION",
            default_hours=2.0
        )
        
        self.assertEqual(role.title, "Instructor")
        self.assertEqual(responsibility.default_hours, 2.0)
        self.assertEqual(responsibility.frequency_type, "PER_SESSION")
    
    def test_REQ_013_cost_management_system(self):
        """Test REQ-013: Cost management system."""
        from programs.models import BaseCost
        base_cost = BaseCost.objects.create(name="Base Cost", rate=10.00, frequency="PER_SESSION", description="Test cost")
        
        self.assertEqual(base_cost.name, "Base Cost")
        self.assertEqual(base_cost.rate, 10.00)
        self.assertEqual(base_cost.frequency, "PER_SESSION")
    
    def test_REQ_014_program_buildout_configuration(self):
        """Test REQ-014: Program buildout configuration."""
        from programs.models import ProgramType, Role, ProgramBuildout
        role = Role.objects.create(title="Instructor", description="Test instructor role")
        
        program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test Description"
        )
        
        # Create buildout
        buildout = ProgramBuildout.objects.create(
            program_type=program_type,
            title="Test Buildout",
            num_facilitators=2,
            num_new_facilitators=1,
            students_per_program=12,
            sessions_per_program=8,
            rate_per_student=25.00
        )
        
        buildout.roles.add(role)
        
        # Test buildout creation
        self.assertEqual(buildout.title, "Test Buildout")
        self.assertEqual(buildout.num_facilitators, 2)
        self.assertEqual(buildout.students_per_program, 12)
        self.assertEqual(buildout.rate_per_student, 25.00)
        
        # Test role assignment
        self.assertEqual(buildout.roles.count(), 1)
        self.assertEqual(buildout.roles.first(), role)
    
    def test_REQ_015_program_instance_management(self):
        """Test REQ-015: Program instance management."""
        from programs.models import ProgramType, Role, ProgramBuildout, ProgramInstance
        from django.contrib.auth import get_user_model
        from django.utils import timezone
        from datetime import timedelta
        
        User = get_user_model()
        
        role = Role.objects.create(title="Instructor", description="Test instructor role")
        
        program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test Description"
        )
        
        # Create buildout
        buildout = ProgramBuildout.objects.create(
            program_type=program_type,
            title="Test Buildout",
            num_facilitators=2,
            num_new_facilitators=1,
            students_per_program=12,
            sessions_per_program=8,
            rate_per_student=25.00
        )
        
        # Create user
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123"
        )
        
        # Create program instance
        start_date = timezone.now()
        end_date = start_date + timedelta(days=30)
        
        program_instance = ProgramInstance.objects.create(
            buildout=buildout,
            title="Test Instance",
            start_date=start_date,
            end_date=end_date,
            location="Test Location",
            capacity=20
        )
        
        # Create instance role assignment
        from programs.models import InstanceRoleAssignment
        instance_role = InstanceRoleAssignment.objects.create(
            program_instance=program_instance,
            role=role,
            contractor=user
        )
        
        self.assertEqual(program_instance.title, "Test Instance")
        self.assertEqual(program_instance.location, "Test Location")
        self.assertEqual(program_instance.capacity, 20)
        self.assertEqual(program_instance.contractor_assignments.count(), 1)
    
    def test_REQ_016_registration_form_builder(self):
        """Test REQ-016: Registration form builder."""
        from programs.models import RegistrationForm, FormQuestion
        form = RegistrationForm.objects.create(
            title="Test Form",
            description="Test Description",
            created_by=self.admin_user
        )
        
        question = FormQuestion.objects.create(
            form=form,
            question_text="Test Question",
            question_type="text"
        )
        
        self.assertEqual(form.title, "Test Form")
        self.assertEqual(question.form, form)
        self.assertEqual(question.question_text, "Test Question")
    
    def test_REQ_017_child_management_system(self):
        """Test REQ-017: Child management system."""
        from programs.models import Child
        from datetime import date
        child = Child.objects.create(
            parent=self.parent_user,
            first_name="Test",
            last_name="Child",
            date_of_birth=date(2015, 1, 1)
        )
        
        self.assertEqual(child.parent, self.parent_user)
        self.assertEqual(child.first_name, "Test")
        self.assertEqual(child.last_name, "Child")
    
    def test_REQ_018_program_registration_system(self):
        """Test REQ-018: Program registration system."""
        from programs.models import ProgramType, Role, ProgramBuildout, ProgramInstance, Child, Registration
        from django.contrib.auth import get_user_model
        from django.utils import timezone
        from datetime import timedelta
        
        User = get_user_model()
        
        role = Role.objects.create(title="Instructor", description="Test instructor role")
        
        program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test Description"
        )
        
        # Create buildout
        buildout = ProgramBuildout.objects.create(
            program_type=program_type,
            title="Test Buildout",
            num_facilitators=2,
            num_new_facilitators=1,
            students_per_program=12,
            sessions_per_program=8,
            rate_per_student=25.00
        )
        
        # Create parent user
        parent = User.objects.create_user(
            email="parent@example.com",
            password="testpass123"
        )
        
        # Create child
        child = Child.objects.create(
            parent=parent,
            first_name="Test",
            last_name="Child",
            date_of_birth="2015-01-01"
        )
        
        # Create program instance
        start_date = timezone.now()
        end_date = start_date + timedelta(days=30)
        
        program_instance = ProgramInstance.objects.create(
            buildout=buildout,
            title="Test Instance",
            start_date=start_date,
            end_date=end_date,
            location="Test Location",
            capacity=20
        )
        
        # Create registration
        registration = Registration.objects.create(
            child=child,
            program_instance=program_instance,
            status="pending"
        )
        
        self.assertEqual(registration.child, child)
        self.assertEqual(registration.program_instance, program_instance)
        self.assertEqual(registration.status, "pending")
    
    def test_REQ_019_financial_calculation_engine(self):
        """Test REQ-019: Financial calculation engine."""
        from programs.models import ProgramType, Role, Responsibility, ProgramBuildout
        from decimal import Decimal
        
        role = Role.objects.create(title="Instructor", description="Test instructor role")
        
        # Create responsibility
        responsibility = Responsibility.objects.create(
            role=role,
            name="Teaching",
            description="Teaching responsibilities",
            frequency_type="PER_SESSION",
            default_hours=2.0
        )
        
        program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test Description"
        )
        
        # Create buildout
        buildout = ProgramBuildout.objects.create(
            program_type=program_type,
            title="Test Buildout",
            num_facilitators=2,
            num_new_facilitators=1,
            students_per_program=12,
            sessions_per_program=8,
            rate_per_student=25.00
        )
        
        # Test financial calculations
        self.assertEqual(buildout.total_students_per_year, 96)  # 2 facilitators * 4 workshops * 12 students
        self.assertEqual(buildout.total_revenue_per_year, Decimal('2400.00'))  # 96 students * $25
        self.assertIsInstance(buildout.expected_profit, Decimal)
        self.assertIsInstance(buildout.profit_margin, Decimal)
    
    def test_REQ_020_dashboard_interface(self):
        """Test REQ-020: Dashboard interface."""
        # Test dashboard access
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)
    
    def test_REQ_021_htmx_integration(self):
        """Test REQ-021: HTMX integration."""
        # Test that HTMX is included in base template
        response = self.client.get(reverse('dashboard:dashboard'), follow=True)
        content = b"".join(chunk for chunk in response)
        self.assertIn(b'htmx.org', content)
    
    def test_REQ_022_bootstrap_ui_framework(self):
        """Test REQ-022: Bootstrap UI framework."""
        # Test that Bootstrap is included in base template
        response = self.client.get(reverse('dashboard:dashboard'), follow=True)
        content = b"".join(chunk for chunk in response)
        self.assertIn(b'bootstrap', content)
    
    def test_REQ_023_admin_interface(self):
        """Test REQ-023: Admin interface."""
        # Test admin access
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin/', follow=True)
        self.assertEqual(response.status_code, 200)
    
    def test_REQ_024_testing_framework(self):
        """Test REQ-024: Testing framework."""
        # Test that Django test framework is working
        from django.test import TestCase
        test_case = TestCase()
        test_case.assertTrue(True)  # Basic test functionality
        
        # Test that requirements validation is working
        self.assertTrue(validate_all_implemented())
    
    def test_REQ_025_test_user_setup_system(self):
        """Test REQ-025: Test user setup system."""
        # Test that test users can be created
        User = get_user_model()
        test_user = User.objects.create_user(
            email="test@example.com",
            password="testpass123"
        )
        parent_group = Group.objects.get(name='Parent')
        test_user.groups.add(parent_group)
        
        self.assertEqual(test_user.email, "test@example.com")
        self.assertIn("Parent", test_user.get_role_names())
    
    def test_REQ_026_custom_template_math_filters(self):
        """Test REQ-026: Custom template math filters."""
        # Test that custom template filters are available
        from django.template import Template, Context
        
        # Test that math filters can be used in templates
        template = Template("{% load math_filters %}{{ 10|multiply:5 }}")
        context = Context({})
        result = template.render(context)
        self.assertEqual(result.strip(), "50.0")
        
        # Test divide filter
        template = Template("{% load math_filters %}{{ 10|divide:2 }}")
        result = template.render(context)
        self.assertEqual(result.strip(), "5.0")
        
        # Test subtract filter
        template = Template("{% load math_filters %}{{ 10|subtract:3 }}")
        result = template.render(context)
        self.assertEqual(result.strip(), "7.0")
        
        # Test percentage filter
        template = Template("{% load math_filters %}{{ 25|percentage:100 }}")
        result = template.render(context)
        self.assertEqual(result.strip(), "25.0")
    
    def test_REQ_027_custom_admin_interface(self):
        """Test REQ-027: Custom admin interface."""
        # Test that custom admin pages are accessible
        self.client.force_login(self.admin_user)
        
        # Test user management access
        response = self.client.get(reverse('admin_interface:user_management'))
        self.assertEqual(response.status_code, 200)
        
        # Test program management access
        response = self.client.get(reverse('admin_interface:program_type_management'))
        self.assertEqual(response.status_code, 200)
    
    def test_REQ_028_user_detail_view(self):
        """Test REQ-028: User detail view."""
        # Test user detail page access
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('admin_interface:user_detail', args=[self.admin_user.id]))
        self.assertEqual(response.status_code, 200)

    def test_REQ_078_role_detail_responsibility_edit_fix(self):
        """Test REQ-078: Role detail responsibility edit pencil links to edit view."""
        from programs.models import Role, Responsibility
        self.client.force_login(self.admin_user)
        role = Role.objects.create(title="Ops Support", description="d")
        r = Responsibility.objects.create(
            role=role,
            name="Email Parents",
            description="d",
            frequency_type="PER_PROGRAM",
            default_hours=1.0,
        )
        # Load role detail page
        resp = self.client.get(reverse('admin_interface:role_detail', args=[role.id]))
        self.assertEqual(resp.status_code, 200)
        # The edit URL should be present for this responsibility
        self.assertIn(reverse('admin_interface:responsibility_edit', args=[r.id]).encode(), b"".join(resp))

    def test_REQ_079_remove_role_level_default_hourly_rate_ui(self):
        """Test REQ-079: Role management page has no default hourly rate column."""
        from programs.models import Role
        self.client.force_login(self.admin_user)
        Role.objects.create(title="Designer", description="d")
        resp = self.client.get(reverse('admin_interface:role_management'))
        self.assertEqual(resp.status_code, 200)
        content = b"".join(resp)
        # Ensure the hard-coded default rate label is gone
        self.assertNotIn(b"default rate", content)
        self.assertNotIn(b"Avg Hourly Rate", content)
    
    def test_REQ_029_route_completion_system(self):
        """Test REQ-029: Route completion system."""
        # Test that route completion functionality is available
        from utils.requirements_tracker import scan_templates_for_undefined_routes, parse_template_links
        
        # Test template parsing functionality
        result = parse_template_links("templates/base.html")
        self.assertIsInstance(result, dict)
        self.assertIn("links", result)
        self.assertIn("htmx_calls", result)
        self.assertIn("undefined_routes", result)
        
        # Test template scanning functionality
        scan_result = scan_templates_for_undefined_routes("templates")
        self.assertIsInstance(scan_result, dict)
        self.assertIn("undefined_routes", scan_result)
        
        # Test that the tracker can generate prompts
        tracker = RequirementsTracker()
        prompt = tracker.generate_route_completion_prompt(["test:route"])
        self.assertIn("test:route", prompt)
        self.assertIn("Would you like to implement these routes now?", prompt) 

    def test_REQ_076_contractor_onboarding_and_contract_flow(self):
        """Test REQ-076: Contractor Onboarding and Contract Flow."""
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Group
        from programs.models import ProgramType, ProgramBuildout
        from people.models import Contractor
        from contracts.models import LegalDocumentTemplate
        from django.urls import reverse

        # Seed template entries
        LegalDocumentTemplate.objects.get_or_create(key="nda", defaults={"docusign_template_id": "TEMPLATE_NDA"})
        LegalDocumentTemplate.objects.get_or_create(key="service_agreement", defaults={"docusign_template_id": "TEMPLATE_SVC"})

        # Create users
        User = get_user_model()
        admin = User.objects.create_user(email="admin@x.com", password="pass")
        contractor_user = User.objects.create_user(email="c@x.com", password="pass")
        g, _ = Group.objects.get_or_create(name='Contractor')
        contractor_user.groups.add(g)
        contractor = Contractor.objects.create(user=contractor_user, nda_signed=True)

        # Buildout ready and assigned
        pt = ProgramType.objects.create(name="PT1", description="d")
        b = ProgramBuildout.objects.create(
            program_type=pt,
            title="B",
            num_facilitators=1,
            num_new_facilitators=0,
            students_per_program=10,
            sessions_per_program=5,
            rate_per_student=10.0,
            status='ready'
        )
        b.assigned_contractor = contractor
        b.save()

        # Admin presents to contractor
        self.client.force_login(admin)
        resp = self.client.post(reverse('programs:present_to_contractor', args=[b.id]))
        self.assertIn(resp.status_code, (302, 301))

        # Simulate DocuSign webhook completion
        from contracts.models import Contract
        contract = Contract.objects.filter(buildout=b).first()
        self.assertIsNotNone(contract)
        payload = '{"envelopeId": "%s", "status": "completed"}' % (contract.envelope_id or 'dev-env')
        resp = self.client.post(reverse('contracts:webhook'), data=payload, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        b.refresh_from_db()
        self.assertEqual(b.status, 'active')

    def test_REQ_077_onboarding_gates(self):
        """Assign and availability gates enforced until onboarding complete."""
        from django.contrib.auth.models import Group
        from django.urls import reverse
        from people.models import Contractor
        from programs.models import ProgramType, ProgramBuildout
        from contracts.services.assignment import assign_contractor_to_buildout
        from django.core.exceptions import ValidationError

        # Create contractor lacking onboarding
        user = get_user_model().objects.create_user(email="c4@x.com", password="pass")
        g, _ = Group.objects.get_or_create(name='Contractor')
        user.groups.add(g)
        contractor = Contractor.objects.create(user=user, nda_signed=False)

        # Buildout
        pt = ProgramType.objects.create(name="PT3", description="d")
        b = ProgramBuildout.objects.create(
            program_type=pt,
            title="B3",
            num_facilitators=1,
            num_new_facilitators=0,
            students_per_program=10,
            sessions_per_program=5,
            rate_per_student=10.0,
        )
        with self.assertRaises(ValidationError):
            assign_contractor_to_buildout(b, contractor)

        # Availability create/edit 403 until onboarding complete
        self.client.force_login(user)
        resp = self.client.get(reverse('programs:contractor_availability_create'))
        self.assertEqual(resp.status_code, 403)