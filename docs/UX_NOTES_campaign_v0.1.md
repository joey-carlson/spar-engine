# Campaign UX Prototype v0.1 - UX Notes

**Date**: 2025-12-25  
**Status**: Prototype  
**Goal**: 3-4 click "living campaign" workflow

---

## Overview

This prototype adds a Campaign Manager mode to the Streamlit harness, demonstrating a multi-campaign management workflow with persistent state, editable canon, and session finalization.

---

## User Flow (Click Counts)

### Create New Campaign: **3-4 clicks**
1. Toggle to Campaign Manager mode (1 click)
2. Click "New Campaign" button (1 click)
3. Fill form + Click "Create Campaign" (1 click)
4. **Total: 3 clicks**

### Open Existing Campaign: **2 clicks**
1. Toggle to Campaign Manager mode (1 click)
2. Click "Open →" on campaign card (1 click)
3. **Total: 2 clicks**

### Run Session: **1 click**
1. Click "Run Session" from dashboard (1 click)
2. (Currently redirects to scenario runner - integration point)
3. **Total: 1 click to enter**

### Finalize Session: **2-3 clicks**
1. Click "Finalize Session" (1 click)
2. Fill wizard form (type bullets, check boxes)
3. Click "Commit Session" (1 click)
4. **Total: 2 clicks + typing**

---

## What's Implemented (v0.1)

### ✅ Campaign Selector
- Multi-campaign list with cards
- Pressure/heat band badges (color-coded)
- Session count, scar count, faction activity
- 1-click open
- New campaign creation form

### ✅ Campaign Dashboard
- Living state overview (pressure, heat, sessions, peak severity)
- Editable canon summary (8-12 bullets)
- Expandable scars list (structured with notes)
- Expandable factions board (attention bars, disposition emojis)
- Last session changes summary
- Campaign ledger (expandable history)
- 1-click to run session

### ✅ Session Workspace
- Integration stub (points to existing scenario runner)
- Campaign context display
- 1-click finalize button

### ✅ Finalize Session Wizard
- 3 bullets: "What happened?"
- Checkboxes: Add scar, rumor spread, faction attention
- Manual pressure/heat adjustments
- Structured scar creation (category, severity, notes)
- Faction selection from existing
- 1-click commit

### ✅ Persistence
- Campaigns saved to `campaigns/*.json`
- CampaignState v0.2 integration
- Ledger append-only (no overwrites)
- Canon summary updates automatically

### ✅ Content Sources Management
- Sources list in dashboard (expandable)
- Built-in source always shown (core_complications)
- Add external sources (name + path, no parsing)
- Enable/disable toggle per source
- Active sources displayed in campaign header
- Active sources recorded in ledger metadata

---

## What's Mocked/Simplified

### 🔧 Session Workspace
**Mock**: "Run Session" shows placeholder with link to existing scenario runner  
**Why**: Full integration would require refactoring scenario runner to accept campaign context  
**Production**: Session workspace should embed scenario runner with pre-populated campaign influence

### 🔧 Campaign History Import
**Mock**: Button shows "Coming in v0.2" info message  
**Why**: History parsing and inference is substantial LLM-driven work  
**Production**: Upload doc → LLM extracts factions/scars/summary → GM reviews/approves

### 🔧 Faction Disposition Changes
**Mock**: Finalize wizard doesn't include disposition adjustment  
**Why**: Keeping wizard under 3-click constraint  
**Production**: Add "Faction disposition changed?" with +/-1 adjustment

### 🔧 Canon Summary Auto-Generation
**Mock**: First bullet from "what happened" appends to canon  
**Why**: Simple rule for v0.1  
**Production**: LLM suggests canon updates based on session, GM approves

### 🔧 Source Parsing/Import
**Mock**: Sources are metadata only (name + path tracked)  
**Why**: No parsing or content mapping in v0.1  
**Production**: Parse external sources, map to SPAR content format, validate tags

### 🔧 Campaign Influence Application
**Mock**: Session workspace shows campaign influence but doesn't auto-apply it  
**Why**: No scenario runner refactor in this task  
**Production**: Campaign influence pre-populates scenario tags/factions

---

## Known UX Pain Points

### 1. **Session-to-Scenario Handoff**
- **Issue**: Have to switch to Debug Harness mode to run scenarios
- **Impact**: Breaks immersion, adds clicks
- **Fix**: Embed scenario runner in session workspace (v0.2)

### 2. **Canon Summary Management**
- **Issue**: Manually editing inline can be fiddly
- **Impact**: May discourage keeping canon current
- **Fix**: Auto-suggest canon updates in finalize wizard (v0.2)

### 3. **Faction Setup**
- **Issue**: Can only add 4 factions at campaign creation
- **Impact**: Have to manually edit JSON to add more
- **Fix**: Add "New Faction" button on dashboard (v0.2)

### 4. **No Undo**
- **Issue**: Committing a session is permanent (no undo)
- **Impact**: Typos or mistakes require manual JSON editing
- **Fix**: Add "Edit Last Entry" option on dashboard (v0.2)

### 5. **Scar Display Verbosity**
- **Issue**: Scars expander shows all details (can be long)
- **Impact**: Visual clutter if many scars
- **Fix**: Show scar count + category badges, expand for details (v0.2)

---

## Design Decisions & Rationale

