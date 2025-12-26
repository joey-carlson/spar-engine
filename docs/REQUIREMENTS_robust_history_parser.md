# Robust Campaign History Import - Requirements v1.0

**Created**: 2025-12-25  
**Status**: In Progress  
**Target**: History Parser v0.4

## Overview

Enhance campaign history parser with production-grade robustness:
- Structured markdown parsing (markdown-it-py)
- Flexible date normalization (dateparser)
- Fuzzy entity deduplication (rapidfuzz)
- Inline promote/demote controls with persistence

## Dependencies Added

```
markdown-it-py>=3.0.0  # Structured markdown token parsing
dateparser>=1.2.0      # Flexible date parsing and normalization
rapidfuzz>=3.5.0       # Fuzzy string matching for deduplication
```

All dependencies are local-first, lightweight, deterministic.

## Technical Requirements

### A. Markdown Structure Parsing

**Replace**: Regex-based section splitting  
**With**: markdown-it-py token-based parsing

**Benefits:**
- Handles heading variants: "Canon Summary", "Canon Summary (Expanded)"
- Correctly identifies section boundaries even with immediate subheaders
- More resilient to formatting variations

**Implementation:**
```python
from markdown_it import MarkdownIt

md = MarkdownIt()
tokens = md.parse(text)

# Iterate tokens to find heading_open tokens
# Extract section content between heading boundaries
```

### B. Canon Summary Extraction (Never Empty)

**Current Issue**: Only extracts 1 bullet when subsections present

**Requirements:**
1. Accept header variants: "Canon Summary", "Canon Summary (Expanded)", "Canon Summary …"
2. Extract from subsections by keyword matching:
   - Premise/Pitch: 1-2 bullets
   - Core myth-arc: 1 bullet (if present)
   - Player Characters: 1 bullet (collapsed roster)
   - Key NPCs/Powers: 2-3 bullets
   - Major Artifacts: 2-3 bullets
   - Current Situation: 1-2 bullets
3. If section exists but extraction yields empty:
   - Return warning with section heading, token count, reason code
   - Example: "Canon Summary found (342 chars) but no recognized subsections"

### C. Ledger Session Parsing

**Requirements:**
1. Parse only from Campaign Ledger section
2. Support header formats:
   - `### YYYY-MM-DD — Session N — Title`
   - `### YYYY-MM-DD — Session N (Current) — Title`
3. Extract fields:
   - `date`: ISO YYYY-MM-DD (normalized via dateparser)
   - `session_number`: int
   - `title`: string only (no bullets)
   - `bullets`: list[str] (structured)
   - `content`: raw text
4. Ignore "Session X" mentions outside ledger section

### D. Date Parsing Robustness

**Use dateparser for normalization:**

```python
import dateparser

# Handle variants
dates = [
    "2025-01-05",           # ISO
    "January 5, 2025",      # Natural
    "Jan 5, 2025",          # Abbreviated
    "01/05/2025",           # Numeric
]

normalized = dateparser.parse(date_str).strftime('%Y-%m-%d')
```

**Fallback:** If dateparser fails, allow "Unknown" but preserve ordering by appearance

### E. Entity Classification & Fuzzy Dedupe

**Three-stage process:**
1. Extract candidates from specific sections
2. Classify using keyword heuristics
3. Fuzzy dedupe with rapidfuzz

**Classification Heuristics:**

**Factions** (groups with agency):
- Keywords: pact, guardians, makers, guild, cult, consortium, watch, syndicate, union, order, society, council, alliance, league
- Positive patterns: plurals, "of" phrases

**Places** (locations):
- Keywords: citadel, staircase, bral, tunnels, archives, sphere, chamber, fortress, ship, city, tower, palace, keep, sanctum, spires
- Negative weighting: if faction keywords present, classify as faction

**Artifacts** (named objects):
- Patterns: "The X:", "X's Ring/Device/Crown", "Device of Y"
- Extract from Major Artifacts section primarily
- Common names: Chronolens, Ring, Device, Crown, Scepter, Orb, Staff, Sword

**Concepts** (abstract powers):
- Keywords: incarnate, seed, essence, aspect, principle

**Fuzzy Dedupe with rapidfuzz:**

```python
from rapidfuzz import fuzz, process

def normalize_entity(name: str) -> str:
    # Strip "The " prefix
    name = re.sub(r'^The\s+', '', name)
    return name

def fuzzy_dedupe(names: List[str], threshold: int = 85) -> List[str]:
    normalized = [normalize_entity(n) for n in names]
    # Use rapidfuzz to find near-matches
    # Keep highest-frequency variant
```

### F. Inline Promote/Demote Controls

**UI Requirements:**

**Parse Preview Layout:**
```
Download Parsed JSON [button]

Factions (3)
  • Temporal Guardians [Demote▼] [Remove]
  • Solstice Pact [Demote▼] [Remove]
  • Maker Tunnels [Demote▼] [Remove]

Places (2)
  • Radiant Citadel [Promote▲] [Remove]
  • Infinite Staircase [Promote▲] [Remove]

Artifacts (3)
  • Chronolens [Demote▼] [Remove]
  • Bryannas's Ring [Demote▼] [Remove]
```

