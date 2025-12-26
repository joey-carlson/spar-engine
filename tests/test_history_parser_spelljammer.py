"""Test history parser with real Spelljammer campaign file.

Tests section-aware parsing, entity classification, and correct handling
of structured campaign history documents.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from streamlit_harness.history_parser import (
    parse_campaign_history,
    split_by_sections,
    extract_canon_from_section,
    parse_ledger_sessions,
    classify_entities,
)


# Spelljammer campaign history (abbreviated for testing)
SPELLJAMMER_HISTORY = """# Spelljammer Campaign History for SPAR Import

Notes:
- Dates below are synthetic "Log Dates" for parsing tests

Session 10 is the current session: the Athas one-shot
- "Waking the Guardians Spiral" is listed under Future Sessions

---

## Canon Summary

### Premise
A Spelljammer 5e campaign with a "Treasure Planet meets Planescape meets Radiant Horror" vibe. The core myth-arc is time, memory, and who gets to decide what history "should" be, centered on the Chronolens and the secret order called the Temporal Guardians.

### Key NPCs / Powers in Play
- Biziver (autognome cleric, Twilight/Celestian), linked to the Temporal Guardians, later captured in the betrayal at the Citadel
- The Solstice Pact (Astral Elf splinter faction) seeking "temporal reclamation," using infiltration and chronomancy, with Magnus as an agent
- The Makers (a Phirblas offshoot, conceptual glyph-architects) whose hidden systems under/within the Citadel run on intent-driven glyph logic

### Major Artifacts and Mysteries
- The Chronolens: a powerful temporal vision/observation device; stolen by Magnus + Solstice Pact during the Citadel betrayal

### Current Situation
- The party opened a doorway to the Infinite Staircase (as it began to close) at the same moment a massive warforged city-ship appeared over the Radiant Citadel

---

## Campaign Ledger (Sessionized History)

### 2025-01-05 — Session 0 — Radiant Citadel: Formation and Omens
- The PCs meet on/around the Radiant Citadel
- Zefot is singled out by the Amethyst Incarnate and receives the "branching life-path" boon

### 2025-01-19 — Session 1 — The Blight Job → Fistandia's Mansion
- The party investigates a world/region suffering an accelerating blight
- Research leads them through a portal into Fistandia's extradimensional mansion

### 2025-05-25 — Session 10 (Current) — Athas One-Shot: Glass Spires
This session is a side-story in the Dark Sun–toned desert wasteland (Athas feel).
- The party plays as a four-character one-shot team
- Location focus: the Glass Spires and a partially exposed, ancient colossus structure

---

## Future Sessions

### Future Session — Waking the Guardians Spiral (Projected Session 11)
- Macro-objective: ascend the Infinite Staircase to reach the Temporal Guardians before the Solstice Pact
- Expected play: paradox realms, time fractures, and "what counts as canon" dilemmas

---

## Open Threads and "Next Imports" Hooks
- Recover the Chronolens from the Solstice Pact; determine what they've learned/changed with it
- Rescue Biziver, and recover any stolen notes that decode Makers / Guardians access routes
- Zefot's displacement (Eberron → Radiant Citadel + 20,000 years) and who "touched" that portal
"""


def test_section_splitting():
    """Test that document splits correctly by ## headings."""
    sections = split_by_sections(SPELLJAMMER_HISTORY)
    
    # Should have these sections
    assert "_preamble" in sections
    assert "canon summary" in sections
    assert "campaign ledger sessionized history" in sections
    assert "future sessions" in sections
    
    # Preamble should contain notes
    assert "Session 10 is the current session" in sections["_preamble"]
    
    # Canon Summary should not contain ledger text
    assert "2025-01-05" not in sections["canon summary"]
    assert "Session 0" not in sections["canon summary"]


def test_canon_extraction_clean():
    """Test that Canon Summary extraction is clean (no preamble/ledger bleed)."""
    parsed = parse_campaign_history(SPELLJAMMER_HISTORY)
    canon = parsed["canon_summary"]
    
    # Should have canon bullets
    assert len(canon) > 0
    assert len(canon) <= 12  # Capped at 12
    
    # Should NOT contain meta-text
    for bullet in canon:
        assert "import" not in bullet.lower()
        assert "session 10 is current" not in bullet.lower()
        assert "waking the guardians spiral" not in bullet.lower()
        assert "## campaign ledger" not in bullet.lower()
    
    # Should contain actual canon content
    canon_text = ' '.join(canon)
    assert "Chronolens" in canon_text or "Temporal Guardians" in canon_text


