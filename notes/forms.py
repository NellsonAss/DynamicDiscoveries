from django import forms
from .models import StudentNote, ParentNote


class StudentNoteForm(forms.ModelForm):
    """Form for creating and editing student notes."""
    
    class Meta:
        model = StudentNote
        fields = ['title', 'body', 'visibility_scope']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional title for the note'
            }),
            'body': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter note content...',
                'required': True
            }),
            'visibility_scope': forms.RadioSelect(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'title': 'Title (Optional)',
            'body': 'Note Content',
            'visibility_scope': 'Visibility'
        }
        help_texts = {
            'visibility_scope': 'Choose who can see this note'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to radio buttons
        self.fields['visibility_scope'].widget.attrs.update({'class': 'form-check-input'})
        
    def clean(self):
        cleaned_data = super().clean()
        body = cleaned_data.get('body', '').strip()
        visibility_scope = cleaned_data.get('visibility_scope')
        
        if visibility_scope == 'public_parent' and not body:
            raise forms.ValidationError("Cannot make an empty note visible to parents.")
        
        return cleaned_data

    def save(self, commit=True):
        note = super().save(commit=False)
        
        # Sync is_public with visibility_scope
        note.is_public = (note.visibility_scope == 'public_parent')
        
        if commit:
            note.save()
        return note


class ParentNoteForm(forms.ModelForm):
    """Form for creating and editing parent notes."""
    
    class Meta:
        model = ParentNote
        fields = ['title', 'body', 'visibility_scope']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional title for the note'
            }),
            'body': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter note content...',
                'required': True
            }),
            'visibility_scope': forms.RadioSelect(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'title': 'Title (Optional)',
            'body': 'Note Content',
            'visibility_scope': 'Visibility'
        }
        help_texts = {
            'visibility_scope': 'Choose who can see this note'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to radio buttons
        self.fields['visibility_scope'].widget.attrs.update({'class': 'form-check-input'})
        
    def clean(self):
        cleaned_data = super().clean()
        body = cleaned_data.get('body', '').strip()
        visibility_scope = cleaned_data.get('visibility_scope')
        
        if visibility_scope == 'public_parent' and not body:
            raise forms.ValidationError("Cannot make an empty note visible to parents.")
        
        return cleaned_data

    def save(self, commit=True):
        note = super().save(commit=False)
        
        # Sync is_public with visibility_scope
        note.is_public = (note.visibility_scope == 'public_parent')
        
        if commit:
            note.save()
        return note
