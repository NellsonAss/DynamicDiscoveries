from django import forms
from django.contrib.auth import get_user_model
from .models import (
    Child, RegistrationForm, FormQuestion, ProgramInstance,
    ProgramType, Role, ProgramBuildout, BuildoutResponsibility, 
    BuildoutRoleAssignment, BaseCost, BuildoutBaseCost
)

User = get_user_model()


class RoleForm(forms.ModelForm):
    """Form for creating and editing roles."""
    
    class Meta:
        model = Role
        fields = ['name', 'hourly_rate', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'hourly_rate': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


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
        fields = [
            'name', 'description', 'scope', 'target_grade_levels', 'rate_per_student',
            'default_num_facilitators', 'default_num_new_facilitators',
            'default_workshops_per_facilitator_per_year', 'default_students_per_workshop',
            'default_sessions_per_workshop', 'default_new_workshop_concepts_per_year',
            'default_registration_form'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'scope': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'target_grade_levels': forms.TextInput(attrs={'class': 'form-control'}),
            'rate_per_student': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'class': 'form-control'}),
            'default_num_facilitators': forms.NumberInput(attrs={'min': '1', 'class': 'form-control'}),
            'default_num_new_facilitators': forms.NumberInput(attrs={'min': '0', 'class': 'form-control'}),
            'default_workshops_per_facilitator_per_year': forms.NumberInput(attrs={'min': '1', 'class': 'form-control'}),
            'default_students_per_workshop': forms.NumberInput(attrs={'min': '1', 'class': 'form-control'}),
            'default_sessions_per_workshop': forms.NumberInput(attrs={'min': '1', 'class': 'form-control'}),
            'default_new_workshop_concepts_per_year': forms.NumberInput(attrs={'min': '0', 'class': 'form-control'}),
            'default_registration_form': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure all fields have proper styling
        for field in self.fields.values():
            if hasattr(field.widget, 'attrs'):
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control'
            else:
                field.widget.attrs = {'class': 'form-control'}


class ProgramBuildoutForm(forms.ModelForm):
    """Form for creating and editing program buildouts."""
    class Meta:
        model = ProgramBuildout
        fields = [
            'program_type', 'title', 'num_facilitators', 'num_new_facilitators',
            'workshops_per_facilitator_per_year', 'students_per_workshop',
            'sessions_per_workshop', 'new_workshop_concepts_per_year'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'num_facilitators': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'num_new_facilitators': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'workshops_per_facilitator_per_year': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'students_per_workshop': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'sessions_per_workshop': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'new_workshop_concepts_per_year': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'program_type': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure all fields have proper styling
        for field in self.fields.values():
            if hasattr(field.widget, 'attrs'):
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control'
            else:
                field.widget.attrs = {'class': 'form-control'}
    
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