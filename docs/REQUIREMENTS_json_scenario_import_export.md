# Requirements: JSON Scenario Import/Export System

<!--
Version History:
- v1.0 (2025-12-25): Initial requirements definition
-->

**Status**: Approved for implementation  
**Date**: December 2025

## Objective

Enable JSON-based scenario definition, import, execution, and result export in the Streamlit harness to support:
- Automated validation workflows
- Reproducible test scenarios
- Phase weighting analysis
- Scenario library management

## User Requirements

### Primary Workflow
1. Define scenario parameters in JSON format
2. Import scenario JSON (file upload or library)
3. Execute scenario with specified parameters
4. Export results to user-specified file path

### Secondary Features
- Built-in scenario library for common validation tasks
- **Save as Template**: Export current hardcoded suite UI settings as JSON scenario
  - Unified save/export UX (same as report saves)
  - Working directory display for path clarity
  - Specify save path with cross-session persistence (survives app restarts)
  - Descriptive default filenames with timestamps
  - Includes all parameters: presets, phases, modes, batch size, seed, tags, ticks
  - Enables ad-hoc scenario creation without manual JSON editing
  - Uses shared save_report_to_path() backend (no code duplication)
- **Unified Save/Export UX**: All three save/export operations use consistent interface
  - Save Report (Markdown)
  - Save Report (JSON)
  - Save as Template (JSON)
  - Each displays working directory, accepts path specification, persists paths across all sessions
- **Cross-Session Persistence**: User-specified file paths stored in `.streamlit_harness_config.json`
  - Paths remembered across app restarts and browser sessions
  - Config file excluded from git (personal preferences)
  - Automatic fallback to sensible defaults if config missing
- Maintain existing hardcoded suite functionality
- Backward compatibility with current UI

## JSON Schema

### Execution Modes

Scenarios support two execution modes:

**Matrix Mode** (default):
- Cartesian product of presets × phases × rarity_modes
- Fresh EngineState per combination
- Good for validating phase behavior in isolation

**Campaign Mode** (new):
- Sequential execution with ordered scene_sequence
- Single shared EngineState across all scenes
- Enables multi-scene rhythm validation
- Observes state evolution and pressure/release patterns

### Scenario Definition Format

**Matrix Mode Example**:
```json
{
  "schema_version": "1.0",
  "execution_mode": "matrix",
  "name": "Scenario Name",
  "description": "Brief description of validation purpose",
  "output_basename": "clean_filename_base",
  "presets": ["dungeon", "city", "wilderness", "ruins"],
  "phases": ["approach", "engage", "aftermath"],
  "rarity_modes": ["normal"],
  "batch_size": 200,
  "base_seed": 1000,
  "include_tags": "",
  "exclude_tags": "",
  "tick_between": true,
  "ticks_between": 1,
  "verbose": false
}
```

**Campaign Mode Example**:
```json
{
  "schema_version": "1.0",
  "execution_mode": "campaign",
  "name": "Campaign Rhythm Validation",
  "description": "Tests multi-scene narrative rhythm with shared state",
  "output_basename": "campaign_rhythm",
  "scene_sequence": [
    {"preset": "dungeon", "phase": "approach", "rarity_mode": "normal"},
    {"preset": "dungeon", "phase": "engage", "rarity_mode": "normal"},
    {"preset": "dungeon", "phase": "aftermath", "rarity_mode": "normal"},
    {"preset": "dungeon", "phase": "approach", "rarity_mode": "normal"},
    {"preset": "dungeon", "phase": "engage", "rarity_mode": "normal"},
    {"preset": "dungeon", "phase": "aftermath", "rarity_mode": "normal"}
  ],
  "batch_size": 50,
  "base_seed": 5000,
  "include_tags": "",
  "exclude_tags": "",
  "tick_between": true,
  "ticks_between": 1,
  "verbose": false
}
```

### Required Fields

**Matrix Mode**:
- `name` (string)
- `presets` (array of strings)
- `phases` (array of strings)
- `rarity_modes` (array of strings)
- `batch_size` (integer)
- `base_seed` (integer or string "random")

