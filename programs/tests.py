from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import (
    ProgramType, Role, ProgramBuildout, BuildoutResponsibility, 
    BuildoutRoleAssignment, RegistrationForm, Child, Registration, ProgramInstance
)
from decimal import Decimal

User = get_user_model()


class RoleModelTest(TestCase):
    def setUp(self):
        self.role = Role.objects.create(
            name="Test Facilitator",
            hourly_rate=Decimal('25.00'),
            description="Test responsibilities"
        )

    def test_role_creation(self):
        self.assertEqual(self.role.name, "Test Facilitator")
        self.assertEqual(self.role.hourly_rate, Decimal('25.00'))
        self.assertEqual(str(self.role), "Test Facilitator")


class ProgramBuildoutModelTest(TestCase):
    def setUp(self):
        self.program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test description",
            scope="Test scope",
            target_grade_levels="K-2",
            rate_per_student=Decimal('100.00')
        )
        self.buildout = ProgramBuildout.objects.create(
            program_type=self.program_type,
            title="Test Buildout",
            num_facilitators=2,
            num_new_facilitators=1,
            workshops_per_facilitator_per_year=4,
            students_per_workshop=12,
            sessions_per_workshop=8,
            new_workshop_concepts_per_year=1
        )

    def test_buildout_creation(self):
        self.assertEqual(self.buildout.title, "Test Buildout")
        self.assertEqual(self.buildout.num_facilitators, 2)
        self.assertEqual(self.buildout.num_workshops_per_year, 8)  # 2 * 4
        self.assertEqual(str(self.buildout), "Test Buildout (Test Program)")

    def test_buildout_calculations(self):
        self.assertEqual(self.buildout.total_students_per_year, 96)  # 8 * 12
        self.assertEqual(self.buildout.total_sessions_per_year, 64)  # 8 * 8
        self.assertEqual(self.buildout.total_revenue_per_year, Decimal('9600.00'))  # 96 * 100


