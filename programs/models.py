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
    visible_to_parents = models.BooleanField(
        default=True,
        help_text="Whether this role and assigned contractors are visible to parents in program listings and catalogs"
    )
    default_responsibilities = models.TextField(
        blank=True,
        help_text="Default responsibilities used as templates when included in a buildout"
    )
    # Default frequency and hours for seeding version lines
    default_frequency_unit = models.CharField(
        max_length=32,
        choices=[
            ('PER_PROGRAM_CONCEPT', 'Per Program Concept'),
            ('PER_NEW_FACILITATOR', 'Per New Facilitator'),
            ('PER_PROGRAM', 'Per Program'),
            ('PER_SESSION', 'Per Session'),
        ],
        default='PER_PROGRAM',
        help_text="Default frequency unit for this role"
    )
    default_hours_per_frequency = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('1.00'),
        help_text="Default hours per frequency unit for this role"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title

    def get_assigned_contractors(self):
        """Get all contractors assigned to this role with completed onboarding."""
        from people.models import Contractor
        return User.objects.filter(
            general_role_assignments__role=self,
            groups__name='Contractor'
        ).select_related('profile').prefetch_related(
            models.Prefetch(
                'contractor',
                queryset=Contractor.objects.filter(onboarding_complete=True)
            )
        )

    def get_assigned_users(self):
        """Get all users assigned to this role."""
        return User.objects.filter(general_role_assignments__role=self)


