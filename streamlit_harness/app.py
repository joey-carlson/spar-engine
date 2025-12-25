from __future__ import annotations

# Ensure repo root is on sys.path when running via `streamlit run`.
import sys
from pathlib import Path as _Path
_REPO_ROOT = _Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from collections import Counter
import json
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st

from spar_engine.content import load_pack
from spar_engine.engine import generate_event
from spar_engine.models import Constraints, SceneContext, SelectionContext
from spar_engine.rng import TraceRNG
from spar_engine.state import apply_state_delta, tick_state

from streamlit_harness.harness_state import HarnessState


DEFAULT_PACK = "data/core_complications.json"
SCENARIOS_DIR = Path("scenarios")
CONFIG_FILE = Path(".streamlit_harness_config.json")


def load_config() -> Dict[str, Any]:
    """Load persistent configuration from disk."""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            pass
    # Return defaults if config doesn't exist or is invalid
    return {
        "scenario_output_path": "results/scenario_output.json",
        "template_save_path": "scenarios/my_scenario.json",
        "report_save_path": "results/suite_report.json",
    }


def save_config(config: Dict[str, Any]) -> None:
    """Save persistent configuration to disk."""
    try:
        CONFIG_FILE.write_text(json.dumps(config, indent=2))
    except Exception:
        pass  # Fail silently - don't disrupt UX if config save fails


def split_csv(v: str) -> List[str]:
    if not v:
        return []
    return [x.strip() for x in v.split(",") if x.strip()]


def scene_preset_values(preset: str) -> Dict[str, Any]:
    preset = (preset or "").strip().lower()
    if preset == "dungeon":
        return {"env": ["dungeon"], "confinement": 0.8, "connectivity": 0.3, "visibility": 0.6}
    if preset == "city":
        return {"env": ["city"], "confinement": 0.4, "connectivity": 0.8, "visibility": 0.7}
    if preset == "wilderness":
        return {"env": ["wilderness"], "confinement": 0.3, "connectivity": 0.5, "visibility": 0.4}
    if preset == "ruins":
        return {"env": ["ruins"], "confinement": 0.6, "connectivity": 0.4, "visibility": 0.5}
    return {"env": ["dungeon"], "confinement": 0.5, "connectivity": 0.5, "visibility": 0.5}


def get_hs() -> HarnessState:
    """Get or initialize the harness state singleton."""
    if "hs" not in st.session_state or not isinstance(st.session_state.hs, HarnessState):
        st.session_state.hs = HarnessState()
    return st.session_state.hs


def init_persistent_paths() -> None:
    """Initialize persistent path state from config file."""
    if "paths_initialized" not in st.session_state:
        config = load_config()
        st.session_state.scenario_output_path = config.get("scenario_output_path", "results/scenario_output.json")
        st.session_state.template_save_path = config.get("template_save_path", "scenarios/my_scenario.json")
        st.session_state.report_save_path = config.get("report_save_path", "results/suite_report.json")
        st.session_state.paths_initialized = True


def update_persistent_path(key: str, value: str) -> None:
    """Update a persistent path in both session state and config file."""
    st.session_state[key] = value
    config = load_config()
    config[key] = value
    save_config(config)


def load_entries(pack_path: str):
    p = Path(pack_path)
    if not p.exists():
        raise FileNotFoundError(f"Pack not found: {pack_path}")
    return load_pack(p)


def derive_tag_vocab(entries) -> List[str]:
    s = set()
    for e in entries:
        for t in e.tags:
            s.add(t)
    return sorted(s)


def event_to_dict(ev) -> Dict[str, Any]:
    d = ev.__dict__.copy()
    d["effect_vector"] = ev.effect_vector.__dict__
    d["fiction"] = ev.fiction.__dict__
    d["state_delta"] = ev.state_delta.__dict__
    return d


