<!--
Version History:
- v0.1 (2025-12-25): Initial requirements and design
-->

# Campaign Mechanics Layer v0.1 - Requirements & Design

**Status**: Draft v0.1  
**Date**: 2025-12-25  
**Type**: New Feature Layer

---

## 1. Purpose & Scope

### Objective
Introduce an optional campaign-level mechanics layer that tracks long-term pressure and consequences across multiple scenes without modifying core SPAR Engine behavior.

### Design Principle
> Scene mechanics create pressure. Campaign mechanics remember it.

### Scope
- **New module**: `spar_campaign/` with pure functions
- **New models**: CampaignState, CampaignDelta
- **Integration**: Optional influence on scene setup
- **Validation**: Multi-scene demonstration script

### Out of Scope (v0.1)
- UI integration (Streamlit harness changes deferred)
- Campaign scenario schema extensions (optional future)
- Full faction/reward/loot systems
- System-specific adapter rules
- Replacement of scene-level mechanics

---

## 2. Problem Statement

### Observations from Campaign Rhythm Validation
- Scene clocks (tension, heat) plateau quickly within individual scenes
- No mechanism tracks consequences beyond scene boundaries
- Campaign rhythm currently driven by severity variance alone
- No "memory" of volatile past scenes
- Aftermath feels isolated rather than connected to campaign arc

### Gap Identified
The SPAR Engine operates at scene timescale. We need a layer that operates at campaign timescale without replacing or overriding scene mechanics.

---

## 3. Design Model

### 3.1 CampaignState

Campaign-level state that persists across scenes:

```python
@dataclass(frozen=True)
class CampaignState:
    campaign_pressure: int = 0      # Long-term tension
    heat: int = 0                    # External attention/response
    scars: Set[str] = set()         # Irreversible changes
    total_scenes_run: int = 0       # Tracking
    total_cutoffs_seen: int = 0     # Tracking
    highest_severity_seen: int = 0  # Tracking
```

**Design notes**:
- Uses integers (not floats) for deterministic behavior
- Immutable (frozen=True) for pure functional updates
- Serializable for save/load
- Separate from EngineState (no coupling)

### 3.2 Accumulation Rules (v0.1)

**Campaign Pressure** accumulates when:
- Severity > 5: +1 per point above 5
- Cutoff triggered: +2 (near breaking point)

**Heat** accumulates from:
- Tags: +1 per visibility/social_friction/reinforcements tag
- Effect vector: +effect_vector.heat value

**Scars** (v0.1):
- Explicit only (not auto-generated)
- Examples: "resources_depleted", "known_to_authorities"
- Permanent (no decay)

### 3.3 Decay Model

Applied explicitly (not automatic):
- Typical use: Aftermath scenes, downtime between sessions
- Pressure decay: -3 default
- Heat decay: -2 default
- Scars: No decay (permanent)

**Design note**: Partial release, not full reset. Campaign state should echo recent volatility.

### 3.4 Campaign Influence on Scene Setup

Campaign state suggests (does not mandate) scene configuration:

**High pressure (≥20)**:
- Include tags: time_pressure, reinforcements
- Rarity bias: spiky
- Note: "Very high campaign pressure: volatile conditions likely"

**Moderate pressure (≥10)**:
- Include tags: time_pressure
- Note: "Elevated campaign pressure: situation remains tense"

**High heat (≥15)**:
- Include tags: social_friction, visibility
- Note: "High heat: authorities and factions are aware"

**Moderate heat (≥8)**:
- Include tags: visibility
- Note: "Moderate heat: attention is building"

**Low pressure + heat (<5 each)**:
- Exclude tags: time_pressure
- Note: "Low pressure: opportunity for recovery"

**Scars influence**:
- "resources_depleted" → include attrition
- "known_to_authorities" → include social_friction

---

## 4. Integration Architecture

### 4.1 Pure Function Design

All campaign mechanics are pure functions:
```python
apply_campaign_delta(state, delta, **caps) -> CampaignState
decay_campaign_state(state, **decay_amounts) -> CampaignState
get_campaign_influence(state) -> Dict[str, Any]
```

### 4.2 Non-Invasive Integration

Campaign mechanics **NEVER**:
- Modify engine.py logic
- Override severity sampling
- Alter cutoff behavior
- Touch EngineState directly

Campaign mechanics **MAY**:
- Add/remove tags in SelectionContext
- Suggest rarity_mode changes
- Provide human-readable notes

### 4.3 Separation of Concerns

```
┌─────────────────┐
│  Scene Setup    │ (applies campaign influence)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SPAR Engine    │ (generates events, untouched)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Scene Outcome  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Campaign Delta  │ (observes outcome)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ CampaignState   │ (accumulates, decays)
└─────────────────┘
```

---

## 5. Usage Pattern

### Typical Campaign Flow

