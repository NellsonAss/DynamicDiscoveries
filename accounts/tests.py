from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

class AccountsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
    def test_login_page(self):
        """Test that login page loads correctly."""
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')
        
    def test_verify_code_page(self):
        """Test that verify code page loads correctly."""
        # Set up session
        session = self.client.session
        session['login_email'] = 'test@example.com'
        session['verification_email'] = 'test@example.com'
        session['verification_code'] = '000000'
        session.save()
        
        response = self.client.get(reverse('accounts:verify_code'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/verify_code.html')
        
    def test_profile_page(self):
        """Test that profile page requires login."""
        # Test without login
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 302)
        
        # Test with login
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/profile.html') 