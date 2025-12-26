# Campaign Integration Architecture v0.1

**Last Updated**: 2025-12-25  
**Status**: Active  
**Campaign Version**: v0.2  
**Integration Flows**: A, B, C, D (Complete)

## Overview

This document describes the technical architecture of Campaign integration with SPAR Tool Engine. It covers data models, flow patterns, persistence, and design decisions.

## System Components

### Core Campaign Module (`spar_campaign/`)

**Purpose**: Pure functional campaign state management, isolated from UI/persistence.

**Files:**
- `models.py` - Immutable dataclasses (CampaignState, Scar, FactionState, Band, SessionRecord, CampaignDelta)
- `campaign.py` - Pure functions (apply_campaign_delta, decay_campaign_state, get_campaign_influence)
- `__init__.py` - Package exports

**Design Principles:**
- Immutable data structures (frozen dataclasses)
- No side effects (pure functions)
- No I/O dependencies
- Type-safe with full annotations
- Unit testable in isolation

### Integration Layer (`streamlit_harness/`)

**Purpose**: Bridge campaign state ↔ event generator ↔ UI

**Files:**
- `campaign_context.py` - ContextBundle computation and session state management
- `session_packet.py` - SessionPacket derivation from generator results
- `history_parser.py` - Heuristic parsing of narrative text → structured data
- `campaign_ui.py` - Streamlit UI components
- `app.py` - Main application with mode toggle and context strip

**Design Principles:**
- Advisory pattern (suggests, never enforces)
- Clear separation: computation vs. UI vs. persistence
- Defensive validation at boundaries
- Graceful degradation on errors

## Data Models

### CampaignState (v0.2)

Core campaign state representation:

```python
@dataclass(frozen=True)
class CampaignState:
    pressure: float           # 0-10, long-term problem accumulation
    heat: float              # 0-10, immediate attention/pursuit
    active_scars: List[Scar] # Structured lasting conditions
    factions: Dict[str, FactionState]  # Known factions and dispositions
    bands: Dict[str, Band]   # Long-arc narrative threads
    content_sources: List[str]  # Available complication pools
    session_history: List[SessionRecord]  # Ledger of past sessions
    canon_summary: List[str]  # Key narrative events
    created_at: datetime
    last_updated: datetime
```

**Key Properties:**
- `pressure`: Decays slowly (0.3/session), represents unresolved problems
- `heat`: Decays faster (0.8/session), represents immediate danger
- Both clamped to [0, 10] range
- Immutable - updates return new instance

### Scar (Structured Injuries)

```python
@dataclass(frozen=True)
class Scar:
    effect: str      # Description of mechanical impact
    severity: int    # 1-5, severity level
    gained_in_session: int  # Session number when acquired
```

**Severity Bands:**
- 1-2: Minor hindrances
- 3: Significant limitations
- 4-5: Major debilitations

**Design Note**: Scars are campaign-wide, not PC-specific, allowing flexibility in narrative application.

### FactionState

```python
@dataclass(frozen=True)
class FactionState:
    name: str
    disposition: int  # -5 (hostile) to +5 (allied), 0 = neutral
```

**Disposition Scale:**
- -5 to -3: Openly hostile
- -2 to -1: Unfriendly
- 0: Neutral
- +1 to +2: Friendly
- +3 to +5: Allied

### Band (Long-Arc Threads)

```python
@dataclass(frozen=True)
class Band:
    band_id: str      # e.g., "SHADOW_OPS"
    intensity: float  # 0-10, how active this thread is
    last_activated: int  # Session number
```

**Supported Bands:**
- SHADOW_OPS: Covert operations, surveillance
- NETWORK_DECAY: Infrastructure failure
- FALLOUT_SPIRAL: Cascading consequences
- RESOURCE_CRUNCH: Scarcity pressures
- FACTION_WAR: Multi-group conflicts

### CampaignDelta

Advisory change recommendations:

