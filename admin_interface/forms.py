from django import forms
from programs.models import ProgramInstance, ProgramBuildout, RegistrationForm
from django.core.exceptions import ValidationError
from django.utils import timezone


class AdminProgramInstanceForm(forms.ModelForm):
    """Custom form for creating and editing program instances in the admin interface."""
    
    class Meta:
        model = ProgramInstance
        fields = [
            'buildout', 'title', 'start_date', 'end_date', 'location',
            'capacity', 'assigned_form', 'is_active'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter program instance title...'
            }),
            'start_date': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control'
                },
                format='%Y-%m-%dT%H:%M'
            ),
            'end_date': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control'
                },
                format='%Y-%m-%dT%H:%M'
            ),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter location (e.g., Community Center - Room 101)'
            }),
            'capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'Maximum number of students'
            }),
            'buildout': forms.Select(attrs={'class': 'form-select'}),
            'assigned_form': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        # If buildout is provided in initial data, filter the buildout choices
        initial_buildout = kwargs.get('initial', {}).get('buildout')
        super().__init__(*args, **kwargs)
        
        # Filter buildout choices if a specific buildout is provided
        if initial_buildout:
            self.fields['buildout'].queryset = ProgramBuildout.objects.filter(id=initial_buildout)
            self.fields['buildout'].initial = initial_buildout
        
        # Filter form choices to only show active forms
        self.fields['assigned_form'].queryset = RegistrationForm.objects.filter(is_active=True)
        
        # Set default values
        if not self.instance.pk:  # Only for new instances
            self.fields['is_active'].initial = True
            if initial_buildout:
                buildout = ProgramBuildout.objects.filter(id=initial_buildout).first()
                if buildout:
                    self.fields['title'].initial = f"{buildout.title} - {timezone.now().strftime('%Y')}"
                    self.fields['capacity'].initial = buildout.students_per_program
    
    def clean(self):
        """Validate form data."""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        capacity = cleaned_data.get('capacity')
        buildout = cleaned_data.get('buildout')
        
        # Validate dates
        if start_date and end_date:
            if end_date <= start_date:
                raise ValidationError("End date must be after start date.")
            
            if start_date <= timezone.now():
                raise ValidationError("Start date must be in the future.")
        
        # Validate capacity
        if capacity and capacity < 1:
            raise ValidationError("Capacity must be at least 1.")
        
        # Validate buildout
        if buildout and not buildout.is_active:
            raise ValidationError("Cannot create instances for inactive buildouts.")
        
        return cleaned_data
