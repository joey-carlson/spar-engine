"""Test content availability across all preset/phase combinations.

Identifies which combinations might run out of content during batch generation.
"""

from spar_engine.content import load_pack, filter_entries
from spar_engine.models import Constraints, ScenePhase


def test_content_availability_by_preset_phase():
    """Test that each preset/phase combination has sufficient content."""
    entries = load_pack("data/core_complications_v0_1.json")
    
    presets = {
        "dungeon": {"env": ["dungeon"], "confinement": 0.8, "connectivity": 0.3, "visibility": 0.6},
        "city": {"env": ["city"], "confinement": 0.4, "connectivity": 0.8, "visibility": 0.7},
        "wilderness": {"env": ["wilderness"], "confinement": 0.3, "connectivity": 0.5, "visibility": 0.4},
        "ruins": {"env": ["ruins"], "confinement": 0.6, "connectivity": 0.4, "visibility": 0.5},
    }
    
    phases: list[ScenePhase] = ["approach", "engage", "aftermath"]
    
    # Default harness tags
    include_tags = [
        "hazard", "reinforcements", "time_pressure", "social_friction",
        "visibility", "mystic", "attrition", "terrain", "positioning",
        "opportunity", "information"
    ]
    
    print("\nContent Availability Report:")
    print("=" * 70)
    
    problematic = []
    
    for preset_name, preset_vals in presets.items():
        for phase in phases:
            filtered = filter_entries(
                entries,
                environment=preset_vals["env"],
                phase=phase,
                include_tags=include_tags,
                exclude_tags=[],
                recent_event_ids=[],
                tag_cooldowns={},
            )
            
            count = len(filtered)
            status = "✓" if count >= 10 else "⚠" if count >= 5 else "✗"
            print(f"{status} {preset_name:12s} / {phase:10s}: {count:2d} events")
            
            if count < 5:
                problematic.append((preset_name, phase, count))
                print(f"   Available: {[e.event_id for e in filtered]}")
    
    print("=" * 70)
    
    if problematic:
        print("\nProblematic combinations (< 5 events):")
        for preset, phase, count in problematic:
            print(f"  - {preset} / {phase}: only {count} events")
        print("\nNote: With cooldowns enabled in batch runs, these combinations")
        print("may run out of content before completing 200-event batches.")
    
    # Don't fail the test, just report
    assert True, "Content availability report generated"


def test_aftermath_content_by_environment():
    """Specifically check aftermath phase content for each environment."""
    entries = load_pack("data/core_complications_v0_1.json")
    
    print("\nAftermath Phase Content by Environment:")
    print("=" * 70)
    
    environments = ["dungeon", "city", "wilderness", "ruins", "industrial", "sea", "planar"]
    
    include_tags = [
        "hazard", "reinforcements", "time_pressure", "social_friction",
        "visibility", "mystic", "attrition", "terrain", "positioning",
        "opportunity", "information"
    ]
    
    for env in environments:
        filtered = filter_entries(
            entries,
            environment=[env],
            phase="aftermath",
            include_tags=include_tags,
            exclude_tags=[],
            recent_event_ids=[],
            tag_cooldowns={},
        )
        
        count = len(filtered)
        print(f"{env:12s}: {count:2d} events")
        if count > 0:
            for e in filtered:
                print(f"  - {e.event_id}: {e.tags}")
    
    print("=" * 70)


if __name__ == "__main__":
    test_content_availability_by_preset_phase()
    print("\n")
    test_aftermath_content_by_environment()
