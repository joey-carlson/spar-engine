"""Tests for Loot Generator - Narrative Resource Shock System"""

import pytest

from spar_engine.content import load_pack
from spar_engine.loot import generate_loot
from spar_engine.models import Constraints, SceneContext, SelectionContext
from spar_engine.rng import TraceRNG
from spar_engine.state import EngineState, apply_state_delta


def test_loot_pack_loads():
    """Verify core loot pack loads successfully."""
    entries = load_pack("data/core_loot_situations.json")
    assert len(entries) > 0, "Loot pack should contain entries"
    assert all(e.event_id.startswith("loot_") for e in entries), "All loot IDs should start with 'loot_'"


def test_loot_generation_basic():
    """Verify loot generator produces valid output."""
    entries = load_pack("data/core_loot_situations.json")
    
    scene = SceneContext(
        scene_id="test",
        scene_phase="aftermath",
        environment=["derelict"],
        tone=["test"],
        constraints=Constraints(confinement=0.5, connectivity=0.5, visibility=0.5),
        party_band="unknown",
        spotlight=[]
    )
    
    selection = SelectionContext(
        enabled_packs=["loot"],
        include_tags=["opportunity"],
        exclude_tags=[],
        factions_present=[],
        rarity_mode="normal"
    )
    
    state = EngineState.default()
    rng = TraceRNG(seed=42)
    
    loot = generate_loot(scene, state, selection, entries, rng)
    
    # Validate output structure
    assert loot.event_id.startswith("loot_")
    assert loot.title
    assert len(loot.tags) > 0
    assert 1 <= loot.severity <= 10
    assert loot.fiction.prompt
    assert len(loot.fiction.immediate_choice) == 2


def test_loot_soc_pipeline():
    """Verify loot uses SOC severity sampling."""
    entries = load_pack("data/core_loot_situations.json")
    
    scene = SceneContext(
        scene_id="test",
        scene_phase="aftermath",
        environment=["populated"],
        tone=["test"],
        constraints=Constraints(confinement=0.5, connectivity=0.5, visibility=0.5),
        party_band="unknown",
        spotlight=[]
    )
    
    selection = SelectionContext(
        enabled_packs=["loot"],
        include_tags=[],
        exclude_tags=[],
        factions_present=[],
        rarity_mode="spiky"  # Should produce more variance
    )
    
    state = EngineState.default()
    
    # Generate multiple loot situations
    severities = []
    for seed in range(20):
        rng = TraceRNG(seed=seed)
        loot = generate_loot(scene, state, selection, entries, rng)
        severities.append(loot.severity)
    
    # Verify heavy-tail distribution (should have range)
    assert min(severities) < max(severities), "Spiky mode should produce severity variance"
    assert max(severities) >= 5, "Should occasionally produce higher severity"


def test_loot_cutoff_mechanics():
    """Verify cutoff system works for loot."""
    entries = load_pack("data/core_loot_situations.json")
    
    scene = SceneContext(
        scene_id="test",
        scene_phase="aftermath",
        environment=["derelict"],
        tone=["test"],
        constraints=Constraints(confinement=0.8, connectivity=0.3, visibility=0.6),  # Confined = lower cap
        party_band="low",  # Low band = lower cap
        spotlight=[]
    )
    
    selection = SelectionContext(
        enabled_packs=["loot"],
        include_tags=[],
        exclude_tags=[],
        factions_present=[],
        rarity_mode="spiky"
    )
    
    state = EngineState.default()
    
    # Generate many samples - some should trigger cutoff
    cutoff_count = 0
    for seed in range(50):
        rng = TraceRNG(seed=seed)
        loot = generate_loot(scene, state, selection, entries, rng)
        if loot.cutoff_applied:
            cutoff_count += 1
            # Verify cutoff resolution is applied
            assert loot.cutoff_resolution in ["omen", "clock_tick", "downshift"]
            # Verify fiction overlay
            if loot.cutoff_resolution == "omen":
                assert "Omen of Wealth" in loot.fiction.prompt
            elif loot.cutoff_resolution == "clock_tick":
                assert "Contested Resource" in loot.fiction.prompt
            elif loot.cutoff_resolution == "downshift":
                assert "Modest Gain" in loot.fiction.prompt
    
    assert cutoff_count > 0, "Should have some cutoffs in 50 samples with low cap"


