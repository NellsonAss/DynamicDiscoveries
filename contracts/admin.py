from django.contrib import admin
from .models import Contract, LegalDocumentTemplate


@admin.register(LegalDocumentTemplate)
class LegalDocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ["key", "docusign_template_id", "description"]
    search_fields = ["key", "description", "docusign_template_id"]


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = [
        "contractor",
        "buildout",
        "template_key",
        "envelope_id",
        "status",
        "created_at",
        "updated_at",
        "has_signed_pdf",
        "admin_open_link",
    ]
    list_filter = ["status", "template_key", "created_at"]
    search_fields = ["contractor__user__email", "buildout__title", "envelope_id"]
    readonly_fields = ["created_at", "updated_at"]

    def has_signed_pdf(self, obj):
        return bool(obj.signed_pdf)
    has_signed_pdf.boolean = True
    has_signed_pdf.short_description = "Signed PDF"

    def admin_open_link(self, obj):
        from django.utils.html import format_html
        if obj.admin_note_url:
            return format_html('<a href="{}" target="_blank">Open in DocuSign</a>', obj.admin_note_url)
        return ""
    admin_open_link.short_description = "Open DocuSign"



