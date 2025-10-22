"""
Tests for role preview template tags.
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.template import Context, Template
from django.contrib.sessions.middleware import SessionMiddleware

User = get_user_model()


class RoleTagsTestCase(TestCase):
    """Tests for role_tags template tags."""
    
    def setUp(self):
        """Set up test users and roles."""
        self.factory = RequestFactory()
        
        # Create roles
        self.admin_group = Group.objects.get_or_create(name='Admin')[0]
        self.parent_group = Group.objects.get_or_create(name='Parent')[0]
        self.contractor_group = Group.objects.get_or_create(name='Contractor')[0]
        
        # Create multi-role user
        self.multi_role_user = User.objects.create_user(
            email='multi@example.com',
            password='testpass123'
        )
        self.multi_role_user.groups.add(self.admin_group, self.parent_group, self.contractor_group)
    
    def get_request_with_session(self, user, effective_role='Auto'):
        """Helper to create a request with session."""
        request = self.factory.get('/')
        request.user = user
        
        # Add session
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        # Set effective_role if not Auto
        if effective_role != 'Auto':
            request.session['effective_role'] = effective_role
        
        return request
    
    def render_template(self, template_string, context_dict):
        """Helper to render a template with context."""
        template = Template(template_string)
        context = Context(context_dict)
        return template.render(context)
    
    def test_show_role_menu_auto_mode(self):
        """In Auto mode, show_role_menu shows menu if user has the role."""
        request = self.get_request_with_session(self.multi_role_user, 'Auto')
        
        template = Template('{% load role_tags %}{% show_role_menu "Admin" as show_menu %}{{ show_menu }}')
        context = Context({'request': request, 'effective_role': 'Auto'})
        result = template.render(context)
        
        self.assertEqual(result.strip(), 'True')
    
    def test_show_role_menu_specific_role(self):
        """When effective_role is set, only show that role's menu."""
        request = self.get_request_with_session(self.multi_role_user, 'Parent')
        
        # Should show Parent menu
        template = Template('{% load role_tags %}{% show_role_menu "Parent" as show_menu %}{{ show_menu }}')
        context = Context({'request': request, 'effective_role': 'Parent'})
        result = template.render(context)
        self.assertEqual(result.strip(), 'True')
        
        # Should NOT show Admin menu
        template = Template('{% load role_tags %}{% show_role_menu "Admin" as show_menu %}{{ show_menu }}')
        context = Context({'request': request, 'effective_role': 'Parent'})
        result = template.render(context)
        self.assertEqual(result.strip(), 'False')
    
    def test_show_role_menu_no_privilege_escalation(self):
        """Cannot show menu for role user doesn't have."""
        # Create user with only Parent role
        parent_user = User.objects.create_user(
            email='parent@example.com',
            password='testpass123'
        )
        parent_user.groups.add(self.parent_group)
        
        request = self.get_request_with_session(parent_user, 'Auto')
        
        # Should NOT show Admin menu even in Auto mode
        template = Template('{% load role_tags %}{% show_role_menu "Admin" as show_menu %}{{ show_menu }}')
        context = Context({'request': request, 'effective_role': 'Auto'})
        result = template.render(context)
        self.assertEqual(result.strip(), 'False')
    
    def test_should_show_contractor_menu_auto(self):
        """Contractor menu shows for users with Contractor or Admin role in Auto mode."""
        request = self.get_request_with_session(self.multi_role_user, 'Auto')
        
        template = Template('{% load role_tags %}{% should_show_contractor_menu as show_menu %}{{ show_menu }}')
        context = Context({'request': request, 'effective_role': 'Auto'})
        result = template.render(context)
        
        self.assertEqual(result.strip(), 'True')
    
    def test_should_show_contractor_menu_specific_role(self):
        """Contractor menu only shows when previewing Contractor role, not Admin."""
        # Should show when previewing as Contractor
        request = self.get_request_with_session(self.multi_role_user, 'Contractor')
        
        template = Template('{% load role_tags %}{% should_show_contractor_menu as show_menu %}{{ show_menu }}')
        context = Context({'request': request, 'effective_role': 'Contractor'})
        result = template.render(context)
        
        self.assertEqual(result.strip(), 'True')
        
        # Should NOT show when previewing as Admin
        request = self.get_request_with_session(self.multi_role_user, 'Admin')
        
        template = Template('{% load role_tags %}{% should_show_contractor_menu as show_menu %}{{ show_menu }}')
        context = Context({'request': request, 'effective_role': 'Admin'})
        result = template.render(context)
        
        self.assertEqual(result.strip(), 'False')
        
        # Should NOT show when previewing as Parent
        request = self.get_request_with_session(self.multi_role_user, 'Parent')
        
        template = Template('{% load role_tags %}{% should_show_contractor_menu as show_menu %}{{ show_menu }}')
        context = Context({'request': request, 'effective_role': 'Parent'})
        result = template.render(context)
        
        self.assertEqual(result.strip(), 'False')

