from django import forms
from django.contrib.auth import get_user_model
from django.forms import inlineformset_factory
from datetime import datetime, timedelta
from .models import (
    Child, RegistrationForm, FormQuestion, ProgramInstance,
    ProgramType, Role, Responsibility, ProgramBuildout, BuildoutResponsibilityAssignment, 
    BuildoutRoleAssignment, BaseCost, BuildoutBaseCostAssignment, Location, BuildoutLocationAssignment,
    ContractorAvailability, AvailabilityProgram, ProgramSession, SessionBooking,
    ProgramBuildoutScheduling, ContractorDayOffRequest, ProgramRequest
)
from django.db import models

User = get_user_model()


class RoleForm(forms.ModelForm):
    """Form for creating and editing roles."""
    
    class Meta:
        model = Role
        fields = ['title', 'description', 'visible_to_parents', 'default_responsibilities']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'default_responsibilities': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class ResponsibilityForm(forms.ModelForm):
    """Form for creating and editing responsibilities."""
    
    class Meta:
        model = Responsibility
        fields = ['role', 'name', 'description', 'frequency_type', 'default_hours']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter responsibility name...'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'default_hours': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
    
    def clean(self):
        """Custom validation to handle unique_together constraint gracefully."""
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        name = cleaned_data.get('name')
        
        if role and name:
            # Check if another responsibility with this role/name combination exists
            existing_responsibility = Responsibility.objects.filter(role=role, name=name)
            
            # If this is an edit (self.instance exists and has a pk), exclude the current instance
            if self.instance and self.instance.pk:
                existing_responsibility = existing_responsibility.exclude(pk=self.instance.pk)
            
            if existing_responsibility.exists():
                raise forms.ValidationError(
                    f"A responsibility named '{name}' already exists for the role '{role.title}'. "
                    "Please choose a different name."
                )
        
        return cleaned_data


