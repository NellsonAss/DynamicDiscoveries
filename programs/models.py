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
    scope = models.TextField(help_text="Learning scope and objectives")
    target_grade_levels = models.CharField(
        max_length=200,
        help_text="Comma-separated grade levels (e.g., 'K-2, 3-5')"
    )
    rate_per_student = models.DecimalField(
        max_digits=8, 
        decimal_places=2,
        help_text="Base rate charged per student"
    )
    
    # Default counts for new buildouts
    default_num_facilitators = models.PositiveIntegerField(default=1)
    default_num_new_facilitators = models.PositiveIntegerField(default=0)
    default_workshops_per_facilitator_per_year = models.PositiveIntegerField(default=4)
    default_students_per_workshop = models.PositiveIntegerField(default=12)
    default_sessions_per_workshop = models.PositiveIntegerField(default=8)
    default_new_workshop_concepts_per_year = models.PositiveIntegerField(default=1)
    
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


class Role(models.Model):
    """Defines roles that can be assigned to program types."""
    name = models.CharField(max_length=100, unique=True)
    hourly_rate = models.DecimalField(
        max_digits=8, 
        decimal_places=2,
        help_text="Hourly rate for this role"
    )
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class ProgramBuildout(models.Model):
    """Specific configuration of a program type with detailed role breakdown."""
    program_type = models.ForeignKey(ProgramType, on_delete=models.CASCADE, related_name="buildouts")
    title = models.CharField(max_length=100)
    
    # Count fields for calculations
    num_facilitators = models.PositiveIntegerField(help_text="Number of qualified facilitators working")
    num_new_facilitators = models.PositiveIntegerField(help_text="Number of new hires/turnover")
    workshops_per_facilitator_per_year = models.PositiveIntegerField(help_text="Workshops each facilitator runs per year")
    students_per_workshop = models.PositiveIntegerField(help_text="Students per workshop")
    sessions_per_workshop = models.PositiveIntegerField(help_text="Sessions per workshop")
    new_workshop_concepts_per_year = models.PositiveIntegerField(default=1, help_text="New workshop concepts developed per year")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return f"{self.title} ({self.program_type.name})"

    @property
    def num_workshops_per_year(self):
        """Calculate total workshops per year."""
        return self.num_facilitators * self.workshops_per_facilitator_per_year

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
        return self.total_students_per_year * self.program_type.rate_per_student

    def calculate_total_role_costs(self):
        """Calculate total costs for all roles."""
        total = Decimal('0.00')
        for role_assignment in self.role_assignments.all():
            total += role_assignment.calculate_yearly_cost()
        return total

    def calculate_total_baseline_costs(self):
        """Calculate total baseline costs."""
        total = Decimal('0.00')
        for baseline_cost in self.baseline_costs.all():
            total += baseline_cost.calculate_yearly_cost()
        return total

    @property
    def total_yearly_costs(self):
        """Calculate total yearly costs."""
        return self.calculate_total_role_costs() + self.calculate_total_baseline_costs()

    @property
    def yearly_profit(self):
        """Calculate yearly profit."""
        return self.total_revenue_per_year - self.total_yearly_costs

    @property
    def profit_margin(self):
        """Calculate profit margin as percentage."""
        if self.total_revenue_per_year > 0:
            return (self.yearly_profit / self.total_revenue_per_year) * 100
        return Decimal('0.00')


class ResponsibilityFrequency(models.TextChoices):
    """Frequency options for responsibilities and costs."""
    PER_WORKSHOP_CONCEPT = 'PER_WORKSHOP_CONCEPT', 'Per Workshop Concept'
    PER_NEW_FACILITATOR = 'PER_NEW_FACILITATOR', 'Per New Facilitator'
    PER_WORKSHOP = 'PER_WORKSHOP', 'Per Workshop'
    PER_SESSION = 'PER_SESSION', 'Per Session'
    PER_STUDENT = 'PER_STUDENT', 'Per Student'
    PER_YEAR = 'PER_YEAR', 'Per Year'
    ADMIN_FLAT = 'ADMIN_FLAT', 'Admin Flat'
    OVERRIDE = 'OVERRIDE', 'Manual Override'