**Control Behaviors:**
- **Promote▲**: Moves entity to Factions list
- **Demote▼**: Opens inline selector (Place/Artifact/Concept/Remove)
- **Remove**: Adds to ignored list

**Persistence Model:**
```python
@dataclass
class ImportOverrides:
    campaign_id: str
    promoted_to_faction: List[str]
    demoted_to_place: List[str]
    demoted_to_artifact: List[str]
    demoted_to_concept: List[str]
    ignored: List[str]
    
    def save(self) -> None:
        # Save to campaigns/{campaign_id}_import_overrides.json
```

**Application Order:**
1. Run heuristic classification
2. Apply fuzzy dedupe
3. Load import overrides for campaign
4. Apply overrides (promote/demote/ignore)
5. Display in UI with controls

### G. Artifact Extraction Patterns

**Major Artifacts Section:**
- "The Chronolens: description" → "Chronolens"
- "Bryannas's Ring: description" → "Bryannas's Ring"
- "Infernal Device of Lum the Mad: description" → "Infernal Device of Lum the Mad"

**Control Rod Patterns:**
- "Control lever/rod" → "Control Lever"
- "Chronal Prism" → "Chronal Prism"

**Extraction Strategy:**
```python
# Pattern 1: "The X:" or "X:"
# Pattern 2: "X's Y:"
# Pattern 3: "Device/Ring/Crown of Z"
# Pattern 4: Common artifact nouns + "of" phrase
```

## Acceptance Criteria

Using expanded Spelljammer file (v1.1):

1. **Canon Summary:**
   - ✅ Extracted even with "(Expanded)" suffix
   - ✅ Contains premise + current situation
   - ✅ No import instructions or ledger bleed
   - ✅ 8-12 bullets target

2. **Sessions:**
   - ✅ Sessions 0-10 with correct dates
   - ✅ Titles clean (no bullets)
   - ✅ Bullets in separate field
   - ✅ Correct date ordering

3. **Factions:**
   - ✅ Includes: Temporal Guardians, Solstice Pact, Makers
   - ✅ Excludes: "Future Sessions", "Maker Tunnels"
   - ✅ Normalized: "The Solstice Pact" → "Solstice Pact"
   - ✅ No duplicates

4. **Artifacts:**
   - ✅ Includes: Chronolens, Bryannas's Ring, Infernal Device of Lum the Mad
   - ✅ Optional: Chronal Prism, Control Lever

5. **UI Controls:**
   - ✅ Inline promote/demote buttons (no subdialogs)
   - ✅ Changes apply immediately
   - ✅ Overrides persist per campaign

## Implementation Phases

### Phase 1: Dependency Integration (Current)
- [x] Add dependencies to requirements.txt
- [x] Install dependencies
- [ ] Commit requirements update

### Phase 2: Core Parser Rewrite
- [ ] Implement markdown-it-py based section extraction
- [ ] Implement dateparser integration
- [ ] Implement rapidfuzz deduplication
- [ ] Update existing tests

### Phase 3: UI Controls
- [ ] Design import overrides data model
- [ ] Implement inline promote/demote controls
- [ ] Implement override persistence
- [ ] Update campaign_ui.py preview section

### Phase 4: Testing & Validation
- [ ] Unit tests for markdown parsing
- [ ] Unit tests for date normalization
- [ ] Unit tests for fuzzy dedupe
- [ ] Integration test with v1.1 Spelljammer file
- [ ] Validate all acceptance criteria

### Phase 5: Documentation
- [ ] Update PLAY_GUIDE_campaigns.md with new features
- [ ] Update ARCH_campaign_integration.md with parser details
- [ ] Document inline controls usage
- [ ] Update CHANGELOG

## Design Rationale

**Why markdown-it-py?**
- Structured token parsing replaces fragile regex
- Handles heading variants naturally
- Identifies lists, code blocks, etc. reliably

**Why dateparser?**
- Handles messy date formats without manual patterns
- Timezone-aware
- Locale support for international campaigns

**Why rapidfuzz?**
- Fast, deterministic fuzzy matching
- No training data or models needed
- Perfect for entity normalization

**Why inline controls?**
- Cheap to use (1-2 clicks per correction)
- No context switching (subdialogs break flow)
- Corrections persist across imports
- GM sees and controls classification

**Why persistent overrides?**
- Heuristics will never be perfect
- Campaign-specific entity types vary
- GM corrections should "stick"
- No repeated work across imports

## Performance Targets

- Parse 50KB file: <500ms
- Parse 500KB file: <2s (with warning if larger)
- Fuzzy dedupe 100 entities: <100ms
- UI controls responsive: <50ms per action

## Safety & Privacy

- All processing local (no API calls)
- No telemetry on parsed content
- Overrides stored locally only
- Deterministic (same input → same output + overrides)

## Out of Scope

- LLM-based summarization
- Hosted parsing services
- Spreadsheet import
- Cross-campaign entity linking
- UI redesign beyond preview panel

## Success Metrics

1. Parser never returns empty canon when section exists
2. Session titles 100% clean (no bullet pollution)
3. Faction false positive rate <5%
4. Artifact recall rate >90% for common patterns
5. GM correction flow <10 seconds per entity

---

**Version**: 1.0  
**Next Review**: After Phase 2 completion