def summarize_events(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    severities = [int(e.get("severity", 0)) for e in events]
    cutoff_count = sum(1 for e in events if e.get("cutoff_applied"))

    buckets = {"1-3": 0, "4-6": 0, "7-10": 0}
    for s in severities:
        if s <= 3:
            buckets["1-3"] += 1
        elif s <= 6:
            buckets["4-6"] += 1
        else:
            buckets["7-10"] += 1

    tag_counts = Counter()
    id_counts = Counter()
    resolution_counts = Counter()
    for e in events:
        id_counts[e.get("event_id")] += 1
        resolution_counts[str(e.get("cutoff_resolution", "none"))] += 1
        for t in e.get("tags", []) or []:
            tag_counts[t] += 1

    return {
        "n": len(events),
        "cutoff_rate": (cutoff_count / max(1, len(events))),
        "severity_buckets": buckets,
        "severity_min": min(severities) if severities else None,
        "severity_max": max(severities) if severities else None,
        "severity_avg": (sum(severities) / len(severities)) if severities else None,
        "top_tags": tag_counts.most_common(15),
        "top_event_ids": id_counts.most_common(15),
        "cutoff_resolutions": dict(resolution_counts),
    }


def diagnostics(events: List[Dict[str, Any]]) -> None:
    if not events:
        st.info("No batch to analyze yet.")
        return

    s = summarize_events(events)
    st.write("**Cutoff rate:**", f"{s['cutoff_rate']*100:.1f}%")
    st.write("**Severity buckets:**")
    st.bar_chart(s["severity_buckets"])
    st.write("**Cutoff resolutions:**")
    st.write(s["cutoff_resolutions"])
    st.write("**Top tags:**")
    st.write(dict(s["top_tags"]))
    st.write("**Top event IDs:**")
    st.write(dict(s["top_event_ids"]))


def event_card(e: Dict[str, Any]) -> None:
    st.subheader(e["title"])
    st.caption(
        f"id={e['event_id']} | severity={e['severity']} | cutoff={e['cutoff_applied']} ({e['cutoff_resolution']})"
    )
    st.write("**Tags:**", ", ".join(e.get("tags", [])))
    st.write("**Effects:**", e.get("effect_vector", {}))

    fic = e.get("fiction", {}) or {}
    if fic.get("prompt"):
        st.write(f"**Prompt:** {fic['prompt']}")
    choices = fic.get("immediate_choice", []) or []
    if choices:
        st.write("**Choices:**")
        for c in choices:
            st.write(f"- {c}")

    followups = e.get("followups", []) or []
    if followups:
        st.write("**Followups:**", followups)

    with st.expander("JSON"):
        st.code(json.dumps(e, indent=2), language="json")


def run_batch(
    *,
    scene: SceneContext,
    selection: SelectionContext,
    entries,
    seed: int,
    n: int,
    starting_engine_state,
    tick_between: bool,
    ticks_between: int,
    verbose: bool,
) -> Dict[str, Any]:
    state = starting_engine_state
    rng = TraceRNG(seed=int(seed))
    events: List[Dict[str, Any]] = []

    for idx in range(int(n)):
        if idx > 0:
            # Always tick at least 1 to prevent cooldown accumulation
            # Without ticking, tag cooldowns never expire and content exhausts quickly
            tick_amount = max(1, int(ticks_between) if tick_between else 1)
            state = tick_state(state, ticks=tick_amount)

        rng.trace.clear()
        ev = generate_event(scene, state, selection, entries, rng)
        state = apply_state_delta(state, ev.state_delta)
        events.append(event_to_dict(ev))

    summary = summarize_events(events)
    return {
        "seed": int(seed),
        "n": int(n),
        "final_state": state.__dict__,
        "summary": summary,
        "events": events if verbose else None,
        "events_sample": None if verbose else events[:10],
    }


def report_to_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"# Scenario Suite Report: {report.get('suite')}")
    lines.append("")
    lines.append(f"- Batch N: {report.get('batch_n')}")
    lines.append(f"- Base seed: {report.get('base_seed')}")
    lines.append(f"- Presets: {', '.join(report.get('presets', []))}")
    lines.append(f"- Phases: {', '.join(report.get('phases', []))}")
    lines.append(f"- Rarity modes: {', '.join(report.get('rarity_modes', []))}")
    lines.append(f"- Include tags: `{report.get('include_tags')}`")
    lines.append(f"- Exclude tags: `{report.get('exclude_tags')}`")
    lines.append(f"- Tick between: {report.get('tick_between')} (ticks={report.get('ticks_between')})")
    lines.append(f"- Verbose events included: {report.get('verbose')}")
    lines.append("")

    for run in report.get("runs", []):
        preset = run.get("preset")
        phase = run.get("phase")
        rm = run.get("rarity_mode")
        seed = run.get("seed")
        summary = run["result"]["summary"]

        lines.append(f"## {preset} / {phase} / {rm}  (seed={seed})")
        lines.append(f"- Cutoff rate: {summary['cutoff_rate']*100:.1f}%")
        lines.append(f"- Cutoff resolutions: {summary.get('cutoff_resolutions', {})}")
        lines.append(f"- Severity buckets: {summary['severity_buckets']}")
        lines.append(
            f"- Severity avg: {summary['severity_avg']:.2f} "
            f"(min={summary['severity_min']}, max={summary['severity_max']})"
        )
        lines.append(f"- Top tags: {summary['top_tags'][:8]}")
        lines.append(f"- Top event IDs: {summary['top_event_ids'][:8]}")
        lines.append("")

    return "\n".join(lines)