```python
@dataclass(frozen=True)
class CampaignDelta:
    pressure_change: float
    heat_change: float
    new_scars: List[Scar]
    faction_changes: Dict[str, int]  # faction_name -> disposition delta
    band_triggers: Dict[str, float]  # band_id -> intensity delta
    new_canon_bullets: List[str]
    rationale: str  # Why these changes are suggested
```

**Usage Pattern:**
1. Generate complications with campaign context
2. Derive SessionPacket from run results
3. User reviews and edits suggested changes
4. Apply delta to create new campaign state

## Data Flows

### Flow A: Context → Generator

**Purpose**: Campaign state influences event generation

```
CampaignState → ContextBundle → GeneratorDefaults → ComplicationSelection
```

**Steps:**
1. User selects campaign and clicks "Apply Context to Generator"
2. `compute_context_bundle(state)` derives influence values:
   - Severity weights from pressure bands
   - Recent complication IDs for cooldown checking
   - Active scars for thematic influence
3. ContextBundle stored in session state
4. User switches to Generator tab
5. Generator reads context from session state
6. Severity weights adjust selection probabilities
7. Cooldowns prevent immediate repetition
8. Generated complications are cached in session

**Key Design Decision**: Advisory pattern - context suggests weights but never hard-filters. Generator remains valid without context.

### Flow B: Session Finalization

**Purpose**: Generator results → Campaign ledger

```
GeneratedComplications → SessionPacket → UserEdits → CampaignDelta → NewCampaignState
```

**Steps:**
1. User clicks "Finalize This Session" after generating
2. `SessionPacket.from_run_result(result, state)` derives suggestions:
   - Pressure delta from severity distribution
   - Heat delta from time-pressure complications
   - Scar suggestions from severity 4-5 outcomes
   - Faction updates from organizational themes
3. Wizard presents suggestions for user review/edit
4. User provides: canon bullets, scar edits, faction adjustments
5. `apply_campaign_delta(state, delta)` creates new state:
   - Updates pressure/heat (clamped)
   - Adds scars to active list
   - Updates faction dispositions
   - Appends session to ledger
6. New state persisted to disk
7. UI returns to dashboard with updated stats

**Key Design Decision**: Three-step wizard (review → edit → confirm) ensures user control. Nothing auto-commits.

### Flow C: Import to Existing Campaign

**Purpose**: Add historical narrative → existing ledger

```
HistoryText → Parser → StructuredSessions → MergeWithExisting → UpdatedState
```

**Steps:**
1. User clicks "Import" on dashboard
2. Pastes narrative text into text area
3. `parse_campaign_history(text)` heuristically extracts:
   - `detect_dates()`: Finds date patterns (ISO, natural language)
   - `split_into_sessions()`: Chunks by date boundaries
   - `extract_canon_summary()`: Bullet points, significant events
   - `extract_factions()`: @ mentions, org names, proper nouns
4. Preview shows detected structure
5. User confirms merge
6. New sessions appended to ledger
7. Canon bullets appended to summary
8. Factions added (if new) or ignored (if existing)
9. Pressure/heat unchanged (history is informational)

**Key Design Decision**: Non-destructive merge. Existing state preserved, only additive operations.

### Flow D: Import to New Campaign

**Purpose**: Historical narrative → campaign creation

```
HistoryText → Parser → StructuredSessions → NewCampaignState
```

**Steps:**
1. User clicks "Import Campaign History" on landing
2. Enters campaign name
3. Pastes narrative text
4. Parser extracts sessions, canon, factions (same as Flow C)
5. Preview shows what will be created
6. User confirms
7. Create new CampaignState with:
   - Parsed sessions in ledger
   - Canon summary populated
   - Factions initialized at neutral (0)
   - Pressure/heat at defaults (0)
   - Default content sources
8. Persist and display dashboard

**Key Design Decision**: Clean slate initialization. Parser provides structure, user provides meaning through later finalization.

## Persistence Layer

### File Format

Campaigns stored as JSON in `campaigns/` directory:

