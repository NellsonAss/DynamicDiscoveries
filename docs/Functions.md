Public Functions, Utilities, and Template Tags

Accounts (`accounts/views.py`)
- login_view(request) [GET, POST]: Begins email verification login; sends code via AzureEmailService; HTMX partials supported.
- verify_code(request) [GET, POST]: Verifies code from session; logs in user; HTMX redirect support.
- profile(request) [GET]: Displays profile; requires auth.
- signup(request) [GET, POST]: Starts signup + verification (same flow as login).
- UserListView (ListView): Admin-only user listing.
- UserRoleUpdateView (UpdateView + POST): Admin-only; add/remove roles; HTMX partial updates.
- debug_user(request) [GET]: Displays role/debug info for current user.

Communications (`communications/views.py`)
- contact_form(request) [GET, POST]: Validates and persists `Contact`; sends notifications and confirmation emails.
- contact_list(request) [GET]: Paginated staff view; filters by search, status, interest; requires Admin/Consultant.
- contact_list_widget(request) [GET]: HTMX partial for dashboard widget.
- contact_detail(request, contact_id) [GET, POST]: Update status, send follow-ups on transition to contacted.
- test_email(request) [GET, POST]: Sends test email via AzureEmailService; surfaces errors.

Dashboard (`dashboard/views.py`)
- dashboard(request) [GET]: Main dashboard page.
- dashboard_stats(request) [GET]: HTMX stats partial with counts for users.
- dashboard_activity(request) [GET]: HTMX partial with recent Registration and Program activity.

People (`people/views.py`)
- contractor_onboarding(request) [GET]: Onboarding hub; shows NDA/W-9 state.
- send_nda(request) [POST]: Creates `Contract` from NDA template and sends via DocuSign.
- upload_w9(request) [POST]: Accepts PDF upload and stores on `Contractor`.
- start_w9_docusign(request) [POST]: Sends W-9 envelope via DocuSign.
- nda_sign(request) [GET]: Renders in-app NDA signing page.
- sign_nda(request) [POST]: Persists signature into `NDASignature`; flips flags on `Contractor`.

Programs (`programs/views.py`) [selected]
- parent_dashboard(request) [GET]: Shows active programs and registrations for parent.
- program_instance_detail(request, pk) [GET]: Detail + ability check to register.
- register_child(request, program_instance_pk) [GET, POST]: Register a child; redirects to form if assigned.
- complete_registration_form(request, registration_pk) [GET, POST]: Capture question_*-prefixed POST answers.
- contractor_dashboard(request) [GET]: Contractor view with assigned programs and forms.
- buildout_list/detail/manage/assign/...: End-to-end buildout management and finance summaries.
- form_builder(request, form_pk?) [GET, POST]: Create/edit forms; lists existing forms.
- add_form_question/delete_form_question [POST]: HTMX-driven partial updates.
- available_sessions_list/book_session/parent_bookings [Parent booking flow].
- contractor_availability_* and session_*: Enhanced scheduling utilities (availability, sessions, bookings).
- contractor_day_off_request_*: Time-off request lifecycle (create, approve, deny) with conflict checks.

Contracts (`contracts/views.py`)
- docusign_webhook(request) [POST, CSRF exempt]: Verifies signature; persists status; downloads PDFs when completed.
- return_view(request) [GET]: Post-signature landing with message.

Template Tags (`programs/templatetags`)
- dict_filters.lookup(dictionary, key): Safe dictionary key lookup for templates.
- math_filters.multiply/divide/subtract/percentage: Basic numeric helpers for templates.

Utilities (`utils/requirements_tracker.py`)
- RequirementsTracker: load/save/add/update/query requirements from `site_requirements.json`.
- parse_template_links(template_path): Extract Django url tags and HTMX calls; identify undefined routes.
- scan_templates_for_undefined_routes(templates_dir): Aggregate undefined routes across all templates.

Usage Examples
- Verify code in HTMX flow (headers drive partials vs full page):
```python
if request.headers.get('HX-Request'):
    return render(request, 'accounts/_verify_code_card.html', {'email': email})
```
- Requirements tracker:
```python
from utils.requirements_tracker import RequirementsTracker
tracker = RequirementsTracker('site_requirements.json')
data = tracker.load_requirements()
tracker.add_requirement('REQ-1', 'Auth', 'Email verification login', 'implemented')
```

