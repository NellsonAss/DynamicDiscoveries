from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.contrib import messages
from django.core.files.uploadedfile import UploadedFile
from django.urls import reverse
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

from .models import Contractor, NDASignature
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


@login_required
def nda_sign(request):
    """Display the NDA signing page"""
    contractor = _get_or_create_contractor(request.user)
    
    # Check if NDA is already signed
    if contractor.nda_signed:
        messages.info(request, "You have already signed the NDA.")
        return redirect(reverse("people:contractor_onboarding"))
    
    context = {
        "contractor": contractor,
        "today": timezone.now().date(),
    }
    return render(request, "people/nda_sign.html", context)


@login_required
def sign_nda(request):
    """Process NDA signature submission"""
    if request.method != "POST":
        return redirect(reverse("people:nda_sign"))
    
    contractor = _get_or_create_contractor(request.user)
    
    # Check if NDA is already signed
    if contractor.nda_signed:
        messages.info(request, "You have already signed the NDA.")
        return redirect(reverse("people:contractor_onboarding"))
    
    # Get form data
    signed_name = request.POST.get('signed_name', '').strip()
    signature_data = request.POST.get('signature_data', '')
    agree_terms = request.POST.get('agree_terms')
    
    # Validate form data
    if not signed_name:
        messages.error(request, "Please enter your full name.")
        return redirect(reverse("people:nda_sign"))
    
    if not signature_data:
        messages.error(request, "Please provide your signature.")
        return redirect(reverse("people:nda_sign"))
    
    if not agree_terms:
        messages.error(request, "You must agree to the terms and conditions.")
        return redirect(reverse("people:nda_sign"))
    
    try:
        # Create NDA signature record
        nda_signature = NDASignature.objects.create(
            contractor=contractor,
            signature_data=signature_data,
            signed_name=signed_name,
            signed_at=timezone.now(),
            ip_address=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
        
        # Mark contractor as having signed NDA
        contractor.nda_signed = True
        contractor.save()
        
        # Log the signature for audit purposes
        print(f"NDA SIGNED - User: {request.user.email}, Name: {signed_name}, IP: {request.META.get('REMOTE_ADDR', '')}, Time: {timezone.now()}")
        
        messages.success(request, "NDA signed successfully! You can now access your contractor dashboard.")
        
        # Redirect to contractor dashboard if onboarding is complete
        if contractor.onboarding_complete:
            return redirect("programs:contractor_dashboard")
        else:
            return redirect(reverse("people:contractor_onboarding"))
            
    except Exception as e:
        messages.error(request, f"Failed to process NDA signature: {str(e)}")
        return redirect(reverse("people:nda_sign"))



