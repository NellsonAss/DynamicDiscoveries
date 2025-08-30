# Programs App

A comprehensive Django app for managing educational programs, registrations, and dynamic forms.

## Features

### Core Models

- **ProgramType**: Template for program types (e.g., "STEAM", "Literary")
- **ProgramInstance**: Specific program offerings with scheduling and capacity
- **RegistrationForm**: Dynamic forms for program registration and feedback
- **FormQuestion**: Individual questions within forms with multiple types
- **Child**: Parent's children information for registration
- **Registration**: Child's registration for a specific program instance

### User Roles & Access Control

- **Parents**: Can manage children, register for programs, complete forms
- **Contractors**: Can manage their programs, create forms, view registrations
- **Admins**: Full access to all functionality

### Key Functionality

#### For Parents
- Dashboard showing available programs and current registrations
- Child management (add, edit children)
- Program registration with dynamic form completion
- View registration history and status

#### For Contractors/Admins
- Form builder with HTMX integration
- Program management and registration oversight
- Dynamic form assignment to programs
- Registration status management

#### Form System
- Multiple question types: text, textarea, email, phone, select, radio, checkbox, date, number
- Form duplication with deep cloning
- Dynamic form rendering for parents
- Form response tracking and viewing

## URL Structure

```
/programs/
├── parent/
│   ├── dashboard/              # Parent dashboard
│   ├── children/               # Manage children
│   └── children/<id>/edit/     # Edit child
├── programs/
│   ├── <id>/                   # Program details
│   ├── <id>/register/          # Register for program
│   └── <id>/registrations/     # View registrations (contractors)
├── registration/
│   └── <id>/form/              # Complete registration form
├── contractor/
│   └── dashboard/              # Contractor dashboard
├── forms/
│   ├── /                       # Form builder
│   ├── <id>/                   # Edit form
│   ├── <id>/duplicate/         # Duplicate form
│   └── <id>/questions/add/     # Add question (HTMX)
└── questions/<id>/delete/      # Delete question (HTMX)
```

## Templates

- `parent_dashboard.html`: Parent's main dashboard
- `program_instance_detail.html`: Program details and registration
- `complete_registration_form.html`: Dynamic form completion
- `form_builder.html`: Form creation/editing with HTMX
- `contractor_dashboard.html`: Contractor's management dashboard
- `manage_children.html`: Child management for parents
- `view_registrations.html`: Registration management for contractors
- `send_form_to_participants.html`: Form assignment to programs

## HTMX Integration

The app uses HTMX for dynamic interactions:
- Form question management (add/delete questions)
- Registration status updates
- Dynamic form loading

## Bootstrap Styling

All templates use Bootstrap 5 for responsive, modern UI with:
- Card-based layouts
- Responsive tables
- Modal dialogs
- Progress bars for enrollment
- Badge indicators for status

## Security & Access Control

- Role-based access control using Django groups
- Form validation and CSRF protection
- User-specific data filtering
- Secure form response handling

## Database Relationships

```
User (Parent) → Child → Registration → ProgramInstance → ProgramType
User (Contractor) → ProgramInstance (instructor)
User (Admin) → RegistrationForm (created_by)
RegistrationForm → FormQuestion (questions)
ProgramInstance → RegistrationForm (assigned_form)
```

## Usage Examples

### Creating a Program Type
```python
program_type = ProgramType.objects.create(
    name="STEAM Program",
    description="Science, Technology, Engineering, Arts, and Math activities",
    target_grade_levels="3-5"
)
```

### Creating a Program Instance
```python
program_instance = ProgramInstance.objects.create(
    program_type=program_type,
    start_date=datetime.now(),
    end_date=datetime.now() + timedelta(days=5),
    location="Community Center",
    instructor=contractor_user,
    capacity=20
)
```

### Creating a Registration Form
```python
form = RegistrationForm.objects.create(
    title="Student Information Form",
    description="Please provide additional information about your child",
    created_by=contractor_user
)

FormQuestion.objects.create(
    form=form,
    question_text="Does your child have any allergies?",
    question_type="textarea",
    is_required=True
)
```

## Testing

Run the Django test suite:
```bash
python manage.py test programs
```

## Admin Interface

All models are registered in the Django admin with:
- Inline editing for related models
- Search and filtering capabilities
- Bulk actions for form duplication
- Read-only computed fields 