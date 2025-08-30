from django.db import models


class LegalDocumentTemplate(models.Model):
    key = models.SlugField(unique=True)
    docusign_template_id = models.CharField(max_length=128)
    description = models.CharField(max_length=255, blank=True)

    def __str__(self) -> str:
        return self.key


class Contract(models.Model):
    contractor = models.ForeignKey("people.Contractor", on_delete=models.CASCADE, related_name="contracts")
    buildout = models.ForeignKey("programs.ProgramBuildout", on_delete=models.CASCADE, related_name="contracts", null=True, blank=True)
    template_key = models.CharField(max_length=128)
    envelope_id = models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=64, default="created")  # created|sent|completed|voided
    signed_pdf = models.FileField(upload_to="contracts/", null=True, blank=True)
    admin_note_url = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        subject = self.buildout.title if self.buildout else self.template_key
        return f"Contract for {self.contractor.user.email} - {subject}"



