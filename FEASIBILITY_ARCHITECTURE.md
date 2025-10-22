# Feasibility Engine Architecture

## System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     USER REQUEST                                     │
│          "Show me available programs for October 22"                │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        VIEW LAYER                                    │
│  availability_rules_calendar_partial() or availability_day_details() │
│                                                                      │
│  1. Fetch active AvailabilityRules for contractor                   │
│  2. Fetch RuleBookings for date range                               │
│  3. Fetch ProgramInstances with durations                           │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FEASIBILITY ENGINE                                │
│              (programs/utils/feasibility_engine.py)                  │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ Step 1: Get Rule Windows                                   │    │
│  │ ────────────────────────────────────────────────────────── │    │
│  │ - Filter rules by date range                               │    │
│  │ - Apply weekday filter (for WEEKLY_RECURRING)              │    │
│  │ - Check exceptions (SKIP, TIME_OVERRIDE)                   │    │
│  │                                                             │    │
│  │ Result: List[TimeInterval]                                 │    │
│  │   Example: [(9:00, 17:00), (19:00, 21:00)]                │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                │                                     │
│                                ▼                                     │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ Step 2: Merge Overlapping Windows                          │    │
│  │ ────────────────────────────────────────────────────────── │    │
│  │ Algorithm: _merge_overlapping_intervals()                  │    │
│  │                                                             │    │
│  │ Input:  [(9:00, 13:00), (12:00, 17:00), (19:00, 21:00)]   │    │
│  │ Output: [(9:00, 17:00), (19:00, 21:00)]                   │    │
│  │                                                             │    │
│  │ - Sort by start time                                       │    │
│  │ - Merge consecutive/overlapping intervals                  │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                │                                     │
│                                ▼                                     │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ Step 3: Get Bookings                                       │    │
│  │ ────────────────────────────────────────────────────────── │    │
│  │ - Query RuleBooking for date                               │    │
│  │ - Filter by status (confirmed, pending)                    │    │
│  │                                                             │    │
│  │ Result: List[TimeInterval]                                 │    │
│  │   Example: [(12:00, 13:00), (15:00, 16:00)]               │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                │                                     │
│                                ▼                                     │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ Step 4: Subtract Bookings to Find Free Gaps                │    │
│  │ ────────────────────────────────────────────────────────── │    │
│  │ Algorithm: _subtract_intervals()                           │    │
│  │                                                             │    │
│  │ Available: [(9:00, 17:00)]                                 │    │
│  │ Bookings:  [(12:00, 13:00), (15:00, 16:00)]               │    │
│  │                                                             │    │
│  │ Process:                                                    │    │
│  │   Start with: [9:00-17:00]                                 │    │
│  │   Subtract [12:00-13:00]:                                  │    │
│  │     → [9:00-12:00, 13:00-17:00]                           │    │
│  │   Subtract [15:00-16:00]:                                  │    │
│  │     → [9:00-12:00, 13:00-15:00, 16:00-17:00]              │    │
│  │                                                             │    │
│  │ Output: [(9:00, 12:00), (13:00, 15:00), (16:00, 17:00)]   │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                │                                     │
│                                ▼                                     │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ Step 5: Determine Program Feasibility                      │    │
│  │ ────────────────────────────────────────────────────────── │    │
│  │ For each program:                                          │    │
│  │   1. Get duration from ProgramBuildoutScheduling           │    │
│  │   2. Check if any free gap ≥ program duration              │    │
│  │   3. If yes → FEASIBLE                                     │    │
│  │                                                             │    │
│  │ Example:                                                    │    │
│  │   Program A (90 mins): ✅ Fits in [9:00-12:00] (180m)     │    │
│  │   Program B (120 mins): ✅ Fits in [9:00-12:00] (180m)    │    │
│  │   Program C (150 mins): ✅ Fits in [9:00-12:00] (180m)    │    │
│  │   Program D (180 mins): ✅ Fits in [9:00-12:00] (180m)    │    │
│  │   Program E (210 mins): ❌ No gap ≥ 210 minutes           │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                │                                     │
│                                ▼                                     │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ Step 6: Find Valid Start Times (for booking form)          │    │
│  │ ────────────────────────────────────────────────────────── │    │
│  │ Algorithm: find_valid_start_times()                        │    │
│  │                                                             │    │
│  │ For Program A (90 mins) in gap [9:00-12:00]:              │    │
│  │   Try every 15-minute increment:                           │    │
│  │     9:00 + 90m = 10:30 ✅ (< 12:00)                       │    │
│  │     9:15 + 90m = 10:45 ✅ (< 12:00)                       │    │
│  │     9:30 + 90m = 11:00 ✅ (< 12:00)                       │    │
│  │     9:45 + 90m = 11:15 ✅ (< 12:00)                       │    │
│  │     10:00 + 90m = 11:30 ✅ (< 12:00)                      │    │
│  │     10:15 + 90m = 11:45 ✅ (< 12:00)                      │    │
│  │     10:30 + 90m = 12:00 ✅ (exactly fits)                 │    │
│  │     10:45 + 90m = 12:15 ❌ (exceeds gap)                  │    │
│  │                                                             │    │
│  │   Valid starts: [9:00, 9:15, 9:30, ..., 10:30]            │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                │                                     │
│                                ▼                                     │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ Return: DayFeasibility                                      │    │
│  │ ────────────────────────────────────────────────────────── │    │
│  │ {                                                           │    │
│  │   date: 2025-10-22,                                        │    │
│  │   contractor_id: 42,                                       │    │
│  │   rule_windows: [(9:00, 17:00)],                          │    │
│  │   bookings: [                                              │    │
│  │     {start: 12:00, end: 13:00, program: "STEAM", ...}     │    │
│  │   ],                                                        │    │
│  │   free_gaps: [                                             │    │
│  │     (9:00, 12:00),                                         │    │
│  │     (13:00, 15:00),                                        │    │
│  │     (16:00, 17:00)                                         │    │
│  │   ],                                                        │    │
│  │   feasible_programs: [                                     │    │
│  │     {id: 1, title: "STEAM", duration: 90, fits: true},    │    │
│  │     {id: 2, title: "Literary", duration: 60, fits: true}  │    │
│  │   ],                                                        │    │
│  │   summary_ranges: ["9a-5p"]                                │    │
│  │ }                                                           │    │
│  └────────────────────────────────────────────────────────────┘    │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      TEMPLATE LAYER                                  │
│          _calendar_month.html or _day_details.html                   │
│                                                                      │
│  Render:                                                             │
│  - Calendar cells with feasible programs                            │
│  - Day timeline with rule windows + bookings + gaps                 │
│  - Booking form with valid start times dropdown                     │
│                                                                      │
│  HTMX:                                                               │
│  - Month navigation swaps calendar partial                          │
│  - Day click swaps modal with day details                           │
│  - Booking submit updates day details                               │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow Example

