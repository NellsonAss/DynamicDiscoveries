# ADR-001: Stdlib-Aligned App Boundaries

**Status**: Proposed  
**Date**: 2025-01-27  
**Deciders**: Development Team  
**Technical Story**: Epic refactor to stdlib-aligned Django + HTMX architecture  

## Context

The current Django application has evolved organically over time, resulting in a **monolithic `programs` app** with 15+ models and mixed concerns. This violates Django best practices and makes the codebase difficult to maintain, test, and extend. We need to refactor to **domain-aligned app boundaries** that follow stdlib patterns with minimal dependencies.

### Current Problems
1. **Monolithic programs app** - Single app contains program management, role management, cost management, registration, forms, and contractor assignments
2. **Scattered admin functionality** - Custom admin views spread across multiple apps  
3. **Missing domain boundaries** - No dedicated apps for payments, documents, or audit
4. **Third-party dependency drift** - Multiple auth systems, captcha, OTP without clear necessity
5. **Template proliferation** - 119 templates without clear organization
6. **Complex cross-app dependencies** - Unclear model relationships

### Business Requirements
- Preserve all existing functionality during refactor
- Maintain contractor onboarding gates and assignment rules  
- Keep role-based access control and notes visibility policies
- Preserve DocuSign integration and document workflows
- Maintain HTMX-powered interactive UI
- Support Django 5.x upgrade path

## Decision

We will refactor the application into **9 domain-aligned apps** with clear boundaries and minimal dependencies:

### Target App Architecture

#### 1. **accounts/** - User Management & Authentication
**Scope**: Core user functionality only
- **Models**: User (keep existing), Profile (keep existing)
- **Responsibilities**: 
  - Email-based authentication (evaluate allauth vs native Django)
  - User profile management
  - Role assignment via Django Groups (stdlib approach)
  - Permission management
- **Migration**: Keep existing models, evaluate third-party auth dependencies

#### 2. **contractors/** - Contractor Domain
**Scope**: All contractor-specific functionality  
- **Models**: Contractor (from people), ContractorEligibility (new), ContractorOnboarding (enhanced)
- **Responsibilities**:
  - Contractor profile and onboarding state
  - NDA + W-9 completion gates  
  - Dashboard banner gating for incomplete onboarding
  - Eligibility checks for program assignments
  - Contractor-specific dashboard and views
- **Migration**: Move from people/ + extract from programs/

#### 3. **programs/** - Core Program Management (Simplified)
**Scope**: Program definition and management only
- **Models**: ProgramType (keep), ProgramBuildout (keep), ProgramInstance (keep), Role (keep), Responsibility (keep)
- **Responsibilities**:
  - Program type templates (name, description only)
  - Program buildout configuration with status workflow
  - Program instance scheduling and management  
  - Role and responsibility catalog management
  - Contract link storage on buildouts
- **Migration**: Remove contractor-specific logic, keep core program models

#### 4. **scheduling/** - Availability & Time Management  
**Scope**: All scheduling and availability functionality
- **Models**: Keep existing scheduling models, enhance for grouped operations
- **Responsibilities**:
  - Contractor availability rules (grouped ranges, not individual entries)
  - Bulk apply operations (copy week → other weeks, remove/override week)
  - Time-off integration with availability suppression
  - Role-aware assignment UI
  - Conflict detection and resolution
- **Migration**: Keep existing models, enhance UX for bulk operations

#### 5. **documents/** - Document Management & DocuSign
**Scope**: All document handling and legal workflows
- **Models**: DocumentTemplate (enhanced from contracts), Envelope (new), DocumentSignature (new), W9Document (new)
- **Responsibilities**:
  - DocuSign service abstraction layer
  - Template management (NDA, W-9 templates)
  - Envelope creation, tracking, and status updates
  - Webhook handling for signature completion
  - W-9 handling (DocuSign template preferred, upload fallback)
  - Document storage and retrieval
- **Migration**: Enhance existing contracts/ models, add abstraction layer

