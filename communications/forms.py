from django import forms
from captcha.fields import CaptchaField
from django.contrib.auth import get_user_model
from .models import Conversation, Message

User = get_user_model()


class ContactComposeForm(forms.Form):
    """Form for authenticated users to compose new messages."""
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Message subject'
        }),
        required=True
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Your message...'
        }),
        required=True
    )
    honeypot = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={
            'style': 'display:none !important;',
            'tabindex': '-1',
            'autocomplete': 'off'
        })
    )
    
    def clean_honeypot(self):
        """Check that the honeypot field is empty."""
        honeypot = self.cleaned_data.get('honeypot')
        if honeypot:
            raise forms.ValidationError("Bot detected. Please try again.")
        return honeypot


class ContactQuickForm(forms.Form):
    """Form for anonymous users to create account and send message."""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your@email.com'
        }),
        required=True
    )
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name (optional)'
        }),
        required=False
    )
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name (optional)'
        }),
        required=False
    )
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Message subject'
        }),
        required=True
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Your message...'
        }),
        required=True
    )
    captcha = CaptchaField()
    honeypot = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={
            'style': 'display:none !important;',
            'tabindex': '-1',
            'autocomplete': 'off'
        })
    )
    
    def clean_honeypot(self):
        """Check that the honeypot field is empty."""
        honeypot = self.cleaned_data.get('honeypot')
        if honeypot:
            raise forms.ValidationError("Bot detected. Please try again.")
        return honeypot
    
    def clean_email(self):
        """Validate email format."""
        email = self.cleaned_data.get('email')
        # Don't check for existing email here - let the view handle it
        # so we can show the login CTA
        return email


class MessageReplyForm(forms.Form):
    """Form for replying to existing conversations."""
    body = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Type your reply...'
        }),
        required=True
    )
    honeypot = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={
            'style': 'display:none !important;',
            'tabindex': '-1',
            'autocomplete': 'off'
        })
    )
    
    def clean_honeypot(self):
        """Check that the honeypot field is empty."""
        honeypot = self.cleaned_data.get('honeypot')
        if honeypot:
            raise forms.ValidationError("Bot detected. Please try again.")
        return honeypot