class BuildoutResponsibility(models.Model):
    """Individual responsibility within a buildout."""
    buildout = models.ForeignKey(ProgramBuildout, on_delete=models.CASCADE, related_name='responsibilities')
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, help_text="Responsibility name/title")
    description = models.TextField(blank=True)
    frequency = models.CharField(
        max_length=32,
        choices=ResponsibilityFrequency.choices,
        help_text="How often this responsibility occurs"
    )
    base_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Hours per frequency unit"
    )
    override_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Manual override for total hours (ignores frequency calculation)"
    )

    class Meta:
        ordering = ['role__name', 'name']
        unique_together = ['buildout', 'role', 'name']

    def __str__(self):
        return f"{self.role.name} - {self.name}"

    def calculate_yearly_hours(self):
        """Calculate total yearly hours for this responsibility."""
        if self.frequency == ResponsibilityFrequency.OVERRIDE and self.override_hours is not None:
            return self.override_hours

        buildout = self.buildout
        
        if self.frequency == ResponsibilityFrequency.PER_WORKSHOP_CONCEPT:
            return self.base_hours * buildout.new_workshop_concepts_per_year
        elif self.frequency == ResponsibilityFrequency.PER_NEW_FACILITATOR:
            return self.base_hours * buildout.num_new_facilitators
        elif self.frequency == ResponsibilityFrequency.PER_WORKSHOP:
            return self.base_hours * buildout.num_workshops_per_year
        elif self.frequency == ResponsibilityFrequency.PER_SESSION:
            return self.base_hours * buildout.total_sessions_per_year
        elif self.frequency == ResponsibilityFrequency.PER_STUDENT:
            return self.base_hours * buildout.total_students_per_year
        elif self.frequency == ResponsibilityFrequency.PER_YEAR:
            return self.base_hours
        elif self.frequency == ResponsibilityFrequency.ADMIN_FLAT:
            return self.base_hours
        else:
            return Decimal('0.00')

    def calculate_yearly_cost(self):
        """Calculate yearly cost for this responsibility."""
        hours = self.calculate_yearly_hours()
        return hours * self.role.hourly_rate


class BuildoutRoleAssignment(models.Model):
    """Assignment of a role to a buildout with percentage tracking."""
    buildout = models.ForeignKey(ProgramBuildout, on_delete=models.CASCADE, related_name='role_assignments')
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    percent_of_revenue = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Percentage of revenue this role represents"
    )

    class Meta:
        unique_together = ['buildout', 'role']

    def __str__(self):
        return f"{self.role.name} - {self.buildout.title}"

    def calculate_yearly_hours(self):
        """Calculate total yearly hours for this role."""
        total = Decimal('0.00')
        for responsibility in self.buildout.responsibilities.filter(role=self.role):
            total += responsibility.calculate_yearly_hours()
        return total

    def calculate_yearly_cost(self):
        """Calculate yearly cost for this role."""
        total = Decimal('0.00')
        for responsibility in self.buildout.responsibilities.filter(role=self.role):
            total += responsibility.calculate_yearly_cost()
        return total

    def calculate_percent_of_revenue(self):
        """Calculate actual percentage of revenue this role represents."""
        cost = self.calculate_yearly_cost()
        revenue = self.buildout.total_revenue_per_year
        if revenue > 0:
            return (cost / revenue) * 100
        return Decimal('0.00')


