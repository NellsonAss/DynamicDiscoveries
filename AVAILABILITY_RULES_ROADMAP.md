# Availability Rules with Booking Feasibility - Implementation Roadmap

## ✅ COMPLETED (Phase 1 - Foundation)

### Models & Database
- ✅ `AvailabilityRule` model with WEEKLY_RECURRING and DATE_RANGE support
- ✅ `AvailabilityException` model for SKIP and TIME_OVERRIDE
- ✅ `RuleBooking` model for tracking bookings that block time
- ✅ Added `legacy` field to `ContractorAvailability` for migration support
- ✅ All migrations created and applied

### Utilities
- ✅ `occurrence_generator.py` - Generates dynamic occurrences from rules
- ✅ `feasibility_engine.py` - **NEW**: Computes free time gaps after subtracting bookings
  - Merges overlapping rule windows
  - Subtracts bookings to find free gaps
  - Determines which programs fit in remaining time
  - Finds valid start times for booking creation

### Admin Interface
- ✅ Admin for AvailabilityRule with exception inline
- ✅ Admin for AvailabilityException
- ✅ Admin for RuleBooking

### Existing Views & URLs
- ✅ `availability_rules_index` - Main dashboard
- ✅ `availability_rule_create` - Create new rules
- ✅ `availability_rule_detail` - View/edit rules
- ✅ `availability_rule_toggle/archive/delete` - Rule management
- ✅ HTMX partials for calendar and list updates

---

## 🚧 TODO (Phase 2 - Feasibility Integration)

### 1. Enhanced Month Calendar View

**File**: `programs/views.py`

**Update**: `availability_rules_calendar_partial`

```python
@login_required
def availability_rules_calendar_partial(request):
    """HTMX partial: Render calendar with feasibility analysis."""
    from .utils.feasibility_engine import compute_month_feasibility
    from .models import RuleBooking
    
    # ... existing code to get rules ...
    
    # NEW: Compute feasibility for the month
    bookings_qs = RuleBooking.objects.filter(
        rule__contractor=request.user,
        status__in=['confirmed', 'pending']
    )
    
    # Get programs this contractor can offer
    programs_qs = ProgramInstance.objects.filter(
        programs_offered__in=rules_qs.values_list('id', flat=True)
    ).distinct().select_related('buildout__scheduling_config')
    
    # Compute feasibility
    feasibility_map = compute_month_feasibility(
        contractor_id=request.user.id,
        year=year,
        month=month,
        rules_queryset=rules_qs,
        bookings_queryset=bookings_qs,
        programs_queryset=programs_qs
    )
    
    context = {
        ...existing...,
        'feasibility_map': feasibility_map,  # NEW
    }
    
    return render(request, 'programs/availability_rules/_calendar_month.html', context)
```

**Template**: `programs/availability_rules/_calendar_month.html`

Update each day cell to show:
- Summary time ranges (from `day_feasibility.summary_ranges`)
- Feasible programs as badges (from `day_feasibility.feasible_programs`)
- Click handler to open day details

```html
{% for day_date, day_feas in feasibility_map.items %}
<div class="day-cell">
    <div class="day-header">{{ day_date.day }}</div>
    
    <!-- Summary ranges -->
    <div class="time-summary">
        {% for range_str in day_feas.summary_ranges %}
            <span class="badge bg-light text-dark">{{ range_str }}</span>
        {% endfor %}
    </div>
    
    <!-- Feasible programs -->
    <div class="programs-list">
        {% for prog in day_feas.feasible_programs|slice:":3" %}
            <span class="badge bg-primary">{{ prog.title }}</span>
        {% endfor %}
        {% if day_feas.feasible_programs|length > 3 %}
            <span class="badge bg-secondary">+{{ day_feas.feasible_programs|length|add:"-3" }}</span>
        {% endif %}
    </div>
    
    <!-- Click to drill down -->
    <button class="btn btn-sm btn-link"
            hx-get="{% url 'programs:availability_day_details' %}?date={{ day_date|date:'Y-m-d' }}"
            hx-target="#day-details-modal"
            hx-swap="innerHTML">
        Details
    </button>
</div>
{% endfor %}
```

### 2. Day Details View (Drill-Down)

**File**: `programs/views.py`

**New View**: `availability_day_details`

