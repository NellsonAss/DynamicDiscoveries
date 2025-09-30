Services

AzureEmailService (`communications/services.py`)
- Purpose: Send emails via Azure Communication Service with fallback to Django EmailBackend.
- Initialization: Reads `AZURE_COMMUNICATION_CONNECTION_STRING` and `AZURE_COMMUNICATION_SENDER_ADDRESS` from settings; initializes `EmailClient` if configured.
- Methods:
  - send_email(to_email, subject, html_content) → bool
  - send_templated_email(to_email, subject, template_name, context) → bool
- Usage example (Django view):
```python
from communications.services import AzureEmailService
service = AzureEmailService()
service.send_templated_email(
    to_email='user@example.com',
    subject='Welcome',
    template_name='communications/welcome_email.html',
    context={'name': 'User'}
)
```

DocuSignService (`contracts/services/docusign.py`)
- Purpose: Integrates with DocuSign to create envelopes, download PDFs, and verify webhooks.
- Settings: `DOCUSIGN_BASE_URL`, `DOCUSIGN_ACCOUNT_ID`, `DOCUSIGN_INTEGRATION_KEY`, `DOCUSIGN_USER_ID`, `DOCUSIGN_PRIVATE_KEY`, `DOCUSIGN_WEBHOOK_SECRET`, `DOCUSIGN_WEBHOOK_URL`
- Methods:
  - create_envelope(template_id, recipient_email, recipient_name, merge_fields?, return_url?, webhook_url?) → envelope_id
  - download_completed_pdf(envelope_id) → bytes
  - verify_webhook_signature(body, signature_header) → bool
- Dev behavior: If not configured, returns deterministic dev envelope IDs and no-op downloads.
- Usage example:
```python
from contracts.services.docusign import DocuSignService
svc = DocuSignService()
envelope_id = svc.create_envelope(
    template_id='abcd1234',
    recipient_email='contractor@example.com',
    recipient_name='Alex Contractor',
    merge_fields={'BUILDOUT_TITLE': 'STEAM v1'},
    return_url='http://localhost:8000/contracts/return',
    webhook_url='http://localhost:8000/contracts/webhook'
)
```

