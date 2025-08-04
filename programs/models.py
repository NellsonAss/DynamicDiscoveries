from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
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


class ProgramInstance(models.Model):
    """Specific offering of a ProgramType with scheduling details."""
    program_type = models.ForeignKey(
        ProgramType,
        on_delete=models.CASCADE,
        related_name='instances'
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