class RoleAssignment(models.Model):
    """Assignment of a user to a role."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='general_role_assignments'
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='user_assignments'
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='role_assignments_made',
        help_text="Admin user who made this assignment"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'role']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.email} - {self.role.title}"


class ResponsibilityFrequency(models.TextChoices):
    """Frequency options for responsibilities."""
    PER_PROGRAM_CONCEPT = 'PER_PROGRAM_CONCEPT', 'Per Program Concept'
    PER_NEW_FACILITATOR = 'PER_NEW_FACILITATOR', 'Per New Facilitator'
    PER_PROGRAM = 'PER_PROGRAM', 'Per Program'
    PER_SESSION = 'PER_SESSION', 'Per Session'
    PER_CHILD = 'PER_CHILD', 'Per Child'


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
    # Default hours for seeding version lines
    default_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Default hours per frequency unit"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['role__title', 'name']
        unique_together = ['role', 'name']

    def __str__(self):
        return f"{self.role.title} - {self.name}"


class ContractorRoleRate(models.Model):
    """Default pay rates for contractors in specific roles."""
    contractor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='role_rates',
        limit_choices_to={'groups__name__in': ['Contractor', 'Admin']}
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='contractor_rates')
    
    # Pay structure
    pay_type = models.CharField(
        max_length=32,
        choices=[
            ('HOURLY', 'Hourly'),
            ('PER_PROGRAM', 'Per Program'),
            ('PER_SESSION', 'Per Session'),
            ('FLAT_RATE', 'Flat Rate'),
        ],
        default='HOURLY',
        help_text="How this contractor is paid for this role"
    )
    pay_value = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="Pay amount (hourly rate, per program rate, etc.)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['contractor', 'role']
        ordering = ['contractor__email', 'role__title']

    def __str__(self):
        return f"{self.contractor.email} - {self.role.title}: ${self.pay_value}"


class ProgramBuildout(models.Model):
    """Specific configuration of a program type with versioning and cloning support."""
    program_type = models.ForeignKey(ProgramType, on_delete=models.CASCADE, related_name="buildouts")
    title = models.CharField(max_length=100)
    
    # Versioning support
    version_number = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    is_published = models.BooleanField(default=False, help_text="Published versions are immutable")
    
    # Scoping fields
    is_new_program = models.BooleanField(default=False, help_text="Whether this is a new program concept")
    num_facilitators = models.PositiveIntegerField(help_text="Number of qualified facilitators working")
    num_new_facilitators = models.PositiveIntegerField(help_text="Number of new hires/turnover")
    students_per_program = models.PositiveIntegerField(help_text="Students per program")
    sessions_per_program = models.PositiveIntegerField(help_text="Sessions per program")
    new_program_concepts_per_year = models.PositiveIntegerField(
        default=1, 
        help_text="New program concepts developed per year"
    )
    rate_per_student = models.DecimalField(
        max_digits=8, 
        decimal_places=2,
        help_text="Rate charged per student"
    )
    
    # Related models - updated to use new through models
    roles = models.ManyToManyField(Role, through='BuildoutRoleLine', related_name='buildouts')
    responsibilities = models.ManyToManyField(Responsibility, through='BuildoutResponsibilityLine', related_name='buildouts')
    base_costs = models.ManyToManyField('BaseCost', through='BuildoutBaseCostAssignment', related_name='buildouts')
    locations = models.ManyToManyField('Location', through='BuildoutLocationAssignment', related_name='buildouts')
    default_forms = models.ManyToManyField('RegistrationForm', blank=True, related_name='default_buildouts')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Status(models.TextChoices):
        NEW = "new", "New"
        IN_PROGRESS = "in_progress", "In Progress"
        READY = "ready", "Ready"
        AWAITING_SIGNATURES = "awaiting_signatures", "Awaiting Signatures"
        ACTIVE = "active", "Active"
        ON_HOLD = "on_hold", "On Hold"
        CANCELLED = "cancelled", "Cancelled"

    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
    )
    assigned_contractor = models.ForeignKey(
        "people.Contractor",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="buildouts",
    )

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if self.assigned_contractor_id:
            contractor = self.assigned_contractor
            # Require contractor onboarding completion before assignment
            if not getattr(contractor, "onboarding_complete", False):
                raise ValidationError({
                    "assigned_contractor": "Contractor must complete NDA and W-9 before assignment."
                })

    class Meta:
        ordering = ['title', '-version_number']
        unique_together = ['program_type', 'title', 'version_number']

    def __str__(self):
        return f"{self.title} v{self.version_number} ({self.program_type.name})"

    @property
    def num_programs_per_year(self):
        """Calculate total programs per year."""
        return self.num_facilitators * 4  # Assuming 4 programs per facilitator per year

    @property
    def total_students_per_year(self):
        """Calculate total students served per year."""
        return self.num_programs_per_year * self.students_per_program

    @property
    def total_sessions_per_year(self):
        """Calculate total sessions per year."""
        return self.num_programs_per_year * self.sessions_per_program

    @property
    def total_revenue_per_year(self):
        """Calculate total yearly revenue."""
        return Decimal(str(self.total_students_per_year * self.rate_per_student))

    def calculate_total_hours_per_role(self, role):
        """Calculate total hours per role."""
        total = Decimal('0.00')
        for assignment in self.responsibility_lines.filter(role=role):
            total += assignment.calculate_yearly_hours()
        return total

    def calculate_payout_per_role(self, role):
        """Calculate payout per role."""
        try:
            role_line = self.role_lines.get(role=role)
            return role_line.calculate_payout()
        except BuildoutRoleLine.DoesNotExist:
            return Decimal('0.00')

    def calculate_percent_of_revenue_per_role(self, role):
        """Calculate percent of revenue per role."""
        payout = self.calculate_payout_per_role(role)
        revenue = self.total_revenue_per_year
        if revenue > 0:
            return (payout / revenue) * 100
        return Decimal('0.00')

    def calculate_base_costs_and_overhead(self):
        """Calculate base costs + location costs + total overhead."""
        total = Decimal('0.00')
        
        # Add base costs
        for assignment in self.base_cost_assignments.all():
            total += assignment.calculate_yearly_cost()
        
        # Add location costs
        for assignment in self.location_assignments.all():
            total += assignment.calculate_yearly_cost()
            
        return total

    @property
    def total_yearly_costs(self):
        """Calculate total yearly costs."""
        role_costs = Decimal('0.00')
        for role_line in self.role_lines.all():
            role_costs += role_line.calculate_payout()
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

    # --- Status transition helpers ---
    def mark_ready(self):
        if self.status not in [self.Status.NEW, self.Status.IN_PROGRESS]:
            raise ValueError("Buildout can only be marked ready from New or In Progress states")
        self.status = self.Status.READY
        self.save(update_fields=["status", "updated_at"])

    def mark_awaiting_signatures(self):
        if self.status != self.Status.READY:
            raise ValueError("Buildout must be in Ready state to await signatures")
        if not self.assigned_contractor_id:
            raise ValueError("Assigned contractor is required before requesting signatures")
        self.status = self.Status.AWAITING_SIGNATURES
        self.save(update_fields=["status", "updated_at"])

    def mark_active(self):
        if self.status != self.Status.AWAITING_SIGNATURES:
            raise ValueError("Buildout can only be activated after signatures are completed")
        self.status = self.Status.ACTIVE
        self.save(update_fields=["status", "updated_at"])

    def clone(self):
        """Create a new version of this buildout."""
        new_buildout = ProgramBuildout.objects.create(
            program_type=self.program_type,
            title=self.title,
            version_number=self.version_number + 1,
            is_new_program=self.is_new_program,
            num_facilitators=self.num_facilitators,
            num_new_facilitators=self.num_new_facilitators,
            students_per_program=self.students_per_program,
            sessions_per_program=self.sessions_per_program,
            rate_per_student=self.rate_per_student
        )
        
        # Copy role lines with all their data
        for role_line in self.role_lines.all():
            BuildoutRoleLine.objects.create(
                buildout=new_buildout,
                role=role_line.role,
                contractor=role_line.contractor,
                pay_type=role_line.pay_type,
                pay_value=role_line.pay_value,
                frequency_unit=role_line.frequency_unit,
                frequency_count=role_line.frequency_count,
                hours_per_frequency=role_line.hours_per_frequency
            )
        
        # Copy responsibility lines
        for resp_line in self.responsibility_lines.all():
            BuildoutResponsibilityLine.objects.create(
                buildout=new_buildout,
                responsibility=resp_line.responsibility,
                hours=resp_line.hours
            )
        
        # Copy base cost assignments with overrides
        for base_cost_assignment in self.base_cost_assignments.all():
            BuildoutBaseCostAssignment.objects.create(
                buildout=new_buildout,
                base_cost=base_cost_assignment.base_cost,
                override_rate=base_cost_assignment.override_rate,
                override_frequency=base_cost_assignment.override_frequency,
                multiplier=base_cost_assignment.multiplier
            )
        
        # Copy location assignments with overrides
        for location_assignment in self.location_assignments.all():
            BuildoutLocationAssignment.objects.create(
                buildout=new_buildout,
                location=location_assignment.location,
                override_rate=location_assignment.override_rate,
                override_frequency=location_assignment.override_frequency,
                multiplier=location_assignment.multiplier
            )
        
        # Copy other related data
        new_buildout.default_forms.set(self.default_forms.all())
        
        return new_buildout


class BuildoutRoleLine(models.Model):
    """Assignment of a role to a buildout with contractor and pay information."""
    buildout = models.ForeignKey(ProgramBuildout, on_delete=models.CASCADE, related_name='role_lines')
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    contractor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='buildout_role_assignments',
        limit_choices_to={'groups__name__in': ['Contractor', 'Admin']}
    )
    
    # Pay structure - version-specific overrides
    pay_type = models.CharField(
        max_length=32,
        choices=[
            ('HOURLY', 'Hourly'),
            ('PER_PROGRAM', 'Per Program'),
            ('PER_SESSION', 'Per Session'),
            ('FLAT_RATE', 'Flat Rate'),
        ],
        default='HOURLY',
        help_text="How this contractor is paid for this role in this version"
    )
    pay_value = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Pay amount for this version"
    )
    
    # Frequency and hours - version-specific overrides
    frequency_unit = models.CharField(
        max_length=32,
        choices=[
            ('PER_PROGRAM_CONCEPT', 'Per Program Concept'),
            ('PER_NEW_FACILITATOR', 'Per New Facilitator'),
            ('PER_PROGRAM', 'Per Program'),
            ('PER_SESSION', 'Per Session'),
            ('PER_CHILD', 'Per Child'),
        ],
        help_text="Frequency unit for this role in this version"
    )
    frequency_count = models.PositiveIntegerField(
        default=1,
        help_text="Multiplier for frequency calculations"
    )
    hours_per_frequency = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Hours per frequency unit for this version"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['buildout', 'role', 'contractor']
        ordering = ['role__title']

    def __str__(self):
        return f"{self.role.title} - {self.contractor.get_full_name()} - {self.buildout.title}"
    
    @classmethod
    def get_available_contractors_for_role(cls, role):
        """Get contractors available for assignment to this role (assigned to role with completed onboarding)."""
        from people.models import Contractor
        
        # Get users assigned to the role who are contractors with completed onboarding
        return User.objects.filter(
            general_role_assignments__role=role,
            groups__name='Contractor',
            contractor__onboarding_complete=True
        ).select_related('profile', 'contractor').distinct()

    def calculate_yearly_hours(self):
        """Calculate total yearly hours for this role line."""
        buildout = self.buildout
        
        if self.frequency_unit == 'PER_PROGRAM_CONCEPT':
            return self.hours_per_frequency * self.frequency_count * (1 if buildout.is_new_program else 0)
        elif self.frequency_unit == 'PER_NEW_FACILITATOR':
            return self.hours_per_frequency * self.frequency_count * buildout.num_new_facilitators
        elif self.frequency_unit == 'PER_PROGRAM':
            return self.hours_per_frequency * self.frequency_count * buildout.num_programs_per_year
        elif self.frequency_unit == 'PER_SESSION':
            return self.hours_per_frequency * self.frequency_count * buildout.total_sessions_per_year
        elif self.frequency_unit == 'PER_CHILD':
            return self.hours_per_frequency * self.frequency_count * buildout.total_students_per_year
        else:
            return Decimal('0.00')

    def calculate_payout(self):
        """Calculate payout for this role line."""
        hours = self.calculate_yearly_hours()
        buildout = self.buildout
        
        if self.pay_type == 'HOURLY':
            return hours * self.pay_value
        elif self.pay_type == 'PER_PROGRAM':
            return self.pay_value * buildout.num_programs_per_year
        elif self.pay_type == 'PER_SESSION':
            return self.pay_value * buildout.total_sessions_per_year
        elif self.pay_type == 'FLAT_RATE':
            return self.pay_value
        else:
            return Decimal('0.00')


class BuildoutResponsibilityLine(models.Model):
    """Assignment of a responsibility to a buildout with version-specific hours."""
    buildout = models.ForeignKey(ProgramBuildout, on_delete=models.CASCADE, related_name='responsibility_lines')
    responsibility = models.ForeignKey(Responsibility, on_delete=models.CASCADE)
    hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Hours per frequency unit for this version"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['buildout', 'responsibility']
        ordering = ['responsibility__role__title', 'responsibility__name']

    def __str__(self):
        return f"{self.responsibility.name} - {self.buildout.title}"

    def calculate_yearly_hours(self):
        """Calculate total yearly hours for this responsibility."""
        buildout = self.buildout
        
        if self.responsibility.frequency_type == ResponsibilityFrequency.PER_PROGRAM_CONCEPT:
            return self.hours * (1 if buildout.is_new_program else 0)
        elif self.responsibility.frequency_type == ResponsibilityFrequency.PER_NEW_FACILITATOR:
            return self.hours * buildout.num_new_facilitators
        elif self.responsibility.frequency_type == ResponsibilityFrequency.PER_PROGRAM:
            return self.hours * buildout.num_programs_per_year
        elif self.responsibility.frequency_type == ResponsibilityFrequency.PER_SESSION:
            return self.hours * buildout.total_sessions_per_year
        elif self.responsibility.frequency_type == ResponsibilityFrequency.PER_CHILD:
            return self.hours * buildout.total_students_per_year
        else:
            return Decimal('0.00')


# Legacy models for backward compatibility - these will be removed in future migrations
class BuildoutRoleAssignment(models.Model):
    """Legacy assignment of a role to a buildout - DEPRECATED."""
    buildout = models.ForeignKey(ProgramBuildout, on_delete=models.CASCADE, related_name='role_assignments_legacy')
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['buildout', 'role']

    def __str__(self):
        return f"{self.role.title} - {self.buildout.title}"


class BuildoutResponsibilityAssignment(models.Model):
    """Legacy assignment of a responsibility to a buildout - DEPRECATED."""
    buildout = models.ForeignKey(ProgramBuildout, on_delete=models.CASCADE, related_name='responsibility_assignments_legacy')
    responsibility = models.ForeignKey(Responsibility, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['buildout', 'responsibility']

    def __str__(self):
        return f"{self.responsibility.name} - {self.buildout.title}"

    def calculate_yearly_hours(self):
        """Calculate yearly hours for this responsibility."""
        buildout = self.buildout
        
        if self.responsibility.frequency_type == ResponsibilityFrequency.PER_PROGRAM_CONCEPT:
            return self.responsibility.default_hours * (1 if buildout.is_new_program else 0)
        elif self.responsibility.frequency_type == ResponsibilityFrequency.PER_NEW_FACILITATOR:
            return self.responsibility.default_hours * buildout.num_new_facilitators
        elif self.responsibility.frequency_type == ResponsibilityFrequency.PER_PROGRAM:
            return self.responsibility.default_hours * buildout.num_programs_per_year
        elif self.responsibility.frequency_type == ResponsibilityFrequency.PER_SESSION:
            return self.responsibility.default_hours * buildout.total_sessions_per_year
        elif self.responsibility.frequency_type == ResponsibilityFrequency.PER_CHILD:
            return self.responsibility.default_hours * buildout.total_students_per_year
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


class Location(models.Model):
    """Physical locations where programs can be held."""
    name = models.CharField(max_length=100, help_text="Location name (e.g., Downtown Community Center)")
    address = models.TextField(blank=True, help_text="Full address of the location")
    description = models.TextField(blank=True, help_text="Additional details about the location")
    
    # Default cost information
    default_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="Default cost amount per frequency unit for this location"
    )
    default_frequency = models.CharField(
        max_length=32,
        choices=ResponsibilityFrequency.choices,
        default=ResponsibilityFrequency.PER_PROGRAM,
        help_text="Default frequency for location costs"
    )
    
    # Capacity and features
    max_capacity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of participants this location can accommodate"
    )
    features = models.TextField(
        blank=True,
        help_text="Special features or amenities (e.g., projector, whiteboard, parking)"
    )
    
    # Contact information
    contact_name = models.CharField(max_length=100, blank=True, help_text="Primary contact person")
    contact_phone = models.CharField(max_length=20, blank=True, help_text="Contact phone number")
    contact_email = models.EmailField(blank=True, help_text="Contact email address")
    
    # Availability
    is_active = models.BooleanField(default=True, help_text="Whether this location is available for booking")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class BuildoutLocationAssignment(models.Model):
    """Assignment of locations to buildouts with specific rate and frequency."""
    buildout = models.ForeignKey(ProgramBuildout, on_delete=models.CASCADE, related_name='location_assignments')
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    
    # Actual rate and frequency for this buildout (defaults loaded from location)
    rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Rate",
        help_text="Location rate for this buildout"
    )
    frequency = models.CharField(
        max_length=32,
        choices=ResponsibilityFrequency.choices,
        null=True,
        blank=True,
        verbose_name="Frequency",
        help_text="Location frequency for this buildout"
    )
    
    multiplier = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=1.00,
        help_text="Multiplier for the final cost calculation"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Keep override fields for backward compatibility during migration
    override_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="DEPRECATED: Use rate field instead"
    )
    override_frequency = models.CharField(
        max_length=32,
        choices=ResponsibilityFrequency.choices,
        null=True,
        blank=True,
        help_text="DEPRECATED: Use frequency field instead"
    )

    class Meta:
        unique_together = ['buildout', 'location']

    def __str__(self):
        return f"{self.location.name} - {self.buildout.title}"

    def calculate_yearly_cost(self):
        """Calculate yearly cost for this location assignment."""
        buildout = self.buildout
        
        # Use the actual rate and frequency fields (with backward compatibility)
        if hasattr(self, 'rate') and self.rate is not None:
            rate = self.rate
        else:
            rate = self.override_rate if self.override_rate is not None else self.location.default_rate
            
        if hasattr(self, 'frequency') and self.frequency:
            frequency = self.frequency
        else:
            frequency = self.override_frequency if self.override_frequency else self.location.default_frequency
            
        base_amount = rate * self.multiplier

        if frequency == ResponsibilityFrequency.PER_PROGRAM_CONCEPT:
            return base_amount * (1 if buildout.is_new_program else 0)
        elif frequency == ResponsibilityFrequency.PER_NEW_FACILITATOR:
            return base_amount * buildout.num_new_facilitators
        elif frequency == ResponsibilityFrequency.PER_PROGRAM:
            return base_amount * buildout.num_programs_per_year
        elif frequency == ResponsibilityFrequency.PER_SESSION:
            return base_amount * buildout.total_sessions_per_year
        elif frequency == ResponsibilityFrequency.PER_CHILD:
            return base_amount * buildout.total_students_per_year
        else:
            return Decimal('0.00')


class BuildoutBaseCostAssignment(models.Model):
    """Assignment of base costs to buildouts with specific rate and frequency."""
    buildout = models.ForeignKey(ProgramBuildout, on_delete=models.CASCADE, related_name='base_cost_assignments')
    base_cost = models.ForeignKey(BaseCost, on_delete=models.CASCADE)
    
    # Actual rate and frequency for this buildout (defaults loaded from base cost)
    rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Rate",
        help_text="Cost rate for this buildout"
    )
    frequency = models.CharField(
        max_length=32,
        choices=ResponsibilityFrequency.choices,
        null=True,
        blank=True,
        verbose_name="Frequency",
        help_text="Cost frequency for this buildout"
    )
    
    multiplier = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=1.00,
        help_text="Multiplier for the final cost calculation"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Keep override fields for backward compatibility during migration
    override_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="DEPRECATED: Use rate field instead"
    )
    override_frequency = models.CharField(
        max_length=32,
        choices=ResponsibilityFrequency.choices,
        null=True,
        blank=True,
        help_text="DEPRECATED: Use frequency field instead"
    )

    class Meta:
        unique_together = ['buildout', 'base_cost']

    def __str__(self):
        return f"{self.base_cost.name} - {self.buildout.title}"

    def calculate_yearly_cost(self):
        """Calculate yearly cost for this base cost assignment."""
        buildout = self.buildout
        
        # Use the actual rate and frequency fields (with backward compatibility)
        if hasattr(self, 'rate') and self.rate is not None:
            rate = self.rate
        else:
            rate = self.override_rate if self.override_rate is not None else self.base_cost.rate
            
        if hasattr(self, 'frequency') and self.frequency:
            frequency = self.frequency
        else:
            frequency = self.override_frequency if self.override_frequency else self.base_cost.frequency
            
        base_amount = rate * self.multiplier

        if frequency == ResponsibilityFrequency.PER_PROGRAM_CONCEPT:
            return base_amount * (1 if buildout.is_new_program else 0)
        elif frequency == ResponsibilityFrequency.PER_NEW_FACILITATOR:
            return base_amount * buildout.num_new_facilitators
        elif frequency == ResponsibilityFrequency.PER_PROGRAM:
            return base_amount * buildout.num_programs_per_year
        elif frequency == ResponsibilityFrequency.PER_SESSION:
            return base_amount * buildout.total_sessions_per_year
        elif frequency == ResponsibilityFrequency.PER_CHILD:
            return base_amount * buildout.total_students_per_year
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
        help_text="JSON object with buildout count overrides (e.g., {'students_per_program': 8})"
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
            'students_per_program': self.buildout.students_per_program,
            'sessions_per_program': self.buildout.sessions_per_program,
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
        for assignment in self.program_instance.buildout.responsibility_lines.filter(responsibility__role=self.role):
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


class ProgramRequest(models.Model):
    """Parent or contractor request for a program type to be offered."""
    REQUEST_TYPES = [
        ('parent_request', 'Parent Program Request'),
        ('contractor_buildout', 'Contractor Buildout Request'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]
    
    request_type = models.CharField(max_length=32, choices=REQUEST_TYPES)
    program_type = models.ForeignKey(ProgramType, on_delete=models.CASCADE, related_name='requests')
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='program_requests', null=True, blank=True)
    
    # Contact information (in case user is not logged in or for additional details)
    contact_name = models.CharField(max_length=100)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20, blank=True)
    
    # Request details
    preferred_location = models.CharField(max_length=200, blank=True, help_text="Preferred location for the program")
    preferred_dates = models.TextField(blank=True, help_text="Preferred dates or time periods")
    expected_participants = models.PositiveIntegerField(blank=True, null=True, help_text="Expected number of participants")
    additional_notes = models.TextField(blank=True, help_text="Additional information or special requests")
    
    # For contractor requests
    contractor_experience = models.TextField(blank=True, help_text="Contractor's experience with this program type")
    proposed_location = models.CharField(max_length=200, blank=True, help_text="Contractor's proposed location")
    
    # Administration
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, help_text="Internal notes for administrators")
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='reviewed_program_requests'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_request_type_display()}: {self.program_type.name} by {self.contact_name}"


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


# ============================================================================
# ENHANCED SCHEDULING SYSTEM MODELS
# ============================================================================

class ContractorAvailability(models.Model):
    """
    Defines when a contractor is available to work and their status.
    
    This model allows contractors to set blocks of time when they're available
    to teach programs. Each availability slot can have multiple programs offered.
    """
    
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('partially_booked', 'Partially Booked'),
        ('fully_booked', 'Fully Booked'),
        ('blocked', 'Blocked/Unavailable'),
    ]
    
    contractor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='availability_slots',
        limit_choices_to={'groups__name__in': ['Contractor', 'Admin']}
    )
    start_datetime = models.DateTimeField(
        help_text="When this availability period starts"
    )
    end_datetime = models.DateTimeField(
        help_text="When this availability period ends"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='available',
        help_text="Current booking status of this time slot"
    )
    
    # Holiday exclusion support
    exclude_holidays = models.BooleanField(
        default=False,
        help_text="If true, this availability will automatically exclude system holidays"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Internal notes about this availability (e.g., 'Prefer morning sessions')"
    )
    
    # Archive and active status
    is_active = models.BooleanField(
        default=True,
        help_text="Auto-set to False when end_datetime is in the past"
    )
    is_archived = models.BooleanField(
        default=False,
        help_text="Set to True when contractor archives this availability"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['start_datetime']
        verbose_name_plural = "Contractor Availability"
    
    def __str__(self):
        return f"{self.contractor.get_full_name()} - {self.start_datetime.strftime('%Y-%m-%d %H:%M')} to {self.end_datetime.strftime('%H:%M')}"
    
    @property
    def duration_hours(self):
        """Calculate total hours in this availability slot."""
        delta = self.end_datetime - self.start_datetime
        return Decimal(str(delta.total_seconds() / 3600))
    
    @property
    def remaining_hours(self):
        """Calculate hours remaining after scheduled sessions."""
        from decimal import Decimal
        scheduled_hours = Decimal('0.00')
        
        # Get all sessions through program offerings
        for offering in self.program_offerings.all():
            for session in offering.sessions.filter(status__in=['scheduled', 'confirmed']):
                scheduled_hours += session.duration_hours
        
        return self.duration_hours - scheduled_hours
    
    def can_accommodate_session(self, duration_hours):
        """Check if this availability can accommodate a session of given duration."""
        return self.remaining_hours >= Decimal(str(duration_hours))
    
    def update_status(self):
        """Update status based on current bookings."""
        if self.remaining_hours <= 0:
            self.status = 'fully_booked'
        elif self.remaining_hours < self.duration_hours:
            self.status = 'partially_booked'
        else:
            self.status = 'available'
        self.save(update_fields=['status'])


class AvailabilityProgram(models.Model):
    """
    Links a contractor's availability slot to specific programs they're willing to teach.
    
    This allows contractors to specify which programs they can teach during 
    each availability period, along with session parameters.
    """
    
    availability = models.ForeignKey(
        ContractorAvailability,
        on_delete=models.CASCADE,
        related_name='program_offerings'
    )
    program_buildout = models.ForeignKey(
        ProgramBuildout,
        on_delete=models.CASCADE,
        related_name='availability_offerings'
    )
    session_duration_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.25'))],
        help_text="Duration in hours for each session of this program (e.g., 1.5 for 90 minutes)"
    )
    max_sessions = models.PositiveIntegerField(
        default=1,
        help_text="Maximum number of sessions of this program that can fit in this availability slot"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['availability', 'program_buildout']
        ordering = ['program_buildout__title']
    
    def __str__(self):
        return f"{self.program_buildout.title} - {self.session_duration_hours}h sessions"
    
    @property
    def total_possible_hours(self):
        """Calculate total hours if all sessions were booked."""
        return self.session_duration_hours * self.max_sessions
    
    def can_add_session(self):
        """Check if another session can be added to this program offering."""
        current_sessions = self.sessions.filter(status__in=['scheduled', 'confirmed']).count()
        return (
            current_sessions < self.max_sessions and
            self.availability.can_accommodate_session(self.session_duration_hours)
        )


class ProgramSession(models.Model):
    """
    Individual session within a program instance.
    
    This represents an actual scheduled session that parents can book their children into.
    Multiple sessions can exist within one availability slot if time permits.
    """
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    program_instance = models.ForeignKey(
        ProgramInstance,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    availability_program = models.ForeignKey(
        AvailabilityProgram,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    start_datetime = models.DateTimeField(
        help_text="When this specific session starts"
    )
    end_datetime = models.DateTimeField(
        help_text="When this specific session ends"
    )
    duration_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        help_text="Actual duration of this session in hours"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled'
    )
    enrolled_count = models.PositiveIntegerField(
        default=0,
        help_text="Current number of children enrolled in this session"
    )
    max_capacity = models.PositiveIntegerField(
        help_text="Maximum children that can attend this session"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['start_datetime']
    
    def __str__(self):
        return f"{self.program_instance.title} - {self.start_datetime.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def available_spots(self):
        """Calculate available spots in this session."""
        return max(0, self.max_capacity - self.enrolled_count)
    
    @property
    def is_full(self):
        """Check if session is at capacity."""
        return self.enrolled_count >= self.max_capacity
    
    @property
    def contractor(self):
        """Get the contractor teaching this session."""
        return self.availability_program.availability.contractor
    
    def can_book(self):
        """Check if this session can accept new bookings."""
        return (
            not self.is_full and
            self.status in ['scheduled', 'confirmed'] and
            self.start_datetime > timezone.now()
        )
    
    def update_enrollment_count(self):
        """Update enrolled count based on confirmed bookings."""
        self.enrolled_count = self.bookings.filter(status='confirmed').count()
        self.save(update_fields=['enrolled_count'])


# ============================================================================
# HOLIDAY AND TIME-OFF MANAGEMENT MODELS
# ============================================================================

class Holiday(models.Model):
    """
    System-wide holidays that affect availability scheduling.
    
    When contractors set recurring availability with 'except for holidays' option,
    these dates will be automatically excluded from their availability.
    """
    
    name = models.CharField(
        max_length=100,
        help_text="Name of the holiday (e.g., 'Christmas Day', 'Independence Day')"
    )
    date = models.DateField(
        help_text="Date of the holiday"
    )
    is_recurring = models.BooleanField(
        default=False,
        help_text="Whether this holiday recurs annually (e.g., Christmas vs. specific observed days)"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description or notes about this holiday"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['date']
        unique_together = ['name', 'date']
    
    def __str__(self):
        return f"{self.name} - {self.date.strftime('%Y-%m-%d')}"


class ContractorDayOffRequest(models.Model):
    """
    Contractor requests for days off that need admin approval.
    
    When approved, these will block availability and alert if there are
    existing bookings that need to be handled.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
        ('cancelled', 'Cancelled'),
    ]
    
    contractor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='day_off_requests',
        limit_choices_to={'groups__name__in': ['Contractor', 'Admin']}
    )
    # Legacy field - will be removed after migration
    date = models.DateField(
        help_text="Date requested for time off (legacy field)",
        null=True,
        blank=True
    )
    start_date = models.DateField(
        help_text="Start date for time off request",
        null=True,  # Temporary: will be made non-null after migration
        blank=True
    )
    end_date = models.DateField(
        help_text="End date for time off request",
        null=True,  # Temporary: will be made non-null after migration
        blank=True
    )
    reason = models.TextField(
        help_text="Reason for time off request"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Admin response
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_day_off_requests',
        limit_choices_to={'groups__name': 'Admin'}
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(
        blank=True,
        help_text="Admin notes about the decision"
    )
    
    # Conflict tracking
    affected_sessions_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of sessions that would be affected by this day off"
    )
    affected_bookings_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of student bookings that would be affected"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['contractor', 'start_date', 'end_date']
    
    def __str__(self):
        if self.start_date and self.end_date:
            if self.start_date == self.end_date:
                return f"{self.contractor.get_full_name()} - {self.start_date.strftime('%Y-%m-%d')} ({self.get_status_display()})"
            else:
                return f"{self.contractor.get_full_name()} - {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')} ({self.get_status_display()})"
        elif self.date:
            return f"{self.contractor.get_full_name()} - {self.date.strftime('%Y-%m-%d')} ({self.get_status_display()})"
        else:
            return f"{self.contractor.get_full_name()} - Date Range ({self.get_status_display()})"
    
    def clean(self):
        """Validate that end_date is not before start_date."""
        from django.core.exceptions import ValidationError
        
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError("End date cannot be before start date.")
    
    def check_conflicts(self):
        """Check for existing sessions and bookings on this date range."""
        from django.utils import timezone
        
        if self.start_date and self.end_date:
            # Find sessions in this date range for this contractor
            affected_sessions = ProgramSession.objects.filter(
                availability_program__availability__contractor=self.contractor,
                start_datetime__date__gte=self.start_date,
                start_datetime__date__lte=self.end_date,
                status__in=['scheduled', 'confirmed']
            )
        elif self.date:
            # Legacy: find sessions on this specific date
            affected_sessions = ProgramSession.objects.filter(
                availability_program__availability__contractor=self.contractor,
                start_datetime__date=self.date,
                status__in=['scheduled', 'confirmed']
            )
        else:
            affected_sessions = ProgramSession.objects.none()
        
        # Count bookings for these sessions
        affected_bookings = SessionBooking.objects.filter(
            session__in=affected_sessions,
            status__in=['pending', 'confirmed']
        )
        
        self.affected_sessions_count = affected_sessions.count()
        self.affected_bookings_count = affected_bookings.count()
        self.save(update_fields=['affected_sessions_count', 'affected_bookings_count'])
        
        return {
            'sessions': affected_sessions,
            'bookings': affected_bookings
        }
    
    def approve(self, admin_user, admin_notes=""):
        """Approve the day off request and block availability."""
        self.status = 'approved'
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.admin_notes = admin_notes
        self.save()
        
        # Block any existing availability for this date
        ContractorAvailability.objects.filter(
            contractor=self.contractor,
            start_datetime__date=self.date
        ).update(status='blocked')


