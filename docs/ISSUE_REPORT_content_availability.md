# Issue Report: Content Availability in Aftermath Phase

**Date**: 2025-12-22  
**Reporter**: Cline  
**Severity**: Medium (blocks certain test scenarios)  
**Status**: Identified, awaiting GPT design decision

---

## Issue Description

When running the Streamlit harness suite "Presets × (Approach/Engage/Aftermath) × Normal" with 200-event batches, the **aftermath phase** runs out of available content and produces this error:

```
No content entries available after filtering/cooldowns. Broaden tags or add content.
```

## Root Cause

**Insufficient aftermath content in the starter pack** combined with **cooldown exhaustion in long batch runs**.

### Content Availability by Phase

| Preset | Approach | Engage | Aftermath | Status |
|--------|----------|--------|-----------|--------|
| Dungeon | 10 events | 21 events | **5 events** | ⚠️ Marginal |
| City | 12 events | 21 events | **4 events** | ✗ Insufficient |
| Wilderness | 6 events | 12 events | **3 events** | ✗ Insufficient |
| Ruins | 16 events | 29 events | **5 events** | ⚠️ Marginal |

### Why This Breaks

When running 200-event batches:
1. The harness includes ALL tag filters by default (11 tags)
2. With only 3-5 aftermath events available per preset
3. After generating 10-15 events, cooldowns accumulate:
   - Event-level cooldowns (2-4 turns)
   - Tag-level cooldowns (1-3 turns per tag)
4. Eventually, all available events are on cooldown simultaneously
5. No content passes the filter → Error

### Aftermath Content Analysis

**City aftermath** (4 events total):
- hazard_smoke_01
- hazard_fire_01
- social_rival_01
- social_witness_01

**Wilderness aftermath** (3 events total):
- time_ammo_dry_01
- attrition_gear_fail_01
- attrition_fatigue_01

**Dungeon aftermath** (5 events):
- Same as open + hazard_smoke_01 + hazard_water_rise_01

---

## Impact Assessment

### Does NOT affect:
✅ Cutoff tuning implementation (completed successfully)  
✅ Approach and Engage phases (sufficient content)  
✅ Normal gameplay sessions (GMs rarely generate 200 consecutive aftermath events)  
✅ Core engine behavior (filtering logic works correctly)

### Does affect:
❌ Streamlit scenario suite testing for aftermath  
❌ Distribution analysis for aftermath phase  
❌ Cooldown stress testing with small content pools

---

## Proposed Solutions

### Option 1: Content Expansion (Recommended)
**Add 10-15 more aftermath-compatible events** to the core pack.

**Pros:**
- Addresses root cause directly
- Makes aftermath testing robust
- Improves gameplay variety
- Aligns with starter pack goals

**Cons:**
- Requires content design work from GPT
- More work upfront

**Aftermath content suggestions:**
- Witness/consequence events (social_friction, visibility)
- Environmental cleanup/stabilization (hazard aftermath)
- Loot/opportunity discoveries (opportunity, information)
- Injury/fatigue effects (attrition, cost)
- Reinforcement arrivals too late (reinforcements + aftermath)

---

### Option 2: Relax Filtering for Testing
**Modify harness default tags for aftermath runs** to include fewer filters.

**Pros:**
- Quick fix for testing
- No content work needed
- Makes current content stretch further

**Cons:**
- Doesn't fix underlying scarcity
- Different filtering between phases feels inconsistent
- Masks the content gap

**Implementation:**
```python
# In harness, detect aftermath and use broader tags:
if phase == "aftermath":
    include_tags = ["attrition", "hazard", "social_friction", "opportunity"]
else:
    include_tags = [all_tags]  # Full tag set
```

---

### Option 3: Reduce Batch Size for Aftermath
**Run smaller batches (50 events) for aftermath testing.**

**Pros:**
- Immediate workaround
- No code changes
- Still provides distribution data

**Cons:**
- Less statistical confidence
- Doesn't fix the underlying issue
- Manual parameter adjustment needed

---

### Option 4: Conditional Cooldown Relaxation
**Temporarily disable or reduce cooldowns for aftermath in test scenarios.**

**Pros:**
- Allows testing with current content
- Preserves tag filtering

**Cons:**
- Test conditions don't match real usage
- Masks cooldown exhaustion problem
- False sense of sufficiency

---

## Recommendation

**Option 1 (Content Expansion)** is the best long-term solution.

The starter pack should have:
- **Minimum 10 events per environment/phase combination** for core presets
- **Ideally 15-20 events** for robust cooldown handling

Aftermath is thematically rich and deserves more content:
- Consequences manifesting
- Cleanup and recovery
- Discoveries and revelations
- Social/political fallout
- Environmental state changes

---

## Immediate Workaround

For current testing needs, use **Option 3** temporarily:
- Run aftermath with `batch_n = 50` instead of 200
- This provides sufficient data while avoiding cooldown exhaustion
- Continue using 200 for approach/engage phases

---

## Design Question for GPT

**Should aftermath content be expanded now, or deferred?**

If now:
- What aftermath themes should be prioritized?
- Which environments need the most attention?
- Should aftermath events be generally lower severity than engage?

If deferred:
- Which workaround should be documented for users?
- Should the harness detect low-content phases and warn?

---

## Technical Notes

### No Engine Changes Required
The engine is working correctly. This is purely a **content volume issue**.

### Filtering is Correct
The error message is accurate - after cooldowns accumulate, no content genuinely passes all filters.

### Deterministic Behavior Preserved
Results remain fully deterministic with fixed seeds.

---

**Status**: Awaiting GPT design decision  
**Blocking**: Aftermath phase scenario testing  
**Priority**: Medium (doesn't affect core functionality or cutoff tuning task)