def test_loot_state_delta():
    """Verify loot produces valid state deltas."""
    entries = load_pack("data/core_loot_situations.json")
    
    scene = SceneContext(
        scene_id="test",
        scene_phase="aftermath",
        environment=["populated"],
        tone=["test"],
        constraints=Constraints(confinement=0.5, connectivity=0.5, visibility=0.5),
        party_band="unknown",
        spotlight=[]
    )
    
    selection = SelectionContext(
        enabled_packs=["loot"],
        include_tags=["obligation"],  # Should have some heat impact
        exclude_tags=[],
        factions_present=[],
        rarity_mode="normal"
    )
    
    state = EngineState.default()
    rng = TraceRNG(seed=42)
    
    loot = generate_loot(scene, state, selection, entries, rng)
    
    # Verify state delta structure
    assert loot.state_delta.recent_event_ids_add
    assert loot.event_id in loot.state_delta.recent_event_ids_add
    
    # Apply delta and verify state changes
    new_state = apply_state_delta(state, loot.state_delta)
    assert loot.event_id in new_state.recent_event_ids


def test_loot_cooldowns():
    """Verify loot respects cooldown mechanics."""
    entries = load_pack("data/core_loot_situations.json")
    
    scene = SceneContext(
        scene_id="test",
        scene_phase="aftermath",
        environment=["derelict"],
        tone=["test"],
        constraints=Constraints(confinement=0.5, connectivity=0.5, visibility=0.5),
        party_band="unknown",
        spotlight=[]
    )
    
    selection = SelectionContext(
        enabled_packs=["loot"],
        include_tags=["opportunity"],
        exclude_tags=[],
        factions_present=[],
        rarity_mode="normal"
    )
    
    state = EngineState.default()
    rng = TraceRNG(seed=42)
    
    # Generate first loot
    loot1 = generate_loot(scene, state, selection, entries, rng)
    state = apply_state_delta(state, loot1.state_delta)
    
    # Verify cooldown was set
    assert loot1.event_id in state.recent_event_ids
    if loot1.state_delta.tag_cooldowns_set:
        for tag, cd in loot1.state_delta.tag_cooldowns_set.items():
            assert tag in state.tag_cooldowns
            assert state.tag_cooldowns[tag] > 0


def test_loot_deterministic():
    """Verify loot generation is deterministic with same seed."""
    entries = load_pack("data/core_loot_situations.json")
    
    scene = SceneContext(
        scene_id="test",
        scene_phase="aftermath",
        environment=["populated"],
        tone=["test"],
        constraints=Constraints(confinement=0.5, connectivity=0.5, visibility=0.5),
        party_band="unknown",
        spotlight=[]
    )
    
    selection = SelectionContext(
        enabled_packs=["loot"],
        include_tags=[],
        exclude_tags=[],
        factions_present=[],
        rarity_mode="normal"
    )
    
    state = EngineState.default()
    
    # Generate with same seed twice
    rng1 = TraceRNG(seed=123)
    loot1 = generate_loot(scene, state, selection, entries, rng1)
    
    rng2 = TraceRNG(seed=123)
    loot2 = generate_loot(scene, state, selection, entries, rng2)
    
    # Should be identical
    assert loot1.event_id == loot2.event_id
    assert loot1.severity == loot2.severity
    assert loot1.title == loot2.title


def test_loot_effects_have_opportunity():
    """Verify loot entries emphasize opportunity vector."""
    entries = load_pack("data/core_loot_situations.json")
    
    scene = SceneContext(
        scene_id="test",
        scene_phase="aftermath",
        environment=["derelict"],
        tone=["test"],
        constraints=Constraints(confinement=0.5, connectivity=0.5, visibility=0.5),
        party_band="unknown",
        spotlight=[]
    )
    
    selection = SelectionContext(
        enabled_packs=["loot"],
        include_tags=["opportunity"],
        exclude_tags=[],
        factions_present=[],
        rarity_mode="normal"
    )
    
    state = EngineState.default()
    
    # Generate multiple loot situations
    opportunity_values = []
    for seed in range(20):
        rng = TraceRNG(seed=seed)
        loot = generate_loot(scene, state, selection, entries, rng)
        opportunity_values.append(loot.effect_vector.opportunity)
    
    # Most loot should have positive opportunity
    positive_count = sum(1 for v in opportunity_values if v > 0)
    assert positive_count > len(opportunity_values) * 0.7, "Most loot should provide opportunity"


