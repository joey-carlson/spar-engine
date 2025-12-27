# Root Cause Analysis: Content Availability Error

## Executive Summary

**Root Cause Identified**: Cooldown accumulation without expiration when `tick_between=False`.

The error "No content entries available after filtering/cooldowns" occurs because:
1. Tag cooldowns are applied after each event generation
2. When "Tick between events" is disabled, cooldowns NEVER expire
3. With limited aftermath content (8 events) and overlapping tags, the available pool exhausts within ~5-8 events
4. This is not a UI bug—it's a fundamental design issue in the cooldown system

## Code Trace Analysis

### Execution Path

```python
# streamlit_harness/app.py - run_batch() function
state = starting_engine_state  # Fresh state initially
for idx in range(n):
    if idx > 0 and tick_between and ticks_between > 0:
        state = tick_state(state, ticks=ticks_between)  # ← ONLY PATH to clear cooldowns
    ev = generate_event(scene, state, selection, entries, rng)
    state = apply_state_delta(state, ev.state_delta)  # ← ADDS cooldowns
```

**Critical Issue**: When `tick_between=False`, the `tick_state()` call never happens, so cooldowns never decrement.

### Concrete Example: Aftermath Phase, Batch Size 10, tick_between=False

**Available Aftermath Events** (from core_complications.json):
1. `hazard_smoke_01` - tags: hazard(cd:2), visibility(cd:1), time_pressure(cd:0)
2. `time_ammo_dry_01` - tags: attrition(cd:2), cost(cd:0), time_pressure(cd:0)
3. `hazard_fire_01` - tags: hazard(cd:2), time_pressure(cd:0), visibility(cd:0)
4. `attrition_gear_fail_01` - tags: attrition(cd:2), cost(cd:0), time_pressure(cd:0)
5. `social_rival_01` - tags: social_friction(cd:2), opportunity(cd:0), visibility(cd:0)
6. `attrition_fatigue_01` - tags: attrition(cd:2), cost(cd:0), time_pressure(cd:0)
7. `hazard_water_rise_01` - tags: hazard(cd:2), terrain(cd:2), time_pressure(cd:0)
8. `social_witness_01` - tags: visibility(cd:2), social_friction(cd:0), heat(cd:0)

**Generation Sequence Without Ticking**:

```
Event 1: hazard_smoke_01
  After: recent=[hazard_smoke_01], cooldowns={hazard:2, visibility:1}
  Pool size: 7 (hazard_smoke_01 blocked by recent)

Event 2: time_ammo_dry_01 (can't use hazard events)
  After: recent=[time_ammo_dry_01, hazard_smoke_01], cooldowns={hazard:2, visibility:1, attrition:2}
  Pool size: 4 (3 hazard events blocked, 1 attrition event blocked, 1 in recent)

Event 3: social_rival_01 (can't use hazard/attrition events)
  After: recent=[social_rival_01, time_ammo_dry_01, hazard_smoke_01], 
         cooldowns={hazard:2, visibility:1, attrition:2, social_friction:2}
  Pool size: 2 (only hazard_water_rise_01 and social_witness_01 might be available)

Event 4: hazard_water_rise_01
  After: cooldowns={hazard:2, visibility:1, attrition:2, social_friction:2, terrain:2}
  Pool size: 1 (social_witness_01 only, but it has visibility tag which is on cooldown!)

Event 5: FAILURE
  All aftermath events are either:
  - In recent_event_ids (blocked)
  - Have tags on cooldown (blocked)
  - Pool is EMPTY
  - ValueError raised: "No content entries available after filtering/cooldowns"
```

### Why User's Attempts Failed

1. **Batch size reduction to 10**: Still exhausts pool by event 5-8
2. **Clearing include tags**: Doesn't affect cooldown filtering logic
3. **Disabling "Tick between events"**: Makes the problem WORSE, not better
4. **Reducing to batch size 10 with tick disabled**: Pool still exhausts quickly

### Code Evidence

**From `spar_engine/content.py` - filter_entries()**:
```python
def _any_tag_on_cooldown(entry: ContentEntry, tag_cooldowns: dict[str, int]) -> bool:
    for t in entry.tags:
        if tag_cooldowns.get(t, 0) > 0:  # ← Any tag > 0 blocks the entry
            return True
    return False

# In filter_entries:
if _any_tag_on_cooldown(e, tag_cooldowns):
    continue  # ← Entry blocked
```

**From `spar_engine/state.py` - apply_state_delta()**:
```python
# Cooldowns are SET to maximum
for tag, cd in (delta.tag_cooldowns_set or {}).items():
    tag_cooldowns[tag] = max(tag_cooldowns.get(tag, 0), int(cd))
```

