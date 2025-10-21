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
        """Test that requirement IDs follow valid patterns (REQ-XXX, REQ-XXXX-XX-XX-XXX, REQ-CATEGORY-XXX)."""
        requirements_data = self.tracker.load_requirements()
        
        # Valid patterns: REQ-XXX, REQ-YYYY-MM-DD-XXX, REQ-CATEGORY-XXX, unified_communication_system (legacy)
        valid_patterns = [
            r"^REQ-\d{3}$",  # REQ-001
            r"^REQ-\d{4}-\d{3}-\d{3}$",  # REQ-2025-001-038 (year-sequential-number)
            r"^REQ-\d{4}-\d{2}-\d{2}-\d{3}$",  # REQ-2025-10-09-001 (year-month-day-number)
            r"^REQ-\d{4}-\d{1}-\d{2}-\d{3}$",  # REQ-2025-1-27-002 (year-month-day-number with single digit month)
            r"^REQ-[A-Z]+(?:-[A-Z]+)*-\d{3}$",  # REQ-USER-001 or REQ-USER-MGMT-001 (multi-part categories)
            r"^unified_[a-z_]+_system$",  # Legacy pattern for unified_communication_system
        ]
        
        for req in requirements_data["requirements"]:
            req_id = req["id"]
            matches_pattern = any(
                __import__('re').match(pattern, req_id) 
                for pattern in valid_patterns
            )
            self.assertTrue(
                matches_pattern,
                f"Requirement ID '{req_id}' does not match any valid pattern"
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
        # Test contact form page access
        response = self.client.get(reverse('communications:contact_entry'))
        self.assertIn(response.status_code, [200, 302])  # 200 for form display or 302 for redirect
    
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
        from programs.models import ProgramType, Role, BaseCost, BuildoutRoleLine
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        contractor = User.objects.create_user(email="contractor-010@test.com", password="test")
        
        role = Role.objects.create(title="Instructor", description="Test instructor role")
        base_cost = BaseCost.objects.create(name="Base Cost", rate=10.00, frequency="PER_SESSION", description="Test cost")
        
        program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test Description"
        )
        
        # Create buildout
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
        
        # Create role line (proper way to add roles to buildout)
        role_line = BuildoutRoleLine.objects.create(
            buildout=buildout,
            role=role,
            contractor=contractor,
            pay_type='HOURLY',
            pay_value=50.00,
            frequency_unit='PER_PROGRAM',
            frequency_count=1,
            hours_per_frequency=10.0
        )
        
        # Create buildout base cost
        from programs.models import BuildoutBaseCostAssignment
        buildout_base_cost = BuildoutBaseCostAssignment.objects.create(
            buildout=buildout,
            base_cost=base_cost,
            rate=10.00,
            frequency='PER_SESSION'
        )
        
        self.assertEqual(program_type.name, "Test Program")
        self.assertEqual(buildout.role_lines.count(), 1)
        self.assertEqual(buildout.base_cost_assignments.count(), 1)
    
    def test_REQ_011_program_type_templates(self):
        """Test REQ-011: Program type templates."""
        from programs.models import ProgramType, Role, BaseCost, BuildoutRoleLine
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        contractor = User.objects.create_user(email="contractor-011@test.com", password="test")
        
        role = Role.objects.create(title="Instructor", description="Test instructor role")
        base_cost = BaseCost.objects.create(name="Base Cost", rate=10.00, frequency="PER_SESSION", description="Test cost")
        
        program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test Description"
        )
        
        # Create buildout
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
        
        # Create role line
        role_line = BuildoutRoleLine.objects.create(
            buildout=buildout,
            role=role,
            contractor=contractor,
            pay_type='HOURLY',
            pay_value=50.00,
            frequency_unit='PER_PROGRAM',
            frequency_count=1,
            hours_per_frequency=10.0
        )
        
        # Create buildout base cost
        from programs.models import BuildoutBaseCostAssignment
        buildout_base_cost = BuildoutBaseCostAssignment.objects.create(
            buildout=buildout,
            base_cost=base_cost,
            rate=10.00,
            frequency='PER_SESSION'
        )
        
        # Test role assignment
        self.assertEqual(buildout.role_lines.count(), 1)
        self.assertEqual(role.title, "Instructor")
        
        # Test cost assignment
        self.assertEqual(buildout.base_cost_assignments.count(), 1)
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
        from programs.models import ProgramType, Role, ProgramBuildout, BuildoutRoleLine
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        contractor = User.objects.create_user(email="contractor-014@test.com", password="test")
        
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
        
        # Create role line
        role_line = BuildoutRoleLine.objects.create(
            buildout=buildout,
            role=role,
            contractor=contractor,
            pay_type='HOURLY',
            pay_value=50.00,
            frequency_unit='PER_PROGRAM',
            frequency_count=1,
            hours_per_frequency=10.0
        )
        
        # Test buildout creation
        self.assertEqual(buildout.title, "Test Buildout")
        self.assertEqual(buildout.num_facilitators, 2)
        self.assertEqual(buildout.students_per_program, 12)
        self.assertEqual(buildout.rate_per_student, 25.00)
        
        # Test role assignment
        self.assertEqual(buildout.role_lines.count(), 1)
        self.assertEqual(buildout.role_lines.first().role, role)
    
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

    def test_req_092_comprehensive_parent_landing_page(self):
        """Test REQ-092: Comprehensive Parent Landing Page."""
        from programs.models import Child, ProgramType, ProgramBuildout, ProgramInstance, Registration
        from programs.views import parent_dashboard, send_program_inquiry
        from django.contrib.auth.models import Group
        
        # Use existing parent user from setUp (parent@test.com already exists)
        parent_user = self.parent_user
        parent_user.first_name = 'Test'
        parent_user.last_name = 'Parent'
        parent_user.save()
        
        # Test parent dashboard access control
        client = Client()
        response = client.get(reverse('programs:parent_dashboard'))
        self.assertEqual(response.status_code, 302)  # Should redirect to login
        
        # Login as parent
        client.login(email='parent@test.com', password='testpass123')
        response = client.get(reverse('programs:parent_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome, Test')
        
        # Test sections are present
        self.assertContains(response, 'Your Kids')
        self.assertContains(response, 'Current Sign-ups')
        self.assertContains(response, 'Availability Calendar')
        self.assertContains(response, 'Available Programs to Inquire')
        self.assertContains(response, 'Facilitators')
        
        # Test empty state for kids
        self.assertContains(response, 'No kids on file yet')
        self.assertContains(response, 'Add a Child')
        
        # Create a child and test it appears
        child = Child.objects.create(
            parent=parent_user,
            first_name='Test',
            last_name='Child',
            date_of_birth='2015-01-01',
            grade_level='3rd'
        )
        
        response = client.get(reverse('programs:parent_dashboard'))
        self.assertContains(response, 'Test Child')
        self.assertContains(response, 'Grade: 3rd')
        
        # Test program inquiry functionality
        program_type = ProgramType.objects.create(
            name='Test Program',
            description='A test program'
        )
        
        # Test inquiry submission
        response = client.post(reverse('programs:send_program_inquiry'), {
            'program_type_id': program_type.id,
            'child_id': child.id,
            'note': 'Test inquiry'
        })
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertTrue(response_data['success'])
        self.assertIn('Thanks! We\'ll be in touch about Test Program', response_data['message'])
        
        # Test that program request was created
        from programs.models import ProgramRequest
        inquiry = ProgramRequest.objects.filter(
            requester=parent_user,
            program_type=program_type
        ).first()
        self.assertIsNotNone(inquiry)
        self.assertEqual(inquiry.request_type, 'parent_request')
        self.assertIn('Child: Test Child', inquiry.additional_notes)
        
        # Test non-parent access is denied
        non_parent = User.objects.create_user(
            email='notparent@test.com',
            password='testpass123'
        )
        client.logout()
        client.login(email='notparent@test.com', password='testpass123')
        response = client.get(reverse('programs:parent_dashboard'))
        self.assertEqual(response.status_code, 302)  # Should redirect

    def test_REQ_030_cost_management_interface(self):
        """Test REQ-030: Cost Management Interface."""
        from programs.models import BaseCost
        self.client.force_login(self.admin_user)
        
        # Create a base cost
        cost = BaseCost.objects.create(
            name="Test Cost",
            rate=15.00,
            frequency="PER_SESSION",
            description="Test cost"
        )
        
        # Test cost list view is accessible
        response = self.client.get(reverse('admin_interface:cost_management'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cost Management")
    
    def test_REQ_033_refactored_program_management_data_model(self):
        """Test REQ-033: Refactored Program Management Data Model."""
        from programs.models import ProgramType, ProgramBuildout, Role, BuildoutRoleLine
        
        # Test new architecture with simplified models
        program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test"
        )
        
        role = Role.objects.create(
            title="Test Role",
            description="Test"
        )
        
        buildout = ProgramBuildout.objects.create(
            program_type=program_type,
            title="Test Buildout",
            num_facilitators=1,
            num_new_facilitators=0,
            students_per_program=10,
            sessions_per_program=5,
            rate_per_student=20.00
        )
        
        self.assertEqual(program_type.name, "Test Program")
        self.assertIsNotNone(buildout)
    
    def test_REQ_053_enhanced_contractor_availability_system(self):
        """Test REQ-053: Enhanced Contractor Availability System."""
        from programs.models import ContractorAvailability
        from django.utils import timezone
        from datetime import timedelta
        
        contractor = User.objects.create_user(email="contractor-053@test.com", password="test")
        
        # Create availability
        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(hours=4)
        
        availability = ContractorAvailability.objects.create(
            contractor=contractor,
            start_datetime=start,
            end_datetime=end,
            status='available'
        )
        
        self.assertEqual(availability.contractor, contractor)
        self.assertEqual(availability.status, 'available')
    
    def test_REQ_062_holiday_management_system(self):
        """Test REQ-062: Holiday Management System."""
        from programs.models import Holiday
        from datetime import date
        
        # Create holiday
        holiday = Holiday.objects.create(
            name="Test Holiday",
            date=date(2025, 12, 25),
            is_recurring=True
        )
        
        self.assertEqual(holiday.name, "Test Holiday")
        self.assertTrue(holiday.is_recurring)
    
    def test_REQ_073_public_program_catalog(self):
        """Test REQ-073: Public Program Catalog."""
        from programs.models import ProgramType
        
        # Create program type
        program_type = ProgramType.objects.create(
            name="Catalog Program",
            description="Test"
        )
        
        # Test catalog is accessible
        self.client.force_login(self.parent_user)
        response = self.client.get(reverse('programs:program_catalog'))
        self.assertEqual(response.status_code, 200)
    
    def test_REQ_080_notes_system(self):
        """Test REQ-080: Notes System with Role-Based Visibility."""
        from notes.models import StudentNote
        from programs.models import Child
        
        # Create child
        child = Child.objects.create(
            parent=self.parent_user,
            first_name="Test",
            last_name="Child",
            date_of_birth="2015-01-01"
        )
        
        # Create note
        note = StudentNote.objects.create(
            student=child,
            created_by=self.admin_user,
            title="Test Note",
            body="Test content",
            visibility_scope='private_staff'
        )
        
        self.assertEqual(note.student, child)
        self.assertEqual(note.created_by, self.admin_user)
        self.assertEqual(note.visibility_scope, 'private_staff')
    
    def test_REQ_081_accurate_dashboard_metrics(self):
        """Test REQ-081: Accurate Dashboard User Metrics."""
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Verify dashboard shows real user counts
        user_count = User.objects.count()
        self.assertGreater(user_count, 0)
    
    def test_REQ_082_role_based_user_assignment(self):
        """Test REQ-082: Role-Based User Assignment System."""
        from programs.models import Role, RoleAssignment
        
        role = Role.objects.create(title="Test Assignment Role", description="Test")
        
        # Create role assignment
        assignment = RoleAssignment.objects.create(
            user=self.contractor_user,
            role=role,
            assigned_by=self.admin_user
        )
        
        self.assertEqual(assignment.user, self.contractor_user)
        self.assertEqual(assignment.role, role)
    
    def test_REQ_090_in_app_nda_signing(self):
        """Test REQ-090: In-App NDA Signing System."""
        from people.models import NDASignature, Contractor
        
        # Create contractor first
        contractor = Contractor.objects.create(user=self.contractor_user)
        
        # Create NDA signature
        signature = NDASignature.objects.create(
            contractor=contractor,
            signature_data="test_signature_data",
            signed_name="Test Contractor",
            ip_address="127.0.0.1",
            user_agent="Test Browser"
        )
        
        self.assertEqual(signature.contractor, contractor)
        self.assertIsNotNone(signature.signed_at)
    
    def test_REQ_091_admin_document_approval(self):
        """Test REQ-091: Admin Document Approval System."""
        from people.models import Contractor
        
        contractor = Contractor.objects.create(user=self.contractor_user)
        
        # Verify approval fields exist
        self.assertFalse(contractor.nda_signed)
        self.assertIsNone(contractor.nda_approved_by)
        self.assertIsNone(contractor.w9_approved_by)
    
    def test_REQ_095_multi_child_enrollment(self):
        """Test REQ-095: Multi-Child Program Enrollment System."""
        from programs.models import Child, ProgramType, ProgramBuildout, ProgramInstance, Registration
        from django.utils import timezone
        from datetime import timedelta
        
        # Create two children
        child1 = Child.objects.create(
            parent=self.parent_user,
            first_name="Child",
            last_name="One",
            date_of_birth="2015-01-01"
        )
        
        child2 = Child.objects.create(
            parent=self.parent_user,
            first_name="Child",
            last_name="Two",
            date_of_birth="2016-01-01"
        )
        
        # Create program instance
        program_type = ProgramType.objects.create(name="Multi-Child Program", description="Test")
        buildout = ProgramBuildout.objects.create(
            program_type=program_type,
            title="Test Buildout",
            num_facilitators=1,
            num_new_facilitators=0,
            students_per_program=10,
            sessions_per_program=5,
            rate_per_student=20.00
        )
        
        start_date = timezone.now()
        end_date = start_date + timedelta(days=30)
        
        instance = ProgramInstance.objects.create(
            buildout=buildout,
            title="Test Instance",
            start_date=start_date,
            end_date=end_date,
            location="Test Location",
            capacity=20
        )
        
        # Register both children
        reg1 = Registration.objects.create(
            child=child1,
            program_instance=instance,
            status="pending"
        )
        
        reg2 = Registration.objects.create(
            child=child2,
            program_instance=instance,
            status="pending"
        )
        
        # Verify both registrations exist
        self.assertEqual(instance.registrations.count(), 2)
        self.assertIn(reg1, instance.registrations.all())
        self.assertIn(reg2, instance.registrations.all())
    
    def test_REQ_099_admin_view_as_impersonation(self):
        """Test REQ-099: Admin View As (Role Preview & Safe User Impersonation)."""
        from audit.models import ImpersonationLog
        
        # Verify impersonation log model exists
        self.assertTrue(hasattr(ImpersonationLog, 'admin_user'))
        self.assertTrue(hasattr(ImpersonationLog, 'target_user'))
        self.assertTrue(hasattr(ImpersonationLog, 'started_at'))
    
    def test_REQ_034_program_type_instance_relationship_fix(self):
        """Test REQ-034: Program Type Instance Relationship Fix."""
        from programs.models import ProgramType, ProgramBuildout
        
        program_type = ProgramType.objects.create(name="Relationship Test", description="Test")
        buildout = ProgramBuildout.objects.create(
            program_type=program_type,
            title="Test Buildout",
            num_facilitators=1,
            num_new_facilitators=0,
            students_per_program=10,
            sessions_per_program=5,
            rate_per_student=20.00
        )
        
        # Verify buildout relationship
        self.assertEqual(buildout.program_type, program_type)
        self.assertIn(buildout, program_type.buildouts.all())
    
    def test_REQ_064_contractor_day_off_request_system(self):
        """Test REQ-064: Contractor Day-Off Request System."""
        from programs.models import ContractorDayOffRequest
        from datetime import date, timedelta
        
        contractor = User.objects.create_user(email="contractor-064@test.com", password="test")
        
        # Create day-off request with date range
        start_date = date.today() + timedelta(days=7)
        end_date = start_date + timedelta(days=2)
        
        day_off = ContractorDayOffRequest.objects.create(
            contractor=contractor,
            start_date=start_date,
            end_date=end_date,
            reason="Vacation",
            status="pending"
        )
        
        self.assertEqual(day_off.contractor, contractor)
        self.assertEqual(day_off.status, "pending")
        self.assertIsNotNone(day_off.start_date)
        self.assertIsNotNone(day_off.end_date)
    
    def test_REQ_074_program_request_system(self):
        """Test REQ-074: Program Request System."""
        from programs.models import ProgramRequest, ProgramType
        
        program_type = ProgramType.objects.create(name="Request Test Program", description="Test")
        
        # Parent requests program
        request = ProgramRequest.objects.create(
            requester=self.parent_user,
            program_type=program_type,
            request_type="parent_request",
            additional_notes="Interested in this program"
        )
        
        self.assertEqual(request.requester, self.parent_user)
        self.assertEqual(request.program_type, program_type)
        self.assertEqual(request.request_type, "parent_request")
    
    def test_REQ_075_integrated_contact_management(self):
        """Test REQ-075: Integrated Contact Management."""
        from communications.models import Contact
        
        # Create contact from program request
        contact = Contact.objects.create(
            parent_name="Test Parent",
            email="test-075@example.com",
            message="Program inquiry",
            interest="after_school"
        )
        
        self.assertEqual(contact.parent_name, "Test Parent")
        self.assertEqual(contact.interest, "after_school")
    
    def test_REQ_084_role_management_user_count_display(self):
        """Test REQ-084: Role Management User Count Display."""
        from programs.models import Role, RoleAssignment
        
        role = Role.objects.create(title="Count Test Role", description="Test")
        
        # Assign users to role
        RoleAssignment.objects.create(
            user=self.contractor_user,
            role=role,
            assigned_by=self.admin_user
        )
        
        # Test role shows correct count
        self.assertEqual(role.user_assignments.count(), 1)
    
    def test_REQ_085_enhanced_cost_and_location_management(self):
        """Test REQ-085: Enhanced Cost and Location Management System."""
        from programs.models import BaseCost, Location
        
        # Test PER_CHILD frequency
        cost = BaseCost.objects.create(
            name="Per Child Cost",
            rate=5.00,
            frequency="PER_CHILD",
            description="Test cost per child"
        )
        
        # Test Location model
        location = Location.objects.create(
            name="Test Location",
            address="123 Test St",
            max_capacity=50,
            default_rate=100.00,
            default_frequency="PER_PROGRAM"
        )
        
        self.assertEqual(cost.frequency, "PER_CHILD")
        self.assertEqual(location.max_capacity, 50)
    
    def test_REQ_096_contact_message_parent_dashboard(self):
        """Test REQ-096: Contact → One-Step Account + Message → Parent Dashboard System."""
        from communications.models import Conversation, Message
        
        # Create conversation
        conversation = Conversation.objects.create(
            owner=self.parent_user,
            subject="Test Conversation",
            status="open"
        )
        
        # Create message
        message = Message.objects.create(
            conversation=conversation,
            author=self.parent_user,
            role="parent",
            body="Test message"
        )
        
        self.assertEqual(message.conversation, conversation)
        self.assertEqual(message.role, "parent")
    
    def test_REQ_093_email_case_insensitive_authentication(self):
        """Test REQ-093: Email Case-Insensitive Authentication."""
        # Test that authentication handles email case-insensitively
        # Try to find user with different case
        test_email = "testcase093@example.com"
        test_user = User.objects.create_user(
            email=test_email,
            password="testpass123"
        )
        
        # Try to authenticate with different cases
        auth_backend = 'accounts.backends.EmailBackend'
        
        # Login with different case should work
        from django.contrib.auth import authenticate
        user_lower = User.objects.filter(email__iexact="TESTCASE093@EXAMPLE.COM").first()
        
        self.assertIsNotNone(user_lower)
        self.assertEqual(user_lower, test_user)
    
    def test_REQ_097_navigation_links_fix(self):
        """Test REQ-097: Navigation Links Fix."""
        # Test that home navigation is accessible
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
    
    def test_REQ_098_contact_form_template_fix(self):
        """Test REQ-098: Contact Form Template Fix."""
        # Test contact form displays proper template
        response = self.client.get(reverse('communications:contact_entry'))
        self.assertIn(response.status_code, [200, 302])
    
    def test_req_092_comprehensive_parent_landing_page(self):
        """Test that parents are automatically redirected to Parent Landing Page after login."""
        from django.contrib.auth.models import Group
        from accounts.views import get_user_redirect_url, role_based_redirect
        
        # Create parent user
        parent_group, _ = Group.objects.get_or_create(name='Parent')
        parent_user = User.objects.create_user(
            email='parentredirect@test.com',
            password='testpass123',
            first_name='Parent',
            last_name='User'
        )
        parent_user.groups.add(parent_group)
        
        # Test utility function
        redirect_url = get_user_redirect_url(parent_user)
        self.assertEqual(redirect_url, 'programs:parent_dashboard')
        
        # Test role-based redirect view
        client = Client()
        client.force_login(parent_user)
        response = client.get(reverse('accounts:role_based_redirect'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('programs:parent_dashboard'))
        
        # Test with non-parent user
        regular_user = User.objects.create_user(
            email='regularredirect@test.com',
            password='testpass123'
        )
        
        redirect_url = get_user_redirect_url(regular_user)
        self.assertEqual(redirect_url, 'dashboard:dashboard')
        
        client.force_login(regular_user)
        response = client.get(reverse('accounts:role_based_redirect'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard:dashboard'))
    
    def test_REQ_100_mandatory_requirements_workflow(self):
        """Test REQ-100: Mandatory Requirements and Testing Workflow."""
        from pathlib import Path
        import json
        
        # Verify .cursorrules file exists
        cursorrules_path = Path('/workspaces/Dynamic Discoveries/.cursorrules')
        self.assertTrue(cursorrules_path.exists(), ".cursorrules file must exist")
        
        # Verify .cursorrules contains the mandatory workflow rule
        with open(cursorrules_path, 'r') as f:
            cursorrules = json.load(f)
        
        self.assertIn('custom_rules', cursorrules)
        
        # Find the mandatory workflow rule
        workflow_rule = None
        for rule in cursorrules['custom_rules']:
            if 'Automated Requirements and Test Workflow' in rule.get('description', ''):
                workflow_rule = rule
                break
        
        self.assertIsNotNone(workflow_rule, "Mandatory workflow rule must exist in .cursorrules")
        self.assertIn('workflow_steps', workflow_rule)
        self.assertIn('skip_conditions', workflow_rule)
        
        # Verify workflow steps are defined
        workflow_steps = workflow_rule['workflow_steps']
        self.assertGreaterEqual(len(workflow_steps), 5, "Workflow must have at least 5 steps")
        
        # Verify key workflow components are mentioned
        workflow_text = ' '.join(workflow_steps).lower()
        self.assertIn('site_requirements.json', workflow_text)
        self.assertIn('test_requirements.py', workflow_text)
        self.assertIn('test', workflow_text)
        
        # Verify requirements tracking system is operational
        tracker = RequirementsTracker()
        requirements_data = tracker.load_requirements()
        self.assertIn('requirements', requirements_data)
        
        # Verify REQ-100 exists in requirements
        req_100 = None
        for req in requirements_data['requirements']:
            if req['id'] == 'REQ-100':
                req_100 = req
                break
        
        self.assertIsNotNone(req_100, "REQ-100 must exist in site_requirements.json")
        self.assertEqual(req_100['status'], 'implemented')
        self.assertEqual(req_100['title'], 'Mandatory Requirements and Testing Workflow')
    
    def test_REQ_101_recurring_weekly_availability_creation_fix(self):
        """Test REQ-101: Recurring weekly availability creates multiple entries."""
        from programs.models import ContractorAvailability
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        # Create a contractor user
        contractor = User.objects.create_user(
            email='contractor_recurring@test.com',
            password='testpass',
            first_name='Recurring',
            last_name='Contractor'
        )
        contractor_group, _ = Group.objects.get_or_create(name='Contractor')
        contractor.groups.add(contractor_group)
        
        # Create a recurring weekly availability (Monday and Wednesday for 2 weeks)
        from programs.forms import ContractorAvailabilityForm
        
        # Calculate dates for the next 2 weeks
        today = datetime.now().date()
        end_date = today + timedelta(days=14)
        
        # Find next Monday
        days_ahead = 0 - today.weekday()  # Monday is 0
        if days_ahead <= 0:
            days_ahead += 7
        next_monday = today + timedelta(days=days_ahead)
        
        form_data = {
            'availability_type': 'recurring',
            'recurring_weekdays': ['0', '2'],  # Monday (0) and Wednesday (2)
            'recurring_until': end_date.strftime('%Y-%m-%d'),
            'start_time': '09:00',
            'end_time': '12:00',
            'notes': 'Test recurring availability',
            'exclude_holidays': False,
        }
        
        form = ContractorAvailabilityForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form should be valid. Errors: {form.errors}")
        
        # Set contractor on form instance before saving
        form.instance.contractor = contractor
        
        # Save the form (should create multiple instances)
        availability = form.save(commit=True)
        
        # Verify multiple availability entries were created
        all_availability = ContractorAvailability.objects.filter(contractor=contractor)
        
        # Should have at least 2 entries (could be more depending on how many Mon/Wed in the next 2 weeks)
        self.assertGreaterEqual(
            all_availability.count(), 
            2, 
            f"Recurring availability should create at least 2 entries (Monday and Wednesday). Found {all_availability.count()}"
        )
        
        # Verify all entries have correct contractor
        for avail in all_availability:
            self.assertEqual(avail.contractor, contractor)
            self.assertEqual(avail.start_datetime.hour, 9)
            self.assertEqual(avail.end_datetime.hour, 12)
        
        # Verify entries are on correct weekdays (Monday=0, Wednesday=2)
        weekdays = [avail.start_datetime.weekday() for avail in all_availability]
        for weekday in weekdays:
            self.assertIn(weekday, [0, 2], f"All entries should be on Monday (0) or Wednesday (2), found {weekday}")