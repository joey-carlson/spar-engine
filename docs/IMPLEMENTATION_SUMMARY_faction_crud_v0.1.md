# Faction CRUD v0.1 — Implementation Summary

**Version**: 0.1  
**Implemented**: 2025-12-26  
**Status**: Complete  

## Overview

Added full CRUD (Create, Read, Update, Delete/Archive) functionality for factions with clear attention/disposition semantics, GM-private notes separation, and export integration.

## What Changed

### Data Model (spar_campaign/models.py)

**FactionState v0.3 Structure**:
```python
@dataclass(frozen=True)
class FactionState:
    faction_id: str              # Stable identifier
    name: str                    # Display name (story-facing, required)
    description: str = ""        # What it is/wants (story-facing)
    attention: int = 0           # Neutral salience 0-20 (how much watching)
    disposition: int = 0         # Valence -2 to +2 (hostile ↔ allied)
    notes: Optional[str] = None  # GM-private scratchpad (NOT in story exports)
    is_active: bool = True       # Soft delete flag
```

**Key Changes**:
- Split `notes` field into three distinct fields:
  - `name`: Display name (required, story-facing)
  - `description`: What it is/wants (story-facing, exported)
  - `notes`: GM-private scratchpad (NOT exported in story view)
- Added `is_active` for soft delete (preserves historical references)
- Added `get_attention_band()` and `get_disposition_label()` helper methods

**Migration Strategy**:
- Automatic migration in `from_dict()` for v0.2 → v0.3
- Short notes without punctuation → `name` field
- Long punctuated notes → derive name from ID, preserve as `notes`
- Empty notes → derive name from ID
- One-time conversion, no repeated migrations

### UI Changes (streamlit_harness/campaign_ui.py)

**Replaced Read-Only Display with Interactive CRUD**:

1. **Add Faction**:
   - Inline form (not modal)
   - Fields: name*, description, initial attention/disposition, GM notes
   - Live attention band preview
   - Disposition select slider with friendly labels
   - Duplicate ID check

2. **View Mode**:
   - Shows name, description, attention band, disposition label
   - Progress bar for attention visualization
   - Quick +/- buttons for attention adjustment (session play)
   - Edit (✏️) and Archive (📦) buttons

3. **Edit Mode**:
   - Inline editing (no modal)
   - Full field editing: name, description, attention, disposition, notes
   - Live band preview during editing
   - Cancel/Save options

4. **Archive/Restore**:
   - Soft delete: sets `is_active=False`
   - Archived factions shown in collapsed section
   - One-click restore (↩️ button)
   - Preserves all faction data for historical references

**Attention Semantics**:
- Bands: Unaware (0) → Noticed (1-5) → Interested (6-10) → Focused (11-15) → Obsessed (16-20)
- Neutral salience (not good/bad)
- Quick +/- buttons for session-time updates

**Disposition Semantics**:
- Labels: 😡 Hostile (-2) → 😠 Unfriendly (-1) → 😐 Neutral (0) → 🙂 Friendly (+1) → 😊 Allied (+2)
- Select slider with clear visual feedback

### Export Integration

**Campaign History Export** now includes Factions section:
```markdown
## Factions

**City Watch** *(Focused, Unfriendly)*  
Local law enforcement investigating recent activities. Primary focus on maintaining public order.

**Merchant Guild** *(Noticed, Neutral)*  
Trade organization with significant political influence in the city.
```

**Story/System Separation**:
- Included: name, description, attention band (human-readable), disposition label
- Excluded: raw attention/disposition numbers, GM-private notes
- Only active factions exported (archived excluded)

### Audit Trail

**Admin Actions Logged** (system-facing only):
- `faction_added`: Records new faction creation outside sessions
- `faction_edited`: Tracks changes to name, attention, disposition
- `faction_archived`: Records when faction archived
- `faction_restored`: Records when faction restored from archive

**Audit Entry Structure**:
```json
{
  "entry_type": "admin_action",
  "timestamp": "2025-12-26T15:30:00",
  "action": "faction_added",
  "details": {
    "faction_id": "new_faction",
    "name": "New Faction",
    "initial_attention": 0,
    "initial_disposition": 0
  }
}
```

Admin audit entries do NOT appear in story exports by default (system-facing only).

## Design Decisions

### Field Separation Rationale

**Why split notes into three fields?**
1. **name**: Clear display name for UI and exports
2. **description**: Story-facing context (what the faction is/wants)
3. **notes**: GM-private scratchpad (plans, secrets, reminders)

This separation enables:
- Clean story exports without GM secrets
- Stable faction descriptions that evolve slowly
- Private workspace for GM planning

### Soft Delete Rationale

