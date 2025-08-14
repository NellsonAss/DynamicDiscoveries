from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import (
    ProgramType, Role, Responsibility, ProgramBuildout, 
    BuildoutResponsibilityAssignment, BuildoutRoleAssignment, RegistrationForm, 
    Child, Registration, ProgramInstance, BaseCost
)
from decimal import Decimal

User = get_user_model()


class RoleModelTest(TestCase):
    def setUp(self):
        self.role = Role.objects.create(
            title="Test Facilitator",
            description="Test responsibilities",
            default_responsibilities="Session facilitation, planning"
        )

    def test_role_creation(self):
        self.assertEqual(self.role.title, "Test Facilitator")
        self.assertEqual(self.role.description, "Test responsibilities")
        self.assertEqual(str(self.role), "Test Facilitator")


class ResponsibilityModelTest(TestCase):
    def setUp(self):
        self.role = Role.objects.create(
            title="Test Facilitator",
            description="Test responsibilities"
        )

    def test_responsibility_creation(self):
        responsibility = Responsibility.objects.create(
            role=self.role,
            name="Session Facilitation",
            description="Facilitate sessions",
            frequency_type="PER_SESSION",
            hours=Decimal('2.0')
        )
        self.assertEqual(responsibility.role.title, "Test Facilitator")
        self.assertEqual(responsibility.frequency_type, "PER_SESSION")
        self.assertEqual(str(responsibility), "Test Facilitator - Session Facilitation")


class ProgramTypeModelTest(TestCase):
    def setUp(self):
        self.program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test description"
        )

    def test_program_type_creation(self):
        self.assertEqual(self.program_type.name, "Test Program")
        self.assertEqual(self.program_type.description, "Test description")
        self.assertEqual(str(self.program_type), "Test Program")


class ProgramBuildoutModelTest(TestCase):
    def setUp(self):
        self.program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test description"
        )
        self.buildout = ProgramBuildout.objects.create(
            program_type=self.program_type,
            title="Test Buildout",
            num_facilitators=2,
            num_new_facilitators=1,
            students_per_workshop=12,
            sessions_per_workshop=8,
            rate_per_student=Decimal('100.00')
        )

    def test_buildout_creation(self):
        self.assertEqual(self.buildout.title, "Test Buildout")
        self.assertEqual(self.buildout.num_facilitators, 2)
        self.assertEqual(self.buildout.num_workshops_per_year, 8)  # 2 * 4
        self.assertEqual(str(self.buildout), "Test Buildout v1 (Test Program)")

    def test_buildout_calculations(self):
        self.assertEqual(self.buildout.total_students_per_year, 96)  # 8 * 12
        self.assertEqual(self.buildout.total_sessions_per_year, 64)  # 8 * 8
        self.assertEqual(self.buildout.total_revenue_per_year, Decimal('9600.00'))  # 96 * 100


class BuildoutResponsibilityAssignmentModelTest(TestCase):
    def setUp(self):
        self.program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test description"
        )
        self.buildout = ProgramBuildout.objects.create(
            program_type=self.program_type,
            title="Test Buildout",
            num_facilitators=2,
            num_new_facilitators=1,
            students_per_workshop=12,
            sessions_per_workshop=8,
            rate_per_student=Decimal('100.00')
        )
        self.role = Role.objects.create(
            title="Test Facilitator",
            description="Test responsibilities"
        )
        self.responsibility = Responsibility.objects.create(
            role=self.role,
            name="Session Facilitation",
            description="Facilitate sessions",
            frequency_type="PER_SESSION",
            hours=Decimal('2.0')
        )

    def test_responsibility_assignment_creation(self):
        assignment = BuildoutResponsibilityAssignment.objects.create(
            buildout=self.buildout,
            responsibility=self.responsibility
        )
        self.assertEqual(assignment.buildout.title, "Test Buildout")
        self.assertEqual(assignment.responsibility.name, "Session Facilitation")

    def test_calculate_yearly_hours(self):
        assignment = BuildoutResponsibilityAssignment.objects.create(
            buildout=self.buildout,
            responsibility=self.responsibility
        )
        # 64 sessions per year * 2 hours per session = 128 hours
        expected_hours = Decimal('2.0') * 64
        self.assertEqual(assignment.calculate_yearly_hours(), expected_hours)