```
campaigns/
  the-wasteland-run.json
  urban-decay-arc.json
  ...
```

**Filename Convention**: Lowercase campaign name with hyphens, `.json` extension.

### JSON Schema

Direct serialization of CampaignState dataclass:

```json
{
  "pressure": 3.2,
  "heat": 1.5,
  "active_scars": [
    {
      "effect": "Broken rib - difficulty breathing",
      "severity": 3,
      "gained_in_session": 2
    }
  ],
  "factions": {
    "Raiders": {
      "name": "Raiders",
      "disposition": -2
    }
  },
  "bands": {
    "SHADOW_OPS": {
      "band_id": "SHADOW_OPS",
      "intensity": 4.5,
      "last_activated": 3
    }
  },
  "content_sources": ["core_complications.json"],
  "session_history": [...],
  "canon_summary": [...],
  "created_at": "2025-12-20T14:30:00",
  "last_updated": "2025-12-22T19:45:00"
}
```

**Serialization:**
- dataclasses → dict via `dataclasses.asdict()`
- datetime → ISO string via `.isoformat()`
- Deserialization reverses with validation

### Auto-Save Strategy

**Current Behavior:**
- Manual save on user actions (create, finalize, import)
- No automatic periodic saves
- Single file per campaign (no history/undo)

**Future Consideration**: Versioned saves with rollback capability.

## Context Bundle Computation

### Purpose

Translate CampaignState → read-only influence object for generator.

### Implementation

```python
def compute_context_bundle(state: CampaignState) -> ContextBundle:
    # Severity weights from pressure
    weights = calculate_severity_weights(state.pressure)
    
    # Recent complications for cooldown
    recent = extract_recent_complications(state.session_history, n=3)
    
    # Structured influence data
    return ContextBundle(
        pressure=state.pressure,
        heat=state.heat,
        severity_weights=weights,
        recent_complication_ids=recent,
        active_scars=[s.effect for s in state.active_scars],
        faction_dispositions={f.name: f.disposition for f in state.factions.values()},
        active_bands={b.band_id: b.intensity for b in state.bands.values()}
    )
```

### Severity Weighting

Pressure bands influence severity distribution:

```python
if pressure < 3:
    # Low pressure: favor lower severity
    weights = {1: 0.35, 2: 0.30, 3: 0.20, 4: 0.10, 5: 0.05}
elif pressure < 6:
    # Medium pressure: balanced distribution
    weights = {1: 0.20, 2: 0.25, 3: 0.25, 4: 0.20, 5: 0.10}
else:
    # High pressure: favor higher severity
    weights = {1: 0.05, 2: 0.10, 3: 0.25, 4: 0.35, 5: 0.25}
```

**Design Note**: Weights are suggestions. Generator applies them probabilistically but never hard-filters.

## Session Packet Derivation

### Purpose

Translate generator results → advisory campaign updates.

### Heuristic Rules

```python
def from_run_result(result: RunResult, state: CampaignState) -> SessionPacket:
    # Analyze generated complications
    severities = [c.severity for c in result.complications]
    has_time_pressure = any("time_pressure" in c.tags for c in result.complications)
    high_severity_count = sum(1 for s in severities if s >= 4)
    
    # Suggest pressure delta
    pressure_delta = 0.5 * len(severities) + 1.0 * high_severity_count
    
    # Suggest heat delta
    heat_delta = 2.0 if has_time_pressure else 0.5
    
    # Suggest scars from severity 4-5 outcomes
    suggested_scars = ["Consider scar" for s in severities if s >= 4]
    
    # Suggest faction updates from themes
    faction_suggestions = detect_faction_references(result.complications)
    
    return SessionPacket(
        complications=result.complications,
        suggested_pressure_delta=pressure_delta,
        suggested_heat_delta=heat_delta,
        suggested_new_scars=suggested_scars,
        suggested_faction_changes=faction_suggestions,
        rationale="Auto-derived from complication analysis"
    )
```