class SessionBooking(models.Model):
    """
    Individual child's booking for a specific session.
    
    This allows parents to book their children into specific sessions,
    replacing the previous program-instance level registration system.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending Confirmation'),
        ('confirmed', 'Confirmed'),
        ('waitlisted', 'Waitlisted'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]
    
    session = models.ForeignKey(
        ProgramSession,
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    child = models.ForeignKey(
        Child,
        on_delete=models.CASCADE,
        related_name='session_bookings'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    booked_at = models.DateTimeField(auto_now_add=True)
    parent_notes = models.TextField(
        blank=True,
        help_text="Special notes or requests from parent"
    )
    
    # Form responses from registration
    form_responses = models.JSONField(
        blank=True,
        null=True,
        help_text="Responses to any required forms for this booking"
    )
    
    # Metadata
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['session', 'child']
        ordering = ['-booked_at']
    
    def __str__(self):
        return f"{self.child.full_name} - {self.session}"
    
    @property
    def parent(self):
        """Get the parent who made this booking."""
        return self.child.parent
    
    @property
    def can_cancel(self):
        """Check if this booking can be cancelled."""
        from datetime import timedelta
        return (
            self.status in ['pending', 'confirmed', 'waitlisted'] and
            self.session.start_datetime > timezone.now() + timedelta(hours=24)  # 24hr cancellation policy
        )
    
    def confirm_booking(self):
        """Confirm this booking and update session enrollment."""
        if self.session.can_book():
            self.status = 'confirmed'
            self.save()
            self.session.update_enrollment_count()
            return True
        return False
    
    def cancel_booking(self):
        """Cancel this booking and update session enrollment."""
        if self.can_cancel:
            self.status = 'cancelled'
            self.save()
            self.session.update_enrollment_count()
            return True
        return False


class ProgramBuildoutScheduling(models.Model):
    """
    Extension to ProgramBuildout for scheduling-specific settings.
    
    This model extends the existing ProgramBuildout with scheduling parameters
    without modifying the core model structure.
    """
    
    buildout = models.OneToOneField(
        ProgramBuildout,
        on_delete=models.CASCADE,
        related_name='scheduling_config'
    )
    default_session_duration = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('1.0'),
        help_text="Default duration in hours for sessions of this program"
    )
    min_session_duration = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('0.5'),
        help_text="Minimum allowed session duration"
    )
    max_session_duration = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('4.0'),
        help_text="Maximum allowed session duration"
    )
    max_students_per_session = models.PositiveIntegerField(
        default=12,
        help_text="Maximum students allowed per individual session"
    )
    requires_advance_booking = models.BooleanField(
        default=True,
        help_text="Whether bookings must be made in advance"
    )
    advance_booking_hours = models.PositiveIntegerField(
        default=24,
        help_text="Minimum hours in advance that bookings must be made"
    )
    
    class Meta:
        verbose_name = "Program Scheduling Configuration"
        verbose_name_plural = "Program Scheduling Configurations"
    
    def __str__(self):
        return f"Scheduling config for {self.buildout.title}"
