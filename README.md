# SPAR Tool Engine (v0.1) – Encounter Complications

This is an engine-first prototype implementing the **SPAR Engine v0.1 Contract** for encounter complications.

## What this includes
- A system-agnostic event generator (`spar_engine.generate_event`)
- Seedable, inspectable RNG wrapper
- Truncated heavy-tail severity sampling + scene-based caps + cutoff handling
- Tag-based content filtering with cooldowns (anti-repetition)
- Minimal starter content pack
- Pytest suite (gist + unit tests)

## Run tests
```sh
python -m pytest
```

## Run Streamlit UI (Rapid Prototyping)
```sh
# Install dependencies (recommended in virtual environment or with pipx)
pip install streamlit
# OR using pipx (avoids dependency conflicts)
pipx install streamlit

# Run the interactive web interface
streamlit run app.py
```

The Streamlit app provides an interactive interface for testing engine parameters and visualizing generated complications.

## Minimal usage
```py
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
sel = SelectionContext(
    enabled_packs=["core_complications_v0_1"],
    include_tags=["hazard","reinforcements","time_pressure","social_friction"],
    exclude_tags=[],
    factions_present=[],
    rarity_mode="normal",
)

event = generate_event(scene, state, sel, entries, rng)
print(event.title, event.severity, event.tags)
```


---

## Running from the CLI

A thin CLI wrapper is provided at the repo root: `engine.py`.

### Examples (zsh)

Generate 1 event (default settings):
```zsh
python3 engine.py
```

Set scene inputs explicitly:
```zsh
python3 engine.py \
  --scene myscene \
  --scene-phase engage \
  --env confined \
  --tone gritty \
  --spotlight combat \
  --party-band mid \
  --confinement 0.8 --connectivity 0.2 --visibility 0.7 \
  --rarity-mode normal \
  --seed 42
```

Generate multiple events:
```zsh
python3 engine.py --count 5 --seed 123
```

Force a specific event by `event_id`:
```zsh
python3 engine.py --event-id hazard_smoke_01 --count 1
```

Machine-readable output (one JSON object per line):
```zsh
python3 engine.py --count 3 --format jsonl
```

Include RNG trace (debugging):
```zsh
python3 engine.py --show-trace --format jsonl --count 1
```


### Stateful CLI usage

Persist engine state across runs using `--state-in` and `--state-out`:

```zsh
python3 engine.py --state-in state.json --state-out state.json --count 1 --seed 42
```

Advance cooldowns between calls (tick mode):

```zsh
python3 engine.py --state-in state.json --state-out state.json --tick-mode turn --ticks 1 --count 1
```

Use a scene preset (sets sensible morphology defaults):

```zsh
python3 engine.py --scene-preset confined --scene-phase engage --count 1
```

See all options:
```zsh
python3 engine.py --help
```

### Sample Commands for Testing System Knobs

These examples demonstrate how different parameter combinations affect generation. Each command includes a fixed seed for reproducible results.

**Default balanced scene:**
```zsh
python3 engine.py --seed 123
```
*Expected: Low-moderate severity events with balanced effects*

**High confinement (tight, claustrophobic space):**
```zsh
python3 engine.py --confinement 0.9 --connectivity 0.1 --visibility 0.8 --scene-phase engage --seed 456
```
*Expected: Higher severity, more positioning/time pressure effects*

**Spiky rarity mode (unpredictable events):**
```zsh
python3 engine.py --rarity-mode spiky --scene-phase approach --env open --seed 789
```
*Expected: Greater severity variation, more extreme outcomes*

**City social encounter with low party:**
```zsh
python3 engine.py --env city --party-band low --include-tags social_friction,visibility --scene-phase engage --seed 101
```
*Expected: Social complications, bystander effects, heat buildup*

**Industrial confined with high visibility:**
```zsh
python3 engine.py --env industrial,confined --visibility 0.9 --rarity-mode normal --spotlight combat --seed 202
```
*Expected: Hazard-heavy events, reinforcement possibilities*

**Multiple events to see distribution:**
```zsh
python3 engine.py --count 5 --confinement 0.8 --rarity-mode spiky --seed 303
```
*Expected: Mix of severities showing heavy-tail distribution*

---

## Streamlit Debug Harness (v0.1)

A debug-first Streamlit harness is provided in `streamlit_harness/` to exercise the engine and visualize diagnostics.

### Run (zsh)

```zsh
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r streamlit_harness/requirements.txt

# Editable install should work (package discovery is explicitly configured in pyproject.toml).
# Optional (recommended if you want standard imports):
# pip install -e .
streamlit run streamlit_harness/app.py
```

This harness is intentionally not a product UI. It is a tuning and QA instrument.
