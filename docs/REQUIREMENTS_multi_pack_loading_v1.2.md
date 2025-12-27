# Multi-Pack Content Loading v1.2 - Requirements

**Date**: 2025-12-26  
**Status**: Design Phase  
**Goal**: Enable multiple content packs to be active simultaneously

## Objective

Support thematic content packs and future Loot Generator by implementing the existing but unused `SelectionContext.enabled_packs` field for true multi-pack loading.

## Background

**Current State:**
- `SelectionContext.enabled_packs: List[str]` field exists but is unused
- All code uses single pack: `["core_complications"]`
- Content loading via `load_pack(path)` loads one JSON file
- 18 references across codebase hardcode single pack names

**Why Now:**
- Phase 1 content expansion complete (107 entries)
- Default pack is now production-grade, reusable backbone
- Thematic packs will be additive, not corrective
- Loot Generator will need same multi-pack infrastructure

## Design Philosophy

### Rule: Union, Not Weighting (v1.x)

**Approach**: Multiple packs combine into single merged pool
- All entries treated equally by SOC distribution
- No per-pack weighting or priority
- Simple, predictable, debuggable

**Why Union:**
- Preserves existing SOC math
- Avoids weighting complexity
- Makes pack interactions transparent
- Easier to reason about content availability

**Future**: Pack weighting could be v2.0 feature if needed

### Rule: Campaign-Level Selection (Primary)

**Control Point**: Pack selection happens at campaign level
- Campaign dashboard gets pack toggles (like content sources)
- Per-run overrides available but not primary workflow
- "Choose voices you want active; engine does the rest"

**Why Campaign-Level:**
- Matches existing content sources model
- Pack selection is campaign identity, not per-session
- Reduces cognitive load in Event Generator
- Natural integration point

### Rule: No New Generator Knobs

**UI Principle**: Pack management stays out of Event Generator UI
- Generator sidebar shows which packs are active
- No per-run pack selection controls
- Context strip shows active pack names
- Advanced Settings could allow one-time override

**Why:**
- Avoids UI complexity creep
- Maintains v1.0 UX simplicity
- Pack choice is strategic, not tactical

## Technical Design

### 1. Content Loading

**New Function**: `load_packs(paths: List[str | Path]) -> List[ContentEntry]`

```python
def load_packs(paths: List[str | Path]) -> List[ContentEntry]:
    """Load and merge multiple content packs into union pool."""
    all_entries = []
    for path in paths:
        entries = load_pack(path)
        all_entries.extend(entries)
    return all_entries
```

**Deduplication**: If same event_id appears in multiple packs, last one wins (explicit override)

**Validation**: All packs must use same schema version

### 2. Pack Registry

**Location**: `data/packs/` directory structure

```
data/
├── core_complications.json (always available)
├── packs/
│   ├── urban_intrigue.json
│   ├── frontier_survival.json
│   ├── loot_situations.json (future)
│   └── campaign_spelljammer.json (future, campaign-specific)
```

**Metadata**: Each pack includes header:
```json
{
  "$schema": "spar_content_pack_v1.0",
  "pack_id": "urban_intrigue",
  "pack_name": "Urban Intrigue",
  "version": "1.0",
  "description": "Power, witnesses, institutions, leverage",
  "tags_emphasized": ["visibility", "social_friction", "obligation"],
  "entries": [...]
}
```

### 3. Campaign Integration

**Campaign Model Extension**:
```python
@dataclass
class Campaign:
    # existing fields...
    enabled_content_packs: List[str] = field(default_factory=lambda: ["core_complications"])
```

**UI Integration**:
- Dashboard "Content Packs" section (alongside Sources)
- Toggle switches for available packs
- Core pack always enabled (cannot disable)
- Show active pack count in generator context strip

### 4. Generator Integration

**Current**:
```python
selection = SelectionContext(
    enabled_packs=["core_complications_v0_1"],  # hardcoded
    include_tags=tags,
    ...
)
```

**New**:
```python
# Get from campaign context
active_packs = campaign.enabled_content_packs if campaign else ["core_complications"]

selection = SelectionContext(
    enabled_packs=active_packs,
    include_tags=tags,
    ...
)
```

**Entry Loading**: Engine loads union of all enabled packs before filtering

### 5. Guardrails

**Max Active Packs**: 3-4 packs maximum
- Prevents content bloat
- Maintains debuggability
- Forces curation decisions

**Provenance Display**:
- Generator context strip shows: "Active: Core + Urban Intrigue"
- Diagnostics show entry count per pack
- Session exports note which packs were active

**Validation Rules**:
- All packs must have unique pack_id
- Schema version must match across packs
- No duplicate event_ids within union (warning, last wins)
- Core pack always required

## User Experience

### Campaign Manager Flow

1. **Dashboard → Content Packs Section**
   - Shows available packs (from data/packs/)
   - Toggle switches (Core always on, grayed)
   - Live preview of total entries

2. **Pack Selection**
   - Click toggle to enable/disable
   - Save campaign to persist
   - Generator automatically uses new union

3. **Generator Context Strip**
   - Shows "Core Complications + Urban Intrigue (143 entries)"
   - Subtle, non-intrusive

### Event Generator Flow

**No Changes** - packs are transparent:
- Generator uses whatever packs campaign has enabled
- No new controls or decisions
- Works exactly like v1.0

## Implementation Sequence

### Phase 1: Core Infrastructure (Small, Safe)
1. Implement `load_packs()` function
2. Update engine to use enabled_packs properly
3. Add pack validation
4. Test with multiple instances of core pack (smoke test)

### Phase 2: Campaign Integration (Medium)
1. Add enabled_content_packs field to Campaign model
2. Add Content Packs section to campaign dashboard
3. Update generator to pull from campaign.enabled_content_packs
4. Update context strip to show active packs

### Phase 3: First Thematic Packs (Content)
1. Create Urban Intrigue pack (~20 entries)
2. Create Frontier Survival pack (~20 entries)
3. Test multi-pack loading with real thematic content

### Phase 4: Loot Generator Foundation
- Loot pack becomes another content type
- Uses same multi-pack infrastructure
- No special handling needed

## Success Criteria

- [ ] Multiple packs can be loaded and merged
- [ ] Campaign can enable/disable packs via UI
- [ ] Generator respects campaign pack selection
- [ ] No duplicate event_id conflicts
- [ ] Context strip shows active packs
- [ ] All existing tests pass
- [ ] No regression in v1.0 functionality

## Migration Path

**Backward Compatibility**:
- Existing campaigns default to `["core_complications"]`
- All hardcoded single-pack references updated
- Tests continue using core pack only
- No breaking changes to engine API

## Benefits

✓ Prepares infrastructure for Loot Generator  
✓ Enables thematic campaign voices  
✓ Leverages Phase 1 content density work  
✓ Small surface change with immediate payoff  
✓ No new UX complexity in generator  

## Next Steps

1. Implement core infrastructure (Phase 1)
2. Test with synthetic multi-pack scenarios
3. Add campaign UI integration (Phase 2)
4. Create first thematic pack (Phase 3)

**Recommendation**: Start with Phase 1 infrastructure before writing thematic pack content.