**Key Design Decision**: Heuristics provide starting point. User always has final say.

## History Parser

### Purpose

Extract structured data from free-form narrative text.

### Detection Strategies

#### Date Detection (`detect_dates`)

Patterns recognized:
- ISO format: `2025-12-20`
- Natural: `December 20, 2025`
- Informal: `Dec 20`, `12/20/25`
- Relative: `Session 1`, `Day 3`

**Algorithm:**
1. Regex scan for date patterns
2. Extract (date_string, line_index) pairs
3. Sort chronologically
4. Return session boundary markers

#### Session Splitting (`split_into_sessions`)

**Algorithm:**
1. Use date markers as boundaries
2. Chunk text between dates
3. Assign content to sessions
4. Return list of (date, content) tuples

**Edge Cases:**
- No dates → single session with generic timestamp
- Multiple dates close together → separate sessions
- Malformed dates → skip, use surrounding context

#### Canon Extraction (`extract_canon_summary`)

**Heuristics:**
1. Look for bullet points (-, *, •)
2. Identify "significant event" markers (survived, lost, discovered)
3. Filter out meta-commentary ("we should", "players decided")
4. Return cleaned bullet list

**False Positive Prevention:**
- Skip lines with "?", "maybe", "could"
- Ignore OOC markers ((parens)), [[brackets]]
- Focus on declarative statements

#### Faction Extraction (`extract_factions`)

**Heuristics:**
1. @ mentions: `@Raiders`, `@Enclave`
2. Capitalized proper nouns followed by org markers: `Steel Brotherhood`, `Trade Guild`
3. Common faction keywords: "gang", "faction", "group", "syndicate"
4. Filter out player names (cross-reference with session context)

**Initialization:**
- All factions start at disposition 0 (neutral)
- User adjusts dispositions during play

### Parser Limitations

**Known Issues:**
- Date ambiguity (US vs. EU formats)
- False positives on capitalized names
- Cannot infer dispositions from text tone
- Misses subtle narrative threads

**Mitigation:**
- Preview step before committing
- User can edit parsed results
- Parser is advisory, not authoritative

## UI Session State Management

### Streamlit Session State Keys

```python
# Campaign selection and context
st.session_state["selected_campaign"]       # str | None
st.session_state["campaign_context_active"] # bool
st.session_state["active_context_bundle"]   # ContextBundle | None

# Generator integration
st.session_state["generated_complications"] # List[Complication]
st.session_state["run_result_cache"]       # RunResult | None

# Finalize wizard
st.session_state["finalize_step"]          # int (1-3)
st.session_state["session_packet"]         # SessionPacket | None

# History import
st.session_state["import_mode"]            # "existing" | "new" | None
st.session_state["parsed_history"]         # ParsedHistory | None
```

### State Transitions

**Activating Context:**
```
Dashboard → "Apply Context" → context_active=True → Navigate to Generator
```

**Clearing Context:**
```
Generator → "Clear Context" → context_active=False → context_bundle=None
```

**Finalizing Session:**
```
Generator → "Finalize" → Wizard Step 1 → Edit Step 2 → Confirm Step 3 → Dashboard
```

**Importing History:**
```
Dashboard → "Import" → Paste Text → Preview → Confirm → Updated Dashboard
```

## Integration Points

### Generator ← Campaign Context

**File**: `streamlit_harness/app.py` (Event Generator tab)

**Flow:**
1. Check if `st.session_state["campaign_context_active"]`
2. If true, retrieve `st.session_state["active_context_bundle"]`
3. Pass context_bundle to generator initialization
4. Generator applies severity weights during selection
5. Generator checks recent_complication_ids for cooldowns

**Code Location**:
```python
# In Event Generator tab rendering
if st.session_state.get("campaign_context_active"):
    bundle = st.session_state["active_context_bundle"]
    # Use bundle.severity_weights in generator config
    # Use bundle.recent_complication_ids for cooldowns
```

### Campaign ← Finalization Results

