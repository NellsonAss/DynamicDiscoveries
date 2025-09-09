from django.conf import settings
from django.db import models
from django.utils import timezone


class Contractor(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    w9_file = models.FileField(upload_to="w9/", null=True, blank=True)
    nda_signed = models.BooleanField(default=False)
    onboarding_complete = models.BooleanField(default=False)
    
    # Admin approval fields
    nda_approved = models.BooleanField(default=False, help_text="Admin approval for NDA signature")
    w9_approved = models.BooleanField(default=False, help_text="Admin approval for W-9 document")
    nda_approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_ndas', help_text="Admin who approved the NDA")
    w9_approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_w9s', help_text="Admin who approved the W-9")
    nda_approved_at = models.DateTimeField(null=True, blank=True, help_text="When the NDA was approved")
    w9_approved_at = models.DateTimeField(null=True, blank=True, help_text="When the W-9 was approved")

    def recalc_onboarding(self):
        self.onboarding_complete = bool(self.w9_file and self.nda_signed and self.nda_approved and self.w9_approved)

    def save(self, *args, **kwargs):
        self.recalc_onboarding()
        super().save(*args, **kwargs)

    @property
    def needs_onboarding(self) -> bool:
        return not bool(self.onboarding_complete)
    
    @property
    def nda_status(self) -> str:
        """Return human-readable NDA status"""
        if not self.nda_signed:
            return "Not Signed"
        elif not self.nda_approved:
            return "Signed - Pending Approval"
        else:
            return "Approved"
    
    @property
    def w9_status(self) -> str:
        """Return human-readable W-9 status"""
        if not self.w9_file:
            return "Not Uploaded"
        elif not self.w9_approved:
            return "Uploaded - Pending Approval"
        else:
            return "Approved"

    def __str__(self) -> str:
        return f"Contractor: {self.user.email}"


class NDASignature(models.Model):
    """Model to store NDA signatures and related information"""
    contractor = models.OneToOneField(Contractor, on_delete=models.CASCADE, related_name='nda_signature')
    signature_data = models.TextField(help_text="Base64 encoded signature image data")
    signed_name = models.CharField(max_length=255, help_text="Name as signed by the contractor")
    signed_at = models.DateTimeField(default=timezone.now, help_text="When the NDA was signed")
    ip_address = models.GenericIPAddressField(help_text="IP address of the signer")
    user_agent = models.TextField(blank=True, help_text="User agent string from the browser")
    
    class Meta:
        verbose_name = "NDA Signature"
        verbose_name_plural = "NDA Signatures"
    
    def __str__(self) -> str:
        return f"NDA Signature by {self.signed_name} on {self.signed_at.strftime('%Y-%m-%d %H:%M')}"