**Campaign Mode**:
- `name` (string)
- `scene_sequence` (array of scene objects)
  - Each scene requires: `preset`, `phase`, `rarity_mode`
  - Optional per-scene: `batch_size`, `include_tags`, `exclude_tags`
- `batch_size` (integer, default per scene)
- `base_seed` (integer or string "random")

### Optional Fields (Both Modes)
- `schema_version` (string, default: "1.0") - Future-proofs format evolution
- `execution_mode` (string, default: "matrix") - Options: "matrix" or "campaign"
- `output_basename` (string, optional) - Clean basename for output files. Characters like `/`, `\`, and spaces are automatically sanitized to `_` to prevent unwanted directory creation
- `description` (string, default: "")
- `include_tags` (string CSV, default: "") - Global default for all scenes
- `exclude_tags` (string CSV, default: "") - Global default for all scenes
- `tick_between` (boolean, default: true)
- `ticks_between` (integer, default: 1)
- `verbose` (boolean, default: false)

### Design Notes
- **schema_version**: Added per designer feedback to avoid future pain when extending the format. Currently "1.0", future scenarios can validate compatibility.
- **output_basename**: Added per designer feedback to provide consistent basename when generating multiple output files (JSON + markdown summaries). If omitted, system auto-generates from scenario name. Automatically sanitized to remove path separators.
- **base_seed**: Supports both integer values (for reproducible testing) and string "random" (for pseudorandom generation). When set to "random", uses Python's Mersenne Twister algorithm (via `random.randint()`) to generate high-quality pseudorandom integers across the full range (0-999,999,999). Each run still gets base_seed + run_index offset for determinism within the scenario execution.

## UI Components

### Scenarios Tab Enhancements

**Import Section** (new):
- File uploader: "Upload scenario JSON"
- Dropdown: "Or select from library"
- Display: Loaded scenario details (shows resolved seed value if "random")
- Validation: Show errors for invalid JSON

**Configuration Section** (existing):
- Keep current suite dropdown for hardcoded suites
- Keep existing manual controls
- Base seed input: Text field accepting integers or "random"
- Random seed button (🎲): Quick way to generate random seed

**Export Section** (unified):
- Working directory display: Shows Path.cwd() for path context
- Text input: "Save results to path" (full file path, persists in session)
- Buttons: 
  - "Run and Save Scenario" (scenario execution with auto-save)
  - "Save Report (Markdown)" (manual export current results)
  - "Save Report (JSON)" (manual export current results)
  - "Save as Template" (export current UI settings as scenario JSON)
- All save operations use unified save_report_to_path() backend
- All path inputs persist across sessions via st.session_state
- Status: Success/error feedback for all operations

**Results Section** (existing):
- Summary table
- Download buttons (markdown/JSON)

## Implementation Details

### File Structure
```
scenarios/
├── phase_validation_scenario_a.json
├── phase_validation_scenario_b.json
└── README.md
```

### Core Functions

1. **load_scenario_json(file_or_path) -> Dict**
   - Parse JSON
   - Validate required fields
   - Return scenario dict or raise error

2. **save_report_to_path(report: Dict, path: str) -> bool**
   - Write JSON to specified path
   - Create parent directories if needed
   - Return success/failure

3. **get_builtin_scenarios() -> List[Dict]**
   - Scan scenarios/ directory
   - Load and return scenario metadata
   - Cache results

### Execution Flow

**Scenario Execution**:
```
Import JSON → Validate → Display preview → User specifies output path 
→ Click "Run and save scenario" → Execute suite → Save to path → Show success/error
```

**Report Export**:
```
Run hardcoded suite → Generate results → Specify save path 
→ Click "Save Report (Markdown/JSON)" → Save to path → Show success/error
```

**Template Creation**:
```
Configure UI settings → Specify template save path 
→ Click "Save as Template" → Export settings as JSON → Show success/error
```

All operations share the same UX pattern:
1. Working directory displayed above path input
2. Path specification with cross-session persistence (survives app restarts)
3. Descriptive default filenames with timestamps
4. Success/error feedback

### Persistence Implementation
- Paths stored in `.streamlit_harness_config.json` in project root
- File loaded on app startup, saved whenever paths change
- Config file excluded from git via `.gitignore`
- Ensures user preferences persist across all sessions (browser restarts, terminal restarts, etc.)

## Built-in Scenarios

### Matrix Mode Scenarios

**Scenario A: Phase Weighting Validation - Normal**
- All presets × All phases × Normal mode
- Batch size: 200
- Purpose: Validate phase differentiation

**Scenario B: Phase Weighting Validation - Spiky**
- All presets × All phases × Spiky mode  
- Batch size: 200
- Same seed as Scenario A
- Purpose: Compare rarity mode impact on phases

### Campaign Mode Scenarios

**Scenario C: Campaign Rhythm - Normal Mode**
- 6-scene sequence: Approach → Engage → Aftermath (×2 cycles)
- Preset: Dungeon (consistent environment)
- Rarity mode: Normal
- Batch size: 50 events per scene
- Base seed: 5000
- Purpose: Validate natural escalation/release rhythm across multiple scenes

**Scenario D: Campaign Rhythm - Spiky Mode**
- Same 6-scene sequence as Scenario C
- Rarity mode: Spiky
- Same seed (5000) for direct comparison
- Purpose: Validate pressure spikes occur and release naturally, avoid permanent tension plateaus

## Parking Lot Items

### Deferred to Future Iterations
1. **Directory browser UI**: Visual directory selection for output path
2. **Sea preset support**: Add sea environment to preset options
3. **Full JSON validation**: Validate field types and value ranges
4. **Scenario editor**: In-app JSON editing and creation
5. **Scenario comparison**: Side-by-side result comparison UI

## Campaign Mode Details

### State Carry-Forward Behavior

Campaign mode maintains a single EngineState instance across the entire scene_sequence:
1. Initialize fresh EngineState at start
2. For each scene in sequence:
   - Run batch with current state
   - Apply state_delta from each event
   - Pass evolved state to next scene
3. Export final state and per-scene snapshots

### Output Format

Campaign reports include:
- `execution_mode`: "campaign"
- `scene_count`: Total scenes in sequence
- `batch_size_per_scene`: Events per scene
- `initial_state`: Reference snapshot of fresh state
- `scenes[]`: Ordered array with per-scene results:
  - `step_index`: Sequential position
  - `preset`, `phase`, `rarity_mode`
  - `summary`: Standard metrics (severity, cutoffs, tags)
  - `state_snapshot`: Key state values (tension_clock, heat_clock, cooldown counts)
  - `events` or `events_sample`: Event data
- `final_state`: Complete state after all scenes

### Analysis Capabilities

Campaign mode enables observation of:
- **Rhythm patterns**: Severity trends across scenes (escalation/release)
- **State evolution**: Clock accumulation and decay
- **Tag patterns**: Dominance shifts (e.g., hazard → opportunity → information)
- **Pressure indicators**: Cutoff rates per scene
- **Memory effects**: How earlier scenes affect later ones

## Acceptance Criteria

- ✅ Can load scenario JSON from file upload
- ✅ Can select scenarios from built-in library
- ✅ Required field validation works
- ✅ Results save to user-specified file path
- ✅ Existing suite functionality unchanged
- ✅ Error messages clear and actionable
- ✅ All three save/export operations use unified UX
- ✅ All file paths persist across all sessions (app restarts, browser sessions)
- ✅ Paths stored in `.streamlit_harness_config.json` (excluded from git)
- ✅ Working directory displayed for all save operations
- ✅ Descriptive default filenames generated for all exports
- ✅ Campaign mode executes with shared state
- ✅ Campaign scenarios load and display correctly
- ✅ Campaign reports include per-scene state snapshots

## Technical Constraints

- No engine logic changes
- No changes to result data format
- Maintain determinism (same scenario + seed = same results)
- Handle file I/O errors gracefully

## Files to Modify

1. `streamlit_harness/app.py` - Main implementation
2. `scenarios/` - New directory with built-in scenarios
3. `scenarios/README.md` - Scenario library documentation
4. `PARKING_LOT.md` - Add deferred features
5. `docs/` - This requirements document

## Expected Outcome

Users can define validation scenarios in JSON, import them into the harness, execute them with one click, and have results automatically saved to a specified location - enabling automated validation workflows and reproducible testing.
