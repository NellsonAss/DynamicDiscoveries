Public HTTP APIs and Routes

Base URL prefixes are relative to site root as defined in `config/urls.py`.

Overview
- This project is a Django 5 app. Most endpoints render HTML templates. Some endpoints act as HTMX partials when the `HX-Request` header is present.
- Authentication is email-based; many endpoints require specific roles: Parent, Contractor, Admin, Consultant.

Home and Core
- GET `/` → Home page (template)
- GET `/test/` → Test page (template)
- GET `/admin/` → Django admin
- Allauth under `/auth/` (login, logout, etc.)

Accounts (`/accounts/`)
- GET, POST `/accounts/login/` → Start email verification login
- GET, POST `/accounts/verify-code/` → Submit verification code and log in
- GET `/accounts/profile/` → User profile (auth required)
- GET `/accounts/users/` → User list (admin only)
- POST `/accounts/users/<pk>/roles/` → Update roles (admin only; HTMX-supported)
- GET `/accounts/debug/` → Debug user context (auth required)

Communications (`/communications/`)
- GET, POST `/communications/contact/` → Submit contact form
- GET `/communications/contact/form/` → Contact form (alias)
- GET `/communications/contacts/` → Staff contact list (Admin, Consultant)
- GET `/communications/contacts/widget/` → HTMX widget for dashboard (auth/role)
- GET, POST `/communications/contacts/<contact_id>/` → Contact detail/update (Admin, Consultant)
- GET, POST `/communications/test-email/` → Send test email (auth)

People (`/people/`)
- GET `/people/contractor/onboarding/` → Contractor onboarding (auth)
- POST `/people/contractor/nda/send/` → Send NDA via DocuSign (auth)
- GET `/people/contractor/nda/sign/` → NDA sign page (auth)
- POST `/people/contractor/nda/sign/submit/` → Submit NDA signature (auth)
- POST `/people/contractor/w9/upload/` → Upload W-9 (auth)
- POST `/people/onboarding/w9/docusign/start/` → Start W-9 DocuSign (auth)

Contracts (`/contracts/`)
- POST `/contracts/webhook` → DocuSign Connect webhook (CSRF exempt)
- GET `/contracts/return` → DocuSign return landing

Dashboard (`/dashboard/`)
- GET `/dashboard/` → Dashboard home (auth)
- GET `/dashboard/stats/` → HTMX stats partial (auth)
- GET `/dashboard/activity/` → HTMX activity feed (auth)

Programs (`/programs/`)
- Admin/Contractor buildouts and roles
  - GET `/programs/roles/` → Roles list (admin)
  - GET `/programs/buildouts/` → Buildout list (admin/contractor)
  - GET `/programs/buildouts/<buildout_pk>/` → Buildout detail (admin/contractor)
  - POST `/programs/buildouts/<buildout_pk>/mark-ready/` → Mark buildout ready
  - POST `/programs/buildouts/<buildout_pk>/present/` → Present service agreement (DocuSign)
  - GET `/programs/buildouts/<buildout_pk>/review/` → Review agreement (access-controlled)
  - POST `/programs/buildouts/<buildout_pk>/agree-sign/` → Agree + send DocuSign
  - POST `/programs/buildouts/<buildout_pk>/manage-responsibilities/` → Update hours
  - POST `/programs/buildouts/<buildout_pk>/assign-roles/` → Assign roles
  - GET `/programs/program-types/<program_type_pk>/buildouts/` → Buildouts by program type

- Parent + registration
  - GET `/programs/programs/<pk>/` → Program instance detail
  - POST `/programs/programs/<program_instance_pk>/register/` → Register child (Parent)
  - GET, POST `/programs/registration/<registration_pk>/form/` → Complete registration form (Parent)

- Registration management (Contractor/Admin)
  - GET `/programs/programs/<program_instance_pk>/registrations/` → View registrations
  - POST `/programs/registrations/<registration_pk>/status/` → Update status (HTMX)
  - POST `/programs/programs/<program_instance_pk>/send-form/` → Send form to participants

- Form builder (Contractor/Admin)
  - GET `/programs/forms/` and `/programs/forms/<form_pk>/` → Builder (create/edit)
  - POST `/programs/forms/<form_pk>/duplicate/` → Duplicate form
  - POST `/programs/forms/<form_pk>/questions/add/` → Add question (HTMX)
  - POST `/programs/questions/<question_pk>/delete/` → Delete question (HTMX)

- Contractor dashboards and scheduling
  - GET `/programs/contractor/dashboard/` → Contractor dashboard
  - GET `/programs/contractor/availability/` → Availability list
  - GET, POST `/programs/contractor/availability/new/` → Create availability
  - GET `/programs/contractor/availability/<pk>/` → Availability detail
  - GET, POST `/programs/contractor/availability/<pk>/edit/` → Edit availability
  - GET, POST `/programs/contractor/availability/<availability_pk>/add-program/` → Add program to availability
  - GET `/programs/contractor/sessions/` → Contractor sessions list
  - GET `/programs/sessions/<session_pk>/` → Session detail
  - GET `/programs/instances/<instance_pk>/schedule/` → Assign availability to instance

- Parent booking flow
  - GET `/programs/parent/available-sessions/` → Available sessions list
  - GET, POST `/programs/parent/book-session/<session_pk>/` → Book a session
  - GET `/programs/parent/bookings/` → Parent bookings
  - POST `/programs/parent/bookings/<booking_pk>/cancel/` → Cancel booking

- Catalog
  - GET `/programs/catalog/` → Program catalog
  - GET `/programs/catalog/<program_type_id>/programs/` → Instances by type
  - GET, POST `/programs/catalog/<program_type_id>/request/` → Create program request

Notes (`/notes/`)
- GET `/notes/students/<student_id>/notes/` → Student notes list
- GET, POST `/notes/students/<student_id>/notes/new/` → Create student note
- GET, POST `/notes/students/<student_id>/notes/<note_id>/edit/` → Edit student note
- POST `/notes/students/<student_id>/notes/<note_id>/toggle-public/` → Toggle student note visibility
- GET `/notes/parents/<parent_id>/notes/` → Parent notes list
- GET, POST `/notes/parents/<parent_id>/notes/new/` → Create parent note
- GET, POST `/notes/parents/<parent_id>/notes/<note_id>/edit/` → Edit parent note
- POST `/notes/parents/<parent_id>/notes/<note_id>/toggle-public/` → Toggle parent note visibility

Authentication and Permissions
- Many endpoints require authentication and role checks: Parent, Contractor, Admin, Consultant.
- HTMX partials return partial templates when `HX-Request: true` is present; otherwise full pages.

Examples
- Submit contact form:
  curl -X POST \
       -H "Content-Type: application/x-www-form-urlencoded" \
       -d "parent_name=Jane Doe&email=jane@example.com&interest=programs&message=Tell me more" \
       http://localhost:8000/communications/contact/

- Update registration status via HTMX:
  curl -X POST \
       -H "HX-Request: true" \
       -d "status=approved" \
       http://localhost:8000/programs/registrations/123/status/