from django.test import TestCase, Client
from django.urls import get_resolver, reverse, NoReverseMatch
from django.contrib.auth import get_user_model


ALLOWED_STATUSES = {200, 301, 302, 403, 404}


class DynamicUrlSmokeTests(TestCase):
    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(email="smoker@test.com", password="pass")
        self.admin = User.objects.create_user(email="admin@test.com", password="pass", is_staff=True, is_superuser=True)

    def _all_named_routes_without_args(self):
        resolver = get_resolver()
        names = set()
        for key in resolver.reverse_dict.keys():
            if isinstance(key, str):
                try:
                    reverse(key)
                except NoReverseMatch:
                    continue
                names.add(key)
        return sorted(names)

    def _get_ok(self, url_name):
        # Try anonymous
        try:
            url = reverse(url_name)
        except NoReverseMatch:
            return True  # skip named routes that require args
        resp = self.client.get(url)
        if resp.status_code in ALLOWED_STATUSES:
            return True
        # Try authenticated user
        self.client.force_login(self.user)
        resp = self.client.get(url)
        if resp.status_code in ALLOWED_STATUSES:
            return True
        # Try admin
        self.client.force_login(self.admin)
        resp = self.client.get(url)
        return resp.status_code in ALLOWED_STATUSES

    def test_all_named_routes_load_or_redirect(self):
        failures = []
        for name in self._all_named_routes_without_args():
            # Skip known special-case routes that may depend on external backend
            if name in {"captcha-refresh", "captcha_image"}:
                continue
            ok = self._get_ok(name)
            if not ok:
                failures.append(name)
        if failures:
            self.fail(f"The following routes returned unexpected status (not in {sorted(ALLOWED_STATUSES)}): {', '.join(failures)}")

