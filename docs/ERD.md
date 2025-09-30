Data Model ERD

Mermaid ER Diagram
```mermaid
erDiagram
  accounts_user ||--o| accounts_profile : has

  accounts_user ||--o{ programs_child : has
  programs_child }o--|| programs_registration : participates_in
  programs_registration }o--|| programs_programinstance : registers_for

  programs_programtype ||--o{ programs_programbuildout : has
  programs_programbuildout ||--o{ programs_programinstance : has_instances

  programs_role ||--o{ programs_responsibility : defines
  programs_programbuildout ||--o{ programs_buildoutresponsibilityline : uses
  programs_responsibility ||--o{ programs_buildoutresponsibilityline : linked

  accounts_user ||--o{ programs_buildoutroleline : assigned_as_contractor
  programs_role ||--o{ programs_buildoutroleline : assigned_role
  programs_programbuildout ||--o{ programs_buildoutroleline : in_buildout

  programs_basecost ||--o{ programs_buildoutbasecostassignment : base_cost_for
  programs_programbuildout ||--o{ programs_buildoutbasecostassignment : has_cost

  programs_location ||--o{ programs_buildoutlocationassignment : loc_cost_for
  programs_programbuildout ||--o{ programs_buildoutlocationassignment : has_loc

  programs_registrationform ||--o{ programs_formquestion : has
  programs_registrationform ||--o{ programs_programbuildout : default_for
  programs_programinstance }o--|| programs_registrationform : assigned_form

  people_contractor ||--|| accounts_user : is_user
  people_ndasignature ||--|| people_contractor : for

  contracts_contract }o--|| people_contractor : for
  contracts_contract }o--o| programs_programbuildout : about
  contracts_legaldocumenttemplate ||--o{ contracts_contract : used_by

  communications_contact {
    int id
    char parent_name
    char email
    char phone
    char interest
    text message
    char status
    datetime created_at
  }

  notes_studentnote }o--|| programs_child : for
  notes_parentnote }o--|| accounts_user : for

  %% Enhanced scheduling
  accounts_user ||--o{ programs_contractoravailability : has_availability
  programs_contractoravailability ||--o{ programs_availabilityprogram : offers
  programs_availabilityprogram }o--|| programs_programbuildout : offering_of
  programs_programinstance ||--o{ programs_programsession : has_sessions
  programs_availabilityprogram ||--o{ programs_programsession : scheduled_in
  programs_programsession ||--o{ programs_sessionbooking : has_bookings
  programs_sessionbooking }o--|| programs_child : booking_for

  programs_holiday
  programs_contractordayoffrequest }o--|| accounts_user : requested_by
```

Notes
- Field names and additional attributes (choices, validators) are defined in app `models.py` files. This diagram focuses on relationships and cardinality.
- Some legacy models exist for backward compatibility (e.g., `BuildoutRoleAssignment`, `BuildoutResponsibilityAssignment`). New relationships use the `*Line` and `*Assignment` models.

