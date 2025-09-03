# Refactor Baseline Report

Generated: 2025-01-27
Branch: `epic/refactor-stdlib`
Base Branch: `feature/new-branch`

## System Overview

### Python & Django Versions
- **Python**: 3.11.13
- **Django**: 4.2.23 (requirements.txt) vs 5.2.1 (settings.py comment - needs alignment)
- **Target**: Upgrade to Django 5.x as requested

### Current Dependencies Analysis

#### Allowed Dependencies (per non-negotiables)
✅ **Django** - 4.2.23 (needs upgrade to 5.x)  
✅ **django-htmx** - 1.17.0  
✅ **django-bootstrap5** - 23.0  
✅ **python-dotenv** - 1.0.0  
✅ **black** - 23.0.0  
✅ **pylint** - 3.0.0  

#### Dependencies Requiring Evaluation
🔍 **django-allauth** - 0.57.0 (vs native Django auth)  
🔍 **django-otp** - 1.2.0 + yubikey plugin (vs native auth)  
🔍 **django-simple-captcha** - 0.5.20 (vs native solutions)  
✅ **azure-communication-email** - (explicitly approved to keep)  
✅ **django-environ** - 0.11.0 (for .env handling)  
✅ **requests** - 2.31.0 (standard library)  

#### Restricted Dependencies Found
❌ **django.contrib.sites** - in INSTALLED_APPS (used by allauth)  

## Current App Structure

### Installed Apps
```python
INSTALLED_APPS = [
    # Django Core
    "django.contrib.admin",
    "django.contrib.auth", 
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",  # ← May be removed with allauth
    
    # Third Party
    "django_htmx",           # ✅ Keep
    "django_bootstrap5",     # ✅ Keep  
    "allauth",               # 🔍 Evaluate vs native auth
    "allauth.account",       # 🔍 Evaluate vs native auth
    "allauth.socialaccount", # 🔍 Evaluate vs native auth
    "django_otp",            # 🔍 Evaluate vs native auth
    "django_otp.plugins.otp_totp", # 🔍 Evaluate
    "django_otp.plugins.otp_static", # 🔍 Evaluate
    "captcha",               # 🔍 Evaluate vs native
    
    # Local Apps
    "accounts.apps.AccountsConfig",        # ✅ User management
    "dashboard.apps.DashboardConfig",      # ✅ Main dashboard
    "communications",                      # ✅ Contact forms, emails
    "core",                               # ✅ Shared models (Location)
    "people.apps.PeopleConfig",           # ✅ Contractor profiles  
    "contracts.apps.ContractsConfig",     # ✅ DocuSign, legal docs
    "programs",                           # ✅ Program management
    "notes.apps.NotesConfig",             # ✅ Student/parent notes
    "utils.apps.UtilsConfig",             # ✅ Utilities
    "admin_interface.apps.AdminInterfaceConfig", # ✅ Custom admin
    "scheduling.apps.SchedulingConfig",   # ✅ Availability, scheduling
]
```

## Current vs Target App Boundaries

### Current Structure Issues Identified
1. **Monolithic `programs` app** - Contains buildouts, instances, roles, costs, responsibilities
2. **Mixed concerns** - Scheduling in separate app but availability in programs
3. **Admin interface** as separate app - should be integrated per-domain
4. **Core app** - minimal usage (just Location model)
5. **Missing domain separation** - Payments, documents, audit functionality scattered

### Authentication System Analysis

#### Current Implementation (django-allauth)
- Email-based authentication ✅
- Email verification ✅  
- Custom User model extending AbstractUser ✅
- Role-based access via Django groups ✅

#### Native Django Alternative Evaluation
- **Pros**: Simpler, stdlib-aligned, no third-party dependency
- **Cons**: Would need to rebuild email verification, password reset flows
- **Recommendation**: Evaluate complexity of migration vs benefits

### Database & Migration Status
- **Database**: SQLite (development)
- **Migration Status**: Multiple apps with migrations (needs assessment)
- **Custom User Model**: `accounts.User` (email-based, no username)

### Key Models Overview

#### accounts/models.py
- `User` (AbstractUser, email-based)
- `Profile` (user extensions)

#### programs/models.py (LARGE - needs refactoring)
- `ProgramType` (simplified: name, description)
- `Role` (reusable role definitions)
- `Responsibility` (role responsibilities with frequency)
- `ProgramBuildout` (program configurations)
- `BuildoutRoleLine` (contractor assignments)
- `BaseCost` (cost templates)
- `ProgramInstance` (scheduled programs)
- Registration and form models

#### people/models.py
- `Contractor` (contractor profiles, onboarding status)

#### contracts/models.py
- `LegalDocumentTemplate` (DocuSign templates)
- `DocuSignConnection` (API connection tracking)

#### core/models.py
- `Location` (venue management)
- `UserLocation` (user-location assignments)

#### communications/models.py
- `Contact` (contact form submissions)

#### notes/models.py
- Student/parent notes with visibility controls

#### scheduling/models.py
- Availability rules and time-off management

## Test Coverage Status
- **Test Discovery**: Import errors detected (needs fixing)
- **Test Files**: Present in most apps
- **Coverage**: Unknown (needs measurement after fixes)

## Code Quality Status
- **Black Formatting**: Configured but status unknown
- **Pylint**: Configured but status unknown  
- **Pre-commit**: Not configured (needs addition)

## Current Issues Identified
1. **Import Errors**: communications.urls import failure
2. **Django Version Mismatch**: requirements.txt (4.2) vs settings comment (5.2)
3. **Scattered Responsibilities**: Program management spread across multiple models
4. **Third-party Dependencies**: Need evaluation against stdlib-first approach
5. **Missing App Boundaries**: Need clear domain separation per target architecture

## Baseline Commands Used
```bash
# Version check
python --version && python -m django --version

# Git status
git status
git checkout -b epic/refactor-stdlib

# App discovery  
find . -name "apps.py" -exec grep -l "AppConfig" {} \;
find . -name "models.py" -exec wc -l {} \;

# Migration status (failed due to import errors)
python manage.py showmigrations  # ← Needs fixing

# Test discovery (failed due to import errors)  
python manage.py test --dry-run  # ← Needs fixing
```

## Next Steps
1. Fix import errors to enable proper testing
2. Complete inventory of all models, views, templates
3. Create architecture map with proposed boundaries
4. Evaluate third-party dependencies vs native alternatives
5. Plan Django 5.x upgrade path
