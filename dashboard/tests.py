from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

class DashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
    def test_dashboard_access(self):
        """Test that dashboard requires login."""
        # Test without login
        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 302)
        
        # Test with login
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/dashboard.html')
        
    def test_dashboard_stats(self):
        """Test that dashboard stats endpoint works."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('dashboard:stats'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/partials/stats.html')
        
        # Check that stats are in the response
        self.assertIn('total_users', response.context)
        self.assertIn('active_users', response.context)
        self.assertIn('new_users_today', response.context) 