class ChildForm(forms.ModelForm):
    """Form for creating and editing children."""
    
    class Meta:
        model = Child
        fields = [
            'first_name', 'last_name', 'date_of_birth', 'grade_level',
            'special_needs', 'emergency_contact', 'emergency_phone'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'special_needs': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class RegistrationFormForm(forms.ModelForm):
    """Form for creating and editing registration forms."""
    
    class Meta:
        model = RegistrationForm
        fields = ['title', 'description', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class FormQuestionForm(forms.ModelForm):
    """Form for creating and editing form questions."""
    
    class Meta:
        model = FormQuestion
        fields = ['question_text', 'question_type', 'is_required', 'options', 'order']
        widgets = {
            'question_text': forms.TextInput(attrs={'placeholder': 'Enter your question...'}),
            'options': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Enter options as JSON array, e.g., ["Option 1", "Option 2"]'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        
        # Make options field conditional
        self.fields['options'].required = False
    
    def clean_options(self):
        """Validate options field for select/radio/checkbox questions."""
        options = self.cleaned_data.get('options')
        question_type = self.cleaned_data.get('question_type')
        
        if question_type in ['select', 'radio', 'checkbox'] and not options:
            raise forms.ValidationError(
                "Options are required for select, radio, and checkbox questions."
            )
        
        return options


class ProgramInstanceForm(forms.ModelForm):
    """Form for creating and editing program instances."""
    
    class Meta:
        model = ProgramInstance
        fields = [
            'buildout', 'title', 'start_date', 'end_date', 'location',
            'capacity', 'assigned_form', 'is_active'
        ]
        widgets = {
            'start_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'end_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'title': forms.TextInput(attrs={'placeholder': 'Enter program title...'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
    
    def clean(self):
        """Validate that end_date is after start_date."""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date <= start_date:
            raise forms.ValidationError(
                "End date must be after start date."
            )
        
        return cleaned_data


class ProgramTypeForm(forms.ModelForm):
    """Form for creating and editing program types."""
    
    class Meta:
        model = ProgramType
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure all fields have proper styling
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class ProgramBuildoutForm(forms.ModelForm):
    """Form for creating and editing program buildouts."""
    class Meta:
        model = ProgramBuildout
        fields = [
            'program_type', 'title', 'version_number', 'is_active',
            'is_new_program', 'num_facilitators', 'num_new_facilitators',
            'students_per_program', 'sessions_per_program', 'new_program_concepts_per_year',
            'rate_per_student'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'version_number': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'num_facilitators': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'num_new_facilitators': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'students_per_program': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'sessions_per_program': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'new_program_concepts_per_year': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'rate_per_student': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'program_type': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_new_program': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure all fields have proper styling, but preserve checkbox styling for Boolean fields
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                # For checkboxes, use Bootstrap's form-check-input class
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                # For other fields, use form-control class
                field.widget.attrs.update({'class': 'form-control'})
    
    def clean(self):
        """Validate buildout configuration."""
        cleaned_data = super().clean()
        num_facilitators = cleaned_data.get('num_facilitators')
        num_new_facilitators = cleaned_data.get('num_new_facilitators')
        
        if num_facilitators and num_new_facilitators and num_new_facilitators > num_facilitators:
            raise forms.ValidationError(
                "Number of new facilitators cannot exceed total number of facilitators."
            )
        
        return cleaned_data


class BaseCostForm(forms.ModelForm):
    """Form for creating and editing base costs."""
    
    class Meta:
        model = BaseCost
        fields = ['name', 'description', 'rate', 'frequency']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter cost name...'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'rate': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class LocationForm(forms.ModelForm):
    """Form for creating and editing locations."""
    
    class Meta:
        model = Location
        fields = [
            'name', 'address', 'description', 'default_rate', 'default_frequency',
            'max_capacity', 'features', 'contact_name', 'contact_phone', 
            'contact_email', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter location name...'}),
            'address': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Enter full address...'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Additional details...'}),
            'default_rate': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'max_capacity': forms.NumberInput(attrs={'min': '1'}),
            'features': forms.Textarea(attrs={'rows': 2, 'placeholder': 'e.g., projector, whiteboard, parking...'}),
            'contact_name': forms.TextInput(attrs={'placeholder': 'Primary contact person...'}),
            'contact_phone': forms.TextInput(attrs={'placeholder': 'Phone number...'}),
            'contact_email': forms.EmailInput(attrs={'placeholder': 'Email address...'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        
        # Special handling for select fields
        self.fields['default_frequency'].widget.attrs.update({'class': 'form-select'})


class BuildoutBaseCostAssignmentForm(forms.ModelForm):
    """Form for assigning base costs to buildouts with default value preloading."""
    
    class Meta:
        model = BuildoutBaseCostAssignment
        fields = ['base_cost', 'override_rate', 'override_frequency', 'multiplier']
        widgets = {
            'base_cost': forms.Select(attrs={'class': 'form-select cost-selector'}),
            'override_rate': forms.NumberInput(attrs={
                'class': 'form-control override-field', 
                'step': '0.01',
                'data-field-type': 'rate'
            }),
            'override_frequency': forms.Select(attrs={
                'class': 'form-select override-field',
                'data-field-type': 'frequency'
            }),
            'multiplier': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If we have an instance and a base_cost, preload defaults
        if self.instance and self.instance.base_cost_id:
            base_cost = self.instance.base_cost
            
            # Always set data attributes for JavaScript
            self.fields['override_rate'].widget.attrs['data-default-value'] = str(base_cost.rate)
            self.fields['override_frequency'].widget.attrs['data-default-value'] = base_cost.frequency
            
            # Set initial values - use override if exists, otherwise use default
            if self.instance.override_rate is not None:
                self.fields['override_rate'].initial = self.instance.override_rate
            else:
                self.fields['override_rate'].initial = base_cost.rate
            
            if self.instance.override_frequency:
                self.fields['override_frequency'].initial = self.instance.override_frequency
            else:
                self.fields['override_frequency'].initial = base_cost.frequency
        
        # Add help text to show current behavior
        self.fields['override_rate'].help_text = "Leave blank to use the base cost default rate"
        self.fields['override_frequency'].help_text = "Leave blank to use the base cost default frequency"


class BuildoutLocationAssignmentForm(forms.ModelForm):
    """Form for assigning locations to buildouts with default value preloading."""
    
    class Meta:
        model = BuildoutLocationAssignment
        fields = ['location', 'override_rate', 'override_frequency', 'multiplier']
        widgets = {
            'location': forms.Select(attrs={'class': 'form-select location-selector'}),
            'override_rate': forms.NumberInput(attrs={
                'class': 'form-control override-field', 
                'step': '0.01',
                'data-field-type': 'rate'
            }),
            'override_frequency': forms.Select(attrs={
                'class': 'form-select override-field',
                'data-field-type': 'frequency'
            }),
            'multiplier': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If we have an instance and a location, preload defaults
        if self.instance and self.instance.location_id:
            location = self.instance.location
            
            # Always set data attributes for JavaScript
            self.fields['override_rate'].widget.attrs['data-default-value'] = str(location.default_rate)
            self.fields['override_frequency'].widget.attrs['data-default-value'] = location.default_frequency
            
            # Set initial values - use override if exists, otherwise use default
            if self.instance.override_rate is not None:
                self.fields['override_rate'].initial = self.instance.override_rate
            else:
                self.fields['override_rate'].initial = location.default_rate
            
            if self.instance.override_frequency:
                self.fields['override_frequency'].initial = self.instance.override_frequency
            else:
                self.fields['override_frequency'].initial = location.default_frequency
        
        # Add help text to show current behavior
        self.fields['override_rate'].help_text = "Leave blank to use the location default rate"
        self.fields['override_frequency'].help_text = "Leave blank to use the location default frequency"


class BuildoutResponsibilityAssignmentForm(forms.ModelForm):
    """Form for assigning responsibilities to buildouts."""
    
    class Meta:
        model = BuildoutResponsibilityAssignment
        fields = ['responsibility']
        widgets = {
            'responsibility': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class BuildoutRoleAssignmentForm(forms.ModelForm):
    """Form for assigning roles to buildouts."""
    
    class Meta:
        model = BuildoutRoleAssignment
        fields = ['role']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class BuildoutBaseCostAssignmentForm(forms.ModelForm):
    """Form for assigning base costs to buildouts."""
    
    class Meta:
        model = BuildoutBaseCostAssignment
        fields = ['base_cost', 'rate', 'frequency', 'multiplier']
        widgets = {
            'base_cost': forms.Select(attrs={'class': 'form-select'}),
            'rate': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'frequency': forms.Select(attrs={'class': 'form-select'}),
            'multiplier': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'value': '1.00'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        # Keep the select widgets with form-select class
        self.fields['base_cost'].widget.attrs.update({'class': 'form-select'})
        self.fields['frequency'].widget.attrs.update({'class': 'form-select'})
        
        # Load defaults from base cost when creating new assignment
        if not self.instance.pk and 'base_cost' in self.data:
            try:
                from programs.models import BaseCost
                base_cost = BaseCost.objects.get(pk=self.data['base_cost'])
                if not self.instance.rate:
                    self.initial['rate'] = base_cost.rate
                if not self.instance.frequency:
                    self.initial['frequency'] = base_cost.frequency
            except (BaseCost.DoesNotExist, ValueError):
                pass

# Create inline formset for base cost assignments
BuildoutBaseCostAssignmentFormSet = inlineformset_factory(
    ProgramBuildout,
    BuildoutBaseCostAssignment,
    form=BuildoutBaseCostAssignmentForm,
    extra=1,
    can_delete=True,
    fields=['base_cost', 'rate', 'frequency', 'multiplier']
)


class BuildoutLocationAssignmentForm(forms.ModelForm):
    """Form for assigning locations to buildouts."""
    
    class Meta:
        model = BuildoutLocationAssignment
        fields = ['location', 'rate', 'frequency', 'multiplier']
        widgets = {
            'location': forms.Select(attrs={'class': 'form-select'}),
            'rate': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'frequency': forms.Select(attrs={'class': 'form-select'}),
            'multiplier': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'value': '1.00'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        # Keep the select widgets with form-select class
        self.fields['location'].widget.attrs.update({'class': 'form-select'})
        self.fields['frequency'].widget.attrs.update({'class': 'form-select'})
        
        # Load defaults from location when creating new assignment
        if not self.instance.pk and 'location' in self.data:
            try:
                from programs.models import Location
                location = Location.objects.get(pk=self.data['location'])
                if not self.instance.rate:
                    self.initial['rate'] = location.default_rate
                if not self.instance.frequency:
                    self.initial['frequency'] = location.default_frequency
            except (Location.DoesNotExist, ValueError):
                pass

# Create inline formset for location assignments
BuildoutLocationAssignmentFormSet = inlineformset_factory(
    ProgramBuildout,
    BuildoutLocationAssignment,
    form=BuildoutLocationAssignmentForm,
    extra=1,
    can_delete=True,
    fields=['location', 'rate', 'frequency', 'multiplier']
)


class RegistrationForm(forms.Form):
    """Dynamic form for registration form responses."""
    
    def __init__(self, form_instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_instance = form_instance
        
        # Dynamically create form fields based on form questions
        for question in form_instance.questions.all():
            field_name = f"question_{question.pk}"
            
            if question.question_type == 'text':
                field = forms.CharField(
                    max_length=500,
                    required=question.is_required,
                    widget=forms.TextInput(attrs={'class': 'form-control'})
                )
            elif question.question_type == 'textarea':
                field = forms.CharField(
                    required=question.is_required,
                    widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
                )
            elif question.question_type == 'email':
                field = forms.EmailField(
                    required=question.is_required,
                    widget=forms.EmailInput(attrs={'class': 'form-control'})
                )
            elif question.question_type == 'phone':
                field = forms.CharField(
                    max_length=20,
                    required=question.is_required,
                    widget=forms.TextInput(attrs={'class': 'form-control'})
                )
            elif question.question_type == 'select':
                choices = [(opt, opt) for opt in question.options or []]
                field = forms.ChoiceField(
                    choices=choices,
                    required=question.is_required,
                    widget=forms.Select(attrs={'class': 'form-control'})
                )
            elif question.question_type == 'radio':
                choices = [(opt, opt) for opt in question.options or []]
                field = forms.ChoiceField(
                    choices=choices,
                    required=question.is_required,
                    widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
                )
            elif question.question_type == 'checkbox':
                choices = [(opt, opt) for opt in question.options or []]
                field = forms.MultipleChoiceField(
                    choices=choices,
                    required=question.is_required,
                    widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
                )
            elif question.question_type == 'date':
                field = forms.DateField(
                    required=question.is_required,
                    widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
                )
            elif question.question_type == 'number':
                field = forms.IntegerField(
                    required=question.is_required,
                    widget=forms.NumberInput(attrs={'class': 'form-control'})
                )
            else:
                field = forms.CharField(
                    required=question.is_required,
                    widget=forms.TextInput(attrs={'class': 'form-control'})
                )
            
            field.label = question.question_text
            field.help_text = "Required" if question.is_required else "Optional"
            
            self.fields[field_name] = field


class ChildSelectionForm(forms.Form):
    """Form for selecting a child to register."""
    child = forms.ModelChoiceField(
        queryset=Child.objects.none(),
        empty_label="Select a child...",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, parent_user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['child'].queryset = Child.objects.filter(parent=parent_user)


# ============================================================================
# SCHEDULING FORMS
# ============================================================================

class ContractorAvailabilityForm(forms.ModelForm):
    """Form for contractors to set their availability with improved date/time selection and repeating options."""
    
    # Availability type choices
    AVAILABILITY_TYPE_CHOICES = [
        ('single', 'Single Date'),
        ('range', 'Date Range'),
        ('recurring', 'Recurring (Weekly)'),
    ]
    
    availability_type = forms.ChoiceField(
        choices=AVAILABILITY_TYPE_CHOICES,
        initial='single',
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        }),
        label="Availability Type"
    )
    
    # Single date field
    date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="Date",
        required=False
    )
    
    # Date range fields
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="Start Date",
        required=False
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="End Date",
        required=False
    )
    
    # Recurring options
    WEEKDAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    recurring_weekdays = forms.MultipleChoiceField(
        choices=WEEKDAY_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        label="Days of the Week",
        required=False
    )
    
    recurring_until = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="Repeat Until",
        required=False,
        help_text="Last date to create recurring availability"
    )
    
    exclude_holidays = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label="Except for holidays",
        help_text="Automatically exclude system holidays from recurring availability"
    )
    
    # Time fields
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'class': 'form-control',
            'type': 'time',
            'step': '900'  # 15-minute intervals
        }),
        label="Start Time"
    )
    end_time = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'class': 'form-control',
            'type': 'time',
            'step': '900'  # 15-minute intervals
        }),
        label="End Time"
    )
    
    # Common time presets
    PRESET_CHOICES = [
        ('', 'Select a preset (optional)'),
        ('morning', 'Morning (9:00 AM - 12:00 PM)'),
        ('afternoon', 'Afternoon (1:00 PM - 5:00 PM)'),
        ('evening', 'Evening (6:00 PM - 9:00 PM)'),
        ('full_day', 'Full Day (9:00 AM - 5:00 PM)'),
        ('custom', 'Custom Times'),
    ]
    
    time_preset = forms.ChoiceField(
        choices=PRESET_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'time-preset'
        }),
        label="Quick Time Presets"
    )
    
    class Meta:
        model = ContractorAvailability
        fields = ['notes', 'exclude_holidays']
        widgets = {
            'notes': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Optional notes about this availability (e.g., "Prefer morning sessions")'
                }
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['notes'].required = False
        
        # Set initial values if editing existing availability
        if self.instance and self.instance.pk:
            self.fields['date'].initial = self.instance.start_datetime.date()
            self.fields['start_time'].initial = self.instance.start_datetime.time()
            self.fields['end_time'].initial = self.instance.end_datetime.time()
            self.fields['availability_type'].initial = 'single'
        else:
            # Set default date to today
            from datetime import date, time
            self.fields['date'].initial = date.today()
            self.fields['start_date'].initial = date.today()
            self.fields['start_time'].initial = time(9, 0)  # 9:00 AM
            self.fields['end_time'].initial = time(17, 0)   # 5:00 PM
    
    def clean(self):
        cleaned_data = super().clean()
        availability_type = cleaned_data.get('availability_type')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if not start_time or not end_time:
            raise forms.ValidationError("Start time and end time are required.")
        
        # Validate time range
        from datetime import datetime, timedelta
        temp_date = datetime.now().date()
        start_datetime = datetime.combine(temp_date, start_time)
        end_datetime = datetime.combine(temp_date, end_time)
        
        # Handle overnight availability (end time next day)
        if end_time <= start_time:
            end_datetime = datetime.combine(temp_date + timedelta(days=1), end_time)
        
        if start_datetime >= end_datetime:
            raise forms.ValidationError("End time must be after start time.")
        
        # Check for minimum duration (30 minutes)
        if end_datetime - start_datetime < timedelta(minutes=30):
            raise forms.ValidationError("Availability must be at least 30 minutes long.")
        
        # Validate based on availability type
        if availability_type == 'single':
            date = cleaned_data.get('date')
            if not date:
                raise forms.ValidationError("Date is required for single date availability.")
            
            # Check that availability is not in the past (with timezone awareness)
            from django.utils import timezone
            start_dt = timezone.make_aware(datetime.combine(date, start_time))
            if start_dt < timezone.now():
                raise forms.ValidationError("Availability cannot be set in the past.")
                
        elif availability_type == 'range':
            start_date = cleaned_data.get('start_date')
            end_date = cleaned_data.get('end_date')
            
            if not start_date or not end_date:
                raise forms.ValidationError("Start date and end date are required for date range availability.")
            
            if start_date > end_date:
                raise forms.ValidationError("End date must be after start date.")
            
            # Check that start date is not in the past
            from django.utils import timezone
            start_dt = timezone.make_aware(datetime.combine(start_date, start_time))
            if start_dt < timezone.now():
                raise forms.ValidationError("Start date cannot be in the past.")
                
        elif availability_type == 'recurring':
            recurring_weekdays = cleaned_data.get('recurring_weekdays')
            recurring_until = cleaned_data.get('recurring_until')
            
            if not recurring_weekdays:
                raise forms.ValidationError("Please select at least one day of the week for recurring availability.")
            
            if not recurring_until:
                raise forms.ValidationError("Please specify an end date for recurring availability.")
            
            # Check that end date is in the future
            if recurring_until <= datetime.now().date():
                raise forms.ValidationError("Recurring end date must be in the future.")
        
        return cleaned_data
    
    def save(self, commit=True):
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        availability_type = self.cleaned_data.get('availability_type')
        start_time = self.cleaned_data.get('start_time')
        end_time = self.cleaned_data.get('end_time')
        
        instances = []
        
        if availability_type == 'single':
            # Create single availability
            date = self.cleaned_data.get('date')
            instance = super().save(commit=False)
            instance.exclude_holidays = self.cleaned_data.get('exclude_holidays', False)
            
            # Create timezone-aware datetimes
            instance.start_datetime = timezone.make_aware(datetime.combine(date, start_time))
            end_datetime = datetime.combine(date, end_time)
            if end_time <= start_time:
                end_datetime = datetime.combine(date + timedelta(days=1), end_time)
            instance.end_datetime = timezone.make_aware(end_datetime)
            
            if commit:
                instance.save()
            instances.append(instance)
            
        elif availability_type == 'range':
            # Create availability for each day in range
            start_date = self.cleaned_data.get('start_date')
            end_date = self.cleaned_data.get('end_date')
            current_date = start_date
            
            while current_date <= end_date:
                instance = ContractorAvailability()
                instance.contractor = self.instance.contractor
                instance.notes = self.cleaned_data.get('notes', '')
                instance.exclude_holidays = self.cleaned_data.get('exclude_holidays', False)
                
                # Create timezone-aware datetimes
                instance.start_datetime = timezone.make_aware(datetime.combine(current_date, start_time))
                end_datetime = datetime.combine(current_date, end_time)
                if end_time <= start_time:
                    end_datetime = datetime.combine(current_date + timedelta(days=1), end_time)
                instance.end_datetime = timezone.make_aware(end_datetime)
                
                if commit:
                    instance.save()
                instances.append(instance)
                current_date += timedelta(days=1)
                
        elif availability_type == 'recurring':
            # Create recurring availability
            recurring_weekdays = [int(day) for day in self.cleaned_data.get('recurring_weekdays')]
            recurring_until = self.cleaned_data.get('recurring_until')
            exclude_holidays = self.cleaned_data.get('exclude_holidays', False)
            
            # Get holiday dates if excluding holidays
            holiday_dates = set()
            if exclude_holidays:
                from .models import Holiday
                holidays = Holiday.objects.filter(
                    date__gte=datetime.now().date(),
                    date__lte=recurring_until
                )
                holiday_dates = set(holiday.date for holiday in holidays)
            
            # Start from next occurrence of selected weekdays
            current_date = datetime.now().date()
            while current_date <= recurring_until:
                if current_date.weekday() in recurring_weekdays:
                    # Skip if excluding holidays and this is a holiday
                    if exclude_holidays and current_date in holiday_dates:
                        current_date += timedelta(days=1)
                        continue
                        
                    # Skip if in the past
                    temp_start = timezone.make_aware(datetime.combine(current_date, start_time))
                    if temp_start >= timezone.now():
                        instance = ContractorAvailability()
                        instance.contractor = self.instance.contractor
                        instance.notes = self.cleaned_data.get('notes', '')
                        instance.exclude_holidays = exclude_holidays
                        
                        # Create timezone-aware datetimes
                        instance.start_datetime = temp_start
                        end_datetime = datetime.combine(current_date, end_time)
                        if end_time <= start_time:
                            end_datetime = datetime.combine(current_date + timedelta(days=1), end_time)
                        instance.end_datetime = timezone.make_aware(end_datetime)
                        
                        if commit:
                            instance.save()
                        instances.append(instance)
                
                current_date += timedelta(days=1)
        
        # Return the first instance for compatibility
        return instances[0] if instances else super().save(commit=commit)


class AvailabilityProgramForm(forms.ModelForm):
    """Form for adding programs to availability slots."""
    
    class Meta:
        model = AvailabilityProgram
        fields = ['program_buildout', 'session_duration_hours', 'max_sessions']
        widgets = {
            'program_buildout': forms.Select(attrs={'class': 'form-control'}),
            'session_duration_hours': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.25',
                    'min': '0.25',
                    'max': '8.0'
                }
            ),
            'max_sessions': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': '1',
                    'max': '10'
                }
            ),
        }
    
    def __init__(self, contractor=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter buildouts to only show those the contractor is assigned to
        if contractor:
            assigned_buildouts = ProgramBuildout.objects.filter(
                role_lines__contractor=contractor
            ).distinct()
            self.fields['program_buildout'].queryset = assigned_buildouts
        
        self.fields['session_duration_hours'].label = "Session Duration (Hours)"
        self.fields['max_sessions'].label = "Maximum Sessions"
        
        # Set help text
        self.fields['session_duration_hours'].help_text = "Duration in hours (e.g., 1.5 for 90 minutes)"
        self.fields['max_sessions'].help_text = "How many sessions of this program can fit in this time slot"


class ContractorDayOffRequestForm(forms.ModelForm):
    """Form for contractors to request days off."""
    
    class Meta:
        model = ContractorDayOffRequest
        fields = ['start_date', 'end_date', 'reason']
        widgets = {
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'min': datetime.now().date().isoformat()
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'min': datetime.now().date().isoformat()
            }),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Please explain the reason for your time off request...'
            })
        }
    
    def __init__(self, contractor=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.contractor = contractor
        
        # Set minimum date to tomorrow
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        self.fields['start_date'].widget.attrs['min'] = tomorrow.isoformat()
        self.fields['end_date'].widget.attrs['min'] = tomorrow.isoformat()
        
        self.fields['start_date'].help_text = "Select the start date for your time off"
        self.fields['end_date'].help_text = "Select the end date for your time off"
        self.fields['reason'].help_text = "Provide a brief explanation for your request"
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            # Must be in the future
            if start_date <= datetime.now().date():
                raise forms.ValidationError("Day off requests must be for future dates.")
            
            # End date cannot be before start date
            if end_date < start_date:
                raise forms.ValidationError("End date cannot be before start date.")
            
            # Check if there's already a request that overlaps with this date range
            if self.contractor:
                existing = ContractorDayOffRequest.objects.filter(
                    contractor=self.contractor,
                    status__in=['pending', 'approved']
                ).filter(
                    # Check for overlap: existing request overlaps with new request
                    models.Q(start_date__lte=end_date) & models.Q(end_date__gte=start_date)
                ).exists()
                
                if existing:
                    raise forms.ValidationError("You already have a day off request that overlaps with this date range.")
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.contractor:
            instance.contractor = self.contractor
        if commit:
            instance.save()
        return instance


class SessionBookingForm(forms.ModelForm):
    """Form for parents to book children into sessions."""
    
    class Meta:
        model = SessionBooking
        fields = ['parent_notes']
        widgets = {
            'parent_notes': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Any special notes or requests for this session (optional)'
                }
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parent_notes'].required = False
        self.fields['parent_notes'].label = "Special Notes"


class ProgramSessionForm(forms.ModelForm):
    """Form for creating/editing program sessions."""
    
    class Meta:
        model = ProgramSession
        fields = ['start_datetime', 'end_datetime', 'max_capacity']
        widgets = {
            'start_datetime': forms.DateTimeInput(
                attrs={
                    'class': 'form-control',
                    'type': 'datetime-local'
                }
            ),
            'end_datetime': forms.DateTimeInput(
                attrs={
                    'class': 'form-control',
                    'type': 'datetime-local'
                }
            ),
            'max_capacity': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': '1',
                    'max': '50'
                }
            ),
        }
    
    def __init__(self, availability_program=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.availability_program = availability_program
        
        if availability_program:
            # Set max capacity from scheduling config if available
            if hasattr(availability_program.program_buildout, 'scheduling_config'):
                default_capacity = availability_program.program_buildout.scheduling_config.max_students_per_session
                self.fields['max_capacity'].initial = default_capacity
    
    def clean(self):
        cleaned_data = super().clean()
        start_datetime = cleaned_data.get('start_datetime')
        end_datetime = cleaned_data.get('end_datetime')
        
        if start_datetime and end_datetime:
            if start_datetime >= end_datetime:
                raise forms.ValidationError("End time must be after start time.")
            
            # Validate against availability program constraints
            if self.availability_program:
                availability = self.availability_program.availability
                
                # Check if session fits within availability window
                if start_datetime < availability.start_datetime or end_datetime > availability.end_datetime:
                    raise forms.ValidationError(
                        f"Session must be within availability window: "
                        f"{availability.start_datetime} to {availability.end_datetime}"
                    )
                
                # Check duration matches expected
                from decimal import Decimal
                duration = Decimal(str((end_datetime - start_datetime).total_seconds() / 3600))
                expected_duration = self.availability_program.session_duration_hours
                
                if abs(duration - expected_duration) > Decimal('0.1'):  # Allow 6-minute tolerance
                    raise forms.ValidationError(
                        f"Session duration ({duration}h) should match expected duration ({expected_duration}h)"
                    )
        
        return cleaned_data


class ProgramBuildoutSchedulingForm(forms.ModelForm):
    """Form for configuring scheduling settings for a program buildout."""
    
    class Meta:
        model = ProgramBuildoutScheduling
        fields = [
            'default_session_duration', 'min_session_duration', 'max_session_duration',
            'max_students_per_session', 'requires_advance_booking', 'advance_booking_hours'
        ]
        widgets = {
            'default_session_duration': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.25', 'min': '0.25'}
            ),
            'min_session_duration': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.25', 'min': '0.25'}
            ),
            'max_session_duration': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.25', 'min': '0.25'}
            ),
            'max_students_per_session': forms.NumberInput(
                attrs={'class': 'form-control', 'min': '1'}
            ),
            'requires_advance_booking': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
            'advance_booking_hours': forms.NumberInput(
                attrs={'class': 'form-control', 'min': '1'}
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set labels and help text
        self.fields['default_session_duration'].label = "Default Session Duration (Hours)"
        self.fields['min_session_duration'].label = "Minimum Session Duration (Hours)"
        self.fields['max_session_duration'].label = "Maximum Session Duration (Hours)"
        self.fields['max_students_per_session'].label = "Maximum Students Per Session"
        self.fields['requires_advance_booking'].label = "Requires Advance Booking"
        self.fields['advance_booking_hours'].label = "Advance Booking Hours Required"
        
        self.fields['advance_booking_hours'].help_text = "Minimum hours in advance bookings must be made"
    
    def clean(self):
        cleaned_data = super().clean()
        min_duration = cleaned_data.get('min_session_duration')
        default_duration = cleaned_data.get('default_session_duration')
        max_duration = cleaned_data.get('max_session_duration')
        
        if min_duration and default_duration and max_duration:
            if not (min_duration <= default_duration <= max_duration):
                raise forms.ValidationError(
                    "Duration constraints must follow: minimum ≤ default ≤ maximum"
                )
        
        return cleaned_data


class ProgramRequestForm(forms.ModelForm):
    """Form for parents and contractors to request programs."""
    
    class Meta:
        model = ProgramRequest
        fields = [
            'request_type', 'contact_name', 'contact_email', 'contact_phone',
            'preferred_location', 'preferred_dates', 'expected_participants',
            'additional_notes', 'contractor_experience', 'proposed_location'
        ]
        widgets = {
            'request_type': forms.Select(attrs={'class': 'form-control'}),
            'contact_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your full name'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'your.email@example.com'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(555) 123-4567'}),
            'preferred_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Downtown Community Center'}),
            'preferred_dates': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'e.g., Weekday evenings in March, or specific dates'
            }),
            'expected_participants': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': '10'}),
            'additional_notes': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4,
                'placeholder': 'Any special requirements, accommodations, or additional information'
            }),
            'contractor_experience': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4,
                'placeholder': 'Describe your experience with this type of program (for contractor requests)'
            }),
            'proposed_location': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Where you would like to run the program (for contractor requests)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make some fields conditional based on request type
        self.fields['contact_phone'].required = False
        self.fields['expected_participants'].required = False
        self.fields['contractor_experience'].required = False
        self.fields['proposed_location'].required = False
        
        # Set help text
        self.fields['preferred_dates'].help_text = "When would you like this program to run?"
        self.fields['expected_participants'].help_text = "Approximate number of children/participants"
        self.fields['contractor_experience'].help_text = "Only required for contractor buildout requests"
        self.fields['proposed_location'].help_text = "Only required for contractor buildout requests"
    
    def clean(self):
        cleaned_data = super().clean()
        request_type = cleaned_data.get('request_type')
        
        # Validate contractor-specific fields
        if request_type == 'contractor_buildout':
            if not cleaned_data.get('contractor_experience'):
                raise forms.ValidationError("Experience description is required for contractor buildout requests.")
            
            if not cleaned_data.get('proposed_location'):
                raise forms.ValidationError("Proposed location is required for contractor buildout requests.")
        
        return cleaned_data


# Formsets for managing multiple related objects
AvailabilityProgramFormSet = forms.inlineformset_factory(
    ContractorAvailability,
    AvailabilityProgram,
    form=AvailabilityProgramForm,
    extra=1,
    can_delete=True
) 