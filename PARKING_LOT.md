# SPAR Tool Parking Lot

A running list of deferred ideas and improvements.

## Engine (Deferred)

- **State aging for `recent_event_ids`**: add tick-based eviction/aging policy (distinct from the bounded list). Consider a per-ID TTL or decay by tick/scene.
- **Pack versioning + pack metadata header**: support pack-level metadata (schema version, pack id, pack version, author, tags, notes) and enforce schema validation on load.

## Streamlit Harness - JSON Scenario System (Deferred)

- **Directory browser UI**: Visual directory/file selection widget for scenario result output paths (currently text input only)
- **Sea preset support**: Add "sea" environment to preset options and scene_preset_values() function
- **Full JSON schema validation**: Validate field types, value ranges, and enum constraints (currently only validates required fields exist)
- **Scenario editor**: In-app JSON editing and creation interface for building scenarios without external editor
- **Scenario comparison**: Side-by-side result comparison UI for analyzing multiple scenario runs

## Campaign Mechanics Layer - Future Enhancements (v0.3+)

**Status**: v0.2 COMPLETE (see `spar_campaign/` module and Campaign Manager UI)

Campaign Mechanics v0.1 + v0.2 successfully implement:
- ✅ Campaign pressure and heat tracking
- ✅ Scene outcome observation
- ✅ Non-invasive scene setup influence
- ✅ Explicit decay mechanics
- ✅ Structured scars (category, severity, source, notes)
- ✅ Faction tracking (attention + disposition)
- ✅ Long-arc bands (descriptive state tiers)
- ✅ Multi-campaign UI with dashboard
- ✅ Session finalization wizard
- ✅ Content sources metadata tracking

Potential future enhancements (v0.3+):
- **Auto-scar triggers**: Automatic scar generation from significant events
- **Disposition auto-adjustment**: Context-aware faction disposition changes
- **Resource depletion mechanics**: Campaign-scale supply tracking with game effects
- **Richer influence rules**: More sophisticated scene setup hints
- **Scenario schema integration**: CampaignState in JSON scenario format
- **Campaign-level cutoffs**: Optional hard gates based on campaign state
- **Scar remediation**: Mechanics for resolving/healing scars
- **Faction AI/actions**: Active faction responses (not just tracking)

**Design Intent**: All future work must preserve optional nature, pure functional design, and engine separation.

## Source List Import & Parsing (External Content Feeds) - Partially Complete

**Status**: Metadata tracking COMPLETE, parsing/import still deferred

**What's implemented (Campaign UX v0.1)**:
- ✅ Source metadata model (name, path, enabled, type)
- ✅ UI for adding/toggling sources
- ✅ Active sources displayed in campaign header
- ✅ Active sources recorded in ledger metadata
- ✅ Per-campaign source management

**What remains deferred (future work)**:
- **Content parsing**: Read external files (CSV, spreadsheet, JSON)
- **Content mapping**: Transform external format → SPAR content schema
- **Tag normalization**: Validate and clean external tags
- **Validation layer**: Prevent low-quality imports
- **Live import UI**: Parse and preview before accepting
- **Community pipeline**: Submission and curation workflow

**Design considerations for parsing (future):**
- Clear separation between canonical packs and imported sources
- Strong tag hygiene and validation
- Selective enable/disable (already implemented at metadata level)
- Preview and approve workflow (not auto-import)

**Next step**: Implement parser for one format (e.g., CSV) as proof of concept

---

## Campaign History Import - Phase 3 UI Controls (In Progress)

**Status**: Parser integration COMPLETE, UI controls deferred

**Completed (Phase 2 + Foundation)**:
- ✅ markdown-it-py token parsing (handles heading variants)
- ✅ dateparser date normalization
- ✅ rapidfuzz fuzzy deduplication
- ✅ ImportOverrides data model
- ✅ Parser accepts campaign_id and applies overrides
- ✅ All tests passing (10/10 + 88/88)

**Remaining UI Work** (Phase 3):
Inline promote/demote controls in Parse Preview (no subdialogs):
- Add Promote▲ buttons for places/artifacts/concepts
- Add Demote▼ buttons for factions  
- Add Remove✕ buttons for all entities
- Controls update parsed data immediately
- Changes save to ImportOverrides on action

