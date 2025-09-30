UI Components, Pages, and HTMX Partials

Conventions
- Views render full-page templates by default; when the `HX-Request` header is present, many views return partials under `templates/.../partials/`.
- Bootstrap 5 is available via `django_bootstrap5`.

Key Pages
- Home: `templates/home.html` (contact entry point)
- Dashboard: `templates/dashboard/dashboard.html`
  - Partials: `templates/dashboard/partials/stats.html`, `templates/dashboard/partials/activity_feed.html`

Accounts
- Login: `templates/accounts/login.html`
- Signup: `templates/accounts/signup.html`
- Verify Code: `templates/accounts/verify_code.html`
- HTMX partials:
  - `templates/accounts/_login_form.html`
  - `templates/accounts/_signup_form.html`
  - `templates/accounts/_verify_code_card.html`

People
- Contractor Onboarding: `templates/people/contractor_onboarding.html`
  - Banner partials: `templates/people/partials/contractor/_onboarding_banner.html`

Programs
- Buildout Detail: `templates/programs/buildout_detail.html`
  - Partial: `templates/programs/partials/buildout_review.html`
- Form Builder: `templates/programs/form_builder.html`
  - HTMX partial item: `templates/programs/partials/question_item.html`
- Other views (registrations, sessions, availability, bookings) render templates matching view names in `programs/views.py`.

Notes
- Student Notes:
  - Full page: `templates/notes/student_notes_list.html`
  - Partials: `templates/notes/partials/_student_notes_list.html`, `templates/notes/partials/_student_note_form.html`
- Parent Notes:
  - Full page: `templates/notes/parent_notes_list.html`
  - Partials: `templates/notes/partials/_parent_notes_list.html`, `templates/notes/partials/_parent_note_form.html`

Admin Interface
- Custom admin UI under `templates/admin_interface/` (e.g., contractor docs views)

HTMX Usage Pattern
- Many views switch between partials and full pages based on `HX-Request`:
```python
if request.headers.get('HX-Request'):
    return render(request, 'notes/partials/_student_notes_list.html', context)
return render(request, 'notes/student_notes_list.html', context)
```

Including Partials in Templates
```django
<div hx-get="{% url 'dashboard:stats' %}" hx-trigger="load" hx-target="#stats" id="stats"></div>
```