class BuildoutRoleAssignmentModelTest(TestCase):
    def setUp(self):
        self.program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test description"
        )
        self.buildout = ProgramBuildout.objects.create(
            program_type=self.program_type,
            title="Test Buildout",
            num_facilitators=2,
            num_new_facilitators=1,
            students_per_workshop=12,
            sessions_per_workshop=8,
            rate_per_student=Decimal('100.00')
        )
        self.role = Role.objects.create(
            title="Test Facilitator",
            description="Test responsibilities"
        )

    def test_role_assignment_creation(self):
        role_assignment = BuildoutRoleAssignment.objects.create(
            buildout=self.buildout,
            role=self.role
        )
        self.assertEqual(role_assignment.role.title, "Test Facilitator")
        self.assertEqual(str(role_assignment), "Test Facilitator - Test Buildout")


class BaseCostModelTest(TestCase):
    def setUp(self):
        self.base_cost = BaseCost.objects.create(
            name="Test Cost",
            description="Test cost description",
            rate=Decimal('50.00'),
            frequency="PER_WORKSHOP"
        )

    def test_base_cost_creation(self):
        self.assertEqual(self.base_cost.name, "Test Cost")
        self.assertEqual(self.base_cost.rate, Decimal('50.00'))
        self.assertEqual(str(self.base_cost), "Test Cost")


class ProgramBuildoutIntegrationTest(TestCase):
    def setUp(self):
        self.program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test description"
        )
        self.role = Role.objects.create(
            title="Test Facilitator",
            description="Test responsibilities"
        )
        self.responsibility = Responsibility.objects.create(
            role=self.role,
            name="Session Facilitation",
            description="Facilitate sessions",
            frequency_type="PER_SESSION",
            hours=Decimal('2.0')
        )
        self.buildout = ProgramBuildout.objects.create(
            program_type=self.program_type,
            title="Test Buildout",
            num_facilitators=2,
            num_new_facilitators=1,
            students_per_workshop=12,
            sessions_per_workshop=8,
            rate_per_student=Decimal('100.00')
        )

    def test_buildout_with_responsibilities(self):
        # Add role assignment
        BuildoutRoleAssignment.objects.create(
            buildout=self.buildout,
            role=self.role
        )
        
        # Add responsibility assignment
        BuildoutResponsibilityAssignment.objects.create(
            buildout=self.buildout,
            responsibility=self.responsibility
        )
        
        # Test calculations
        self.assertEqual(self.buildout.calculate_total_hours_per_role(self.role), Decimal('128.0'))
        self.assertEqual(self.buildout.calculate_payout_per_role(self.role), Decimal('6400.0'))  # 128 * 50
        # Test with rounded value to handle decimal precision
        percent = self.buildout.calculate_percent_of_revenue_per_role(self.role)
        self.assertAlmostEqual(percent, Decimal('66.67'), places=1)


class RegistrationFormModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123"
        )
        self.form = RegistrationForm.objects.create(
            title="Test Form",
            description="Test form description",
            created_by=self.user
        )

    def test_form_creation(self):
        self.assertEqual(self.form.title, "Test Form")
        self.assertEqual(self.form.created_by, self.user)
        self.assertEqual(str(self.form), "Test Form")


class ChildModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="parent@example.com",
            password="testpass123"
        )
        self.child = Child.objects.create(
            parent=self.user,
            first_name="Test",
            last_name="Child",
            date_of_birth="2015-01-01",
            grade_level="3rd Grade"
        )

    def test_child_creation(self):
        self.assertEqual(self.child.first_name, "Test")
        self.assertEqual(self.child.last_name, "Child")
        self.assertEqual(self.child.full_name, "Test Child")
        self.assertEqual(str(self.child), "Test Child")


class ProgramInstanceModelTest(TestCase):
    def setUp(self):
        self.program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test description"
        )
        self.buildout = ProgramBuildout.objects.create(
            program_type=self.program_type,
            title="Test Buildout",
            num_facilitators=2,
            num_new_facilitators=1,
            students_per_workshop=12,
            sessions_per_workshop=8,
            rate_per_student=Decimal('100.00')
        )
        self.instance = ProgramInstance.objects.create(
            buildout=self.buildout,
            title="Test Instance",
            start_date="2024-01-01T09:00:00Z",
            end_date="2024-01-01T17:00:00Z",
            location="Test Location",
            capacity=20
        )

    def test_instance_creation(self):
        self.assertEqual(self.instance.title, "Test Instance")
        self.assertEqual(self.instance.capacity, 20)
        self.assertEqual(self.instance.available_spots, 20)  # No registrations yet