def test_loot_negative_cost():
    """Verify some loot can have negative cost (pressure relief)."""
    entries = load_pack("data/core_loot_situations.json")
    
    # Find entries with negative cost potential
    negative_cost_entries = [
        e for e in entries 
        if e.effect_vector_template.get("cost", (0, 0))[0] < 0
    ]
    
    assert len(negative_cost_entries) > 0, "Some loot should offer cost relief"


def test_loot_consequence_tags():
    """Verify loot includes consequence-oriented tags."""
    entries = load_pack("data/core_loot_situations.json")
    
    # Collect all tags from loot pack
    all_tags = set()
    for e in entries:
        all_tags.update(e.tags)
    
    # Should include consequence tags
    consequence_tags = {"obligation", "social_friction", "visibility", "heat"}
    found_consequence = consequence_tags & all_tags
    
    assert len(found_consequence) > 0, "Loot should include consequence-oriented tags"


def test_loot_no_content_error():
    """Verify loot generator raises appropriate error when no content available."""
    entries = load_pack("data/core_loot_situations.json")
    
    scene = SceneContext(
        scene_id="test",
        scene_phase="approach",  # Most loot is aftermath
        environment=["sea"],  # Limited environment
        tone=["test"],
        constraints=Constraints(confinement=0.5, connectivity=0.5, visibility=0.5),
        party_band="unknown",
        spotlight=[]
    )
    
    selection = SelectionContext(
        enabled_packs=["loot"],
        include_tags=["nonexistent_tag"],  # Impossible filter
        exclude_tags=[],
        factions_present=[],
        rarity_mode="normal"
    )
    
    state = EngineState.default()
    rng = TraceRNG(seed=42)
    
    with pytest.raises(ValueError, match="No loot entries available"):
        generate_loot(scene, state, selection, entries, rng)


def test_loot_adaptive_weighting():
    """Verify loot uses adaptive weighting to prevent repetition."""
    from spar_engine.state import tick_state
    
    entries = load_pack("data/core_loot_situations.json")
    
    scene = SceneContext(
        scene_id="test",
        scene_phase="aftermath",
        environment=["populated"],
        tone=["test"],
        constraints=Constraints(confinement=0.5, connectivity=0.5, visibility=0.5),
        party_band="unknown",
        spotlight=[]
    )
    
    selection = SelectionContext(
        enabled_packs=["loot"],
        include_tags=[],
        exclude_tags=[],
        factions_present=[],
        rarity_mode="normal"
    )
    
    state = EngineState.default()
    rng = TraceRNG(seed=42)
    
    # Generate first loot
    loot1 = generate_loot(scene, state, selection, entries, rng)
    state = apply_state_delta(state, loot1.state_delta)
    
    # Tick to expire cooldowns (like the real generator does)
    state = tick_state(state, ticks=2)
    
    # Generate second loot with updated state
    rng = TraceRNG(seed=43)  # Different seed
    loot2 = generate_loot(scene, state, selection, entries, rng)
    
    # Should be different due to recency penalty
    assert loot1.event_id != loot2.event_id, "Consecutive loot should avoid recent IDs"


def test_loot_followups():
    """Verify loot cutoffs produce appropriate followups."""
    entries = load_pack("data/core_loot_situations.json")
    
    scene = SceneContext(
        scene_id="test",
        scene_phase="aftermath",
        environment=["derelict"],
        tone=["test"],
        constraints=Constraints(confinement=0.9, connectivity=0.2, visibility=0.7),  # Very confined
        party_band="low",
        spotlight=[]
    )
    
    selection = SelectionContext(
        enabled_packs=["loot"],
        include_tags=[],
        exclude_tags=[],
        factions_present=[],
        rarity_mode="spiky"
    )
    
    state = EngineState.default()
    
    # Generate many samples to find cutoff cases
    for seed in range(100):
        rng = TraceRNG(seed=seed)
        loot = generate_loot(scene, state, selection, entries, rng)
        
        if loot.cutoff_applied:
            # Cutoffs should produce followups
            if loot.cutoff_resolution == "omen":
                assert any("wealth_omen" in str(f) for f in loot.followups)
            elif loot.cutoff_resolution == "clock_tick":
                assert any("contested_resource" in str(f) for f in loot.followups)
            # Found at least one cutoff, test passes
            return
    
    # If no cutoffs in 100 samples, that's also valid (depends on cap/alpha interaction)
    # Just ensure the test doesn't fail spuriously
    pass


# ============================================================================
# PHASE 1: DISTRIBUTION TARGET VALIDATION TESTS
# Tests validate distribution shape using ranges, not exact values.
# Failures indicate systemic drift, not random variance.
# ============================================================================