#### 6. **payments/** - Payment Foundation
**Scope**: Invoice management and payment processing
- **Models**: Invoice (new), InvoiceLineItem (new), PaymentLink (new)
- **Responsibilities**:
  - First-party invoice model (no direct processor integration)
  - Invoice line item management
  - External payment link storage (processor-agnostic)
  - Invoice status tracking and parent notifications
  - Payment history and reporting
- **Migration**: New app, integrate with existing parent/child relationships

#### 7. **notes/** - Notes System (Keep Existing)
**Scope**: Student and parent notes with visibility controls
- **Models**: Keep existing StudentNote, ParentNote
- **Responsibilities**: 
  - Facilitators can write notes on students
  - Admins can write notes on parents  
  - Public flag controls parent visibility
  - Permission enforcement in views and templates
- **Migration**: Keep as-is, already well-designed

#### 8. **adminui/** - Unified Admin Interface
**Scope**: Admin dashboard and management interfaces
- **Models**: None (view-only app)
- **Responsibilities**:
  - Consolidated admin dashboard with metrics
  - List filters, search, and pagination
  - Quick actions for common administrative tasks
  - Per-domain admin interfaces (replace scattered admin views)
  - User management and role assignment
  - System health and integration monitoring
- **Migration**: Consolidate existing admin_interface/ functionality

#### 9. **audit/** - Audit Trail & Logging
**Scope**: Simple audit logging for critical events
- **Models**: AuditLog (new)
- **Responsibilities**:
  - Authorization changes logging
  - Contract sent/signed event tracking
  - Payout and financial event logging
  - User role changes
  - Critical system events
  - Simple audit trail queries
- **Migration**: New app, add logging to existing critical paths