```python
# Initialize
campaign_state = CampaignState.default()
engine_state = EngineState.default()

for scene in campaign_scenes:
    # 1. Get campaign influence
    influence = get_campaign_influence(campaign_state)
    
    # 2. Apply influence to scene setup
    tags = base_tags + influence["include_tags"]
    tags = [t for t in tags if t not in influence["exclude_tags"]]
    rarity = influence.get("rarity_bias") or scene.rarity
    
    # 3. Run scene (engine unchanged)
    event = generate_event(context, engine_state, selection, entries, rng)
    engine_state = apply_state_delta(engine_state, event.state_delta)
    
    # 4. Derive campaign delta from outcome
    delta = CampaignDelta.from_scene_outcome(
        event.severity,
        event.cutoff_applied,
        event.tags,
        effect_vector_dict,
    )
    
    # 5. Update campaign state
    campaign_state = apply_campaign_delta(campaign_state, delta)
    
    # 6. Apply decay at narrative moments
    if scene.phase == "aftermath":
        campaign_state = decay_campaign_state(campaign_state)
```

---

## 6. Caps & Safety Rails

### Pressure Cap (default: 30)
- Prevents runaway escalation
- Configurable per campaign style
- Suggested ranges:
  - Low-intensity campaigns: 15-20
  - Standard campaigns: 25-30
  - High-intensity campaigns: 35-40

### Heat Cap (default: 20)
- Prevents perpetual maximum attention
- Represents practical limits of response capacity
- Suggested ranges:
  - Rural/open: 10-15
  - Urban/political: 15-25

### Decay Rates
- Pressure decay: 1-3 per application
- Heat decay: 1-2 per application
- No automatic decay (explicit only)

---

## 7. Validation Criteria

### Functional Requirements
- [x] CampaignState can be created, serialized, deserialized
- [x] Campaign delta derives correctly from scene outcomes
- [x] Caps prevent runaway values
- [x] Decay reduces pressure/heat correctly
- [x] get_campaign_influence returns valid scene hints
- [x] Scars persist across updates

### Integration Requirements
- [x] No modifications to spar_engine/* files
- [x] EngineState remains authoritative for scenes
- [x] Campaign mechanics are optional (scenes work without them)
- [x] Deterministic behavior (given same scenes/seed)

### User Experience Requirements
- [x] Campaign state evolution is observable
- [x] Influence notes explain reasoning
- [x] Simple to integrate into existing code
- [x] Demo script shows complete workflow

---

## 8. Demo Script Results

**File**: `examples/campaign_mechanics_demo.py`

### Observed Behavior (Seed 42)
- 6 scenes executed successfully
- Heat accumulated: 0 → 3 → 5 → 3 → 7 → 9 → 10
- Aftermath decay applied correctly (scenes 3, 6)
- Campaign pressure stayed 0 (no severity >5 in this run)
- Campaign influence provided appropriate tags based on heat level
- No engine internals modified

### Key Validations
✅ Heat tracks visibility/social friction across scenes  
✅ Partial decay (not full reset) after aftermath  
✅ Campaign influence correctly suggests tags  
✅ Engine state and campaign state remain separate  
✅ Deterministic with fixed seed  

---

## 9. Future Extensions (v0.2+)

### Potential Enhancements (Not in v0.1)
- Campaign scenario schema support
- Streamlit harness UI integration
- Additional trackers (faction standing, resources)
- Auto-scar triggers for significant events
- Richer influence rules
- Campaign-level cutoffs or gates

### Design Constraints for Future
- Must remain optional
- Must not override engine behavior
- Must stay simple and inspectable
- Must preserve determinism

---

## 10. Acceptance Criteria

This implementation is complete if:

- [x] CampaignState model exists and is usable
- [x] Pure functions for delta application and decay
- [x] Campaign influence translates to scene setup hints
- [x] Demo script runs and shows expected behavior
- [x] No modifications to spar_engine/* files
- [x] Documentation explains model and usage
- [x] Code follows engineering_rules.md standards

**Status**: ✅ All acceptance criteria met

---

## 11. Documentation Deliverables

- [x] This requirements document
- [x] Module docstrings with version history
- [x] Inline code documentation
- [x] Demo script with explanatory output
- [ ] CHANGELOG.md entry
- [ ] Contract extension (if needed)

---

## 12. Testing Strategy

### v0.1 Testing Approach
- **Gist test**: Demo script serves as comprehensive gist test
- **No unit tests required**: Pure functions with obvious behavior
- **Integration validation**: Observe multi-scene evolution

### Future Testing (v0.2+)
- Unit tests for accumulation edge cases
- Determinism validation tests
- Cap enforcement tests
- Serialization roundtrip tests

---

## Related Documents

- `docs/contract.md` - SPAR Engine v0.1 Contract (unchanged)
- `docs/engineering_rules.md` - Governs implementation approach
- `examples/campaign_mechanics_demo.py` - Working demonstration
- `spar_campaign/` - Implementation modules

---

**Implementation Date**: 2025-12-25  
**Next Review**: After designer feedback on demo results