def load_scenario_json(file_content: str) -> Dict[str, Any]:
    """Load and validate a scenario JSON."""
    try:
        scenario = json.loads(file_content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")
    
    # Validate required fields
    required = ["name", "presets", "phases", "rarity_modes", "batch_size", "base_seed"]
    missing = [f for f in required if f not in scenario]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    
    return scenario


def get_builtin_scenarios() -> List[Dict[str, Any]]:
    """Load all built-in scenarios from scenarios/ directory."""
    scenarios = []
    if not SCENARIOS_DIR.exists():
        return scenarios
    
    for json_file in SCENARIOS_DIR.glob("*.json"):
        try:
            content = json_file.read_text()
            scenario = json.loads(content)
            scenario["_source_file"] = str(json_file)
            scenarios.append(scenario)
        except Exception:
            continue  # Skip invalid files
    
    return sorted(scenarios, key=lambda s: s.get("name", ""))


def save_report_to_path(report: Dict[str, Any], path: str) -> tuple[bool, str]:
    """Save report JSON to specified file path.
    
    Returns: (success: bool, message: str)
    """
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, indent=2))
        return True, f"Report saved to {path}"
    except Exception as e:
        return False, f"Failed to save: {str(e)}"


def run_scenario_from_json(
    scenario: Dict[str, Any],
    entries,
    engine_state_class,
) -> Dict[str, Any]:
    """Execute a scenario definition and return results."""
    report: Dict[str, Any] = {
        "suite": scenario.get("name", "Custom scenario"),
        "batch_n": int(scenario["batch_size"]),
        "base_seed": int(scenario["base_seed"]),
        "presets": scenario["presets"],
        "phases": scenario["phases"],
        "rarity_modes": scenario["rarity_modes"],
        "include_tags": scenario.get("include_tags", ""),
        "exclude_tags": scenario.get("exclude_tags", ""),
        "tick_between": scenario.get("tick_between", True),
        "ticks_between": scenario.get("ticks_between", 1),
        "verbose": scenario.get("verbose", False),
        "runs": [],
    }
    
    run_idx = 0
    for preset_name in scenario["presets"]:
        pv = scene_preset_values(preset_name)
        for phase in scenario["phases"]:
            for rarity_mode in scenario["rarity_modes"]:
                run_idx += 1
                scene = SceneContext(
                    scene_id=f"scenario:{scenario['name']}:{preset_name}:{phase}:{rarity_mode}",
                    scene_phase=phase,  # type: ignore
                    environment=list(pv["env"]),
                    tone=["debug"],
                    constraints=Constraints(
                        confinement=float(pv["confinement"]),
                        connectivity=float(pv["connectivity"]),
                        visibility=float(pv["visibility"]),
                    ),
                    party_band="unknown",
                    spotlight=["debug"],
                )
                selection = SelectionContext(
                    enabled_packs=["core_complications"],
                    include_tags=split_csv(scenario.get("include_tags", "")),
                    exclude_tags=split_csv(scenario.get("exclude_tags", "")),
                    factions_present=[],
                    rarity_mode=rarity_mode,  # type: ignore
                )
                seed = int(scenario["base_seed"]) + run_idx
                result = run_batch(
                    scene=scene,
                    selection=selection,
                    entries=entries,
                    seed=seed,
                    n=int(scenario["batch_size"]),
                    starting_engine_state=engine_state_class.default(),
                    tick_between=bool(scenario.get("tick_between", True)),
                    ticks_between=int(scenario.get("ticks_between", 1)),
                    verbose=bool(scenario.get("verbose", False)),
                )
                report["runs"].append({
                    "preset": preset_name,
                    "phase": phase,
                    "rarity_mode": rarity_mode,
                    "seed": seed,
                    "result": result,
                })
    
    return report