### Removed/Consolidated Apps
- **people/**: Merge into contractors/
- **core/**: Keep Location model, move to appropriate domain or shared utilities
- **admin_interface/**: Consolidate into adminui/
- **communications/**: Keep as-is (small, well-defined scope)
- **dashboard/**: Merge views into adminui/
- **utils/**: Keep for shared utilities and requirements tracking

## Rationale

### Why These Boundaries?
1. **Domain-Driven Design**: Each app represents a clear business domain
2. **Single Responsibility**: Each app has one primary purpose
3. **Minimal Dependencies**: Reduced cross-app coupling
4. **Testability**: Easier to write focused unit and integration tests
5. **Maintainability**: Logical code organization for developers

### Why Not Alternative Approaches?
- **Keep monolithic programs/**: Violates Django best practices, makes testing difficult
- **More granular apps**: Would create too many small apps with excessive dependencies
- **Functional boundaries**: Domain boundaries are more stable than functional ones

### Dependency Management Strategy
- **accounts/** as foundation (no dependencies on other apps)
- **contractors/** depends only on accounts/
- **programs/** depends on contractors/ for eligibility checks
- **scheduling/** depends on contractors/ for availability rules
- **documents/** depends on contractors/ for onboarding docs
- **payments/** depends on accounts/ for invoice recipients
- **notes/** depends on programs/ for student/parent references
- **audit/** depends on accounts/ for event attribution
- **adminui/** can depend on all apps for management interfaces

## Consequences

### Positive
- **Clear separation of concerns** - easier to understand and maintain
- **Better testability** - focused test suites per domain
- **Improved developer experience** - predictable code organization
- **Easier onboarding** - new developers can focus on specific domains
- **Better performance potential** - more targeted queries and caching
- **Stdlib alignment** - minimal third-party dependencies
- **Django 5.x ready** - clean foundation for framework upgrade

### Negative  
- **Migration complexity** - requires careful data migration planning
- **Temporary code duplication** - during transition period
- **Learning curve** - team needs to adapt to new structure
- **Potential circular dependencies** - requires careful dependency management

### Neutral
- **No feature changes** - purely architectural refactor
- **Same user experience** - no UI/UX changes planned
- **Same performance** - no performance impact expected initially

## Implementation Plan

### Phase 1: Foundation & Dependencies (Week 1)
1. **Evaluate third-party dependencies**
   - django-allauth vs native Django auth
   - django-otp usage assessment
   - django-simple-captcha vs native alternatives
2. **Set up pre-commit hooks** (Black, Pylint, isort)
3. **Create audit/ app** and basic logging infrastructure
4. **Plan data migration strategy**

### Phase 2: Domain Extraction (Weeks 2-3)
1. **Create contractors/ app** - move from people/ + extract from programs/
2. **Create documents/ app** - enhance contracts/ with abstraction layer
3. **Create payments/ app** - new foundation for invoice management
4. **Create adminui/ app** - consolidate admin interfaces

### Phase 3: Core Refactoring (Week 4)
1. **Simplify programs/ app** - remove contractor-specific logic
2. **Enhance scheduling/ app** - add bulk operations and grouped availability
3. **Update notes/ app** - ensure visibility policies are enforced
4. **Consolidate templates** - organize by domain, remove duplication

### Phase 4: Integration & Testing (Week 5)
1. **Update all cross-app references**
2. **Comprehensive test coverage** for new boundaries
3. **HTMX pattern consolidation** - ensure consistent partial patterns
4. **Django 5.x compatibility testing**

### Phase 5: Cleanup & Documentation (Week 6)
1. **Remove deprecated code and models**
2. **Update documentation and README**
3. **Performance testing and optimization**
4. **Final code review and quality gates**

## Validation Criteria

### Technical Acceptance
- [ ] All existing functionality preserved
- [ ] All tests passing with improved coverage
- [ ] No circular dependencies between apps
- [ ] Django 5.x compatibility confirmed
- [ ] Pre-commit hooks enforcing code quality
- [ ] All HTMX interactions working correctly

### Business Acceptance  
- [ ] Contractor onboarding gates enforced everywhere
- [ ] Role-based assignment dropdowns working correctly
- [ ] Scheduling bulk operations functional
- [ ] Notes visibility policies enforced
- [ ] DocuSign integration working correctly
- [ ] Admin interfaces consolidated and functional

### Quality Gates
- [ ] Code coverage ≥ 80% for all new/modified code
- [ ] All linting rules passing (Black, Pylint)
- [ ] No security vulnerabilities introduced
- [ ] Performance benchmarks maintained or improved
- [ ] Documentation updated for new architecture

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Data migration failure | High | Low | Comprehensive backup, rollback plan, staging testing |
| Feature regression | High | Medium | Extensive test coverage, gradual rollout |
| Circular dependencies | Medium | Medium | Clear dependency hierarchy, shared utilities pattern |
| Team adoption | Medium | Low | Documentation, code reviews, pair programming |
| Third-party compatibility | Medium | Low | Evaluate alternatives before removal |

## Alternatives Considered

### Alternative 1: Keep Current Structure
- **Pros**: No migration risk, familiar to team
- **Cons**: Technical debt continues, harder to maintain, Django 5.x upgrade difficult
- **Verdict**: Rejected - doesn't solve underlying problems

### Alternative 2: Microservices Architecture  
- **Pros**: Ultimate separation, scalability
- **Cons**: Over-engineering, deployment complexity, not stdlib-aligned
- **Verdict**: Rejected - too complex for current needs

### Alternative 3: Gradual Refactoring
- **Pros**: Lower risk, incremental improvement
- **Cons**: Inconsistent architecture, longer timeline
- **Verdict**: Considered but rejected - clean break preferred

## References

- [Django Apps Best Practices](https://docs.djangoproject.com/en/5.0/ref/applications/)
- [Domain-Driven Design Principles](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [Django 5.x Migration Guide](https://docs.djangoproject.com/en/5.0/releases/5.0/)
- Project Requirements: `site_requirements.json` (96 requirements to preserve)

---

**Next Steps**: Await stakeholder approval, then begin Phase 1 implementation.
