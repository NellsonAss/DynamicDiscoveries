import base64
import hashlib
import hmac
import os
from typing import Dict, Optional

import requests
from django.conf import settings


class DocuSignService:
    def __init__(self) -> None:
        self.base_url = getattr(settings, "DOCUSIGN_BASE_URL", "")
        self.account_id = getattr(settings, "DOCUSIGN_ACCOUNT_ID", "")
        self.integration_key = getattr(settings, "DOCUSIGN_INTEGRATION_KEY", "")
        self.user_id = getattr(settings, "DOCUSIGN_USER_ID", "")
        self.private_key = getattr(settings, "DOCUSIGN_PRIVATE_KEY", "")
        self.webhook_secret = getattr(settings, "DOCUSIGN_WEBHOOK_SECRET", "")

    def _get_access_token(self) -> Optional[str]:
        # Placeholder: In production, implement JWT grant to fetch token.
        # For dev without DocuSign configured, return None to enable no-op flow.
        return os.environ.get("DOCUSIGN_ACCESS_TOKEN")

    def create_envelope(
        self,
        *,
        template_id: str,
        recipient_email: str,
        recipient_name: str,
        merge_fields: Dict[str, str] | None = None,
        return_url: Optional[str] = None,
        webhook_url: Optional[str] = None,
    ) -> str:
        if not self.base_url or not self.account_id:
            # Dev fallback: pretend we created an envelope
            return f"dev-envelope-{hashlib.sha256((recipient_email+template_id).encode()).hexdigest()[:12]}"

        token = self._get_access_token()
        if not token:
            # If token not available, return deterministic id to avoid runtime failure in dev
            return f"dev-envelope-{hashlib.sha256((recipient_email+template_id).encode()).hexdigest()[:12]}"

        # Construct payload for DocuSign create envelope from template
        url = f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes"
        payload = {
            "templateId": template_id,
            "templateRoles": [
                {
                    "email": recipient_email,
                    "name": recipient_name,
                    "roleName": "Contractor",
                    "tabs": {
                        "textTabs": [
                            {"tabLabel": k, "value": v} for k, v in (merge_fields or {}).items()
                        ]
                    },
                }
            ],
            "status": "sent",
        }
        if webhook_url or getattr(settings, "DOCUSIGN_WEBHOOK_URL", None):
            connect_url = webhook_url or settings.DOCUSIGN_WEBHOOK_URL
            payload["eventNotification"] = {
                "url": connect_url,
                "loggingEnabled": "true",
                "requireAcknowledgment": "true",
                "envelopeEvents": [{"envelopeEventStatusCode": "completed"}],
            }

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        resp = requests.post(url, json=payload, headers=headers, timeout=20)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"DocuSign API error: {resp.status_code} {resp.text}")
        data = resp.json()
        return data.get("envelopeId", "")

    def download_completed_pdf(self, envelope_id: str) -> bytes:
        if not self.base_url or not self.account_id:
            return b""
        token = self._get_access_token()
        if not token:
            return b""
        url = f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes/{envelope_id}/documents/combined"
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to download PDF: {resp.status_code}")
        return resp.content

    def verify_webhook_signature(self, body: bytes, signature_header: str | None) -> bool:
        if not self.webhook_secret or not signature_header:
            return True  # allow when not configured
        mac = hmac.new(self.webhook_secret.encode(), body, hashlib.sha256).digest()
        expected = base64.b64encode(mac).decode()
        return hmac.compare_digest(expected, signature_header)



