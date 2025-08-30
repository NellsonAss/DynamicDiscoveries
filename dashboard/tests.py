from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

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
        
    def test_dashboard_stats_accuracy(self):
        """Test that dashboard stats reflect actual database counts."""
        User = get_user_model()
        
        # Create additional test users
        User.objects.create_user(email='active@example.com', password='test', is_active=True)
        User.objects.create_user(email='inactive@example.com', password='test', is_active=False)
        
        # Create a user with today's date
        today_user = User.objects.create_user(email='today@example.com', password='test')
        today_user.date_joined = timezone.now()
        today_user.save()
        
        # Login and get stats
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('dashboard:stats'))
        
        # Get actual database counts
        actual_total = User.objects.count()
        actual_active = User.objects.filter(is_active=True).count()
        actual_today = User.objects.filter(date_joined__date=timezone.now().date()).count()
        
        # Verify stats match database
        stats = response.context['stats']
        self.assertEqual(stats['total_users'], actual_total, 
                         f"Total users should be {actual_total}, got {stats['total_users']}")
        self.assertEqual(stats['active_users'], actual_active,
                         f"Active users should be {actual_active}, got {stats['active_users']}")
        self.assertEqual(stats['new_users_today'], actual_today,
                         f"New users today should be {actual_today}, got {stats['new_users_today']}") 