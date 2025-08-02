from django import forms
from captcha.fields import CaptchaField


class LoginForm(forms.Form):
    """Form for login with CAPTCHA."""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    captcha = CaptchaField()


class SignupForm(forms.Form):
    """Form for signup with CAPTCHA."""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    captcha = CaptchaField() 