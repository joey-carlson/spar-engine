# History Parser v0.6 Requirements - Real World Fixes

**Created**: 2025-12-25  
**Status**: Planned  
**Context**: Comprehensive testing with 5 diverse campaign documents revealed systematic gaps

## Test Corpus Summary

| Document | Format | Status | Key Issues |
|----------|--------|--------|------------|
| Spelljammer v1.4 | Markdown | Partial success | Separators in bullets, GM notes merged, no artifacts |
| SPAR Saffron Fog | Markdown | Failed | Canon from wrong source, no factions, no entities, prep-only not handled |
| GURPS Ashline | Plain text | Failed | Empty session content, dates missed, wrong faction classification |
| VtM Crimson Sermon | DOCX | Failed | Empty session content, no factions, no entities |
| Space Opera Veilline | Plain text | Failed | Empty session content, no factions, no entities, no parsing of prep sections |

## Critical Issues (Must Fix)

### 1. Session Content Extraction Failures

**Problem**: Sessions detected but have empty bullets/content  
**Affected**: GURPS (4 sessions), VtM (2 sessions), Space Opera (1 session)

**Root Cause**: Relaxed header detection finds headers but doesn't properly extract following content.

**Fix Required**:
- Capture indented/labeled lines (Job:, Combat:, Aftermath:, etc.)
- Parse Date: lines within session blocks
- Preserve block structure until next major delimiter
- Extract GM notes into separate notes[] field

### 2. Separator Artifacts Leaking

**Problem**: Literal `---` strings appearing in bullets and content  
**Affected**: Spelljammer (all sessions)

**Fix Required**:
- Strip decorative separators (`---`, `====`, etc.) from stored content
- Use them as block boundaries but don't preserve in output
- Apply to bullets, content, and canon_summary

### 3. GM Notes Inline Contamination

**Problem**: "GM note:", "Table note:", "GM seed:" mixed into regular bullets  
**Affected**: Spelljammer sessions

**Fix Required**:
- Detect labeled GM commentary patterns
- Extract to session.notes[] or session.gm_notes field
- Keep bullets clean for narrative content only

### 4. Artifact Extraction Complete Failure

**Problem**: artifacts[] empty despite explicit content  
**Affected**: All 5 documents

**Specific Misses**:
- Spelljammer: Party assets/gear section (Message Bottle, control rod, etc.)
- SPAR: Parking Lot items
- VtM: No artifact section but props mentioned
- GURPS: Loot/economy section
- Space Opera: Implicitly mentioned gear

**Fix Required**:
- Mine "Party assets", "Notable gear", "Equipment" sections
- Mine "Parking Lot" → items/props subsections
- Mine "Loot" and "Economy" sections
- Extract from session finds/loot mentions

### 5. Faction Section Authority

**Problem**: Parser ignores explicit "Factions" sections, returns empty  
**Affected**: SPAR, VtM, GURPS (wrong classification), Space Opera

**Fix Required**:
- Treat "Factions" section as authoritative
- Parse faction names from ### headings under Factions
- Extract "Key faces" as faction.npcs[]
- Don't override with heuristic classification

### 6. Entity Extraction Under-Performance

**Problem**: Places, NPCs, concepts all empty despite rich source data  
**Affected**: All documents

**Specific Misses**:
- Places: SPAR (Saltglass Pier, Lantern Row, etc.), GURPS (Dustfall Depot, The Sinks), VtM (Avalon Theater, Getty tunnels)
- NPCs: VtM has explicit cast list, Space Opera has pocket NPCs
- Concepts: SPAR (Saffron Fog, Fog Ledger), GURPS (water fever), VtM (Masquerade)

**Fix Required**:
- Mine "Night Map", "Region snapshot", "Appendix: quick names"
- Mine "NPC Cast List", "Pocket NPCs"
- Treat named phenomena as concepts
- Extract from "Questions", "Cool stuff" sections

### 7. Prep-Only Documents Not Handled

