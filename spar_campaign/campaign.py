"""Campaign mechanics operations for long-term pressure management.

Version History:
- v0.2 (2025-12-25): Extended for structured scars and faction tracking
- v0.1 (2025-12-25): Initial implementation

This module provides pure functions for managing campaign state across
multiple scenes. It handles pressure accumulation, decay, and translation
of campaign state into scene setup influences.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set

from .models import CampaignState, CampaignDelta, FactionState, Scar


def apply_campaign_delta(
    state: CampaignState,
    delta: CampaignDelta,
    *,
    pressure_cap: int = 30,
    heat_cap: int = 20,
) -> CampaignState:
    """Apply a CampaignDelta to CampaignState (pure function).
    
    Args:
        state: Current campaign state
        delta: Changes from scene outcome
        pressure_cap: Maximum campaign pressure (prevents runaway)
        heat_cap: Maximum heat/attention (prevents runaway)
    
    Returns:
        New campaign state with delta applied and caps enforced
    """
    # Add pressure, cap to prevent runaway
    new_pressure = min(
        state.campaign_pressure + delta.campaign_pressure_add,
        pressure_cap
    )
    
    # Add heat, cap to prevent runaway
    new_heat = min(
        state.heat + delta.heat_add,
        heat_cap
    )
    
    # Add new scars (irreversible, no duplicates by scar_id)
    existing_scar_ids = {s.scar_id for s in state.scars}
    new_scars = list(state.scars)
    for scar in delta.scars_add:
        if scar.scar_id not in existing_scar_ids:
            new_scars.append(scar)
    
    # Update factions
    new_factions = dict(state.factions)
    for faction_id, updates in delta.faction_updates.items():
        if faction_id in new_factions:
            # Update existing faction
            old_faction = new_factions[faction_id]
            new_attention = min(
                old_faction.attention + updates.get("attention_add", 0),
                20  # faction attention cap
            )
            new_disposition = max(-2, min(2,
                old_faction.disposition + updates.get("disposition_add", 0)
            ))
            new_factions[faction_id] = FactionState(
                faction_id=faction_id,
                name=old_faction.name,
                description=old_faction.description,
                attention=new_attention,
                disposition=new_disposition,
                notes=old_faction.notes,
                is_active=old_faction.is_active,
            )
        else:
            # Create new faction with default name from ID
            display_name = faction_id.replace('_', ' ').title()
            new_factions[faction_id] = FactionState(
                faction_id=faction_id,
                name=display_name,
                description="",
                attention=updates.get("attention_add", 0),
                disposition=updates.get("disposition_add", 0),
                notes=None,
                is_active=True,
            )
    
    # Track highest severity seen
    new_highest = state.highest_severity_seen
    
    # Increment counters
    new_scenes = state.total_scenes_run + delta.scenes_increment
    new_cutoffs = state.total_cutoffs_seen + (1 if delta.campaign_pressure_add >= 2 else 0)
    
    return CampaignState(
        version="0.2",
        campaign_pressure=new_pressure,
        heat=new_heat,
        scars=new_scars,
        factions=new_factions,
        total_scenes_run=new_scenes,
        total_cutoffs_seen=new_cutoffs,
        highest_severity_seen=new_highest,
        _legacy_scars=state._legacy_scars,  # Preserve legacy
    )


def decay_campaign_state(
    state: CampaignState,
    *,
    pressure_decay: int = 1,
    heat_decay: int = 1,
) -> CampaignState:
    """Apply time-based decay to campaign state (pure function).
    
    Use this between scenes or at narrative downtime moments to
    represent pressure release, cooling attention, etc.
    
    Args:
        state: Current campaign state
        pressure_decay: Amount to reduce campaign_pressure
        heat_decay: Amount to reduce heat
    
    Returns:
        New state with decay applied
    
    Note: Scars are permanent and do not decay.
    """
    new_pressure = max(0, state.campaign_pressure - pressure_decay)
    new_heat = max(0, state.heat - heat_decay)
    
    return CampaignState(
        version="0.2",
        campaign_pressure=new_pressure,
        heat=new_heat,
        scars=state.scars,  # Unchanged
        factions=state.factions,  # Unchanged
        total_scenes_run=state.total_scenes_run,
        total_cutoffs_seen=state.total_cutoffs_seen,
        highest_severity_seen=state.highest_severity_seen,
        _legacy_scars=state._legacy_scars,
    )


def get_campaign_influence(state: CampaignState) -> Dict[str, Any]:
    """Translate campaign state into scene setup influence.
    
    This function provides hints for scene setup without modifying
    engine internals. The calling code decides how to apply these hints.
    
    Returns dictionary with:
        - include_tags: Tags to add to scene selection
        - exclude_tags: Tags to suppress
        - rarity_bias: Suggested shift to rarity mode (if any)
        - notes: Human-readable explanation
    
    Design principle: Campaign state suggests, scene setup decides.
    """
    include_tags: List[str] = []
    exclude_tags: List[str] = []
    rarity_bias: str | None = None
    notes: List[str] = []
    
    # High campaign pressure suggests more volatility
    if state.campaign_pressure >= 20:
        include_tags.append("time_pressure")
        include_tags.append("reinforcements")
        rarity_bias = "spiky"
        notes.append("Very high campaign pressure: volatile conditions likely")
    elif state.campaign_pressure >= 10:
        include_tags.append("time_pressure")
        notes.append("Elevated campaign pressure: situation remains tense")
    
    # High heat means attention and response
    if state.heat >= 15:
        include_tags.append("social_friction")
        include_tags.append("visibility")
        notes.append("High heat: authorities and factions are aware")
    elif state.heat >= 8:
        include_tags.append("visibility")
        notes.append("Moderate heat: attention is building")
    
    # Low pressure + low heat might allow breathing room
    if state.campaign_pressure < 5 and state.heat < 5:
        exclude_tags.append("time_pressure")
        notes.append("Low pressure: opportunity for recovery")
    
    # Specific scars might enable/disable certain content (v0.2)
    for scar in state.scars:
        if scar.category == "resource":
            include_tags.append("attrition")
            notes.append(f"Scar: {scar.scar_id} - supply pressure continues")
        
        if scar.category in ["social", "political", "reputation"]:
            include_tags.append("social_friction")
            notes.append(f"Scar: {scar.scar_id} - social complications likely")
    
    # v0.1 legacy scar support
    if "resources_depleted" in state._legacy_scars:
        include_tags.append("attrition")
        notes.append("Resources depleted: supply pressure continues")
    
    if "known_to_authorities" in state._legacy_scars:
        include_tags.append("social_friction")
        notes.append("Known to authorities: heightened scrutiny")
    
    # Add pressure and heat band descriptors
    pressure_band = state.get_pressure_band()
    heat_band = state.get_heat_band()
    
    if pressure_band != "stable" or heat_band != "quiet":
        notes.append(f"Campaign state: {pressure_band} pressure, {heat_band} heat")
    
    # v0.3: Improved faction scoring for suggested spotlight factions
    faction_scores: List[tuple[str, float, List[str]]] = []  # (faction_id, score, reasons)
    
    for fid, faction in state.factions.items():
        if not faction.is_active:
            continue  # Skip archived factions
        
        reasons = []
        score = float(faction.attention)  # Base score
        reasons.append(f"Attention: {faction.attention}")
        
        # +1 if disposition != Neutral
        if faction.disposition != 0:
            score += 1
            disp_label = faction.get_disposition_label().split()[1]  # Remove emoji
            reasons.append(f"Non-neutral ({disp_label})")
        
        # +1 if high heat (hunted or exposed bands)
        if heat_band in ["hunted", "exposed"]:
            score += 1
            reasons.append(f"High heat ({heat_band})")
        
        # +2 if any active scar mentions this faction (v0.3: references not yet in Scar model)
        # TODO: When Scar model gets related_factions field, check here
        
        # Store if score > 0 or all factions are at 0
        if score > 0:
            faction_scores.append((fid, score, reasons))
    
    # Fallback: if all factions have 0 attention, include them anyway for visibility
    if not faction_scores and state.factions:
        faction_scores = [
            (fid, 0.0, ["No attention yet"])
            for fid, f in state.factions.items()
            if f.is_active
        ]
    
    # Sort by score descending and select top 1-3
    faction_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Apply minimum threshold (score >= 3) unless all scores are below threshold
    threshold = 3
    above_threshold = [(fid, score, r) for fid, score, r in faction_scores if score >= threshold]
    
    if above_threshold:
        top_factions = above_threshold[:3]
    elif faction_scores:
        # All below threshold, take top 3 anyway (including zero-attention fallback factions)
        top_factions = faction_scores[:3]
    else:
        top_factions = []
    
    suggested_factions = [fid for fid, _, _ in top_factions]
    
    # Generate faction influence notes
    faction_influence_notes: List[str] = []
    faction_tag_bias: List[str] = []
    
    for fid, score, reasons in top_factions:
        if fid in state.factions:
            faction = state.factions[fid]
            faction_influence_notes.append(f"{faction.name} (score: {score:.0f}): {', '.join(reasons)}")
            
            # Add tag nudges based on faction state
            if faction.attention >= 10:
                faction_tag_bias.append("reinforcements")
                faction_tag_bias.append("visibility")
            
            if faction.disposition <= -1:
                faction_tag_bias.append("social_friction")
                if faction.disposition == -2:
                    faction_tag_bias.append("threat")
            elif faction.disposition >= 1:
                faction_tag_bias.append("opportunity")
                if faction.disposition == 2:
                    faction_tag_bias.append("information")
    
    # Merge faction tag bias into include_tags (deduplicate)
    for tag in faction_tag_bias:
        if tag not in include_tags:
            include_tags.append(tag)
    
    return {
        "include_tags": include_tags,
        "exclude_tags": exclude_tags,
        "rarity_bias": rarity_bias,
        "notes": notes,
        "suggested_factions_involved": suggested_factions,
        "faction_influence_notes": faction_influence_notes,
        "faction_tag_bias": list(set(faction_tag_bias)),  # Deduplicated
        "pressure_band": pressure_band,
        "heat_band": heat_band,
    }


def record_severity_high_water_mark(
    state: CampaignState,
    severity: int,
) -> CampaignState:
    """Update highest severity seen if this scene exceeds it.
    
    Helper function to track campaign volatility peak.
    """
    if severity > state.highest_severity_seen:
        return CampaignState(
            version="0.2",
            campaign_pressure=state.campaign_pressure,
            heat=state.heat,
            scars=state.scars,
            factions=state.factions,
            total_scenes_run=state.total_scenes_run,
            total_cutoffs_seen=state.total_cutoffs_seen,
            highest_severity_seen=severity,
            _legacy_scars=state._legacy_scars,
        )
    return state
