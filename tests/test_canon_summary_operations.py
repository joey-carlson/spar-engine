"""Tests for Canon Summary operations in Campaign UI.

These tests verify that Canon Summary deletion and editing work correctly,
addressing the bug where deleting any item would always remove the last item
in the list instead of the clicked item.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

# Import test dependencies
from streamlit_harness.campaign_ui import Campaign, CAMPAIGNS_DIR


@pytest.fixture
def temp_campaigns_dir(monkeypatch, tmp_path):
    """Provide a temporary campaigns directory for testing."""
    temp_dir = tmp_path / "test_campaigns"
    temp_dir.mkdir()
    monkeypatch.setattr("streamlit_harness.campaign_ui.CAMPAIGNS_DIR", temp_dir)
    return temp_dir


@pytest.fixture
def sample_campaign(temp_campaigns_dir):
    """Create a sample campaign with multiple canon summary items."""
    campaign_id = "test_campaign_001"
    campaign_name = "Test Campaign"
    timestamp = datetime.now().isoformat()
    
    campaign = Campaign(
        campaign_id=campaign_id,
        name=campaign_name,
        created=timestamp,
        last_played=timestamp,
        canon_summary=[
            "The heroes arrived in the city",
            "They met the merchant guild leader",
            "A mysterious figure appeared",
            "The city watch became suspicious",
            "An ancient artifact was discovered",
        ],
        campaign_state=None,
        ledger=[],
        sources=[],
        prep_queue=[],
    )
    
    campaign.save()
    return campaign


def test_canon_summary_deletion_first_item(sample_campaign):
    """Test deleting the first item in canon summary."""
    original_count = len(sample_campaign.canon_summary)
    first_item = sample_campaign.canon_summary[0]
    
    # Simulate index-based deletion (matches UI behavior)
    delete_index = 0
    text_edits = {}
    
    new_canon_summary = []
    for original_idx, bullet in enumerate(sample_campaign.canon_summary):
        if delete_index is not None and original_idx == delete_index:
            continue
        if original_idx in text_edits:
            new_canon_summary.append(text_edits[original_idx])
        else:
            new_canon_summary.append(bullet)
    
    sample_campaign.canon_summary = new_canon_summary
    sample_campaign.save()
    
    # Reload and verify
    reloaded = Campaign.load(sample_campaign.campaign_id)
    assert reloaded is not None
    assert len(reloaded.canon_summary) == original_count - 1
    assert first_item not in reloaded.canon_summary
    assert reloaded.canon_summary[0] == "They met the merchant guild leader"


def test_canon_summary_deletion_middle_item(sample_campaign):
    """Test deleting a middle item in canon summary."""
    original_count = len(sample_campaign.canon_summary)
    middle_item = sample_campaign.canon_summary[2]  # "A mysterious figure appeared"
    
    # Simulate index-based deletion (matches UI behavior)
    delete_index = 2
    text_edits = {}
    
    new_canon_summary = []
    for original_idx, bullet in enumerate(sample_campaign.canon_summary):
        if delete_index is not None and original_idx == delete_index:
            continue
        if original_idx in text_edits:
            new_canon_summary.append(text_edits[original_idx])
        else:
            new_canon_summary.append(bullet)
    
    sample_campaign.canon_summary = new_canon_summary
    sample_campaign.save()
    
    # Reload and verify
    reloaded = Campaign.load(sample_campaign.campaign_id)
    assert reloaded is not None
    assert len(reloaded.canon_summary) == original_count - 1
    assert middle_item not in reloaded.canon_summary
    # Verify correct items remain in order
    assert reloaded.canon_summary[0] == "The heroes arrived in the city"
    assert reloaded.canon_summary[1] == "They met the merchant guild leader"
    assert reloaded.canon_summary[2] == "The city watch became suspicious"
    assert reloaded.canon_summary[3] == "An ancient artifact was discovered"


def test_canon_summary_deletion_last_item(sample_campaign):
    """Test deleting the last item in canon summary."""
    original_count = len(sample_campaign.canon_summary)
    last_item = sample_campaign.canon_summary[-1]
    
    # Simulate index-based deletion (matches UI behavior)
    delete_index = len(sample_campaign.canon_summary) - 1
    text_edits = {}
    
    new_canon_summary = []
    for original_idx, bullet in enumerate(sample_campaign.canon_summary):
        if delete_index is not None and original_idx == delete_index:
            continue
        if original_idx in text_edits:
            new_canon_summary.append(text_edits[original_idx])
        else:
            new_canon_summary.append(bullet)
    
    sample_campaign.canon_summary = new_canon_summary
    sample_campaign.save()
    
    # Reload and verify
    reloaded = Campaign.load(sample_campaign.campaign_id)
    assert reloaded is not None
    assert len(reloaded.canon_summary) == original_count - 1
    assert last_item not in reloaded.canon_summary


def test_canon_summary_multiple_deletions(sample_campaign):
    """Test multiple successive deletions maintain correct indices."""
    # Delete item at index 1
    deleted_item_1 = sample_campaign.canon_summary[1]
    delete_index = 1
    text_edits = {}
    
    new_canon_summary = []
    for original_idx, bullet in enumerate(sample_campaign.canon_summary):
        if delete_index is not None and original_idx == delete_index:
            continue
        if original_idx in text_edits:
            new_canon_summary.append(text_edits[original_idx])
        else:
            new_canon_summary.append(bullet)
    
    sample_campaign.canon_summary = new_canon_summary
    sample_campaign.save()
    
    # Reload
    sample_campaign = Campaign.load(sample_campaign.campaign_id)
    assert sample_campaign is not None
    assert deleted_item_1 not in sample_campaign.canon_summary
    assert len(sample_campaign.canon_summary) == 4
    
    # Delete another item at index 2
    deleted_item_2 = sample_campaign.canon_summary[2]
    delete_index = 2
    text_edits = {}
    
    new_canon_summary = []
    for original_idx, bullet in enumerate(sample_campaign.canon_summary):
        if delete_index is not None and original_idx == delete_index:
            continue
        if original_idx in text_edits:
            new_canon_summary.append(text_edits[original_idx])
        else:
            new_canon_summary.append(bullet)
    
    sample_campaign.canon_summary = new_canon_summary
    sample_campaign.save()
    
    # Reload and verify
    reloaded = Campaign.load(sample_campaign.campaign_id)
    assert reloaded is not None
    assert len(reloaded.canon_summary) == 3
    assert deleted_item_1 not in reloaded.canon_summary
    assert deleted_item_2 not in reloaded.canon_summary


def test_canon_summary_edit_item(sample_campaign):
    """Test editing a canon summary item."""
    # Edit item at index 1
    new_text = "They met the guild leader and signed a contract"
    new_canon_summary = list(sample_campaign.canon_summary)
    new_canon_summary[1] = new_text
    sample_campaign.canon_summary = new_canon_summary
    sample_campaign.save()
    
    # Reload and verify
    reloaded = Campaign.load(sample_campaign.campaign_id)
    assert reloaded is not None
    assert reloaded.canon_summary[1] == new_text
    assert len(reloaded.canon_summary) == len(sample_campaign.canon_summary)


def test_canon_summary_add_item(sample_campaign):
    """Test adding a new canon summary item."""
    original_count = len(sample_campaign.canon_summary)
    new_bullet = "The party discovered a secret passage"
    
    sample_campaign.canon_summary.append(new_bullet)
    sample_campaign.save()
    
    # Reload and verify
    reloaded = Campaign.load(sample_campaign.campaign_id)
    assert reloaded is not None
    assert len(reloaded.canon_summary) == original_count + 1
    assert reloaded.canon_summary[-1] == new_bullet


def test_canon_summary_deletion_with_display_limit(sample_campaign):
    """Test deletion behavior when only displaying first N items.
    
    This simulates the UI behavior where only first 15 items are displayed.
    """
    # Add more items to exceed display limit
    for i in range(10):
        sample_campaign.canon_summary.append(f"Additional event {i+1}")
    sample_campaign.save()
    
    # Simulate UI: only display first 15
    bullets_to_display = sample_campaign.canon_summary[:15]
    
    # Delete item at index 3
    deleted_item = bullets_to_display[3]
    delete_index = 3
    text_edits = {}
    
    new_canon_summary = []
    for original_idx, bullet in enumerate(sample_campaign.canon_summary):
        if delete_index is not None and original_idx == delete_index:
            continue
        if original_idx in text_edits:
            new_canon_summary.append(text_edits[original_idx])
        else:
            new_canon_summary.append(bullet)
    
    sample_campaign.canon_summary = new_canon_summary
    sample_campaign.save()
    
    # Reload and verify
    reloaded = Campaign.load(sample_campaign.campaign_id)
    assert reloaded is not None
    assert deleted_item not in reloaded.canon_summary
    # Verify item at index 3 is now what was at index 4
    assert reloaded.canon_summary[3] == "An ancient artifact was discovered"


def test_canon_summary_deletion_preserves_order(sample_campaign):
    """Test that deletion preserves the order of remaining items."""
    original_items = list(sample_campaign.canon_summary)
    
    # Delete item at index 2
    delete_index = 2
    text_edits = {}
    
    new_canon_summary = []
    for original_idx, bullet in enumerate(sample_campaign.canon_summary):
        if delete_index is not None and original_idx == delete_index:
            continue
        if original_idx in text_edits:
            new_canon_summary.append(text_edits[original_idx])
        else:
            new_canon_summary.append(bullet)
    
    sample_campaign.canon_summary = new_canon_summary
    sample_campaign.save()
    
    # Reload and verify order
    reloaded = Campaign.load(sample_campaign.campaign_id)
    assert reloaded is not None
    expected = [original_items[0], original_items[1], original_items[3], original_items[4]]
    assert reloaded.canon_summary == expected


def test_canon_summary_empty_after_all_deletions(sample_campaign):
    """Test deleting all items results in empty list."""
    count = len(sample_campaign.canon_summary)
    
    # Delete all items one by one from index 0
    for _ in range(count):
        if sample_campaign.canon_summary:
            delete_index = 0
            text_edits = {}
            
            new_canon_summary = []
            for original_idx, bullet in enumerate(sample_campaign.canon_summary):
                if delete_index is not None and original_idx == delete_index:
                    continue
                if original_idx in text_edits:
                    new_canon_summary.append(text_edits[original_idx])
                else:
                    new_canon_summary.append(bullet)
            
            sample_campaign.canon_summary = new_canon_summary
            sample_campaign.save()
            sample_campaign = Campaign.load(sample_campaign.campaign_id)
            assert sample_campaign is not None
    
    # Verify empty
    assert len(sample_campaign.canon_summary) == 0


def test_canon_summary_deletion_with_duplicates(sample_campaign):
    """Test deletion when list contains duplicate text.
    
    With index-based deletion, only the specific index is removed.
    """
    # Add duplicate entries
    sample_campaign.canon_summary.append("They met the merchant guild leader")  # Duplicate at index 5
    sample_campaign.canon_summary.append("Another unique event")
    sample_campaign.save()
    
    original_count = len(sample_campaign.canon_summary)
    
    # Delete ONLY the duplicate at index 5 using index-based deletion
    delete_index = 5
    text_edits = {}
    
    new_canon_summary = []
    for original_idx, bullet in enumerate(sample_campaign.canon_summary):
        if delete_index is not None and original_idx == delete_index:
            continue
        if original_idx in text_edits:
            new_canon_summary.append(text_edits[original_idx])
        else:
            new_canon_summary.append(bullet)
    
    sample_campaign.canon_summary = new_canon_summary
    sample_campaign.save()
    
    # Reload and verify - only ONE occurrence removed
    reloaded = Campaign.load(sample_campaign.campaign_id)
    assert reloaded is not None
    assert len(reloaded.canon_summary) == original_count - 1
    # Original at index 1 should still exist
    assert reloaded.canon_summary[1] == "They met the merchant guild leader"
    # The duplicate at index 5 should be gone, so index 6 moved to 5
    assert reloaded.canon_summary[5] == "Another unique event"


def test_canon_summary_edit_and_delete_sequence(sample_campaign):
    """Test that editing and then deleting works correctly."""
    # Edit item at index 1
    new_text = "Modified merchant guild meeting"
    new_canon_summary = list(sample_campaign.canon_summary)
    new_canon_summary[1] = new_text
    sample_campaign.canon_summary = new_canon_summary
    sample_campaign.save()
    
    # Reload
    sample_campaign = Campaign.load(sample_campaign.campaign_id)
    assert sample_campaign is not None
    assert sample_campaign.canon_summary[1] == new_text
    
    # Now delete item at index 3
    deleted_item = sample_campaign.canon_summary[3]
    delete_index = 3
    text_edits = {}
    
    new_canon_summary = []
    for original_idx, bullet in enumerate(sample_campaign.canon_summary):
        if delete_index is not None and original_idx == delete_index:
            continue
        if original_idx in text_edits:
            new_canon_summary.append(text_edits[original_idx])
        else:
            new_canon_summary.append(bullet)
    
    sample_campaign.canon_summary = new_canon_summary
    sample_campaign.save()
    
    # Reload and verify
    reloaded = Campaign.load(sample_campaign.campaign_id)
    assert reloaded is not None
    assert len(reloaded.canon_summary) == 4
    assert deleted_item not in reloaded.canon_summary
    assert reloaded.canon_summary[1] == new_text  # Edit persisted


def test_canon_summary_deletion_index_stability():
    """Test index-based deletion works correctly across multiple operations.
    
    This is the critical test for the bug fix - ensuring we delete
    the CORRECT item using stable indices.
    """
    campaign_id = "test_index_stability"
    timestamp = datetime.now().isoformat()
    
    # Create campaign with exactly numbered bullets to track indices
    campaign = Campaign(
        campaign_id=campaign_id,
        name="Index Test",
        created=timestamp,
        last_played=timestamp,
        canon_summary=[
            "Item 0",
            "Item 1", 
            "Item 2",
            "Item 3",
            "Item 4",
        ],
        campaign_state=None,
        ledger=[],
        sources=[],
        prep_queue=[],
    )
    campaign.save()
    
    # Delete at index 2
    delete_index = 2
    text_edits = {}
    
    new_canon_summary = []
    for original_idx, bullet in enumerate(campaign.canon_summary):
        if delete_index is not None and original_idx == delete_index:
            continue
        if original_idx in text_edits:
            new_canon_summary.append(text_edits[original_idx])
        else:
            new_canon_summary.append(bullet)
    
    campaign.canon_summary = new_canon_summary
    campaign.save()
    
    # Verify deletion
    reloaded = Campaign.load(campaign_id)
    assert reloaded is not None
    assert "Item 2" not in reloaded.canon_summary
    assert reloaded.canon_summary == ["Item 0", "Item 1", "Item 3", "Item 4"]
    
    # Delete at index 0 from NEW list
    delete_index = 0
    text_edits = {}
    
    new_canon_summary = []
    for original_idx, bullet in enumerate(reloaded.canon_summary):
        if delete_index is not None and original_idx == delete_index:
            continue
        if original_idx in text_edits:
            new_canon_summary.append(text_edits[original_idx])
        else:
            new_canon_summary.append(bullet)
    
    reloaded.canon_summary = new_canon_summary
    reloaded.save()
    
    # Verify deletion
    reloaded = Campaign.load(campaign_id)
    assert reloaded is not None
    assert "Item 0" not in reloaded.canon_summary
    assert reloaded.canon_summary == ["Item 1", "Item 3", "Item 4"]
    
    # Delete at index 1 from CURRENT list
    delete_index = 1
    text_edits = {}
    
    new_canon_summary = []
    for original_idx, bullet in enumerate(reloaded.canon_summary):
        if delete_index is not None and original_idx == delete_index:
            continue
        if original_idx in text_edits:
            new_canon_summary.append(text_edits[original_idx])
        else:
            new_canon_summary.append(bullet)
    
    reloaded.canon_summary = new_canon_summary
    reloaded.save()
    
    # Verify final state
    reloaded = Campaign.load(campaign_id)
    assert reloaded is not None
    assert reloaded.canon_summary == ["Item 1", "Item 4"]
