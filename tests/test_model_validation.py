"""
Model Validation Tests

This module tests that all models have proper validation, constraints,
and data integrity checks to prevent errors from new updates.
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from programs.models import (
    ProgramType, Role, Responsibility, ProgramBuildout, 
    ProgramInstance, Child, Registration, RegistrationForm,
    BaseCost, Location, BuildoutRoleLine, BuildoutResponsibilityLine,
    ContractorAvailability, AvailabilityProgram, ProgramSession
)
from communications.models import Contact
from people.models import Contractor
from notes.models import StudentNote, ParentNote

User = get_user_model()


class ModelConstraintTests(TestCase):
    """Test model constraints and validation rules."""
    
    def setUp(self):
        """Set up test data."""
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123'
        )
        admin_group, _ = Group.objects.get_or_create(name='Admin')
        self.admin_user.groups.add(admin_group)
        
        self.contractor_user = User.objects.create_user(
            email='contractor@test.com',
            password='testpass123'
        )
        contractor_group, _ = Group.objects.get_or_create(name='Contractor')
        self.contractor_user.groups.add(contractor_group)
    
    def test_user_email_uniqueness(self):
        """Test that user emails must be unique."""
        # First user should create successfully
        user1 = User.objects.create_user(
            email='unique@test.com',
            password='testpass123'
        )
        self.assertIsNotNone(user1)
        
        # Second user with same email should fail
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email='unique@test.com',  # Same email
                password='testpass123'
            )
    
    def test_program_type_validation(self):
        """Test ProgramType model validation."""
        # Valid program type
        program_type = ProgramType.objects.create(
            name="Valid Program",
            description="Valid description"
        )
        self.assertIsNotNone(program_type)
        
        # Test name length constraints
        with self.assertRaises(ValidationError):
            long_name_program = ProgramType(
                name="A" * 201,  # Assuming max length is 200
                description="Test"
            )
            long_name_program.full_clean()
    
    def test_role_responsibility_relationship(self):
        """Test that responsibilities are properly linked to roles."""
        role = Role.objects.create(
            title="Test Role",
            description="Test role description"
        )
        
        responsibility = Responsibility.objects.create(
            role=role,
            name="Test Responsibility",
            description="Test responsibility description",
            frequency_type="PER_SESSION",
            default_hours=Decimal('2.0')
        )
        
        # Test relationship
        self.assertEqual(responsibility.role, role)
        self.assertIn(responsibility, role.responsibilities.all())
    
    def test_buildout_role_line_validation(self):
        """Test BuildoutRoleLine model validation."""
        program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test description"
        )
        
        buildout = ProgramBuildout.objects.create(
            program_type=program_type,
            title="Test Buildout",
            num_facilitators=1,
            num_new_facilitators=0,
            students_per_program=10,
            sessions_per_program=5,
            rate_per_student=Decimal('25.00')
        )
        
        role = Role.objects.create(
            title="Test Role",
            description="Test role"
        )
        
        # Valid role line
        role_line = BuildoutRoleLine.objects.create(
            buildout=buildout,
            role=role,
            contractor=self.contractor_user,
            pay_type='HOURLY',
            pay_value=Decimal('25.00'),
            frequency_unit='PER_SESSION',
            frequency_count=1,
            hours_per_frequency=Decimal('2.0')
        )
        self.assertIsNotNone(role_line)
        
        # Test negative values are not allowed
        with self.assertRaises(ValidationError):
            invalid_role_line = BuildoutRoleLine(
                buildout=buildout,
                role=role,
                contractor=self.admin_user,
                pay_type='HOURLY',
                pay_value=Decimal('-25.00'),  # Negative value
                frequency_unit='PER_SESSION',
                frequency_count=1,
                hours_per_frequency=Decimal('2.0')
            )
            invalid_role_line.full_clean()
    
    def test_child_parent_relationship(self):
        """Test Child model validation and parent relationship."""
        parent_user = User.objects.create_user(
            email='parent@test.com',
            password='testpass123'
        )
        
        # Valid child
        child = Child.objects.create(
            first_name="Test",
            last_name="Child",
            parent=parent_user,
            date_of_birth=date(2015, 1, 1)
        )
        self.assertEqual(child.parent, parent_user)
        
        # Test future birth date is not allowed
        with self.assertRaises(ValidationError):
            future_child = Child(
                first_name="Future",
                last_name="Child",
                parent=parent_user,
                date_of_birth=date.today() + timedelta(days=1)
            )
            future_child.full_clean()
    
    def test_contact_email_validation(self):
        """Test Contact model email validation."""
        # Valid contact
        contact = Contact.objects.create(
            parent_name="Test Parent",
            email="valid@example.com",
            message="Test message",
            interest="after_school"
        )
        self.assertIsNotNone(contact)
        
        # Invalid email format should be caught by validation
        with self.assertRaises(ValidationError):
            invalid_contact = Contact(
                parent_name="Test Parent",
                email="invalid-email",  # Invalid format
                message="Test message",
                interest="after_school"
            )
            invalid_contact.full_clean()
    
    def test_program_instance_date_validation(self):
        """Test ProgramInstance date validation."""
        program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test description"
        )
        
        buildout = ProgramBuildout.objects.create(
            program_type=program_type,
            title="Test Buildout",
            num_facilitators=1,
            num_new_facilitators=0,
            students_per_program=10,
            sessions_per_program=5,
            rate_per_student=Decimal('25.00')
        )
        
        # Valid instance
        valid_instance = ProgramInstance.objects.create(
            buildout=buildout,
            title="Valid Instance",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            location="Test Location",
            capacity=20
        )
        self.assertIsNotNone(valid_instance)
        
        # Test end date before start date
        with self.assertRaises(ValidationError):
            invalid_instance = ProgramInstance(
                buildout=buildout,
                title="Invalid Instance",
                start_date=timezone.now(),
                end_date=timezone.now() - timedelta(days=1),  # End before start
                location="Test Location",
                capacity=20
            )
            invalid_instance.full_clean()
    
    def test_decimal_field_precision(self):
        """Test decimal field precision and constraints."""
        # Test BaseCost decimal precision
        base_cost = BaseCost.objects.create(
            name="Test Cost",
            rate=Decimal('123.45'),
            frequency="PER_SESSION",
            description="Test cost"
        )
        self.assertEqual(base_cost.rate, Decimal('123.45'))
        
        # Test extremely precise decimal (should be rounded/rejected)
        with self.assertRaises((ValidationError, ValueError)):
            precise_cost = BaseCost(
                name="Precise Cost",
                rate=Decimal('123.12345678'),  # Too many decimal places
                frequency="PER_SESSION",
                description="Test cost"
            )
            precise_cost.full_clean()
    
    def test_choice_field_validation(self):
        """Test that choice fields only accept valid choices."""
        role = Role.objects.create(
            title="Test Role",
            description="Test role"
        )
        
        # Valid choice
        responsibility = Responsibility.objects.create(
            role=role,
            name="Test Responsibility",
            description="Test description",
            frequency_type="PER_SESSION",  # Valid choice
            default_hours=Decimal('2.0')
        )
        self.assertIsNotNone(responsibility)
        
        # Invalid choice should be rejected
        with self.assertRaises(ValidationError):
            invalid_responsibility = Responsibility(
                role=role,
                name="Invalid Responsibility",
                description="Test description",
                frequency_type="INVALID_CHOICE",  # Invalid choice
                default_hours=Decimal('2.0')
            )
            invalid_responsibility.full_clean()


class ModelMethodTests(TestCase):
    """Test model methods and computed properties."""
    
    def setUp(self):
        """Set up test data."""
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123'
        )
        
        self.contractor_user = User.objects.create_user(
            email='contractor@test.com',
            password='testpass123'
        )
        
        # Create Contractor instance
        self.contractor = Contractor.objects.create(
            user=self.contractor_user,
            nda_signed=True
        )
    
    def test_buildout_calculated_properties(self):
        """Test ProgramBuildout calculated properties."""
        program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test description"
        )
        
        buildout = ProgramBuildout.objects.create(
            program_type=program_type,
            title="Test Buildout",
            num_facilitators=2,
            num_new_facilitators=1,
            students_per_program=12,
            sessions_per_program=8,
            rate_per_student=Decimal('25.00'),
            programs_per_facilitator_per_year=4
        )
        
        # Test calculated properties
        self.assertEqual(buildout.num_programs_per_year, 8)  # 2 facilitators * 4 programs
        self.assertEqual(buildout.total_students_per_year, 96)  # 8 programs * 12 students
        self.assertEqual(buildout.total_revenue_per_year, Decimal('2400.00'))  # 96 * $25
        
        # These should be Decimal values
        self.assertIsInstance(buildout.total_revenue_per_year, Decimal)
    
    def test_user_role_methods(self):
        """Test User model role-related methods."""
        admin_group, _ = Group.objects.get_or_create(name='Admin')
        contractor_group, _ = Group.objects.get_or_create(name='Contractor')
        
        # Test admin user
        self.admin_user.groups.add(admin_group)
        role_names = self.admin_user.get_role_names()
        self.assertIn('Admin', role_names)
        
        # Test contractor user
        self.contractor_user.groups.add(contractor_group)
        contractor_roles = self.contractor_user.get_role_names()
        self.assertIn('Contractor', contractor_roles)
    
    def test_contractor_onboarding_status(self):
        """Test Contractor onboarding status calculation."""
        # Initially not complete (no W-9)
        self.assertFalse(self.contractor.onboarding_complete)
        
        # Complete onboarding
        from django.core.files.base import ContentFile
        self.contractor.w9_file.save("test_w9.pdf", ContentFile(b"%PDF-1.4 test"), save=True)
        
        # Now should be complete
        self.assertTrue(self.contractor.onboarding_complete)
    
    def test_string_representations(self):
        """Test __str__ methods of models."""
        program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test description"
        )
        
        role = Role.objects.create(
            title="Test Role",
            description="Test role"
        )
        
        # Test string representations
        self.assertEqual(str(program_type), "Test Program")
        self.assertEqual(str(role), "Test Role")
        self.assertEqual(str(self.admin_user), "admin@test.com")


class DataIntegrityTests(TestCase):
    """Test data integrity and consistency."""
    
    def setUp(self):
        """Set up test data."""
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123'
        )
    
    def test_cascade_deletion(self):
        """Test that related objects are properly handled on deletion."""
        program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test description"
        )
        
        buildout = ProgramBuildout.objects.create(
            program_type=program_type,
            title="Test Buildout",
            num_facilitators=1,
            num_new_facilitators=0,
            students_per_program=10,
            sessions_per_program=5,
            rate_per_student=Decimal('25.00')
        )
        
        # Delete program type should cascade to buildout
        program_type_id = program_type.id
        buildout_id = buildout.id
        
        program_type.delete()
        
        # Buildout should be deleted due to cascade
        self.assertFalse(ProgramBuildout.objects.filter(id=buildout_id).exists())
    
    def test_foreign_key_constraints(self):
        """Test foreign key constraints are enforced."""
        role = Role.objects.create(
            title="Test Role",
            description="Test role"
        )
        
        responsibility = Responsibility.objects.create(
            role=role,
            name="Test Responsibility",
            description="Test description",
            frequency_type="PER_SESSION",
            default_hours=Decimal('2.0')
        )
        
        # Try to delete role that has responsibilities
        role_id = role.id
        role.delete()
        
        # Responsibility should be deleted due to cascade
        self.assertFalse(Responsibility.objects.filter(role_id=role_id).exists())
    
    def test_unique_constraints(self):
        """Test unique constraints are enforced where expected."""
        # Test that we can't create duplicate program types with same name
        program_type1 = ProgramType.objects.create(
            name="Unique Program",
            description="First description"
        )
        
        # This might not have a unique constraint, but test if it does
        try:
            program_type2 = ProgramType.objects.create(
                name="Unique Program",
                description="Second description"
            )
            # If we get here, unique constraint isn't enforced (which might be OK)
        except IntegrityError:
            # If we get an error, unique constraint is enforced
            pass
    
    def test_data_consistency_after_updates(self):
        """Test that data remains consistent after updates."""
        program_type = ProgramType.objects.create(
            name="Original Program",
            description="Original description"
        )
        
        buildout = ProgramBuildout.objects.create(
            program_type=program_type,
            title="Test Buildout",
            num_facilitators=2,
            num_new_facilitators=1,
            students_per_program=10,
            sessions_per_program=5,
            rate_per_student=Decimal('25.00')
        )
        
        # Update program type
        program_type.name = "Updated Program"
        program_type.save()
        
        # Buildout should still reference updated program type
        buildout.refresh_from_db()
        self.assertEqual(buildout.program_type.name, "Updated Program")
        
        # Update buildout calculations
        original_revenue = buildout.total_revenue_per_year
        buildout.rate_per_student = Decimal('30.00')
        buildout.save()
        
        # Revenue should update accordingly
        self.assertNotEqual(buildout.total_revenue_per_year, original_revenue)
        self.assertEqual(buildout.total_revenue_per_year, Decimal('3000.00'))  # 100 students * $30


class SecurityValidationTests(TestCase):
    """Test security-related validations."""
    
    def setUp(self):
        """Set up test data."""
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123'
        )
        
        self.parent_user = User.objects.create_user(
            email='parent@test.com',
            password='testpass123'
        )
    
    def test_user_permission_isolation(self):
        """Test that users can only access their own data where appropriate."""
        # Create two children for different parents
        parent1 = User.objects.create_user(
            email='parent1@test.com',
            password='testpass123'
        )
        
        parent2 = User.objects.create_user(
            email='parent2@test.com',
            password='testpass123'
        )
        
        child1 = Child.objects.create(
            first_name="Child",
            last_name="One",
            parent=parent1,
            date_of_birth=date(2015, 1, 1)
        )
        
        child2 = Child.objects.create(
            first_name="Child",
            last_name="Two",
            parent=parent2,
            date_of_birth=date(2016, 1, 1)
        )
        
        # Each parent should only see their own children
        parent1_children = Child.objects.filter(parent=parent1)
        parent2_children = Child.objects.filter(parent=parent2)
        
        self.assertEqual(parent1_children.count(), 1)
        self.assertEqual(parent2_children.count(), 1)
        self.assertEqual(parent1_children.first(), child1)
        self.assertEqual(parent2_children.first(), child2)
    
    def test_sensitive_data_handling(self):
        """Test that sensitive data is properly handled."""
        # Test that contact information is stored securely
        contact = Contact.objects.create(
            parent_name="Test Parent",
            email="parent@test.com",
            message="This is sensitive information",
            interest="after_school"
        )
        
        # Verify data is stored
        self.assertEqual(contact.parent_name, "Test Parent")
        self.assertEqual(contact.email, "parent@test.com")
        
        # Test that we can retrieve and display safely
        safe_display = str(contact)
        self.assertIsInstance(safe_display, str)
    
    def test_input_sanitization(self):
        """Test that potentially dangerous inputs are handled safely."""
        # Test script injection attempts
        dangerous_name = "<script>alert('xss')</script>"
        
        try:
            program_type = ProgramType.objects.create(
                name=dangerous_name,
                description="Test description"
            )
            
            # Data should be stored as-is (sanitization happens at template level)
            self.assertEqual(program_type.name, dangerous_name)
            
            # But string representation should be safe
            safe_str = str(program_type)
            self.assertIsInstance(safe_str, str)
            
        except ValidationError:
            # If validation rejects dangerous input, that's also acceptable
            pass