**File**: `streamlit_harness/campaign_ui.py` (Finalize Wizard)

**Flow:**
1. Wizard Step 2: User provides canon/scars/factions
2. Construct CampaignDelta from inputs
3. Step 3: Preview changes and confirm
4. `apply_campaign_delta(current_state, delta)` → new_state
5. Persist new_state to disk
6. Update session state with new campaign
7. Clear context and return to dashboard

### History Import Flows

**Flow C - Existing Campaign:**
```
Paste Text → parse_campaign_history() → Preview → Merge → Save
```

**Flow D - New Campaign:**
```
Paste Text → parse_campaign_history() → Preview → Create → Save
```

**Common Parser Output:**
```python
@dataclass
class ParsedHistory:
    sessions: List[Tuple[datetime, str]]  # (date, content)
    canon_bullets: List[str]
    detected_factions: List[str]
```

## Pure Functional Design

### Principles

All campaign logic is pure functions:
- Input state → Output state
- No mutations
- No I/O
- No random number generation
- Deterministic and testable

### Example: Apply Delta

```python
def apply_campaign_delta(
    state: CampaignState,
    delta: CampaignDelta
) -> CampaignState:
    # Create new objects, never mutate
    new_pressure = max(0, min(10, state.pressure + delta.pressure_change))
    new_heat = max(0, min(10, state.heat + delta.heat_change))
    
    new_scars = state.active_scars + delta.new_scars
    
    # Update factions (combine dispositions)
    new_factions = dict(state.factions)
    for fname, change in delta.faction_changes.items():
        if fname in new_factions:
            old_disp = new_factions[fname].disposition
            new_disp = max(-5, min(5, old_disp + change))
            new_factions[fname] = FactionState(fname, new_disp)
        else:
            new_factions[fname] = FactionState(fname, change)
    
    # Return entirely new state
    return CampaignState(
        pressure=new_pressure,
        heat=new_heat,
        active_scars=new_scars,
        factions=new_factions,
        # ... other fields
    )
```

**Benefits:**
- Easy to test (input → output)
- No hidden state changes
- Safe parallelization (if needed)
- Clear data flow

## Error Handling

### Validation Layers

**Model Layer:**
- Type hints enforce structure
- Dataclass validation on construction
- Value ranges validated in constructors

**Integration Layer:**
- Defensive checks before persistence
- Try/except around I/O operations
- User-friendly error messages in UI

**UI Layer:**
- Input validation before submission
- Preview before destructive operations
- Confirmation dialogs for major changes

### Error Recovery

**File Corruption:**
- If campaign.json corrupted, user can recreate via import
- Backup campaigns/ directory before major operations
- Parser gracefully handles malformed history

**State Inconsistency:**
- Validate bounds on load (pressure/heat 0-10)
- Filter invalid scars/factions
- Log warnings but continue operation

## Performance Considerations

### Current Scale

- ~10-50 campaigns per user (typical)
- ~20-100 sessions per campaign (typical)
- ~100-500 complications per session history (typical)

**Performance Profile:**
- File I/O: <10ms per campaign load/save
- Context computation: <1ms
- History parsing: <100ms for 10KB text
- UI rendering: <200ms for full dashboard

### Optimization Opportunities

**Future (if needed):**
- Lazy load session history (only show recent N)
- Cache computed context bundles
- Incremental saves (delta-based)
- Batch operations for multi-campaign updates

## Testing Strategy

### Unit Tests (Core Module)

**File**: `tests/test_campaign_mechanics.py`

**Coverage:**
- CampaignDelta application
- Pressure/heat decay
- Scar management
- Faction disposition updates
- Band intensity tracking

**Pattern**: Pure input → output testing, no mocks needed.

### Integration Tests (Harness)

**File**: `tests/test_campaign_integration.py`

**Coverage:**
- ContextBundle computation
- SessionPacket derivation
- History parser accuracy
- File persistence round-trip

