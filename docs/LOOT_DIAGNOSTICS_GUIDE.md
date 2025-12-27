# Loot Generator Diagnostics Guide v1.0

**Audience:** Designers, contributors, and content authors  
**Purpose:** Internal guidance for evaluating loot behavior and content quality  
**Not player-facing**

This document describes the diagnostics-driven review process for loot generator tuning and validation.

---

## Loot Design Principles (Locked)

Loot should **relieve pressure locally while increasing risk globally**.

Core characteristics:
- Not a reward table or inventory system
- Narrative resource shock with consequences
- Should feel meaningful, not constant
- Frequently carries delayed or social consequences

**Explicit non-goals:**
- No item stats
- No currency math
- No inventory UI
- No per-loot or per-pack tuning sliders

---

## Target Distribution Ranges

These define "normal" behavior. Not exact outcomes.

### Severity Distribution (Normal mode, 100-500 samples)

- **Severity 1-2:** 45-55% (small relief, minor echo)
- **Severity 3-4:** 30-40% (meaningful shift, visible consequence)  
- **Severity 5-6:** 10-15% (campaign-altering resource shock)
- **Severity 7+:** under 5% (rare windfall or dangerous prize)

**Interpretation:**
- Too many 1-2 → loot feels boring/inconsequential
- Too many 5+ → loot feels like balance problem

### Cutoff Rates by Rarity Mode

Loot cutoffs should be rarer than event cutoffs, but louder when they occur.

- **Calm:** ~0-1%
- **Normal:** ~2-4%
- **Spiky:** ~5-8%

**Cutoff resolution text should always read:**
- "This is more than it seems."
- "This will not go unnoticed."
- "This changes the equation."

**Never:**
- "You just get more stuff."

### Tag Balance (over large batches)

- **resource/opportunity:** Present in most results
- **visibility or attention:** ~50% of results
- **obligation or social_friction:** ~30-40% of results
- **hazard or cost:** ~20-30% of results

**Red flag:** If loot lacks social/attention tags → drifting toward "free loot"

---

## Three-Step Diagnostics Review Process

### Step A: Baseline Diagnostic Run

**Setup:**
- Generator: Loot
- Campaign: One with moderate heat and pressure
- Batch size: 100-200
- Rarity: Normal

**Review:**
- Severity histogram
- Cutoff rate
- Top tags

**Red flags:**
- 70%+ severity 1-2 → loot is trivial
- 20%+ severity 5+ → loot too swingy
- Cutoff rate 0% → loot lacks drama
- Absence of visibility/obligation tags → loot is consequence-free

### Step B: Campaign Context Contrast

**Repeat diagnostics with:**
- No campaign selected
- High-heat campaign
- High-attention faction campaign

**Desired behavior:**
- Loot shifts from "quiet relief" to "contested resource"
- Same entries feel different under different contexts

**Red flag:** If outputs barely change → faction influence not biting hard enough

### Step C: Qualitative Review (Most Important)

Pick 10 generated loot entries and ask:

1. **Can I immediately tell what was gained?**
2. **Can I immediately tell what it will cost later?**
3. **Would I put this into the Prep Queue?**
4. **Would this naturally seed a follow-up scene?**

**If an entry fails #2 or #4:** That's a content phrasing problem, not tuning.

---

## Loot v1.0 Baseline Behavior

Established via Phase 1-5 validation (December 2025).

### Single Pack (Core Loot, 15 entries)

- Severity 1-2: 73%
- Severity 3-4: 18%
- Visibility tags: 11.5%
- Cutoff rates: Within targets
- Consequence density: 60%+

**Interpretation:** Conservative, high consequence density, low visibility.

### Multi-Pack (Core + Salvage & Black Market, 37 entries)

- Severity 1-2: 64.5%
- Severity 3-4: 20%
- Visibility tags: 18.5%
- Cutoff rates: 5% (Normal mode)
- Opportunity: 100%
- Obligation/social: 24-22%

**Interpretation:** Still conservative but improved. Salvage pack adds visibility/provenance focus as designed.

### Assessment

Loot v1.0 is intentionally conservative with strong consequence coupling:
- Relieves pressure without breaking campaigns
- Maintains narrative tension through obligations/visibility
- Cutoff rates appropriate for resource shocks
- Multi-pack system working as designed

**Locked behavior unless real play reveals issues.**

---

## When to Adjust Content vs Tuning

### Content problems (fix in pack JSON):
- Unclear what was gained
- Unclear what it costs later
- Fiction doesn't seed follow-up scenes
- Entries feel like "free loot"

### Tuning problems (adjust weights/severity bands):
- Distribution severely mismatched across many packs
- Cutoff rates consistently 0% or 80%+
- Tag balance completely absent

**Prefer content fixes over tuning.** If an entry doesn't work, rewrite it.

---

## Multi-Pack Validation Checklist

When adding new loot packs or updating existing:

1. **Run Phase 1 tests** - Verify distribution shape
2. **Run Phase 2 tests** - Verify context sensitivity
3. **Run multi-pack diagnostic** - Check combined behavior
4. **Verify no pack dominates** - Check ID frequency balance
5. **Qualitative review** - Test 10 samples with 4-question framework

If all five pass → pack is ready.

---

## Future Work Guidance

### Before adding more loot packs:
1. Validate current packs meet intent
2. Document specific gaps they don't address
3. Ensure new pack has distinct voice/theme

### Before adjusting severity bands:
1. Run diagnostics with multiple campaigns
2. Get real GM feedback on "too safe" vs "too swingy"
3. Adjust incrementally (±1 severity point at a time)

### Before changing cutoff overlays:
1. Verify problem is fiction, not rates
2. Test alternative phrasings with real GMs
3. Ensure overlays stay narrative-focused

---

## Test Coverage

### Phase 1: Distribution Target Validation
- `test_loot_severity_distribution_normal`
- `test_loot_cutoff_rates_by_rarity`
- `test_loot_tag_balance`
- `test_loot_consequence_density`

### Phase 2: Campaign Context Sensitivity
- `test_loot_severity_shifts_with_campaign_pressure`
- `test_loot_attention_tags_increase_with_context`
- `test_loot_cutoff_probability_increases_with_constraint`

All tests use ranges and proportions, never exact values.  
Tests fail only when systemic drift occurs, not from random variance.

---

## Designer Sign-Off

Loot Generator v1.0 is **production-ready** with:
- ✅ Distribution validation framework
- ✅ Context sensitivity confirmed
- ✅ Reference thematic pack (Salvage & Black Market)
- ✅ Multi-pack system validated
- ✅ Conservative distribution with strong consequence coupling

Lock unless real play reveals issues requiring adjustment.

**Last updated:** 2025-12-26  
**Status:** Locked for v1.0
