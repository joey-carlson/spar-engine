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
                    # Find and update item
                    for i, p in enumerate(campaign.prep_queue):
                        if p.item_id == item.item_id:
                            campaign.prep_queue[i].status = "queued"
                            break
                    campaign.save()
                    st.rerun()
            else:
                if st.button("📌", key=f"pin_{item.item_id}", help="Pin"):
                    # Find and update item
                    for i, p in enumerate(campaign.prep_queue):
                        if p.item_id == item.item_id:
                            campaign.prep_queue[i].status = "pinned"
                            break
                    campaign.save()
                    st.rerun()
            
            if show_unarchive:
                if st.button("↩️", key=f"unarchive_{item.item_id}", help="Unarchive"):
                    for i, p in enumerate(campaign.prep_queue):
                        if p.item_id == item.item_id:
                            campaign.prep_queue[i].status = "queued"
                            break
                    campaign.save()
                    st.rerun()
            else:
                if st.button("📦", key=f"archive_{item.item_id}", help="Archive"):
                    for i, p in enumerate(campaign.prep_queue):
                        if p.item_id == item.item_id:
                            campaign.prep_queue[i].status = "archived"
                            break
                    campaign.save()
                    st.rerun()
            
            if st.button("🗑️", key=f"delete_{item.item_id}", help="Delete"):
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
                            attention=0,
                            disposition=0,
                            notes=f_name,
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
                    ledger = []
                    for session in parsed["sessions"]:
                        ledger.append({
                            "session_number": session["session_number"],
                            "session_date": session["date"],
                            "what_happened": [session["content"][:200]],  # Truncate
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
    
    st.divider()
    
    # Prep Queue (Non-Canon) with Selection
    queued_items = [p for p in campaign.prep_queue if p.status == "queued"]
    pinned_items = [p for p in campaign.prep_queue if p.status == "pinned"]
    archived_items = [p for p in campaign.prep_queue if p.status == "archived"]
    active_count = len(queued_items) + len(pinned_items)
    
    with st.expander(f"🎴 Prep Queue ({active_count}) — Not Yet Canon", expanded=False):
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
                    if st.button(
                        f"📝 Create Session Draft from Selected ({selected_prep_count})",
                        disabled=(selected_prep_count == 0),
                        type="primary" if selected_prep_count > 0 else "secondary",
                        use_container_width=True,
                        key="create_session_from_prep"
                    ):
                        # Create session packet from selected prep items
                        from streamlit_harness.session_packet import SessionPacket
                        
                        selected_items = [
                            item for item in active_items
                            if st.session_state.get(f"prep_select_{item.item_id}", False)
                        ]
                        
                        # Build packet from selected prep items
                        what_happened_bullets = [f"{item.title}" for item in selected_items[:3]]
                        
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
                        
                        # Create packet
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
                            notes=[
                                f"Session draft created from {len(selected_items)} prep items",
                                "Review and edit 'What Happened' bullets before committing"
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
                            for session in parsed["sessions"]:
                                campaign.ledger.append({
                                    "session_number": len(campaign.ledger) + 1,
                                    "session_date": session["date"],
                                    "what_happened": [session["content"][:200]],
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
                                        new_factions[fid] = FactionState(fid, 0, 0, f_name)
                                
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
            
            if session_packet.notes:
                st.markdown("**Suggestions:**")
                for note in session_packet.notes:
                    st.caption(f"• {note}")
    
    with st.form("finalize_session_form"):
        st.subheader("What Happened?")
        
        # Pre-fill from top events if packet exists
        default_bullets = ["", "", ""]
        if session_packet and session_packet.top_events:
            for idx, event in enumerate(session_packet.top_events[:3]):
                default_bullets[idx] = event.get("title", "")
        
        bullet1 = st.text_input("Bullet 1", value=default_bullets[0], placeholder="Key event or outcome...")
        bullet2 = st.text_input("Bullet 2", value=default_bullets[1], placeholder="Another development...")
        bullet3 = st.text_input("Bullet 3", value=default_bullets[2], placeholder="Third notable thing...")
        
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
        
        # Pre-fill from packet if available
        default_pressure = session_packet.suggested_pressure_delta if session_packet else 0
        default_heat = session_packet.suggested_heat_delta if session_packet else 0
        
        col1, col2 = st.columns(2)
        with col1:
            pressure_change = st.number_input("Pressure change", min_value=-10, max_value=10, value=default_pressure, step=1)
        with col2:
            heat_change = st.number_input("Heat change", min_value=-10, max_value=10, value=default_heat, step=1)
        
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
            
            # Clear session packet after commit
            if "pending_session_packet" in st.session_state:
                del st.session_state.pending_session_packet
            
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