def test_session_parsing_uses_actual_dates():
    """Test that sessions use real YYYY-MM-DD dates, not line numbers."""
    parsed = parse_campaign_history(SPELLJAMMER_HISTORY)
    sessions = parsed["sessions"]
    
    # Should detect 3 sessions from ledger
    assert len(sessions) == 3
    
    # First session should be Session 0
    assert sessions[0]["session_number"] == 0
    assert sessions[0]["date"] == "2025-01-05"
    assert "Radiant Citadel" in sessions[0]["title"]
    
    # Last session should be Session 10
    assert sessions[2]["session_number"] == 10
    assert sessions[2]["date"] == "2025-05-25"
    assert "Athas" in sessions[2]["title"]
    
    # Session numbers should NOT be line numbers like 4, 6, 8
    session_nums = [s["session_number"] for s in sessions]
    assert 4 not in session_nums
    assert 6 not in session_nums


def test_entity_classification():
    """Test that entities are classified correctly (factions vs places vs artifacts)."""
    parsed = parse_campaign_history(SPELLJAMMER_HISTORY)
    
    factions = parsed["factions"]
    entities = parsed["entities"]
    
    # Should classify Temporal Guardians and Solstice Pact as factions
    assert "Temporal Guardians" in factions
    assert "Solstice Pact" in factions
    
    # Should classify Radiant Citadel as place, not faction
    assert "Radiant Citadel" not in factions
    if entities.get("places"):
        assert "Radiant Citadel" in entities["places"]
    
    # Should classify Infinite Staircase as place, not faction
    assert "Infinite Staircase" not in factions
    if entities.get("places"):
        assert "Infinite Staircase" in entities["places"]


def test_future_sessions_not_in_ledger():
    """Test that Future Sessions content doesn't bleed into ledger or canon."""
    parsed = parse_campaign_history(SPELLJAMMER_HISTORY)
    
    # "Waking the Guardians Spiral" should appear in future_sessions
    future = parsed.get("future_sessions", [])
    assert len(future) > 0
    assert any("Waking the Guardians" in f["title"] for f in future)
    
    # Should NOT appear in sessions
    session_titles = [s.get("title", "") for s in parsed["sessions"]]
    assert not any("Waking the Guardians" in title for title in session_titles)
    
    # Should NOT appear in canon summary
    canon_text = ' '.join(parsed["canon_summary"])
    assert "Waking the Guardians" not in canon_text


def test_open_threads_extracted():
    """Test that Open Threads are extracted separately."""
    parsed = parse_campaign_history(SPELLJAMMER_HISTORY)
    
    threads = parsed.get("open_threads", [])
    assert len(threads) > 0
    
    # Should contain thread about Chronolens recovery
    assert any("Chronolens" in thread for thread in threads)
    
    # Threads should NOT appear in canon summary
    canon_text = ' '.join(parsed["canon_summary"])
    # Canon can mention Chronolens, but not as "Recover the Chronolens" hook
    if "Recover the Chronolens" in canon_text:
        pytest.fail("Open Threads leaked into Canon Summary")


def test_full_parse_structure():
    """Test that full parse returns expected structure."""
    parsed = parse_campaign_history(SPELLJAMMER_HISTORY)
    
    # Should have all expected keys
    assert "sessions" in parsed
    assert "canon_summary" in parsed
    assert "factions" in parsed
    assert "entities" in parsed
    assert "future_sessions" in parsed
    assert "open_threads" in parsed
    assert "notes" in parsed
    
    # Entities should be categorized
    entities = parsed["entities"]
    assert "places" in entities
    assert "artifacts" in entities
    assert "concepts" in entities
    
    # Notes should be informative
    notes = parsed["notes"]
    assert len(notes) > 0
    assert any("session" in note.lower() for note in notes)


if __name__ == "__main__":
    # Run smoke test
    parsed = parse_campaign_history(SPELLJAMMER_HISTORY)
    
    print("=== PARSE TEST RESULTS ===\n")
    
    print(f"Sessions: {len(parsed['sessions'])}")
    for s in parsed['sessions']:
        print(f"  {s['date']} — Session {s['session_number']} — {s['title'][:50]}")
    
    print(f"\nCanon Summary: {len(parsed['canon_summary'])} bullets")
    for bullet in parsed['canon_summary'][:3]:
        print(f"  • {bullet[:80]}...")
    
    print(f"\nFactions: {len(parsed['factions'])}")
    for faction in parsed['factions']:
        print(f"  • {faction}")
    
    print(f"\nPlaces: {len(parsed['entities']['places'])}")
    for place in parsed['entities']['places']:
        print(f"  • {place}")
    
    print(f"\nFuture Sessions: {len(parsed.get('future_sessions', []))}")
    for future in parsed.get('future_sessions', []):
        print(f"  • {future['title']}")
    
    print(f"\nOpen Threads: {len(parsed.get('open_threads', []))}")
    for thread in parsed.get('open_threads', [])[:3]:
        print(f"  • {thread[:80]}...")
    
    print("\n✓ All assertions passed")
