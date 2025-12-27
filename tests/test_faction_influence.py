"""Tests for faction influence scoring in campaign context.

Validates the deterministic faction scoring algorithm that suggests
which factions should be in the spotlight for the next session.
"""

import pytest
from spar_campaign import CampaignState, FactionState, get_campaign_influence


def test_faction_scoring_by_attention():
    """Factions with higher attention score higher."""
    state = CampaignState(
        version="0.2",
        campaign_pressure=0,
        heat=0,
        scars=[],
        factions={
            "city_watch": FactionState(
                faction_id="city_watch",
                name="City Watch",
                description="",
                attention=15,
                disposition=0,
                notes=None,
                is_active=True,
            ),
            "merchant_guild": FactionState(
                faction_id="merchant_guild",
                name="Merchant Guild",
                description="",
                attention=5,
                disposition=0,
                notes=None,
                is_active=True,
            ),
            "thieves": FactionState(
                faction_id="thieves",
                name="Thieves",
                description="",
                attention=0,
                disposition=0,
                notes=None,
                is_active=True,
            ),
        },
        total_scenes_run=0,
        total_cutoffs_seen=0,
        highest_severity_seen=0,
        _legacy_scars=set(),
    )
    
    influence = get_campaign_influence(state)
    
    # Should suggest City Watch (att=15) and Merchant Guild (att=5), not Thieves (att=0)
    assert len(influence["suggested_factions_involved"]) == 2
    assert "city_watch" in influence["suggested_factions_involved"]
    assert "merchant_guild" in influence["suggested_factions_involved"]
    assert "thieves" not in influence["suggested_factions_involved"]


def test_faction_scoring_with_disposition():
    """Non-neutral disposition adds +1 to score."""
    state = CampaignState(
        version="0.2",
        campaign_pressure=0,
        heat=0,
        scars=[],
        factions={
            "hostile_faction": FactionState(
                faction_id="hostile_faction",
                name="Hostile Faction",
                description="",
                attention=5,
                disposition=-2,  # Hostile
                notes=None,
                is_active=True,
            ),
            "neutral_faction": FactionState(
                faction_id="neutral_faction",
                name="Neutral Faction",
                description="",
                attention=5,
                disposition=0,  # Neutral
                notes=None,
                is_active=True,
            ),
        },
        total_scenes_run=0,
        total_cutoffs_seen=0,
        highest_severity_seen=0,
        _legacy_scars=set(),
    )
    
    influence = get_campaign_influence(state)
    notes = influence["faction_influence_notes"]
    
    # Hostile faction should have higher score (5+1=6) than neutral (5)
    hostile_note = next((n for n in notes if "Hostile Faction" in n), None)
    neutral_note = next((n for n in notes if "Neutral Faction" in n), None)
    
    assert hostile_note is not None
    assert "score: 6" in hostile_note
    assert "Non-neutral" in hostile_note
    
    if neutral_note:  # May not appear if below threshold
        assert "score: 5" in neutral_note


def test_faction_scoring_with_high_heat():
    """High heat band adds +1 to all faction scores."""
    state = CampaignState(
        version="0.2",
        campaign_pressure=0,
        heat=18,  # Hunted band
        scars=[],
        factions={
            "faction_a": FactionState(
                faction_id="faction_a",
                name="Faction A",
                description="",
                attention=5,
                disposition=0,
                notes=None,
                is_active=True,
            ),
        },
        total_scenes_run=0,
        total_cutoffs_seen=0,
        highest_severity_seen=0,
        _legacy_scars=set(),
    )
    
    influence = get_campaign_influence(state)
    notes = influence["faction_influence_notes"]
    
    # Should have score 5+1=6 (attention + high heat)
    faction_note = next((n for n in notes if "Faction A" in n), None)
    assert faction_note is not None
    assert "score: 6" in faction_note
    assert "High heat" in faction_note


def test_faction_threshold_filtering():
    """Factions below threshold (score < 3) are filtered unless all are low."""
    state = CampaignState(
        version="0.2",
        campaign_pressure=0,
        heat=0,
        scars=[],
        factions={
            "high_attention": FactionState(
                faction_id="high_attention",
                name="High Attention",
                description="",
                attention=10,
                disposition=0,
                notes=None,
                is_active=True,
            ),
            "low_attention": FactionState(
                faction_id="low_attention",
                name="Low Attention",
                description="",
                attention=2,
                disposition=0,
                notes=None,
                is_active=True,
            ),
        },
        total_scenes_run=0,
        total_cutoffs_seen=0,
        highest_severity_seen=0,
        _legacy_scars=set(),
    )
    
    influence = get_campaign_influence(state)
    
    # Should only suggest high_attention (score 10 >= threshold 3)
    assert "high_attention" in influence["suggested_factions_involved"]
    assert "low_attention" not in influence["suggested_factions_involved"]


