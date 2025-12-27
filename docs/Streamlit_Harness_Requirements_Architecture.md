# Streamlit Harness – Requirements & Architecture

<!--
Version History:
- v0.1 (2025-12-22): Initial requirements and architecture definition
-->

**Current Version**: v0.1  
**Date**: December 2025

## 1) Purpose

Build a **debug-first Streamlit harness** for the SPAR Engine. This harness is not a "product UI," it is a **development and tuning instrument** that makes it easy to validate:

- severity distribution behavior (calm/normal/spiky + morphology sliders)
- cutoff frequency and cutoff resolution behavior
- content filtering and cooldown interactions
- state evolution across ticks/events
- repeat rates and tag frequency

This harness should accelerate engine iteration while keeping the engine **UI-agnostic**.

---

## 2) Scope (v0.1)

### In scope
- Run the engine with **configurable scene inputs**
- Generate **single** and **batch** events
- Display events as readable cards + JSON debug view
- Show **distribution diagnostics** over a batch run
- Support **seeded deterministic runs**
- Support **stateful runs** (load/save state; tick before run)
- Support **pack selection** by local file path

### Out of scope (explicitly deferred)
- Multi-user or hosted deployment concerns
- Authentication/authorization
- Collaborative features or shared sessions
- Content authoring UI beyond raw JSON viewing/editing
- System adapters (D&D mapping) inside the harness
- Marketplace / pack discovery

---

## 3) Functional Requirements

### R1 – Inputs panel (left sidebar)
Controls (minimum set):
- Scene preset: `confined | populated | open | derelict`
- Scene phase: `approach | engage | aftermath`
- Party band: `low | mid | high | unknown`
- Rarity mode: `calm | normal | spiky`
- Morphology sliders:
  - confinement (0..1)
  - connectivity (0..1)
  - visibility (0..1)
- Include tags (text or multiselect from discovered tags)
- Exclude tags (text or multiselect)
- Content pack path (default: `data/core_complications.json`)
- Seed (int)
- Batch count (default: 50; options 10/50/200)

State controls:
- Tick mode: `none | turn | scene`
- Ticks (int)
- Load state from file (optional path)
- Save state to file (optional path)

### R2 – Run controls
- Button: **Generate 1**
- Button: **Generate N** (N from batch count)
- Optional: **Reset session** (clears displayed events and local state)

### R3 – Event display
For each generated event, show:
- Title + event_id
- Severity + cutoff applied + cutoff resolution
- Tags
- Effect vector
- Fiction prompt + choices
- Followups
- Expand/collapse:
  - RNG trace
  - Full JSON payload

### R4 – Diagnostics (batch runs)
For last batch (or rolling window), show:
- Severity histogram or bucket counts (1–3, 4–6, 7–10)
- Cutoff rate (% events with cutoff applied)
- Top tags frequency
- Top event_id frequency (to spot repetition)

### R5 – Determinism
Given the same seed + inputs + pack, the harness must produce the same output sequence.

### R6 – Safety / failure modes
If filtering results in no candidate entries:
- Show a clear error explaining what to loosen (tags/env/phase/cooldowns)
- Do not crash the app session

---

## 4) Non-Functional Requirements

- Keep changes small and debuggable (engine rules).
- No engine logic embedded in UI code.
- Harness must run locally with minimal dependencies.
- No "magic state": any state mutation is explicit and displayed.

---

## 5) Architecture

### 5.1 Component Overview
- `spar_engine` (existing):
  - engine core (`generate_event`)
  - state helpers (`apply_state_delta`, `tick_state`)
  - content loader (`load_pack`)
  - RNG (`TraceRNG`)
- `streamlit_harness/app.py` (new):
  - UI controls
  - session state management
  - orchestration calls into `spar_engine`
  - rendering + diagnostics

### 5.2 Data Flow
1. User configures inputs in sidebar.
2. Harness loads content pack (once per change).
3. On run:
   - (optional) tick state
   - create RNG with seed
   - call `generate_event(...)`
   - apply `apply_state_delta(...)` to session state
   - append event to displayed history
4. Batch runs repeat step 3 N times and compute diagnostics.

### 5.3 Session State Model (Streamlit)
Use `st.session_state` keys:
- `engine_state` (EngineState as dict or dataclass)
- `events` (list of EngineEvent dicts)
- `last_batch_events` (subset for diagnostics)
- `pack_entries` (loaded pack)
- `derived_tags` (tag vocabulary from pack)

Persisted state files use the same JSON schema as the CLI:
```json
{
  "clocks": {...},
  "recent_event_ids": [...],
  "tag_cooldowns": {...},
  "flags": {...}
}
```

### 5.4 Minimal Dependency Plan
- Add `streamlit` for harness only.
- Keep engine package dependency-free for now.

---

## 6) Acceptance Criteria (v0.1 harness)

- Can generate a single event with default settings and see a readable card.
- Can generate 50 events and see diagnostics (severity distribution + cutoff rate).
- Seeded runs are stable and repeatable.
- State can be loaded from a file, advanced, and saved back out.
- Harness never embeds system mechanics, only shows engine outputs.

---

## 7) Next Steps After v0.1 Harness

- Add a "pack browser" (read-only metadata and tag explorer).
- Add a "tuning snapshot" export (inputs + seed + summary stats).
- Add charts for tag frequency and cutoff resolution breakdown.
- Only after engine feel stabilizes: begin React prototype for product UI.
