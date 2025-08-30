from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.contrib import messages
from django.core.files.uploadedfile import UploadedFile
from django.urls import reverse

from .models import Contractor
from contracts.models import Contract, LegalDocumentTemplate
from contracts.services.docusign import DocuSignService


def _get_or_create_contractor(user):
    contractor, _ = Contractor.objects.get_or_create(user=user)
    return contractor


@login_required
def contractor_onboarding(request):
    contractor = _get_or_create_contractor(request.user)
    context = {
        "contractor": contractor,
    }
    return render(request, "people/contractor_onboarding.html", context)


@login_required
def send_nda(request):
    contractor = _get_or_create_contractor(request.user)
    try:
        template = LegalDocumentTemplate.objects.get(key="nda")
    except LegalDocumentTemplate.DoesNotExist:
        messages.error(request, "NDA template is not configured.")
        return redirect(reverse("people:contractor_onboarding"))

    contract = Contract.objects.create(
        contractor=contractor,
        buildout=None,
        template_key="nda",
        status="created",
    )
    service = DocuSignService()
    try:
        envelope_id = service.create_envelope(
            template_id=template.docusign_template_id,
            recipient_email=request.user.email,
            recipient_name=getattr(request.user, "get_full_name", lambda: request.user.email)(),
            merge_fields={},
            return_url=None,
            webhook_url=None,
        )
        contract.envelope_id = envelope_id
        contract.status = "sent"
        contract.save(update_fields=["envelope_id", "status"])
        messages.success(request, "NDA sent — check your email.")
    except Exception as e:
        messages.error(request, f"Failed to send NDA: {e}")
    return redirect(reverse("people:contractor_onboarding"))


@login_required
def upload_w9(request):
    if request.method != "POST":
        return redirect(reverse("people:contractor_onboarding"))
    contractor = _get_or_create_contractor(request.user)
    file: UploadedFile | None = request.FILES.get("w9_file")
    if not file:
        messages.error(request, "Please select a PDF file.")
        return redirect(reverse("people:contractor_onboarding"))
    if not file.name.lower().endswith(".pdf"):
        messages.error(request, "Only PDF files are accepted.")
        return redirect(reverse("people:contractor_onboarding"))
    contractor.w9_file = file
    contractor.save()
    if contractor.onboarding_complete:
        messages.success(request, "Onboarding complete. Welcome!")
        return redirect("programs:contractor_dashboard")
    messages.success(request, "W-9 uploaded. Please complete NDA.")
    return redirect(reverse("people:contractor_onboarding"))


@login_required
def start_w9_docusign(request):
    contractor = _get_or_create_contractor(request.user)
    try:
        template = LegalDocumentTemplate.objects.get(key="w9")
    except LegalDocumentTemplate.DoesNotExist:
        messages.error(request, "W-9 DocuSign template is not configured.")
        return redirect(reverse("people:contractor_onboarding"))

    contract = Contract.objects.create(
        contractor=contractor,
        buildout=None,
        template_key="w9",
        status="created",
    )
    service = DocuSignService()
    try:
        envelope_id = service.create_envelope(
            template_id=template.docusign_template_id,
            recipient_email=request.user.email,
            recipient_name=getattr(request.user, "get_full_name", lambda: request.user.email)(),
            merge_fields={},
            return_url=None,
            webhook_url=None,
        )
        contract.envelope_id = envelope_id
        contract.status = "sent"
        # Optional admin deep-link for DocuSign inbox if configured
        contract.admin_note_url = getattr(service, "base_url", "") or ""
        contract.save(update_fields=["envelope_id", "status", "admin_note_url"])
        messages.success(request, "W-9 sent — check your email.")
    except Exception as e:
        messages.error(request, f"Failed to send W-9: {e}")
    return redirect(reverse("people:contractor_onboarding"))