class BuildoutResponsibilityModelTest(TestCase):
    def setUp(self):
        self.program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test description",
            scope="Test scope",
            target_grade_levels="K-2",
            rate_per_student=Decimal('100.00')
        )
        self.buildout = ProgramBuildout.objects.create(
            program_type=self.program_type,
            title="Test Buildout",
            num_facilitators=2,
            num_new_facilitators=1,
            workshops_per_facilitator_per_year=4,
            students_per_workshop=12,
            sessions_per_workshop=8,
            new_workshop_concepts_per_year=1
        )
        self.role = Role.objects.create(
            name="Test Facilitator",
            hourly_rate=Decimal('25.00'),
            description="Test responsibilities"
        )

    def test_responsibility_creation(self):
        responsibility = BuildoutResponsibility.objects.create(
            buildout=self.buildout,
            role=self.role,
            name="Session Facilitation",
            frequency="PER_SESSION",
            base_hours=Decimal('2.0')
        )
        self.assertEqual(responsibility.role.name, "Test Facilitator")
        self.assertEqual(responsibility.frequency, "PER_SESSION")

    def test_calculate_yearly_hours_per_workshop(self):
        responsibility = BuildoutResponsibility.objects.create(
            buildout=self.buildout,
            role=self.role,
            name="Workshop Planning",
            frequency="PER_WORKSHOP",
            base_hours=Decimal('4.0')
        )
        # 8 workshops per year * 4 hours per workshop = 32 hours
        expected_hours = Decimal('4.0') * 8
        self.assertEqual(responsibility.calculate_yearly_hours(), expected_hours)

    def test_calculate_yearly_hours_per_session(self):
        responsibility = BuildoutResponsibility.objects.create(
            buildout=self.buildout,
            role=self.role,
            name="Session Facilitation",
            frequency="PER_SESSION",
            base_hours=Decimal('2.0')
        )
        # 64 sessions per year * 2 hours per session = 128 hours
        expected_hours = Decimal('2.0') * 64
        self.assertEqual(responsibility.calculate_yearly_hours(), expected_hours)

    def test_calculate_yearly_hours_per_new_facilitator(self):
        responsibility = BuildoutResponsibility.objects.create(
            buildout=self.buildout,
            role=self.role,
            name="New Facilitator Training",
            frequency="PER_NEW_FACILITATOR",
            base_hours=Decimal('8.0')
        )
        # 1 new facilitator * 8 hours per new facilitator = 8 hours
        expected_hours = Decimal('8.0') * 1
        self.assertEqual(responsibility.calculate_yearly_hours(), expected_hours)

    def test_calculate_yearly_hours_per_workshop_concept(self):
        responsibility = BuildoutResponsibility.objects.create(
            buildout=self.buildout,
            role=self.role,
            name="Concept Development",
            frequency="PER_WORKSHOP_CONCEPT",
            base_hours=Decimal('10.0')
        )
        # 1 new concept per year * 10 hours per concept = 10 hours
        expected_hours = Decimal('10.0') * 1
        self.assertEqual(responsibility.calculate_yearly_hours(), expected_hours)

    def test_calculate_yearly_hours_override(self):
        responsibility = BuildoutResponsibility.objects.create(
            buildout=self.buildout,
            role=self.role,
            name="Manual Override",
            frequency="OVERRIDE",
            base_hours=Decimal('2.0'),
            override_hours=Decimal('15.0')
        )
        self.assertEqual(responsibility.calculate_yearly_hours(), Decimal('15.0'))

    def test_calculate_yearly_hours_admin_flat(self):
        responsibility = BuildoutResponsibility.objects.create(
            buildout=self.buildout,
            role=self.role,
            name="Admin Support",
            frequency="ADMIN_FLAT",
            base_hours=Decimal('5.0')
        )
        self.assertEqual(responsibility.calculate_yearly_hours(), Decimal('5.0'))

    def test_calculate_yearly_cost(self):
        responsibility = BuildoutResponsibility.objects.create(
            buildout=self.buildout,
            role=self.role,
            name="Session Facilitation",
            frequency="PER_SESSION",
            base_hours=Decimal('2.0')
        )
        # 128 hours * $25/hour = $3200
        expected_cost = Decimal('2.0') * 64 * Decimal('25.00')
        self.assertEqual(responsibility.calculate_yearly_cost(), expected_cost)


