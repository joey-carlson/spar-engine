"""Campaign context bridge for Event Generator.

Version History:
- v0.1 (2025-12-25): Initial context bundle integration

Provides Context Bundle computation and UI components for bridging
Campaign Manager context into Event Generator.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import streamlit as st

from spar_campaign import CampaignState
from spar_campaign.campaign import get_campaign_influence


@dataclass
class ContextBundle:
    """Context bundle derived from CampaignState for Event Generator.
    
    This is a read-only, derived object that translates campaign state
    into generator-friendly defaults. It never modifies campaign state.
    """
    
    campaign_id: str
    campaign_name: str
    include_tags: List[str]
    exclude_tags: List[str]
    suggested_factions: List[str]
    active_sources: List[str]
    pressure_band: str
    heat_band: str
    notes: List[str]
    faction_influence_notes: List[str]  # v0.3: Faction spotlight explanations
    faction_tag_bias: List[str]  # v0.3: Tag nudges from faction state
    
    @staticmethod
    def from_campaign(campaign_id: str, campaign_name: str, campaign_state: CampaignState, sources: List[Any]) -> "ContextBundle":
        """Compute context bundle from campaign state.
        
        Args:
            campaign_id: Campaign identifier
            campaign_name: Campaign display name
            campaign_state: Current CampaignState v0.2
            sources: List of Source objects
        
        Returns:
            ContextBundle with suggested tags, factions, sources, and explanatory notes
        """
        # Get campaign influence (already implements tag suggestion logic)
        influence = get_campaign_influence(campaign_state)
        
        # Extract suggested tags
        include_tags = influence.get("include_tags", [])
        exclude_tags = influence.get("exclude_tags", [])
        
        # Get suggested factions (top 3 by attention, or all with attention ≥5)
        suggested_factions = influence.get("suggested_factions_involved", [])[:3]
        
        # Get active sources
        active_sources = [s.name for s in sources if s.enabled]
        
        # Get bands
        pressure_band = influence.get("pressure_band", "stable")
        heat_band = influence.get("heat_band", "quiet")
        
        # Get notes (explanations for why tags/factions suggested)
        notes = influence.get("notes", [])
        
        # v0.3: Get faction influence details
        faction_influence_notes = influence.get("faction_influence_notes", [])
        faction_tag_bias = influence.get("faction_tag_bias", [])
        
        return ContextBundle(
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            include_tags=include_tags,
            exclude_tags=exclude_tags,
            suggested_factions=suggested_factions,
            active_sources=active_sources,
            pressure_band=pressure_band,
            heat_band=heat_band,
            notes=notes,
            faction_influence_notes=faction_influence_notes,
            faction_tag_bias=faction_tag_bias,
        )
    
    def to_tag_csv(self) -> tuple[str, str]:
        """Convert to CSV strings for include/exclude tags.
        
        Returns:
            (include_csv, exclude_csv)
        """
        include_csv = ",".join(self.include_tags) if self.include_tags else ""
        exclude_csv = ",".join(self.exclude_tags) if self.exclude_tags else ""
        return include_csv, exclude_csv
    
    def get_summary_text(self) -> str:
        """Get one-line summary of context."""
        parts = []
        
        if self.pressure_band != "stable":
            parts.append(f"Pressure: {self.pressure_band.title()}")
        
        if self.heat_band != "quiet":
            parts.append(f"Heat: {self.heat_band.title()}")
        
        if self.suggested_factions:
            faction_str = ", ".join(self.suggested_factions[:2])  # First 2
            if len(self.suggested_factions) > 2:
                faction_str += f" +{len(self.suggested_factions)-2}"
            parts.append(f"Factions: {faction_str}")
        
        if self.active_sources:
            parts.append(f"Sources: {len(self.active_sources)} active")
        
        return " • ".join(parts) if parts else "No special context"


def init_campaign_context_state():
    """Initialize campaign context session state."""
    if "active_campaign_context" not in st.session_state:
        st.session_state.active_campaign_context = None
    if "context_enabled" not in st.session_state:
        st.session_state.context_enabled = True


def set_campaign_context(context_bundle: Optional[ContextBundle]):
    """Set the active campaign context for Event Generator."""
    st.session_state.active_campaign_context = context_bundle
    st.session_state.context_enabled = True


def get_campaign_context() -> Optional[ContextBundle]:
    """Get the active campaign context if enabled."""
    if not st.session_state.get("context_enabled", True):
        return None
    return st.session_state.get("active_campaign_context")


def clear_campaign_context():
    """Clear campaign context."""
    st.session_state.active_campaign_context = None
    st.session_state.context_enabled = False
