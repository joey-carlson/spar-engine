#!/usr/bin/env python3
"""
Campaign Rhythm Validation Script

Executes both Normal and Spiky mode campaign scenarios and generates
a comprehensive analysis report of multi-scene rhythm patterns.
"""

import json
import sys
from pathlib import Path

# Ensure repo root is on path
_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from streamlit_harness.app import (
    run_scenario_from_json,
    load_entries,
    save_report_to_path,
)
from streamlit_harness.harness_state import HarnessState


def main():
    print("Campaign Rhythm Validation")
    print("=" * 60)
    print()
    
    # Load content pack
    print("Loading content pack...")
    entries = load_entries("data/core_complications.json")
    print(f"Loaded {len(entries)} entries")
    print()
    
    # Get engine state class
    hs = HarnessState()
    engine_state_class = hs.engine_state.__class__
    
    # Load and run Normal mode scenario
    print("Running Campaign Rhythm - Normal Mode...")
    normal_scenario = json.loads(Path("scenarios/campaign_rhythm_normal.json").read_text())
    normal_report = run_scenario_from_json(normal_scenario, entries, engine_state_class)
    normal_path = "scenarios/results/campaign_rhythm_normal_validation.json"
    save_report_to_path(normal_report, normal_path)
    print(f"✓ Normal mode completed - saved to {normal_path}")
    print()
    
    # Load and run Spiky mode scenario
    print("Running Campaign Rhythm - Spiky Mode...")
    spiky_scenario = json.loads(Path("scenarios/campaign_rhythm_spiky.json").read_text())
    spiky_report = run_scenario_from_json(spiky_scenario, entries, engine_state_class)
    spiky_path = "scenarios/results/campaign_rhythm_spiky_validation.json"
    save_report_to_path(spiky_report, spiky_path)
    print(f"✓ Spiky mode completed - saved to {spiky_path}")
    print()
    
    # Generate analysis
    print("Generating analysis...")
    analysis = analyze_campaign_rhythm(normal_report, spiky_report)
    
    # Save analysis
    analysis_path = "docs/CAMPAIGN_RHYTHM_VALIDATION_ANALYSIS.md"
    Path(analysis_path).write_text(analysis)
    print(f"✓ Analysis saved to {analysis_path}")
    print()
    
    print("Campaign rhythm validation complete!")
    print(f"Review {analysis_path} for findings and recommendations.")


