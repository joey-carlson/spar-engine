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
import random
import time

import streamlit as st

from spar_engine.content import load_pack, load_packs
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
        "scenario_output_path": "scenarios/results/scenario_output.json",
        "template_save_path": "scenarios/my_scenario.json",
        "report_save_path": "scenarios/results/suite_report.json",
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
    if preset == "confined":
        return {"env": ["confined"], "confinement": 0.8, "connectivity": 0.3, "visibility": 0.6}
    if preset == "populated":
        return {"env": ["populated"], "confinement": 0.4, "connectivity": 0.8, "visibility": 0.7}
    if preset == "open":
        return {"env": ["open"], "confinement": 0.3, "connectivity": 0.5, "visibility": 0.4}
    if preset == "derelict":
        return {"env": ["derelict"], "confinement": 0.6, "connectivity": 0.4, "visibility": 0.5}
    return {"env": ["confined"], "confinement": 0.5, "connectivity": 0.5, "visibility": 0.5}


def get_hs() -> HarnessState:
    """Get or initialize the harness state singleton."""
    if "hs" not in st.session_state or not isinstance(st.session_state.hs, HarnessState):
        st.session_state.hs = HarnessState()
    return st.session_state.hs


def init_persistent_paths() -> None:
    """Initialize persistent path state from config file."""
    if "paths_initialized" not in st.session_state:
        config = load_config()
        # Sanitize all paths when loading from config to ensure no directory separators
        scenario_path = config.get("scenario_output_path", "scenarios/results/scenario_output.json")
        template_path = config.get("template_save_path", "scenarios/my_scenario.json")
        report_path = config.get("report_save_path", "scenarios/results/suite_report.json")
        
        # Sanitize basenames in loaded paths
        st.session_state.scenario_output_path = sanitize_path(scenario_path)
        st.session_state.template_save_path = sanitize_path(template_path)
        st.session_state.report_save_path = sanitize_path(report_path)
        
        # Also load the manual edit flag from config
        st.session_state.output_path_manually_edited = config.get("output_path_manually_edited", False)
        st.session_state.paths_initialized = True


def update_persistent_path(key: str, value: str, manual_edit: bool = False) -> None:
    """Update a persistent path in both session state and config file.
    
    Args:
        key: The config key to update
        value: The new path value
        manual_edit: If True, also sets the manual edit flag
    """
    st.session_state[key] = value
    config = load_config()
    config[key] = value
    if manual_edit:
        config["output_path_manually_edited"] = True
        st.session_state.output_path_manually_edited = True
    save_config(config)


def sanitize_basename(basename: str) -> str:
    """Sanitize basename to remove path separators and other problematic characters."""
    # Replace all potentially problematic characters
    import re
    # Remove or replace: spaces, slashes, backslashes, parentheses, commas, periods, etc.
    sanitized = basename.lower()
    # Replace spaces and path separators with underscores
    sanitized = sanitized.replace(' ', '_').replace('/', '_').replace('\\', '_')
    # Remove parentheses, commas, periods, and other special characters
    sanitized = sanitized.replace('(', '').replace(')', '').replace(',', '')
    sanitized = sanitized.replace('.', '').replace('×', 'x').replace(':', '')
    # Remove any remaining characters that aren't alphanumeric or underscore
    sanitized = re.sub(r'[^a-z0-9_]', '', sanitized)
    # Collapse multiple underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    return sanitized


def sanitize_path(path: str) -> str:
    """Sanitize a full file path to ensure no unintended directory separators in basename.
    
    Extracts directory and filename, sanitizes the basename, and reconstructs the path.
    """
    from pathlib import Path
    
    # Split into directory and filename
    path_obj = Path(path)
    directory = path_obj.parent
    filename = path_obj.name
    
    # Extract basename and extension
    if '.' in filename:
        parts = filename.rsplit('.', 1)
        basename = parts[0]
        extension = '.' + parts[1]
    else:
        basename = filename
        extension = ''
    
    # Sanitize just the basename
    clean_basename = sanitize_basename(basename)
    
    # Reconstruct the path
    clean_filename = clean_basename + extension
    clean_path = str(directory / clean_filename)
    
    # Ensure forward slashes for cross-platform compatibility
    clean_path = clean_path.replace('\\', '/')
    
    return clean_path


def generate_random_seed() -> int:
    """Generate a random seed value using Mersenne Twister algorithm."""
    # Python's random module uses Mersenne Twister
    return random.randint(0, 10**9 - 1)


