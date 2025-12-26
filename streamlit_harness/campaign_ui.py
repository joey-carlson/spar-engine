"""Campaign Management UI for Streamlit Harness.

Version History:
- v0.1 (2025-12-25): Initial campaign UX prototype

This module provides a multi-campaign management interface with:
- Campaign selector (1 click to open)
- Campaign dashboard (living state view)
- Session finalization wizard (2-3 clicks)
- Campaign ledger (history tracking)
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

from spar_campaign import CampaignState, Scar, FactionState


CAMPAIGNS_DIR = Path("campaigns")
CAMPAIGNS_DIR.mkdir(exist_ok=True)


@dataclass
class Source:
    """Content source reference (built-in or external)."""
    
    source_id: str
    name: str
    path: str  # File path or identifier
    enabled: bool = True
    source_type: str = "external"  # "built-in" or "external"
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "source_id": self.source_id,
            "name": self.name,
            "path": self.path,
            "enabled": self.enabled,
            "source_type": self.source_type,
            "notes": self.notes,
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Source":
        """Deserialize from dictionary."""
        return Source(
            source_id=data["source_id"],
            name=data["name"],
            path=data["path"],
            enabled=data.get("enabled", True),
            source_type=data.get("source_type", "external"),
            notes=data.get("notes"),
        )


@dataclass
class Campaign:
    """Campaign metadata and state."""
    
    campaign_id: str
    name: str
    created: str
    last_played: str
    canon_summary: List[str] = field(default_factory=list)
    campaign_state: Optional[CampaignState] = None
    ledger: List[Dict[str, Any]] = field(default_factory=list)
    sources: List[Source] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "campaign_id": self.campaign_id,
            "name": self.name,
            "created": self.created,
            "last_played": self.last_played,
            "canon_summary": self.canon_summary,
            "campaign_state": self.campaign_state.to_dict() if self.campaign_state else None,
            "ledger": self.ledger,
            "sources": [s.to_dict() for s in self.sources],
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Campaign":
        """Deserialize from dictionary."""
        campaign_state = None
        if data.get("campaign_state"):
            campaign_state = CampaignState.from_dict(data["campaign_state"])
        
        sources_data = data.get("sources", [])
        sources = [Source.from_dict(s) for s in sources_data]
        
        return Campaign(
            campaign_id=data["campaign_id"],
            name=data["name"],
            created=data["created"],
            last_played=data["last_played"],
            canon_summary=data.get("canon_summary", []),
            campaign_state=campaign_state,
            ledger=data.get("ledger", []),
            sources=sources,
        )
    
    def get_path(self) -> Path:
        """Get filesystem path for this campaign."""
        return CAMPAIGNS_DIR / f"{self.campaign_id}.json"
    
    def save(self) -> None:
        """Save campaign to disk."""
        self.get_path().write_text(json.dumps(self.to_dict(), indent=2))
    
    @staticmethod
    def load(campaign_id: str) -> Optional["Campaign"]:
        """Load campaign from disk."""
        path = CAMPAIGNS_DIR / f"{campaign_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            return Campaign.from_dict(data)
        except Exception:
            return None
    
    @staticmethod
    def list_all() -> List["Campaign"]:
        """List all campaigns."""
        campaigns = []
        for json_file in CAMPAIGNS_DIR.glob("*.json"):
            try:
                data = json.loads(json_file.read_text())
                campaigns.append(Campaign.from_dict(data))
            except Exception:
                continue
        return sorted(campaigns, key=lambda c: c.last_played, reverse=True)


def init_campaign_session() -> None:
    """Initialize campaign-related session state."""
    if "current_campaign_id" not in st.session_state:
        st.session_state.current_campaign_id = None
    if "campaign_page" not in st.session_state:
        st.session_state.campaign_page = "selector"  # selector, dashboard, session, finalize


def render_campaign_selector() -> None:
    """Campaign selector page (1 click to open campaign)."""
    st.title("🎲 SPAR Campaigns")
    st.caption("Manage multiple living campaigns with persistent state")
    
    # Action buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ New Campaign", use_container_width=True, type="primary"):
            st.session_state.show_new_campaign_form = True
    with col2:
        if st.button("📥 Import Campaign History", use_container_width=True):
            st.info("Campaign history import - Coming in v0.2")
    
    # New campaign form
    if st.session_state.get("show_new_campaign_form", False):
        with st.form("new_campaign_form"):
            st.subheader("Create New Campaign")
            
            campaign_name = st.text_input("Campaign Name", placeholder="e.g., City of Fog")
            
            st.caption("Initial Factions (optional)")
            faction1 = st.text_input("Faction 1", placeholder="e.g., City Watch")
            faction2 = st.text_input("Faction 2", placeholder="e.g., Merchant Guild")
            faction3 = st.text_input("Faction 3", placeholder="")
            faction4 = st.text_input("Faction 4", placeholder="")
            
            submitted = st.form_submit_button("Create Campaign", type="primary")
            cancel = st.form_submit_button("Cancel")
            
            if submitted and campaign_name:
                # Create new campaign
                campaign_id = f"campaign_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                timestamp = datetime.now().isoformat()
                
                # Initialize campaign state
                campaign_state = CampaignState.default()
                
                # Add initial factions if provided
                initial_factions = {}
                for f_name in [faction1, faction2, faction3, faction4]:
                    if f_name:
                        fid = f_name.lower().replace(" ", "_")
                        initial_factions[fid] = FactionState(
                            faction_id=fid,
                            attention=0,
                            disposition=0,
                            notes=f_name,  # Store display name in notes
                        )
                
                if initial_factions:
                    from spar_campaign.campaign import apply_campaign_delta
                    from spar_campaign.models import CampaignDelta
                    # Apply empty delta with faction setup
                    campaign_state = CampaignState(
                        version="0.2",
                        campaign_pressure=0,
                        heat=0,
                        scars=[],
                        factions=initial_factions,
                        total_scenes_run=0,
                        total_cutoffs_seen=0,
                        highest_severity_seen=0,
                        _legacy_scars=set(),
                    )
                
                campaign = Campaign(
                    campaign_id=campaign_id,
                    name=campaign_name,
                    created=timestamp,
                    last_played=timestamp,
                    canon_summary=[f"Campaign '{campaign_name}' begins..."],
                    campaign_state=campaign_state,
                    ledger=[],
                )
                
                campaign.save()
                st.session_state.current_campaign_id = campaign_id
                st.session_state.show_new_campaign_form = False
                st.session_state.campaign_page = "dashboard"
                st.rerun()
            
            if cancel:
                st.session_state.show_new_campaign_form = False
                st.rerun()
    
    st.divider()
    
    # List existing campaigns
    st.subheader("Your Campaigns")
    
    campaigns = Campaign.list_all()
    
    if not campaigns:
        st.info("No campaigns yet. Create your first campaign above!")
        return
    
    for campaign in campaigns:
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                st.markdown(f"### {campaign.name}")
                st.caption(f"Last played: {campaign.last_played[:10]}")
                
                # Show pressure/heat bands if campaign state exists
                if campaign.campaign_state:
                    pressure_band = campaign.campaign_state.get_pressure_band()
                    heat_band = campaign.campaign_state.get_heat_band()
                    
                    # Badge styling
                    pressure_color = {
                        "stable": "🟢",
                        "strained": "🟡",
                        "volatile": "🟠",
                        "critical": "🔴"
                    }.get(pressure_band, "⚪")
                    
                    heat_color = {
                        "quiet": "🔵",
                        "noticed": "🟡",
                        "hunted": "🟠",
                        "exposed": "🔴"
                    }.get(heat_band, "⚪")
                    
                    st.caption(f"{pressure_color} {pressure_band.title()} | {heat_color} {heat_band.title()}")
            
            with col2:
                if campaign.campaign_state:
                    st.caption(f"Sessions: {campaign.campaign_state.total_scenes_run}")
                    if campaign.campaign_state.scars:
                        st.caption(f"Scars: {len(campaign.campaign_state.scars)}")
                    if campaign.campaign_state.factions:
                        active_factions = sum(1 for f in campaign.campaign_state.factions.values() if f.attention > 0)
                        st.caption(f"Active Factions: {active_factions}/{len(campaign.campaign_state.factions)}")
            
            with col3:
                if st.button("Open →", key=f"open_{campaign.campaign_id}", use_container_width=True):
                    st.session_state.current_campaign_id = campaign.campaign_id
                    st.session_state.campaign_page = "dashboard"
                    st.rerun()


def render_campaign_dashboard() -> None:
    """Campaign dashboard - living state view (main campaign page)."""
    campaign_id = st.session_state.current_campaign_id
    campaign = Campaign.load(campaign_id)
    
    if not campaign:
        st.error("Campaign not found")
        st.session_state.campaign_page = "selector"
        st.rerun()
        return
    
    # Header with back button
    col1, col2 = st.columns([1, 11])
    with col1:
        if st.button("← Back"):
            st.session_state.campaign_page = "selector"
            st.session_state.current_campaign_id = None
            st.rerun()
    with col2:
        st.title(f"📖 {campaign.name}")
    
    # Show active sources in header
    active_sources = [s for s in campaign.sources if s.enabled]
    if active_sources:
        source_names = ", ".join([s.name for s in active_sources])
        st.caption(f"Active Sources: {source_names}")
    else:
        st.caption("Active Sources: core_complications (built-in)")
    
    st.caption(f"Campaign ID: {campaign.campaign_id} | Last played: {campaign.last_played[:16]}")
    
    # Primary action button
    if st.button("▶️ Run Session", type="primary", use_container_width=True):
        st.session_state.campaign_page = "session"
        st.rerun()
    
    st.divider()
    
    # Campaign State Overview
    if campaign.campaign_state:
        cs = campaign.campaign_state
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Campaign Pressure",
                cs.campaign_pressure,
                help=f"Band: {cs.get_pressure_band()}"
            )
            st.caption(f"🎚️ {cs.get_pressure_band().title()}")
        
        with col2:
            st.metric(
                "Heat",
                cs.heat,
                help=f"Band: {cs.get_heat_band()}"
            )
            st.caption(f"🌡️ {cs.get_heat_band().title()}")
        
        with col3:
            st.metric("Sessions", cs.total_scenes_run)
        
        with col4:
            st.metric("Peak Severity", cs.highest_severity_seen)
    
    st.divider()
    
    # Canon Summary (editable)
    st.subheader("📜 Canon Summary")
    
    if not campaign.canon_summary:
        campaign.canon_summary = [f"Campaign '{campaign.name}' begins..."]
    
    # Display as editable bullet list
    st.caption("Current state of the world (8-12 bullets recommended)")
    
    for idx, bullet in enumerate(campaign.canon_summary[:15]):  # Cap at 15
        col1, col2 = st.columns([11, 1])
        with col1:
            new_text = st.text_input(
                f"Canon {idx+1}",
                value=bullet,
                key=f"canon_bullet_{idx}",
                label_visibility="collapsed"
            )
            if new_text != bullet:
                campaign.canon_summary[idx] = new_text
                campaign.save()
        with col2:
            if st.button("🗑️", key=f"delete_canon_{idx}"):
                campaign.canon_summary.pop(idx)
                campaign.save()
                st.rerun()
    
    if st.button("➕ Add Canon Bullet"):
        campaign.canon_summary.append("New development...")
        campaign.save()
        st.rerun()
    
    st.divider()
    
    # Sources Management
    with st.expander(f"📚 Content Sources ({len([s for s in campaign.sources if s.enabled])} active)", expanded=False):
        st.caption("Content sources for this campaign (no parsing yet, metadata only)")
        
        # Show built-in source
        st.markdown("**core_complications** (built-in)")
        st.caption("✅ Always active | data/core_complications.json")
        st.divider()
        
        # Show campaign sources
        if campaign.sources:
            for idx, source in enumerate(campaign.sources):
                col1, col2, col3 = st.columns([6, 3, 1])
                
                with col1:
                    status = "✅" if source.enabled else "⏸️"
                    st.markdown(f"{status} **{source.name}**")
                    st.caption(f"{source.path}")
                    if source.notes:
                        st.caption(f"_{source.notes}_")
                
                with col2:
                    st.caption(source.source_type)
                
                with col3:
                    # Toggle enabled state
                    if st.button("⚙️", key=f"toggle_source_{source.source_id}"):
                        campaign.sources[idx] = Source(
                            source_id=source.source_id,
                            name=source.name,
                            path=source.path,
                            enabled=not source.enabled,
                            source_type=source.source_type,
                            notes=source.notes,
                        )
                        campaign.save()
                        st.rerun()
                
                st.divider()
        
        # Add new source form
        if st.button("➕ Add Source"):
            st.session_state.show_add_source_form = True
        
        if st.session_state.get("show_add_source_form", False):
            st.markdown("**Add New Source**")
            
            new_source_name = st.text_input("Source Name", placeholder="e.g., City Loot Table", key="new_source_name")
            new_source_path = st.text_input("File Path", placeholder="e.g., data/city_loot.csv", key="new_source_path")
            new_source_notes = st.text_input("Notes (optional)", placeholder="e.g., Urban encounters", key="new_source_notes")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Add", key="add_source_confirm"):
                    if new_source_name and new_source_path:
                        source_id = f"source_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        new_source = Source(
                            source_id=source_id,
                            name=new_source_name,
                            path=new_source_path,
                            enabled=True,
                            source_type="external",
                            notes=new_source_notes if new_source_notes else None,
                        )
                        campaign.sources.append(new_source)
                        campaign.save()
                        st.session_state.show_add_source_form = False
                        st.rerun()
                    else:
                        st.error("Name and path required")
            
            with col2:
                if st.button("Cancel", key="add_source_cancel"):
                    st.session_state.show_add_source_form = False
                    st.rerun()
    
    # Scars
    if campaign.campaign_state and campaign.campaign_state.scars:
        with st.expander(f"🩹 Scars ({len(campaign.campaign_state.scars)})", expanded=False):
            for scar in campaign.campaign_state.scars:
                st.markdown(f"**{scar.scar_id}** ({scar.category}, {scar.severity})")
                if scar.notes:
                    st.caption(scar.notes)
                st.caption(f"Created: Scene {scar.created_scene_index or 'Unknown'}")
                st.divider()
    
    # Factions
    if campaign.campaign_state and campaign.campaign_state.factions:
        with st.expander(f"👥 Factions ({len(campaign.campaign_state.factions)})", expanded=True):
            for fid, faction in campaign.campaign_state.factions.items():
                disp_str = {
                    -2: "😡 Hostile",
                    -1: "😠 Unfriendly",
                    0: "😐 Neutral",
                    1: "🙂 Friendly",
                    2: "😊 Allied"
                }.get(faction.disposition, "Unknown")
                
                display_name = faction.notes or fid
                st.markdown(f"**{display_name}**")
                st.caption(f"{disp_str} | Attention: {faction.attention}/20")
                
                # Progress bar for attention
                attention_pct = (faction.attention / 20) * 100
                st.progress(attention_pct / 100)
                st.divider()
    
    # Last session changes
    if campaign.ledger:
        with st.expander("📋 Last Session Changes", expanded=True):
            last_entry = campaign.ledger[-1]
            st.caption(f"Session {last_entry.get('session_number', '?')}: {last_entry.get('session_date', '')}")
            
            if last_entry.get("what_happened"):
                st.markdown("**What Happened:**")
                for bullet in last_entry["what_happened"]:
                    st.markdown(f"• {bullet}")
            
            if last_entry.get("deltas"):
                deltas = last_entry["deltas"]
                st.caption(f"Pressure: {deltas.get('pressure_change', 0):+d} | Heat: {deltas.get('heat_change', 0):+d}")
    
    # Ledger
    if campaign.ledger:
        with st.expander(f"📚 Campaign Ledger ({len(campaign.ledger)} sessions)", expanded=False):
            for entry in reversed(campaign.ledger):  # Newest first
                st.markdown(f"**Session {entry.get('session_number', '?')}** — {entry.get('session_date', '')}")
                if entry.get("what_happened"):
                    for bullet in entry["what_happened"][:3]:  # First 3 bullets
                        st.caption(f"• {bullet}")
                st.divider()


def render_session_workspace() -> None:
    """Session workspace - run scenarios with campaign context."""
    campaign_id = st.session_state.current_campaign_id
    campaign = Campaign.load(campaign_id)
    
    if not campaign:
        st.error("Campaign not found")
        st.session_state.campaign_page = "selector"
        st.rerun()
        return
    
    # Header
    col1, col2 = st.columns([1, 11])
    with col1:
        if st.button("← Back"):
            st.session_state.campaign_page = "dashboard"
            st.rerun()
    with col2:
        st.title(f"🎮 Session Workspace: {campaign.name}")
    
    st.info("🔧 This integrates with existing Scenario Runner functionality. For prototype v0.1, use the Scenarios tab and then click 'Finalize Session' when done.")
    
    # Quick access to finalize
    if st.button("✅ Finalize Session", type="primary", use_container_width=True):
        st.session_state.campaign_page = "finalize"
        st.rerun()
    
    st.divider()
    
    # Campaign context for reference
    with st.expander("📊 Campaign Context", expanded=False):
        if campaign.campaign_state:
            cs = campaign.campaign_state
            st.write(f"**Pressure**: {cs.campaign_pressure} ({cs.get_pressure_band()})")
            st.write(f"**Heat**: {cs.heat} ({cs.get_heat_band()})")
            
            from spar_campaign.campaign import get_campaign_influence
            influence = get_campaign_influence(cs)
            
            if influence["notes"]:
                st.write("**Campaign Influence:**")
                for note in influence["notes"]:
                    st.write(f"• {note}")


def render_finalize_session() -> None:
    """Finalize session wizard (2-3 clicks)."""
    campaign_id = st.session_state.current_campaign_id
    campaign = Campaign.load(campaign_id)
    
    if not campaign:
        st.error("Campaign not found")
        st.session_state.campaign_page = "selector"
        st.rerun()
        return
    
    st.title("✅ Finalize Session")
    st.caption(f"Campaign: {campaign.name}")
    
    with st.form("finalize_session_form"):
        st.subheader("What Happened?")
        
        bullet1 = st.text_input("Bullet 1", placeholder="Key event or outcome...")
        bullet2 = st.text_input("Bullet 2", placeholder="Another development...")
        bullet3 = st.text_input("Bullet 3", placeholder="Third notable thing...")
        
        st.subheader("What Changed?")
        
        col1, col2 = st.columns(2)
        
        with col1:
            add_scar = st.checkbox("Add new scar?")
            if add_scar:
                scar_id = st.text_input("Scar ID", placeholder="e.g., known_to_authorities")
                scar_category = st.selectbox("Category", ["physical", "social", "political", "resource", "reputation", "environment"])
                scar_severity = st.selectbox("Severity", ["low", "medium", "high"])
                scar_notes = st.text_area("Notes", placeholder="How did this happen?")
        
        with col2:
            rumor_spread = st.checkbox("Rumor spread?")
            faction_attention = st.checkbox("Faction attention increased?")
            if faction_attention and campaign.campaign_state:
                faction_choices = list(campaign.campaign_state.factions.keys())
                if faction_choices:
                    affected_faction = st.selectbox("Which faction?", faction_choices)
                else:
                    st.caption("No factions defined yet")
        
        st.subheader("State Changes (Manual)")
        
        col1, col2 = st.columns(2)
        with col1:
            pressure_change = st.number_input("Pressure change", min_value=-10, max_value=10, value=0, step=1)
        with col2:
            heat_change = st.number_input("Heat change", min_value=-10, max_value=10, value=0, step=1)
        
        col1, col2 = st.columns(2)
        with col1:
            commit = st.form_submit_button("💾 Commit Session", type="primary", use_container_width=True)
        with col2:
            cancel = st.form_submit_button("Cancel", use_container_width=True)
        
        if commit:
            # Build ledger entry
            what_happened = [b for b in [bullet1, bullet2, bullet3] if b.strip()]
            
            if not what_happened:
                st.error("Please enter at least one bullet point")
                st.stop()
            
            # Record active sources in session metadata
            active_source_ids = [s.source_id for s in campaign.sources if s.enabled]
            active_source_names = [s.name for s in campaign.sources if s.enabled]
            
            session_entry = {
                "session_number": len(campaign.ledger) + 1,
                "session_date": datetime.now().isoformat(),
                "what_happened": what_happened,
                "deltas": {
                    "pressure_change": pressure_change,
                    "heat_change": heat_change,
                    "rumor_spread": rumor_spread,
                    "faction_attention_change": faction_attention,
                },
                "active_sources": active_source_names,  # Human-readable
                "active_source_ids": active_source_ids,  # Machine-readable
            }
            
            # Update campaign state
            if campaign.campaign_state:
                cs = campaign.campaign_state
                
                # Manual adjustments
                new_pressure = max(0, min(30, cs.campaign_pressure + pressure_change))
                new_heat = max(0, min(20, cs.heat + heat_change))
                
                # Add scar if specified
                new_scars = list(cs.scars)
                if add_scar and scar_id:
                    new_scar = Scar(
                        scar_id=scar_id,
                        category=scar_category,  # type: ignore
                        severity=scar_severity,  # type: ignore
                        source=f"Session {len(campaign.ledger) + 1}",
                        created_scene_index=cs.total_scenes_run,
                        notes=scar_notes if scar_notes else None,
                    )
                    new_scars.append(new_scar)
                
                # Update faction if specified
                new_factions = dict(cs.factions)
                if faction_attention and 'affected_faction' in locals() and affected_faction:
                    if affected_faction in new_factions:
                        old_faction = new_factions[affected_faction]
                        new_factions[affected_faction] = FactionState(
                            faction_id=old_faction.faction_id,
                            attention=min(20, old_faction.attention + 2),
                            disposition=old_faction.disposition,
                            notes=old_faction.notes,
                        )
                
                # Create new state
                campaign.campaign_state = CampaignState(
                    version="0.2",
                    campaign_pressure=new_pressure,
                    heat=new_heat,
                    scars=new_scars,
                    factions=new_factions,
                    total_scenes_run=cs.total_scenes_run + 1,
                    total_cutoffs_seen=cs.total_cutoffs_seen,
                    highest_severity_seen=cs.highest_severity_seen,
                    _legacy_scars=cs._legacy_scars,
                )
            
            # Add to canon summary (first bullet becomes canon)
            if what_happened:
                campaign.canon_summary.append(what_happened[0])
            
            # Add to ledger
            campaign.ledger.append(session_entry)
            campaign.last_played = datetime.now().isoformat()
            
            # Save
            campaign.save()
            
            st.success("Session finalized!")
            st.session_state.campaign_page = "dashboard"
            st.rerun()
        
        if cancel:
            st.session_state.campaign_page = "dashboard"
            st.rerun()


def render_campaign_ui() -> bool:
    """Render campaign management UI.
    
    Returns True if campaign UI is active, False if should show main harness.
    """
    init_campaign_session()
    
    page = st.session_state.campaign_page
    
    if page == "selector":
        render_campaign_selector()
        return True
    elif page == "dashboard":
        render_campaign_dashboard()
        return True
    elif page == "session":
        render_session_workspace()
        return True
    elif page == "finalize":
        render_finalize_session()
        return True
    
    return False
