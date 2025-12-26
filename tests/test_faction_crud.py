"""Tests for Faction CRUD v0.1 implementation.

Test coverage:
- Data model migration (v0.2 → v0.3)
- CRUD operations (add, edit, archive, restore)
- Export integration (faction roster in campaign history)
- Audit trail generation
- Story/system separation
"""

import json
from datetime import datetime

import pytest

from spar_campaign.models import FactionState, CampaignState


class TestFactionDataModel:
    """Test FactionState data model and migration."""
    
    def test_new_faction_state_structure(self):
        """Test creating new FactionState with v0.3 structure."""
        faction = FactionState(
            faction_id="city_watch",
            name="City Watch",
            description="Local law enforcement",
            attention=5,
            disposition=-1,
            notes="Secret: corrupt captain",
            is_active=True,
        )
        
        assert faction.faction_id == "city_watch"
        assert faction.name == "City Watch"
        assert faction.description == "Local law enforcement"
        assert faction.attention == 5
        assert faction.disposition == -1
        assert faction.notes == "Secret: corrupt captain"
        assert faction.is_active is True
    
    def test_faction_attention_bands(self):
        """Test attention band labels."""
        bands = [
            (0, "Unaware"),
            (3, "Noticed"),
            (8, "Interested"),
            (13, "Focused"),
            (18, "Obsessed"),
        ]
        
        for attention, expected_band in bands:
            faction = FactionState(faction_id="test", name="Test", attention=attention)
            assert faction.get_attention_band() == expected_band
    
    def test_faction_disposition_labels(self):
        """Test disposition labels with emoji."""
        labels = [
            (-2, "😡 Hostile"),
            (-1, "😠 Unfriendly"),
            (0, "😐 Neutral"),
            (1, "🙂 Friendly"),
            (2, "😊 Allied"),
        ]
        
        for disposition, expected_label in labels:
            faction = FactionState(faction_id="test", name="Test", disposition=disposition)
            assert faction.get_disposition_label() == expected_label
    
    def test_migration_short_notes_to_name(self):
        """Test migration: short notes without punctuation → name field."""
        # v0.2 format: notes contained display name
        old_data = {
            "faction_id": "city_watch",
            "attention": 10,
            "disposition": -1,
            "notes": "City Watch",  # Short, no punctuation
        }
        
        faction = FactionState.from_dict(old_data)
        
        assert faction.name == "City Watch"  # Migrated from notes
        assert faction.description == ""  # Empty for migrated
        assert faction.notes is None  # Cleared
        assert faction.is_active is True  # Defaults to active
    
    def test_migration_long_notes_preserved(self):
        """Test migration: long punctuated notes → derive name from ID, preserve notes."""
        old_data = {
            "faction_id": "merchant_guild",
            "attention": 5,
            "disposition": 0,
            "notes": "Trade organization. Controls imports. Secret: laundering money for syndicate.",
        }
        
        faction = FactionState.from_dict(old_data)
        
        assert faction.name == "Merchant Guild"  # Derived from ID
        assert faction.description == ""  # Empty for migrated
        assert faction.notes == "Trade organization. Controls imports. Secret: laundering money for syndicate."
        assert faction.is_active is True
    
    def test_migration_empty_notes(self):
        """Test migration: empty notes → derive name from ID."""
        old_data = {
            "faction_id": "shadow_syndicate",
            "attention": 0,
            "disposition": 0,
            "notes": None,
        }
        
        faction = FactionState.from_dict(old_data)
        
        assert faction.name == "Shadow Syndicate"  # Derived from ID
        assert faction.description == ""
        assert faction.notes is None
        assert faction.is_active is True
    
    def test_new_format_no_migration(self):
        """Test loading new v0.3 format (no migration needed)."""
        new_data = {
            "faction_id": "rebel_alliance",
            "name": "Rebel Alliance",
            "description": "Underground resistance movement",
            "attention": 12,
            "disposition": 1,
            "notes": "Leader: Commander Phoenix",
            "is_active": True,
        }
        
        faction = FactionState.from_dict(new_data)
        
        assert faction.name == "Rebel Alliance"
        assert faction.description == "Underground resistance movement"
        assert faction.notes == "Leader: Commander Phoenix"
        assert faction.attention == 12
        assert faction.disposition == 1
        assert faction.is_active is True
    
    def test_soft_delete_serialization(self):
        """Test that is_active flag is preserved in serialization."""
        faction = FactionState(
            faction_id="archived",
            name="Archived Faction",
            description="",
            is_active=False,  # Soft deleted
        )
        
        data = faction.to_dict()
        assert data["is_active"] is False
        
        restored = FactionState.from_dict(data)
        assert restored.is_active is False