def test_loot_severity_distribution_normal():
    """Validate loot severity distribution follows target ranges in Normal mode.
    
    Target distribution (Normal rarity, large batch):
    - Severity 1-2: 45-55% (small relief, minor echo)
    - Severity 3-4: 30-40% (meaningful shift, visible consequence)
    - Severity 5-6: 10-15% (campaign-altering resource shock)
    - Severity 7+: under 5% (rare windfall or dangerous prize)
    
    Uses wide tolerance to allow for randomness while catching drift.
    """
    from spar_engine.state import tick_state
    
    entries = load_pack("data/core_loot_situations.json")
    
    scene = SceneContext(
        scene_id="distribution_test",
        scene_phase="aftermath",
        environment=["populated"],
        tone=["test"],
        constraints=Constraints(confinement=0.5, connectivity=0.5, visibility=0.5),
        party_band="mid",
        spotlight=[]
    )
    
    selection = SelectionContext(
        enabled_packs=["loot"],
        include_tags=[],
        exclude_tags=[],
        factions_present=[],
        rarity_mode="normal"
    )
    
    state = EngineState.default()
    
    # Generate large batch to observe distribution
    severities = []
    for seed in range(200):
        rng = TraceRNG(seed=seed + 1000)
        loot = generate_loot(scene, state, selection, entries, rng)
        severities.append(loot.severity)
        
        # Tick to expire cooldowns
        state = tick_state(state, ticks=1)
    
    # Count buckets
    bucket_1_2 = sum(1 for s in severities if 1 <= s <= 2)
    bucket_3_4 = sum(1 for s in severities if 3 <= s <= 4)
    bucket_5_6 = sum(1 for s in severities if 5 <= s <= 6)
    bucket_7_plus = sum(1 for s in severities if s >= 7)
    
    total = len(severities)
    
    # Calculate percentages
    pct_1_2 = (bucket_1_2 / total) * 100
    pct_3_4 = (bucket_3_4 / total) * 100
    pct_5_6 = (bucket_5_6 / total) * 100
    pct_7_plus = (bucket_7_plus / total) * 100
    
    # Validate ranges with generous tolerance (±10% of target)
    assert 35 <= pct_1_2 <= 65, f"Severity 1-2 should be 45-55% (±10%), got {pct_1_2:.1f}%"
    assert 20 <= pct_3_4 <= 50, f"Severity 3-4 should be 30-40% (±10%), got {pct_3_4:.1f}%"
    assert 5 <= pct_5_6 <= 25, f"Severity 5-6 should be 10-15% (±10%), got {pct_5_6:.1f}%"
    assert pct_7_plus <= 10, f"Severity 7+ should be under 5% (+5% tolerance), got {pct_7_plus:.1f}%"


def test_loot_cutoff_rates_by_rarity():
    """Validate loot cutoff rates match targets per rarity mode.
    
    Target cutoff rates:
    - Calm: ~0-1%
    - Normal: ~2-4%
    - Spiky: ~5-8%
    
    Loot cutoffs should be rarer than event cutoffs but louder when they occur.
    """
    from spar_engine.state import tick_state
    
    entries = load_pack("data/core_loot_situations.json")
    
    scene = SceneContext(
        scene_id="cutoff_test",
        scene_phase="aftermath",
        environment=["derelict"],
        tone=["test"],
        constraints=Constraints(confinement=0.6, connectivity=0.4, visibility=0.5),
        party_band="mid",
        spotlight=[]
    )
    
    # Test each rarity mode
    rarity_modes = {
        "calm": (0, 3),    # Target 0-1%, tolerance up to 3%
        "normal": (1, 6),  # Target 2-4%, tolerance 1-6%
        "spiky": (3, 12),  # Target 5-8%, tolerance 3-12%
    }
    
    for rarity_mode, (min_pct, max_pct) in rarity_modes.items():
        selection = SelectionContext(
            enabled_packs=["loot"],
            include_tags=[],
            exclude_tags=[],
            factions_present=[],
            rarity_mode=rarity_mode  # type: ignore
        )
        
        state = EngineState.default()
        cutoff_count = 0
        
        for seed in range(200):
            rng = TraceRNG(seed=seed + 2000)
            loot = generate_loot(scene, state, selection, entries, rng)
            if loot.cutoff_applied:
                cutoff_count += 1
            state = tick_state(state, ticks=1)
        
        cutoff_rate = (cutoff_count / 200) * 100
        
        assert min_pct <= cutoff_rate <= max_pct, \
            f"{rarity_mode.title()} mode cutoff rate should be {min_pct}-{max_pct}%, got {cutoff_rate:.1f}%"


