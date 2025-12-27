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
from streamlit_harness.import_overrides import ImportOverrides


CAMPAIGNS_DIR = Path("campaigns")
CAMPAIGNS_DIR.mkdir(exist_ok=True)


def normalize_campaign_name_to_dir(name: str) -> str:
    """Normalize campaign name to valid directory name.
    
    Removes special characters, replaces spaces/hyphens with underscores.
    Used for creating campaign subdirectories.
    """
    import re
    dir_name = re.sub(r'[^\w\s-]', '', name)  # Remove special chars
    dir_name = re.sub(r'[-\s]+', '_', dir_name)  # Replace spaces/hyphens
    dir_name = dir_name.strip('_')  # Remove leading/trailing underscores
    return dir_name


@dataclass
class PrepItem:
    """Prep queue item - potential encounter/event (non-canon)."""
    
    item_id: str
    created_at: str
    title: str
    summary: str
    tags: List[str] = field(default_factory=list)
    source: Dict[str, Any] = field(default_factory=dict)  # Run metadata
    status: str = "queued"  # "queued", "pinned", "archived"
    related_factions: List[str] = field(default_factory=list)
    related_scars: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "item_id": self.item_id,
            "created_at": self.created_at,
            "title": self.title,
            "summary": self.summary,
            "tags": self.tags,
            "source": self.source,
            "status": self.status,
            "related_factions": self.related_factions,
            "related_scars": self.related_scars,
            "notes": self.notes,
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "PrepItem":
        """Deserialize from dictionary."""
        return PrepItem(
            item_id=data["item_id"],
            created_at=data["created_at"],
            title=data["title"],
            summary=data["summary"],
            tags=data.get("tags", []),
            source=data.get("source", {}),
            status=data.get("status", "queued"),
            related_factions=data.get("related_factions", []),
            related_scars=data.get("related_scars", []),
            notes=data.get("notes"),
        )


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
    prep_queue: List[PrepItem] = field(default_factory=list)
    
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
            "prep_queue": [p.to_dict() for p in self.prep_queue],
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Campaign":
        """Deserialize from dictionary."""
        campaign_state = None
        if data.get("campaign_state"):
            campaign_state = CampaignState.from_dict(data["campaign_state"])
        
        sources_data = data.get("sources", [])
        sources = [Source.from_dict(s) for s in sources_data]
        
        prep_queue_data = data.get("prep_queue", [])
        prep_queue = [PrepItem.from_dict(p) for p in prep_queue_data]
        
        return Campaign(
            campaign_id=data["campaign_id"],
            name=data["name"],
            created=data["created"],
            last_played=data["last_played"],
            canon_summary=data.get("canon_summary", []),
            campaign_state=campaign_state,
            ledger=data.get("ledger", []),
            sources=sources,
            prep_queue=prep_queue,
        )
    
    def get_path(self) -> Path:
        """Get filesystem path for this campaign in subdirectory."""
        campaign_dir = CAMPAIGNS_DIR / normalize_campaign_name_to_dir(self.name)
        return campaign_dir / f"{self.campaign_id}.json"

    def save(self) -> None:
        """Save campaign to disk in subdirectory."""
        path = self.get_path()
        path.parent.mkdir(parents=True, exist_ok=True)  # Ensure subdirectory exists
        path.write_text(json.dumps(self.to_dict(), indent=2))
    
    @staticmethod
    def load(campaign_id: str) -> Optional["Campaign"]:
        """Load campaign from disk (searches subdirectories)."""
        # Search all subdirectories for the campaign file
        for subdir in CAMPAIGNS_DIR.iterdir():
            if subdir.is_dir():
                path = subdir / f"{campaign_id}.json"
                if path.exists():
                    try:
                        data = json.loads(path.read_text())
                        return Campaign.from_dict(data)
                    except Exception:
                        continue
        return None

    @staticmethod
    def list_all() -> List["Campaign"]:
        """List all campaigns from subdirectories."""
        campaigns = []
        # Scan all subdirectories for campaign JSON files
        for subdir in CAMPAIGNS_DIR.iterdir():
            if subdir.is_dir():
                for json_file in subdir.glob("campaign_*.json"):
                    # Skip import_overrides files
                    if "_import_overrides" in json_file.name:
                        continue
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


def _save_override_promote_to_faction(campaign_id: str, entity_name: str, from_category: str) -> None:
    """Helper to save promotion to faction in overrides."""
    overrides = ImportOverrides.load(campaign_id)
    overrides.promoted_to_faction.add(entity_name)
    # Remove from demoted sets
    overrides.demoted_to_place.discard(entity_name)
    overrides.demoted_to_artifact.discard(entity_name)
    overrides.demoted_to_concept.discard(entity_name)
    overrides.ignored.discard(entity_name)
    overrides.save()


def _save_override_demote_from_faction(campaign_id: str, entity_name: str, to_category: str) -> None:
    """Helper to save demotion from faction in overrides."""
    overrides = ImportOverrides.load(campaign_id)
    overrides.promoted_to_faction.discard(entity_name)
    
    if to_category == "place":
        overrides.demoted_to_place.add(entity_name)
    elif to_category == "artifact":
        overrides.demoted_to_artifact.add(entity_name)
    elif to_category == "concept":
        overrides.demoted_to_concept.add(entity_name)
    
    overrides.save()


def _save_override_lateral_move(campaign_id: str, entity_name: str, to_category: str) -> None:
    """Helper to save lateral move (non-faction to non-faction) in overrides."""
    overrides = ImportOverrides.load(campaign_id)
    
    # Remove from all demoted sets first
    overrides.demoted_to_place.discard(entity_name)
    overrides.demoted_to_artifact.discard(entity_name)
    overrides.demoted_to_concept.discard(entity_name)
    
    # Add to target category
    if to_category == "place":
        overrides.demoted_to_place.add(entity_name)
    elif to_category == "artifact":
        overrides.demoted_to_artifact.add(entity_name)
    elif to_category == "concept":
        overrides.demoted_to_concept.add(entity_name)
    
    overrides.save()


def _save_override_remove(campaign_id: str, entity_name: str) -> None:
    """Helper to save entity removal in overrides."""
    overrides = ImportOverrides.load(campaign_id)
    overrides.ignored.add(entity_name)
    # Remove from all other sets
    overrides.promoted_to_faction.discard(entity_name)
    overrides.demoted_to_place.discard(entity_name)
    overrides.demoted_to_artifact.discard(entity_name)
    overrides.demoted_to_concept.discard(entity_name)
    overrides.save()


