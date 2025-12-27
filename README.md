# SPAR - Campaign Manager & Multi-Generator System v1.0

**Situation, Pressure, and Response** — A living campaign management system with multi-domain narrative generators.

## What is SPAR?

SPAR is a campaign management tool with integrated multi-domain generators for tabletop RPGs. It provides:

- **Campaign Manager**: Multi-campaign state tracking with factions, pressure, heat, scars, and session history
- **Event Generator**: SOC-based complication generator for approach/engage/aftermath phases
- **Loot Generator**: Narrative resource shock system (gains with consequences)
- **Content Pack System**: Extensible, multi-generator content ecosystem
- **Session Workflows**: Prep Queue → Canon flow with rich export capabilities

**Design Philosophy:** System-agnostic, narrative-first, consequence-driven. No item stats, no mechanics rules, no genre lock.

---

## Quick Start

### Installation

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r streamlit_harness/requirements.txt
```

### Launch Campaign Manager

```sh
streamlit run streamlit_harness/app.py
```

This opens the full Campaign Manager UI with:
- Campaign creation and management
- Multi-domain generators (Events, Loot)
- Session finalization wizard
- Markdown export for campaign history

---

## Core Features

### Campaign Manager

**Multi-Campaign Management:**
- Create campaigns with Fast Start (2 clicks to first session) or Structured Setup
- Track living state: pressure, heat, factions, scars
- Campaign ledger with full session history
- Content pack selection per campaign

**Session Workflow:**
1. Generate complications/loot in Generator mode
2. Send to Prep Queue (non-canon)
3. Select items to promote to canon
4. Finalize session with "What Happened" entries
5. Export campaign history or individual sessions

**Faction System:**
- Track attention (0-20) and disposition (-2 to +2)
- Attention bands: dormant, lurking, active, mobilized, overwhelming
- Disposition: hostile, unfriendly, neutral, friendly, allied
- Faction influence affects generator tag nudges

### Multi-Domain Generators

**Event Generator (v1.0):**
- SOC-based severity sampling with heavy-tail distribution
- 107 core complications across approach/engage/aftermath
- Phase-aware content filtering
- Tag-based cooldowns prevent repetition
- Cutoff system converts extreme values to story beats

**Loot Generator (v1.0):**
- Narrative resource shock (gains with consequences)
- 15 core situations + 12 Salvage & Black Market entries
- Emphasizes opportunity paired with obligation/visibility
- Campaign context sensitivity
- Conservative baseline (relieves pressure without breaking campaigns)

**Both generators:**
- Share SOC foundation (Self-Organized Criticality)
- Respect campaign-selected content packs
- Support calm/normal/spiky rarity modes
- Deterministic with seed
- Full test coverage

### Content Pack System

**Multi-Generator Architecture:**
- Packs self-identify with `generator_type` field (event, loot, rumor, npc)
- Backward-compatible with legacy array format
- Campaign-level pack selection (one list, filtered by generator)
- Pack discovery shows type badges in UI

**Available Packs:**
- ⚔️ Core Complications (107 event entries)
- 💰 Core Loot Situations (15 loot entries)
- 💰 Salvage & Black Market (12 loot entries, reference model)

**Authoring:**
- Three templates provided (minimal, thematic, LLM-assisted)
- Full authoring guide in `docs/templates/README.md`
- Packs change narrative voice, not mechanics

---

## Test Suite

```sh
python -m pytest
```

**Coverage:**
- 191 tests total
- Event generation (SOC, cutoffs, adaptive weighting)
- Loot generation (distribution, context sensitivity)
- Campaign mechanics (factions, state, ledger)
- Content loading (multi-pack, backward compatibility)
- Session finalization and export

**Test Philosophy:**
- Tests validate shape and behavior, not exact outcomes
- Wide tolerances allow randomness while catching drift
- Deterministic with seeds for reproducibility

---

## Architecture

### SOC Foundation (Self-Organized Criticality)

Both generators use truncated Pareto distributions for severity sampling:
- Heavy-tail distribution creates emergent drama
- Scene-based caps prevent implausible spikes
- Cutoff system converts extremes to narrative beats

**Key Concept:** Severity measures *instability*, not importance.

### Campaign State Model

```python
CampaignState:
  - campaign_pressure: 0-30 (stable/strained/volatile/critical)
  - heat: 0-20 (quiet/noticed/hunted/exposed)
  - scars: List[Scar] (lasting campaign changes)
  - factions: Dict[str, FactionState] (attention + disposition)
  - total_scenes_run: int