def test_archived_factions_excluded():
    """Archived factions are never suggested."""
    state = CampaignState(
        version="0.2",
        campaign_pressure=0,
        heat=0,
        scars=[],
        factions={
            "active": FactionState(
                faction_id="active",
                name="Active Faction",
                description="",
                attention=10,
                disposition=0,
                notes=None,
                is_active=True,
            ),
            "archived": FactionState(
                faction_id="archived",
                name="Archived Faction",
                description="",
                attention=10,
                disposition=0,
                notes=None,
                is_active=False,  # Archived
            ),
        },
        total_scenes_run=0,
        total_cutoffs_seen=0,
        highest_severity_seen=0,
        _legacy_scars=set(),
    )
    
    influence = get_campaign_influence(state)
    
    # Should only suggest active faction
    assert "active" in influence["suggested_factions_involved"]
    assert "archived" not in influence["suggested_factions_involved"]


def test_faction_tag_bias_hostile():
    """Hostile factions add social_friction and threat tags."""
    state = CampaignState(
        version="0.2",
        campaign_pressure=0,
        heat=0,
        scars=[],
        factions={
            "hostiles": FactionState(
                faction_id="hostiles",
                name="Hostiles",
                description="",
                attention=10,
                disposition=-2,  # Hostile
                notes=None,
                is_active=True,
            ),
        },
        total_scenes_run=0,
        total_cutoffs_seen=0,
        highest_severity_seen=0,
        _legacy_scars=set(),
    )
    
    influence = get_campaign_influence(state)
    
    # Should add hostile-related tags
    assert "social_friction" in influence["faction_tag_bias"]
    assert "threat" in influence["faction_tag_bias"]
    
    # These should merge into include_tags
    assert "social_friction" in influence["include_tags"]
    assert "threat" in influence["include_tags"]


def test_faction_tag_bias_allied():
    """Allied factions add opportunity and information tags."""
    state = CampaignState(
        version="0.2",
        campaign_pressure=0,
        heat=0,
        scars=[],
        factions={
            "allies": FactionState(
                faction_id="allies",
                name="Allies",
                description="",
                attention=10,
                disposition=2,  # Allied
                notes=None,
                is_active=True,
            ),
        },
        total_scenes_run=0,
        total_cutoffs_seen=0,
        highest_severity_seen=0,
        _legacy_scars=set(),
    )
    
    influence = get_campaign_influence(state)
    
    # Should add allied-related tags
    assert "opportunity" in influence["faction_tag_bias"]
    assert "information" in influence["faction_tag_bias"]
    
    # These should merge into include_tags
    assert "opportunity" in influence["include_tags"]
    assert "information" in influence["include_tags"]


def test_faction_tag_bias_high_attention():
    """High attention (>=10) adds reinforcements and visibility."""
    state = CampaignState(
        version="0.2",
        campaign_pressure=0,
        heat=0,
        scars=[],
        factions={
            "watchers": FactionState(
                faction_id="watchers",
                name="Watchers",
                description="",
                attention=15,
                disposition=0,
                notes=None,
                is_active=True,
            ),
        },
        total_scenes_run=0,
        total_cutoffs_seen=0,
        highest_severity_seen=0,
        _legacy_scars=set(),
    )
    
    influence = get_campaign_influence(state)
    
    # Should add high-attention tags
    assert "reinforcements" in influence["faction_tag_bias"]
    assert "visibility" in influence["faction_tag_bias"]
    
    # These should merge into include_tags
    assert "reinforcements" in influence["include_tags"]
    assert "visibility" in influence["include_tags"]


def test_all_factions_zero_attention_fallback():
    """When all factions have 0 attention, still suggest top 3 for visibility."""
    state = CampaignState(
        version="0.2",
        campaign_pressure=0,
        heat=0,
        scars=[],
        factions={
            "a": FactionState(faction_id="a", name="A", description="", attention=0, disposition=0, notes=None, is_active=True),
            "b": FactionState(faction_id="b", name="B", description="", attention=0, disposition=0, notes=None, is_active=True),
            "c": FactionState(faction_id="c", name="C", description="", attention=0, disposition=0, notes=None, is_active=True),
            "d": FactionState(faction_id="d", name="D", description="", attention=0, disposition=0, notes=None, is_active=True),
        },
        total_scenes_run=0,
        total_cutoffs_seen=0,
        highest_severity_seen=0,
        _legacy_scars=set(),
    )
    
    influence = get_campaign_influence(state)
    
    # Should suggest up to 3 factions even with 0 attention
    assert len(influence["suggested_factions_involved"]) <= 3
    assert len(influence["suggested_factions_involved"]) > 0
