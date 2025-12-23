"""Test cutoff tuning for Spiky rarity mode.

Validates that the new cap adjustments produce target cutoff rates:
- Spiky: 5-10% for dungeon/ruins, 2-5% for wilderness
- Normal: ≤3% for all presets
- Calm: ≤1% for all presets
"""

from spar_engine.content import load_pack
from spar_engine.engine import generate_event
from spar_engine.models import (
    Constraints,
    EngineState,
    SceneContext,
    SelectionContext,
)
from spar_engine.rng import TraceRNG


def count_cutoffs(
    preset_name: str,
    environment: list[str],
    constraints: Constraints,
    rarity_mode: str,
    num_samples: int = 200,
    seed: int = 42,
) -> tuple[int, float]:
    """Generate events and count cutoff rate."""
    entries = load_pack("data/core_complications_v0_1.json")
    
    cutoff_count = 0
    for i in range(num_samples):
        rng = TraceRNG(seed=seed + i)
        scene = SceneContext(
            scene_id=f"test_{preset_name}_{i}",
            scene_phase="engage",
            environment=environment,
            tone=["gritty"],
            constraints=constraints,
            party_band="mid",
            spotlight=["combat"],
        )
        state = EngineState.default()
        sel = SelectionContext(
            enabled_packs=["core_complications_v0_1"],
            include_tags=[],
            exclude_tags=[],
            factions_present=[],
            rarity_mode=rarity_mode,
        )
        
        event = generate_event(scene, state, sel, entries, rng)
        if event.cutoff_applied:
            cutoff_count += 1
    
    cutoff_rate = (cutoff_count / num_samples) * 100
    return cutoff_count, cutoff_rate


def test_spiky_dungeon_cutoff_rate():
    """Spiky dungeon should have 5-10% cutoff rate."""
    constraints = Constraints(confinement=0.8, connectivity=0.2, visibility=0.7)
    _, rate = count_cutoffs("dungeon", ["dungeon"], constraints, "spiky")
    print(f"Spiky dungeon cutoff rate: {rate:.1f}%")
    assert 5.0 <= rate <= 10.0, f"Expected 5-10%, got {rate:.1f}%"


def test_spiky_ruins_cutoff_rate():
    """Spiky ruins should have 5-10% cutoff rate."""
    constraints = Constraints(confinement=0.7, connectivity=0.3, visibility=0.6)
    _, rate = count_cutoffs("ruins", ["ruins"], constraints, "spiky")
    print(f"Spiky ruins cutoff rate: {rate:.1f}%")
    assert 5.0 <= rate <= 10.0, f"Expected 5-10%, got {rate:.1f}%"


def test_spiky_wilderness_cutoff_rate():
    """Spiky wilderness should have 2-5% cutoff rate."""
    constraints = Constraints(confinement=0.3, connectivity=0.6, visibility=0.4)
    _, rate = count_cutoffs("wilderness", ["wilderness"], constraints, "spiky")
    print(f"Spiky wilderness cutoff rate: {rate:.1f}%")
    assert 2.0 <= rate <= 5.0, f"Expected 2-5%, got {rate:.1f}%"


def test_normal_dungeon_cutoff_rate():
    """Normal dungeon should have ≤3% cutoff rate."""
    constraints = Constraints(confinement=0.8, connectivity=0.2, visibility=0.7)
    _, rate = count_cutoffs("dungeon", ["dungeon"], constraints, "normal")
    print(f"Normal dungeon cutoff rate: {rate:.1f}%")
    assert rate <= 3.0, f"Expected ≤3%, got {rate:.1f}%"


def test_normal_wilderness_cutoff_rate():
    """Normal wilderness should have ≤3% cutoff rate."""
    constraints = Constraints(confinement=0.3, connectivity=0.6, visibility=0.4)
    _, rate = count_cutoffs("wilderness", ["wilderness"], constraints, "normal")
    print(f"Normal wilderness cutoff rate: {rate:.1f}%")
    assert rate <= 3.0, f"Expected ≤3%, got {rate:.1f}%"


def test_calm_dungeon_cutoff_rate():
    """Calm dungeon should have ≤1% cutoff rate."""
    constraints = Constraints(confinement=0.8, connectivity=0.2, visibility=0.7)
    _, rate = count_cutoffs("dungeon", ["dungeon"], constraints, "calm")
    print(f"Calm dungeon cutoff rate: {rate:.1f}%")
    assert rate <= 1.0, f"Expected ≤1%, got {rate:.1f}%"


def test_calm_wilderness_cutoff_rate():
    """Calm wilderness should have ≤1% cutoff rate."""
    constraints = Constraints(confinement=0.3, connectivity=0.6, visibility=0.4)
    _, rate = count_cutoffs("wilderness", ["wilderness"], constraints, "calm")
    print(f"Calm wilderness cutoff rate: {rate:.1f}%")
    assert rate <= 1.0, f"Expected ≤1%, got {rate:.1f}%"


def test_rarity_mode_cutoff_differences():
    """Verify cutoff rates differ meaningfully between rarity modes."""
    dungeon_constraints = Constraints(confinement=0.8, connectivity=0.2, visibility=0.7)
    
    _, calm_rate = count_cutoffs("dungeon", ["dungeon"], dungeon_constraints, "calm")
    _, normal_rate = count_cutoffs("dungeon", ["dungeon"], dungeon_constraints, "normal")
    _, spiky_rate = count_cutoffs("dungeon", ["dungeon"], dungeon_constraints, "spiky")
    
    print(f"Dungeon cutoff rates - Calm: {calm_rate:.1f}%, Normal: {normal_rate:.1f}%, Spiky: {spiky_rate:.1f}%")
    
    assert calm_rate < normal_rate < spiky_rate, (
        f"Expected calm < normal < spiky, got calm={calm_rate:.1f}%, "
        f"normal={normal_rate:.1f}%, spiky={spiky_rate:.1f}%"
    )


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s"])