class BuildoutRoleAssignmentModelTest(TestCase):
    def setUp(self):
        self.program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test description",
            scope="Test scope",
            target_grade_levels="K-2",
            rate_per_student=Decimal('100.00')
        )
        self.buildout = ProgramBuildout.objects.create(
            program_type=self.program_type,
            title="Test Buildout",
            num_facilitators=2,
            num_new_facilitators=1,
            workshops_per_facilitator_per_year=4,
            students_per_workshop=12,
            sessions_per_workshop=8,
            new_workshop_concepts_per_year=1
        )
        self.role = Role.objects.create(
            name="Test Facilitator",
            hourly_rate=Decimal('25.00'),
            description="Test responsibilities"
        )

    def test_role_assignment_creation(self):
        role_assignment = BuildoutRoleAssignment.objects.create(
            buildout=self.buildout,
            role=self.role,
            percent_of_revenue=Decimal('25.00')
        )
        self.assertEqual(role_assignment.role.name, "Test Facilitator")
        self.assertEqual(role_assignment.percent_of_revenue, Decimal('25.00'))

    def test_calculate_yearly_hours(self):
        # Create a responsibility for this role
        BuildoutResponsibility.objects.create(
            buildout=self.buildout,
            role=self.role,
            name="Session Facilitation",
            frequency="PER_SESSION",
            base_hours=Decimal('2.0')
        )
        
        role_assignment = BuildoutRoleAssignment.objects.create(
            buildout=self.buildout,
            role=self.role,
            percent_of_revenue=Decimal('25.00')
        )
        
        # Should calculate total hours from all responsibilities for this role
        expected_hours = Decimal('2.0') * 64  # 64 sessions * 2 hours
        self.assertEqual(role_assignment.calculate_yearly_hours(), expected_hours)

    def test_calculate_yearly_cost(self):
        # Create a responsibility for this role
        BuildoutResponsibility.objects.create(
            buildout=self.buildout,
            role=self.role,
            name="Session Facilitation",
            frequency="PER_SESSION",
            base_hours=Decimal('2.0')
        )
        
        role_assignment = BuildoutRoleAssignment.objects.create(
            buildout=self.buildout,
            role=self.role,
            percent_of_revenue=Decimal('25.00')
        )
        
        # Should calculate total cost from all responsibilities for this role
        expected_cost = Decimal('2.0') * 64 * Decimal('25.00')  # 128 hours * $25/hour
        self.assertEqual(role_assignment.calculate_yearly_cost(), expected_cost)

    def test_calculate_percent_of_revenue(self):
        # Create a responsibility for this role
        BuildoutResponsibility.objects.create(
            buildout=self.buildout,
            role=self.role,
            name="Session Facilitation",
            frequency="PER_SESSION",
            base_hours=Decimal('2.0')
        )
        
        role_assignment = BuildoutRoleAssignment.objects.create(
            buildout=self.buildout,
            role=self.role,
            percent_of_revenue=Decimal('25.00')
        )
        
        # Calculate actual percentage based on cost vs revenue
        cost = role_assignment.calculate_yearly_cost()
        revenue = self.buildout.total_revenue_per_year
        expected_percentage = (cost / revenue) * 100
        self.assertEqual(role_assignment.calculate_percent_of_revenue(), expected_percentage)


class ProgramBuildoutIntegrationTest(TestCase):
    def setUp(self):
        self.program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test description",
            scope="Test scope",
            target_grade_levels="K-2",
            rate_per_student=Decimal('100.00')
        )
        self.buildout = ProgramBuildout.objects.create(
            program_type=self.program_type,
            title="Test Buildout",
            num_facilitators=2,
            num_new_facilitators=1,
            workshops_per_facilitator_per_year=4,
            students_per_workshop=12,
            sessions_per_workshop=8,
            new_workshop_concepts_per_year=1
        )
        
        # Create roles
        self.facilitator_role = Role.objects.create(
            name="Facilitator",
            hourly_rate=Decimal('25.00'),
            description="Test responsibilities"
        )
        self.admin_role = Role.objects.create(
            name="Admin Support",
            hourly_rate=Decimal('30.00'),
            description="Test responsibilities"
        )

    def test_buildout_financial_calculations(self):
        # Add responsibilities
        BuildoutResponsibility.objects.create(
            buildout=self.buildout,
            role=self.facilitator_role,
            name="Session Facilitation",
            frequency="PER_SESSION",
            base_hours=Decimal('2.0')
        )
        BuildoutResponsibility.objects.create(
            buildout=self.buildout,
            role=self.admin_role,
            name="Admin Support",
            frequency="PER_YEAR",
            base_hours=Decimal('40.0')
        )
        
        # Add role assignments
        BuildoutRoleAssignment.objects.create(
            buildout=self.buildout,
            role=self.facilitator_role,
            percent_of_revenue=Decimal('80.00')
        )
        BuildoutRoleAssignment.objects.create(
            buildout=self.buildout,
            role=self.admin_role,
            percent_of_revenue=Decimal('20.00')
        )
        
        # Test calculations
        self.assertEqual(self.buildout.total_revenue_per_year, Decimal('9600.00'))
        self.assertGreater(self.buildout.total_yearly_costs, Decimal('0.00'))
        self.assertGreater(self.buildout.yearly_profit, Decimal('0.00'))
        self.assertGreater(self.buildout.profit_margin, Decimal('0.00'))