### Scenario: Contractor views Tuesday, Oct 22

**Input:**
- Contractor: Dr. Smith (ID: 42)
- Date: 2025-10-22 (Tuesday)
- Active Rules:
  - Rule #1: Mon-Fri, 9 AM - 5 PM
- Existing Bookings:
  - STEAM Workshop: 12 PM - 1 PM (Jane)
  - Literary Arts: 3 PM - 4 PM (Tom)
- Programs:
  - STEAM (90 mins)
  - Literary (60 mins)
  - Robotics (120 mins)

**Processing:**

1. **Get Rules**: Rule #1 applies (Tuesday is a weekday)
   - Result: [(9:00, 17:00)]

2. **Merge**: Only one rule, nothing to merge
   - Result: [(9:00, 17:00)]

3. **Get Bookings**: 2 bookings on this date
   - Result: [(12:00, 13:00), (15:00, 16:00)]

4. **Subtract**:
   ```
   Start:  [9:00────────────────17:00]
   
   Booking 1: [12:00─13:00]
   After:  [9:00──12:00][13:00───17:00]
   
   Booking 2:              [15:00─16:00]
   After:  [9:00──12:00][13:00─15:00][16:00─17:00]
   ```
   - Result: [(9:00, 12:00), (13:00, 15:00), (16:00, 17:00)]
   - Durations: 180 mins, 120 mins, 60 mins

5. **Check Feasibility**:
   - STEAM (90m): ✅ Fits in gap 1 (180m) or gap 2 (120m)
   - Literary (60m): ✅ Fits in all gaps
   - Robotics (120m): ✅ Fits in gap 1 (180m) or gap 2 (120m exactly)

6. **Find Valid Starts** (for STEAM, 90 mins):
   - Gap 1 [9:00-12:00]:
     - 9:00, 9:15, 9:30, 9:45, 10:00, 10:15, 10:30
   - Gap 2 [13:00-15:00]:
     - 13:00, 13:15, 13:30
   - Gap 3 [16:00-17:00]:
     - ❌ Too short (60 mins < 90 mins)

**Output to Template:**
```html
<div class="day-cell">
    <div class="day-number">22</div>
    <div class="time-summary">
        <span class="badge">9a-5p</span>
    </div>
    <div class="programs">
        <span class="badge bg-primary">STEAM</span>
        <span class="badge bg-success">Literary</span>
        <span class="badge bg-info">Robotics</span>
    </div>
    <button hx-get="/day-details?date=2025-10-22">Details</button>
</div>
```

---

## Key Algorithms in Detail

### 1. Interval Merging (Union of Overlapping Ranges)

**Problem**: Multiple rules can create overlapping time windows

**Solution**: Sort and merge

```python
def _merge_overlapping_intervals(intervals):
    if not intervals:
        return []
    
    # Convert to minutes, sort by start time
    sorted_intervals = sorted([i.to_minutes() for i in intervals])
    
    merged = []
    current_start, current_end = sorted_intervals[0]
    
    for start, end in sorted_intervals[1:]:
        if start <= current_end:
            # Overlap detected - extend current interval
            current_end = max(current_end, end)
        else:
            # No overlap - save current, start new
            merged.append((current_start, current_end))
            current_start, current_end = start, end
    
    merged.append((current_start, current_end))
    return [TimeInterval.from_minutes(s, e) for s, e in merged]
```