```python
@login_required
def availability_day_details(request):
    """
    Show detailed timeline for a specific day with booking capability.
    
    Displays:
    - Rule windows as blocks
    - Existing bookings
    - Free gaps
    - Booking form with valid start times
    """
    from .utils.feasibility_engine import compute_day_feasibility, find_valid_start_times
    from datetime import datetime
    
    target_date_str = request.GET.get('date')
    target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
    
    # Get rules, bookings, programs
    rules_qs = AvailabilityRule.objects.filter(
        contractor=request.user,
        is_active=True
    ).prefetch_related('exceptions', 'programs_offered')
    
    bookings_qs = RuleBooking.objects.filter(
        rule__contractor=request.user,
        booking_date=target_date
    ).select_related('program', 'child')
    
    programs_qs = ProgramInstance.objects.filter(
        availability_rules__contractor=request.user
    ).distinct().select_related('buildout__scheduling_config')
    
    # Compute feasibility
    day_feasibility = compute_day_feasibility(
        contractor_id=request.user.id,
        target_date=target_date,
        rules_queryset=rules_qs,
        bookings_queryset=bookings_qs,
        programs_queryset=programs_qs
    )
    
    # For booking form: compute valid start times for each program
    program_start_times = {}
    for prog in day_feasibility.feasible_programs:
        valid_starts = find_valid_start_times(
            free_gaps=day_feasibility.free_gaps,
            duration_minutes=prog['duration_minutes'],
            interval_minutes=15
        )
        program_start_times[prog['program_id']] = valid_starts
    
    context = {
        'date': target_date,
        'day_feasibility': day_feasibility,
        'program_start_times': program_start_times,
    }
    
    return render(request, 'programs/availability_rules/_day_details.html', context)
```

**Template**: `programs/availability_rules/_day_details.html`

```html
<div class="modal-header">
    <h5>{{ date|date:"F d, Y" }}</h5>
    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
</div>

<div class="modal-body">
    <!-- Timeline visualization -->
    <div class="timeline">
        <h6>Rule Windows</h6>
        {% for window in day_feasibility.rule_windows %}
        <div class="timeline-block rule-window">
            {{ window.start_time|time:"g:i A" }} - {{ window.end_time|time:"g:i A" }}
        </div>
        {% endfor %}
        
        <h6 class="mt-3">Bookings</h6>
        {% for booking in day_feasibility.bookings %}
        <div class="timeline-block booking">
            <strong>{{ booking.start_time|time:"g:i A" }} - {{ booking.end_time|time:"g:i A" }}</strong><br>
            {{ booking.program }} - {{ booking.child }}
        </div>
        {% endfor %}
        
        <h6 class="mt-3">Free Gaps</h6>
        {% for gap in day_feasibility.free_gaps %}
        <div class="timeline-block free-gap">
            {{ gap.start_time|time:"g:i A" }} - {{ gap.end_time|time:"g:i A" }}
            ({{ gap.duration_minutes }} mins available)
        </div>
        {% endfor %}
    </div>
    
    <!-- Booking form -->
    <div class="booking-form mt-4">
        <h6>Create Booking</h6>
        <form hx-post="{% url 'programs:create_rule_booking' %}"
              hx-target="#day-details-modal"
              hx-swap="innerHTML">
            {% csrf_token %}
            <input type="hidden" name="date" value="{{ date|date:'Y-m-d' }}">
            
            <div class="mb-3">
                <label>Program</label>
                <select name="program_id" class="form-control" id="program-select">
                    {% for prog in day_feasibility.feasible_programs %}
                    <option value="{{ prog.program_id }}"
                            data-duration="{{ prog.duration_minutes }}">
                        {{ prog.title }} ({{ prog.duration_minutes }} mins)
                    </option>
                    {% endfor %}
                </select>
            </div>
            
            <div class="mb-3">
                <label>Start Time</label>
                <select name="start_time" class="form-control" id="start-time-select">
                    <!-- Populated via JS based on selected program -->
                </select>
            </div>
            
            <div class="mb-3">
                <label>Child</label>
                <select name="child_id" class="form-control">
                    {% for child in request.user.children.all %}
                    <option value="{{ child.id }}">{{ child.first_name }}</option>
                    {% endfor %}
                </select>
            </div>
            
            <button type="submit" class="btn btn-primary">Book</button>
        </form>
    </div>
</div>

<script>
// Update valid start times when program changes
document.getElementById('program-select').addEventListener('change', function() {
    const programId = this.value;
    const startTimeSelect = document.getElementById('start-time-select');
    const validTimes = {{ program_start_times|safe }};
    
    startTimeSelect.innerHTML = '';
    if (validTimes[programId]) {
        validTimes[programId].forEach(time => {
            const option = document.createElement('option');
            option.value = time;
            option.textContent = time;
            startTimeSelect.appendChild(option);
        });
    }
});
// Trigger once on load
document.getElementById('program-select').dispatchEvent(new Event('change'));
</script>
```

### 3. Booking Creation View

**File**: `programs/views.py`

**New View**: `create_rule_booking`