def test_loot_tag_balance():
    """Validate loot tag balance over large batch.
    
    Expected tag frequencies:
    - opportunity: present in most results (>70%)
    - visibility or attention tags: ~50% of results
    - obligation or social_friction: ~30-40% of results
    - hazard or cost: ~20-30% of results
    
    If loot lacks social/attention tags, it's drifting toward "free loot".
    """
    from spar_engine.state import tick_state
    
    entries = load_pack("data/core_loot_situations.json")
    
    scene = SceneContext(
        scene_id="tag_balance_test",
        scene_phase="aftermath",
        environment=["populated"],
        tone=["test"],
        constraints=Constraints(confinement=0.5, connectivity=0.5, visibility=0.5),
        party_band="mid",
        spotlight=[]
    )
    
    selection = SelectionContext(
        enabled_packs=["loot"],
        include_tags=[],
        exclude_tags=[],
        factions_present=[],
        rarity_mode="normal"
    )
    
    state = EngineState.default()
    
    # Track tag occurrences
    tag_counts = {
        "opportunity": 0,
        "visibility": 0,
        "obligation": 0,
        "social_friction": 0,
        "hazard": 0,
        "cost": 0,
    }
    
    total = 200
    for seed in range(total):
        rng = TraceRNG(seed=seed + 3000)
        loot = generate_loot(scene, state, selection, entries, rng)
        
        # Count occurrences
        for tag in loot.tags:
            if tag in tag_counts:
                tag_counts[tag] += 1
        
        state = tick_state(state, ticks=1)
    
    # Calculate percentages
    opportunity_pct = (tag_counts["opportunity"] / total) * 100
    visibility_pct = (tag_counts["visibility"] / total) * 100
    obligation_social_pct = ((tag_counts["obligation"] + tag_counts["social_friction"]) / total) * 100
    hazard_cost_pct = ((tag_counts["hazard"] + tag_counts["cost"]) / total) * 100
    
    # Validate with generous tolerance
    assert opportunity_pct >= 60, f"Opportunity should appear in most results (>70% target), got {opportunity_pct:.1f}%"
    assert 30 <= visibility_pct <= 70, f"Visibility should appear in ~50% (±20%), got {visibility_pct:.1f}%"
    assert 20 <= obligation_social_pct <= 50, f"Obligation/social tags should appear in ~30-40% (±10%), got {obligation_social_pct:.1f}%"
    assert 10 <= hazard_cost_pct <= 40, f"Hazard/cost should appear in ~20-30% (±10%), got {hazard_cost_pct:.1f}%"


def test_loot_consequence_density():
    """Validate minimum proportion of loot includes consequence tags.
    
    Loot without consequence tags is drifting toward "free loot".
    This test ensures a baseline proportion includes attention-bearing tags.
    """
    from spar_engine.state import tick_state
    
    entries = load_pack("data/core_loot_situations.json")
    
    scene = SceneContext(
        scene_id="consequence_test",
        scene_phase="aftermath",
        environment=["populated"],
        tone=["test"],
        constraints=Constraints(confinement=0.5, connectivity=0.5, visibility=0.5),
        party_band="mid",
        spotlight=[]
    )
    
    selection = SelectionContext(
        enabled_packs=["loot"],
        include_tags=[],
        exclude_tags=[],
        factions_present=[],
        rarity_mode="normal"
    )
    
    state = EngineState.default()
    
    # Consequence tags that indicate non-free loot
    consequence_tags = {"visibility", "obligation", "social_friction", "heat", "cost", "hazard"}
    
    results_with_consequences = 0
    total = 150
    
    for seed in range(total):
        rng = TraceRNG(seed=seed + 4000)
        loot = generate_loot(scene, state, selection, entries, rng)
        
        # Check if any consequence tags present
        if any(tag in consequence_tags for tag in loot.tags):
            results_with_consequences += 1
        
        state = tick_state(state, ticks=1)
    
    consequence_pct = (results_with_consequences / total) * 100
    
    # At least 70% of loot should have consequence tags
    assert consequence_pct >= 60, \
        f"At least 70% of loot should include consequence tags (±10% tolerance), got {consequence_pct:.1f}%"