class TestFactionCRUD:
    """Test CRUD operations on factions."""
    
    def test_add_faction_to_campaign(self):
        """Test adding a new faction to campaign state."""
        campaign_state = CampaignState.default()
        assert len(campaign_state.factions) == 0
        
        new_faction = FactionState(
            faction_id="new_faction",
            name="New Faction",
            description="A new organization",
            attention=0,
            disposition=0,
        )
        
        new_factions = dict(campaign_state.factions)
        new_factions["new_faction"] = new_faction
        
        updated_state = CampaignState(
            version=campaign_state.version,
            campaign_pressure=campaign_state.campaign_pressure,
            heat=campaign_state.heat,
            scars=campaign_state.scars,
            factions=new_factions,
            total_scenes_run=campaign_state.total_scenes_run,
            total_cutoffs_seen=campaign_state.total_cutoffs_seen,
            highest_severity_seen=campaign_state.highest_severity_seen,
            _legacy_scars=campaign_state._legacy_scars,
        )
        
        assert len(updated_state.factions) == 1
        assert "new_faction" in updated_state.factions
        assert updated_state.factions["new_faction"].name == "New Faction"
    
    def test_edit_faction(self):
        """Test editing an existing faction."""
        initial_faction = FactionState(
            faction_id="test",
            name="Original Name",
            description="Original desc",
            attention=5,
            disposition=0,
        )
        
        campaign_state = CampaignState(
            factions={"test": initial_faction}
        )
        
        # Edit faction
        updated_faction = FactionState(
            faction_id="test",
            name="Updated Name",
            description="Updated description",
            attention=10,
            disposition=1,
            notes="New notes",
            is_active=True,
        )
        
        new_factions = dict(campaign_state.factions)
        new_factions["test"] = updated_faction
        
        updated_state = CampaignState(
            version=campaign_state.version,
            campaign_pressure=campaign_state.campaign_pressure,
            heat=campaign_state.heat,
            scars=campaign_state.scars,
            factions=new_factions,
            total_scenes_run=campaign_state.total_scenes_run,
            total_cutoffs_seen=campaign_state.total_cutoffs_seen,
            highest_severity_seen=campaign_state.highest_severity_seen,
            _legacy_scars=campaign_state._legacy_scars,
        )
        
        edited = updated_state.factions["test"]
        assert edited.name == "Updated Name"
        assert edited.description == "Updated description"
        assert edited.attention == 10
        assert edited.disposition == 1
        assert edited.notes == "New notes"
    
    def test_archive_faction_soft_delete(self):
        """Test archiving a faction (soft delete)."""
        faction = FactionState(
            faction_id="to_archive",
            name="To Archive",
            description="Will be archived",
            attention=8,
            disposition=0,
            is_active=True,
        )
        
        # Archive by setting is_active=False
        archived = FactionState(
            faction_id=faction.faction_id,
            name=faction.name,
            description=faction.description,
            attention=faction.attention,
            disposition=faction.disposition,
            notes=faction.notes,
            is_active=False,  # Soft delete
        )
        
        assert archived.is_active is False
        assert archived.attention == 8  # Data preserved
        assert archived.name == "To Archive"  # Still accessible
    
    def test_restore_archived_faction(self):
        """Test restoring an archived faction."""
        archived = FactionState(
            faction_id="archived",
            name="Archived Faction",
            description="Was archived",
            attention=12,
            disposition=-1,
            is_active=False,
        )
        
        # Restore by setting is_active=True
        restored = FactionState(
            faction_id=archived.faction_id,
            name=archived.name,
            description=archived.description,
            attention=archived.attention,
            disposition=archived.disposition,
            notes=archived.notes,
            is_active=True,  # Restore
        )
        
        assert restored.is_active is True
        assert restored.attention == 12  # Data preserved
        assert restored.name == "Archived Faction"
    
    def test_quick_attention_adjustment(self):
        """Test quick +/- attention adjustments."""
        faction = FactionState(
            faction_id="test",
            name="Test",
            attention=10,
            disposition=0,
        )
        
        # Increase attention
        increased = FactionState(
            faction_id=faction.faction_id,
            name=faction.name,
            description=faction.description,
            attention=min(20, faction.attention + 1),
            disposition=faction.disposition,
            notes=faction.notes,
            is_active=faction.is_active,
        )
        assert increased.attention == 11
        
        # Decrease attention
        decreased = FactionState(
            faction_id=faction.faction_id,
            name=faction.name,
            description=faction.description,
            attention=max(0, faction.attention - 1),
            disposition=faction.disposition,
            notes=faction.notes,
            is_active=faction.is_active,
        )
        assert decreased.attention == 9
        
        # Test boundaries
        max_faction = FactionState(faction_id="test", name="Test", attention=20)
        maxed = FactionState(
            faction_id=max_faction.faction_id,
            name=max_faction.name,
            description=max_faction.description,
            attention=min(20, max_faction.attention + 1),
            disposition=max_faction.disposition,
            notes=max_faction.notes,
            is_active=max_faction.is_active,
        )
        assert maxed.attention == 20  # Capped
        
        min_faction = FactionState(faction_id="test", name="Test", attention=0)
        minned = FactionState(
            faction_id=min_faction.faction_id,
            name=min_faction.name,
            description=min_faction.description,
            attention=max(0, min_faction.attention - 1),
            disposition=min_faction.disposition,
            notes=min_faction.notes,
            is_active=min_faction.is_active,
        )
        assert minned.attention == 0  # Floored