**Implementation locations**:
- Flow D: render_campaign_selector() "show_history_import" section
- Flow C: render_campaign_dashboard() "show_dashboard_history_import" section

**Estimated**: ~40-50 small UI additions per requirements

---

## Loot Generator & Generators Framework (Future Architecture)

**Status**: Deferred - foundational work for multi-generator system

### A) Loot Generator Feature

A future Loot Generator should parallel the Event Generator architecture with campaign integration:

**Core requirements**:
- **Campaign context integration**: Pull faction/scar/pressure context like Event Generator
- **Prep queue push**: Send generated loot to campaign prep queue (non-canon staging)
- **Sources support**: Built-in loot tables + external sources (CSV, spreadsheet)
- **Deterministic generation**: Seed-based RNG for reproducible results
- **Campaign mechanics advisory**: Faction attention and scars influence suggestions only (no direct modification)

**Design principles**:
- Same workflow as Event Generator: Generate → Curate → Stage (Prep) → Commit (Canon)
- Preserve separation: generator outputs suggestions, campaign commits changes
- Use ContextBundle for campaign state access (read-only)

### B) General Generators Framework

**Foundation**: All generators (Events, Loot, Rumors, NPC hooks, etc.) must share a common architecture based on the "Self-organized-criticality-in-fragmenting" (SOC) paper foundation (see `docs/Self-organized-criticality-in-fragmenting.pdf`).

**Shared architecture components**:

1. **Distribution mechanics** (SOC foundation):
   - Heavy-tail distributions with finite-size cutoffs
   - Morphology/constraints as tuning knobs (confinement, connectivity, visibility)
   - Clear safety rails and truncation logic
   - Severity bands and adaptive weighting

2. **State management**:
   - Shared EngineState model (cooldowns, clocks, recent_ids)
   - Deterministic state evolution
   - Explicit tick mechanics

3. **Content filtering**:
   - Tag-based inclusion/exclusion
   - Rarity mode support (calm/normal/spiky)
   - Source pack enable/disable
   - Faction/scar context filtering

4. **RNG and reproducibility**:
   - TraceRNG for deterministic generation
   - Seed-based batch generation
   - Clear separation: seed → distribution → selection → output

5. **Campaign context integration**:
   - ContextBundle for read-only campaign state access
   - Advisory influence only (no direct state modification)
   - Prep queue push for non-canon staging

6. **Export formats**:
   - JSON for machine processing
   - Markdown for human reading
   - Deterministic output ordering

**Design goals**:
- Avoid code duplication across generators
- Simplify testing and maintenance
- Preserve SOC mathematical foundation
- Enable extensibility for new generator types

### C) Testing and Maintainability

**Shared test infrastructure**:
- One suite for distribution sanity tests across all generators
- Verify heavy-tail properties, cutoff behavior, severity bands
- Reusable scenario validation framework

**Content pack schema evolution**:
- Type tags to distinguish content: `event`, `loot`, `rumor`, `npc_hook`
- Shared tag vocabulary and normalization rules
- Support mixed-type packs or specialized packs

**UI pattern consistency**:
- All generators follow: Generate → Curate → Stage (Prep) → Commit (Canon)
- Shared widgets: batch size, seed, tick controls, campaign context selector
- Consistent Prep Queue integration
- Reusable export utilities

**Implementation strategy** (when unparked):
1. Extract common base classes from Event Generator
2. Refactor existing code to use shared framework
3. Implement Loot Generator as second reference implementation
4. Validate framework supports third generator type
5. Document framework patterns and extension points

**References**:
- SOC paper: `docs/Self-organized-criticality-in-fragmenting.pdf`
- Existing Event Generator: `spar_engine/engine.py`, `streamlit_harness/app.py`
- Campaign context: `streamlit_harness/campaign_context.py`

---

## SPAR ↔ D&D Adapter Formalization (Explicitly Deferred)

**Status**: Parked pending content richness and campaign mechanics validation

Integration and publication-facing work:
- **Mechanical mappings**: How SPAR outputs map to D&D complications
- **DC/Damage translation**: SPAR severity → D&D difficulty/damage
- **System-specific consequences**: SPAR state → D&D mechanical effects
- **Adapter documentation**: Usage examples and integration guides
- **SPAR mechanics formalization**: Reverse mapping (D&D → SPAR inputs)

**Design Intent**: Requires stable content library and optional campaign layer before formalization makes sense.
