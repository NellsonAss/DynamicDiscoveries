# Repository Inventory Report

Generated: 2025-01-27
Branch: `epic/refactor-stdlib`

## Django Apps Overview

### Current App Structure

| App | Purpose | Models Count | Key Responsibilities |
|-----|---------|--------------|---------------------|
| **accounts** | User management | 2 | Custom User model, Profile, role-based auth |
| **programs** | Program management | 15+ | Program types, buildouts, instances, roles, registrations |
| **people** | User profiles | 1 | Contractor profiles, onboarding status |
| **contracts** | Legal documents | 2 | DocuSign integration, legal templates |
| **communications** | Contact forms | 1 | Contact submissions, email service |
| **notes** | Notes system | 2 | Student/parent notes with visibility |
| **core** | Shared models | 2 | Location management, user-location assignments |
| **scheduling** | Availability | 6+ | Rules-based availability, time-off, conflicts |
| **admin_interface** | Custom admin | 0 | Custom admin UI, management interfaces |
| **dashboard** | Dashboard | 0 | Main dashboard views |
| **utils** | Utilities | 0 | Requirements tracking, template utilities |

## Detailed Model Inventory

### accounts/models.py
- **User** (AbstractUser)
  - Fields: email (unique, USERNAME_FIELD), groups, permissions
  - Methods: role checking, permissions
  - Relationships: OneToOne → Profile, FK from many models
- **Profile** 
  - Fields: bio, timestamps
  - Relationships: OneToOne → User

### programs/models.py (⚠️ LARGE - Needs Refactoring)
- **ProgramType** - Program templates (name, description)
- **Role** - Reusable role definitions with visibility controls
- **Responsibility** - Role responsibilities with frequency calculations
- **ProgramBuildout** - Program configurations with status workflow
- **BuildoutRoleLine** - Contractor-role assignments with pay rates
- **BuildoutResponsibilityLine** - Responsibility assignments
- **ContractorRoleRate** - Default contractor pay rates
- **BaseCost** - Cost templates with frequency options
- **BuildoutBaseCostAssignment** - Cost assignments to buildouts
- **ProgramInstance** - Scheduled program offerings
- **InstanceRoleAssignment** - Contractor assignments to instances
- **Child** - Parent's children for registrations
- **Registration** - Child registrations for programs
- **RegistrationForm** - Dynamic form builder
- **FormQuestion** - Form questions with multiple types

### people/models.py
- **Contractor**
  - Fields: w9_file, nda_signed, onboarding_complete
  - Relationships: OneToOne → User
  - Methods: onboarding status calculation

### contracts/models.py
- **LegalDocumentTemplate** - DocuSign template definitions
- **DocuSignConnection** - API connection tracking and status

### communications/models.py  
- **Contact** - Contact form submissions with status tracking

### notes/models.py
- **StudentNote** - Notes about students with visibility controls
- **ParentNote** - Notes about parents with visibility controls

### core/models.py
- **Location** - Venue/site management with full address info
- **UserLocation** - User assignments to locations with roles

### scheduling/models.py
- **AvailabilityRule** - Weekly recurring availability patterns
- **TimeOff** - Contractor time-off periods
- **ExceptionHold** - One-off unavailability 
- **ProgramBlock** - Batch program assignments
- **Holiday** - System-wide holidays
- **ContractorDayOffRequest** - Day-off request workflow

## Model Relationships Analysis

### Key Dependency Chains

#### User → Role → Program Flow
```
User (accounts) 
├─ Contractor (people)
├─ Profile (accounts)  
├─ Child (programs) [Parent role]
└─ BuildoutRoleLine (programs) [Contractor assignments]
   └─ ProgramBuildout (programs)
      └─ ProgramInstance (programs)
         └─ Registration (programs)
```

#### Program Management Hierarchy  
```
ProgramType (programs)
└─ ProgramBuildout (programs)
   ├─ BuildoutRoleLine (programs) → Role (programs)
   ├─ BuildoutResponsibilityLine (programs) → Responsibility (programs)
   ├─ BuildoutBaseCostAssignment (programs) → BaseCost (programs)
   └─ ProgramInstance (programs)
      ├─ InstanceRoleAssignment (programs)
      └─ Registration (programs) → Child (programs)
```

#### Scheduling & Availability
```
User (accounts)
└─ AvailabilityRule (scheduling)
   ├─ TimeOff (scheduling) [exclusions]
   ├─ ExceptionHold (scheduling) [one-off blocks]
   └─ ProgramBlock (scheduling) [assignments]
```

### Cross-App Dependencies

| From App | To App | Relationship Type | Models Involved |
|----------|--------|------------------|-----------------|
| programs | accounts | ForeignKey | Child → User (parent) |
| programs | accounts | ForeignKey | BuildoutRoleLine → User (contractor) |
| people | accounts | OneToOne | Contractor → User |
| notes | accounts | ForeignKey | StudentNote → User (author) |
| notes | programs | ForeignKey | StudentNote → Child |
| scheduling | accounts | ForeignKey | AvailabilityRule → User |
| core | accounts | ForeignKey | UserLocation → User |

## HTMX Usage Patterns

### Authentication Forms
- **Login/Signup**: `hx-post` for form submissions with `hx-target="#auth-card"`
- **CAPTCHA**: Refresh functionality with JavaScript integration
- **Email verification**: HTMX-powered code submission