**Why soft delete instead of hard delete?**
- Preserves historical ledger references
- No cascade checking needed
- Can restore if archived by mistake
- Simple is_active flag implementation

**Alternative (parking lot)**: Add "Delete Permanently" option later for cleaning up truly unwanted factions.

### Attention vs Disposition

**Clarified semantics**:
- **Attention**: Neutral "how much watching" (salience, not valence)
- **Disposition**: Good/bad attitude (valence, not intensity)

**Why this matters**:
- Prevents confusion of "high attention = bad thing"
- Faction can be Obsessed + Allied (high attention, positive)
- Faction can be Unaware + Hostile (low attention, negative)

### Export Human-Readable Language

**Why bands instead of numbers in story exports?**
- "Focused, Unfriendly" reads naturally at the table
- "15, -1" requires explaining SPAR's scale
- Passes the "read-aloud test" (data contract principle)

## Testing

**Test Coverage**: 23 tests, 5 test classes
- Data model and migration (9 tests)
- CRUD operations (6 tests)
- Audit trail structure (4 tests)
- Export integration (3 tests)
- Story/system separation (1 test)

**All tests pass** ✅

## Story/System Separation

**Story-Facing** (exported in campaign history):
- Faction name
- Faction description
- Attention band (human-readable)
- Disposition label (human-readable)

**System-Facing** (ledger only, not story exports):
- Raw attention/disposition numbers
- GM-private notes
- Admin audit entries
- Soft delete flag

**GM-Private** (never exported, even in system view):
- Notes field (scratchpad for plans/secrets)

## Backward Compatibility

**v0.2 Campaigns**:
- Automatically migrated on load
- Short notes → name field
- Long notes → preserved as notes, name derived from ID
- No data loss
- No user action required

**Existing References**:
- Faction IDs unchanged
- Manual entry references remain valid
- Session finalization logic unchanged

## Future Work (Parking Lot)

These items are explicitly deferred:

1. **Faction influence on generator context**: After CRUD is stable, add faction-based tag/source suggestions (high attention → social_friction bias, etc.)

2. **Permanent delete option**: UI to permanently remove archived factions (with safety checks)

3. **Faction detail view**: Expanded view showing all historical references to faction

4. **Faction notes in system export**: Optional diagnostic export including GM notes

## Files Modified

- `spar_campaign/models.py`: FactionState v0.3 structure, migration logic
- `streamlit_harness/campaign_ui.py`: Interactive CRUD UI, export integration
- `tests/test_faction_crud.py`: Comprehensive test suite (23 tests)
- `docs/IMPLEMENTATION_SUMMARY_faction_crud_v0.1.md`: This document
- `CHANGELOG.md`: Version history entry

## Verification Steps

1. ✅ All 23 tests pass
2. ✅ Data model migration handles v0.2 format
3. ✅ CRUD UI functional (add/edit/archive/restore)
4. ✅ Export includes faction roster with human-readable bands
5. ✅ Story/system separation maintained
6. ✅ Audit trail generated for admin actions
7. ✅ Soft delete preserves historical references

## Usage Example

### Adding a Faction (Dashboard)
1. Open campaign dashboard
2. Expand "👥 Factions" section
3. Click "➕ Add Faction"
4. Fill in name (required), description (optional), initial values
5. Optionally add GM-private notes
6. Click "💾 Add"

### Quick Attention Update (During Play)
- Use ➖/➕ buttons in faction view mode
- Instant adjustment without full edit form
- Useful for session-time updates

### Full Edit (Between Sessions)
1. Click ✏️ Edit button on faction
2. Update any fields
3. Save changes
4. Audit entry created automatically

### Archiving Inactive Factions
1. Click 📦 Archive button
2. Faction moves to "Archived Factions" section
3. Historical references preserved
4. Can restore with ↩️ button if needed

## Integration Points

**Works with**:
- Campaign history export (faction roster section)
- Session finalization (faction attention updates)
- Manual entry form (faction references)
- Import override system (faction classification)

**Future integration** (parking lot):
- Campaign context bundle (generator influence)
- Faction-linked scars (explicit relationships)
- Faction reaction events (v0.3+ campaign mechanics)

---

## Summary

Faction CRUD v0.1 is complete with:
- ✅ Full CRUD operations (inline, no modals)
- ✅ Clear attention (salience) vs disposition (valence) semantics
- ✅ Story/system field separation (description exported, notes private)
- ✅ Soft delete with reference preservation
- ✅ Export integration with human-readable bands
- ✅ System-facing audit trail
- ✅ Automatic v0.2 → v0.3 migration
- ✅ 23 passing tests

Next: Faction influence on generator context (after CRUD is verified stable in use).