```python
@login_required
@require_POST
def create_rule_booking(request):
    """Create a new booking and return updated day details."""
    from datetime import datetime
    
    booking_date_str = request.POST.get('date')
    booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()
    start_time_str = request.POST.get('start_time')
    program_id = request.POST.get('program_id')
    child_id = request.POST.get('child_id')
    
    # Find the rule that applies to this date
    rules = AvailabilityRule.objects.filter(
        contractor=request.user,
        is_active=True,
        date_start__lte=booking_date,
        date_end__gte=booking_date
    )
    
    rule = None
    for r in rules:
        if r.kind == 'DATE_RANGE':
            rule = r
            break
        elif r.kind == 'WEEKLY_RECURRING':
            if booking_date.weekday() in r.get_weekdays_list():
                rule = r
                break
    
    if not rule:
        messages.error(request, "No availability rule found for this date")
        return redirect('programs:availability_rules_index')
    
    # Get program and calculate end time
    program = get_object_or_404(ProgramInstance, id=program_id)
    duration_mins = int(program.buildout.scheduling_config.default_session_duration * 60)
    
    start_time = datetime.strptime(start_time_str, '%H:%M').time()
    start_dt = datetime.combine(booking_date, start_time)
    end_dt = start_dt + timedelta(minutes=duration_mins)
    end_time = end_dt.time()
    
    # Create booking
    booking = RuleBooking.objects.create(
        rule=rule,
        program=program,
        booking_date=booking_date,
        start_time=start_time,
        end_time=end_time,
        booked_by=request.user,
        child_id=child_id,
        status='confirmed'
    )
    
    messages.success(request, f"Booking created for {program.title}")
    
    # Return updated day details
    request.GET = request.GET.copy()
    request.GET['date'] = booking_date_str
    return availability_day_details(request)
```

### 4. Update URLs

**File**: `programs/urls.py`

```python
# Add to existing urlpatterns:
path('contractor/availability-rules/day-details/', views.availability_day_details, name='availability_day_details'),
path('contractor/availability-rules/create-booking/', views.create_rule_booking, name='create_rule_booking'),
```

### 5. Update site_requirements.json

Add REQ-104 for the booking and feasibility system.

---

## 📋 Testing Checklist

### Unit Tests
- [ ] RuleBooking model validation
- [ ] Feasibility engine interval merging
- [ ] Feasibility engine booking subtraction
- [ ] Free gap computation
- [ ] Valid start time finding

### Integration Tests
- [ ] Month calendar shows feasible programs
- [ ] Day details shows timeline correctly
- [ ] Booking creation subtracts time from gaps
- [ ] Multiple overlapping rules handled correctly
- [ ] Program duration respected in feasibility

### User Acceptance
- [ ] "Mon–Fri 1–6 PM" rule displays across weekdays
- [ ] Booking 12:00–1:00 blocks only that hour
- [ ] 2-hour program disappears when max gap < 120 mins
- [ ] Rules list shows rolled-up rules, not daily entries
- [ ] Day details shows granular timeline with free gaps
- [ ] Valid start times only shown for feasible slots

---

## 🎨 UI/UX Enhancements

### Month Calendar Cell
```html
<div class="calendar-day-cell">
    <div class="day-number">22</div>
    <div class="time-ranges">
        <span class="badge bg-light">1-6p</span>
    </div>
    <div class="programs">
        <span class="badge bg-primary" title="STEAM Workshop">STEAM</span>
        <span class="badge bg-success" title="Literary Arts">Literary</span>
        <span class="badge bg-secondary">+2</span>
    </div>
    <button class="btn-details">Details</button>
</div>
```

### Day Details Timeline (Visual)
```
9:00 AM ┌─────────────────────────┐  Rule Window
        │                         │
12:00 PM│  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│  Booking (STEAM - Jane)
        │                         │
        │  ░░░░░░░░░░░░░░░░░░░░░░│  Free Gap (3 hours)
5:00 PM └─────────────────────────┘
```

---

## 🚀 Deployment Steps

1. Run migrations: `python manage.py migrate`
2. Test feasibility engine independently
3. Update calendar partial template
4. Add day details view and template
5. Add booking creation endpoint
6. Test HTMX swaps
7. Update documentation
8. Train users on new workflow

---

## 📝 Notes

- **Backward Compatibility**: Legacy `ContractorAvailability` entries marked with `legacy=True` still visible in admin
- **Performance**: Feasibility computed per-request for visible month only (no caching needed for MVP)
- **Timezone**: All times stored in contractor's timezone (configurable per rule)
- **Minimum Gap**: 15-minute minimum enforced by feasibility engine
- **Program Duration**: Pulled from `ProgramBuildoutScheduling.default_session_duration`

---

## 📚 Key Files Reference

| File | Purpose |
|------|---------|
| `programs/models.py` | AvailabilityRule, AvailabilityException, RuleBooking |
| `programs/utils/occurrence_generator.py` | Dynamic occurrence generation |
| `programs/utils/feasibility_engine.py` | **NEW** - Gap computation, feasibility |
| `programs/views.py` | Calendar, day details, booking creation |
| `programs/templates/availability_rules/_calendar_month.html` | Month grid with feasibility |
| `programs/templates/availability_rules/_day_details.html` | **NEW** - Timeline + booking form |
| `programs/urls.py` | URL patterns |

---

This roadmap provides the complete architecture. The foundation is built - now implement Phase 2 to bring booking/feasibility to life! 🎯

