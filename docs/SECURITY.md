Security Notes
==============

Storage of sensitive documents
------------------------------

- Signed W-9s and executed contracts (NDA, Service Agreements) are stored as files in private Azure Blob Storage containers via Django storage backend.
- Blobs are encrypted at rest. Access is restricted via least-privilege RBAC and time-limited SAS links for admin-only downloads.
- These files are not served through public CDNs (e.g., Front Door). Access occurs via secure, authenticated admin flows only.

PII handling
------------

- We do not persist full SSN/TIN values in database fields. The authoritative source is the secured PDF itself.
- If a summary is ever needed, store only masked values (e.g., last 4) and never the full identifier.

References
----------

- IRS W-9 official form and guidance.
- DocuSign guidance for W-9 e-sign and merge-field tabs.
- Microsoft Learn: Azure Storage best practices for private containers and encryption.