**Example**:
```
Input:  [(9, 13), (12, 17), (19, 21)]
Sorted: [(9, 13), (12, 17), (19, 21)]

Step 1: current = (9, 13)
Step 2: Check (12, 17)
        12 <= 13 → overlap! → extend to (9, 17)
Step 3: Check (19, 21)
        19 > 17 → no overlap → save (9, 17), start new (19, 21)

Output: [(9, 17), (19, 21)]
```

### 2. Interval Subtraction (Gap Finding)

**Problem**: Remove booked time from available windows

**Solution**: Iteratively carve out bookings

```python
def _subtract_intervals(available, occupied):
    result = []
    
    for free_start, free_end in available:
        current_free = [(free_start, free_end)]
        
        for occ_start, occ_end in occupied:
            new_free = []
            for seg_start, seg_end in current_free:
                if occ_end <= seg_start or occ_start >= seg_end:
                    # No overlap - keep segment
                    new_free.append((seg_start, seg_end))
                elif occ_start <= seg_start and occ_end >= seg_end:
                    # Completely covered - discard
                    pass
                elif occ_start > seg_start and occ_end < seg_end:
                    # Split - booking in middle
                    new_free.append((seg_start, occ_start))
                    new_free.append((occ_end, seg_end))
                elif occ_start <= seg_start < occ_end < seg_end:
                    # Overlap at start
                    new_free.append((occ_end, seg_end))
                elif seg_start < occ_start < seg_end <= occ_end:
                    # Overlap at end
                    new_free.append((seg_start, occ_start))
            
            current_free = new_free
        
        result.extend(current_free)
    
    return [TimeInterval.from_minutes(s, e) for s, e in result if e - s >= 15]
```

**Cases Handled**:
```
Case 1: No Overlap
  Free:    [──────]
  Booking:           [───]
  Result:  [──────]

Case 2: Complete Cover
  Free:    [──────]
  Booking: [────────────]
  Result:  (nothing)

Case 3: Split
  Free:    [──────────]
  Booking:    [───]
  Result:  [──]   [──]

Case 4: Partial Start
  Free:    [──────]
  Booking: [───]
  Result:     [───]

Case 5: Partial End
  Free:    [──────]
  Booking:     [───]
  Result:  [───]
```

---

## Performance Considerations

### Time Complexity
- **Merging**: O(n log n) for sorting, O(n) for merging → **O(n log n)**
- **Subtraction**: O(n × m) where n = available windows, m = bookings
- **Feasibility Check**: O(p × g) where p = programs, g = gaps
- **Valid Start Times**: O(g × t) where g = gaps, t = time slots per gap

### Typical Case
- Rules: 5-10 per day
- Bookings: 3-5 per day
- Programs: 10-20 total
- Gaps: 3-5 per day

**Total**: < 1ms per day, ~30ms for full month

### Optimization Opportunities (Future)
1. **Caching**: Cache month feasibility (invalidate on booking change)
2. **Incremental**: Only recompute affected days when booking added
3. **Parallel**: Compute multiple days in parallel for large ranges
4. **Database**: Move interval logic to database with PostGIS

---

## Testing Strategy

### Unit Tests
```python
def test_merge_overlapping():
    intervals = [
        TimeInterval(time(9, 0), time(13, 0)),
        TimeInterval(time(12, 0), time(17, 0))
    ]
    merged = _merge_overlapping_intervals(intervals)
    assert len(merged) == 1
    assert merged[0].to_minutes() == (540, 1020)  # 9 AM - 5 PM

def test_subtract_splits_interval():
    available = [TimeInterval(time(9, 0), time(17, 0))]
    occupied = [TimeInterval(time(12, 0), time(13, 0))]
    gaps = _subtract_intervals(available, occupied)
    assert len(gaps) == 2
    assert gaps[0].to_minutes() == (540, 720)  # 9 AM - 12 PM
    assert gaps[1].to_minutes() == (780, 1020)  # 1 PM - 5 PM
```

### Integration Tests
```python
def test_day_feasibility_with_bookings():
    # Create rule, booking, programs
    rule = AvailabilityRule.objects.create(...)
    booking = RuleBooking.objects.create(...)
    program = ProgramInstance.objects.create(...)
    
    # Compute feasibility
    result = compute_day_feasibility(
        contractor_id=1,
        target_date=date(2025, 10, 22),
        rules_queryset=AvailabilityRule.objects.filter(id=rule.id),
        bookings_queryset=RuleBooking.objects.filter(id=booking.id),
        programs_queryset=ProgramInstance.objects.filter(id=program.id)
    )
    
    # Assert
    assert len(result.free_gaps) > 0
    assert program.id in [p['program_id'] for p in result.feasible_programs]
```

---

This architecture provides the foundation for sophisticated booking and scheduling workflows while maintaining simplicity and performance! 🎯

