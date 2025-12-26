"""Tests for Canon Summary deletion with concurrent text edits.

These tests simulate the actual UI behavior where text inputs have been edited
but not yet saved, and the user clicks a delete button.
"""

from datetime import datetime
import pytest
from streamlit_harness.campaign_ui import Campaign


@pytest.fixture
def temp_campaigns_dir(monkeypatch, tmp_path):
    """Provide a temporary campaigns directory for testing."""
    temp_dir = tmp_path / "test_campaigns"
    temp_dir.mkdir()
    monkeypatch.setattr("streamlit_harness.campaign_ui.CAMPAIGNS_DIR", temp_dir)
    return temp_dir


def test_delete_with_edited_text_ui_scenario(temp_campaigns_dir):
    """Test deletion when text has been edited but not saved.
    
    This simulates the exact bug scenario:
    1. Campaign has items ["A", "B", "C"]
    2. User edits "B" to "B_EDITED" in the text input (not saved yet)
    3. User clicks delete button next to "B_EDITED"
    4. Expected: "B" should be deleted
    5. Bug: Wrong item gets deleted because we match "B_EDITED" but stored value is "B"
    """
    # Create campaign
    campaign_id = "test_edit_delete"
    campaign = Campaign(
        campaign_id=campaign_id,
        name="Edit Delete Test",
        created=datetime.now().isoformat(),
        last_played=datetime.now().isoformat(),
        canon_summary=["A", "B", "C"],
        campaign_state=None,
        ledger=[],
        sources=[],
        prep_queue=[],
    )
    campaign.save()
    
    # Simulate UI state after user edits
    bullets_to_display = campaign.canon_summary[:15]
    delete_content = None
    text_edits = {}
    
    # User edited index 1 from "B" to "B_EDITED"
    text_edits["B"] = "B_EDITED"
    
    # User clicks delete on the row showing "B_EDITED" (index 1)
    displayed_text = "B_EDITED"  # What widget shows
    delete_content = displayed_text
    
    # Apply changes (matches UI code)
    new_canon_summary = []
    for bullet in campaign.canon_summary:
        current_content = text_edits.get(bullet, bullet)
        if delete_content is not None and current_content == delete_content:
            continue
        new_canon_summary.append(current_content)
    
    campaign.canon_summary = new_canon_summary
    campaign.save()
    
    # Verify: "B" should be deleted (became "B_EDITED" then deleted)
    reloaded = Campaign.load(campaign_id)
    assert reloaded is not None
    assert "B" not in reloaded.canon_summary
    assert "B_EDITED" not in reloaded.canon_summary
    assert reloaded.canon_summary == ["A", "C"]


def test_delete_original_when_other_row_edited(temp_campaigns_dir):
    """Test deleting unedited row when another row has unsaved edits.
    
    Scenario:
    1. Campaign has ["A", "B", "C"]
    2. User edits "A" to "A_EDITED" (not saved)
    3. User clicks delete on "C" (not edited)
    4. Expected: "C" should be deleted, "A" becomes "A_EDITED"
    """
    campaign_id = "test_mixed_ops"
    campaign = Campaign(
        campaign_id=campaign_id,
        name="Mixed Ops Test",
        created=datetime.now().isoformat(),
        last_played=datetime.now().isoformat(),
        canon_summary=["A", "B", "C"],
        campaign_state=None,
        ledger=[],
        sources=[],
        prep_queue=[],
    )
    campaign.save()
    
    # User edited index 0, wants to delete index 2
    text_edits = {"A": "A_EDITED"}
    delete_content = "C"  # Original, not edited
    
    # Apply changes
    new_canon_summary = []
    for bullet in campaign.canon_summary:
        current_content = text_edits.get(bullet, bullet)
        if delete_content is not None and current_content == delete_content:
            continue
        new_canon_summary.append(current_content)
    
    campaign.canon_summary = new_canon_summary
    campaign.save()
    
    # Verify
    reloaded = Campaign.load(campaign_id)
    assert reloaded is not None
    assert reloaded.canon_summary == ["A_EDITED", "B"]
    assert "C" not in reloaded.canon_summary


def test_delete_edited_row_among_multiple_edits(temp_campaigns_dir):
    """Test deleting when multiple rows have unsaved edits.
    
    Scenario matching user's exact case:
    1. Campaign has ["Long text", "1", "2", "4"]
    2. User edits "1" to "I have HUGE PLANS..."
    3. User edits "2" to "I keep writing..."
    4. User clicks delete on row showing "I have HUGE PLANS..."
    5. Expected: "1" should be deleted (the one that became "I have HUGE PLANS...")
    """
    campaign_id = "test_real_scenario"
    campaign = Campaign(
        campaign_id=campaign_id,
        name="Real Scenario Test",
        created=datetime.now().isoformat(),
        last_played=datetime.now().isoformat(),
        canon_summary=[
            "Vampire: The Masquerade Campaign Plan...",
            "1",
            "2",
            "4"
        ],
        campaign_state=None,
        ledger=[],
        sources=[],
        prep_queue=[],
    )
    campaign.save()
    
    # User edited both rows
    text_edits = {
        "1": "I have HUGE PLANS and I am probably overdoing it",
        "2": "I keep writing like it is a TV show and like the entire city is watching the PCs"
    }
    
    # User clicks delete on the row showing "I have HUGE PLANS..."
    delete_content = "I have HUGE PLANS and I am probably overdoing it"
    
    # Apply changes
    new_canon_summary = []
    for bullet in campaign.canon_summary:
        current_content = text_edits.get(bullet, bullet)
        if delete_content is not None and current_content == delete_content:
            continue
        new_canon_summary.append(current_content)
    
    campaign.canon_summary = new_canon_summary
    campaign.save()
    
    # Verify: "1" should be gone, "2" should become the edited version
    reloaded = Campaign.load(campaign_id)
    assert reloaded is not None
    assert "1" not in reloaded.canon_summary
    assert "I have HUGE PLANS and I am probably overdoing it" not in reloaded.canon_summary
    assert "I keep writing like it is a TV show and like the entire city is watching the PCs" in reloaded.canon_summary
    assert len(reloaded.canon_summary) == 3