def main() -> None:
    st.set_page_config(page_title="SPAR Engine Harness v0.1", layout="wide")
    init_persistent_paths()
    hs = get_hs()

    st.title("SPAR Engine Harness v0.1")
    st.caption("Debug-first harness for tuning the encounter complications engine. Not a product UI.")

    # ---------------- Sidebar ----------------
    with st.sidebar:
        st.header("Inputs")

        preset = st.selectbox("Scene preset", ["dungeon", "city", "wilderness", "ruins"], index=0)
        pv = scene_preset_values(preset)

        scene_id = st.text_input("Scene ID", value="harness")
        scene_phase = st.selectbox("Scene phase", ["approach", "engage", "aftermath"], index=1)
        party_band = st.selectbox("Party band", ["low", "mid", "high", "unknown"], index=3)
        rarity_mode = st.selectbox("Rarity mode", ["calm", "normal", "spiky"], index=1)

        confinement = st.slider("Confinement", 0.0, 1.0, float(pv["confinement"]), 0.05)
        connectivity = st.slider("Connectivity", 0.0, 1.0, float(pv["connectivity"]), 0.05)
        visibility = st.slider("Visibility", 0.0, 1.0, float(pv["visibility"]), 0.05)

        pack_path = st.text_input("Content pack path", value=DEFAULT_PACK)
        seed = st.number_input("Seed", min_value=0, max_value=10**9, value=42, step=1)

        # Canonical batch size lives on HarnessState (never a local variable)
        hs.batch_n = st.selectbox(
            "Batch count",
            [10, 50, 200],
            index=[10, 50, 200].index(hs.batch_n) if hs.batch_n in [10, 50, 200] else 1,
        )

        tick_mode = st.selectbox("Tick mode", ["none", "turn", "scene"], index=0)
        ticks = st.number_input("Ticks", min_value=0, max_value=100, value=0, step=1)

        st.caption("Batch runs are sequential by default (treat each generated event as a 'turn').")
        tick_between = st.checkbox("Tick between events in batch", value=True)
        ticks_between_events = st.number_input("Ticks between events", min_value=0, max_value=10, value=1, step=1)

        include_tags_text = st.text_input(
            "Include tags (CSV)",
            value="hazard,reinforcements,time_pressure,social_friction,visibility,mystic,attrition,terrain,positioning,opportunity,information",
        )
        exclude_tags_text = st.text_input("Exclude tags (CSV)", value="")

        st.divider()
        st.subheader("State")

        if st.button("Reset session state"):
            hs.reset()
            st.toast("Session reset.", icon="✅")

        st.text_area(
            "Current state (read-only)",
            value=json.dumps(hs.engine_state.__dict__, indent=2),
            height=180,
        )

        st.divider()
        st.subheader("Pack")

        if st.button("Load pack") or not hs.pack_entries:
            try:
                entries = load_entries(pack_path)
                hs.pack_entries = entries
                hs.tag_vocab = derive_tag_vocab(entries)
                st.toast(f"Loaded {len(entries)} entries", icon="✅")
            except Exception as ex:
                st.error(str(ex))

        if hs.tag_vocab:
            st.caption("Pack tags:")
            st.write(hs.tag_vocab)

    entries = hs.pack_entries
    if not entries:
        st.info("Load a content pack from the sidebar to begin.")
        return

    scene = SceneContext(
        scene_id=scene_id,
        scene_phase=scene_phase,  # type: ignore
        environment=list(pv["env"]),
        tone=["debug"],
        constraints=Constraints(confinement=confinement, connectivity=connectivity, visibility=visibility),
        party_band=party_band,  # type: ignore
        spotlight=["debug"],
    )
    selection = SelectionContext(
        enabled_packs=["core_complications_v0_1"],
        include_tags=split_csv(include_tags_text),
        exclude_tags=split_csv(exclude_tags_text),
        factions_present=[],
        rarity_mode=rarity_mode,  # type: ignore
    )

    tabs = st.tabs(["Events", "Scenarios"])

    with tabs[0]:
        colA, colB = st.columns([2, 1])

        with colA:
            st.header("Events")
            btn1, btnN = st.columns(2)
            run_one = btn1.button("Generate 1", use_container_width=True)
            run_many = btnN.button(f"Generate {hs.batch_n}", use_container_width=True)

            if run_one or run_many:
                n = 1 if run_one else int(hs.batch_n)

                if tick_mode != "none" and int(ticks) > 0:
                    hs.engine_state = tick_state(hs.engine_state, ticks=int(ticks))

                rng = TraceRNG(seed=int(seed))

                batch_events: List[Dict[str, Any]] = []
                for idx in range(n):
                    if idx > 0 and tick_between and int(ticks_between_events) > 0:
                        hs.engine_state = tick_state(hs.engine_state, ticks=int(ticks_between_events))

                    rng.trace.clear()
                    ev = generate_event(scene, hs.engine_state, selection, entries, rng)
                    hs.engine_state = apply_state_delta(hs.engine_state, ev.state_delta)

                    d = event_to_dict(ev)
                    batch_events.append(d)
                    hs.events.insert(0, d)

                hs.last_batch = batch_events

            if hs.events:
                for e in hs.events[:25]:
                    with st.container(border=True):
                        event_card(e)
            else:
                st.info("No events generated yet.")

        with colB:
            st.header("Diagnostics")
            diagnostics(hs.last_batch)

    with tabs[1]:
        st.header("Scenario Runner (Multi-run)")
        st.caption("Run predefined multi-run suites and download a debug report for tuning.")
        
        # JSON Scenario Import/Export Section
        st.subheader("JSON Scenario Import/Export")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.caption("**Import Scenario**")
            
            # File uploader
            uploaded_file = st.file_uploader("Upload scenario JSON", type=['json'])
            
            # Library dropdown
            builtin_scenarios = get_builtin_scenarios()
            # Filter out scenarios without names and create dropdown list
            valid_scenarios = [s for s in builtin_scenarios if "name" in s]
            scenario_names = ["-- Select from library --"] + [s["name"] for s in valid_scenarios]
            selected_scenario_name = st.selectbox("Or select from library", scenario_names)
            
            # Load scenario
            loaded_scenario = None
            if uploaded_file is not None:
                try:
                    content = uploaded_file.read().decode('utf-8')
                    loaded_scenario = load_scenario_json(content)
                    st.success(f"Loaded: {loaded_scenario['name']}")
                except Exception as e:
                    st.error(f"Failed to load scenario: {e}")
            elif selected_scenario_name != "-- Select from library --":
                matching = [s for s in valid_scenarios if s["name"] == selected_scenario_name]
                if matching:
                    loaded_scenario = matching[0]
                    st.success(f"Loaded: {loaded_scenario['name']}")
            
            # Display loaded scenario details
            if loaded_scenario:
                with st.expander("Scenario Details", expanded=True):
                    st.write(f"**Name**: {loaded_scenario['name']}")
                    st.write(f"**Description**: {loaded_scenario.get('description', 'N/A')}")
                    st.write(f"**Presets**: {', '.join(loaded_scenario['presets'])}")
                    st.write(f"**Phases**: {', '.join(loaded_scenario['phases'])}")
                    st.write(f"**Rarity Modes**: {', '.join(loaded_scenario['rarity_modes'])}")
                    st.write(f"**Batch Size**: {loaded_scenario['batch_size']}")
                    st.write(f"**Base Seed**: {loaded_scenario['base_seed']}")
                    st.write(f"**Tick Between**: {loaded_scenario.get('tick_between', True)}")
                    st.write(f"**Ticks Between**: {loaded_scenario.get('ticks_between', 1)}")
        
        with col2:
            st.caption("**Export Results**")
            
            # Generate default filename based on loaded scenario
            if loaded_scenario:
                # Get the scenario name for comparison
                scenario_name = loaded_scenario.get("name", "scenario")
                
                # Check if this is a different scenario from last time
                if "last_loaded_scenario" not in st.session_state or st.session_state.last_loaded_scenario != scenario_name:
                    # New scenario selected - generate fresh filename with timestamp
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    # Use output_basename if provided, otherwise sanitize scenario name
                    if "output_basename" in loaded_scenario and loaded_scenario["output_basename"]:
                        basename = loaded_scenario["output_basename"]
                    else:
                        basename = scenario_name.lower().replace(' ', '_').replace('/', '_').replace('\\', '_')
                    
                    # Truncate basename if total filename would be too long (>255 chars)
                    # Keep timestamp intact, truncate basename if needed
                    max_filename_length = 255
                    path_prefix = "results/"
                    extension = ".json"
                    available_length = max_filename_length - len(path_prefix) - len(timestamp) - 1 - len(extension)  # -1 for underscore
                    
                    if len(basename) > available_length:
                        basename = basename[:available_length]
                    
                    new_path = f"{path_prefix}{basename}_{timestamp}{extension}"
                    
                    # Update persistent config and session tracking
                    update_persistent_path("scenario_output_path", new_path)
                    st.session_state.last_loaded_scenario = scenario_name
            
            st.caption(f"📁 Working directory: {Path.cwd()}")
            output_path = st.text_input(
                "Save results to path",
                value=st.session_state.scenario_output_path,
                help="Full file path where results JSON will be saved (persisted between sessions). Relative paths are from working directory shown above.",
                key="output_path_input"
            )
            
            # Update persistent config when user modifies path
            if output_path and output_path != st.session_state.scenario_output_path:
                update_persistent_path("scenario_output_path", output_path)
            
            run_and_save = st.button(
                "Run and Save Scenario",
                type="primary",
                disabled=(loaded_scenario is None),
                use_container_width=True
            )
            
            if run_and_save and loaded_scenario:
                try:
                    with st.spinner(f"Running scenario: {loaded_scenario['name']}..."):
                        report = run_scenario_from_json(
                            loaded_scenario,
                            entries,
                            hs.engine_state.__class__
                        )
                        hs.last_suite_report = report
                    
                    # Save to specified path
                    if output_path:
                        success, message = save_report_to_path(report, output_path)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                    else:
                        st.error("Please specify an output path")
                        
                except Exception as ex:
                    st.error(f"Scenario execution failed: {str(ex)}")
        
        st.divider()
        
        # Existing hardcoded suite section
        st.subheader("Hardcoded Suites (Legacy)")
        
        suite = st.selectbox(
            "Suite",
            [
                "Presets × Engage × Normal (quick)",
                "Presets × (Approach/Engage/Aftermath) × Normal",
                "Presets × Engage × (Calm/Normal/Spiky)",
            ],
            index=0,
        )

        presets = ["dungeon", "city", "wilderness", "ruins"]

        if suite == "Presets × Engage × Normal (quick)":
            phases = ["engage"]
            rarity_modes = ["normal"]
        elif suite == "Presets × (Approach/Engage/Aftermath) × Normal":
            phases = ["approach", "engage", "aftermath"]
            rarity_modes = ["normal"]
        else:
            phases = ["engage"]
            rarity_modes = ["calm", "normal", "spiky"]

        batchN = st.number_input("Batch size per run", min_value=10, max_value=500, value=int(hs.batch_n), step=10)
        base_seed = st.number_input("Base seed", min_value=0, max_value=10**9, value=1000, step=1)

        include_tags_suite = st.text_input("Include tags (CSV)", value=include_tags_text)
        exclude_tags_suite = st.text_input("Exclude tags (CSV)", value=exclude_tags_text)

        tick_between_suite = st.checkbox("Tick between events in each batch", value=True)
        ticks_between_suite = st.number_input("Ticks between events", min_value=0, max_value=10, value=1, step=1)

        verbose_report = st.checkbox("Include full event lists in report", value=False)
        
        run_suite = st.button("Run suite", type="primary")
        
        # Save current settings as template
        st.subheader("Save Current Settings as Template")
        
        # Generate default path with timestamp for current suite
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_basename = suite.lower().replace(' ', '_').replace('×', 'x').replace('(', '').replace(')', '')
        default_template_path = f"scenarios/{default_basename}_{timestamp}.json"
        
        # Update persistent config with new default
        if st.session_state.template_save_path != default_template_path:
            update_persistent_path("template_save_path", default_template_path)
        
        st.caption(f"📁 Working directory: {Path.cwd()}")
        template_path = st.text_input(
            "Save template to path",
            value=st.session_state.template_save_path,
            help="Full file path where scenario JSON will be saved. Relative paths are from working directory shown above.",
            key="template_path_input"
        )
        
        # Update persistent config
        if template_path and template_path != st.session_state.template_save_path:
            update_persistent_path("template_save_path", template_path)
        
        save_template = st.button("Save as Template", use_container_width=True)
        
        if save_template:
            # Export current settings as scenario JSON
            current_scenario = {
                "schema_version": "1.0",
                "name": suite,
                "description": f"Exported from hardcoded suite: {suite}",
                "output_basename": default_basename,
                "presets": presets,
                "phases": phases,
                "rarity_modes": rarity_modes,
                "batch_size": int(batchN),
                "base_seed": int(base_seed),
                "include_tags": str(include_tags_suite),
                "exclude_tags": str(exclude_tags_suite),
                "tick_between": bool(tick_between_suite),
                "ticks_between": int(ticks_between_suite),
                "verbose": bool(verbose_report),
            }
            
            # Reuse save_report_to_path function (no code duplication)
            if template_path:
                success, message = save_report_to_path(current_scenario, template_path)
                if success:
                    st.success(message)
                else:
                    st.error(message)
            else:
                st.error("Please specify a template path")
        if run_suite:
            try:
                suite_report: Dict[str, Any] = {
                    "suite": suite,
                    "batch_n": int(batchN),
                    "base_seed": int(base_seed),
                    "presets": presets,
                    "phases": phases,
                    "rarity_modes": rarity_modes,
                    "include_tags": str(include_tags_suite),
                    "exclude_tags": str(exclude_tags_suite),
                    "tick_between": bool(tick_between_suite),
                    "ticks_between": int(ticks_between_suite),
                    "verbose": bool(verbose_report),
                    "runs": [],
                }

                run_idx = 0
                for preset_name in presets:
                    pv2 = scene_preset_values(preset_name)
                    for ph in phases:
                        for rm in rarity_modes:
                            run_idx += 1
                            scene2 = SceneContext(
                                scene_id=f"suite:{suite}:{preset_name}:{ph}:{rm}",
                                scene_phase=ph,  # type: ignore
                                environment=list(pv2["env"]),
                                tone=["debug"],
                                constraints=Constraints(
                                    confinement=float(pv2["confinement"]),
                                    connectivity=float(pv2["connectivity"]),
                                    visibility=float(pv2["visibility"]),
                                ),
                                party_band="unknown",
                                spotlight=["debug"],
                            )
                            selection2 = SelectionContext(
                                enabled_packs=["core_complications_v0_1"],
                                include_tags=split_csv(include_tags_suite),
                                exclude_tags=split_csv(exclude_tags_suite),
                                factions_present=[],
                                rarity_mode=rm,  # type: ignore
                            )
                            seed2 = int(base_seed) + run_idx
                            result = run_batch(
                                scene=scene2,
                                selection=selection2,
                                entries=entries,
                                seed=seed2,
                                n=int(batchN),
                                starting_engine_state=hs.engine_state.__class__.default(),
                                tick_between=bool(tick_between_suite),
                                ticks_between=int(ticks_between_suite),
                                verbose=bool(verbose_report),
                            )
                            suite_report["runs"].append(
                                {
                                    "preset": preset_name,
                                    "phase": ph,
                                    "rarity_mode": rm,
                                    "seed": seed2,
                                    "result": result,
                                }
                            )

                hs.last_suite_report = suite_report
                st.success("Suite completed.")
            except Exception as ex:
                st.error(str(ex))

        report = hs.last_suite_report
        if report:
            st.subheader("Suite Summary")

            rows = []
            for run in report.get("runs", []):
                s = run["result"]["summary"]
                rows.append(
                    {
                        "preset": run["preset"],
                        "phase": run["phase"],
                        "rarity_mode": run["rarity_mode"],
                        "cutoff_rate_pct": round(s["cutoff_rate"] * 100.0, 2),
                        "cutoff_resolutions": s.get("cutoff_resolutions", {}),
                        "bucket_1_3": s["severity_buckets"]["1-3"],
                        "bucket_4_6": s["severity_buckets"]["4-6"],
                        "bucket_7_10": s["severity_buckets"]["7-10"],
                        "severity_avg": round(s["severity_avg"], 2) if s["severity_avg"] is not None else None,
                        "severity_min": s["severity_min"],
                        "severity_max": s["severity_max"],
                    }
                )
            st.dataframe(rows, use_container_width=True, hide_index=True)
            
            st.subheader("Save Report")
            
            # Generate default path with timestamp from suite name
            if report:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                suite_basename = report.get("suite", "suite_report").lower().replace(' ', '_').replace('×', 'x').replace('(', '').replace(')', '')
                default_report_path = f"results/{suite_basename}_{timestamp}.json"
                
                # Update persistent config with new default
                if st.session_state.report_save_path != default_report_path:
                    update_persistent_path("report_save_path", default_report_path)
            
            st.caption(f"📁 Working directory: {Path.cwd()}")
            report_path = st.text_input(
                "Save report to path",
                value=st.session_state.report_save_path,
                help="Full file path where report JSON will be saved. Relative paths are from working directory shown above.",
                key="report_path_input"
            )
            
            # Update persistent config
            if report_path and report_path != st.session_state.report_save_path:
                update_persistent_path("report_save_path", report_path)
            
            save_report = st.button("Save Report", use_container_width=True)
            
            if save_report:
                if report_path:
                    success, message = save_report_to_path(report, report_path)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
                else:
                    st.error("Please specify a report path")


if __name__ == "__main__":
    main()