**Problem**: Session 0 prep documents return mostly empty despite rich content  
**Affected**: SPAR (explicit "Pre-Session 0" status)

**Fix Required**:
- Detect campaign_prep mode indicators
- Extract even when sessions[] empty:
  - Factions, entities, canon, hooks
  - Session 0 goals, questions, opening scene
  - Parking lot materials

### 8. Future Content Not Captured

**Problem**: open_threads[] empty despite explicit forward-looking sections  
**Affected**: SPAR, GURPS, VtM, Space Opera

**Missed Sections**:
- "Next session" options
- "Cool stuff, no slot yet"
- "Parking Lot" items
- "Loose Ideas"
- "Questions to answer"
- "Things that can go wrong"

**Fix Required**:
- Parse Parking Lot sections
- Detect "Next session" variants
- Extract "Cool stuff", "Loose Ideas", "Questions" sections
- Mine "Things that can go wrong" patterns

### 9. Content Cleanup Issues

**Problem**: Markdown artifacts, broken emphasis, truncation mid-sentence  
**Affected**: SPAR canon, Spelljammer bullets

**Examples**:
- `"---\n\n## Elevator pitch\n..."` in canon bullets
- `"*Status right now:**"` (broken emphasis)
- `"#### Astral Elves (recurring"` (heading marker in bullet)

**Fix Required**:
- Strip heading markers (####) from bullet text
- Clean broken emphasis markers
- Clip at sentence boundaries when truncating
- Add `was_truncated: true` flag if clipped

## Implementation Strategy

### Phase 1: Content Extraction Fixes (High Priority)
1. Session block capture improvements
2. Labeled line extraction (Job:, Combat:, etc.)
3. Date: line parsing within blocks
4. GM note separation

### Phase 2: Section Authority (High Priority)
1. Explicit Factions section parsing
2. Assets/Gear section mining
3. Parking Lot section extraction
4. Appendix/Quick names extraction

### Phase 3: Entity Enrichment (Medium Priority)
1. NPC Cast List parsing
2. Night Map/Region mining
3. Concept/phenomena detection
4. Named mechanics as concepts

### Phase 4: Prep Document Support (Medium Priority)
1. Campaign prep mode detection
2. Session 0 goals/questions extraction
3. Opening scene capture
4. Table style/playstyle metadata

### Phase 5: Content Cleanup (Low Priority)
1. Separator stripping
2. Heading marker removal
3. Emphasis repair
4. Sentence-boundary truncation

## Acceptance Criteria

### Minimum Viability Per Import
1. If doc contains "Session X" blocks → sessions must have non-empty bullets OR content
2. If doc contains "Factions" section → factions[] must be non-empty
3. If doc contains "Parking Lot" / "Questions" / "Next session" → open_threads[] must be non-empty
4. No separator artifacts in output (---, ====)
5. GM notes in separate field, not inline with bullets

### Format Coverage
- Markdown with headers ✓ (existing)
- Plain text with separators (GURPS, Space Opera)
- DOCX with sections (VtM)
- Prep-only documents (SPAR)

## Design Constraints

- Maintain deterministic behavior
- No LLM/hosted parsing
- Local-first dependencies only
- Backward compatible with v1.1/v1.4 structured formats
- Fallbacks only when structured extraction insufficient

## Estimated Effort

This is a **major revision** (v0.6), not a tuning pass:
- ~300-500 lines of new extraction logic
- New section type handlers
- Substantial testing required
- Breaking changes to fallback triggers possible

## Recommendation

Given scope, suggest implementing in phases rather than all at once:
1. **v0.6.1**: Session content + separator cleanup (Spelljammer fixes)
2. **v0.6.2**: Faction section authority + asset mining (SPAR/VtM fixes)
3. **v0.6.3**: Entity enrichment (all documents)
4. **v0.6.4**: Prep document mode (SPAR Session 0)

Each phase deliverable and testable independently.