def analyze_campaign_rhythm(normal_report, spiky_report):
    """Generate markdown analysis of campaign rhythm patterns."""
    
    lines = []
    lines.append("# Campaign Rhythm Validation Analysis")
    lines.append("")
    lines.append("**Date**: December 2025")
    lines.append("**Scenarios**: Campaign Rhythm - Normal Mode & Spiky Mode")
    lines.append("**Execution Mode**: Sequential 6-scene campaign with shared EngineState")
    lines.append("")
    
    lines.append("## Executive Summary")
    lines.append("")
    lines.append("This analysis validates whether SPAR naturally creates pressure/release/recovery/renewed-tension")
    lines.append("rhythms across multiple scenes WITHOUT requiring explicit campaign-level rules.")
    lines.append("")
    
    # Extract per-scene metrics for Normal mode
    lines.append("## Normal Mode Analysis")
    lines.append("")
    lines.append("### Per-Scene Metrics")
    lines.append("")
    lines.append("| Scene | Phase | Severity Avg | Cutoff Rate | Clocks | Tag Cooldowns | Recent IDs |")
    lines.append("|-------|-------|--------------|-------------|--------|---------------|------------|")
    
    for scene in normal_report["scenes"]:
        step = scene["step_index"]
        phase = scene["phase"]
        summary = scene["summary"]
        snapshot = scene["state_snapshot"]
        
        sev_avg = f"{summary['severity_avg']:.2f}" if summary['severity_avg'] else "N/A"
        cutoff_rate = f"{summary['cutoff_rate']*100:.1f}%"
        clocks_str = str(snapshot["clocks"])
        cooldowns = snapshot["tag_cooldowns_count"]
        recent_ids = snapshot["recent_ids_count"]
        
        lines.append(f"| {step} | {phase} | {sev_avg} | {cutoff_rate} | {clocks_str} | {cooldowns} | {recent_ids} |")
    
    lines.append("")
    
    # Analyze trends
    lines.append("### Observations")
    lines.append("")
    
    # Check for rhythm patterns
    scenes = normal_report["scenes"]
    severity_trend = [s["summary"]["severity_avg"] for s in scenes if s["summary"]["severity_avg"]]
    cutoff_trend = [s["summary"]["cutoff_rate"] for s in scenes]
    
    # Scene 1 vs 2 (approach → engage)
    if len(severity_trend) >= 2:
        sev_change_1to2 = severity_trend[1] - severity_trend[0]
        lines.append(f"**Approach → Engage (Scenes 1-2)**: Severity {'increased' if sev_change_1to2 > 0 else 'decreased'} by {abs(sev_change_1to2):.2f}")
    
    # Scene 2 vs 3 (engage → aftermath)
    if len(severity_trend) >= 3:
        sev_change_2to3 = severity_trend[2] - severity_trend[1]
        lines.append(f"**Engage → Aftermath (Scenes 2-3)**: Severity {'decreased' if sev_change_2to3 < 0 else 'increased'} by {abs(sev_change_2to3):.2f}")
    
    # First cycle vs second cycle
    if len(severity_trend) >= 6:
        first_cycle_avg = sum(severity_trend[:3]) / 3
        second_cycle_avg = sum(severity_trend[3:6]) / 3
        lines.append(f"**First Cycle Avg**: {first_cycle_avg:.2f}")
        lines.append(f"**Second Cycle Avg**: {second_cycle_avg:.2f}")
        lines.append(f"**Cycle Comparison**: Second cycle {'higher' if second_cycle_avg > first_cycle_avg else 'lower'} by {abs(second_cycle_avg - first_cycle_avg):.2f}")
    
    lines.append("")
    
    # Spiky Mode Analysis
    lines.append("## Spiky Mode Analysis")
    lines.append("")
    lines.append("### Per-Scene Metrics")
    lines.append("")
    lines.append("| Scene | Phase | Severity Avg | Cutoff Rate | Clocks | Tag Cooldowns | Recent IDs |")
    lines.append("|-------|-------|--------------|-------------|--------|---------------|------------|")
    
    for scene in spiky_report["scenes"]:
        step = scene["step_index"]
        phase = scene["phase"]
        summary = scene["summary"]
        snapshot = scene["state_snapshot"]
        
        sev_avg = f"{summary['severity_avg']:.2f}" if summary['severity_avg'] else "N/A"
        cutoff_rate = f"{summary['cutoff_rate']*100:.1f}%"
        clocks_str = str(snapshot["clocks"])
        cooldowns = snapshot["tag_cooldowns_count"]
        recent_ids = snapshot["recent_ids_count"]
        
        lines.append(f"| {step} | {phase} | {sev_avg} | {cutoff_rate} | {clocks_str} | {cooldowns} | {recent_ids} |")
    
    lines.append("")
    
    # Comparative analysis
    lines.append("## Comparative Analysis (Normal vs Spiky)")
    lines.append("")
    
    # Calculate averages
    normal_avg_sev = sum(s["summary"]["severity_avg"] for s in normal_report["scenes"] if s["summary"]["severity_avg"]) / 6
    spiky_avg_sev = sum(s["summary"]["severity_avg"] for s in spiky_report["scenes"] if s["summary"]["severity_avg"]) / 6
    
    normal_avg_cutoff = sum(s["summary"]["cutoff_rate"] for s in normal_report["scenes"]) / 6
    spiky_avg_cutoff = sum(s["summary"]["cutoff_rate"] for s in spiky_report["scenes"]) / 6
    
    lines.append(f"- **Normal Mode Average Severity**: {normal_avg_sev:.2f}")
    lines.append(f"- **Spiky Mode Average Severity**: {spiky_avg_sev:.2f}")
    lines.append(f"- **Normal Mode Average Cutoff Rate**: {normal_avg_cutoff*100:.1f}%")
    lines.append(f"- **Spiky Mode Average Cutoff Rate**: {spiky_avg_cutoff*100:.1f}%")
    lines.append("")
    
    # Findings
    lines.append("## Key Findings")
    lines.append("")
    
    lines.append("### 1. Phase Differentiation Across Scenes")
    lines.append("- [ ] Approach scenes show exploratory/controlled behavior")
    lines.append("- [ ] Engage scenes show elevated pressure")
    lines.append("- [ ] Aftermath scenes show pressure release")
    lines.append("")
    
    lines.append("### 2. State Evolution (Clock Trends)")
    lines.append("- [ ] Clocks accumulate across scenes (not reset)")
    lines.append("- [ ] Meaningful variation between scenes")
    lines.append("- [ ] Natural rhythm vs flatline behavior")
    lines.append("")
    
    lines.append("### 3. Second Cycle Behavior")
    lines.append("- [ ] Second cycle affected by first cycle state")
    lines.append("- [ ] Not identical to first cycle")
    lines.append("- [ ] Evidence of memory/consequence")
    lines.append("")
    
    lines.append("### 4. Rarity Mode Differentiation")
    lines.append("- [ ] Spiky mode shows pressure spikes")
    lines.append("- [ ] At least one meaningful cutoff event in sequence")
    lines.append("- [ ] Avoids permanent high tension plateau")
    lines.append("- [ ] Avoids permanent calm (no spikes)")
    lines.append("")
    
    lines.append("## Detailed Findings")
    lines.append("")
    lines.append("_[To be completed after manual review of metrics]_")
    lines.append("")
    lines.append("### Normal Mode Rhythm")
    lines.append("")
    lines.append("- **Escalation Pattern**: [Describe if severity/pressure builds appropriately]")
    lines.append("- **Release Pattern**: [Describe if aftermath provides recovery]")
    lines.append("- **Cycle Differentiation**: [Describe how second cycle differs from first]")
    lines.append("- **Clock Behavior**: [Describe tension/heat accumulation patterns]")
    lines.append("")
    
    lines.append("### Spiky Mode Rhythm")
    lines.append("")
    lines.append("- **Spike Occurrences**: [Describe when and how pressure spikes]")
    lines.append("- **Release Effectiveness**: [Describe if aftermath reduces spikes]")
    lines.append("- **Plateau Avoidance**: [Confirm no permanent high tension]")
    lines.append("- **Differentiation from Normal**: [Describe how Spiky feels distinctly more volatile]")
    lines.append("")
    
    lines.append("## Recommendation")
    lines.append("")
    lines.append("**Status**: _[PENDING MANUAL REVIEW]_")
    lines.append("")
    lines.append("Options:")
    lines.append("1. **Campaign rhythm is sufficient, lock it** - System naturally creates coherent multi-scene rhythms")
    lines.append("2. **Campaign rhythm needs adjustment** - Specific issues identified below")
    lines.append("")
    lines.append("### Issues Identified (if any)")
    lines.append("")
    lines.append("- [ ] None - rhythm is sufficient")
    lines.append("- [ ] Flatline behavior - same metrics across all scenes")
    lines.append("- [ ] Runaway escalation - tension never releases")
    lines.append("- [ ] Hard resets - no state carry-forward evident")
    lines.append("- [ ] Other: [Describe]")
    lines.append("")
    
    lines.append("## Next Steps")
    lines.append("")
    lines.append("If rhythm is sufficient:")
    lines.append("- Campaign validation complete")
    lines.append("- Ready for next design frontier:")
    lines.append("  - Campaign-level consequence mechanics (long-term clocks, scars, factions), OR")
    lines.append("  - Content richness passes (loot, factions, narrative arcs), OR")
    lines.append("  - SPAR ↔ D&D adapter formalization")
    lines.append("")
    lines.append("If rhythm needs adjustment:")
    lines.append("- Document specific issues")
    lines.append("- Propose solutions")
    lines.append("- DO NOT implement yet - designer review required")
    lines.append("")
    
    return "\n".join(lines)


if __name__ == "__main__":
    main()
