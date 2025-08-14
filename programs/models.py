from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
import uuid

User = get_user_model()


class ProgramType(models.Model):
    """Template for program types like 'STEAM' or 'Literary' - simplified to contain only name and description."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('programs:program_type_detail', kwargs={'pk': self.pk})


class Role(models.Model):
    """Reusable role definition with title, description, and optional default responsibilities."""
    title = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    default_responsibilities = models.TextField(
        blank=True,
        help_text="Default responsibilities used as templates when included in a buildout"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title


class ResponsibilityFrequency(models.TextChoices):
    """Frequency options for responsibilities."""
    PER_WORKSHOP_CONCEPT = 'PER_WORKSHOP_CONCEPT', 'Per Workshop Concept'
    PER_NEW_FACILITATOR = 'PER_NEW_FACILITATOR', 'Per New Facilitator'
    PER_WORKSHOP = 'PER_WORKSHOP', 'Per Workshop'
    PER_SESSION = 'PER_SESSION', 'Per Session'


class Responsibility(models.Model):
    """Individual responsibility with role assignment and frequency-based calculations."""
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='responsibilities')
    name = models.CharField(max_length=200, help_text="Responsibility name/title")
    description = models.TextField(blank=True)
    frequency_type = models.CharField(
        max_length=32,
        choices=ResponsibilityFrequency.choices,
        help_text="How often this responsibility occurs"
    )
    hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Hours per frequency unit"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['role__title', 'name']
        unique_together = ['role', 'name']

    def __str__(self):
        return f"{self.role.title} - {self.name}"


class ProgramBuildout(models.Model):
    """Specific configuration of a program type with versioning and cloning support."""
    program_type = models.ForeignKey(ProgramType, on_delete=models.CASCADE, related_name="buildouts")
    title = models.CharField(max_length=100)
    
    # Versioning support
    version_number = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    
    # Scoping fields
    is_new_workshop = models.BooleanField(default=False, help_text="Whether this is a new workshop concept")
    num_facilitators = models.PositiveIntegerField(help_text="Number of qualified facilitators working")
    num_new_facilitators = models.PositiveIntegerField(help_text="Number of new hires/turnover")
    students_per_workshop = models.PositiveIntegerField(help_text="Students per workshop")
    sessions_per_workshop = models.PositiveIntegerField(help_text="Sessions per workshop")
    new_workshop_concepts_per_year = models.PositiveIntegerField(
        default=1, 
        help_text="New workshop concepts developed per year"
    )
    rate_per_student = models.DecimalField(
        max_digits=8, 
        decimal_places=2,
        help_text="Rate charged per student"
    )
    
    # Related models
    roles = models.ManyToManyField(Role, through='BuildoutRoleAssignment', related_name='buildouts')
    responsibilities = models.ManyToManyField(Responsibility, through='BuildoutResponsibilityAssignment', related_name='buildouts')
    base_costs = models.ManyToManyField('BaseCost', through='BuildoutBaseCostAssignment', related_name='buildouts')
    default_forms = models.ManyToManyField('RegistrationForm', blank=True, related_name='default_buildouts')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title', '-version_number']
        unique_together = ['program_type', 'title', 'version_number']

    def __str__(self):
        return f"{self.title} v{self.version_number} ({self.program_type.name})"

    @property
    def num_workshops_per_year(self):
        """Calculate total workshops per year."""
        return self.num_facilitators * 4  # Assuming 4 workshops per facilitator per year

    @property
    def total_students_per_year(self):
        """Calculate total students served per year."""
        return self.num_workshops_per_year * self.students_per_workshop

    @property
    def total_sessions_per_year(self):
        """Calculate total sessions per year."""
        return self.num_workshops_per_year * self.sessions_per_workshop

    @property
    def total_revenue_per_year(self):
        """Calculate total yearly revenue."""
        return Decimal(str(self.total_students_per_year * self.rate_per_student))

    def calculate_total_hours_per_role(self, role):
        """Calculate total hours per role."""
        total = Decimal('0.00')
        for assignment in self.responsibility_assignments.filter(responsibility__role=role):
            total += assignment.calculate_yearly_hours()
        return total

    def calculate_payout_per_role(self, role):
        """Calculate payout per role."""
        hours = self.calculate_total_hours_per_role(role)
        # Assuming $50/hour rate - this should be configurable
        return hours * Decimal('50.00')

    def calculate_percent_of_revenue_per_role(self, role):
        """Calculate percent of revenue per role."""
        payout = self.calculate_payout_per_role(role)
        revenue = self.total_revenue_per_year
        if revenue > 0:
            return (payout / revenue) * 100
        return Decimal('0.00')

    def calculate_base_costs_and_overhead(self):
        """Calculate base costs + total overhead."""
        total = Decimal('0.00')
        for assignment in self.base_cost_assignments.all():
            total += assignment.calculate_yearly_cost()
        return total

    @property
    def total_yearly_costs(self):
        """Calculate total yearly costs."""
        role_costs = Decimal('0.00')
        for role in self.roles.all():
            role_costs += self.calculate_payout_per_role(role)
        base_costs = self.calculate_base_costs_and_overhead()
        return role_costs + base_costs

    @property
    def expected_profit(self):
        """Compute expected profit."""
        return self.total_revenue_per_year - self.total_yearly_costs

    @property
    def profit_margin(self):
        """Compute profit margin as percentage."""
        if self.total_revenue_per_year > 0:
            return (self.expected_profit / self.total_revenue_per_year) * 100
        return Decimal('0.00')

    def clone(self):
        """Create a new version of this buildout."""
        new_buildout = ProgramBuildout.objects.create(
            program_type=self.program_type,
            title=self.title,
            version_number=self.version_number + 1,
            is_new_workshop=self.is_new_workshop,
            num_facilitators=self.num_facilitators,
            num_new_facilitators=self.num_new_facilitators,
            students_per_workshop=self.students_per_workshop,
            sessions_per_workshop=self.sessions_per_workshop,
            rate_per_student=self.rate_per_student
        )
        
        # Copy related data
        new_buildout.roles.set(self.roles.all())
        new_buildout.responsibilities.set(self.responsibilities.all())
        new_buildout.base_costs.set(self.base_costs.all())
        new_buildout.default_forms.set(self.default_forms.all())
        
        return new_buildout


class BuildoutRoleAssignment(models.Model):
    """Assignment of a role to a buildout."""
    buildout = models.ForeignKey(ProgramBuildout, on_delete=models.CASCADE, related_name='role_assignments')
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['buildout', 'role']

    def __str__(self):
        return f"{self.role.title} - {self.buildout.title}"


class BuildoutResponsibilityAssignment(models.Model):
    """Assignment of a responsibility to a buildout."""
    buildout = models.ForeignKey(ProgramBuildout, on_delete=models.CASCADE, related_name='responsibility_assignments')
    responsibility = models.ForeignKey(Responsibility, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['buildout', 'responsibility']

    def __str__(self):
        return f"{self.responsibility.name} - {self.buildout.title}"

    def calculate_yearly_hours(self):
        """Calculate total yearly hours for this responsibility."""
        buildout = self.buildout
        
        if self.responsibility.frequency_type == ResponsibilityFrequency.PER_WORKSHOP_CONCEPT:
            return self.responsibility.hours * (1 if buildout.is_new_workshop else 0)
        elif self.responsibility.frequency_type == ResponsibilityFrequency.PER_NEW_FACILITATOR:
            return self.responsibility.hours * buildout.num_new_facilitators
        elif self.responsibility.frequency_type == ResponsibilityFrequency.PER_WORKSHOP:
            return self.responsibility.hours * buildout.num_workshops_per_year
        elif self.responsibility.frequency_type == ResponsibilityFrequency.PER_SESSION:
            return self.responsibility.hours * buildout.total_sessions_per_year
        else:
            return Decimal('0.00')


class BaseCost(models.Model):
    """Fixed costs that apply to programs (location, insurance, etc.)."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="Cost amount per frequency unit"
    )
    frequency = models.CharField(
        max_length=32,
        choices=ResponsibilityFrequency.choices,
        help_text="How often this cost occurs"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class BuildoutBaseCostAssignment(models.Model):
    """Assignment of base costs to buildouts."""
    buildout = models.ForeignKey(ProgramBuildout, on_delete=models.CASCADE, related_name='base_cost_assignments')
    base_cost = models.ForeignKey(BaseCost, on_delete=models.CASCADE)
    multiplier = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=1.00,
        help_text="Multiplier for the base cost"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['buildout', 'base_cost']

    def __str__(self):
        return f"{self.base_cost.name} - {self.buildout.title}"

    def calculate_yearly_cost(self):
        """Calculate yearly cost for this base cost."""
        buildout = self.buildout
        base_amount = self.base_cost.rate * self.multiplier

        if self.base_cost.frequency == ResponsibilityFrequency.PER_WORKSHOP_CONCEPT:
            return base_amount * (1 if buildout.is_new_workshop else 0)
        elif self.base_cost.frequency == ResponsibilityFrequency.PER_NEW_FACILITATOR:
            return base_amount * buildout.num_new_facilitators
        elif self.base_cost.frequency == ResponsibilityFrequency.PER_WORKSHOP:
            return base_amount * buildout.num_workshops_per_year
        elif self.base_cost.frequency == ResponsibilityFrequency.PER_SESSION:
            return base_amount * buildout.total_sessions_per_year
        else:
            return Decimal('0.00')


class ProgramInstance(models.Model):
    """Specific offering of a program buildout with contractor assignments."""
    buildout = models.ForeignKey(ProgramBuildout, on_delete=models.CASCADE, related_name='instances')
    title = models.CharField(max_length=100)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    location = models.CharField(max_length=200)
    capacity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    actual_enrollment = models.PositiveIntegerField(default=0)
    
    # Override fields for customizing buildout parameters
    override_counts = models.JSONField(
        blank=True,
        null=True,
        help_text="JSON object with buildout count overrides (e.g., {'students_per_workshop': 8})"
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
        return f"{self.title} - {self.start_date.strftime('%Y-%m-%d')}"

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
    def actual_revenue(self):
        """Calculate actual revenue based on current enrollment."""
        return self.current_enrollment * self.buildout.rate_per_student

    def get_effective_counts(self):
        """Get counts with any overrides applied."""
        counts = {
            'num_facilitators': self.buildout.num_facilitators,
            'num_new_facilitators': self.buildout.num_new_facilitators,
            'students_per_workshop': self.buildout.students_per_workshop,
            'sessions_per_workshop': self.buildout.sessions_per_workshop,
        }
        
        if self.override_counts:
            counts.update(self.override_counts)
        
        return counts

    def calculate_expected_payouts(self):
        """Calculate expected payouts based on enrollment vs capacity."""
        total = Decimal('0.00')
        for assignment in self.contractor_assignments.all():
            total += assignment.calculate_payout()
        return total

    @property
    def expected_profit(self):
        """Calculate expected profit."""
        return self.actual_revenue - self.calculate_expected_payouts()

    def send_communication_to_participants(self, subject, message):
        """Send communication to all participants."""
        # Implementation for sending communication
        # This would integrate with the communications app
        pass


class InstanceRoleAssignment(models.Model):
    """Assignment of a contractor to a role in a program instance."""
    program_instance = models.ForeignKey(ProgramInstance, on_delete=models.CASCADE, related_name='contractor_assignments')
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    contractor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='role_assignments',
        limit_choices_to={'groups__name__in': ['Contractor', 'Admin']}
    )
    
    # Override fields for customizing payouts
    override_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Override hours for this assignment"
    )
    override_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Override hourly rate for this assignment"
    )
    
    # Computed payout
    computed_payout = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Computed payout amount"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['program_instance', 'role']

    def __str__(self):
        return f"{self.contractor.get_full_name()} - {self.role.title}"

    def calculate_hours(self):
        """Calculate total hours for this role assignment."""
        if self.override_hours is not None:
            return self.override_hours
        
        # Calculate hours from buildout responsibilities
        total_hours = Decimal('0.00')
        for assignment in self.program_instance.buildout.responsibility_assignments.filter(responsibility__role=self.role):
            total_hours += assignment.calculate_yearly_hours()
        
        return total_hours

    def calculate_payout(self):
        """Calculate payout for this assignment."""
        hours = self.calculate_hours()
        rate = self.override_rate if self.override_rate is not None else Decimal('50.00')  # Default rate
        return hours * rate

    def update_computed_payout(self):
        """Update the computed payout."""
        self.computed_payout = self.calculate_payout()
        self.save(update_fields=['computed_payout'])


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
