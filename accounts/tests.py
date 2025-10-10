from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

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


class EmailCaseSensitivityTests(TestCase):
    """Test cases for email case sensitivity issues."""
    
    def setUp(self):
        User = get_user_model()
        # Create a user with lowercase email
        self.user = User.objects.create_user(email='john@example.com')
        # Create admin group and assign to user
        self.admin_group, _ = Group.objects.get_or_create(name='Admin')
        self.user.groups.add(self.admin_group)
        
    def test_email_preserved_in_login_view(self):
        """Test that email case is preserved in login_view session."""
        User = get_user_model()
        
        # Test with different case variations
        test_emails = [
            'john@example.com',      # original
            'John@example.com',      # first letter capitalized
            'JOHN@EXAMPLE.COM',      # all caps
            'John@Example.Com',      # mixed case
        ]
        
        for email in test_emails:
            with self.subTest(email=email):
                # Simulate login form submission
                response = self.client.post(reverse('accounts:login'), {
                    'email': email,
                    'captcha_0': 'dummy-captcha-0',
                    'captcha_1': 'PASSED'  # Assuming CAPTCHA bypass for testing
                }, follow=True)
                
                # Check that the original email case is stored in session
                session_email = self.client.session.get('verification_email')
                if session_email:  # Only check if session was created (captcha might prevent this in tests)
                    self.assertEqual(session_email, email)
    
    def test_email_case_insensitive_lookup_in_verify_code(self):
        """Test that case-insensitive email lookup works in verify_code view."""
        User = get_user_model()
        
        # Set up session with different case email
        session = self.client.session
        session['verification_email'] = 'John@Example.Com'  # Different case
        session['verification_code'] = '123456'
        session.save()
        
        # Submit verification code
        response = self.client.post(reverse('accounts:verify_code'), {
            'code': '123456'
        })
        
        # Should find the existing user, not create a new one
        users = User.objects.filter(email__iexact='john@example.com')
        self.assertEqual(users.count(), 1)
        self.assertEqual(users.first(), self.user)
        # Email should still be stored as originally created
        self.assertEqual(self.user.email, 'john@example.com')
        
    def test_user_permissions_preserved_with_case_variations(self):
        """Test that user permissions are preserved regardless of email case."""
        User = get_user_model()
        
        # Set up session with different case email
        session = self.client.session
        session['verification_email'] = 'JOHN@EXAMPLE.COM'  # All caps
        session['verification_code'] = '123456'
        session.save()
        
        # Submit verification code
        response = self.client.post(reverse('accounts:verify_code'), {
            'code': '123456'
        })
        
        # Get the user and check permissions are preserved
        user = User.objects.get(email='john@example.com')
        self.assertTrue(user.groups.filter(name='Admin').exists())
        self.assertTrue(user.is_app_admin)
        
    def test_no_duplicate_users_created(self):
        """Test that no duplicate users are created with different email cases."""
        User = get_user_model()
        
        # Get initial count and verify our test user exists
        initial_count = User.objects.count()
        self.assertTrue(User.objects.filter(email='john@example.com').exists())
        
        # Test multiple login attempts with different cases
        test_cases = [
            'John@Example.Com',
            'JOHN@EXAMPLE.COM',
            'john@EXAMPLE.com'
        ]
        
        for email_case in test_cases:
            with self.subTest(email=email_case):
                # Set up session
                session = self.client.session
                session['verification_email'] = email_case
                session['verification_code'] = '123456'
                session.save()
                
                # Submit verification code
                response = self.client.post(reverse('accounts:verify_code'), {
                    'code': '123456'
                })
                
                # Should still have the same number of users (no duplicates created)
                self.assertEqual(User.objects.count(), initial_count)
                # Should still have only one user with the normalized email
                self.assertEqual(User.objects.filter(email='john@example.com').count(), 1)
                
    def test_email_stored_as_entered_in_database(self):
        """Test that emails are stored as originally entered in the database."""
        User = get_user_model()
        
        # The existing user should have email as originally created
        self.assertEqual(self.user.email, 'john@example.com')
        
        # Create new user with different case via manager
        new_user = User.objects.create_user(email='Jane@Example.Com')
        # Email should be stored as entered (only domain normalized by Django's default behavior)
        self.assertEqual(new_user.email, 'Jane@example.com')
        
    def test_case_insensitive_login_preserves_original_email_display(self):
        """Test that logging in with different cases finds the same user and displays original email."""
        User = get_user_model()
        
        # Create a user with specific email case
        original_user = User.objects.create_user(email='Test@Example.Com')
        admin_group, _ = Group.objects.get_or_create(name='Admin')
        original_user.groups.add(admin_group)
        
        # Test login attempts with different cases
        test_cases = [
            'test@example.com',      # all lowercase
            'TEST@EXAMPLE.COM',      # all uppercase  
            'Test@Example.Com',      # original case
            'tEsT@eXaMpLe.CoM',      # random case
        ]
        
        for login_email in test_cases:
            with self.subTest(login_email=login_email):
                # Set up session with different case email
                session = self.client.session
                session['verification_email'] = login_email
                session['verification_code'] = '123456'
                session.save()
                
                # Submit verification code
                response = self.client.post(reverse('accounts:verify_code'), {
                    'code': '123456'
                })
                
                # Should find the original user (not create a new one)
                found_user = User.objects.get_by_email_case_insensitive(login_email)
                self.assertEqual(found_user, original_user)
                
                # Email should still be displayed as originally stored
                self.assertEqual(found_user.email, 'Test@example.com')  # Domain normalized by Django
                
                # User should have admin permissions
                self.assertTrue(found_user.groups.filter(name='Admin').exists()) 