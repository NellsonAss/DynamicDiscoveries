from django.conf import settings
from django.db import models


class Contractor(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    w9_file = models.FileField(upload_to="w9/", null=True, blank=True)
    nda_signed = models.BooleanField(default=False)
    onboarding_complete = models.BooleanField(default=False)

    def recalc_onboarding(self):
        self.onboarding_complete = bool(self.w9_file and self.nda_signed)

    def save(self, *args, **kwargs):
        self.recalc_onboarding()
        super().save(*args, **kwargs)

    @property
    def needs_onboarding(self) -> bool:
        return not bool(self.onboarding_complete)

    def __str__(self) -> str:
        return f"Contractor: {self.user.email}"