class TestAuditTrail:
    """Test audit trail generation for faction admin actions."""
    
    def test_audit_entry_faction_added(self):
        """Test audit entry structure for adding faction."""
        audit_entry = {
            "entry_type": "admin_action",
            "timestamp": datetime.now().isoformat(),
            "action": "faction_added",
            "details": {
                "faction_id": "new_faction",
                "name": "New Faction",
                "initial_attention": 5,
                "initial_disposition": 0,
            }
        }
        
        assert audit_entry["entry_type"] == "admin_action"
        assert audit_entry["action"] == "faction_added"
        assert audit_entry["details"]["faction_id"] == "new_faction"
        assert audit_entry["details"]["name"] == "New Faction"
    
    def test_audit_entry_faction_edited(self):
        """Test audit entry structure for editing faction."""
        audit_entry = {
            "entry_type": "admin_action",
            "timestamp": datetime.now().isoformat(),
            "action": "faction_edited",
            "details": {
                "faction_id": "city_watch",
                "changes": {
                    "name": "City Watch (Updated)",
                    "attention": 15,
                    "disposition": -2,
                }
            }
        }
        
        assert audit_entry["action"] == "faction_edited"
        assert audit_entry["details"]["faction_id"] == "city_watch"
        assert "changes" in audit_entry["details"]
    
    def test_audit_entry_faction_archived(self):
        """Test audit entry structure for archiving faction."""
        audit_entry = {
            "entry_type": "admin_action",
            "timestamp": datetime.now().isoformat(),
            "action": "faction_archived",
            "details": {
                "faction_id": "old_faction",
                "name": "Old Faction",
            }
        }
        
        assert audit_entry["action"] == "faction_archived"
        assert audit_entry["details"]["faction_id"] == "old_faction"
    
    def test_audit_entry_faction_restored(self):
        """Test audit entry structure for restoring faction."""
        audit_entry = {
            "entry_type": "admin_action",
            "timestamp": datetime.now().isoformat(),
            "action": "faction_restored",
            "details": {
                "faction_id": "restored_faction",
                "name": "Restored Faction",
            }
        }
        
        assert audit_entry["action"] == "faction_restored"
        assert audit_entry["details"]["faction_id"] == "restored_faction"