**Pattern**: Use temp directories, mock I/O where necessary.

### Manual Testing (UX)

**Checklist:**
- Create campaign → apply context → generate → finalize → verify ledger
- Import history (existing) → verify merge non-destructive
- Import history (new) → verify campaign created correctly
- Multi-campaign switching → verify state isolation
- Edge cases: empty history, malformed JSON, boundary values

## Design Decisions and Rationale

### 1. Advisory Pattern

**Decision**: Campaign suggests, never enforces.

**Rationale:**
- Preserves generator autonomy
- User always has control
- Graceful degradation if campaign disabled
- Easier testing (fewer dependencies)

### 2. Immutable Data Structures

**Decision**: All models are frozen dataclasses.

**Rationale:**
- Thread-safe (if parallelization needed)
- Easy to reason about (no hidden mutations)
- Natural undo/redo support (keep old states)
- Forces explicit state transitions

### 3. Heuristic Parsing (Not AI)

**Decision**: Use regex and rules, not LLM parsing.

**Rationale:**
- Deterministic and fast
- No external API dependencies
- User can understand/predict behavior
- Easy to debug and improve
- No hallucination risk

### 4. Campaign-Wide Scars (Not PC-Specific)

**Decision**: Scars belong to campaign, not individual PCs.

**Rationale:**
- Flexible application in narrative
- Supports variable party composition
- Simpler data model
- User interprets mechanical impact

### 5. Three-Step Finalization Wizard

**Decision**: Review → Edit → Confirm pattern.

**Rationale:**
- User sees generator output before commitment
- Prevents accidental auto-commits
- Educational (shows what system detected)
- Builds trust through transparency

## Future Architecture Considerations

### Extensibility Points

**Additional Bands:**
- Add new band IDs to Band enum
- Update intensity calculation rules
- No structural changes needed

**Custom Content Sources:**
- Modular JSON files in data/
- Campaign specifies which sources to pool
- No code changes for new content

**Alternative Persistence:**
- Abstract CampaignRepository interface
- Swap JSON for SQLite, remote API, etc.
- Core models remain unchanged

### Scalability

**Current Limits:**
- Single-user desktop application
- File-based persistence
- No concurrent access

**If Multi-User Needed:**
- Add campaign ownership/sharing
- Implement conflict resolution
- Database backend for persistence
- API layer for remote access

### Integration with External Systems

**Potential Future:**
- Export campaign to VTT platforms
- Import from RPG session logs
- Sync with cloud backup
- Share campaigns between users

**Architecture Support:**
- Clean model layer (easy to serialize)
- Pure functions (easy to expose as API)
- Modular design (swap components)

## Maintenance and Evolution

### Version Management

**Current Version**: Campaign Mechanics v0.2

**Versioning Policy:**
- v0.x: Iterative development, breaking changes allowed
- v1.0: Stable API, backward compatibility required
- vX.Y.Z: Semantic versioning after v1.0

### Backward Compatibility

**Future Considerations:**
- Schema migrations for campaign files
- Deprecation warnings for old formats
- Automatic upgrade on load
- Preserve user data across versions

### Code Review Standards

All campaign code follows:
- Engineering rules (docs/engineering_rules.md)
- ClineRules general standards
- Type safety (mypy clean)
- Unit test coverage (>80%)
- Documentation for public APIs

## References

**Related Documents:**
- docs/REQUIREMENTS_campaign_mechanics_v0.1.md
- docs/REQUIREMENTS_campaign_mechanics_v0.2.md
- docs/UX_NOTES_campaign_v0.1.md
- docs/INTEGRATION_STATUS_flows_BCD.md
- docs/PLAY_GUIDE_campaigns.md

**Code Locations:**
- spar_campaign/ (core module)
- streamlit_harness/campaign_*.py (integration)
- examples/campaign_mechanics_*.py (demos)

---

**Architecture Version**: 0.1  
**Last Reviewed**: 2025-12-25  
**Maintainer**: SPAR Tool Engine Team
