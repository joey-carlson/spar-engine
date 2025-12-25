# Campaign Rhythm Runner - Design Proposal

## Problem Statement

Current scenario runner cannot validate multi-scene campaign rhythm because:
1. Each run creates fresh engine state (`engine_state_class.default()`)
2. Phases execute as permutations (all presets × all phases × all rarity_modes)
3. No way to observe state evolution across sequential phases

Campaign validation requires:
- Sequential execution: Approach → Engage → Aftermath (repeat 2x)
- Single shared EngineState across entire sequence
- Per-scene metrics to observe rhythm patterns

## Proposed Solution

### Schema Extension

Add optional `execution_mode` field to scenario JSON:

```json
{
  "execution_mode": "campaign",  // NEW: "standard" (default) or "campaign"
  "scene_sequence": [             // NEW: Ordered list of scenes for campaign mode
    {"preset": "dungeon", "phase": "approach"},
    {"preset": "dungeon", "phase": "engage"},
    {"preset": "dungeon", "phase": "aftermath"},
    {"preset": "dungeon", "phase": "approach"},
    {"preset": "dungeon", "phase": "engage"},
    {"preset": "dungeon", "phase": "aftermath"}
  ],
  "rarity_modes": ["normal"],     // Applied to all scenes in sequence
  "batch_size": 50,               // Events per scene
  // ... other standard fields
}
```

### Runner Changes

Modify `run_scenario_from_json()` to support two modes:

**Standard Mode** (existing behavior):
- Cartesian product of presets × phases × rarity_modes
- Fresh state per run
- Good for phase isolation testing

**Campaign Mode** (new):
- Sequential execution following `scene_sequence` order
- Single shared state across all scenes
- Each scene uses same rarity_mode(s)
- Report includes per-scene metrics for rhythm analysis

### Implementation Approach

```python
def run_scenario_from_json(scenario, entries, engine_state_class):
    execution_mode = scenario.get("execution_mode", "standard")
    
    if execution_mode == "campaign":
        return run_campaign_scenario(scenario, entries, engine_state_class)
    else:
        return run_standard_scenario(scenario, entries, engine_state_class)

def run_campaign_scenario(scenario, entries, engine_state_class):
    """Execute scenes sequentially with shared state."""
    shared_state = engine_state_class.default()  # Single state for entire campaign
    scenes = scenario["scene_sequence"]
    
    report = {
        "execution_mode": "campaign",
        "scenes": []  # Per-scene results
    }
    
    for scene_idx, scene_def in enumerate(scenes):
        # Run batch with current shared state
        result = run_batch(
            scene=create_scene_context(scene_def),
            state=shared_state,  # Pass current state
            ...
        )
        # Update shared state from result
        shared_state = result["final_state"]
        
        report["scenes"].append({
            "scene_number": scene_idx + 1,
            "preset": scene_def["preset"],
            "phase": scene_def["phase"],
            "result": result
        })
    
    return report
```

## Benefits

1. **Backward Compatible**: Existing scenarios work unchanged (default to standard mode)
2. **Minimal Changes**: New mode is isolated, doesn't affect existing validation
3. **Clear Semantics**: `scene_sequence` makes execution order explicit
4. **Flexible**: Can model various campaign patterns (not just 2x cycles)

## Example Campaign Scenarios

### Scenario C: Campaign Rhythm - Normal
```json
{
  "schema_version": "1.0",
  "execution_mode": "campaign",
  "name": "Campaign Rhythm - Normal Mode",
  "description": "Validates narrative rhythm across 6-scene sequence (2 full cycles)",
  "output_basename": "campaign_rhythm_normal",
  
  "scene_sequence": [
    {"preset": "dungeon", "phase": "approach"},
    {"preset": "dungeon", "phase": "engage"},
    {"preset": "dungeon", "phase": "aftermath"},
    {"preset": "dungeon", "phase": "approach"},
    {"preset": "dungeon", "phase": "engage"},
    {"preset": "dungeon", "phase": "aftermath"}
  ],
  
  "rarity_modes": ["normal"],
  "batch_size": 50,
  "base_seed": 5000,
  "tick_between": true,
  "ticks_between": 1,
  "verbose": false
}
```

### Scenario D: Campaign Rhythm - Spiky
```json
{
  "execution_mode": "campaign",
  "name": "Campaign Rhythm - Spiky Mode",
  "scene_sequence": [/* same as Scenario C */],
  "rarity_modes": ["spiky"],
  "base_seed": 5000,  // Same seed for comparison
  // ... rest same as Scenario C
}
```

## Analysis Capabilities

With campaign mode, we can track:
- **Per-scene metrics**: severity_avg, cutoff_rate per scene
- **State evolution**: tension/heat trends across scenes
- **Tag patterns**: Dominance shifts (hazard → opportunity → information)
- **Rhythm detection**: Escalation/release patterns

Example analysis:
```
Scene 1 (Approach): severity_avg=3.2, cutoff_rate=5%, tension=low
Scene 2 (Engage):   severity_avg=5.8, cutoff_rate=12%, tension=high
Scene 3 (Aftermath): severity_avg=4.1, cutoff_rate=8%, tension=medium
Scene 4 (Approach): severity_avg=3.8, cutoff_rate=6%, tension=medium (affected by previous)
Scene 5 (Engage):   severity_avg=6.2, cutoff_rate=15%, tension=very_high (escalation)
Scene 6 (Aftermath): severity_avg=4.5, cutoff_rate=9%, tension=medium (release)
```

## Decision Required

This extension is minimal and focused, but it does modify the scenario runner.

Options:
1. **Implement campaign mode** (recommended for proper validation)
2. **Use workaround**: Run phases manually in UI, tracking state across runs
3. **Defer campaign validation** until runner supports it

Given the task's importance for determining SPAR's next design frontier, Option 1 seems warranted.

What would you like me to do?
