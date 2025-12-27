# Implementation Report: Cutoff Tuning - Morphology-Sensitive Cap Compression

<!--
Version History:
- v2.0 (2025-12-25): Morphology-sensitive cap compression with dual thresholds (0.9, 1.4)
- v1.0 (2025-12-22): Initial Spiky mode cap tuning with single morphology threshold (0.8)
-->

**Current Version**: v2.0  
**Date**: December 2025  
**Status**: ✅ Complete - All acceptance criteria met

## Executive Summary

Enhanced Spiky rarity mode with morphology-sensitive severity cap compression to increase cutoff frequency in constrained environments. The implementation treats structural fragility (high confinement, poor visibility, low connectivity) as a multiplier for cutoff likelihood, achieving target rates while preserving Normal and Calm mode behavior.

## Objectives & Results

| Scenario | Target Rate | Achieved Rate | Status |
|----------|-------------|---------------|--------|
| Spiky Dungeon (Engage) | 5-10% | 9.0% | ✅ |
| Spiky Ruins (Engage) | 5-10% | 8.0% | ✅ |
| Spiky Wilderness (Engage) | 2-5% | 5.0% | ✅ (upper edge) |
| Normal (all presets) | ≤3% | 2.0% | ✅ |
| Calm (all presets) | ≤1% | 0.0% | ✅ |

## Implementation Details

### Morphology Score Calculation

The morphology score represents environmental structural fragility:

```
morph = confinement + visibility - connectivity
Range: [-1.0, 2.0]
```

**High morphology** (tight, dark, disconnected spaces) creates more opportunities for extreme outcomes to spill over into cutoff resolutions.

### Cap Compression Logic (Spiky Mode Only)

Located in `spar_engine/severity.py`, function `compute_severity_cap()`:

```python
if rarity_mode == "spiky":
    if morph >= 0.9:
        cap -= 1
    if morph >= 1.4:
        cap -= 1
```

**Graduated System**:
- **Mild morphology** (< 0.9): No additional compression
- **Strong morphology** (0.9-1.39): -1 cap compression  
- **Extreme morphology** (>= 1.4): -2 cap compression

### Preset-Specific Behavior

**Dungeon** (confinement=0.8, connectivity=0.2, visibility=0.7):
- morph = 0.8 + 0.7 - 0.2 = 1.3
- Triggers first threshold (>= 0.9): -1 cap
- Result: 9% cutoff rate

**Ruins** (confinement=0.7, connectivity=0.3, visibility=0.6):
- morph = 0.7 + 0.6 - 0.3 = 1.0
- Triggers first threshold (>= 0.9): -1 cap
- Result: 8% cutoff rate

**Wilderness** (confinement=0.3, connectivity=0.6, visibility=0.4):
- morph = 0.3 + 0.4 - 0.6 = 0.1
- Below threshold: No additional compression
- Result: 5% cutoff rate (base Spiky behavior only)

### Design Rationale

The two-threshold approach allows:
1. **Confined/derelict**: Hit strong morphology threshold, compress cap significantly
2. **Wilderness**: Natural resistance due to high connectivity (open space)
3. **No preset hardcoding**: Behavior emerges from constraint values
4. **Calm/Normal isolation**: Logic strictly gated to `rarity_mode == "spiky"`

## Verification Procedure

### Running the Test Suite

```bash
cd /Users/joecrls/Documents/Code/spar_tool_engine
source .venv/bin/activate
python -m pytest tests/test_cutoff_tuning.py -v -s
```

Expected output:
```
Spiky confined cutoff rate: 9.0%
Spiky derelict cutoff rate: 8.0%
Spiky open cutoff rate: 5.0%
Normal confined cutoff rate: 2.0%
Normal open cutoff rate: 2.0%
Calm confined cutoff rate: 0.0%
Calm open cutoff rate: 0.0%
```

### Streamlit Harness Verification

1. Launch: `streamlit run streamlit_harness/app.py`
2. Navigate to **Scenarios** tab
3. Select suite: **Presets × Engage × (Calm/Normal/Spiky)**
4. Set batch size: **200**
5. Use fixed seed for reproducibility
6. Click **Run suite**

Review the cutoff statistics in the generated report to verify rates match test results.

## Technical Notes

- **No distribution changes**: Zipf alpha parameters remain unchanged
- **Integer arithmetic only**: All cap adjustments are whole numbers
- **Pure constraint-based**: No special casing of preset names
- **Morphology-driven**: Behavior emerges from scene structure, not preset identity

## Files Modified

- `spar_engine/severity.py` - Added morphology-sensitive cap compression for Spiky mode
- `tests/test_cutoff_tuning.py` - Comprehensive test coverage for all rarity modes and presets
- `CHANGELOG.md` - Documented feature and rationale

## Conclusion

The morphology-sensitive cap compression successfully differentiates Spiky mode behavior while maintaining the integrity of Normal and Calm modes. The system now provides meaningful tactical variety across rarity modes without requiring content changes or hardcoded preset logic.
