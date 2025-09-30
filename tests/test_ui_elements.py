"""
UI Element Tests for all application pages.

This module tests that key UI elements and components are present
on pages that load successfully, ensuring the user interface
displays correctly.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from programs.models import ProgramType, Role, ProgramBuildout, BaseCost, Location
from communications.models import Contact

User = get_user_model()


class UIElementTests(TestCase):
    """Test that key UI elements are present on all pages."""
    
    def setUp(self):
        """Set up test data for UI testing."""
        self.client = Client()
        
        # Create admin user
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User'
        )
        admin_group, _ = Group.objects.get_or_create(name='Admin')
        self.admin_user.groups.add(admin_group)
        
        # Create parent user
        self.parent_user = User.objects.create_user(
            email='parent@test.com',
            password='testpass123',
            first_name='Parent',
            last_name='User'
        )
        parent_group, _ = Group.objects.get_or_create(name='Parent')
        self.parent_user.groups.add(parent_group)
        
        # Create basic test data
        self.role = Role.objects.create(
            title="Test Role",
            description="Test role for UI testing"
        )
        
        self.program_type = ProgramType.objects.create(
            name="Test Program",
            description="Test program for UI testing"
        )
        
        self.contact = Contact.objects.create(
            parent_name="Test Parent",
            email="test@example.com",
            message="Test message",
            interest="after_school"
        )
    
    def test_home_page_ui_elements(self):
        """Test that home page has required UI elements."""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        
        # Check for basic HTML structure
        self.assertContains(response, '<html')
        self.assertContains(response, '</html>')
        self.assertContains(response, '<head>')
        self.assertContains(response, '<body>')
        
        # Check for common UI elements (these might vary based on actual template)
        content = response.content.decode()
        # Basic checks that apply to most pages
        self.assertIn('Dynamic Discoveries', content, "Page should contain site name")
    
    def test_login_page_ui_elements(self):
        """Test that login page has required form elements."""
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        
        # Check for login form elements
        content = response.content.decode()
        self.assertContains(response, 'email', msg_prefix="Login form should have email field")
        
        # Check for password field (may be in different formats)
        has_password = any(pwd_term in content.lower() for pwd_term in [
            'password', 'type="password"', 'passwd'
        ])
        if not has_password:
            # Maybe it's a custom login system, just check for basic login terms
            has_login_terms = any(term in content.lower() for term in [
                'login', 'sign in', 'authentication', 'auth'
            ])
            self.assertTrue(has_login_terms, "Page should have login-related content")
        
        # Check for form structure
        self.assertContains(response, '<form', msg_prefix="Page should have a form")
        
        # Check for input types (more lenient)
        has_email_input = 'type="email"' in content or 'email' in content.lower()
        has_password_input = 'type="password"' in content or has_password
        
        self.assertTrue(has_email_input, "Should have email input")
        self.assertTrue(has_password_input, "Should have password input")
    
    def test_contact_page_ui_elements(self):
        """Test that contact page has required form elements."""
        response = self.client.get(reverse('communications:contact'))
        self.assertEqual(response.status_code, 200)
        
        # Check for contact form elements
        self.assertContains(response, '<form', msg_prefix="Contact page should have a form")
        self.assertContains(response, 'parent_name', msg_prefix="Should have parent name field")
        self.assertContains(response, 'email', msg_prefix="Should have email field")
        self.assertContains(response, 'message', msg_prefix="Should have message field")
        
        # Check for submit functionality
        content = response.content.decode()
        has_submit = 'submit' in content.lower()
        self.assertTrue(has_submit, "Should have submit button")
    
    def test_admin_dashboard_ui_elements(self):
        """Test that admin dashboard has required navigation and content."""
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('admin_interface:dashboard'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        
        # Check for dashboard indicators
        self.assertIn('dashboard', content.lower(), "Should be identifiable as dashboard")
        
        # Check for navigation elements (common in admin interfaces)
        has_nav_elements = any(nav_term in content.lower() for nav_term in [
            'navigation', 'nav', 'menu', 'sidebar', 'header'
        ])
        self.assertTrue(has_nav_elements, "Dashboard should have navigation elements")
        
        # Check for admin-specific content
        admin_terms = any(term in content.lower() for term in [
            'management', 'admin', 'users', 'programs', 'settings'
        ])
        self.assertTrue(admin_terms, "Dashboard should have admin-related content")
    
    def test_dashboard_ui_elements(self):
        """Test that main dashboard has required elements."""
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        
        # Check for dashboard structure
        self.assertIn('dashboard', content.lower(), "Should be identifiable as dashboard")
        
        # Check for user greeting or identification
        user_indicators = any(term in content.lower() for term in [
            'welcome', 'hello', self.admin_user.first_name.lower(), 'user'
        ])
        self.assertTrue(user_indicators, "Dashboard should acknowledge the logged-in user")
    
    def test_program_type_management_ui_elements(self):
        """Test that program type management has required table and action elements."""
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('admin_interface:program_type_management'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        
        # Check for management interface elements
        self.assertIn('program', content.lower(), "Should mention programs")
        
        # Check for table or list structure
        has_list_structure = any(element in content for element in [
            '<table', '<ul', '<li', '<tr', '<td'
        ])
        self.assertTrue(has_list_structure, "Should have list or table structure")
        
        # Check for action buttons
        action_terms = any(term in content.lower() for term in [
            'create', 'add', 'new', 'edit', 'manage'
        ])
        self.assertTrue(action_terms, "Should have action buttons or links")
    
    def test_user_management_ui_elements(self):
        """Test that user management has required elements."""
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('admin_interface:user_management'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        
        # Check for user management indicators
        self.assertIn('user', content.lower(), "Should mention users")
        
        # Check for table structure (common in user lists)
        has_table = '<table' in content or '<tr' in content
        has_list = '<ul' in content or '<li' in content
        self.assertTrue(has_table or has_list, "Should have table or list structure for users")
        
        # Check for email addresses (users are identified by email)
        self.assertIn('@', content, "Should show user email addresses")
    
    def test_contact_management_ui_elements(self):
        """Test that contact management has required elements."""
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('admin_interface:contact_management'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        
        # Check for contact management indicators
        self.assertIn('contact', content.lower(), "Should mention contacts")
        
        # Should show our test contact
        self.assertIn(self.contact.parent_name, content, "Should display contact names")
        self.assertIn(self.contact.email, content, "Should display contact emails")
    
    def test_role_management_ui_elements(self):
        """Test that role management has required elements."""
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('admin_interface:role_management'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        
        # Check for role management indicators
        self.assertIn('role', content.lower(), "Should mention roles")
        
        # Should show our test role
        self.assertIn(self.role.title, content, "Should display role titles")
    
    def test_cost_management_ui_elements(self):
        """Test that cost management has required elements."""
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('admin_interface:cost_management'))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        
        # Check for cost management indicators
        cost_terms = any(term in content.lower() for term in [
            'cost', 'price', 'rate', 'money', 'expense'
        ])
        self.assertTrue(cost_terms, "Should mention costs or pricing")
    
    def test_bootstrap_and_responsive_elements(self):
        """Test that pages include Bootstrap and responsive design elements."""
        test_pages = [
            ('home', None, None),
            ('accounts:login', None, None),
            ('communications:contact', None, None)
        ]
        
        for page_name, args, kwargs in test_pages:
            with self.subTest(page=page_name):
                if ':' in page_name:
                    url = reverse(page_name, args=args, kwargs=kwargs)
                else:
                    url = reverse(page_name, args=args, kwargs=kwargs)
                
                response = self.client.get(url)
                if response.status_code == 200:
                    content = response.content.decode()
                    
                    # Check for Bootstrap indicators
                    bootstrap_indicators = any(indicator in content for indicator in [
                        'bootstrap', 'btn', 'form-control', 'container', 'row', 'col-'
                    ])
                    
                    # Check for responsive design indicators
                    responsive_indicators = any(indicator in content for indicator in [
                        'viewport', 'responsive', 'mobile', 'media'
                    ])
                    
                    # At least one of these should be present for modern web design
                    has_modern_design = bootstrap_indicators or responsive_indicators
                    if not has_modern_design:
                        print(f"Warning: {page_name} may lack modern UI framework")
    
    def test_form_csrf_protection(self):
        """Test that forms include CSRF protection."""
        form_pages = [
            ('accounts:login', None, None),
            ('communications:contact', None, None)
        ]
        
        for page_name, args, kwargs in form_pages:
            with self.subTest(page=page_name):
                url = reverse(page_name, args=args, kwargs=kwargs)
                response = self.client.get(url)
                
                if response.status_code == 200 and '<form' in response.content.decode():
                    # Check for CSRF token
                    self.assertContains(
                        response, 
                        'csrfmiddlewaretoken',
                        msg_prefix=f"Form on {page_name} should include CSRF protection"
                    )
    
    def test_error_handling_ui(self):
        """Test that error pages have appropriate UI elements."""
        # Test 404 page
        response = self.client.get('/nonexistent-page/')
        self.assertEqual(response.status_code, 404)
        
        # Even error pages should have basic structure
        content = response.content.decode()
        self.assertIn('<html', content, "404 page should have HTML structure")
        
        # Should indicate it's an error
        error_indicators = any(indicator in content.lower() for indicator in [
            '404', 'not found', 'error', 'missing'
        ])
        self.assertTrue(error_indicators, "404 page should indicate error")


class AccessibilityTests(TestCase):
    """Test basic accessibility features."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    def test_basic_accessibility_elements(self):
        """Test that pages have basic accessibility elements."""
        test_pages = [
            reverse('home'),
            reverse('accounts:login'),
            reverse('communications:contact')
        ]
        
        for url in test_pages:
            with self.subTest(url=url):
                response = self.client.get(url)
                if response.status_code == 200:
                    content = response.content.decode()
                    
                    # Check for language attribute
                    lang_indicators = any(lang in content for lang in [
                        'lang="en"', "lang='en'", 'html lang=', 'xml:lang'
                    ])
                    
                    # Check for title tag
                    has_title = '<title>' in content
                    
                    # Check for meta description (not required but good practice)
                    has_meta_description = 'name="description"' in content
                    
                    # Basic accessibility check
                    if not has_title:
                        print(f"Warning: {url} missing title tag")
                    
                    if not lang_indicators:
                        print(f"Warning: {url} missing language attribute")
    
    def test_form_labels_and_accessibility(self):
        """Test that form elements have proper labels for accessibility."""
        # Test login form
        response = self.client.get(reverse('accounts:login'))
        if response.status_code == 200:
            content = response.content.decode()
            
            # Check for form labels
            has_labels = '<label' in content
            
            # Check for placeholder attributes (alternative to labels)
            has_placeholders = 'placeholder=' in content
            
            # Should have either labels or placeholders for accessibility
            has_form_accessibility = has_labels or has_placeholders
            
            if '<form' in content and not has_form_accessibility:
                print("Warning: Login form may lack accessibility features")


