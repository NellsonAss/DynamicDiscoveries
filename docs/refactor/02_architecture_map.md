# Architecture Map: Current vs Proposed

Generated: 2025-01-27
Branch: `epic/refactor-stdlib`

## Executive Summary

The current architecture has evolved organically, resulting in a **monolithic `programs` app** containing 15+ models with mixed concerns. The proposed stdlib-aligned architecture separates concerns into **domain-specific apps** with clear boundaries and minimal dependencies.

## Current Architecture Issues

### 1. Monolithic Programs App
- **15+ models** in single app (programs/models.py ~1500 lines)
- **Mixed concerns**: roles, costs, buildouts, instances, registrations, forms
- **Complex dependencies**: scheduling partially here, partially separate
- **Admin scattered**: management UI spread across apps

### 2. Unclear Domain Boundaries
- **Contractor management** split between `people` and `programs`
- **Document handling** minimal in `contracts`
- **No payments domain** - invoice functionality missing
- **No audit trail** - critical events untracked

### 3. Third-Party Dependencies
- **django-allauth** vs native Django auth (needs evaluation)
- **django-otp** (usage unclear, may be removable)
- **django-simple-captcha** vs native solutions

## Proposed Target Architecture

### Domain-Aligned Apps

#### 1. **accounts/** - User Management
**Purpose**: Core user authentication and profile management
```python
# Models
- User (AbstractUser, email-based) ✅ Keep existing
- Profile (user extensions) ✅ Keep existing

# Responsibilities
- Email-based authentication (evaluate allauth vs native)
- Role management via Django Groups
- User permissions and access control
- Profile information management
```

#### 2. **contractors/** - Contractor Domain  
**Purpose**: Contractor-specific functionality and onboarding
```python  
# Models (moved from people + programs)
- Contractor (profile, onboarding state)
- ContractorOnboarding (NDA/W-9 tracking)
- ContractorEligibility (role assignments, location constraints)

# Responsibilities  
- Contractor profile management
- Onboarding workflow (NDA + W-9 gates)
- Dashboard banner gating
- Eligibility checks for assignments
- Contractor-specific dashboard views
```

#### 3. **programs/** - Program Management (Simplified)
**Purpose**: Core program definition and management
```python
# Models (simplified from current)
- ProgramType (name, description only) ✅ Keep as-is
- ProgramBuildout (roles, responsibilities, costs, status)
- ProgramInstance (scheduled runs, contractor assignments)
- Role (reusable role definitions) ✅ Keep structure
- Responsibility (role responsibilities) ✅ Keep structure

# Responsibilities
- Program type templates
- Buildout configuration with status workflow
- Program instance scheduling
- Role and responsibility management
- Contract link storage on buildouts
```

#### 4. **scheduling/** - Availability & Scheduling
**Purpose**: All scheduling-related functionality
```python
# Models (enhanced from current)
- AvailabilityRule (weekly patterns) ✅ Keep existing
- TimeOff (contractor time-off) ✅ Keep existing  
- ExceptionHold (one-off blocks) ✅ Keep existing
- ProgramAssignment (bulk assignments)

# Responsibilities
- Grouped availability (ranges → single logical units)
- Bulk apply operations (copy week, remove week)
- Time-off integration with availability
- Role-aware assignment UI
- Conflict detection and resolution
```

#### 5. **documents/** - Document Management
**Purpose**: DocuSign integration and document handling
```python
# Models (enhanced from contracts)
- DocumentTemplate (NDA, W-9 templates)
- Envelope (DocuSign envelope tracking)
- DocumentSignature (signature completion tracking)
- W9Document (W-9 specific handling)

# Responsibilities
- DocuSign service abstraction
- Template management (NDA, W-9)
- Envelope creation and status tracking
- Webhook handling for signature completion
- Document storage and retrieval
- W-9 options (DocuSign template or upload)
```

#### 6. **payments/** - Payment Foundation
**Purpose**: Invoice management and payment tracking
```python
# Models (new)
- Invoice (number, due, status, parent contact)
- InvoiceLineItem (description, quantity, rate, total)
- PaymentLink (external processor link storage)

# Responsibilities
- First-party invoice model
- Line item management
- External payment link storage (no direct SDK)
- Invoice status tracking
- Parent-facing payment interface
```

