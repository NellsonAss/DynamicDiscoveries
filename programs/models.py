from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from decimal import Decimal
import uuid

User = get_user_model()


class ProgramType(models.Model):
    """Template for program types like 'STEAM' or 'Literary'."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    target_grade_levels = models.CharField(
        max_length=200,
        help_text="Comma-separated grade levels (e.g., 'K-2, 3-5')"
    )
    rate_per_student = models.DecimalField(
        max_digits=8, 
        decimal_places=2,
        help_text="Base rate charged per student"
    )
    default_registration_form = models.ForeignKey(
        'RegistrationForm',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='default_for_program_types'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('programs:program_instance_detail', kwargs={'pk': self.pk})

    def calculate_revenue(self, student_count):
        """Calculate total revenue for given number of students."""
        from decimal import Decimal
        return self.rate_per_student * Decimal(str(student_count))

    def calculate_total_payouts(self, student_count):
        """Calculate total payouts to all roles."""
        total = Decimal('0.00')
        for role in self.roles.all():
            total += role.calculate_payout(student_count)
        return total

    def calculate_profit(self, student_count):
        """Calculate business profit (revenue - payouts)."""
        revenue = self.calculate_revenue(student_count)
        payouts = self.calculate_total_payouts(student_count)
        return revenue - payouts


class Role(models.Model):
    """Defines roles that can be assigned to program types."""
    name = models.CharField(max_length=100, unique=True)
    hourly_rate = models.DecimalField(
        max_digits=8, 
        decimal_places=2,
        help_text="Hourly rate for this role"
    )
    responsibilities = models.TextField()

    def __str__(self):
        return self.name


class ProgramRole(models.Model):
    """Defines a role assignment within a program type with hours and responsibilities."""
    FREQUENCY_CHOICES = [
        ("PER_PROGRAM", "Per Program"),
        ("PER_SESSION", "Per Session"),
        ("PER_KID", "Per Kid"),
        ("PER_SESSION_PER_KID", "Per Session per Kid"),
        ("ADMIN_FLAT", "Admin Flat"),
        ("OVERRIDE", "Manual Override"),
    ]

    program_type = models.ForeignKey(ProgramType, on_delete=models.CASCADE, related_name="roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    hour_frequency = models.CharField(max_length=32, choices=FREQUENCY_CHOICES)
    hour_multiplier = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        help_text="Base number for frequency (e.g. 0.5 per session)"
    )
    override_hours = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Manual override for total hours (ignores frequency calculation)"
    )

    class Meta:
        unique_together = ('program_type', 'role')

    def calculate_total_hours(self, student_count, num_days, sessions_per_day=1):
        """
        Compute the total expected hours for this role instance
        based on program context and frequency logic
        """
        from decimal import Decimal
        
        if self.hour_frequency == "OVERRIDE" and self.override_hours is not None:
            return self.override_hours

        sessions = num_days * sessions_per_day

        if self.hour_frequency == "PER_PROGRAM":
            return self.hour_multiplier
        elif self.hour_frequency == "PER_SESSION":
            return self.hour_multiplier * Decimal(str(sessions))
        elif self.hour_frequency == "PER_KID":
            return self.hour_multiplier * Decimal(str(student_count))
        elif self.hour_frequency == "PER_SESSION_PER_KID":
            return self.hour_multiplier * Decimal(str(student_count)) * Decimal(str(sessions))
        elif self.hour_frequency == "ADMIN_FLAT":
            return self.hour_multiplier
        return Decimal('0.00')

    def calculate_payout(self, student_count, num_days=1, sessions_per_day=1):
        """Calculate payout for this role (hours × rate)."""
        hours = self.calculate_total_hours(student_count, num_days, sessions_per_day)
        return hours * self.role.hourly_rate

    def calculate_percentage_of_revenue(self, student_count, num_days=1, sessions_per_day=1):
        """Calculate what percentage of total revenue this role represents."""
        payout = self.calculate_payout(student_count, num_days, sessions_per_day)
        revenue = self.program_type.calculate_revenue(student_count)
        if revenue > 0:
            return (payout / revenue) * 100
        return Decimal('0.00')

    def __str__(self):
        return f"{self.role.name} - {self.program_type.name}"


class BaseCost(models.Model):
    """Fixed costs that apply to all programs (location, insurance, etc.)."""
    name = models.CharField(max_length=100)
    cost_per_student = models.DecimalField(
        max_digits=8, 
        decimal_places=2,
        help_text="Cost per student for this base cost"
    )
    description = models.TextField()

    def __str__(self):
        return self.name


class ProgramBaseCost(models.Model):
    """Assignment of base costs to program types."""
    program_type = models.ForeignKey(ProgramType, on_delete=models.CASCADE, related_name="base_costs")
    base_cost = models.ForeignKey(BaseCost, on_delete=models.CASCADE)
    multiplier = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        default=1.00,
        help_text="Multiplier for the base cost (e.g., 1.5 for higher cost programs)"
    )

    class Meta:
        unique_together = ('program_type', 'base_cost')

    def calculate_cost(self, student_count):
        """Calculate total cost for this base cost item."""
        from decimal import Decimal
        return self.base_cost.cost_per_student * Decimal(str(student_count)) * self.multiplier

    def __str__(self):
        return f"{self.base_cost.name} - {self.program_type.name}"


class ProgramBuildout(models.Model):
    """Specific configuration of a program type with student count and duration."""
    program_type = models.ForeignKey(ProgramType, on_delete=models.CASCADE, related_name="buildouts")
    title = models.CharField(max_length=100)
    expected_students = models.PositiveIntegerField()
    num_days = models.PositiveIntegerField()
    sessions_per_day = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.title} ({self.program_type.name})"

    @property
    def total_revenue(self):
        """Calculate total expected revenue."""
        return self.program_type.calculate_revenue(self.expected_students)

    @property
    def total_role_payouts(self):
        """Calculate total payouts to all roles."""
        total = Decimal('0.00')
        for role in self.program_type.roles.all():
            total += role.calculate_payout(
                self.expected_students, 
                self.num_days, 
                self.sessions_per_day
            )
        return total

    @property
    def total_base_costs(self):
        """Calculate total base costs."""
        total = Decimal('0.00')
        for base_cost in self.program_type.base_costs.all():
            total += base_cost.calculate_cost(self.expected_students)
        return total

    @property
    def total_payouts(self):
        """Calculate total payouts including base costs."""
        return self.total_role_payouts + self.total_base_costs

    @property
    def profit(self):
        """Calculate business profit."""
        return self.total_revenue - self.total_payouts

    @property
    def profit_margin(self):
        """Calculate profit margin as percentage."""
        if self.total_revenue > 0:
            return (self.profit / self.total_revenue) * 100
        return Decimal('0.00')


class ProgramInstance(models.Model):
    """Specific offering of a ProgramType with scheduling details."""
    program_type = models.ForeignKey(
        ProgramType,
        on_delete=models.CASCADE,
        related_name='instances'
    )
    buildout = models.ForeignKey(
        ProgramBuildout,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Optional buildout template to use for this instance"
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    location = models.CharField(max_length=200)
    instructor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='teaching_instances',
        limit_choices_to={'groups__name__in': ['Contractor', 'Admin']}
    )
    capacity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    assigned_form = models.ForeignKey(
        'RegistrationForm',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_instances'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.program_type.name} - {self.start_date.strftime('%Y-%m-%d')}"

    def get_absolute_url(self):
        return reverse('programs:program_instance_detail', kwargs={'pk': self.pk})

    @property
    def current_enrollment(self):
        """Get current number of enrolled children."""
        return self.registrations.filter(status='approved').count()

    @property
    def available_spots(self):
        """Get number of available spots."""
        return max(0, self.capacity - self.current_enrollment)

    @property
    def is_full(self):
        """Check if program is at capacity."""
        return self.current_enrollment >= self.capacity

    @property
    def expected_revenue(self):
        """Calculate expected revenue based on current enrollment."""
        return self.program_type.calculate_revenue(self.current_enrollment)

    @property
    def expected_payouts(self):
        """Calculate expected payouts based on current enrollment."""
        if self.buildout:
            # Use buildout template if available
            return self.buildout.total_payouts
        else:
            # Calculate based on current enrollment
            total = Decimal('0.00')
            for role in self.program_type.roles.all():
                total += role.calculate_payout(self.current_enrollment)
            return total

    @property
    def expected_profit(self):
        """Calculate expected profit."""
        return self.expected_revenue - self.expected_payouts


class RegistrationForm(models.Model):
    """Form template for program registration or feedback."""
    QUESTION_TYPES = [
        ('text', 'Text Input'),
        ('textarea', 'Long Text'),
        ('email', 'Email'),
        ('phone', 'Phone Number'),
        ('select', 'Multiple Choice'),
        ('checkbox', 'Checkbox'),
        ('radio', 'Radio Button'),
        ('date', 'Date'),
        ('number', 'Number'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_forms',
        limit_choices_to={'groups__name__in': ['Contractor', 'Admin']}
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('programs:form_edit', kwargs={'pk': self.pk})

    def duplicate(self):
        """Create a deep copy of this form with all questions."""
        new_form = RegistrationForm.objects.create(
            title=f"{self.title} (Copy)",
            description=self.description,
            created_by=self.created_by
        )
        
        # Copy all questions
        for question in self.questions.all():
            FormQuestion.objects.create(
                form=new_form,
                question_text=question.question_text,
                question_type=question.question_type,
                is_required=question.is_required,
                options=question.options,
                order=question.order
            )
        
        return new_form


class FormQuestion(models.Model):
    """Individual question within a registration form."""
    form = models.ForeignKey(
        RegistrationForm,
        on_delete=models.CASCADE,
        related_name='questions'
    )
    question_text = models.CharField(max_length=500)
    question_type = models.CharField(
        max_length=20,
        choices=RegistrationForm.QUESTION_TYPES,
        default='text'
    )
    is_required = models.BooleanField(default=True)
    options = models.JSONField(
        blank=True,
        null=True,
        help_text="For select/radio/checkbox questions, provide options as JSON array"
    )
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.form.title} - {self.question_text[:50]}"


class Child(models.Model):
    """Child model for parent registration."""
    parent = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='children',
        limit_choices_to={'groups__name': 'Parent'}
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    grade_level = models.CharField(max_length=20, blank=True)
    special_needs = models.TextField(blank=True)
    emergency_contact = models.CharField(max_length=200, blank=True)
    emergency_phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name_plural = 'Children'

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def get_absolute_url(self):
        return reverse('programs:edit_child', kwargs={'pk': self.pk})

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )


class Registration(models.Model):
    """Registration of a child for a program instance."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    child = models.ForeignKey(
        Child,
        on_delete=models.CASCADE,
        related_name='registrations'
    )
    program_instance = models.ForeignKey(
        ProgramInstance,
        on_delete=models.CASCADE,
        related_name='registrations'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    form_responses = models.JSONField(
        blank=True,
        null=True,
        help_text="Responses to registration form questions"
    )
    notes = models.TextField(blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-registered_at']
        unique_together = ['child', 'program_instance']

    def __str__(self):
        return f"{self.child.full_name} - {self.program_instance}"

    def get_absolute_url(self):
        return reverse('programs:registration_detail', kwargs={'pk': self.pk})

    @property
    def parent(self):
        return self.child.parent

    def can_be_approved(self):
        """Check if registration can be approved."""
        if self.program_instance.assigned_form:
            return bool(self.form_responses)
        return True