### Mode Toggle (Radio Buttons)
**Decision**: Top-level radio toggle between Campaign Manager and Debug Harness  
**Rationale**: Clean separation, no nested navigation, preserves existing debug functionality  
**Alternative considered**: Sidebar nav → Rejected (adds click depth)

### Dashboard-First (No Separate Pages)
**Decision**: Dashboard is single scrollable page with collapsible sections  
**Rationale**: Optimizes for "see everything quickly", no tab navigation  
**Alternative considered**: Tabs for scars/factions/ledger → Rejected (cognitive load)

### Finalize Wizard (Form, Not Modal)
**Decision**: Finalize renders as dedicated page, not modal/overlay  
**Rationale**: Streamlit forms work better as pages, modal UX is complex  
**Trade-off**: Adds navigation, but keeps form simple

### Explicit Scar Creation Only
**Decision**: No auto-scar triggers in wizard  
**Rationale**: Scars should be meaningful and rare, GM decides explicitly  
**Alternative considered**: "High severity last scene?" checkbox → Rejected (obscures intent)

### First Bullet → Canon
**Decision**: First "what happened" bullet auto-adds to canon summary  
**Rationale**: Zero-friction canon updates, GM writes once  
**Trade-off**: Less control, but much faster

---

## Click Count Verification

| Action | Clicks | Notes |
|--------|--------|-------|
| Open campaign from selector | 2 | Mode + Open button |
| Create new campaign | 3 | Mode + New + Create |
| Run session | 3 | Open + Run Session + (scenario runner) |
| Finalize session | 2 | Finalize + Commit |
| Edit canon | 0 | Inline, auto-saves |
| View faction details | 1 | Expand factions |
| View scar details | 1 | Expand scars |
| View ledger | 1 | Expand ledger |
| View sources | 1 | Expand sources |
| Add source | 2 | Expand + Add button |
| Toggle source | 1 | Click gear icon |

**Assessment**: Core workflow stays under 4-click limit ✅

---

## What GM Sees After 3 Sessions

**Campaign Dashboard:**
- Canon summary: 10-15 bullets (growing organically)
- Factions: 3-4 with attention bars (visual progress)
- Scars: 1-2 structured (e.g., "supplies_depleted", "known_to_city_watch")
- Pressure/heat metrics with bands ("hunted", "strained")
- Ledger: 3 entries with "what happened" summaries

**Mental model achieved**: "The campaign remembers"

---

## Production Readiness Assessment

### What Works Well ✅
- Multi-campaign management (no confusion)
- Campaign state visibility (metrics + bands)
- Editable canon (inline updates)
- Finalize wizard (simple form)
- Persistent state (survives app restart)

### What Needs Work 🔧
- Session workspace integration (currently stub)
- Campaign influence auto-application (manual in v0.1)
- History import (mocked)
- Canon auto-suggestions (currently manual)
- Faction/scar management after creation (read-only)

### Critical Path for v0.2
1. Embed scenario runner in session workspace
2. Apply campaign influence automatically
3. Add faction management UI
4. LLM-driven canon summary suggestions

---

## Designer Questions (For Feedback)

1. **Does the campaign selector feel like the right entry point?**
   - Alternative: Start in debug mode, campaigns are sidebar option

2. **Is the finalize wizard too light or too heavy?**
   - Too light: Need more capture?
   - Too heavy: Remove some fields?

3. **Should canon summary editing be more prominent?**
   - Current: Inline text inputs
   - Alternative: Dedicated "Edit Canon" mode

4. **Are faction/scar displays too compact or too verbose?**
   - Current: Expanders with full details
   - Alternative: Badge summary + click for details

5. **Does the 1-page dashboard feel crowded or efficient?**
   - Alternative: Separate tabs for factions/scars/ledger

---

## Technical Notes

### Integration Architecture
- `streamlit_harness/campaign_ui.py` - Campaign UI module (standalone)
- `streamlit_harness/app.py` - Mode selector integration (minimal change)
- `campaigns/*.json` - Campaign persistence (one file per campaign)
- `spar_campaign/` - Campaign mechanics (zero modifications)

### State Management
- Campaign selector: `st.session_state.campaign_page` (selector/dashboard/session/finalize)
- Current campaign: `st.session_state.current_campaign_id`
- Persistence: JSON files in campaigns/ directory
- No database required (file-based for v0.1)

### What Wasn't Changed
- ❌ spar_engine/* (engine untouched)
- ❌ spar_campaign/* (mechanics untouched)
- ❌ Scenario runner logic (preserved)
- ❌ Existing debug harness (still accessible)

---

## Next Steps (v0.2 Recommendations)

### High Priority
1. **Embed scenario runner** in session workspace
2. **Auto-apply campaign influence** to scenario setup
3. **Add "Edit Last Entry"** to dashboard

### Medium Priority
4. **Faction management UI** (add/edit factions after creation)
5. **Canon auto-suggestions** (LLM-driven from session notes)
6. **Scar management UI** (mark resolved, add notes)

### Low Priority (Deferred)
7. Campaign history import (LLM extraction)
8. Campaign cloning (alternate timelines)
9. Export campaign packet (shared-world)
10. Living con coordinator mode

---

**Prototype Status**: Ready for designer playtest  
**Production Status**: Proof of concept (needs v0.2 integration work)  
**Click Count Goal**: ✅ Met (≤4 clicks for all core actions)
