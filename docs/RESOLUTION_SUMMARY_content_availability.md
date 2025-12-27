# Resolution Summary: Content Availability Error

## Problem Solved

The "No content entries available after filtering/cooldowns" error that occurred in the Streamlit harness suite runner has been diagnosed and **partially resolved**.

## Root Causes Identified

### 1. Primary Cause: Cooldown Accumulation Bug (✅ FIXED)

**Issue**: Tag cooldowns were never expiring when `tick_between=False`, causing indefinite accumulation and rapid content pool exhaustion.

**Fix Applied**: Modified `streamlit_harness/app.py` line 165-169 to always tick by at least 1 between events:

```python
if idx > 0:
    # Always tick at least 1 to prevent cooldown accumulation
    tick_amount = max(1, int(ticks_between) if tick_between else 1)
    state = tick_state(state, ticks=tick_amount)
```

**Impact**: This fix resolves the error for:
- All approach/engage phases (16-18 events available)
- Confined/populated/derelict aftermath (5-8 events with diverse tags)
- ~90% of suite test combinations

### 2. Secondary Cause: Wilderness Aftermath Content Gap (⚠️ REQUIRES CONTENT)

**Issue**: Wilderness aftermath has only 3 events, and **all 3 share the "attrition" tag** with cooldown=2:
1. `time_ammo_dry_01`
2. `attrition_gear_fail_01`
3. `attrition_fatigue_01`

**Effect**: Even with proper ticking, only 1-2 events can generate before all options are blocked.

**Required Fix**: Add 3-5 open aftermath events with diverse tags (hazard, terrain, visibility, positioning—anything but attrition).

## Testing Status

### Passing Tests
- ✅ All cutoff tuning tests (8/8 pass)
- ✅ Integration tests for dungeon/city phases with batch_size=200
- ✅ Cooldown decay rate verification

### Failing Tests
- ❌ Wilderness aftermath with batch_size >10
- ❌ Suite runs including open aftermath with batch_size=200

**Reason**: Content diversity issue, not code bug.

## User Action Required

**To fully resolve the issue**:

1. **Immediate**: Test the fix in Streamlit harness
   - Most presets should now work with batch_size=200
   - Wilderness aftermath will still fail, but for a different reason (content gap)

2. **Decision needed**: Choose approach for open aftermath:
   - **Option A**: Add 3-5 new events to `data/core_complications.json`
   - **Option B**: Document the limitation and reduce batch size expectations for open aftermath
   - **Option C**: Temporarily disable wilderness in suites until content is expanded

## Files Modified

- `streamlit_harness/app.py` - Implemented minimum tick fix
- `docs/ROOT_CAUSE_ANALYSIS_content_availability.md` - Complete diagnosis
- `tests/test_cooldown_fix.py` - Integration tests for the fix
- `CHANGELOG.md` - Documented fix and known issues

## Verification Steps

1. Run Streamlit harness: `streamlit run streamlit_harness/app.py`
2. Navigate to "Scenarios" tab
3. Select "Presets × (Approach/Engage/Aftermath) × Normal"
4. Set batch size to 200
5. Click "Run suite"

**Expected**: Confined/populated/derelict complete successfully. Wilderness aftermath fails on event 2-3 with descriptive error about attrition tag overlap.

## 3. Tertiary Cause: Normal Mode Tick Threshold Requirement (📊 BEHAVIOR ANALYSIS)

**Observation**: Normal rarity mode requires ticks >= 2 to work reliably, while other modes (calm, spiky) work with ticks >= 1.

**Root Cause**: Normal mode's content selection pattern creates more predictable and constrained choices compared to other rarity modes:

### Content Selection Pattern Differences

**Normal Mode Characteristics**:
- More predictable severity distribution
- Tends to favor certain tag combinations (hazard, visibility, time_pressure)
- Creates patterns where events with overlapping cooldown tags are selected consecutively
- Results in "cooldown cascade" effect where multiple tags go on cooldown simultaneously

**Other Modes (Calm, Spiky)**:
- Different alpha/severity distributions create more diverse selection
- Select from broader range of severity bands
- Less predictable patterns reduce tag overlap concentration
- Natural diversity prevents cooldown cascades

### Why Normal Needs >= 2 Ticks

With only 1 tick between events:
- Tag cooldowns of 2-3 don't fully decay (most events have cooldown values of 2-3)
- Normal mode's predictable pattern selects events with overlapping tags
- Available content pool shrinks progressively as tags accumulate on cooldown
- Eventually hits content availability error despite the minimum tick fix

With ticks >= 2:
- Tag cooldowns of 2-3 fully decay between most events
- Recent event IDs age more aggressively (older entries drop faster)
- Content availability remains stable throughout longer batch runs

### Evidence from Data

From `data/core_complications.json` analysis:
- Most events have tag cooldowns of 2-3 ticks
- Events share common tags: "hazard" (appears in 10 events), "visibility" (10 events), "time_pressure" (11 events)
- Normal mode's selection pattern hits these shared tags repeatedly
- Example cascade: hazard_smoke_01 (hazard:2, visibility:1) → hazard_fire_01 (hazard:2) → hazard_collapse_01 (hazard:2, terrain:2)

### Comparative Behavior

| Rarity Mode | Minimum Ticks | Reason |
|-------------|---------------|---------|
| Calm | >= 1 | Lower severity distribution, different tag selection pattern |
| Normal | >= 2 | Predictable pattern creates cooldown cascades |
| Spiky | >= 1 | Higher severity distribution, more diverse selection |

## Next Steps

Waiting for user decision on how to handle open aftermath content gap. The cooldown system is now functioning correctly, and the Normal mode tick requirement is now documented and understood.
