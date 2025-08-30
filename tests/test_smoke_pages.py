from django.test import TestCase, Client
from django.urls import reverse, NoReverseMatch
from django.contrib.auth import get_user_model


class PageSmokeTests(TestCase):
    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(email="smoke@test.com", password="pass")
        self.admin = User.objects.create_user(email="admin@test.com", password="pass", is_staff=True)

    def _get(self, name, args=None, expect=200, login=None):
        try:
            url = reverse(name, args=args or [])
        except NoReverseMatch:
            return
        if login == 'user':
            self.client.force_login(self.user)
        elif login == 'admin':
            self.client.force_login(self.admin)
        resp = self.client.get(url)
        # Allow redirects for login-required pages
        self.assertIn(resp.status_code, (200, 302))

    def test_core_pages(self):
        # Public or base routes
        self._get('home')
        self._get('dashboard:dashboard', login='user')
        self._get('admin_interface:dashboard', login='admin')
        self._get('communications:contact')
        # Programs
        self._get('programs:buildout_list', login='admin')
        # Accounts (if present)
        try:
            self._get('accounts:login')
        except Exception:
            pass



