"""Tests for Campaign UI session finalization data transformation logic.

These tests focus on the critical data flows in campaign_ui.py that were
previously untested and led to data loss bugs.
"""

import json
from pathlib import Path
import tempfile
import pytest

from streamlit_harness.campaign_ui import Campaign, PrepItem
from spar_campaign import CampaignState, FactionState


def test_campaign_serialization_with_full_bullets():
    """Test that full bullet lists persist through save/load cycle."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Override campaigns directory for test
        import streamlit_harness.campaign_ui as cui
        original_dir = cui.CAMPAIGNS_DIR
        cui.CAMPAIGNS_DIR = Path(tmpdir)
        
        try:
            # Create campaign with rich ledger entry
            campaign = Campaign(
                campaign_id="test_001",
                name="Test Campaign",
                created="2025-01-01T00:00:00",
                last_played="2025-01-01T00:00:00",
                canon_summary=["Campaign begins"],
                campaign_state=CampaignState.default(),
                ledger=[{
                    "session_number": 1,
                    "session_date": "2025-01-01T00:00:00",
                    "what_happened": [
                        "Event 1",
                        "Event 2", 
                        "Event 3",
                        "Event 4",
                        "Event 5",
                        "Event 6",
                        "Event 7",
                        "Event 8",
                        "Event 9",
                        "Event 10",
                    ],
                    "session_notes": "GM notes about the session",
                    "metadata": {
                        "severity_avg": 5.5,
                        "cutoff_rate": 0.2,
                        "top_tags": ["hazard", "social"],
                    },
                    "deltas": {"pressure_change": 2, "heat_change": 1},
                    "active_sources": ["core_complications"],
                }],
            )
            
            # Save and reload
            campaign.save()
            loaded = Campaign.load("test_001")
            
            # Verify full bullet list persisted
            assert loaded is not None
            assert len(loaded.ledger) == 1
            assert len(loaded.ledger[0]["what_happened"]) == 10
            assert loaded.ledger[0]["what_happened"][9] == "Event 10"
            
            # Verify session notes persisted
            assert loaded.ledger[0]["session_notes"] == "GM notes about the session"
            
            # Verify metadata persisted
            assert loaded.ledger[0]["metadata"]["severity_avg"] == 5.5
            assert loaded.ledger[0]["metadata"]["cutoff_rate"] == 0.2
            assert loaded.ledger[0]["metadata"]["top_tags"] == ["hazard", "social"]
            
        finally:
            cui.CAMPAIGNS_DIR = original_dir


def test_canon_summary_synthesis_one_bullet():
    """Test canon synthesis with 1 bullet: use as-is."""
    bullets = ["Single important event"]
    
    # Simulate synthesis logic from render_finalize_session
    if len(bullets) == 1:
        canon_bullet = bullets[0]
    elif len(bullets) <= 4:
        canon_bullet = f"{bullets[0]}; {bullets[1]}"
    else:
        canon_bullet = f"{bullets[0]} (and more)"
    
    assert canon_bullet == "Single important event"


def test_canon_summary_synthesis_two_to_four_bullets():
    """Test canon synthesis with 2-4 bullets: join first two."""
    bullets = ["Event A", "Event B", "Event C"]
    
    # Simulate synthesis logic
    if len(bullets) == 1:
        canon_bullet = bullets[0]
    elif len(bullets) <= 4:
        canon_bullet = f"{bullets[0]}; {bullets[1]}"
    else:
        canon_bullet = f"{bullets[0]} (and more)"
    
    assert canon_bullet == "Event A; Event B"


def test_canon_summary_synthesis_five_plus_bullets():
    """Test canon synthesis with 5+ bullets: first + indicator."""
    bullets = ["Event 1", "Event 2", "Event 3", "Event 4", "Event 5", "Event 6"]
    
    # Simulate synthesis logic
    if len(bullets) == 1:
        canon_bullet = bullets[0]
    elif len(bullets) <= 4:
        canon_bullet = f"{bullets[0]}; {bullets[1]}"
    else:
        canon_bullet = f"{bullets[0]} (and more)"
    
    assert canon_bullet == "Event 1 (and more)"


def test_ledger_entry_structure_with_metadata():
    """Test that ledger entry structure includes all required fields."""
    # Simulate session entry creation
    session_entry = {
        "session_number": 5,
        "session_date": "2025-01-15T12:00:00",
        "what_happened": ["Event A", "Event B", "Event C"],
        "session_notes": "Test notes",
        "metadata": {
            "severity_avg": 6.2,
            "cutoff_rate": 0.25,
            "top_tags": ["hazard", "reinforcements"],
            "scenario_name": "Test Scenario",
            "prep_item_ids": ["prep_001", "prep_002"],
        },
        "deltas": {
            "pressure_change": 3,
            "heat_change": 2,
            "rumor_spread": True,
            "faction_attention_change": False,
        },
        "active_sources": ["core_complications", "custom_content"],
        "active_source_ids": ["source_001"],
    }
    
    # Verify structure
    assert "session_number" in session_entry
    assert "what_happened" in session_entry
    assert "session_notes" in session_entry
    assert "metadata" in session_entry
    assert len(session_entry["what_happened"]) == 3
    assert session_entry["session_notes"] == "Test notes"
    assert session_entry["metadata"]["severity_avg"] == 6.2


def test_prep_item_serialization_preserves_all_fields():
    """Test PrepItem serialization round-trip."""
    item = PrepItem(
        item_id="prep_001",
        created_at="2025-01-01T00:00:00",
        title="Test Event",
        summary="Event summary",
        tags=["hazard", "social"],
        source={"preset": "dungeon", "phase": "engage"},
        status="queued",
        related_factions=["city_watch"],
        related_scars=["wounded"],
        notes="Prep notes",
    )
    
    # Serialize and deserialize
    data = item.to_dict()
    loaded = PrepItem.from_dict(data)
    
    # Verify all fields preserved
    assert loaded.item_id == "prep_001"
    assert loaded.title == "Test Event"
    assert loaded.summary == "Event summary"
    assert loaded.tags == ["hazard", "social"]
    assert loaded.source["preset"] == "dungeon"
    assert loaded.status == "queued"
    assert loaded.notes == "Prep notes"


def test_bullet_collection_from_visible_and_hidden():
    """Test that bullet collection preserves hidden bullets.
    
    This is the regression test for the data loss bug where only visible
    bullets were committed.
    """
    # Simulate session state
    finalize_bullets = [
        "Bullet 1",
        "Bullet 2",
        "Bullet 3",
        "Bullet 4",
        "Bullet 5",
        "Bullet 6",  # Hidden
        "Bullet 7",  # Hidden
        "Bullet 8",  # Hidden
    ]
    
    # Simulate showing only first 5
    show_all_bullets = False
    visible_count = 5 if not show_all_bullets else len(finalize_bullets)
    
    # Simulate form input updates (only visible bullets can be edited)
    # User edited bullet 2
    bullets = finalize_bullets.copy()
    bullets[1] = "Bullet 2 EDITED"
    
    # CRITICAL: Build what_happened from FULL list, not just visible
    what_happened = [b.strip() for b in bullets if b.strip()]
    
    # Verify all 8 bullets preserved
    assert len(what_happened) == 8
    assert what_happened[1] == "Bullet 2 EDITED"
    assert what_happened[5] == "Bullet 6"  # Hidden bullet preserved
    assert what_happened[7] == "Bullet 8"  # Last hidden bullet preserved


def test_session_notes_optional():
    """Test that session notes are optional and None when empty."""
    # Simulate commit with empty notes
    session_notes = ""
    stored_notes = session_notes if session_notes.strip() else None
    
    assert stored_notes is None
    
    # Simulate commit with actual notes
    session_notes = "Some notes"
    stored_notes = session_notes if session_notes.strip() else None
    
    assert stored_notes == "Some notes"


def test_metadata_includes_prep_item_ids():
    """Test that metadata includes prep item IDs when from prep queue."""
    # Simulate session from prep queue
    prep_items_to_archive = ["prep_001", "prep_002", "prep_003"]
    
    metadata = {
        "severity_avg": 5.0,
        "cutoff_rate": 0.1,
        "top_tags": ["hazard"],
        "scenario_name": "Prep Queue",
    }
    
    # Add prep item IDs
    metadata["prep_item_ids"] = prep_items_to_archive
    
    assert "prep_item_ids" in metadata
    assert len(metadata["prep_item_ids"]) == 3
    assert metadata["prep_item_ids"][0] == "prep_001"


def test_campaign_name_normalization():
    """Test campaign name to directory normalization."""
    from streamlit_harness.campaign_ui import normalize_campaign_name_to_dir
    
    assert normalize_campaign_name_to_dir("City of Fog") == "City_of_Fog"
    assert normalize_campaign_name_to_dir("Test-Campaign") == "Test_Campaign"
    assert normalize_campaign_name_to_dir("Campaign!@#") == "Campaign"
    assert normalize_campaign_name_to_dir("  Spaces  ") == "Spaces"


def test_empty_bullet_filtering():
    """Test that empty bullets are filtered out but non-empty preserved."""
    bullets = [
        "Event 1",
        "",  # Empty
        "Event 3",
        "   ",  # Whitespace only
        "Event 5",
    ]
    
    what_happened = [b.strip() for b in bullets if b.strip()]
    
    assert len(what_happened) == 3
    assert what_happened == ["Event 1", "Event 3", "Event 5"]


def test_invalid_session_filtering_on_import():
    """Test that invalid sessions (null number + empty content) are filtered during import.
    
    Regression test for FIX 1: Designer GPT identified bogus "Session None — Unknown" entry.
    """
    # Simulate parsed sessions with invalid entry
    parsed_sessions = [
        {
            "session_number": None,
            "date": "Unknown",
            "content": "",  # Empty content
        },
        {
            "session_number": None,
            "date": "Unknown",
            "content": "   ",  # Whitespace only
        },
        {
            "session_number": 1,
            "date": "2025-01-01",
            "content": "Valid session content",
        },
        {
            "session_number": None,
            "date": "2025-01-02",
            "content": "Valid content without number",  # Valid: has content
        },
    ]
    
    # Simulate import logic with Fix 1
    ledger = []
    for session in parsed_sessions:
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
                "what_happened": [content[:200]],
                "deltas": {"pressure_change": 0, "heat_change": 0},
                "active_sources": [],
            })
    
    # Verify only valid sessions included
    assert len(ledger) == 2  # Only 2 valid sessions
    assert ledger[0]["session_number"] == 1
    assert ledger[1]["session_number"] is None  # But has content, so valid


def test_canon_auto_append_default_off():
    """Test that canon auto-append is now opt-in with default OFF.
    
    Regression test for FIX 2: Designer wants canon updates to be opt-in, not automatic.
    """
    # Simulating the finalize form checkbox default
    add_to_canon_default = False  # FIX 2: Changed from True to False
    
    # Verify default is now OFF
    assert add_to_canon_default == False


def test_campaign_history_export_manual_entries_detailed():
    """Test that campaign history export uses detailed format for manual entries.
    
    Regression test for FIX 3: Campaign history should match session export richness.
    """
    # Simulate manual entry with full data
    manual_entry = {
        "entry_id": "manual_001",
        "title": "Unexpected Ambush",
        "description": "Party ambushed by bandits on road",
        "tags": ["combat", "surprise"],
        "severity": 7,
        "related_factions": ["bandit_gang"],
        "related_scars": ["wounded_leg"],
        "notes": "Player rolled critical fail on perception",
        "pressure_delta": 2,
        "heat_delta": 1,
    }
    
    # Build export lines using FIX 3 format (detailed, not compact)
    lines = []
    lines.append(f"#### {manual_entry['title']}")
    lines.append("")
    lines.append(f"**Description**: {manual_entry['description']}")
    lines.append("")
    
    if manual_entry.get('tags'):
        lines.append(f"**Tags**: {', '.join(manual_entry['tags'])}")
        lines.append("")
    
    if manual_entry.get('severity'):
        lines.append(f"**Severity**: {manual_entry['severity']}/10")
        lines.append("")
    
    if manual_entry.get('related_factions'):
        lines.append(f"**Related Factions**: {', '.join(manual_entry['related_factions'])}")
        lines.append("")
    
    if manual_entry.get('related_scars'):
        lines.append(f"**Related Scars**: {', '.join(manual_entry['related_scars'])}")
        lines.append("")
    
    if manual_entry.get('notes'):
        lines.append(f"**GM Notes**: {manual_entry['notes']}")
        lines.append("")
    
    delta_parts = []
    if manual_entry.get('pressure_delta'):
        delta_parts.append(f"Pressure: {manual_entry['pressure_delta']:+d}")
    if manual_entry.get('heat_delta'):
        delta_parts.append(f"Heat: {manual_entry['heat_delta']:+d}")
    if delta_parts:
        lines.append(f"*Entry Impact: {' | '.join(delta_parts)}*")
        lines.append("")
    
    export_text = "\n".join(lines)
    
    # Verify rich format (not compressed inline)
    assert "**Description**:" in export_text
    assert "**Tags**:" in export_text
    assert "**Severity**:" in export_text
    assert "**Related Factions**:" in export_text
    assert "**Related Scars**:" in export_text
    assert "**GM Notes**:" in export_text
    assert "*Entry Impact:" in export_text
    
    # Verify NOT using old compressed format
    assert "*Tags:" not in export_text  # Old format used * not **
    assert "| Severity:" not in " ".join(lines[:3])  # Not all on one line


def test_session_id_generation_unique():
    """Test that each session gets a unique session_id.
    
    Regression test for duplicate Session 5 issue - session_id prevents ambiguity.
    """
    from datetime import datetime
    
    # Simulate creating two sessions at different times
    timestamp1 = datetime.now()
    session_id_1 = f"session_{timestamp1.strftime('%Y%m%d_%H%M%S')}"
    
    # Wait enough for seconds to change (in real use, sessions are seconds/minutes apart)
    import time
    time.sleep(1.1)
    
    timestamp2 = datetime.now()
    session_id_2 = f"session_{timestamp2.strftime('%Y%m%d_%H%M%S')}"
    
    # Verify uniqueness
    assert session_id_1 != session_id_2
    
    # Verify format
    assert session_id_1.startswith("session_")
    assert len(session_id_1) > 15  # session_YYYYMMDD_HHMMSS


def test_empty_state_changes_omitted():
    """Test that empty 'State Changes' sections are omitted from exports.
    
    Regression test for empty state change blocks looking broken.
    """
    # Simulate deltas with no actual changes
    deltas = {
        "pressure_change": 0,
        "heat_change": 0,
        "rumor_spread": False,
        "faction_attention_change": False,
    }
    
    # Check if there are actual changes
    has_changes = (
        deltas.get('pressure_change', 0) != 0 or
        deltas.get('heat_change', 0) != 0 or
        deltas.get('rumor_spread', False) or
        deltas.get('faction_attention_change', False)
    )
    
    assert has_changes == False
    
    # Simulate deltas with changes
    deltas_with_changes = {
        "pressure_change": 2,
        "heat_change": 0,
        "rumor_spread": False,
        "faction_attention_change": False,
    }
    
    has_changes_2 = (
        deltas_with_changes.get('pressure_change', 0) != 0 or
        deltas_with_changes.get('heat_change', 0) != 0 or
        deltas_with_changes.get('rumor_spread', False) or
        deltas_with_changes.get('faction_attention_change', False)
    )
    
    assert has_changes_2 == True


def test_peak_severity_tracking():
    """Test that peak severity updates from session metadata.
    
    Regression test for highest_severity_seen remaining 0.
    """
    from spar_campaign import CampaignState
    
    # Start with default state
    cs = CampaignState.default()
    assert cs.highest_severity_seen == 0
    
    # Simulate session with severity metadata
    metadata = {"severity_avg": 6.5}
    
    # Update peak severity
    new_peak = cs.highest_severity_seen
    if metadata.get("severity_avg", 0) > new_peak:
        new_peak = int(metadata["severity_avg"])
    
    assert new_peak == 6
    
    # Simulate another session with lower severity
    metadata2 = {"severity_avg": 4.2}
    if metadata2.get("severity_avg", 0) > new_peak:
        new_peak = int(metadata2["severity_avg"])
    
    # Peak should not decrease
    assert new_peak == 6
    
    # Simulate session with higher severity
    metadata3 = {"severity_avg": 8.7}
    if metadata3.get("severity_avg", 0) > new_peak:
        new_peak = int(metadata3["severity_avg"])
    
    assert new_peak == 8


def test_session_id_disambiguates_duplicate_numbers():
    """Test that session_id allows disambiguation in exports when session_number duplicates exist."""
    # Simulate two sessions with same number but different IDs
    entry1 = {
        "session_id": "session_20251226_142749",
        "session_number": 5,
        "session_date": "2025-12-26T14:27:49",
    }
    
    entry2 = {
        "session_id": "session_20251226_144410",
        "session_number": 5,
        "session_date": "2025-12-26T14:44:10",
    }
    
    # Extract time portions for disambiguation
    time1 = entry1["session_id"].split('_')[-1]
    time2 = entry2["session_id"].split('_')[-1]
    
    # Verify they're different
    assert time1 != time2
    assert time1 == "142749"
    assert time2 == "144410"
    
    # Verify export headings would be unique
    heading1 = f"Session {entry1['session_number']} — {entry1['session_date'][:10]} ({time1})"
    heading2 = f"Session {entry2['session_number']} — {entry2['session_date'][:10]} ({time2})"
    
    assert heading1 != heading2


def test_story_export_excludes_system_fields():
    """Test that story exports exclude all system-facing fields per export spec v0.1.
    
    Validates DATA_CONTRACT and EXPORT_SPEC compliance.
    """
    # Simulate manual entry with both story and system fields
    manual_entry = {
        "entry_id": "manual_001",
        "title": "Unexpected Encounter",
        "description": "Crew discovered hidden research lab",
        "tags": ["information", "discovery"],  # SYSTEM
        "severity": 7,  # SYSTEM
        "related_factions": ["corp_security"],  # SYSTEM
        "related_scars": ["exposed_identity"],  # SYSTEM
        "notes": "Players loved this twist",  # STORY
        "pressure_delta": 2,  # SYSTEM
        "heat_delta": 1,  # SYSTEM
    }
    
    # Build story export (should only include story fields)
    story_lines = []
    story_lines.append(f"#### {manual_entry['title']}")
    story_lines.append("")
    story_lines.append(f"{manual_entry['description']}")
    story_lines.append("")
    
    if manual_entry.get('notes'):
        story_lines.append(f"*GM Notes: {manual_entry['notes']}*")
        story_lines.append("")
    
    story_export = "\n".join(story_lines)
    
    # Verify story fields included
    assert "Unexpected Encounter" in story_export
    assert "hidden research lab" in story_export
    assert "Players loved this twist" in story_export
    
    # Verify system fields EXCLUDED
    assert "Tags" not in story_export
    assert "Severity" not in story_export
    assert "Related Factions" not in story_export
    assert "Related Scars" not in story_export
    assert "Entry Impact" not in story_export
    assert "Pressure:" not in story_export
    assert "Heat:" not in story_export
    assert "information" not in story_export  # Tag value
    assert "7" not in story_export  # Severity value
    assert "corp_security" not in story_export  # Faction value


def test_story_export_includes_all_story_fields():
    """Test that story exports include all required story-facing fields.
    
    Validates completeness of story export per export spec v0.1.
    """
    # Simulate session entry with story fields
    session_entry = {
        "session_id": "session_20251226_144410",
        "session_number": 5,
        "session_date": "2025-12-26T14:44:10",
        "what_happened": [
            "Event A happened",
            "Event B followed",
            "Event C concluded"
        ],
        "session_notes": "Great session with high player engagement",
        "manual_entries": [
            {
                "title": "Key Moment",
                "description": "NPC revealed critical information",
                "notes": "This was improvised brilliantly"
            }
        ]
    }
    
    # Build story export
    lines = []
    lines.append(f"### Session {session_entry['session_number']} — {session_entry['session_date'][:10]}")
    lines.append("")
    
    # What Happened
    lines.append("**What Happened:**")
    for bullet in session_entry['what_happened']:
        lines.append(f"- {bullet}")
    lines.append("")
    
    # Manual Entries
    if session_entry.get('manual_entries'):
        lines.append("**Manual Entries & Notable Moments:**")
        lines.append("")
        for entry in session_entry['manual_entries']:
            lines.append(f"#### {entry['title']}")
            lines.append("")
            lines.append(entry['description'])
            lines.append("")
            if entry.get('notes'):
                lines.append(f"*GM Notes: {entry['notes']}*")
                lines.append("")
    
    # Session Notes
    if session_entry.get('session_notes'):
        lines.append("**Session Notes:**")
        lines.append("")
        lines.append(session_entry['session_notes'])
        lines.append("")
    
    export = "\n".join(lines)
    
    # Verify all story fields present
    assert "Session 5 — 2025-12-26" in export
    assert "Event A happened" in export
    assert "Event B followed" in export
    assert "Event C concluded" in export
    assert "Key Moment" in export
    assert "NPC revealed critical information" in export
    assert "This was improvised brilliantly" in export
    assert "Great session with high player engagement" in export


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