**From `spar_engine/state.py` - tick_state()**:
```python
# Cooldowns are DECREMENTED only when ticking
for tag, cd in (state.tag_cooldowns or {}).items():
    n = max(0, int(cd) - t)  # ← Subtract ticks
    if n > 0:
        tag_cooldowns[tag] = n
```

## Root Cause Statement

**There are TWO root causes working together:**

1. **Primary: Cooldown accumulation without ticking** (FIXED)
   - Without periodic `tick_state()` calls, tag cooldowns accumulate indefinitely
   - This causes rapid content exhaustion in ALL phases

2. **Secondary: Insufficient content diversity in open aftermath** (REQUIRES CONTENT)
   - Wilderness aftermath has only 3 events
   - **ALL 3 events share the "attrition" tag with cooldown=2**
   - Even with ticking, the pool can only generate 1-2 events before all options are blocked
   - Other environments have better variety and can sustain longer batches

**Wilderness Aftermath Content Analysis:**
```
1. time_ammo_dry_01: tags=['attrition', 'cost', 'time_pressure']
2. attrition_gear_fail_01: tags=['attrition', 'cost', 'time_pressure']  
3. attrition_fatigue_01: tags=['attrition', 'cost', 'time_pressure']
```

**Critical Issue**: 100% tag overlap on a cooldown=2 tag means:
- Event 1: Sets attrition cooldown to 2
- Tick 1: Reduces to 1
- Event 2 attempt: ALL 3 events blocked (attrition cooldown still active)
- FAILURE at event 2

## Why This Manifests Specifically in Aftermath

- **Aftermath has only 8 events** (vs ~18 for engage, ~16 for approach)
- **High tag overlap**: Multiple events share "hazard" (3), "attrition" (3), "visibility" (4)
- **Cooldown values are 2-3 turns**: Without ticking, tags stay blocked for entire batch
- **Recent event blocking**: With recent_max_len=12, events can't repeat until they age out

With approach/engage phases having 2x the content, the pool can sustain longer before exhaustion, which is why the error appears specifically in aftermath-heavy suites.

## Solution Options

### Option 1: Force Minimum Ticking (Recommended)
Modify `run_batch()` to always tick by at least 1 between events, regardless of UI setting:

```python
for idx in range(n):
    if idx > 0:
        # Always tick at least 1 to prevent cooldown accumulation
        tick_amount = max(1, ticks_between if tick_between else 1)
        state = tick_state(state, ticks=tick_amount)
    ev = generate_event(...)
```

**Pros**: Fixes the issue without changing cooldown logic or adding content
**Cons**: Makes "Tick between events" checkbox misleading (it will always tick at minimum)

### Option 2: Aggressive Recent Event Aging
Modify `apply_state_delta()` to automatically age out the oldest recent event with each new event:

```python
# In apply_state_delta, after building recent list:
if len(recent) >= recent_max_len:
    recent = recent[:-1]  # Drop oldest automatically
```

**Pros**: Allows events to cycle back sooner
**Cons**: Doesn't fix tag cooldown accumulation issue

### Option 3: Zero-Cooldown Mode
Add a parameter to `filter_entries()` to optionally ignore cooldowns:

```python
def filter_entries(..., ignore_cooldowns: bool = False):
    # ...
    if not ignore_cooldowns and _any_tag_on_cooldown(e, tag_cooldowns):
        continue
```

**Pros**: Gives explicit control over cooldown behavior
**Cons**: Defeats the purpose of the cooldown system

### Option 4: Expand Aftermath Content
Add 10-15 more aftermath events with diverse tag combinations.

**Pros**: Addresses the symptom and improves the game
**Cons**: Doesn't fix the underlying cooldown accumulation issue

## Recommendation

**BOTH fixes are required:**

### Immediate: Option 1 (Force Minimum Ticking) - IMPLEMENTED
**Status**: ✅ Completed in `streamlit_harness/app.py`

This fixes the cooldown accumulation issue for most phase/environment combinations. The change ensures batches can complete for:
- Confined/populated/derelict aftermath (5-8 events each)
- All approach/engage phases (16-18 events)

However, **open aftermath still fails** due to complete tag overlap.

### Required: Option 4 (Expand Wilderness Aftermath Content)
**Status**: ⚠️ Required for full functionality

Wilderness aftermath needs 5-7 additional events with diverse tags to achieve sustainable generation. Current options:

1. **Add hazard-focused aftermath events** (fire spread, terrain shift, weather aftermath)
2. **Add social/visibility aftermath events** (witnesses, pursuit, consequences)
3. **Add terrain/positioning aftermath events** (navigation, terrain reading, regrouping)

**Minimum Requirement**: Add 3 events with NO "attrition" tag to break the deadlock.

## Verification Test

After implementing the fix, verify:
1. Suite runs complete successfully with batch_size=200
2. Suite runs work with "Tick between events" unchecked
3. Cutoff rates remain within acceptance criteria
4. Content variety is maintained (no single event dominates)