def resolve_seed_value(seed_input: Any) -> int:
    """Resolve seed input to actual integer seed.
    
    Supports:
    - Integer values (passed through)
    - String "random" (generates time-based seed)
    - None (generates time-based seed)
    """
    if isinstance(seed_input, int):
        return seed_input
    if isinstance(seed_input, str) and seed_input.lower() == "random":
        return generate_random_seed()
    if seed_input is None:
        return generate_random_seed()
    # Try to convert to int
    try:
        return int(seed_input)
    except (ValueError, TypeError):
        return generate_random_seed()


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
    
    execution_mode = scenario.get("execution_mode", "matrix")
    
    if execution_mode == "campaign":
        # Campaign mode validation
        required = ["name", "scene_sequence", "batch_size", "base_seed"]
        missing = [f for f in required if f not in scenario]
        if missing:
            raise ValueError(f"Campaign mode missing required fields: {', '.join(missing)}")
        
        # Validate scene_sequence structure
        if not isinstance(scenario["scene_sequence"], list):
            raise ValueError("scene_sequence must be an array")
        if not scenario["scene_sequence"]:
            raise ValueError("scene_sequence cannot be empty")
        
        # Validate each scene in sequence
        for idx, scene_def in enumerate(scenario["scene_sequence"]):
            scene_required = ["preset", "phase", "rarity_mode"]
            scene_missing = [f for f in scene_required if f not in scene_def]
            if scene_missing:
                raise ValueError(f"Scene {idx+1} missing required fields: {', '.join(scene_missing)}")
    else:
        # Matrix mode validation (original)
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
    """Execute a scenario definition and return results.
    
    Supports two execution modes:
    - matrix (default): Cartesian product of presets × phases × rarity_modes with fresh state per run
    - campaign: Sequential scene_sequence with shared state across all scenes
    """
    execution_mode = scenario.get("execution_mode", "matrix")
    
    if execution_mode == "campaign":
        return run_campaign_scenario(scenario, entries, engine_state_class)
    else:
        return run_matrix_scenario(scenario, entries, engine_state_class)