class BaseCost(models.Model):
    """Fixed costs that apply to programs (location, insurance, etc.)."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    frequency = models.CharField(
        max_length=32,
        choices=ResponsibilityFrequency.choices,
        help_text="How often this cost occurs"
    )
    amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="Cost amount per frequency unit"
    )

    def __str__(self):
        return self.name


class BuildoutBaseCost(models.Model):
    """Assignment of base costs to buildouts."""
    buildout = models.ForeignKey(ProgramBuildout, on_delete=models.CASCADE, related_name='baseline_costs')
    base_cost = models.ForeignKey(BaseCost, on_delete=models.CASCADE)
    multiplier = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=1.00,
        help_text="Multiplier for the base cost"
    )

    class Meta:
        unique_together = ['buildout', 'base_cost']

    def __str__(self):
        return f"{self.base_cost.name} - {self.buildout.title}"

    def calculate_yearly_cost(self):
        """Calculate yearly cost for this baseline cost."""
        buildout = self.buildout
        base_amount = self.base_cost.amount * self.multiplier

        if self.base_cost.frequency == ResponsibilityFrequency.PER_WORKSHOP_CONCEPT:
            return base_amount * buildout.new_workshop_concepts_per_year
        elif self.base_cost.frequency == ResponsibilityFrequency.PER_NEW_FACILITATOR:
            return base_amount * buildout.num_new_facilitators
        elif self.base_cost.frequency == ResponsibilityFrequency.PER_WORKSHOP:
            return base_amount * buildout.num_workshops_per_year
        elif self.base_cost.frequency == ResponsibilityFrequency.PER_SESSION:
            return base_amount * buildout.total_sessions_per_year
        elif self.base_cost.frequency == ResponsibilityFrequency.PER_STUDENT:
            return base_amount * buildout.total_students_per_year
        elif self.base_cost.frequency == ResponsibilityFrequency.PER_YEAR:
            return base_amount
        elif self.base_cost.frequency == ResponsibilityFrequency.ADMIN_FLAT:
            return base_amount
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
        return self.buildout.program_type.calculate_revenue(self.current_enrollment)

    def get_effective_counts(self):
        """Get counts with any overrides applied."""
        counts = {
            'num_facilitators': self.buildout.num_facilitators,
            'num_new_facilitators': self.buildout.num_new_facilitators,
            'workshops_per_facilitator_per_year': self.buildout.workshops_per_facilitator_per_year,
            'students_per_workshop': self.buildout.students_per_workshop,
            'sessions_per_workshop': self.buildout.sessions_per_workshop,
            'new_workshop_concepts_per_year': self.buildout.new_workshop_concepts_per_year,
        }
        
        if self.override_counts:
            counts.update(self.override_counts)
        
        return counts

    def calculate_expected_payouts(self):
        """Calculate expected payouts based on enrollment vs capacity."""
        if self.current_enrollment >= self.capacity:
            # Pay based on hours when at capacity
            total = Decimal('0.00')
            for assignment in self.contractor_assignments.all():
                total += assignment.calculate_hours_payout()
            return total
        else:
            # Pay based on revenue share when below capacity
            total = Decimal('0.00')
            for assignment in self.contractor_assignments.all():
                total += assignment.calculate_revenue_share_payout()
            return total

    @property
    def expected_profit(self):
        """Calculate expected profit."""
        return self.actual_revenue - self.calculate_expected_payouts()


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
    override_revenue_share = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Override revenue share percentage"
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
        return f"{self.contractor.get_full_name()} - {self.role.name}"

    def calculate_hours_payout(self):
        """Calculate payout based on hours when at capacity."""
        if self.override_hours is not None:
            hours = self.override_hours
        else:
            # Calculate hours from buildout responsibilities
            hours = Decimal('0.00')
            for responsibility in self.program_instance.buildout.responsibilities.filter(role=self.role):
                hours += responsibility.calculate_yearly_hours()
        
        return hours * self.role.hourly_rate

    def calculate_revenue_share_payout(self):
        """Calculate payout based on revenue share when below capacity."""
        if self.override_revenue_share is not None:
            share_percentage = self.override_revenue_share
        else:
            # Get share percentage from buildout role assignment
            try:
                role_assignment = self.program_instance.buildout.role_assignments.get(role=self.role)
                share_percentage = role_assignment.percent_of_revenue
            except BuildoutRoleAssignment.DoesNotExist:
                share_percentage = Decimal('0.00')
        
        revenue = self.program_instance.actual_revenue
        return (revenue * share_percentage) / 100

    def update_computed_payout(self):
        """Update the computed payout based on current conditions."""
        if self.program_instance.current_enrollment >= self.program_instance.capacity:
            self.computed_payout = self.calculate_hours_payout()
        else:
            self.computed_payout = self.calculate_revenue_share_payout()
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