```

### Session Ledger Structure

```python
SessionEntry:
  - session_id: str (unique timestamp-based ID)
  - session_number: int (human-friendly)
  - what_happened: List[str] (N-item dynamic list)
  - manual_entries: List[ManualEntry] (rich metadata)
  - session_notes: Optional[str]
  - metadata: Dict (severity, cutoff rate, tags, scenario)
  - deltas: Dict (pressure/heat changes)
```

---

## Documentation

**For GMs:**
- `docs/PLAY_GUIDE_campaigns.md` - Campaign usage guide
- `docs/templates/README.md` - Content pack authoring

**For Designers:**
- `docs/LOOT_DIAGNOSTICS_GUIDE.md` - Loot tuning and validation
- `docs/CAMPAIGN_RHYTHM_RUNNER_DESIGN.md` - Campaign mechanics
- `docs/DATA_CONTRACT_story_vs_system_v0.1.md` - Export specifications

**For Developers:**
- `docs/engineering_rules.md` - Code standards
- Test files serve as executable specifications

---

## Project Status

**v1.0 Components (Locked):**
- ✅ Event Generator v1.0
- ✅ Loot Generator v1.0
- ✅ Multi-Generator Content Pack System v1.0
- ✅ Campaign Manager v0.2 (faction influence, multi-pack)
- ✅ Session Finalization v0.2 (dynamic N-item, manual entries)

**Future Domains:**
- Rumor generator (infrastructure ready)
- NPC generator (infrastructure ready)

---

## CLI Usage (Engine Direct)

A thin CLI wrapper is provided for direct engine access: `engine.py`

### Basic Usage

```zsh
# Generate 1 event with defaults
python3 engine.py

# Generate with campaign context
python3 engine.py --scene-preset confined --scene-phase engage --seed 123

# Generate batch
python3 engine.py --count 5 --rarity-mode spiky --seed 456

# Machine-readable output
python3 engine.py --count 3 --format jsonl
```

### Stateful Usage

```zsh
# Persist state across runs
python3 engine.py --state-in state.json --state-out state.json --count 1

# Advance cooldowns between calls
python3 engine.py --state-in state.json --state-out state.json --tick-mode turn --ticks 1
```

See `python3 engine.py --help` for all options.

---

## Python API

### Event Generation

```python
from spar_engine.engine import generate_event
from spar_engine.models import SceneContext, Constraints, EngineState, SelectionContext
from spar_engine.rng import TraceRNG
from spar_engine.content import load_pack

entries = load_pack("data/core_complications.json")
rng = TraceRNG(seed=123)

scene = SceneContext(
    scene_id="demo",
    scene_phase="engage",
    environment=["confined"],
    tone=["gritty"],
    constraints=Constraints(confinement=0.8, connectivity=0.2, visibility=0.7),
    party_band="mid",
    spotlight=["combat"],
)

state = EngineState.default()
selection = SelectionContext(
    enabled_packs=["core"],
    include_tags=["hazard", "reinforcements"],
    exclude_tags=[],
    factions_present=[],
    rarity_mode="normal",
)

event = generate_event(scene, state, selection, entries, rng)
print(event.title, event.severity, event.tags)
```

### Loot Generation

```python
from spar_engine.loot import generate_loot

loot_entries = load_pack("data/core_loot_situations.json")
loot = generate_loot(scene, state, selection, loot_entries, rng)
print(loot.title, loot.effect_vector.opportunity, loot.tags)
```

### Multi-Pack Loading

```python
from spar_engine.content import load_packs, load_packs_by_generator_type

# Load multiple packs
all_entries = load_packs([
    "data/core_complications.json",
    "data/core_loot_situations.json"
])

# Load by generator type
loot_only = load_packs_by_generator_type(
    ["data/core_complications.json", "data/core_loot_situations.json"],
    "loot"
)
```

---

## License

MIT
