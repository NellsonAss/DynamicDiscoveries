Management Commands

Programs app
- create_sample_buildout: Creates a sample `ProgramBuildout` with summary output.
  - Usage: `python manage.py create_sample_buildout`

- setup_comprehensive_test_data: Seeds users, children, locations, program types, buildouts, instances, registrations, and prints credentials and URLs.
  - Usage: `python manage.py setup_comprehensive_test_data`

- setup_test_accounts: Seeds core accounts with passwords and sample programs; prints credentials.
  - Usage: `python manage.py setup_test_accounts`

- fix_user_roles: Ensures specific users have Admin/Parent/Contractor roles; seeds sample programs.
  - Usage: `python manage.py fix_user_roles`

- load_test_data: Orchestrates seeding by calling `seed_roles`, `create_sample_buildout`, `setup_comprehensive_test_data`, `seed_contacts`; creates additional data.
  - Usage: `python manage.py load_test_data`

- populate_holidays: Populates `Holiday` records for N years.
  - Usage: `python manage.py populate_holidays --years 5 --start-year 2025`

- seed_roles: Seeds core `Role` entries and `BaseCost` items.
  - Usage: `python manage.py seed_roles`

- setup_admin_support_responsibilities: Seeds responsibilities for the "Admin Support" role.
  - Usage: `python manage.py setup_admin_support_responsibilities`

Utils app
- manage_requirements: Manage `site_requirements.json` via CLI.
  - List: `python manage.py manage_requirements --list`
  - Add: `python manage.py manage_requirements --add REQ-003 "Feature Title" "Description"`
  - Update: `python manage.py manage_requirements --update REQ-003 implemented`
  - Validate: `python manage.py manage_requirements --validate`