### Admin Interface  
- **Role Management**: Dynamic contractor filtering based on role selection
- **Buildout Assignment**: `hx-post` for role assignments with validation
- **User Detail**: HTMX-powered status toggles and permission updates

### Notes System
- **Student Notes**: `hx-get`/`hx-post` for CRUD operations with partials
- **Parent Notes**: Similar HTMX patterns with visibility controls
- **Inline Editing**: Form submissions without page reloads

### Scheduling Interface
- **Availability Rules**: `hx-post` for rule creation/editing
- **Quick Setup**: Multi-day availability with HTMX validation  
- **Conflict Detection**: Real-time conflict checking during assignment
- **Calendar Views**: Dynamic calendar updates with merged data

### Form Builder
- **Dynamic Questions**: `hx-post` for adding/removing form questions
- **Question Types**: Dynamic form field rendering based on type
- **Form Duplication**: HTMX-powered form cloning

### Dashboard Widgets
- **Contact List**: `hx-get` for contact list widget updates
- **Statistics**: Real-time dashboard metrics updates
- **User Metrics**: Dynamic user count calculations

## Template Structure

### Base Templates
- `templates/base.html` - Main layout with HTMX/Bootstrap integration
- `templates/dashboard/dashboard.html` - Main dashboard layout

### App-Specific Templates (119 total)
- **admin_interface/**: 15 templates (management interfaces)
- **programs/**: 35+ templates (largest app)
- **scheduling/**: 15 templates (availability management)  
- **notes/**: 8 templates (notes system)
- **accounts/**: Auth-related templates
- **communications/**: Contact form templates

### HTMX Partials Pattern
- Consistent `partials/` subdirectories
- Naming: `_item.html`, `_form.html`, `_list.html`
- Used for: form fragments, list items, modal content

## URL Structure Analysis

### Current URL Patterns
```
/                           # Home page
/accounts/                  # Authentication (allauth integration)
/admin/                     # Django admin
/dashboard/                 # Main dashboard
/programs/                  # Program management (large app)
├─ parent/                  # Parent-specific views
├─ contractor/              # Contractor-specific views  
├─ forms/                   # Form builder
├─ buildouts/               # Buildout management
└─ roles/                   # Role management
/communications/            # Contact forms
/notes/                     # Notes system
/scheduling/                # Availability management
/admin_interface/           # Custom admin UI
```

## Static Files & Assets

### External Dependencies (CDN)
- **Bootstrap 5.3.0** - CSS framework ✅
- **Bootstrap Icons** - Icon library ✅  
- **HTMX 1.9.6** - JavaScript library ✅
- **Google Fonts** - Inter + Fredoka fonts

### Custom Static Files
- Custom CSS for styling overrides
- JavaScript for HTMX enhancements
- Form validation and interaction scripts

## Third-Party Integration Points

### Authentication (django-allauth) 🔍
- Email-based signup/login
- Email verification workflow
- Password reset functionality
- **Evaluation needed**: vs native Django auth

### CAPTCHA (django-simple-captcha) 🔍  
- Math-based CAPTCHA for forms
- Refresh functionality
- **Evaluation needed**: vs native alternatives

### OTP (django-otp) 🔍
- Two-factor authentication support
- TOTP and static token plugins
- **Evaluation needed**: current usage unclear

### Azure Services ✅
- **azure-communication-email** - Email sending
- **Storage integration** - File uploads (W-9, contracts)

### DocuSign Integration ✅
- Contract signing workflow
- Template management
- Webhook handling for status updates

## Issues Identified for Refactoring

### Architecture Issues
1. **Monolithic programs app** - 15+ models, needs domain separation
2. **Mixed concerns** - Scheduling partially in programs, partially separate
3. **Scattered admin functionality** - Should be per-domain
4. **Missing app boundaries** - No clear payments, documents, audit domains

### Code Quality Issues  
1. **Import errors** - Fixed during inventory
2. **Large model files** - programs/models.py needs splitting
3. **Inconsistent naming** - Some drift in field names
4. **Template proliferation** - 119 templates need organization

### Dependency Issues
1. **Django version mismatch** - 4.2 vs 5.x target
2. **Third-party evaluation needed** - allauth, captcha, OTP
3. **Missing stdlib alternatives** - Need native Django solutions

### Business Logic Issues
1. **Role-program relationship** - Moved from ProgramType to Buildout (good)
2. **Onboarding gates** - Partially implemented, needs completion
3. **Contractor assignment** - Complex but functional system
4. **Notes visibility** - Implemented but could be simplified

## Requirements Tracking Status

### From site_requirements.json
- **96 requirements** tracked (REQ-001 to REQ-096)
- **All marked "implemented"** - needs validation
- **Key features covered**:
  - Authentication system ✅
  - Program management ✅  
  - Role-based access ✅
  - Notes system ✅
  - Scheduling system ✅
  - DocuSign integration ✅
  - Contractor onboarding ✅

## Next Steps for Architecture Map

1. **Evaluate third-party dependencies** vs stdlib alternatives
2. **Map target app boundaries** per domain-driven design
3. **Identify migration paths** for model reorganization  
4. **Plan Django 5.x upgrade** strategy
5. **Design template consolidation** approach
