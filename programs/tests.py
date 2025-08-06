from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import (
    ProgramType, Role, ProgramBuildout, ProgramRole,
    RegistrationForm, Child, Registration, ProgramInstance
)
from decimal import Decimal

User = get_user_model()


class RoleModelTest(TestCase):
    def setUp(self):
        self.role = Role.objects.create(
            name="Test Facilitator",
            default_percent_of_revenue=Decimal('25.00'),
            responsibilities="Test responsibilities"
        )

    def test_role_creation(self):
        self.assertEqual(self.role.name, "Test Facilitator")
        self.assertEqual(self.role.default_percent_of_revenue, Decimal('25.00'))
        self.assertEqual(str(self.role), "Test Facilitator")


class ProgramBuildoutModelTest(TestCase):
    def setUp(self):
        self.program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test description",
            target_grade_levels="K-2"
        )
        self.buildout = ProgramBuildout.objects.create(
            program_type=self.program_type,
            title="Test Buildout",
            expected_students=12,
            num_days=4,
            sessions_per_day=1,
            total_expected_revenue=Decimal('1600.00')
        )

    def test_buildout_creation(self):
        self.assertEqual(self.buildout.title, "Test Buildout")
        self.assertEqual(self.buildout.expected_students, 12)
        self.assertEqual(self.buildout.num_days, 4)
        self.assertEqual(str(self.buildout), "Test Buildout (Test Program)")

    def test_get_total_role_percentage_empty(self):
        self.assertEqual(self.buildout.get_total_role_percentage(), 0)

    def test_is_percentage_valid_empty(self):
        self.assertFalse(self.buildout.is_percentage_valid())


class ProgramRoleModelTest(TestCase):
    def setUp(self):
        self.program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test description",
            target_grade_levels="K-2"
        )
        self.buildout = ProgramBuildout.objects.create(
            program_type=self.program_type,
            title="Test Buildout",
            expected_students=12,
            num_days=4,
            sessions_per_day=1,
            total_expected_revenue=Decimal('1600.00')
        )
        self.role = Role.objects.create(
            name="Test Facilitator",
            default_percent_of_revenue=Decimal('25.00'),
            responsibilities="Test responsibilities"
        )

    def test_program_role_creation(self):
        program_role = ProgramRole.objects.create(
            buildout=self.buildout,
            role=self.role,
            percent_of_revenue=Decimal('25.00'),
            hour_frequency="PER_SESSION",
            hour_multiplier=Decimal('2.0')
        )
        self.assertEqual(program_role.role.name, "Test Facilitator")
        self.assertEqual(program_role.percent_of_revenue, Decimal('25.00'))

    def test_calculate_total_hours_per_program(self):
        program_role = ProgramRole.objects.create(
            buildout=self.buildout,
            role=self.role,
            percent_of_revenue=Decimal('25.00'),
            hour_frequency="PER_PROGRAM",
            hour_multiplier=Decimal('8.0')
        )
        self.assertEqual(program_role.calculate_total_hours(), Decimal('8.0'))

    def test_calculate_total_hours_per_session(self):
        program_role = ProgramRole.objects.create(
            buildout=self.buildout,
            role=self.role,
            percent_of_revenue=Decimal('25.00'),
            hour_frequency="PER_SESSION",
            hour_multiplier=Decimal('2.0')
        )
        # 4 days * 1 session per day = 4 sessions
        expected_hours = Decimal('2.0') * 4
        self.assertEqual(program_role.calculate_total_hours(), expected_hours)

    def test_calculate_total_hours_per_kid(self):
        program_role = ProgramRole.objects.create(
            buildout=self.buildout,
            role=self.role,
            percent_of_revenue=Decimal('25.00'),
            hour_frequency="PER_KID",
            hour_multiplier=Decimal('0.5')
        )
        # 12 students * 0.5 hours per kid = 6 hours
        expected_hours = Decimal('0.5') * 12
        self.assertEqual(program_role.calculate_total_hours(), expected_hours)

    def test_calculate_total_hours_per_session_per_kid(self):
        program_role = ProgramRole.objects.create(
            buildout=self.buildout,
            role=self.role,
            percent_of_revenue=Decimal('25.00'),
            hour_frequency="PER_SESSION_PER_KID",
            hour_multiplier=Decimal('0.25')
        )
        # 12 students * 4 sessions * 0.25 hours = 12 hours
        expected_hours = Decimal('0.25') * 12 * 4
        self.assertEqual(program_role.calculate_total_hours(), expected_hours)

    def test_calculate_total_hours_override(self):
        program_role = ProgramRole.objects.create(
            buildout=self.buildout,
            role=self.role,
            percent_of_revenue=Decimal('25.00'),
            hour_frequency="OVERRIDE",
            hour_multiplier=Decimal('2.0'),
            override_hours=Decimal('10.0')
        )
        self.assertEqual(program_role.calculate_total_hours(), Decimal('10.0'))

    def test_calculate_total_hours_admin_flat(self):
        program_role = ProgramRole.objects.create(
            buildout=self.buildout,
            role=self.role,
            percent_of_revenue=Decimal('25.00'),
            hour_frequency="ADMIN_FLAT",
            hour_multiplier=Decimal('5.0')
        )
        self.assertEqual(program_role.calculate_total_hours(), Decimal('5.0'))


class ProgramBuildoutIntegrationTest(TestCase):
    def setUp(self):
        self.program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test description",
            target_grade_levels="K-2"
        )
        self.buildout = ProgramBuildout.objects.create(
            program_type=self.program_type,
            title="Test Buildout",
            expected_students=12,
            num_days=4,
            sessions_per_day=1,
            total_expected_revenue=Decimal('1600.00')
        )
        
        # Create roles
        self.facilitator_role = Role.objects.create(
            name="Facilitator",
            default_percent_of_revenue=Decimal('24.00'),
            responsibilities="Test responsibilities"
        )
        self.admin_role = Role.objects.create(
            name="Admin Support",
            default_percent_of_revenue=Decimal('10.00'),
            responsibilities="Test responsibilities"
        )

    def test_buildout_percentage_validation(self):
        # Add roles that sum to 100%
        ProgramRole.objects.create(
            buildout=self.buildout,
            role=self.facilitator_role,
            percent_of_revenue=Decimal('90.00'),
            hour_frequency="PER_SESSION",
            hour_multiplier=Decimal('2.0')
        )
        ProgramRole.objects.create(
            buildout=self.buildout,
            role=self.admin_role,
            percent_of_revenue=Decimal('10.00'),
            hour_frequency="PER_PROGRAM",
            hour_multiplier=Decimal('5.0')
        )
        
        self.assertTrue(self.buildout.is_percentage_valid())
        self.assertEqual(self.buildout.get_total_role_percentage(), Decimal('100.00'))

    def test_buildout_percentage_validation_invalid(self):
        # Add roles that don't sum to 100%
        ProgramRole.objects.create(
            buildout=self.buildout,
            role=self.facilitator_role,
            percent_of_revenue=Decimal('50.00'),
            hour_frequency="PER_SESSION",
            hour_multiplier=Decimal('2.0')
        )
        ProgramRole.objects.create(
            buildout=self.buildout,
            role=self.admin_role,
            percent_of_revenue=Decimal('10.00'),
            hour_frequency="PER_PROGRAM",
            hour_multiplier=Decimal('5.0')
        )
        
        self.assertFalse(self.buildout.is_percentage_valid())
        self.assertEqual(self.buildout.get_total_role_percentage(), Decimal('60.00'))