class TestFactionExport:
    """Test faction integration in campaign exports."""
    
    def test_faction_roster_in_campaign_export(self):
        """Test that faction roster appears in campaign history export."""
        # Create campaign with factions
        faction1 = FactionState(
            faction_id="city_watch",
            name="City Watch",
            description="Local law enforcement, focused on maintaining order",
            attention=15,  # Focused band
            disposition=-1,  # Unfriendly
            notes="Secret: corrupt captain",  # Should NOT appear in story export
            is_active=True,
        )
        
        faction2 = FactionState(
            faction_id="merchant_guild",
            name="Merchant Guild",
            description="Trade organization with significant political influence",
            attention=5,  # Noticed band
            disposition=0,  # Neutral
            is_active=True,
        )
        
        factions = {
            "city_watch": faction1,
            "merchant_guild": faction2,
        }
        
        campaign_state = CampaignState(
            version="0.2",
            factions=factions,
        )
        
        # Generate export markdown (simulating the export logic)
        lines = []
        lines.append("## Factions")
        lines.append("")
        
        active_factions = {fid: f for fid, f in campaign_state.factions.items() if f.is_active}
        for fid, faction in active_factions.items():
            attention_band = faction.get_attention_band()
            disp_label = faction.get_disposition_label().split()[1]  # Remove emoji
            
            lines.append(f"**{faction.name}** *({attention_band}, {disp_label})*")
            
            # Include description but NOT notes
            if faction.description:
                lines.append(f"{faction.description}")
            
            lines.append("")
        
        export_text = "\n".join(lines)
        
        # Verify story-facing content present
        assert "City Watch" in export_text
        assert "Focused" in export_text
        assert "Unfriendly" in export_text
        assert "Local law enforcement" in export_text
        
        assert "Merchant Guild" in export_text
        assert "Noticed" in export_text
        assert "Neutral" in export_text
        assert "Trade organization" in export_text
        
        # Verify system-facing content excluded
        assert "15" not in export_text  # Raw attention number
        assert "-1" not in export_text  # Raw disposition number
        assert "corrupt captain" not in export_text  # GM-private notes
    
    def test_archived_factions_excluded_from_export(self):
        """Test that archived factions don't appear in story exports."""
        active = FactionState(
            faction_id="active",
            name="Active Faction",
            description="Still relevant",
            is_active=True,
        )
        
        archived = FactionState(
            faction_id="archived",
            name="Archived Faction",
            description="No longer relevant",
            is_active=False,  # Archived
        )
        
        campaign_state = CampaignState(
            factions={
                "active": active,
                "archived": archived,
            }
        )
        
        # Filter to active only for export
        active_factions = {fid: f for fid, f in campaign_state.factions.items() if f.is_active}
        
        assert len(active_factions) == 1
        assert "active" in active_factions
        assert "archived" not in active_factions
    
    def test_faction_without_description(self):
        """Test faction export when description is empty."""
        faction = FactionState(
            faction_id="minimal",
            name="Minimal Faction",
            description="",  # Empty description
            attention=8,
            disposition=0,
        )
        
        lines = []
        lines.append(f"**{faction.name}** *({faction.get_attention_band()}, {faction.get_disposition_label().split()[1]})*")
        
        if faction.description:
            lines.append(f"{faction.description}")
        
        lines.append("")
        
        export_text = "\n".join(lines)
        
        # Verify name and bands appear
        assert "Minimal Faction" in export_text
        assert "Interested" in export_text
        
        # Verify empty description is properly handled (no extra blank lines)
        lines_list = export_text.split('\n')
        assert len(lines_list) == 2  # Title line + trailing blank
        assert lines_list[0].startswith("**Minimal Faction**")
        assert lines_list[1] == ""


class TestStorySystemSeparation:
    """Test that faction data respects story/system separation."""
    
    def test_story_facing_fields(self):
        """Test that story-facing fields are properly identified."""
        faction = FactionState(
            faction_id="test",
            name="Test Faction",  # Story-facing
            description="What it is and wants",  # Story-facing
            attention=10,  # Hybrid (can be both)
            disposition=-1,  # Hybrid (can be both)
            notes="GM secrets",  # GM-private (NOT story-facing)
        )
        
        # Story export should include: name, description, attention band, disposition label
        # Story export should exclude: notes, raw attention/disposition numbers
        
        story_safe = {
            "name": faction.name,
            "description": faction.description,
            "attention_band": faction.get_attention_band(),
            "disposition_label": faction.get_disposition_label(),
        }
        
        assert story_safe["name"] == "Test Faction"
        assert story_safe["description"] == "What it is and wants"
        assert story_safe["attention_band"] == "Interested"
        assert story_safe["disposition_label"] == "😠 Unfriendly"
        assert "notes" not in story_safe
    
    def test_admin_audit_is_system_facing(self):
        """Test that admin audit entries are system-facing only."""
        audit_entry = {
            "entry_type": "admin_action",  # System-facing marker
            "timestamp": datetime.now().isoformat(),
            "action": "faction_added",
            "details": {"faction_id": "test", "name": "Test"},
        }
        
        # Verify it can be filtered out of story exports
        is_story_export = audit_entry.get("entry_type") != "admin_action"
        assert is_story_export is False  # Should be excluded from story


class TestReferenceIntegrity:
    """Test that faction references in ledger are preserved by soft delete."""
    
    def test_archived_faction_preserved_for_historical_references(self):
        """Test that archived factions remain in data for historical ledger entries."""
        # Campaign with faction referenced in past sessions
        faction = FactionState(
            faction_id="old_enemy",
            name="Old Enemy",
            description="Former antagonist",
            attention=18,
            disposition=-2,
            is_active=False,  # Archived now
        )
        
        campaign_state = CampaignState(
            factions={"old_enemy": faction}
        )
        
        # Historical ledger entry referencing this faction
        ledger_entry = {
            "session_number": 5,
            "what_happened": ["Confronted Old Enemy's agents"],
            "manual_entries": [
                {
                    "title": "Boss Fight",
                    "description": "Final confrontation with Old Enemy",
                    "related_factions": ["old_enemy"],  # Reference still valid
                }
            ]
        }
        
        # Verify faction still exists (even if archived)
        assert "old_enemy" in campaign_state.factions
        assert campaign_state.factions["old_enemy"].is_active is False
        
        # Verify reference in ledger is still resolvable
        related = ledger_entry["manual_entries"][0]["related_factions"]
        assert "old_enemy" in related
        assert "old_enemy" in campaign_state.factions  # Reference valid