def _render_prep_item(campaign: Campaign, item: PrepItem, show_unarchive: bool = False) -> None:
    """Render a single prep item with inline controls."""
    with st.container(border=True):
        # Status indicator
        status_emoji = {"pinned": "📌", "queued": "📋", "archived": "📦"}.get(item.status, "📋")
        
        col1, col2 = st.columns([10, 2])
        
        with col1:
            st.markdown(f"{status_emoji} **{item.title}**")
            st.caption(item.summary)
            
            # Tags (compact)
            if item.tags:
                tag_str = ", ".join(item.tags[:5])
                if len(item.tags) > 5:
                    tag_str += f" (+{len(item.tags) - 5} more)"
                st.caption(f"🏷️ {tag_str}")
            
            # Source metadata (small)
            if item.source:
                source_parts = []
                if item.source.get("scenario_name"):
                    source_parts.append(f"Scenario: {item.source['scenario_name']}")
                if item.source.get("preset"):
                    source_parts.append(f"{item.source['preset']}")
                if item.source.get("phase"):
                    source_parts.append(f"{item.source['phase']}")
                if item.source.get("seed"):
                    source_parts.append(f"Seed: {item.source['seed']}")
                if source_parts:
                    st.caption(f"🎲 {' | '.join(source_parts)}")
        
        with col2:
            # Inline controls
            if item.status == "pinned":
                if st.button("📌", key=f"unpin_{item.item_id}", help="Unpin"):
                    # Keep prep queue expanded after action
                    st.session_state.prep_queue_expanded = True
                    # Find and update item
                    for i, p in enumerate(campaign.prep_queue):
                        if p.item_id == item.item_id:
                            campaign.prep_queue[i].status = "queued"
                            break
                    campaign.save()
                    st.rerun()
            else:
                if st.button("📌", key=f"pin_{item.item_id}", help="Pin"):
                    # Keep prep queue expanded after action
                    st.session_state.prep_queue_expanded = True
                    # Find and update item
                    for i, p in enumerate(campaign.prep_queue):
                        if p.item_id == item.item_id:
                            campaign.prep_queue[i].status = "pinned"
                            break
                    campaign.save()
                    st.rerun()
            
            if show_unarchive:
                if st.button("↩️", key=f"unarchive_{item.item_id}", help="Unarchive"):
                    # Keep prep queue expanded after action
                    st.session_state.prep_queue_expanded = True
                    for i, p in enumerate(campaign.prep_queue):
                        if p.item_id == item.item_id:
                            campaign.prep_queue[i].status = "queued"
                            break
                    campaign.save()
                    st.rerun()
            else:
                if st.button("📦", key=f"archive_{item.item_id}", help="Archive"):
                    # Keep prep queue expanded after action
                    st.session_state.prep_queue_expanded = True
                    for i, p in enumerate(campaign.prep_queue):
                        if p.item_id == item.item_id:
                            campaign.prep_queue[i].status = "archived"
                            break
                    campaign.save()
                    st.rerun()
            
            if st.button("🗑️", key=f"delete_{item.item_id}", help="Delete"):
                # Keep prep queue expanded after action
                st.session_state.prep_queue_expanded = True
                campaign.prep_queue = [p for p in campaign.prep_queue if p.item_id != item.item_id]
                campaign.save()
                st.rerun()


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
            st.session_state.show_history_import = True
    
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
                            name=f_name,  # Display name
                            description="",
                            attention=0,
                            disposition=0,
                            notes=None,
                            is_active=True,
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
    
    # History Import Form (Flow D: New Campaign)
    if st.session_state.get("show_history_import", False):
        st.subheader("📥 Import Campaign History")
        st.caption("Create new campaign from existing history")
        
        history_text = st.text_area("Paste campaign history", height=200, placeholder="Paste session notes, date markers, faction names...")
        
        if st.button("Parse History"):
            if history_text:
                from streamlit_harness.history_parser import parse_campaign_history
                parsed = parse_campaign_history(history_text)
                st.session_state.parsed_history = parsed
        
        # Show parse preview if available
        if st.session_state.get("parsed_history"):
            parsed = st.session_state.parsed_history
            
            # Add JSON export button
            parsed_json = json.dumps(parsed, indent=2, default=str)
            st.download_button(
                label="📥 Download Parsed JSON",
                data=parsed_json,
                file_name=f"parsed_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True,
            )
            
            st.markdown("**Parse Preview**")
            for note in parsed["notes"]:
                st.caption(note)
            
            with st.expander("Sessions Detected", expanded=True):
                for session in parsed["sessions"]:
                    st.markdown(f"**Session {session['session_number']}** - {session['date']}")
                    st.caption(session['content'][:100] + "..." if len(session['content']) > 100 else session['content'])
            
            with st.expander("Canon Summary", expanded=True):
                for bullet in parsed["canon_summary"]:
                    st.write(f"• {bullet}")
            
            with st.expander("Factions Detected", expanded=True):
                if parsed["factions"]:
                    for idx, faction in enumerate(parsed["factions"]):
                        col1, col2, col3, col4, col5 = st.columns([8, 2, 2, 2, 1])
                        with col1:
                            st.write(f"• {faction}")
                        with col2:
                            if st.button("→Place", key=f"f_place_{idx}", help="Demote to Place"):
                                factions = list(parsed["factions"])
                                factions.remove(faction)
                                places = list(parsed["entities"]["places"])
                                places.append(faction)
                                st.session_state.parsed_history["factions"] = sorted(factions)
                                st.session_state.parsed_history["entities"]["places"] = sorted(places)
                                st.rerun()
                        with col3:
                            if st.button("→Artifact", key=f"f_art_{idx}", help="Demote to Artifact"):
                                factions = list(parsed["factions"])
                                factions.remove(faction)
                                artifacts = list(parsed["entities"]["artifacts"])
                                artifacts.append(faction)
                                st.session_state.parsed_history["factions"] = sorted(factions)
                                st.session_state.parsed_history["entities"]["artifacts"] = sorted(artifacts)
                                st.rerun()
                        with col4:
                            if st.button("→Concept", key=f"f_con_{idx}", help="Demote to Concept"):
                                factions = list(parsed["factions"])
                                factions.remove(faction)
                                concepts = list(parsed["entities"]["concepts"])
                                concepts.append(faction)
                                st.session_state.parsed_history["factions"] = sorted(factions)
                                st.session_state.parsed_history["entities"]["concepts"] = sorted(concepts)
                                st.rerun()
                        with col5:
                            if st.button("✕", key=f"f_rem_{idx}", help="Remove"):
                                factions = list(parsed["factions"])
                                factions.remove(faction)
                                st.session_state.parsed_history["factions"] = sorted(factions)
                                st.rerun()
                else:
                    st.caption("No factions detected")
            
            # Show classified entities (non-factions) with controls
            entities = parsed.get("entities", {})
            if any(entities.values()):
                with st.expander("Entities (Non-Factions)", expanded=False):
                    if entities.get("places"):
                        st.markdown("**Places:**")
                        for idx, place in enumerate(entities["places"]):
                            col1, col2, col3, col4, col5 = st.columns([8, 2, 2, 2, 1])
                            with col1:
                                st.caption(f"• {place}")
                            with col2:
                                if st.button("↑Faction", key=f"p_fac_{idx}", help="Promote to Faction"):
                                    places = list(parsed["entities"]["places"])
                                    places.remove(place)
                                    factions = list(parsed["factions"])
                                    factions.append(place)
                                    st.session_state.parsed_history["entities"]["places"] = sorted(places)
                                    st.session_state.parsed_history["factions"] = sorted(factions)
                                    st.rerun()
                            with col3:
                                if st.button("→Artifact", key=f"p_art_{idx}", help="Change to Artifact"):
                                    places = list(parsed["entities"]["places"])
                                    places.remove(place)
                                    artifacts = list(parsed["entities"]["artifacts"])
                                    artifacts.append(place)
                                    st.session_state.parsed_history["entities"]["places"] = sorted(places)
                                    st.session_state.parsed_history["entities"]["artifacts"] = sorted(artifacts)
                                    st.rerun()
                            with col4:
                                if st.button("→Concept", key=f"p_con_{idx}", help="Change to Concept"):
                                    places = list(parsed["entities"]["places"])
                                    places.remove(place)
                                    concepts = list(parsed["entities"]["concepts"])
                                    concepts.append(place)
                                    st.session_state.parsed_history["entities"]["places"] = sorted(places)
                                    st.session_state.parsed_history["entities"]["concepts"] = sorted(concepts)
                                    st.rerun()
                            with col5:
                                if st.button("✕", key=f"p_rem_{idx}", help="Remove"):
                                    places = list(parsed["entities"]["places"])
                                    places.remove(place)
                                    st.session_state.parsed_history["entities"]["places"] = sorted(places)
                                    st.rerun()
                    if entities.get("artifacts"):
                        st.markdown("**Artifacts:**")
                        for idx, artifact in enumerate(entities["artifacts"]):
                            col1, col2, col3, col4, col5 = st.columns([8, 2, 2, 2, 1])
                            with col1:
                                st.caption(f"• {artifact}")
                            with col2:
                                if st.button("↑Faction", key=f"a_fac_{idx}", help="Promote to Faction"):
                                    artifacts = list(parsed["entities"]["artifacts"])
                                    artifacts.remove(artifact)
                                    factions = list(parsed["factions"])
                                    factions.append(artifact)
                                    st.session_state.parsed_history["entities"]["artifacts"] = sorted(artifacts)
                                    st.session_state.parsed_history["factions"] = sorted(factions)
                                    st.rerun()
                            with col3:
                                if st.button("→Place", key=f"a_pla_{idx}", help="Change to Place"):
                                    artifacts = list(parsed["entities"]["artifacts"])
                                    artifacts.remove(artifact)
                                    places = list(parsed["entities"]["places"])
                                    places.append(artifact)
                                    st.session_state.parsed_history["entities"]["artifacts"] = sorted(artifacts)
                                    st.session_state.parsed_history["entities"]["places"] = sorted(places)
                                    st.rerun()
                            with col4:
                                if st.button("→Concept", key=f"a_con_{idx}", help="Change to Concept"):
                                    artifacts = list(parsed["entities"]["artifacts"])
                                    artifacts.remove(artifact)
                                    concepts = list(parsed["entities"]["concepts"])
                                    concepts.append(artifact)
                                    st.session_state.parsed_history["entities"]["artifacts"] = sorted(artifacts)
                                    st.session_state.parsed_history["entities"]["concepts"] = sorted(concepts)
                                    st.rerun()
                            with col5:
                                if st.button("✕", key=f"a_rem_{idx}", help="Remove"):
                                    artifacts = list(parsed["entities"]["artifacts"])
                                    artifacts.remove(artifact)
                                    st.session_state.parsed_history["entities"]["artifacts"] = sorted(artifacts)
                                    st.rerun()
                    if entities.get("concepts"):
                        st.markdown("**Concepts/Powers:**")
                        for idx, concept in enumerate(entities["concepts"]):
                            col1, col2, col3, col4, col5 = st.columns([8, 2, 2, 2, 1])
                            with col1:
                                st.caption(f"• {concept}")
                            with col2:
                                if st.button("↑Faction", key=f"c_fac_{idx}", help="Promote to Faction"):
                                    concepts = list(parsed["entities"]["concepts"])
                                    concepts.remove(concept)
                                    factions = list(parsed["factions"])
                                    factions.append(concept)
                                    st.session_state.parsed_history["entities"]["concepts"] = sorted(concepts)
                                    st.session_state.parsed_history["factions"] = sorted(factions)
                                    st.rerun()
                            with col3:
                                if st.button("→Place", key=f"c_pla_{idx}", help="Change to Place"):
                                    concepts = list(parsed["entities"]["concepts"])
                                    concepts.remove(concept)
                                    places = list(parsed["entities"]["places"])
                                    places.append(concept)
                                    st.session_state.parsed_history["entities"]["concepts"] = sorted(concepts)
                                    st.session_state.parsed_history["entities"]["places"] = sorted(places)
                                    st.rerun()
                            with col4:
                                if st.button("→Artifact", key=f"c_art_{idx}", help="Change to Artifact"):
                                    concepts = list(parsed["entities"]["concepts"])
                                    concepts.remove(concept)
                                    artifacts = list(parsed["entities"]["artifacts"])
                                    artifacts.append(concept)
                                    st.session_state.parsed_history["entities"]["concepts"] = sorted(concepts)
                                    st.session_state.parsed_history["entities"]["artifacts"] = sorted(artifacts)
                                    st.rerun()
                            with col5:
                                if st.button("✕", key=f"c_rem_{idx}", help="Remove"):
                                    concepts = list(parsed["entities"]["concepts"])
                                    concepts.remove(concept)
                                    st.session_state.parsed_history["entities"]["concepts"] = sorted(concepts)
                                    st.rerun()
            
            # Show future sessions (not imported)
            future = parsed.get("future_sessions", [])
            if future:
                with st.expander("Future Sessions (Not Imported)", expanded=False):
                    for session in future:
                        st.markdown(f"**{session['title']}**")
                        st.caption(session['notes'][:100] + "..." if len(session['notes']) > 100 else session['notes'])
            
            # Show open threads (not imported)
            threads = parsed.get("open_threads", [])
            if threads:
                with st.expander("Open Threads (Not Imported)", expanded=False):
                    for thread in threads:
                        st.caption(f"• {thread[:150]}..." if len(thread) > 150 else f"• {thread}")
            
            # Create campaign from parsed history
            campaign_name_import = st.text_input("Campaign Name", value="Imported Campaign")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Create Campaign from History", type="primary"):
                    # Create campaign with parsed data
                    campaign_id = f"campaign_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    timestamp = datetime.now().isoformat()
                    
                    # Initialize state with detected factions
                    campaign_state = CampaignState.default()
                    initial_factions = {}
                    for f_name in parsed["factions"]:
                        fid = f_name.lower().replace(" ", "_")
                        initial_factions[fid] = FactionState(
                            faction_id=fid,
                            name=f_name,  # Display name
                            description="",
                            attention=0,
                            disposition=0,
                            notes=None,
                            is_active=True,
                        )
                    
                    if initial_factions:
                        campaign_state = CampaignState(
                            version="0.2",
                            campaign_pressure=0,
                            heat=0,
                            scars=[],
                            factions=initial_factions,
                            total_scenes_run=len(parsed["sessions"]),
                            total_cutoffs_seen=0,
                            highest_severity_seen=0,
                            _legacy_scars=set(),
                        )
                    
                    # Create ledger from parsed sessions
                    # FIX 1: Skip invalid sessions (null session_number AND empty content)
                    ledger = []
                    for session in parsed["sessions"]:
                        # Validate session has meaningful content
                        content = session.get("content", "").strip()
                        session_num = session.get("session_number")
                        
                        # Skip if both null session_number AND empty/whitespace-only content
                        if session_num is None and not content:
                            continue
                        
                        # Only add valid sessions with non-empty content
                        if content:
                            ledger.append({
                                "session_number": session_num,
                                "session_date": session["date"],
                                "what_happened": [content[:200]],  # Truncate
                                "deltas": {"pressure_change": 0, "heat_change": 0},
                                "active_sources": [],
                            })
                    
                    campaign = Campaign(
                        campaign_id=campaign_id,
                        name=campaign_name_import,
                        created=timestamp,
                        last_played=timestamp,
                        canon_summary=parsed["canon_summary"],
                        campaign_state=campaign_state,
                        ledger=ledger,
                    )
                    
                    campaign.save()
                    
                    # Initialize empty import overrides file for new campaign
                    overrides = ImportOverrides(campaign_id=campaign_id)
                    overrides.save()
                    
                    st.session_state.current_campaign_id = campaign_id
                    st.session_state.show_history_import = False
                    st.session_state.parsed_history = None
                    st.session_state.campaign_page = "dashboard"
                    st.success(f"Campaign '{campaign_name_import}' created from history!")
                    st.rerun()
            
            with col2:
                if st.button("Cancel"):
                    st.session_state.show_history_import = False
                    st.session_state.parsed_history = None
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
    
    # Use version counter to force widget refresh on deletion
    if "canon_version" not in st.session_state:
        st.session_state.canon_version = 0
    
    canon_version = st.session_state.canon_version
    bullets_to_display = campaign.canon_summary[:15]  # Display first 15
    delete_index = None
    text_edits = {}
    
    # Phase 1: Collect changes during render (no modifications yet)
    for idx, bullet in enumerate(bullets_to_display):
        col1, col2 = st.columns([11, 1])
        with col1:
            # CRITICAL: Include version in key to force widget recreation on deletion
            new_text = st.text_input(
                f"Canon {idx+1}",
                value=bullet,
                key=f"canon_bullet_{idx}_v{canon_version}",
                label_visibility="collapsed"
            )
            if new_text != bullet:
                text_edits[idx] = new_text  # Map index to new content
        with col2:
            if st.button("🗑️", key=f"delete_canon_{idx}_v{canon_version}"):
                delete_index = idx  # Store which index to delete
    
    # Phase 2: Apply changes after render loop completes
    if text_edits or delete_index is not None:
        working_list = list(campaign.canon_summary)
        
        # CRITICAL: If deletion occurred, IGNORE text edits
        # Text edits from widgets will be stale after rerun/reindex
        if delete_index is not None:
            # Just do deletion, skip text edits
            deleted_content = None
            if delete_index < len(working_list):
                deleted_content = working_list[delete_index]
                working_list.pop(delete_index)
            
            # Save changes
            campaign.canon_summary = working_list
            campaign.save()
            
            # CRITICAL: Increment version to force new widget keys on next render
            # This creates entirely new widgets instead of reusing cached ones
            st.session_state.canon_version += 1
            
            # Use st.stop() to immediately halt execution before rerun
            st.rerun()
            st.stop()  # Ensure no further rendering happens with stale data
        else:
            # No deletion, just apply text edits
            for idx, new_text in text_edits.items():
                if idx < len(working_list):
                    working_list[idx] = new_text
            
            campaign.canon_summary = working_list
            campaign.save()
    
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
    
    # Factions (Interactive CRUD)
    if campaign.campaign_state:
        active_factions = {fid: f for fid, f in campaign.campaign_state.factions.items() if f.is_active}
        archived_factions = {fid: f for fid, f in campaign.campaign_state.factions.items() if not f.is_active}
        
        with st.expander(f"👥 Factions ({len(active_factions)})", expanded=True):
            # Add faction button
            if st.button("➕ Add Faction", key="add_faction_btn"):
                st.session_state.show_add_faction_form = True
            
            # Add faction form (inline)
            if st.session_state.get("show_add_faction_form", False):
                with st.container(border=True):
                    st.markdown("**Add New Faction**")
                    
                    new_faction_name = st.text_input("Name*", placeholder="e.g., City Watch", key="new_faction_name")
                    new_faction_desc = st.text_area(
                        "Description (what it is/wants)",
                        placeholder="e.g., Local law enforcement, focused on maintaining order",
                        height=60,
                        key="new_faction_desc"
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        new_faction_attention = st.slider("Initial Attention", 0, 20, 0, key="new_faction_attention")
                        st.caption(f"Band: {FactionState(faction_id='temp', name='temp', attention=new_faction_attention).get_attention_band()}")
                    with col2:
                        disposition_options = [
                            (-2, "😡 Hostile"),
                            (-1, "😠 Unfriendly"),
                            (0, "😐 Neutral"),
                            (1, "🙂 Friendly"),
                            (2, "😊 Allied"),
                        ]
                        new_faction_disp = st.select_slider(
                            "Initial Disposition",
                            options=[d[0] for d in disposition_options],
                            value=0,
                            format_func=lambda x: next(label for val, label in disposition_options if val == x),
                            key="new_faction_disp"
                        )
                    
                    new_faction_notes = st.text_area(
                        "GM Notes (private, not exported)",
                        placeholder="Your private notes, plans, secrets...",
                        height=60,
                        key="new_faction_notes"
                    )
                    
                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        if st.button("💾 Add", key="save_new_faction", type="primary"):
                            if new_faction_name:
                                fid = new_faction_name.lower().replace(" ", "_").replace("-", "_")
                                
                                # Check for duplicate
                                if fid in campaign.campaign_state.factions:
                                    st.error(f"Faction ID '{fid}' already exists")
                                else:
                                    # Create new faction
                                    new_faction = FactionState(
                                        faction_id=fid,
                                        name=new_faction_name,
                                        description=new_faction_desc.strip(),
                                        attention=new_faction_attention,
                                        disposition=new_faction_disp,
                                        notes=new_faction_notes.strip() if new_faction_notes.strip() else None,
                                        is_active=True,
                                    )
                                    
                                    # Add to campaign
                                    new_factions_dict = dict(campaign.campaign_state.factions)
                                    new_factions_dict[fid] = new_faction
                                    
                                    campaign.campaign_state = CampaignState(
                                        version=campaign.campaign_state.version,
                                        campaign_pressure=campaign.campaign_state.campaign_pressure,
                                        heat=campaign.campaign_state.heat,
                                        scars=campaign.campaign_state.scars,
                                        factions=new_factions_dict,
                                        total_scenes_run=campaign.campaign_state.total_scenes_run,
                                        total_cutoffs_seen=campaign.campaign_state.total_cutoffs_seen,
                                        highest_severity_seen=campaign.campaign_state.highest_severity_seen,
                                        _legacy_scars=campaign.campaign_state._legacy_scars,
                                    )
                                    
                                    # Add audit entry (system-facing)
                                    audit_entry = {
                                        "entry_type": "admin_action",
                                        "timestamp": datetime.now().isoformat(),
                                        "action": "faction_added",
                                        "details": {
                                            "faction_id": fid,
                                            "name": new_faction_name,
                                            "initial_attention": new_faction_attention,
                                            "initial_disposition": new_faction_disp,
                                        }
                                    }
                                    campaign.ledger.append(audit_entry)
                                    
                                    campaign.save()
                                    st.session_state.show_add_faction_form = False
                                    st.success(f"✓ Added faction: {new_faction_name}")
                                    st.rerun()
                            else:
                                st.error("Name is required")
                    
                    with col_cancel:
                        if st.button("Cancel", key="cancel_new_faction"):
                            st.session_state.show_add_faction_form = False
                            st.rerun()
                
                st.divider()
            
            # Display active factions
            if not active_factions:
                st.info("No factions yet. Add your first faction above!")
            else:
                for fid, faction in active_factions.items():
                    # Check if in edit mode
                    edit_key = f"edit_faction_{fid}"
                    is_editing = st.session_state.get(edit_key, False)
                    
                    if is_editing:
                        # Edit mode
                        with st.container(border=True):
                            st.markdown(f"**Editing: {faction.name}**")
                            
                            edit_name = st.text_input("Name*", value=faction.name, key=f"edit_name_{fid}")
                            edit_desc = st.text_area(
                                "Description",
                                value=faction.description,
                                height=60,
                                key=f"edit_desc_{fid}"
                            )
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                edit_attention = st.slider("Attention", 0, 20, faction.attention, key=f"edit_att_{fid}")
                                st.caption(f"Band: {FactionState(faction_id='temp', name='temp', attention=edit_attention).get_attention_band()}")
                            with col2:
                                disposition_options = [
                                    (-2, "😡 Hostile"),
                                    (-1, "😠 Unfriendly"),
                                    (0, "😐 Neutral"),
                                    (1, "🙂 Friendly"),
                                    (2, "😊 Allied"),
                                ]
                                edit_disp = st.select_slider(
                                    "Disposition",
                                    options=[d[0] for d in disposition_options],
                                    value=faction.disposition,
                                    format_func=lambda x: next(label for val, label in disposition_options if val == x),
                                    key=f"edit_disp_{fid}"
                                )
                            
                            edit_notes = st.text_area(
                                "GM Notes (private)",
                                value=faction.notes or "",
                                height=60,
                                key=f"edit_notes_{fid}"
                            )
                            
                            col_save, col_cancel = st.columns(2)
                            with col_save:
                                if st.button("💾 Save", key=f"save_edit_{fid}", type="primary"):
                                    if edit_name:
                                        # Update faction
                                        updated_faction = FactionState(
                                            faction_id=fid,
                                            name=edit_name,
                                            description=edit_desc.strip(),
                                            attention=edit_attention,
                                            disposition=edit_disp,
                                            notes=edit_notes.strip() if edit_notes.strip() else None,
                                            is_active=True,
                                        )
                                        
                                        new_factions_dict = dict(campaign.campaign_state.factions)
                                        new_factions_dict[fid] = updated_faction
                                        
                                        campaign.campaign_state = CampaignState(
                                            version=campaign.campaign_state.version,
                                            campaign_pressure=campaign.campaign_state.campaign_pressure,
                                            heat=campaign.campaign_state.heat,
                                            scars=campaign.campaign_state.scars,
                                            factions=new_factions_dict,
                                            total_scenes_run=campaign.campaign_state.total_scenes_run,
                                            total_cutoffs_seen=campaign.campaign_state.total_cutoffs_seen,
                                            highest_severity_seen=campaign.campaign_state.highest_severity_seen,
                                            _legacy_scars=campaign.campaign_state._legacy_scars,
                                        )
                                        
                                        # Add audit entry
                                        audit_entry = {
                                            "entry_type": "admin_action",
                                            "timestamp": datetime.now().isoformat(),
                                            "action": "faction_edited",
                                            "details": {
                                                "faction_id": fid,
                                                "changes": {
                                                    "name": edit_name if edit_name != faction.name else None,
                                                    "attention": edit_attention if edit_attention != faction.attention else None,
                                                    "disposition": edit_disp if edit_disp != faction.disposition else None,
                                                }
                                            }
                                        }
                                        campaign.ledger.append(audit_entry)
                                        
                                        campaign.save()
                                        st.session_state[edit_key] = False
                                        st.success(f"✓ Updated faction: {edit_name}")
                                        st.rerun()
                                    else:
                                        st.error("Name is required")
                            
                            with col_cancel:
                                if st.button("Cancel", key=f"cancel_edit_{fid}"):
                                    st.session_state[edit_key] = False
                                    st.rerun()
                    else:
                        # View mode with quick controls
                        with st.container(border=True):
                            col1, col2, col3 = st.columns([8, 3, 1])
                            
                            with col1:
                                st.markdown(f"**{faction.name}**")
                                if faction.description:
                                    st.caption(faction.description)
                                
                                # Show attention with band and disposition
                                attention_band = faction.get_attention_band()
                                disp_label = faction.get_disposition_label()
                                st.caption(f"{attention_band} | {disp_label}")
                                
                                # Progress bar for attention
                                attention_pct = (faction.attention / 20) * 100
                                st.progress(attention_pct / 100)
                            
                            with col2:
                                # Quick attention adjustment
                                att_col1, att_col2 = st.columns(2)
                                with att_col1:
                                    if st.button("➖", key=f"dec_att_{fid}", help="Decrease attention", disabled=(faction.attention == 0)):
                                        # Quick decrease
                                        new_factions_dict = dict(campaign.campaign_state.factions)
                                        new_factions_dict[fid] = FactionState(
                                            faction_id=faction.faction_id,
                                            name=faction.name,
                                            description=faction.description,
                                            attention=max(0, faction.attention - 1),
                                            disposition=faction.disposition,
                                            notes=faction.notes,
                                            is_active=faction.is_active,
                                        )
                                        
                                        campaign.campaign_state = CampaignState(
                                            version=campaign.campaign_state.version,
                                            campaign_pressure=campaign.campaign_state.campaign_pressure,
                                            heat=campaign.campaign_state.heat,
                                            scars=campaign.campaign_state.scars,
                                            factions=new_factions_dict,
                                            total_scenes_run=campaign.campaign_state.total_scenes_run,
                                            total_cutoffs_seen=campaign.campaign_state.total_cutoffs_seen,
                                            highest_severity_seen=campaign.campaign_state.highest_severity_seen,
                                            _legacy_scars=campaign.campaign_state._legacy_scars,
                                        )
                                        campaign.save()
                                        st.rerun()
                                
                                with att_col2:
                                    if st.button("➕", key=f"inc_att_{fid}", help="Increase attention", disabled=(faction.attention == 20)):
                                        # Quick increase
                                        new_factions_dict = dict(campaign.campaign_state.factions)
                                        new_factions_dict[fid] = FactionState(
                                            faction_id=faction.faction_id,
                                            name=faction.name,
                                            description=faction.description,
                                            attention=min(20, faction.attention + 1),
                                            disposition=faction.disposition,
                                            notes=faction.notes,
                                            is_active=faction.is_active,
                                        )
                                        
                                        campaign.campaign_state = CampaignState(
                                            version=campaign.campaign_state.version,
                                            campaign_pressure=campaign.campaign_state.campaign_pressure,
                                            heat=campaign.campaign_state.heat,
                                            scars=campaign.campaign_state.scars,
                                            factions=new_factions_dict,
                                            total_scenes_run=campaign.campaign_state.total_scenes_run,
                                            total_cutoffs_seen=campaign.campaign_state.total_cutoffs_seen,
                                            highest_severity_seen=campaign.campaign_state.highest_severity_seen,
                                            _legacy_scars=campaign.campaign_state._legacy_scars,
                                        )
                                        campaign.save()
                                        st.rerun()
                                
                                st.caption(f"{faction.attention}/20")
                            
                            with col3:
                                # Edit and archive buttons
                                if st.button("✏️", key=f"edit_btn_{fid}", help="Edit faction"):
                                    st.session_state[edit_key] = True
                                    st.rerun()
                                
                                if st.button("📦", key=f"archive_btn_{fid}", help="Archive faction"):
                                    # Soft delete
                                    new_factions_dict = dict(campaign.campaign_state.factions)
                                    new_factions_dict[fid] = FactionState(
                                        faction_id=faction.faction_id,
                                        name=faction.name,
                                        description=faction.description,
                                        attention=faction.attention,
                                        disposition=faction.disposition,
                                        notes=faction.notes,
                                        is_active=False,  # Soft delete
                                    )
                                    
                                    campaign.campaign_state = CampaignState(
                                        version=campaign.campaign_state.version,
                                        campaign_pressure=campaign.campaign_state.campaign_pressure,
                                        heat=campaign.campaign_state.heat,
                                        scars=campaign.campaign_state.scars,
                                        factions=new_factions_dict,
                                        total_scenes_run=campaign.campaign_state.total_scenes_run,
                                        total_cutoffs_seen=campaign.campaign_state.total_cutoffs_seen,
                                        highest_severity_seen=campaign.campaign_state.highest_severity_seen,
                                        _legacy_scars=campaign.campaign_state._legacy_scars,
                                    )
                                    
                                    # Add audit entry
                                    audit_entry = {
                                        "entry_type": "admin_action",
                                        "timestamp": datetime.now().isoformat(),
                                        "action": "faction_archived",
                                        "details": {
                                            "faction_id": fid,
                                            "name": faction.name,
                                        }
                                    }
                                    campaign.ledger.append(audit_entry)
                                    
                                    campaign.save()
                                    st.success(f"✓ Archived faction: {faction.name}")
                                    st.rerun()
            
            # Show archived factions (collapsed)
            if archived_factions:
                with st.expander(f"📦 Archived Factions ({len(archived_factions)})", expanded=False):
                    for fid, faction in archived_factions.items():
                        col1, col2 = st.columns([10, 2])
                        with col1:
                            st.caption(f"**{faction.name}** ({faction.get_attention_band()}, {faction.get_disposition_label()})")
                        with col2:
                            if st.button("↩️", key=f"unarchive_{fid}", help="Restore faction"):
                                # Restore from archive
                                new_factions_dict = dict(campaign.campaign_state.factions)
                                new_factions_dict[fid] = FactionState(
                                    faction_id=faction.faction_id,
                                    name=faction.name,
                                    description=faction.description,
                                    attention=faction.attention,
                                    disposition=faction.disposition,
                                    notes=faction.notes,
                                    is_active=True,  # Restore
                                )
                                
                                campaign.campaign_state = CampaignState(
                                    version=campaign.campaign_state.version,
                                    campaign_pressure=campaign.campaign_state.campaign_pressure,
                                    heat=campaign.campaign_state.heat,
                                    scars=campaign.campaign_state.scars,
                                    factions=new_factions_dict,
                                    total_scenes_run=campaign.campaign_state.total_scenes_run,
                                    total_cutoffs_seen=campaign.campaign_state.total_cutoffs_seen,
                                    highest_severity_seen=campaign.campaign_state.highest_severity_seen,
                                    _legacy_scars=campaign.campaign_state._legacy_scars,
                                )
                                
                                # Add audit entry
                                audit_entry = {
                                    "entry_type": "admin_action",
                                    "timestamp": datetime.now().isoformat(),
                                    "action": "faction_restored",
                                    "details": {
                                        "faction_id": fid,
                                        "name": faction.name,
                                    }
                                }
                                campaign.ledger.append(audit_entry)
                                
                                campaign.save()
                                st.success(f"✓ Restored faction: {faction.name}")
                                st.rerun()
    
    # Last session changes
    if campaign.ledger:
        with st.expander("📋 Last Session Changes", expanded=True):
            last_entry = campaign.ledger[-1]
            session_date_str = last_entry.get('session_date', '')[:10] if last_entry.get('session_date') else ''
            st.caption(f"Session {last_entry.get('session_number', '?')}: {session_date_str}")
            
            if last_entry.get("what_happened"):
                what_happened = last_entry["what_happened"]
                st.markdown("**What Happened:**")
                
                # Show first 5 bullets, collapse rest if >5
                bullets_to_show = what_happened[:5]
                for bullet in bullets_to_show:
                    st.markdown(f"• {bullet}")
                
                # Show remaining bullets in collapsed section if >5
                if len(what_happened) > 5:
                    with st.expander(f"Show {len(what_happened) - 5} more bullets", expanded=False):
                        for bullet in what_happened[5:]:
                            st.markdown(f"• {bullet}")
            
            # Session notes if present
            if last_entry.get("session_notes"):
                with st.expander("Session Notes", expanded=False):
                    st.caption(last_entry["session_notes"])
            
            # Metadata if present
            if last_entry.get("metadata"):
                metadata = last_entry["metadata"]
                meta_parts = []
                if "severity_avg" in metadata:
                    meta_parts.append(f"Severity: {metadata['severity_avg']:.1f}")
                if "cutoff_rate" in metadata:
                    meta_parts.append(f"Cutoff: {metadata['cutoff_rate']*100:.0f}%")
                if "top_tags" in metadata and metadata["top_tags"]:
                    meta_parts.append(f"Tags: {', '.join(metadata['top_tags'][:3])}")
                if meta_parts:
                    st.caption(f"📊 {' | '.join(meta_parts)}")
            
            if last_entry.get("deltas"):
                deltas = last_entry["deltas"]
                st.caption(f"Pressure: {deltas.get('pressure_change', 0):+d} | Heat: {deltas.get('heat_change', 0):+d}")
    
    st.divider()
    
    # Prep Queue (Non-Canon) with Selection
    queued_items = [p for p in campaign.prep_queue if p.status == "queued"]
    pinned_items = [p for p in campaign.prep_queue if p.status == "pinned"]
    archived_items = [p for p in campaign.prep_queue if p.status == "archived"]
    active_count = len(queued_items) + len(pinned_items)
    
    # Initialize prep queue expanded state if not set
    if "prep_queue_expanded" not in st.session_state:
        st.session_state.prep_queue_expanded = False
    
    with st.expander(f"🎴 Prep Queue ({active_count}) — Not Yet Canon", expanded=st.session_state.prep_queue_expanded):
        st.caption("Potential encounters/events that haven't happened yet")
        
        if not campaign.prep_queue:
            st.info("No prep items yet. Generate events and send them here!")
        else:
            # Selection controls for promotion to canon
            active_items = pinned_items + queued_items
            if active_items:
                col1, col2, col3 = st.columns([3, 3, 6])
                
                # Compute selection count from checkbox keys
                selected_prep_count = sum(
                    1 for item in active_items
                    if st.session_state.get(f"prep_select_{item.item_id}", False)
                )
                
                with col1:
                    if st.button("☑️ Select All", key="prep_select_all"):
                        for item in active_items:
                            st.session_state[f"prep_select_{item.item_id}"] = True
                        st.rerun()
                
                with col2:
                    if st.button("☐ Select None", key="prep_select_none"):
                        for item in active_items:
                            st.session_state[f"prep_select_{item.item_id}"] = False
                        st.rerun()
                
                with col3:
                    # C: HARD cap check for Prep → Session Draft
                    over_cap = selected_prep_count > 25
                    if over_cap:
                        st.error(f"⚠️ Session drafts support up to 25 items. Currently selected: {selected_prep_count}")
                    
                    if st.button(
                        f"📝 Create Session Draft from Selected ({selected_prep_count})",
                        disabled=(selected_prep_count == 0 or over_cap),
                        type="primary" if (selected_prep_count > 0 and not over_cap) else "secondary",
                        use_container_width=True,
                        key="create_session_from_prep"
                    ):
                        # Create session packet from selected prep items
                        from streamlit_harness.session_packet import SessionPacket
                        
                        selected_items = [
                            item for item in active_items
                            if st.session_state.get(f"prep_select_{item.item_id}", False)
                        ]
                        
                        # Build happened_items list - ONE per selected item (not just top 3)
                        happened_items = [item.title for item in selected_items]
                        
                        # Aggregate tags
                        all_tags = []
                        for item in selected_items:
                            all_tags.extend(item.tags)
                        from collections import Counter
                        tag_counts = Counter(all_tags)
                        top_tags = tag_counts.most_common(10)
                        
                        # Create events from prep items for top_events
                        mock_events = []
                        for item in selected_items:
                            mock_events.append({
                                "title": item.title,
                                "content": item.summary,
                                "tags": item.tags,
                                "severity": 5,  # Default mid-range
                                "source": item.source,
                            })
                        
                        # Create packet with full happened_items list
                        packet = SessionPacket(
                            scenario_name=f"Prep Queue: {', '.join([i.title[:20] for i in selected_items[:2]])}...",
                            preset="prep_queue",
                            phase="mixed",
                            rarity_mode="curated",
                            seed=0,
                            batch_size=len(selected_items),
                            severity_avg=5.0,
                            cutoff_rate=0.0,
                            top_tags=top_tags,
                            top_events=mock_events,
                            suggested_pressure_delta=0,
                            suggested_heat_delta=0,
                            suggested_faction_updates={},
                            candidate_scars=[],
                            happened_items=happened_items,  # Full N-item list
                            notes=[
                                f"Session draft created from {len(selected_items)} prep items",
                                "Review and edit 'What Happened' entries before committing"
                            ],
                        )
                        
                        # Store selected item IDs for cleanup after commit
                        st.session_state.prep_items_to_archive = [item.item_id for item in selected_items]
                        
                        # Set packet and navigate to finalize
                        st.session_state.pending_session_packet = packet
                        st.session_state.campaign_page = "finalize"
                        st.rerun()
                
                st.divider()
            
            # Show pinned first with checkboxes
            if pinned_items:
                st.markdown("**📌 Pinned**")
                for item in pinned_items:
                    # Checkbox for selection
                    col_check, col_item = st.columns([1, 19])
                    with col_check:
                        checkbox_key = f"prep_select_{item.item_id}"
                        if checkbox_key not in st.session_state:
                            st.session_state[checkbox_key] = False
                        st.checkbox("", key=checkbox_key, label_visibility="collapsed")
                    with col_item:
                        _render_prep_item(campaign, item)
                st.divider()
            
            # Then queued with checkboxes
            if queued_items:
                if pinned_items:
                    st.markdown("**📋 Queued**")
                for item in queued_items:
                    # Checkbox for selection
                    col_check, col_item = st.columns([1, 19])
                    with col_check:
                        checkbox_key = f"prep_select_{item.item_id}"
                        if checkbox_key not in st.session_state:
                            st.session_state[checkbox_key] = False
                        st.checkbox("", key=checkbox_key, label_visibility="collapsed")
                    with col_item:
                        _render_prep_item(campaign, item)
            
            # Archived (collapsed, no checkboxes)
            if archived_items:
                with st.expander(f"📦 Archived ({len(archived_items)})", expanded=False):
                    for item in archived_items:
                        _render_prep_item(campaign, item, show_unarchive=True)
    
    st.divider()
    
    # D: Markdown Export Section
    with st.expander("📄 Export Campaign History", expanded=False):
        st.caption("Export campaign history (Canon Summary + Ledger) as Markdown")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Campaign History Export**")
            
            # Default path for campaign history (save in campaign subdirectory)
            normalized_name = campaign.name.lower().replace(' ', '_').replace('/', '_')
            campaign_dir = normalize_campaign_name_to_dir(campaign.name)
            default_history_path = f"campaigns/{campaign_dir}/{normalized_name}_campaign_history_{datetime.now().strftime('%Y%m%d')}.md"
            
            history_path = st.text_input(
                "Export path",
                value=default_history_path,
                key="history_export_path",
                help="Path for campaign history markdown file"
            )
            
            if st.button("📥 Export Campaign History", use_container_width=True):
                if history_path:
                    # Generate markdown content
                    lines = []
                    lines.append(f"# {campaign.name}")
                    lines.append(f"*Campaign history exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
                    lines.append("")
                    
                    # Canon Summary
                    lines.append("## Canon Summary")
                    lines.append("")
                    for bullet in campaign.canon_summary:
                        lines.append(f"- {bullet}")
                    lines.append("")
                    
                    # Factions Roster (story-facing: name + description, with human-readable bands)
                    if campaign.campaign_state and campaign.campaign_state.factions:
                        active_factions = {fid: f for fid, f in campaign.campaign_state.factions.items() if f.is_active}
                        if active_factions:
                            lines.append("## Factions")
                            lines.append("")
                            for fid, faction in active_factions.items():
                                # Human-readable bands (not raw numbers)
                                attention_band = faction.get_attention_band()
                                disp_label = faction.get_disposition_label().split()[1]  # Remove emoji
                                
                                lines.append(f"**{faction.name}** *({attention_band}, {disp_label})*")
                                
                                # Include description (story-facing) but NOT notes (GM-private)
                                if faction.description:
                                    lines.append(f"{faction.description}")
                                
                                lines.append("")
                    
                    # Campaign Ledger (filter out invalid entries)
                    if campaign.ledger:
                        lines.append("## Campaign Ledger")
                        lines.append("")
                        
                        # Filter: only include valid session entries (not admin actions or empty sessions)
                        valid_entries = [
                            e for e in campaign.ledger
                            if e.get('entry_type') != 'admin_action'  # Exclude system audit entries
                            and e.get('what_happened')  # Must have content
                            and any(item.strip() for item in e.get('what_happened', []))  # At least one non-empty item
                        ]
                        
                        for entry in valid_entries:
                            session_num = entry.get('session_number', '?')
                            session_date = entry.get('session_date', '')[:10]
                            
                            # Use session_id for disambiguation if present
                            session_id = entry.get('session_id')
                            if session_id:
                                # Extract just the time portion for disambiguation
                                time_portion = session_id.split('_')[-1] if '_' in session_id else session_id[-6:]
                                lines.append(f"### Session {session_num} — {session_date} ({time_portion})")
                            else:
                                lines.append(f"### Session {session_num} — {session_date}")
                            lines.append("")
                            
                            what_happened = entry.get('what_happened', [])
                            if what_happened:
                                lines.append("**What Happened:**")
                                for bullet in what_happened:
                                    lines.append(f"- {bullet}")
                                lines.append("")
                            
                            # Manual entries - STORY-FACING ONLY (per export spec v0.1)
                            manual_entries = entry.get('manual_entries')
                            if manual_entries:
                                lines.append("**Manual Entries & Notable Moments:**")
                                lines.append("")
                                for manual_entry in manual_entries:
                                    lines.append(f"#### {manual_entry['title']}")
                                    lines.append("")
                                    lines.append(f"{manual_entry['description']}")
                                    lines.append("")
                                    
                                    # Only include GM notes (story-facing)
                                    if manual_entry.get('notes'):
                                        lines.append(f"*GM Notes: {manual_entry['notes']}*")
                                        lines.append("")
                                    
                                    # EXCLUDED per export spec: tags, severity, related_factions/scars, pressure/heat deltas
                            
                            # Session notes if present
                            session_notes = entry.get('session_notes')
                            if session_notes:
                                lines.append("**Session Notes:**")
                                lines.append("")
                                lines.append(session_notes)
                                lines.append("")
                            
                            # EXCLUDED per export spec v0.1:
                            # - State Changes (numeric deltas are system-facing)
                            # - Metadata section (severity/cutoff/tags/scenario all system-facing)
                            # - Content Sources (system-facing attribution)
                    
                    markdown_content = "\n".join(lines)
                    
                    # Always provide download button
                    st.download_button(
                        label="📥 Download Campaign History",
                        data=markdown_content,
                        file_name=Path(history_path).name,
                        mime="text/markdown",
                        use_container_width=True,
                        key="download_campaign_history"
                    )
                    
                    # Also try local write if possible
                    try:
                        path = Path(history_path)
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text(markdown_content)
                        st.info(f"✓ Also saved to: {history_path}")
                    except Exception as e:
                        st.info(f"Note: Could not write to {history_path} - use download button above")
        
        with col2:
            st.markdown("**Session Export (Optional)**")
            
            # Default path for most recent session (save in campaign subdirectory)
            session_num = len(campaign.ledger)
            if session_num > 0:
                normalized_name = campaign.name.lower().replace(' ', '_').replace('/', '_')
                campaign_dir = normalize_campaign_name_to_dir(campaign.name)
                padded_num = str(session_num).zfill(3)
                default_session_path = f"campaigns/{campaign_dir}/{normalized_name}_session_{padded_num}_{datetime.now().strftime('%Y%m%d')}.md"
                
                session_path = st.text_input(
                    "Export path",
                    value=default_session_path,
                    key="session_export_path",
                    help="Path for session markdown file"
                )
                
                if st.button("📥 Export Last Session", use_container_width=True):
                    if session_path and campaign.ledger:
                        # Get last session
                        entry = campaign.ledger[-1]
                        
                        # Generate GM-useful markdown content
                        lines = []
                        session_num = entry.get('session_number', '?')
                        session_date = entry.get('session_date', '')[:10]
                        lines.append(f"# {campaign.name} — Session {session_num}")
                        lines.append(f"*Session date: {session_date}*")
                        lines.append("")
                        
                        # Collect referenced factions from this session
                        referenced_faction_ids = set()
                        
                        # From manual entries (explicit references)
                        manual_entries = entry.get('manual_entries', [])
                        if manual_entries:
                            for manual_entry in manual_entries:
                                if manual_entry.get('related_factions'):
                                    referenced_faction_ids.update(manual_entry['related_factions'])
                        
                        # Fallback: scan text ONLY if no explicit related_factions
                        # Conservative whole-word matching to avoid false positives
                        if not referenced_faction_ids and manual_entries and campaign.campaign_state:
                            import re
                            for manual_entry in manual_entries:
                                title_text = manual_entry.get('title', '')
                                desc_text = manual_entry.get('description', '')
                                combined_text = f"{title_text} {desc_text}".lower()
                                
                                # Only check active factions with attention > 0
                                for fid, faction in campaign.campaign_state.factions.items():
                                    if faction.is_active and faction.attention > 0:
                                        # Normalized whole-word match (avoid false positives)
                                        faction_name_normalized = faction.name.lower().strip()
                                        # Word boundary pattern: faction name as complete word(s)
                                        pattern = r'\b' + re.escape(faction_name_normalized) + r'\b'
                                        if re.search(pattern, combined_text):
                                            referenced_faction_ids.add(fid)
                        
                        # Show faction context for referenced factions (current status)
                        if referenced_faction_ids and campaign.campaign_state:
                            lines.append("## Factions (current status)")
                            lines.append("")
                            
                            for fid in sorted(referenced_faction_ids):
                                if fid in campaign.campaign_state.factions:
                                    faction = campaign.campaign_state.factions[fid]
                                    if faction.is_active:
                                        # Human-readable bands
                                        attention_band = faction.get_attention_band()
                                        disp_label = faction.get_disposition_label().split()[1]  # Remove emoji
                                        
                                        lines.append(f"**{faction.name}** *({attention_band}, {disp_label})*")
                                        
                                        # Include description (story-facing) but NOT notes (GM-private)
                                        if faction.description:
                                            lines.append(f"{faction.description}")
                                        
                                        lines.append("")
                            
                            lines.append("")
                        
                        what_happened = entry.get('what_happened', [])
                        if what_happened:
                            lines.append("## What Happened")
                            lines.append("")
                            for bullet in what_happened:
                                lines.append(f"- {bullet}")
                            lines.append("")
                        
                        # Manual entries - STORY-FACING ONLY (per export spec v0.1)
                        manual_entries = entry.get('manual_entries')
                        if manual_entries:
                            lines.append("## Manual Entries & Notable Moments")
                            lines.append("")
                            for manual_entry in manual_entries:
                                lines.append(f"### {manual_entry['title']}")
                                lines.append("")
                                lines.append(f"{manual_entry['description']}")
                                lines.append("")
                                
                                # Only include GM notes (story-facing)
                                if manual_entry.get('notes'):
                                    lines.append(f"*GM Notes: {manual_entry['notes']}*")
                                    lines.append("")
                                
                                # EXCLUDED per export spec: tags, severity, related_factions/scars, pressure/heat deltas
                        
                        # Session notes if present
                        session_notes = entry.get('session_notes')
                        if session_notes:
                            lines.append("## Session Notes")
                            lines.append("")
                            lines.append(session_notes)
                            lines.append("")
                        
                        # EXCLUDED per export spec v0.1:
                        # - State Changes & Mechanics (numeric deltas are system-facing)
                        # - Session Metadata (severity/cutoff/tags/scenario all system-facing)
                        # - Content Sources (system-facing attribution)
                        
                        markdown_content = "\n".join(lines)
                        
                        # Always provide download button
                        st.download_button(
                            label="📥 Download Session",
                            data=markdown_content,
                            file_name=Path(session_path).name,
                            mime="text/markdown",
                            use_container_width=True,
                            key="download_session"
                        )
                        
                        # Also try local write if possible
                        try:
                            path = Path(session_path)
                            path.parent.mkdir(parents=True, exist_ok=True)
                            path.write_text(markdown_content)
                            st.info(f"✓ Also saved to: {session_path}")
                        except Exception as e:
                            st.info(f"Note: Could not write to {session_path} - use download button above")
            else:
                st.info("No sessions to export yet")
    
    st.divider()
    
    # Ledger with Import button (Flow C)
    if campaign.ledger:
        ledger_col1, ledger_col2 = st.columns([10, 2])
        with ledger_col1:
            st.subheader(f"📚 Campaign Ledger ({len(campaign.ledger)} sessions)")
        with ledger_col2:
            if st.button("📥 Import", key="import_history_dashboard"):
                st.session_state.show_dashboard_history_import = True
        
        # History import for existing campaign (Flow C)
        if st.session_state.get("show_dashboard_history_import", False):
            with st.container(border=True):
                st.markdown("**Import History into Existing Campaign**")
                
                history_text = st.text_area("Paste history", height=150, key="dashboard_history_import")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("Parse"):
                        if history_text:
                            from streamlit_harness.history_parser import parse_campaign_history
                            st.session_state.dashboard_parsed = parse_campaign_history(history_text)
                with col2:
                    if st.button("Clear"):
                        st.session_state.show_dashboard_history_import = False
                        st.session_state.dashboard_parsed = None
                        st.rerun()
                
                # Show preview if parsed
                if st.session_state.get("dashboard_parsed"):
                    parsed = st.session_state.dashboard_parsed
                    
                    # Add JSON export button
                    parsed_json = json.dumps(parsed, indent=2, default=str)
                    st.download_button(
                        label="📥 Download Parsed JSON",
                        data=parsed_json,
                        file_name=f"parsed_history_merge_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        key="download_dashboard_parsed",
                    )
                    
                    # Parse preview with entity controls
                    st.markdown("**Parse Preview**")
                    for note in parsed["notes"]:
                        st.caption(note)
                    
                    with st.expander("Sessions Detected", expanded=True):
                        for session in parsed["sessions"]:
                            st.markdown(f"**Session {session['session_number']}** - {session['date']}")
                            st.caption(session['content'][:100] + "..." if len(session['content']) > 100 else session['content'])
                    
                    with st.expander("Canon Summary", expanded=True):
                        for bullet in parsed["canon_summary"]:
                            st.write(f"• {bullet}")
                    
                    # Factions with controls
                    with st.expander("Factions Detected", expanded=True):
                        if parsed["factions"]:
                            for idx, faction in enumerate(parsed["factions"]):
                                col1, col2, col3, col4, col5 = st.columns([8, 2, 2, 2, 1])
                                with col1:
                                    st.write(f"• {faction}")
                                with col2:
                                    if st.button("→Place", key=f"d_f_place_{idx}", help="Demote to Place"):
                                        _save_override_demote_from_faction(campaign_id, faction, "place")
                                        factions = list(parsed["factions"])
                                        factions.remove(faction)
                                        places = list(parsed["entities"]["places"])
                                        places.append(faction)
                                        st.session_state.dashboard_parsed["factions"] = sorted(factions)
                                        st.session_state.dashboard_parsed["entities"]["places"] = sorted(places)
                                        st.rerun()
                                with col3:
                                    if st.button("→Artifact", key=f"d_f_art_{idx}", help="Demote to Artifact"):
                                        _save_override_demote_from_faction(campaign_id, faction, "artifact")
                                        factions = list(parsed["factions"])
                                        factions.remove(faction)
                                        artifacts = list(parsed["entities"]["artifacts"])
                                        artifacts.append(faction)
                                        st.session_state.dashboard_parsed["factions"] = sorted(factions)
                                        st.session_state.dashboard_parsed["entities"]["artifacts"] = sorted(artifacts)
                                        st.rerun()
                                with col4:
                                    if st.button("→Concept", key=f"d_f_con_{idx}", help="Demote to Concept"):
                                        _save_override_demote_from_faction(campaign_id, faction, "concept")
                                        factions = list(parsed["factions"])
                                        factions.remove(faction)
                                        concepts = list(parsed["entities"]["concepts"])
                                        concepts.append(faction)
                                        st.session_state.dashboard_parsed["factions"] = sorted(factions)
                                        st.session_state.dashboard_parsed["entities"]["concepts"] = sorted(concepts)
                                        st.rerun()
                                with col5:
                                    if st.button("✕", key=f"d_f_rem_{idx}", help="Remove"):
                                        _save_override_remove(campaign_id, faction)
                                        factions = list(parsed["factions"])
                                        factions.remove(faction)
                                        st.session_state.dashboard_parsed["factions"] = sorted(factions)
                                        st.rerun()
                        else:
                            st.caption("No factions detected")
                    
                    # Show classified entities (non-factions) with controls
                    entities = parsed.get("entities", {})
                    if any(entities.values()):
                        with st.expander("Entities (Non-Factions)", expanded=False):
                            if entities.get("places"):
                                st.markdown("**Places:**")
                                for idx, place in enumerate(entities["places"]):
                                    col1, col2, col3, col4, col5 = st.columns([8, 2, 2, 2, 1])
                                    with col1:
                                        st.caption(f"• {place}")
                                    with col2:
                                        if st.button("↑Faction", key=f"d_p_fac_{idx}", help="Promote to Faction"):
                                            _save_override_promote_to_faction(campaign_id, place, "place")
                                            places = list(parsed["entities"]["places"])
                                            places.remove(place)
                                            factions = list(parsed["factions"])
                                            factions.append(place)
                                            st.session_state.dashboard_parsed["entities"]["places"] = sorted(places)
                                            st.session_state.dashboard_parsed["factions"] = sorted(factions)
                                            st.rerun()
                                    with col3:
                                        if st.button("→Artifact", key=f"d_p_art_{idx}", help="Change to Artifact"):
                                            _save_override_lateral_move(campaign_id, place, "artifact")
                                            places = list(parsed["entities"]["places"])
                                            places.remove(place)
                                            artifacts = list(parsed["entities"]["artifacts"])
                                            artifacts.append(place)
                                            st.session_state.dashboard_parsed["entities"]["places"] = sorted(places)
                                            st.session_state.dashboard_parsed["entities"]["artifacts"] = sorted(artifacts)
                                            st.rerun()
                                    with col4:
                                        if st.button("→Concept", key=f"d_p_con_{idx}", help="Change to Concept"):
                                            _save_override_lateral_move(campaign_id, place, "concept")
                                            places = list(parsed["entities"]["places"])
                                            places.remove(place)
                                            concepts = list(parsed["entities"]["concepts"])
                                            concepts.append(place)
                                            st.session_state.dashboard_parsed["entities"]["places"] = sorted(places)
                                            st.session_state.dashboard_parsed["entities"]["concepts"] = sorted(concepts)
                                            st.rerun()
                                    with col5:
                                        if st.button("✕", key=f"d_p_rem_{idx}", help="Remove"):
                                            _save_override_remove(campaign_id, place)
                                            places = list(parsed["entities"]["places"])
                                            places.remove(place)
                                            st.session_state.dashboard_parsed["entities"]["places"] = sorted(places)
                                            st.rerun()
                            if entities.get("artifacts"):
                                st.markdown("**Artifacts:**")
                                for idx, artifact in enumerate(entities["artifacts"]):
                                    col1, col2, col3, col4, col5 = st.columns([8, 2, 2, 2, 1])
                                    with col1:
                                        st.caption(f"• {artifact}")
                                    with col2:
                                        if st.button("↑Faction", key=f"d_a_fac_{idx}", help="Promote to Faction"):
                                            _save_override_promote_to_faction(campaign_id, artifact, "artifact")
                                            artifacts = list(parsed["entities"]["artifacts"])
                                            artifacts.remove(artifact)
                                            factions = list(parsed["factions"])
                                            factions.append(artifact)
                                            st.session_state.dashboard_parsed["entities"]["artifacts"] = sorted(artifacts)
                                            st.session_state.dashboard_parsed["factions"] = sorted(factions)
                                            st.rerun()
                                    with col3:
                                        if st.button("→Place", key=f"d_a_pla_{idx}", help="Change to Place"):
                                            _save_override_lateral_move(campaign_id, artifact, "place")
                                            artifacts = list(parsed["entities"]["artifacts"])
                                            artifacts.remove(artifact)
                                            places = list(parsed["entities"]["places"])
                                            places.append(artifact)
                                            st.session_state.dashboard_parsed["entities"]["artifacts"] = sorted(artifacts)
                                            st.session_state.dashboard_parsed["entities"]["places"] = sorted(places)
                                            st.rerun()
                                    with col4:
                                        if st.button("→Concept", key=f"d_a_con_{idx}", help="Change to Concept"):
                                            _save_override_lateral_move(campaign_id, artifact, "concept")
                                            artifacts = list(parsed["entities"]["artifacts"])
                                            artifacts.remove(artifact)
                                            concepts = list(parsed["entities"]["concepts"])
                                            concepts.append(artifact)
                                            st.session_state.dashboard_parsed["entities"]["artifacts"] = sorted(artifacts)
                                            st.session_state.dashboard_parsed["entities"]["concepts"] = sorted(concepts)
                                            st.rerun()
                                    with col5:
                                        if st.button("✕", key=f"d_a_rem_{idx}", help="Remove"):
                                            _save_override_remove(campaign_id, artifact)
                                            artifacts = list(parsed["entities"]["artifacts"])
                                            artifacts.remove(artifact)
                                            st.session_state.dashboard_parsed["entities"]["artifacts"] = sorted(artifacts)
                                            st.rerun()
                            if entities.get("concepts"):
                                st.markdown("**Concepts/Powers:**")
                                for idx, concept in enumerate(entities["concepts"]):
                                    col1, col2, col3, col4, col5 = st.columns([8, 2, 2, 2, 1])
                                    with col1:
                                        st.caption(f"• {concept}")
                                    with col2:
                                        if st.button("↑Faction", key=f"d_c_fac_{idx}", help="Promote to Faction"):
                                            _save_override_promote_to_faction(campaign_id, concept, "concept")
                                            concepts = list(parsed["entities"]["concepts"])
                                            concepts.remove(concept)
                                            factions = list(parsed["factions"])
                                            factions.append(concept)
                                            st.session_state.dashboard_parsed["entities"]["concepts"] = sorted(concepts)
                                            st.session_state.dashboard_parsed["factions"] = sorted(factions)
                                            st.rerun()
                                    with col3:
                                        if st.button("→Place", key=f"d_c_pla_{idx}", help="Change to Place"):
                                            _save_override_lateral_move(campaign_id, concept, "place")
                                            concepts = list(parsed["entities"]["concepts"])
                                            concepts.remove(concept)
                                            places = list(parsed["entities"]["places"])
                                            places.append(concept)
                                            st.session_state.dashboard_parsed["entities"]["concepts"] = sorted(concepts)
                                            st.session_state.dashboard_parsed["entities"]["places"] = sorted(places)
                                            st.rerun()
                                    with col4:
                                        if st.button("→Artifact", key=f"d_c_art_{idx}", help="Change to Artifact"):
                                            _save_override_lateral_move(campaign_id, concept, "artifact")
                                            concepts = list(parsed["entities"]["concepts"])
                                            concepts.remove(concept)
                                            artifacts = list(parsed["entities"]["artifacts"])
                                            artifacts.append(concept)
                                            st.session_state.dashboard_parsed["entities"]["concepts"] = sorted(concepts)
                                            st.session_state.dashboard_parsed["entities"]["artifacts"] = sorted(artifacts)
                                            st.rerun()
                                    with col5:
                                        if st.button("✕", key=f"d_c_rem_{idx}", help="Remove"):
                                            _save_override_remove(campaign_id, concept)
                                            concepts = list(parsed["entities"]["concepts"])
                                            concepts.remove(concept)
                                            st.session_state.dashboard_parsed["entities"]["concepts"] = sorted(concepts)
                                            st.rerun()
                    
                    # Show future sessions (not imported)
                    future = parsed.get("future_sessions", [])
                    if future:
                        with st.expander("Future Sessions (Not Imported)", expanded=False):
                            for session in future:
                                st.markdown(f"**{session['title']}**")
                                st.caption(session['notes'][:100] + "..." if len(session['notes']) > 100 else session['notes'])
                    
                    # Show open threads (not imported)
                    threads = parsed.get("open_threads", [])
                    if threads:
                        with st.expander("Open Threads (Not Imported)", expanded=False):
                            for thread in threads:
                                st.caption(f"• {thread[:150]}..." if len(thread) > 150 else f"• {thread}")
                    
                    with col3:
                        if st.button("Merge", type="primary"):
                            # Merge into existing campaign
                            # FIX 1: Skip invalid sessions (null session_number AND empty content)
                            for session in parsed["sessions"]:
                                # Validate session has meaningful content
                                content = session.get("content", "").strip()
                                session_num = session.get("session_number")
                                
                                # Skip if both null session_number AND empty/whitespace-only content
                                if session_num is None and not content:
                                    continue
                                
                                # Only add valid sessions with non-empty content
                                if content:
                                    campaign.ledger.append({
                                        "session_number": len(campaign.ledger) + 1,
                                        "session_date": session["date"],
                                        "what_happened": [content[:200]],
                                        "deltas": {"pressure_change": 0, "heat_change": 0},
                                    })
                            
                            # Append canon bullets
                            campaign.canon_summary.extend(parsed["canon_summary"])
                            
                            # Add factions if not present
                            if campaign.campaign_state:
                                new_factions = dict(campaign.campaign_state.factions)
                                for f_name in parsed["factions"]:
                                    fid = f_name.lower().replace(" ", "_")
                                    if fid not in new_factions:
                                        new_factions[fid] = FactionState(
                                            faction_id=fid,
                                            name=f_name,
                                            description="",
                                            attention=0,
                                            disposition=0,
                                            notes=None,
                                            is_active=True,
                                        )
                                
                                campaign.campaign_state = CampaignState(
                                    version="0.2",
                                    campaign_pressure=campaign.campaign_state.campaign_pressure,
                                    heat=campaign.campaign_state.heat,
                                    scars=campaign.campaign_state.scars,
                                    factions=new_factions,
                                    total_scenes_run=campaign.campaign_state.total_scenes_run + len(parsed["sessions"]),
                                    total_cutoffs_seen=campaign.campaign_state.total_cutoffs_seen,
                                    highest_severity_seen=campaign.campaign_state.highest_severity_seen,
                                    _legacy_scars=campaign.campaign_state._legacy_scars,
                                )
                            
                            campaign.save()
                            st.session_state.show_dashboard_history_import = False
                            st.session_state.dashboard_parsed = None
                            st.success("History merged into campaign!")
                            st.rerun()
        
        with st.expander(f"Existing Ledger Entries", expanded=False):
            for entry in reversed(campaign.ledger):  # Newest first
                session_date_str = entry.get('session_date', '')[:10] if entry.get('session_date') else ''
                st.markdown(f"**Session {entry.get('session_number', '?')}** — {session_date_str}")
                
                if entry.get("what_happened"):
                    what_happened = entry["what_happened"]
                    
                    # Show first 3 bullets inline
                    for bullet in what_happened[:3]:
                        st.caption(f"• {bullet}")
                    
                    # Show remaining bullets in nested expander if >3
                    if len(what_happened) > 3:
                        with st.expander(f"+ {len(what_happened) - 3} more", expanded=False):
                            for bullet in what_happened[3:]:
                                st.caption(f"• {bullet}")
                
                # Session notes if present
                if entry.get("session_notes"):
                    st.caption(f"_Notes: {entry['session_notes'][:100]}{'...' if len(entry['session_notes']) > 100 else ''}_")
                
                # Metadata summary if present
                if entry.get("metadata"):
                    metadata = entry["metadata"]
                    meta_parts = []
                    if "severity_avg" in metadata:
                        meta_parts.append(f"Sev: {metadata['severity_avg']:.1f}")
                    if "top_tags" in metadata and metadata["top_tags"]:
                        meta_parts.append(f"Tags: {', '.join(metadata['top_tags'][:2])}")
                    if meta_parts:
                        st.caption(f"📊 {' | '.join(meta_parts)}")
                
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
    
    # Set campaign context for Event Generator
    if campaign.campaign_state:
        from streamlit_harness.campaign_context import ContextBundle, set_campaign_context
        context = ContextBundle.from_campaign(
            campaign_id=campaign.campaign_id,
            campaign_name=campaign.name,
            campaign_state=campaign.campaign_state,
            sources=campaign.sources,
        )
        set_campaign_context(context)
    
    # Header
    col1, col2 = st.columns([1, 11])
    with col1:
        if st.button("← Back"):
            st.session_state.campaign_page = "dashboard"
            st.rerun()
    with col2:
        st.title(f"🎮 Session Workspace: {campaign.name}")
    
    st.info("🔧 Campaign context applied! Switch to Event Generator mode to run scenarios with campaign tags/factions pre-filled.")
    
    # Primary actions
    col_finalize, col_manual = st.columns(2)
    with col_finalize:
        if st.button("✅ Finalize Session", type="primary", use_container_width=True):
            st.session_state.campaign_page = "finalize"
            st.rerun()
    with col_manual:
        if st.button("➕ Add Manual Entry", use_container_width=True):
            st.session_state.show_manual_entry_form = True
    
    st.divider()
    
    # Initialize manual entries in session state
    if "manual_entries" not in st.session_state:
        st.session_state.manual_entries = []
    
    # Manual Entry Form (inline)
    if st.session_state.get("show_manual_entry_form", False):
        with st.container(border=True):
            st.subheader("📝 Manual Entry")
            st.caption("Record improvised events without using the generator")
            
            with st.form("manual_entry_form"):
                # Required fields
                entry_title = st.text_input("Title / Label*", placeholder="e.g., Unexpected Ambush")
                entry_description = st.text_area(
                    "Description / Summary*",
                    placeholder="What happened...",
                    height=100
                )
                
                # Optional fields (collapsed)
                with st.expander("Optional Details", expanded=False):
                    # Tags
                    entry_tags = st.text_input(
                        "Tags (comma-separated)",
                        placeholder="e.g., combat, social, mystery"
                    )
                    
                    # Related factions
                    if campaign.campaign_state and campaign.campaign_state.factions:
                        faction_options = list(campaign.campaign_state.factions.keys())
                        entry_factions = st.multiselect(
                            "Related Factions",
                            faction_options
                        )
                    else:
                        entry_factions = []
                    
                    # Related scars
                    if campaign.campaign_state and campaign.campaign_state.scars:
                        scar_options = [s.scar_id for s in campaign.campaign_state.scars]
                        entry_scars = st.multiselect(
                            "Related Scars",
                            scar_options
                        )
                    else:
                        entry_scars = []
                    
                    # Severity
                    entry_severity = st.number_input(
                        "Severity (1-10, optional)",
                        min_value=0,
                        max_value=10,
                        value=0,
                        help="0 = not applicable"
                    )
                    
                    # Additional notes
                    entry_notes = st.text_area(
                        "Additional Notes",
                        placeholder="Context, player reactions, GM thoughts...",
                        height=80
                    )
                
                # Optional state impact (advanced, collapsed)
                with st.expander("State Impact (Advanced)", expanded=False):
                    entry_pressure_delta = st.number_input(
                        "Pressure Delta",
                        min_value=-5,
                        max_value=5,
                        value=0
                    )
                    entry_heat_delta = st.number_input(
                        "Heat Delta",
                        min_value=-5,
                        max_value=5,
                        value=0
                    )
                
                # Form buttons
                col_save, col_cancel = st.columns(2)
                with col_save:
                    save = st.form_submit_button("💾 Save Entry", type="primary", use_container_width=True)
                with col_cancel:
                    cancel = st.form_submit_button("Cancel", use_container_width=True)
                
                if save:
                    if not entry_title or not entry_description:
                        st.error("Title and Description are required")
                        st.stop()
                    
                    # Create manual entry
                    manual_entry = {
                        "entry_id": f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S%f')}",
                        "title": entry_title,
                        "description": entry_description,
                        "tags": [t.strip() for t in entry_tags.split(",") if t.strip()] if entry_tags else [],
                        "related_factions": entry_factions,
                        "related_scars": entry_scars,
                        "severity": entry_severity if entry_severity > 0 else None,
                        "notes": entry_notes if entry_notes.strip() else None,
                        "pressure_delta": entry_pressure_delta if entry_pressure_delta != 0 else None,
                        "heat_delta": entry_heat_delta if entry_heat_delta != 0 else None,
                        "created_at": datetime.now().isoformat(),
                    }
                    
                    # Add to session manual entries
                    st.session_state.manual_entries.append(manual_entry)
                    st.session_state.show_manual_entry_form = False
                    st.success(f"✓ Manual entry saved: {entry_title}")
                    st.rerun()
                
                if cancel:
                    st.session_state.show_manual_entry_form = False
                    st.rerun()
    
    # Show saved manual entries
    if st.session_state.manual_entries:
        st.subheader(f"📋 Manual Entries ({len(st.session_state.manual_entries)})")
        st.caption("These will be included when you finalize the session")
        
        for idx, entry in enumerate(st.session_state.manual_entries):
            with st.container(border=True):
                col1, col2 = st.columns([10, 2])
                
                with col1:
                    st.markdown(f"**{entry['title']}**")
                    st.caption(entry['description'][:150] + "..." if len(entry['description']) > 150 else entry['description'])
                    
                    # Show tags if present
                    if entry.get('tags'):
                        st.caption(f"🏷️ {', '.join(entry['tags'])}")
                    
                    # Show state deltas if present
                    delta_parts = []
                    if entry.get('pressure_delta'):
                        delta_parts.append(f"Pressure: {entry['pressure_delta']:+d}")
                    if entry.get('heat_delta'):
                        delta_parts.append(f"Heat: {entry['heat_delta']:+d}")
                    if delta_parts:
                        st.caption(f"📊 {' | '.join(delta_parts)}")
                
                with col2:
                    if st.button("🗑️", key=f"delete_manual_{idx}", help="Delete entry"):
                        st.session_state.manual_entries.pop(idx)
                        st.rerun()
        
        # Add another entry button
        if st.button("➕ Add Another Entry"):
            st.session_state.show_manual_entry_form = True
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
    
    # Check for session packet (Flow B: Generator → Campaign or Prep → Canon)
    session_packet = st.session_state.get("pending_session_packet")
    
    # Show prep item badge if using prep items
    if "prep_items_to_archive" in st.session_state:
        prep_count = len(st.session_state.prep_items_to_archive)
        st.info(f"🎴 Using {prep_count} prep item{'s' if prep_count != 1 else ''} from Prep Queue")
    
    if session_packet:
        st.info(f"📊 Session data loaded from: {session_packet.scenario_name}")
        with st.expander("Session Statistics", expanded=False):
            st.write(f"**Severity Avg**: {session_packet.severity_avg:.2f}")
            st.write(f"**Cutoff Rate**: {session_packet.cutoff_rate*100:.1f}%")
            st.write(f"**Top Tags**: {', '.join([tag for tag, _ in session_packet.top_tags[:5]])}")
    
    # B: Suggestions panel - actionable optional commit helpers with checkboxes
    # Only show if we have actionable suggestions (not just info notes)
    actionable_suggestions = []
    if session_packet and session_packet.suggested_faction_updates:
        for faction_id, change in session_packet.suggested_faction_updates.items():
            actionable_suggestions.append(f"Consider updating faction '{faction_id}': {change}")
    if session_packet and session_packet.candidate_scars:
        for scar in session_packet.candidate_scars:
            actionable_suggestions.append(f"Consider adding scar: {scar}")
    
    # B: MUST hide panel if zero actionable items (no empty panels)
    if actionable_suggestions:
        with st.expander("💡 Suggestions (Optional)", expanded=False):
            st.caption("Optional actionable commit helpers - commit works without checking these")
            
            for idx, suggestion in enumerate(actionable_suggestions):
                # Initialize checkbox state
                checkbox_key = f"suggestion_check_{idx}"
                if checkbox_key not in st.session_state:
                    st.session_state[checkbox_key] = False
                
                st.checkbox(suggestion, key=checkbox_key)
    
    with st.form("finalize_session_form"):
        st.subheader("What Happened?")
        
        # Initialize entry list in session state if needed
        if "finalize_entries" not in st.session_state:
            entries_list = []
            
            # Pre-fill from happened_items if packet exists (dynamic N-item list)
            if session_packet and session_packet.happened_items:
                entries_list = list(session_packet.happened_items)
            
            # Add manual entries to list
            if "manual_entries" in st.session_state and st.session_state.manual_entries:
                for entry in st.session_state.manual_entries:
                    entries_list.append(entry["title"])
            
            # Default to 3 empty if nothing
            if not entries_list:
                entries_list = ["", "", ""]
            
            st.session_state.finalize_entries = entries_list
        
        entries = st.session_state.finalize_entries
        
        # Cap visible at 5 by default with toggle
        if "show_all_entries" not in st.session_state:
            st.session_state.show_all_entries = len(entries) <= 5
        
        visible_count = len(entries) if st.session_state.show_all_entries else min(5, len(entries))
        
        # Render visible entry inputs (dynamic N-item list)
        entry_values = []
        for idx in range(visible_count):
            value = entries[idx] if idx < len(entries) else ""
            entry_input = st.text_input(
                f"Entry {idx+1}",
                value=value,
                placeholder="Event or outcome...",
                key=f"finalize_entry_{idx}"
            )
            entry_values.append(entry_input)
        
        # Show toggle if there are hidden entries
        if len(entries) > 5 and not st.session_state.show_all_entries:
            if st.form_submit_button(f"Show all {len(entries)} entries"):
                st.session_state.show_all_entries = True
                st.rerun()
        elif len(entries) > 5 and st.session_state.show_all_entries:
            if st.form_submit_button("Show first 5 only"):
                st.session_state.show_all_entries = False
                st.rerun()
        
        # Add/remove entry buttons
        col_add, col_remove = st.columns(2)
        with col_add:
            add_entry = st.form_submit_button("➕ Add Entry")
        with col_remove:
            remove_entry = st.form_submit_button("➖ Remove Last", disabled=(len(entries) <= 1))
        
        # Handle add/remove
        if add_entry:
            st.session_state.finalize_entries.append("")
            st.rerun()
        if remove_entry and len(entries) > 1:
            st.session_state.finalize_entries.pop()
            st.rerun()
        
        # Optional session notes
        st.subheader("Session Notes (Optional)")
        session_notes = st.text_area(
            "Notes",
            placeholder="Optional freeform notes: context, GM thoughts, player reactions, etc.",
            height=100,
            help="Optional notes about this session"
        )
        
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
        
        st.subheader("State Changes")
        
        # Pre-fill from packet if available, or aggregate from manual entries
        default_pressure = session_packet.suggested_pressure_delta if session_packet else 0
        default_heat = session_packet.suggested_heat_delta if session_packet else 0
        
        # Add manual entry deltas
        if "manual_entries" in st.session_state and st.session_state.manual_entries:
            for entry in st.session_state.manual_entries:
                if entry.get('pressure_delta'):
                    default_pressure += entry['pressure_delta']
                if entry.get('heat_delta'):
                    default_heat += entry['heat_delta']
        
        col1, col2 = st.columns(2)
        with col1:
            pressure_change = st.number_input("Pressure change", min_value=-10, max_value=10, value=default_pressure, step=1)
        with col2:
            heat_change = st.number_input("Heat change", min_value=-10, max_value=10, value=default_heat, step=1)
        
        # C: Canon Summary update with user-editable synthesis
        st.subheader("Canon Summary")
        
        # Generate suggested canon bullet (deterministic synthesis)
        suggested_canon = ""
        if campaign.campaign_state:
            # Check for faction changes
            faction_changed = False
            faction_desc = ""
            if faction_attention and 'affected_faction' in locals() and affected_faction:
                if affected_faction in campaign.campaign_state.factions:
                    faction = campaign.campaign_state.factions[affected_faction]
                    # Synthesize state description
                    new_att = min(20, faction.attention + 2)
                    att_band = FactionState(faction_id='temp', name='temp', attention=new_att).get_attention_band().lower()
                    disp_val = faction.disposition
                    if disp_val <= -1:
                        disp_desc = "openly hostile" if disp_val == -2 else "unfriendly"
                    elif disp_val >= 1:
                        disp_desc = "allied" if disp_val == 2 else "friendly"
                    else:
                        disp_desc = "neutral"
                    faction_desc = f"The {faction.name} are now {att_band} and {disp_desc}."
                    faction_changed = True
            
            # Check for scars or resource changes
            scar_added = add_scar and scar_id
            
            if faction_changed:
                suggested_canon = faction_desc
            elif scar_added:
                # Synthesize from scar
                if scar_category == "resource":
                    suggested_canon = f"Resources have become strained: {scar_id.replace('_', ' ')}."
                elif scar_category == "reputation":
                    suggested_canon = f"The patrol's reputation has shifted: {scar_id.replace('_', ' ')}."
                else:
                    suggested_canon = f"A lasting change: {scar_id.replace('_', ' ')}."
            # Else leave blank (force GM to write or skip)
        
        # Show editable canon bullet field
        canon_bullet = st.text_input(
            "Canon bullet (optional - edit or leave blank)",
            value=suggested_canon,
            placeholder="e.g., The Road Dogs now openly hunt patrol vehicles...",
            help="Curated world-state statement (not event recap). Leave blank to skip."
        )
        
        col1, col2 = st.columns(2)
        with col1:
            commit = st.form_submit_button("💾 Commit Session", type="primary", use_container_width=True)
        with col2:
            cancel = st.form_submit_button("Cancel", use_container_width=True)
        
        if commit:
            # CRITICAL: Collect entries from FULL list, not just visible ones
            # Update visible entries from form inputs
            for idx in range(visible_count):
                entry_key = f"finalize_entry_{idx}"
                if entry_key in st.session_state:
                    entry_text = st.session_state[entry_key]
                    if idx < len(entries):
                        entries[idx] = entry_text
            
            # Build what_happened from full entry list (visible + hidden)
            what_happened = [e.strip() for e in entries if e.strip()]
            
            if not what_happened:
                st.error("Please enter at least one entry")
                st.stop()
            
            # Record active sources in session metadata
            active_source_ids = [s.source_id for s in campaign.sources if s.enabled]
            active_source_names = [s.name for s in campaign.sources if s.enabled]
            
            # Build metadata from session packet if available
            metadata = {}
            if session_packet:
                metadata = {
                    "severity_avg": session_packet.severity_avg,
                    "cutoff_rate": session_packet.cutoff_rate,
                    "top_tags": [tag for tag, _ in session_packet.top_tags[:5]],
                    "scenario_name": session_packet.scenario_name,
                }
            
            # Add prep item IDs if from prep queue
            if "prep_items_to_archive" in st.session_state:
                metadata["prep_item_ids"] = st.session_state.prep_items_to_archive
            
            # Store manual entries with full rich data
            manual_entries_data = None
            if "manual_entries" in st.session_state and st.session_state.manual_entries:
                manual_entries_data = st.session_state.manual_entries
            
            # Generate unique session_id (timestamp-based primary key)
            session_timestamp = datetime.now()
            session_id = f"session_{session_timestamp.strftime('%Y%m%d_%H%M%S')}"
            
            session_entry = {
                "session_id": session_id,  # Unique stable identifier
                "session_number": len(campaign.ledger) + 1,  # Human-friendly label
                "session_date": session_timestamp.isoformat(),
                "what_happened": what_happened,  # Full N-item list preserved
                "session_notes": session_notes if session_notes.strip() else None,
                "manual_entries": manual_entries_data,  # Rich manual entry data
                "metadata": metadata if metadata else None,
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
                            name=old_faction.name,
                            description=old_faction.description,
                            attention=min(20, old_faction.attention + 2),
                            disposition=old_faction.disposition,
                            notes=old_faction.notes,
                            is_active=old_faction.is_active,
                        )
                
                # Update peak severity from session metadata if available
                new_peak_severity = cs.highest_severity_seen
                if metadata and "severity_avg" in metadata:
                    # Update peak if session average exceeds current peak
                    if metadata["severity_avg"] > new_peak_severity:
                        new_peak_severity = int(metadata["severity_avg"])
                
                # Create new state
                campaign.campaign_state = CampaignState(
                    version="0.2",
                    campaign_pressure=new_pressure,
                    heat=new_heat,
                    scars=new_scars,
                    factions=new_factions,
                    total_scenes_run=cs.total_scenes_run + 1,
                    total_cutoffs_seen=cs.total_cutoffs_seen,
                    highest_severity_seen=new_peak_severity,
                    _legacy_scars=cs._legacy_scars,
                )
            
            # C: Canon Summary update - add user-edited bullet if provided
            if canon_bullet and canon_bullet.strip():
                campaign.canon_summary.append(canon_bullet.strip())
            
            # Add to ledger
            campaign.ledger.append(session_entry)
            campaign.last_played = datetime.now().isoformat()
            
            # Archive prep items that were used (if from prep queue)
            if "prep_items_to_archive" in st.session_state:
                items_to_archive = st.session_state.prep_items_to_archive
                for item in campaign.prep_queue:
                    if item.item_id in items_to_archive:
                        item.status = "archived"
                # Clear checkbox states for archived items
                for item_id in items_to_archive:
                    checkbox_key = f"prep_select_{item_id}"
                    if checkbox_key in st.session_state:
                        del st.session_state[checkbox_key]
                del st.session_state.prep_items_to_archive
            
            # Save
            campaign.save()
            
            # Clear session state after commit
            if "pending_session_packet" in st.session_state:
                del st.session_state.pending_session_packet
            if "finalize_entries" in st.session_state:
                del st.session_state.finalize_entries
            if "show_all_entries" in st.session_state:
                del st.session_state.show_all_entries
            if "manual_entries" in st.session_state:
                del st.session_state.manual_entries
            
            st.success("Session finalized!")
            st.session_state.campaign_page = "dashboard"
            st.rerun()
        
        if cancel:
            # Clear session state on cancel
            if "finalize_entries" in st.session_state:
                del st.session_state.finalize_entries
            if "show_all_entries" in st.session_state:
                del st.session_state.show_all_entries
            if "manual_entries" in st.session_state:
                del st.session_state.manual_entries
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