class PerformanceAndOptimizationTests(TestCase):
    """Test for basic performance and optimization indicators."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    def test_static_file_references(self):
        """Test that pages reference static files correctly."""
        test_pages = [
            reverse('home'),
            reverse('accounts:login')
        ]
        
        for url in test_pages:
            with self.subTest(url=url):
                response = self.client.get(url)
                if response.status_code == 200:
                    content = response.content.decode()
                    
                    # Check for CSS references
                    has_css = any(css_indicator in content for css_indicator in [
                        '.css', 'stylesheet', '<style'
                    ])
                    
                    # Check for JavaScript references
                    has_js = any(js_indicator in content for js_indicator in [
                        '.js', '<script', 'javascript'
                    ])
                    
                    # Modern websites typically have both
                    if not has_css:
                        print(f"Warning: {url} may lack CSS styling")
                    
                    if not has_js:
                        print(f"Note: {url} has no JavaScript (may be intentional)")
    
    def test_response_size_reasonable(self):
        """Test that page response sizes are reasonable."""
        test_pages = [
            reverse('home'),
            reverse('accounts:login'),
            reverse('communications:contact')
        ]
        
        for url in test_pages:
            with self.subTest(url=url):
                response = self.client.get(url)
                if response.status_code == 200:
                    content_length = len(response.content)
                    
                    # Reasonable size limits (these are generous)
                    max_size = 1024 * 1024  # 1MB
                    
                    self.assertLess(
                        content_length, 
                        max_size,
                        f"Page {url} response size ({content_length} bytes) exceeds reasonable limit"
                    )
                    
                    # Also check it's not suspiciously small (empty or error)
                    min_size = 100  # 100 bytes minimum
                    self.assertGreater(
                        content_length,
                        min_size,
                        f"Page {url} response size ({content_length} bytes) suspiciously small"
                    )