from django.conf import settings
from django.contrib import messages
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile

from .models import Contract
from .services.docusign import DocuSignService


def return_view(request: HttpRequest) -> HttpResponse:
    messages.success(request, "Thanks. We'll notify you when signatures are complete.")
    return redirect("dashboard:dashboard")


@csrf_exempt
def docusign_webhook(request: HttpRequest) -> HttpResponse:
    service = DocuSignService()
    signature = request.headers.get("X-DocuSign-Signature-1")
    if not service.verify_webhook_signature(request.body, signature):
        return HttpResponseBadRequest("Invalid signature")

    # Minimal parsing: expect JSON payload with envelopeId and status
    try:
        payload = request.body.decode()
        # DocuSign can send XML; support simple search to extract values to avoid heavy deps
        # Prefer JSON if configured, but fall back to naive parsing
        envelope_id = None
        status = None
        if '"envelopeId"' in payload:
            import json
            data = json.loads(payload)
            envelope_id = data.get("envelopeId")
            status = data.get("status") or data.get("eventType")
        else:
            # naive XML parsing
            import re
            m = re.search(r"<envelopeId>([^<]+)</envelopeId>", payload)
            if m:
                envelope_id = m.group(1)
            m = re.search(r"<status>([^<]+)</status>", payload)
            if m:
                status = m.group(1)
    except Exception:
        return HttpResponseBadRequest("Invalid payload")

    if not envelope_id:
        return HttpResponseBadRequest("Missing envelopeId")

    try:
        contract = Contract.objects.select_related("buildout", "contractor").get(envelope_id=envelope_id)
    except Contract.DoesNotExist:
        return HttpResponse("OK")

    if (status or "").lower() == "completed":
        pdf_bytes = b""
        try:
            pdf_bytes = service.download_completed_pdf(envelope_id)
        except Exception:
            pdf_bytes = b""
        if pdf_bytes:
            contract.signed_pdf.save(f"signed_{envelope_id}.pdf", ContentFile(pdf_bytes), save=False)
        contract.status = "completed"
        contract.save()

        # Update related entities
        if contract.buildout:
            try:
                contract.buildout.mark_active()
            except Exception:
                contract.buildout.status = contract.buildout.Status.ACTIVE
                contract.buildout.save(update_fields=["status"]) 
        if contract.template_key == "nda":
            contractor = contract.contractor
            contractor.nda_signed = True
            contractor.save()
        elif contract.template_key == "w9":
            contractor = contract.contractor
            try:
                pdf_bytes = pdf_bytes or service.download_completed_pdf(envelope_id)
            except Exception:
                pdf_bytes = b""
            if pdf_bytes:
                from django.core.files.base import ContentFile
                contractor.w9_file.save(f"w9_{envelope_id}.pdf", ContentFile(pdf_bytes), save=False)
            contractor.save()

    return HttpResponse("OK")