#### 7. **notes/** - Notes System (Enhanced)
**Purpose**: Student and parent notes with visibility controls
```python
# Models ✅ Keep existing structure
- StudentNote (facilitator → student notes)
- ParentNote (admin → parent notes)

# Responsibilities ✅ Keep existing logic
- Role-based note creation (facilitators → students, admins → parents)
- Public/private visibility flags
- Permission enforcement in views and templates
- Note history and audit trail
```

#### 8. **adminui/** - Admin Interface (Consolidated)
**Purpose**: Unified admin dashboard and management
```python
# Models (none - view-only)

# Responsibilities
- Admin dashboard with metrics
- List filters and search functionality
- Quick actions for common tasks
- Per-domain admin interfaces
- User management and permissions
- System health monitoring
```

#### 9. **audit/** - Audit Trail
**Purpose**: Simple audit logging for critical events  
```python
# Models (new)
- AuditLog (event, user, timestamp, details)

# Responsibilities
- Authorization changes logging
- Contract sent/signed events
- Payout and financial events
- User role changes
- Critical system events
```

## Migration Strategy

### Phase 1: Dependency Evaluation
1. **Evaluate django-allauth** vs native Django auth
   - **Keep if**: Email verification, social auth needed
   - **Replace if**: Simple email-based auth sufficient
2. **Evaluate django-otp** - check actual usage
3. **Evaluate django-simple-captcha** vs native alternatives

### Phase 2: Model Reorganization
1. **Extract contractors/** from people + programs
2. **Create documents/** from contracts + DocuSign logic  
3. **Create payments/** foundation
4. **Create audit/** logging
5. **Simplify programs/** by moving domain-specific models

### Phase 3: Template & View Consolidation
1. **Consolidate admin templates** into adminui/
2. **Reorganize HTMX partials** by domain
3. **Standardize naming conventions**
4. **Remove template duplication**

### Phase 4: Django 5.x Upgrade
1. **Update requirements.txt** to Django 5.x
2. **Test compatibility** with existing code
3. **Update deprecated patterns**
4. **Leverage new Django 5 features**

## Dependency Mapping

### Current Cross-App Dependencies
```
programs → accounts (User FK)
people → accounts (User OneToOne)  
notes → accounts (User FK)
notes → programs (Child FK)
scheduling → accounts (User FK)
core → accounts (User FK)
```

### Proposed Cross-App Dependencies
```
contractors → accounts (User OneToOne)
programs → contractors (eligibility checks)
scheduling → contractors (availability rules)
documents → contractors (onboarding docs)
payments → accounts (invoice recipient)
notes → programs (student/parent references)
audit → accounts (event attribution)
```

## Benefits of Proposed Architecture

### 1. **Clear Domain Boundaries**
- Each app has single responsibility
- Easier to understand and maintain
- Better testability and modularity

### 2. **Stdlib-Aligned Dependencies**
- Minimal third-party dependencies
- Leverage Django's built-in functionality
- Easier deployment and maintenance

### 3. **Improved Developer Experience**
- Logical code organization
- Predictable file locations
- Consistent patterns across domains

### 4. **Better Performance**
- Reduced model complexity per app
- More targeted queries
- Better caching opportunities

### 5. **Enhanced Security**
- Clear permission boundaries
- Audit trail for critical events
- Role-based access control

## Risks and Mitigations

### 1. **Migration Complexity**
- **Risk**: Data migration between apps
- **Mitigation**: Careful migration scripts with rollback plans

### 2. **Circular Dependencies**
- **Risk**: Apps depending on each other
- **Mitigation**: Clear dependency hierarchy, shared utilities

### 3. **Feature Regression**
- **Risk**: Breaking existing functionality
- **Mitigation**: Comprehensive test coverage, gradual migration

### 4. **Third-Party Integration**
- **Risk**: Breaking allauth/captcha integration
- **Mitigation**: Evaluate before removing, provide alternatives

## Next Steps

1. **Create ADR-001** with finalized app boundaries
2. **Plan migration order** (least dependent apps first)
3. **Set up pre-commit hooks** for code quality
4. **Begin with contractors/** app extraction
5. **Implement audit/** logging foundation