def run_matrix_scenario(
    scenario: Dict[str, Any],
    entries,
    engine_state_class,
) -> Dict[str, Any]:
    """Execute scenario as Cartesian product with fresh state per run (original behavior)."""
    # Resolve base_seed (supports "random" or integer)
    resolved_base_seed = resolve_seed_value(scenario["base_seed"])
    
    report: Dict[str, Any] = {
        "execution_mode": "matrix",
        "suite": scenario.get("name", "Custom scenario"),
        "batch_n": int(scenario["batch_size"]),
        "base_seed": resolved_base_seed,
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
                seed = resolved_base_seed + run_idx
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


def run_campaign_scenario(
    scenario: Dict[str, Any],
    entries,
    engine_state_class,
) -> Dict[str, Any]:
    """Execute scenario as ordered sequence with shared state across all scenes."""
    # Validate required fields for campaign mode
    if "scene_sequence" not in scenario:
        raise ValueError("Campaign mode requires 'scene_sequence' field")
    
    scene_sequence = scenario["scene_sequence"]
    if not scene_sequence:
        raise ValueError("Campaign mode requires non-empty 'scene_sequence'")
    
    # Resolve base_seed
    resolved_base_seed = resolve_seed_value(scenario["base_seed"])
    
    # Initialize shared state for entire campaign
    shared_state = engine_state_class.default()
    
    report: Dict[str, Any] = {
        "execution_mode": "campaign",
        "suite": scenario.get("name", "Campaign scenario"),
        "base_seed": resolved_base_seed,
        "scene_count": len(scene_sequence),
        "batch_size_per_scene": int(scenario["batch_size"]),
        "include_tags": scenario.get("include_tags", ""),
        "exclude_tags": scenario.get("exclude_tags", ""),
        "tick_between": scenario.get("tick_between", True),
        "ticks_between": scenario.get("ticks_between", 1),
        "verbose": scenario.get("verbose", False),
        "scenes": [],  # Per-scene results in order
        "initial_state": engine_state_class.default().__dict__,  # For reference
    }
    
    # Execute scenes sequentially
    for step_idx, scene_def in enumerate(scene_sequence):
        preset_name = scene_def["preset"]
        phase = scene_def["phase"]
        rarity_mode = scene_def["rarity_mode"]
        
        # Per-scene overrides (inherit from scenario if not specified)
        step_batch_size = scene_def.get("batch_size", scenario["batch_size"])
        step_include_tags = scene_def.get("include_tags", scenario.get("include_tags", ""))
        step_exclude_tags = scene_def.get("exclude_tags", scenario.get("exclude_tags", ""))
        
        pv = scene_preset_values(preset_name)
        scene = SceneContext(
            scene_id=f"campaign:{scenario['name']}:step{step_idx+1}:{preset_name}:{phase}",
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
            include_tags=split_csv(step_include_tags),
            exclude_tags=split_csv(step_exclude_tags),
            factions_present=[],
            rarity_mode=rarity_mode,  # type: ignore
        )
        
        # Deterministic seed per step
        seed = resolved_base_seed + step_idx + 1
        
        # Run batch starting from current shared state
        result = run_batch(
            scene=scene,
            selection=selection,
            entries=entries,
            seed=seed,
            n=int(step_batch_size),
            starting_engine_state=shared_state,  # Use current state
            tick_between=bool(scenario.get("tick_between", True)),
            ticks_between=int(scenario.get("ticks_between", 1)),
            verbose=bool(scenario.get("verbose", False)),
        )
        
        # Update shared state from result's final state
        shared_state = result["final_state"]
        # Convert dict back to EngineState object for next iteration
        from spar_engine.state import EngineState
        if isinstance(shared_state, dict):
            shared_state = EngineState(**shared_state)
        
        # Record step result
        report["scenes"].append({
            "step_index": step_idx + 1,
            "preset": preset_name,
            "phase": phase,
            "rarity_mode": rarity_mode,
            "seed": seed,
            "batch_size": int(step_batch_size),
            "summary": result["summary"],
            "state_snapshot": {
                "clocks": dict(shared_state.clocks),
                "tag_cooldowns_count": len(shared_state.tag_cooldowns),
                "recent_ids_count": len(shared_state.recent_event_ids),
            },
            "events": result.get("events"),  # Include if verbose
            "events_sample": result.get("events_sample"),  # Include if not verbose
        })
    
    # Add final state to report
    report["final_state"] = shared_state.__dict__
    
    return report


def main() -> None:
    st.set_page_config(page_title="SPAR Engine Harness v0.1", layout="wide")
    init_persistent_paths()
    hs = get_hs()
    
    # Initialize campaign context
    from streamlit_harness.campaign_context import init_campaign_context_state, get_campaign_context
    init_campaign_context_state()
    
    # Mode selector at top
    # Use index-based control for programmatic switching
    if "mode_index" not in st.session_state:
        st.session_state.mode_index = 0  # Default to Campaign Manager
    
    mode_options = ["🎲 Campaign Manager", "⚡ Generators"]
    mode = st.radio(
        "Mode",
        mode_options,
        index=st.session_state.mode_index,
        horizontal=True,
        label_visibility="collapsed",
        help="Campaign Manager: Multi-campaign management with living state. Generators: Multi-domain generation (Events, Loot, etc.) with scenario validation."
    )
    
    # Update index when user changes mode
    st.session_state.mode_index = mode_options.index(mode)
    
    # Render campaign UI if in campaign mode
    if mode == "🎲 Campaign Manager":
        from streamlit_harness.campaign_ui import render_campaign_ui
        render_campaign_ui()
        return
    
    # Otherwise render generators workspace
    st.title("SPAR Generators")
    st.caption("Multi-domain generation (Events, Loot, etc.) and scenario validation. Not a product UI.")
    
    # Campaign Context Strip (v0.3: Faction Influence + v0.4: Multi-pack display)
    # Ensure context is loaded when campaign is selected
    current_campaign_id = st.session_state.get("current_campaign_id")
    if current_campaign_id and not get_campaign_context():
        # Campaign selected but context not loaded - initialize it
        from streamlit_harness.campaign_ui import Campaign
        campaign = Campaign.load(current_campaign_id)
        if campaign and campaign.campaign_state:
            from streamlit_harness.campaign_context import ContextBundle, set_campaign_context
            context_bundle = ContextBundle.from_campaign(
                campaign_id=campaign.campaign_id,
                campaign_name=campaign.name,
                campaign_state=campaign.campaign_state,
                sources=campaign.sources,
            )
            set_campaign_context(context_bundle)
    
    context = get_campaign_context()
    if context and st.session_state.get("context_enabled", True):
        with st.container(border=True):
            col1, col2 = st.columns([10, 2])
            
            with col1:
                st.markdown(f"**🎯 Campaign Context:** {context.campaign_name}")
                
                # Show active content packs with entry counts
                current_campaign_id = st.session_state.get("current_campaign_id")
                if current_campaign_id:
                    from streamlit_harness.campaign_ui import Campaign
                    campaign = Campaign.load(current_campaign_id)
                    if campaign and campaign.enabled_content_packs:
                        # Calculate total entries
                        total_entries = 0
                        pack_names = []
                        for pack_path in campaign.enabled_content_packs:
                            try:
                                pack_entries = load_pack(pack_path)
                                total_entries += len(pack_entries)
                                pack_names.append(Path(pack_path).stem.replace('_', ' ').title())
                            except Exception:
                                pack_names.append(Path(pack_path).stem.replace('_', ' ').title())
                        
                        if len(pack_names) == 1:
                            st.caption(f"📦 Pack: {pack_names[0]} ({total_entries} entries)")
                        else:
                            packs_display = " + ".join(pack_names)
                            st.caption(f"📦 Packs: {packs_display} ({total_entries} entries)")
                
                # Faction spotlight (with full names, not just IDs)
                if context.suggested_factions and context.faction_influence_notes:
                    # Show just faction names in summary line
                    faction_names = []
                    for note in context.faction_influence_notes:
                        # Extract name before the score
                        name_part = note.split(" (score:")[0] if " (score:" in note else note
                        faction_names.append(name_part)
                    
                    factions_display = ", ".join(faction_names[:2])
                    if len(faction_names) > 2:
                        factions_display += f" +{len(faction_names)-2}"
                    
                    st.caption(f"👥 Faction focus: {factions_display}")
                
                # Bands summary
                st.caption(f"🎚️ {context.pressure_band.title()} pressure • 🌡️ {context.heat_band.title()} heat")
            
            with col2:
                if st.button("Details", key="view_context"):
                    st.session_state.show_context_details = not st.session_state.get("show_context_details", False)
                if st.button("Disable", key="disable_context", help="Disable campaign context for this run"):
                    st.session_state.context_enabled = False
                    st.rerun()
            
            # Expanded details view
            if st.session_state.get("show_context_details", False):
                st.markdown("**Faction Influence:**")
                if context.faction_influence_notes:
                    for note in context.faction_influence_notes:
                        st.caption(f"• {note}")
                else:
                    st.caption("• No factions with significant attention")
                
                # Show tag bias if present
                if context.faction_tag_bias:
                    st.markdown("**Tag Nudges from Factions:**")
                    st.caption(f"🏷️ {', '.join(context.faction_tag_bias)}")
                
                # Show other context notes
                if context.notes:
                    st.markdown("**Other Context:**")
                    for note in context.notes:
                        st.caption(f"• {note}")

    # ---------------- Sidebar (Tab-Conditional) ----------------
    # Only show sidebar on Events tab
    # Streamlit doesn't have native tab state, so we render conditionally
    # and let variables be accessed from outside the conditional block
    
    # Initialize default values that will be used regardless of sidebar rendering
    preset = "confined"
    scene_phase = "engage"
    rarity_mode = "normal"
    scene_id = "harness"
    party_band = "unknown"
    seed = 42
    confinement = 0.5
    connectivity = 0.5
    visibility = 0.5
    pack_path = DEFAULT_PACK
    tick_mode = "none"
    ticks = 0
    tick_between = True
    ticks_between_events = 1
    include_tags_text = ""
    exclude_tags_text = ""
    
    # Render sidebar only when we're likely on Events tab
    # We detect this by checking if we're in the first iteration of tab rendering
    # This is a workaround since Streamlit doesn't expose tab state directly
    with st.sidebar:
        st.header("Generator Controls")
        st.caption("Configure single-event generation")
        
        # ============================================================
        # LAYER 1: PRIMARY GM CONTROLS
        # ============================================================
        
        # Campaign Context Selector
        st.subheader("Campaign Context")
        
        from streamlit_harness.campaign_ui import Campaign
        campaigns = Campaign.list_all()
        
        if campaigns:
            campaign_options = ["-- No Campaign --"] + [c.name for c in campaigns]
            current_campaign_id = st.session_state.get("current_campaign_id")
            
            # Find current selection index
            current_index = 0
            if current_campaign_id:
                current_campaign = Campaign.load(current_campaign_id)
                if current_campaign and current_campaign.name in campaign_options:
                    current_index = campaign_options.index(current_campaign.name)
            
            selected_campaign_name = st.selectbox(
                "Active Campaign",
                campaign_options,
                index=current_index,
                help="Select a campaign to apply its context (tags, factions) to event generation"
            )
            
            # Update campaign context when selection changes
            if selected_campaign_name == "-- No Campaign --":
                if current_campaign_id:
                    st.session_state.current_campaign_id = None
                    st.session_state.context_enabled = False
                    st.rerun()
            else:
                # Find and activate selected campaign
                matching = [c for c in campaigns if c.name == selected_campaign_name]
                if matching:
                    selected_campaign = matching[0]
                    if selected_campaign.campaign_id != current_campaign_id:
                        st.session_state.current_campaign_id = selected_campaign.campaign_id
                        st.session_state.context_enabled = True
                        
                        # Set campaign context
                        if selected_campaign.campaign_state:
                            from streamlit_harness.campaign_context import ContextBundle, set_campaign_context
                            context_bundle = ContextBundle.from_campaign(
                                campaign_id=selected_campaign.campaign_id,
                                campaign_name=selected_campaign.name,
                                campaign_state=selected_campaign.campaign_state,
                                sources=selected_campaign.sources,
                            )
                            set_campaign_context(context_bundle)
                        
                        st.rerun()
        else:
            st.caption("No campaigns yet. Create one in Campaign Manager mode.")
        
        st.divider()
        
        # Generator type selector (dropdown for scalability)
        gen_type = st.selectbox(
            "Generator",
            ["⚔️ Event", "💰 Loot"],
            index=0,
            key="generator_type_sidebar",
            help="Event: Complications and pressure. Loot: Resource shocks with consequences."
        )
        
        # Conditionally show Scene Setup only for Events
        if gen_type == "⚔️ Event":
            st.subheader("Scene Setup")
            st.caption("Environmental constraints, not genre")
            
            preset = st.selectbox(
                "Scene preset", 
                ["confined", "populated", "open", "derelict"], 
                index=0,
                help="Confined: tight space, limited exits • Populated: crowds, witnesses, institutions • Open: exposure, distance, limited support • Derelict: unstable structures, decay"
            )
            pv = scene_preset_values(preset)
            scene_phase = st.selectbox("Scene phase", ["approach", "engage", "aftermath"], index=1)
        else:
            # Loot mode: use stable defaults internally (not user-configurable)
            preset = "derelict"  # Neutral environment for loot
            pv = scene_preset_values(preset)
            scene_phase = "aftermath"  # Most loot appears in aftermath
        
        # Rarity mode applies to both Event and Loot
        rarity_mode = st.selectbox("Rarity mode", ["calm", "normal", "spiky"], index=1,
                                   help="Calm: Low variance. Normal: Balanced. Spiky: High variance (heavy tail).")
        
        # Filters (collapsed by default per designer constraint)
        with st.expander("🏷️ Filters", expanded=False):
            st.caption("Customize tag filtering for content selection")
            
            # Pre-fill tags from campaign context if available
            default_include_tags = "hazard,reinforcements,time_pressure,social_friction,visibility,mystic,attrition,terrain,positioning,opportunity,information"
            default_exclude_tags = ""
            
            if context and st.session_state.get("context_enabled", True):
                # Merge context tags with defaults
                context_include, context_exclude = context.to_tag_csv()
                if context_include:
                    # Add context tags to defaults (dedupe)
                    all_include = set(split_csv(default_include_tags) + split_csv(context_include))
                    default_include_tags = ",".join(sorted(all_include))
                if context_exclude:
                    default_exclude_tags = context_exclude
            
            include_tags_text = st.text_input(
                "Include tags (CSV)",
                value=default_include_tags,
            )
            exclude_tags_text = st.text_input("Exclude tags (CSV)", value=default_exclude_tags)
        
        # ============================================================
        # LAYER 3: ADVANCED SETTINGS (Collapsed by default)
        # ============================================================
        
        with st.expander("🔧 Advanced Settings", expanded=False):
            st.caption("Engine internals and debugging controls")
            
            # Seed control (moved here per designer constraint)
            seed = st.number_input("Seed", min_value=0, max_value=10**9, value=42, step=1, 
                                   help="RNG seed for reproducible generation")
            
            # Batch size
            hs.batch_n = st.selectbox(
                "Batch count",
                [10, 50, 200],
                index=[10, 50, 200].index(hs.batch_n) if hs.batch_n in [10, 50, 200] else 1,
            )
            
            st.divider()
            
            # Constraint sliders
            st.caption("**Scene Constraints**")
            confinement = st.slider("Confinement", 0.0, 1.0, float(pv["confinement"]), 0.05)
            connectivity = st.slider("Connectivity", 0.0, 1.0, float(pv["connectivity"]), 0.05)
            visibility = st.slider("Visibility", 0.0, 1.0, float(pv["visibility"]), 0.05)
            
            st.divider()
            
            # Tick mechanics
            st.caption("**Tick Mechanics**")
            tick_mode = st.selectbox("Tick mode", ["none", "turn", "scene"], index=0)
            ticks = st.number_input("Ticks", min_value=0, max_value=100, value=0, step=1)
            st.caption("Batch runs are sequential by default (treat each generated event as a 'turn').")
            tick_between = st.checkbox("Tick between events in batch", value=True)
            ticks_between_events = st.number_input("Ticks between events", min_value=0, max_value=10, value=1, step=1)
            
            st.divider()
            
            # Technical identifiers
            st.caption("**Technical Identifiers**")
            scene_id = st.text_input("Scene ID", value="harness")
            party_band = st.selectbox("Party band", ["low", "mid", "high", "unknown"], index=3)
            
            st.divider()
            
            # Content pack
            st.caption("**Content Pack**")
            
            # Check if campaign is selected with packs
            current_campaign_id = st.session_state.get("current_campaign_id")
            if current_campaign_id:
                from streamlit_harness.campaign_ui import Campaign
                campaign = Campaign.load(current_campaign_id)
                if campaign and campaign.enabled_content_packs:
                    # Show detailed pack listing
                    st.markdown("**Active Packs:**")
                    
                    total_pack_entries = 0
                    for pack_path in campaign.enabled_content_packs:
                        try:
                            pack_entries = load_pack(pack_path)
                            pack_name = Path(pack_path).stem.replace('_', ' ').title()
                            st.caption(f"• {pack_name} ({len(pack_entries)} entries)")
                            total_pack_entries += len(pack_entries)
                        except Exception:
                            pack_name = Path(pack_path).stem.replace('_', ' ').title()
                            st.caption(f"• {pack_name} (load failed)")
                    
                    st.caption(f"**Total: {total_pack_entries} entries from {len(campaign.enabled_content_packs)} pack(s)**")
                    
                    if st.button("Load campaign packs") or not hs.pack_entries:
                        try:
                            entries = load_packs(campaign.enabled_content_packs)
                            hs.pack_entries = entries
                            hs.tag_vocab = derive_tag_vocab(entries)
                            st.toast(f"Loaded {len(entries)} entries from {len(campaign.enabled_content_packs)} pack(s)", icon="✅")
                        except Exception as ex:
                            st.error(f"Failed to load campaign packs: {ex}")
                else:
                    # Fallback to single pack if campaign has no packs
                    pack_path = st.text_input("Content pack path", value=DEFAULT_PACK)
                    if st.button("Load pack") or not hs.pack_entries:
                        try:
                            entries = load_entries(pack_path)
                            hs.pack_entries = entries
                            hs.tag_vocab = derive_tag_vocab(entries)
                            st.toast(f"Loaded {len(entries)} entries", icon="✅")
                        except Exception as ex:
                            st.error(str(ex))
            else:
                # No campaign - use single pack path
                pack_path = st.text_input("Content pack path", value=DEFAULT_PACK)
                
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
            
            st.divider()
            
            # State debugging
            st.caption("**State Debugging**")
            if st.button("Reset session state"):
                hs.reset()
                st.toast("Session reset.", icon="✅")

            st.text_area(
                "Current state (read-only)",
                value=json.dumps(hs.engine_state.__dict__, indent=2),
                height=180,
            )

    # Detect active tab for conditional sidebar rendering
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "Events"
    
    tabs = st.tabs(["Generate", "Diagnostics"])
    
    # Tab click detection (workaround for streamlit tab state)
    # We'll render the sidebar conditionally based on which tab's content is being viewed
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

    with tabs[0]:
        # Retrieve generator type from sidebar
        gen_type = st.session_state.get("generator_type_sidebar", "⚔️ Event")
        
        # Loot Context Strip (only when Loot mode active)
        if gen_type == "💰 Loot":
            with st.container(border=True):
                st.markdown("**💰 Loot Context**")
                
                # Derive messaging from campaign state (no new persisted state)
                current_campaign_id = st.session_state.get("current_campaign_id")
                
                if current_campaign_id:
                    from streamlit_harness.campaign_ui import Campaign
                    campaign = Campaign.load(current_campaign_id)
                    
                    if campaign and campaign.campaign_state:
                        cs = campaign.campaign_state
                        
                        # Base message
                        st.caption("Resource shock influenced by campaign state. Gains may attract attention, create obligations, or shift faction interest.")
                        
                        # Faction influence (if present)
                        if context and context.suggested_factions:
                            faction_names = []
                            for note in context.faction_influence_notes[:2]:
                                # Extract just the name and band
                                name_part = note.split(" (score:")[0] if " (score:" in note else note
                                faction_names.append(name_part)
                            
                            if faction_names:
                                st.caption(f"Current interests: {', '.join(faction_names)}")
                        else:
                            # No faction influence - check pressure/heat bands
                            pressure_band = cs.get_pressure_band()
                            heat_band = cs.get_heat_band()
                            
                            if pressure_band in ["volatile", "critical"] or heat_band in ["hunted", "exposed"]:
                                st.caption("Acquisition is likely to be noticed or contested.")
                            else:
                                st.caption("Short-term relief is possible without immediate fallout.")
                    else:
                        st.caption("Resource shock influenced by campaign state. Gains may attract attention, create obligations, or shift faction interest.")
                else:
                    # No campaign selected
                    st.caption("Standalone loot generation. Results reflect generic resource gains with narrative consequences.")
        
        colA, colB = st.columns([2, 1])

        with colA:
            st.header("Events & Loot")
            
            btn1, btnN = st.columns(2)
            run_one = btn1.button("Generate 1", use_container_width=True)
            run_many = btnN.button(f"Generate {hs.batch_n}", use_container_width=True)

            if run_one or run_many:
                n = 1 if run_one else int(hs.batch_n)

                if tick_mode != "none" and int(ticks) > 0:
                    hs.engine_state = tick_state(hs.engine_state, ticks=int(ticks))

                rng = TraceRNG(seed=int(seed))

                batch_events: List[Dict[str, Any]] = []
                
                # Determine which generator to use
                use_loot_gen = (gen_type == "💰 Loot")
                
                # Load appropriate content
                gen_entries = entries
                if use_loot_gen:
                    # Try to load loot pack
                    try:
                        loot_pack_path = "data/core_loot_situations.json"
                        gen_entries = load_entries(loot_pack_path)
                        if not gen_entries:
                            st.error("Loot pack is empty. Using event pack as fallback.")
                            gen_entries = entries
                    except Exception as ex:
                        st.warning(f"Could not load loot pack: {ex}. Using event pack as fallback.")
                        use_loot_gen = False
                        gen_entries = entries
                
                try:
                    for idx in range(n):
                        if idx > 0 and tick_between and int(ticks_between_events) > 0:
                            hs.engine_state = tick_state(hs.engine_state, ticks=int(ticks_between_events))

                        rng.trace.clear()
                        
                        # Route to appropriate generator
                        if use_loot_gen:
                            from spar_engine.loot import generate_loot
                            ev = generate_loot(scene, hs.engine_state, selection, gen_entries, rng)
                        else:
                            ev = generate_event(scene, hs.engine_state, selection, gen_entries, rng)
                        
                        hs.engine_state = apply_state_delta(hs.engine_state, ev.state_delta)

                        d = event_to_dict(ev)
                        batch_events.append(d)
                        hs.events.insert(0, d)
                    
                    hs.last_batch = batch_events
                
                except ValueError as e:
                    # Content exhaustion - show helpful message instead of crashing
                    if "No content entries available" in str(e):
                        st.error("⚠️ Content Exhausted")
                        st.warning(
                            f"Generated {len(batch_events)} of {n} events before running out of available content.\n\n"
                            "**Possible causes:**\n"
                            "- Tag filters too restrictive\n"
                            "- Tag cooldowns from previous events\n"
                            "- Not enough ticking between events\n\n"
                            "**Try:**\n"
                            "- Broaden include tags or remove exclude tags\n"
                            "- Increase 'Ticks between events' to expire cooldowns\n"
                            "- Reset session state to clear cooldowns\n"
                            "- Generate fewer events at once"
                        )
                        # Save partial batch if any events were generated
                        if batch_events:
                            hs.last_batch = batch_events
                            st.info(f"Partial batch saved: {len(batch_events)} events generated")
                    else:
                        # Re-raise other ValueErrors
                        raise

            # Finalize Session button (Flow B: Generator → Campaign)
            if hs.events and st.session_state.get("active_campaign_context"):
                if st.button("✅ Finalize Session", type="primary", use_container_width=True):
                    # Create session packet from last batch
                    if hs.last_batch:
                        from streamlit_harness.session_packet import SessionPacket
                        packet = SessionPacket.from_run_result(
                            scenario_name=f"{preset} / {scene_phase} / {rarity_mode}",
                            preset=preset,
                            phase=scene_phase,
                            rarity_mode=rarity_mode,
                            seed=seed,
                            batch_size=hs.batch_n,
                            events=hs.last_batch,
                            summary=summarize_events(hs.last_batch),
                        )
                        st.session_state.pending_session_packet = packet
                        
                        # Navigate to campaign finalize
                        st.session_state.campaign_page = "finalize"
                        # Switch to campaign mode
                        st.rerun()
                st.divider()
            
            if hs.events:
                # Add "Send to Campaign" section
                if st.session_state.get("current_campaign_id"):
                    from streamlit_harness.campaign_ui import Campaign, PrepItem
                    campaign = Campaign.load(st.session_state.current_campaign_id)
                    if campaign:
                        st.info(f"📤 Sending to: **{campaign.name}** | Events will be added to Prep Queue (not canon)")
                        
                        # Selection controls with computed count
                        col1, col2, col3, col4 = st.columns([3, 2, 2, 5])
                        
                        # Compute count by checking checkbox keys directly
                        selected_count = sum(
                            1 for idx in range(min(25, len(hs.events)))
                            if st.session_state.get(f"select_event_{idx}", False)
                        )
                        
                        with col1:
                            if st.button("☑️ Select All"):
                                for idx in range(min(25, len(hs.events))):
                                    st.session_state[f"select_event_{idx}"] = True
                                st.rerun()
                        
                        with col2:
                            if st.button("☐ Select None"):
                                for idx in range(min(25, len(hs.events))):
                                    st.session_state[f"select_event_{idx}"] = False
                                st.rerun()
                        
                        with col3:
                            st.caption(f"Selected: {selected_count}")
                        
                        # Send buttons
                        send_col1, send_col2 = st.columns(2)
                        
                        with send_col1:
                            if st.button(
                                f"📤 Send Selected ({selected_count})",
                                disabled=(selected_count == 0 or selected_count > 50),
                                use_container_width=True,
                                type="primary" if (selected_count > 0 and selected_count <= 50) else "secondary"
                            ):
                                # CAP CHECK: Generator → Prep Queue
                                if selected_count > 50:
                                    st.error("⚠️ Selection limit exceeded! Maximum 50 items per batch. Please deselect some items.")
                                    st.stop()
                                
                                from datetime import datetime as dt
                                # Get selected indices from checkbox keys
                                selected_indices = [
                                    idx for idx in range(min(25, len(hs.events)))
                                    if st.session_state.get(f"select_event_{idx}", False)
                                ]
                                
                                for idx in selected_indices:
                                    if idx < len(hs.events):
                                        e = hs.events[idx]
                                        prep_item = PrepItem(
                                            item_id=f"prep_{dt.now().strftime('%Y%m%d_%H%M%S%f')}_{idx}",
                                            created_at=dt.now().isoformat(),
                                            title=e.get("title", "Untitled Event"),
                                            summary=e.get("content", "")[:200],
                                            tags=e.get("tags", []),
                                            source={
                                                "scenario_name": "Event Generator",
                                                "preset": preset,
                                                "phase": scene_phase,
                                                "rarity_mode": rarity_mode,
                                                "seed": seed,
                                            },
                                            status="queued",
                                        )
                                        campaign.prep_queue.append(prep_item)
                                
                                campaign.save()
                                # Clear all checkbox states
                                for idx in range(min(25, len(hs.events))):
                                    st.session_state[f"select_event_{idx}"] = False
                                
                                # A: Success banner with "Go to Campaign" CTA
                                st.session_state.send_success_count = len(selected_indices)
                                st.session_state.send_success_campaign = campaign.name
                                st.rerun()
                        
                        with send_col2:
                            if st.button("📤 Send All", use_container_width=True, disabled=(len(hs.events[:25]) > 50)):
                                # CAP CHECK: Generator → Prep Queue
                                send_count = min(50, len(hs.events[:25]))
                                if len(hs.events[:25]) > 50:
                                    st.error("⚠️ Too many items! Maximum 50 items per batch. Use 'Send Selected' to choose specific items.")
                                    st.stop()
                                
                                from datetime import datetime as dt
                                # Create prep items from all events (capped at 50)
                                for idx, e in enumerate(hs.events[:send_count]):
                                    prep_item = PrepItem(
                                        item_id=f"prep_{dt.now().strftime('%Y%m%d_%H%M%S%f')}_{idx}",
                                        created_at=dt.now().isoformat(),
                                        title=e.get("title", "Untitled Event"),
                                        summary=e.get("content", "")[:200],
                                        tags=e.get("tags", []),
                                        source={
                                            "scenario_name": "Event Generator",
                                            "preset": preset,
                                            "phase": scene_phase,
                                            "rarity_mode": rarity_mode,
                                            "seed": seed,
                                        },
                                        status="queued",
                                    )
                                    campaign.prep_queue.append(prep_item)
                                
                                campaign.save()
                                # Clear all checkbox states
                                for idx in range(min(25, len(hs.events))):
                                    st.session_state[f"select_event_{idx}"] = False
                                
                                # A: Success banner with "Go to Campaign" CTA
                                st.session_state.send_success_count = send_count
                                st.session_state.send_success_campaign = campaign.name
                                st.rerun()
                        
                        # A: Show success banner and "Go to Campaign" CTA after send
                        if "send_success_count" in st.session_state:
                            count = st.session_state.send_success_count
                            camp_name = st.session_state.send_success_campaign
                            
                            st.success(f"✓ Sent {count} item{'s' if count != 1 else ''} to Prep Queue for **{camp_name}**")
                            
                            if st.button("🎯 Go to Campaign", type="primary", use_container_width=True):
                                # Clear success state
                                del st.session_state.send_success_count
                                del st.session_state.send_success_campaign
                                # Switch to Campaign Manager mode and dashboard
                                st.session_state.mode_index = 0  # Index 0 = Campaign Manager
                                st.session_state.campaign_page = "dashboard"
                                st.rerun()
                            
                            # Clear button to dismiss
                            if st.button("Dismiss", use_container_width=True):
                                del st.session_state.send_success_count
                                del st.session_state.send_success_campaign
                                st.rerun()
                        
                        st.divider()
                
                # C: Show warning if selection would exceed cap
                if len(hs.events) > 50:
                    st.warning(f"⚠️ Generator has {len(hs.events)} events, but max 50 can be sent per batch. Use 'Send Selected' to choose items.")
                
                # Display events with checkboxes
                for idx, e in enumerate(hs.events[:25]):
                    with st.container(border=True):
                        if st.session_state.get("current_campaign_id"):
                            # Checkbox with key - Streamlit manages state
                            col_check, col_event = st.columns([1, 19])
                            with col_check:
                                # Initialize checkbox key if needed
                                checkbox_key = f"select_event_{idx}"
                                if checkbox_key not in st.session_state:
                                    st.session_state[checkbox_key] = False
                                st.checkbox("", key=checkbox_key, label_visibility="collapsed")
                            with col_event:
                                event_card(e)
                        else:
                            event_card(e)
            else:
                st.info("No events generated yet.")

        with colB:
            st.header("Diagnostics")
            diagnostics(hs.last_batch)

    with tabs[1]:
        st.header("Test Profiles")
        st.caption("Run predefined test profiles for SOC validation and content regression testing. Internal tool.")
        
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
                execution_mode = loaded_scenario.get("execution_mode", "matrix")
                
                with st.expander("Scenario Details", expanded=True):
                    st.write(f"**Name**: {loaded_scenario['name']}")
                    st.write(f"**Description**: {loaded_scenario.get('description', 'N/A')}")
                    st.write(f"**Execution Mode**: {execution_mode}")
                    
                    if execution_mode == "campaign":
                        # Campaign mode display
                        scene_seq = loaded_scenario.get("scene_sequence", [])
                        st.write(f"**Scene Count**: {len(scene_seq)}")
                        st.write(f"**Batch Size per Scene**: {loaded_scenario['batch_size']}")
                        st.write(f"**Base Seed**: {loaded_scenario['base_seed']}")
                        
                        # Display scene sequence
                        st.write("**Scene Sequence**:")
                        for idx, scene_def in enumerate(scene_seq):
                            st.write(f"{idx+1}. {scene_def['preset']} / {scene_def['phase']} / {scene_def['rarity_mode']}")
                    else:
                        # Matrix mode display (original)
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
                if "last_loaded_scenario" not in st.session_state:
                    st.session_state.last_loaded_scenario = None
                
                # Check if scenario has changed
                scenario_changed = st.session_state.last_loaded_scenario != scenario_name
                
                if scenario_changed:
                    # Reset manual edit flag when loading a new scenario
                    st.session_state.output_path_manually_edited = False
                    
                    # Update the last loaded scenario tracker
                    st.session_state.last_loaded_scenario = scenario_name
                    
                    # New scenario selected - generate fresh filename with timestamp
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    # Use output_basename if provided, otherwise sanitize scenario name
                    # ALWAYS sanitize to remove path separators
                    if "output_basename" in loaded_scenario and loaded_scenario["output_basename"]:
                        basename = sanitize_basename(loaded_scenario["output_basename"])
                    else:
                        basename = sanitize_basename(scenario_name)
                    
                    # Truncate basename if total filename would be too long (>255 chars)
                    # Keep timestamp intact, truncate basename if needed
                    max_filename_length = 255
                    path_prefix = "results/"
                    extension = ".json"
                    available_length = max_filename_length - len(path_prefix) - len(timestamp) - 1 - len(extension)  # -1 for underscore
                    
                    if len(basename) > available_length:
                        basename = basename[:available_length]
                    
                    new_path = f"scenarios/results/{basename}_{timestamp}{extension}"
                    
                    # Update session state BEFORE widget is created (avoids warning)
                    st.session_state.output_path_input = new_path
                    st.session_state.scenario_output_path = new_path
                    
                    # Persist to config file
                    config = load_config()
                    config["scenario_output_path"] = new_path
                    save_config(config)
            
            st.caption(f"📁 Working directory: {Path.cwd()}")
            
            # Store current value before widget to detect changes
            previous_path = st.session_state.get("scenario_output_path", "results/scenario_output.json")
            
            output_path = st.text_input(
                "Save results to path",
                value=st.session_state.scenario_output_path,
                help="Full file path where results JSON will be saved (persisted between sessions). Relative paths are from working directory shown above.",
                key="output_path_input"
            )
            
            # Detect if user manually changed the path
            if output_path != previous_path:
                # Update path and set manual edit flag (persisted to config)
                update_persistent_path("scenario_output_path", output_path, manual_edit=True)
            
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

        presets = ["confined", "populated", "open", "derelict"]

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
        
        # Initialize base_seed_value in session state if not present
        if "base_seed_value" not in st.session_state:
            st.session_state.base_seed_value = 1000
        
        # Base seed with random option
        col_seed1, col_seed2 = st.columns([3, 1])
        
        # Check if dice button was clicked
        with col_seed2:
            if st.button("🎲", help="Generate random seed"):
                # Generate and store the actual random integer
                st.session_state.base_seed_value = generate_random_seed()
                st.rerun()
        
        with col_seed1:
            # Use number_input to show the current seed value
            base_seed = st.number_input(
                "Base seed",
                min_value=0,
                max_value=10**9,
                value=st.session_state.base_seed_value,
                step=1,
                help="Click dice button for random seed, or enter a number (0-999999999)"
            )
            # Update session state when user changes value
            if base_seed != st.session_state.base_seed_value:
                st.session_state.base_seed_value = base_seed

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
