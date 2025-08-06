# Program Buildout System Guide

## Overview

The Program Buildout system defines how each ProgramType is operationally delivered, including session days, revenue, role responsibilities, payout percentages, and estimated time. This system is used for contract generation, payout planning, and resource allocation.

## Models

### Role
Defines roles that can be assigned to program buildouts.

**Fields:**
- `name`: Role name (e.g., "Facilitator", "Curriculum Designer")
- `default_percent_of_revenue`: Default percentage of revenue for this role
- `responsibilities`: Description of role responsibilities

### ProgramBuildout
Defines how a ProgramType is operationally delivered.

**Fields:**
- `program_type`: Link to ProgramType
- `title`: Buildout title (e.g., "12 Students, 4 Days")
- `expected_students`: Number of expected students
- `num_days`: Program duration in days
- `sessions_per_day`: Number of sessions per day (default: 1)
- `total_expected_revenue`: Total expected revenue

**Methods:**
- `get_total_role_percentage()`: Calculate sum of all role percentages
- `is_percentage_valid()`: Check if role percentages sum to 100%

### ProgramRole
Defines a role assignment within a program buildout.

**Fields:**
- `buildout`: Link to ProgramBuildout
- `role`: Link to Role
- `percent_of_revenue`: Percentage of revenue for this role
- `hour_frequency`: How hours are calculated (see Frequency Types below)
- `hour_multiplier`: Base number for frequency calculation
- `override_hours`: Manual override for hours (optional)

**Methods:**
- `calculate_total_hours()`: Compute total expected hours based on frequency logic

## Frequency Types

The `hour_frequency` field determines how hours are calculated:

- **PER_PROGRAM**: Applies once per entire program (e.g., curriculum design time)
- **PER_SESSION**: Applies once per session (usually 1 per day)
- **PER_KID**: Applies once per student (e.g., prep/feedback)
- **PER_SESSION_PER_KID**: Applies once per kid per session (e.g., data entry)
- **ADMIN_FLAT**: Fixed total hours assigned manually
- **OVERRIDE**: User-specified direct hour override (no formula)

## Hour Calculation Examples

### PER_PROGRAM
- `hour_multiplier = 8.0`
- Result: 8 hours total for the entire program

### PER_SESSION
- `hour_multiplier = 3.0`, `num_days = 4`, `sessions_per_day = 1`
- Result: 3.0 × 4 × 1 = 12 hours total

### PER_KID
- `hour_multiplier = 0.5`, `expected_students = 12`
- Result: 0.5 × 12 = 6 hours total

### PER_SESSION_PER_KID
- `hour_multiplier = 0.25`, `expected_students = 12`, `num_days = 4`, `sessions_per_day = 1`
- Result: 0.25 × 12 × 4 × 1 = 12 hours total

### ADMIN_FLAT
- `hour_multiplier = 5.0`
- Result: 5 hours total (fixed amount)

### OVERRIDE
- `override_hours = 10.0`
- Result: 10 hours total (ignores frequency logic)

## Workflow

### 1. Create ProgramType
```python
program_type = ProgramType.objects.create(
    name="STEAM Summer 4-Day",
    description="A 4-day STEAM program for elementary students",
    target_grade_levels="K-5"
)
```

### 2. Create ProgramBuildout
```python
buildout = ProgramBuildout.objects.create(
    program_type=program_type,
    title="12 Students, 4 Days",
    expected_students=12,
    num_days=4,
    sessions_per_day=1,
    total_expected_revenue=Decimal('1600.00')
)
```

### 3. Assign Roles
```python
facilitator_role = Role.objects.get(name="Facilitator")

ProgramRole.objects.create(
    buildout=buildout,
    role=facilitator_role,
    percent_of_revenue=Decimal('24.00'),
    hour_frequency="PER_SESSION",
    hour_multiplier=Decimal('3.0')
)
```

### 4. Validate Buildout
```python
if buildout.is_percentage_valid():
    print("Buildout is valid!")
else:
    print(f"Role percentages sum to {buildout.get_total_role_percentage()}% (should be 100%)")
```

## Admin Interface

### Role Management
- Access via Django Admin: `/admin/programs/role/`
- View all roles with their default percentages and responsibilities
- Create, edit, or delete roles

### ProgramBuildout Management
- Access via Django Admin: `/admin/programs/programbuildout/`
- Create buildouts with inline role assignments
- See percentage validation status
- View calculated hours for each role

### ProgramRole Management
- Access via Django Admin: `/admin/programs/programrole/`
- View all role assignments across buildouts
- See calculated hours for each assignment

## Management Commands

### Seed Initial Roles
```bash
python manage.py seed_roles
```
Creates the initial 8 roles with their default percentages and responsibilities.

### Create Sample Buildout
```bash
python manage.py create_sample_buildout
```
Creates a sample buildout to demonstrate the system functionality.

## Integration with Contracts

The buildout system is designed to integrate with contract generation:

1. **Contract Terms**: Use `ProgramRole` data to pre-fill contract terms
2. **Payment Calculation**: Use `percent_of_revenue` to calculate contractor payments
3. **Hour Expectations**: Use `calculate_total_hours()` to set hour expectations
4. **Revenue Allocation**: Use buildout data to validate budget expectations

## Example Use Case

```python
# Get a buildout
buildout = ProgramBuildout.objects.get(title="12 Students, 4 Days")

# Calculate facilitator payment for a $1600 program
facilitator_role = buildout.roles.get(role__name="Facilitator")
facilitator_payment = (facilitator_role.percent_of_revenue / 100) * 1600
facilitator_hours = facilitator_role.calculate_total_hours()

print(f"Facilitator: ${facilitator_payment:.2f} for {facilitator_hours:.1f} hours")
# Output: Facilitator: $384.00 for 12.0 hours
```

## Validation Rules

1. **Role Percentages**: Must sum to 100% for each buildout
2. **Unique Roles**: Each role can only be assigned once per buildout
3. **Override Hours**: Only used when `hour_frequency = "OVERRIDE"`
4. **Positive Values**: All numeric fields must be positive

## Future Enhancements

- HTMX form wizard for creating buildouts with real-time validation
- Visual payout breakdown display
- Contract template integration
- Revenue tracking and comparison
- Resource allocation planning 