from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from bs4 import BeautifulSoup


class PageDomObjectTests(TestCase):
    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(email="dom@test.com", password="pass")
        self.admin = User.objects.create_user(email="admin@test.com", password="pass", is_staff=True, is_superuser=True)

    def _soup(self, url_name, login=None):
        if login == "user":
            self.client.force_login(self.user)
        elif login == "admin":
            self.client.force_login(self.admin)
        resp = self.client.get(reverse(url_name))
        self.assertIn(resp.status_code, (200, 302))
        html = b"".join(resp)
        return BeautifulSoup(html, "html.parser")

    def test_base_navbar_exists(self):
        soup = self._soup("home")
        # .navbar and #navbarNav should exist
        self.assertIsNotNone(soup.select_one(".navbar"))
        self.assertIsNotNone(soup.select_one("#navbarNav"))

    def test_dashboard_stats_widgets_present(self):
        soup = self._soup("dashboard:dashboard", login="admin")
        # Stats container placeholders/targets
        self.assertIsNotNone(soup.select_one("#stats-container"))
        # Optional placeholders
        # Ensure key sections render when present
        # Not asserting text, only presence

    def test_accounts_login_card_present(self):
        soup = self._soup("accounts:login")
        self.assertIsNotNone(soup.select_one("#auth-card"))
        self.assertIsNotNone(soup.select_one("#login-form"))

    def test_contact_form_elements_present(self):
        # Contact page can be public
        soup = self._soup("communications:contact")
        # Ensure the contact section exists when using the public home form too
        # At minimum, presence of a form element
        self.assertIsNotNone(soup.find("form"))

