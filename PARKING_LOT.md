# Parking Lot (Post-v1.0, Additive Only)

These features are **parked** for post-v1.0 development. All v1.0 functionality is complete, locked, and stable. Future work will be additive enhancements, not patches.

## Quick Reference

1. **Generator Richness** - New content packs (thematic, campaign-specific), Loot Generator on SOC foundation
2. **Campaign Story Web View** - Read-only narrative presentation powered by story exports
3. **Canon Summary Heuristics Tuning** - Smarter deterministic synthesis, optional prompts
4. **Cross-System Adapters** - D&D, GURPS, VtM mappings via presets + vocabulary + content packs

---

## 1. Generator Richness (Content, Not Mechanics)

**Status**: Parked  
**Why**: Core generator is stable and usable; richness is additive.

**Includes:**
- Expanding core_complications volume and variety
- Thematic content packs (genre, region, campaign-specific)
- Campaign-specific packs (Spelljammer, Noir, Survival, etc.)
- Vocabulary/phrase tuning for stronger narrative flavor

**Explicitly does not include:**
- Engine math changes
- SOC/cutoff logic changes

---

## 2. Loot Generator (SOC-Based, Shared Framework)

**Status**: Parked  
**Why**: Requires shared generator abstraction; not required for v1.0 play.

**Includes:**
- Loot generator built on the same Self-Organized Criticality foundation
- Shared generator framework to avoid duplication:
  - state → distribution → cutoff → diagnostics
- Same Prep Queue → Canon workflow
- Campaign context influence (factions, scars, heat)

**Explicitly not:**
- Random tables disconnected from SOC
- Separate logic silo

---

## 3. Campaign Story Web View

**Status**: Parked  
**Why**: Story-facing exports are now clean; web view is presentation only.

**Includes:**
- Read-only web presentation of campaign story
- Session timeline
- Canon Summary + Session Log
- Possibly player-safe views

**Explicitly not:**
- New logic
- Editing capabilities
- State mutation

---

## 4. Canon Summary Heuristics Tuning

**Status**: Parked  
**Why**: Canon is now correct and GM-authored; heuristics can be improved later.

**Includes:**
- Better deterministic suggestions for "what is true now"
- Improved synthesis phrasing
- Optional prompts or templates

**Explicitly not:**
- Auto-canon
- LLM-driven summarization

---

## 5. Cross-System Adapters

**Status**: Parked  
**Why**: Engine is system-agnostic; adapters are reach, not foundation.

**Includes:**
- D&D adapter (terminology + presets)
- GURPS adapter
- Vampire: the Masquerade adapter
- Primarily:
  - content packs
  - presets
  - vocabulary mappings

**Explicitly not:**
- Forked engines
- Separate mechanics layers

---

## 6. Source List Import (Deep Parsing)

**Status**: Parked  
**Why**: Metadata-only source support is sufficient for v1.0.

**Includes:**
- Parsing large external files (e.g. "One Loot Table")
- Mapping external content into generator packs
- UX for managing large third-party sources

**Explicitly not:**
- Required for current generator use

---

## 7. Docx / Rich-Format Export

**Status**: Parked  
**Why**: Markdown exports are sufficient and correct.

**Includes:**
- DOCX export
- Possibly PDF
- Formatting polish only

**Explicitly not:**
- Changes to export content or structure

---

## 8. Advanced Campaign / Multi-GM Features

**Status**: Parked  
**Why**: Single-GM workflows are complete and solid.

**Includes:**
- Multi-GM conflict resolution
- Audit views
- Permissions
- Merge tooling

---

## 9. Advanced Faction Features

**Status**: Parked  
**Why**: Faction CRUD + generator influence is complete for v1.0.

**Includes:**
- Permanent delete (vs archive)
- Faction history drill-down
- Faction "moves" or autonomous behavior

**Explicitly not:**
- Required for generator influence

---

## Design Philosophy for v2.0+

All future work follows these principles:

1. **Additive, Not Corrective** - v1.0 is locked and correct
2. **Content Before Code** - Prefer content packs over engine complexity
3. **Preserve Agency** - Never auto-mutate campaign state
4. **Story/System Separation** - Maintain clean boundaries
5. **SOC Foundation** - New generators use same mathematical core
