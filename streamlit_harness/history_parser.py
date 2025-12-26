"""Campaign history parser for imports.

Version History:
- v0.2 (2025-12-25): Section-aware parsing with entity classification
- v0.1 (2025-12-25): Initial history parsing implementation

Provides section-aware parsing of structured campaign history documents into:
- Session entries with dates (from Campaign Ledger section only)
- Canon summary bullets (from Canon Summary section only)
- Faction extraction with entity classification
- Future sessions and open threads (separate buckets)
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


def split_by_sections(text: str) -> Dict[str, str]:
    """Split document by top-level markdown headings (##).
    
    Returns dict mapping section name -> section content.
    Preserves section ordering for later processing.
    """
    sections = {}
    
    # Split on ## headings
    parts = re.split(r'\n##\s+(.+?)\n', text)
    
    # First part is before any section (preamble/notes)
    if parts[0].strip():
        sections["_preamble"] = parts[0].strip()
    
    # Process section pairs (heading, content)
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            heading = parts[i].strip()
            content = parts[i + 1].strip()
            
            # Normalize heading for easier lookup
            key = heading.lower().replace('(', '').replace(')', '').strip()
            sections[key] = content
    
    return sections


def extract_canon_from_section(canon_section: str) -> List[str]:
    """Extract canon bullets from Canon Summary section.
    
    Compresses subsections into 8-12 key bullets.
    Ignores preamble, focuses on subsection content.
    """
    if not canon_section:
        return []
    
    bullets = []
    
    # Split by ### subsections
    subsections = re.split(r'\n###\s+(.+?)\n', canon_section)
    
    # Process each subsection
    for i in range(1, len(subsections), 2):
        if i + 1 < len(subsections):
            heading = subsections[i].strip()
            content = subsections[i + 1].strip()
            
            # Extract substantive sentences from content
            # Split on newlines first to handle bullet lists
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                
                # Skip empty lines and meta-notes
                if not line or line.startswith('#'):
                    continue
                
                # Remove leading bullets/dashes
                cleaned = re.sub(r'^[\-\*•]\s*', '', line)
                
                # Take substantive lines (>30 chars)
                if len(cleaned) > 30:
                    bullets.append(cleaned)
    
    # Limit to 12 bullets max
    return bullets[:12]


def parse_ledger_sessions(ledger_section: str) -> List[Dict[str, Any]]:
    """Parse sessions from Campaign Ledger section.
    
    Expected format:
    ### YYYY-MM-DD — Session N — Title
    - Bullet points...
    
    Returns list of sessions with actual dates and titles.
    """
    if not ledger_section:
        return []
    
    sessions = []
    
    # Pattern for session headers: ### YYYY-MM-DD — Session N — Title
    session_pattern = r'###\s+(\d{4}-\d{2}-\d{2})\s+[—–]\s+Session\s+(\d+)(?:\s+\(Current\))?\s+[—–]\s+(.+?)(?=\n###|\Z)'
    
    for match in re.finditer(session_pattern, ledger_section, re.DOTALL):
        date_str = match.group(1)
        session_num = int(match.group(2))
        title = match.group(3).strip()
        
        # Get content after title (everything until next ### or end)
        content_start = match.end(3)
        content_end = ledger_section.find('\n###', content_start)
        if content_end == -1:
            content_end = len(ledger_section)
        
        content = ledger_section[content_start:content_end].strip()
        
        sessions.append({
            "session_number": session_num,
            "date": date_str,
            "title": title,
            "content": content,
        })
    
    # Sort by date for consistency
    sessions.sort(key=lambda s: s["date"])
    
    return sessions


def classify_entities(text: str) -> Dict[str, List[str]]:
    """Classify capitalized entities as factions, places, artifacts, or concepts.
    
    Returns dict with:
    - factions: Organizations that act (Guilds, Pacts, Orders, etc.)
    - places: Locations (Cities, Citadels, Spheres)
    - artifacts: Named objects (Lenses, Rings, Devices)
    - concepts: Abstract powers (Incarnates, Seeds)
    """
    # Extract all capitalized phrases (2-3 words)
    entity_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b'
    matches = re.findall(entity_pattern, text)
    
    # Count frequency
    entity_counts = {}
    for match in matches:
        entity_counts[match] = entity_counts.get(match, 0) + 1
    
    # Only consider entities mentioned 2+ times
    frequent = {name: count for name, count in entity_counts.items() if count >= 2}
    
    # Classification patterns
    faction_keywords = [
        'pact', 'guild', 'order', 'watch', 'cult', 'consortium',
        'guardians', 'makers', 'council', 'alliance', 'league'
    ]
    
    place_keywords = [
        'citadel', 'city', 'fortress', 'bral', 'sphere', 'staircase',
        'tower', 'palace', 'keep', 'sanctum', 'archives', 'spires'
    ]
    
    artifact_keywords = [
        'lens', 'ring', 'device', 'crown', 'scepter', 'amulet',
        'orb', 'staff', 'sword', 'crystal'
    ]
    
    concept_keywords = [
        'incarnate', 'seed', 'essence', 'aspect', 'principle'
    ]
    
    # Classify each entity
    factions = []
    places = []
    artifacts = []
    concepts = []
    
    for entity in frequent.keys():
        entity_lower = entity.lower()
        
        # Check each category
        if any(kw in entity_lower for kw in faction_keywords):
            factions.append(entity)
        elif any(kw in entity_lower for kw in place_keywords):
            places.append(entity)
        elif any(kw in entity_lower for kw in artifact_keywords):
            artifacts.append(entity)
        elif any(kw in entity_lower for kw in concept_keywords):
            concepts.append(entity)
        # If no match, default to faction if it looks organizational
        elif entity.endswith('s') or ' of ' in entity_lower:
            # Plurals or "X of Y" patterns suggest groups
            factions.append(entity)
    
    return {
        "factions": sorted(set(factions)),
        "places": sorted(set(places)),
        "artifacts": sorted(set(artifacts)),
        "concepts": sorted(set(concepts)),
    }


def parse_future_sessions(future_section: str) -> List[Dict[str, str]]:
    """Parse future sessions from Future Sessions section.
    
    Returns list of future session dicts with:
    - title: Session title
    - notes: Description/expectations
    """
    if not future_section:
        return []
    
    future_sessions = []
    
    # Split by ### subsections (handle both \n### and start of string)
    subsections = re.split(r'(?:^|\n)###\s+(.+?)(?:\n|$)', future_section, flags=re.MULTILINE)
    
    for i in range(1, len(subsections), 2):
        if i + 1 < len(subsections):
            title = subsections[i].strip()
            content = subsections[i + 1].strip()
            
            # Only add if has substantive content
            if title and len(content) > 10:
                future_sessions.append({
                    "title": title,
                    "notes": content,
                })
    
    return future_sessions


def extract_open_threads(threads_section: str) -> List[str]:
    """Extract open threads from Open Threads section.
    
    Returns list of thread descriptions.
    """
    if not threads_section:
        return []
    
    threads = []
    
    # Split on bullet points or newlines
    lines = threads_section.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Remove leading bullets
        cleaned = re.sub(r'^[\-\*•]\s*', '', line)
        
        # Take substantive threads (>20 chars)
        if len(cleaned) > 20:
            threads.append(cleaned)
    
    return threads


def parse_campaign_history(text: str) -> Dict[str, Any]:
    """Parse structured campaign history into components.
    
    This parser is section-aware and respects document structure:
    1. Splits by top-level headings (##)
    2. Extracts content from appropriate sections only
    3. Classifies entities (factions vs places vs artifacts)
    
    Returns:
        Dictionary with:
        - sessions: List of session dicts (from Campaign Ledger)
        - canon_summary: List of bullets (from Canon Summary)
        - factions: List of faction names (classified)
        - entities: Dict of non-faction entities (places, artifacts, concepts)
        - future_sessions: List of planned sessions (from Future Sessions)
        - open_threads: List of thread descriptions (from Open Threads)
        - notes: Parsing notes/warnings
    """
    # Split into sections
    sections = split_by_sections(text)
    
    # Parse Canon Summary (only from Canon Summary section)
    canon_section_key = None
    for key in sections.keys():
        if 'canon summary' in key:
            canon_section_key = key
            break
    
    canon_summary = []
    if canon_section_key:
        canon_summary = extract_canon_from_section(sections[canon_section_key])
    
    # Parse Sessions (only from Campaign Ledger section)
    ledger_section_key = None
    for key in sections.keys():
        if 'campaign ledger' in key or 'sessionized history' in key:
            ledger_section_key = key
            break
    
    sessions = []
    if ledger_section_key:
        sessions = parse_ledger_sessions(sections[ledger_section_key])
    
    # Parse Future Sessions
    future_section_key = None
    for key in sections.keys():
        if 'future sessions' in key or 'future session' in key:
            future_section_key = key
            break
    
    future_sessions = []
    if future_section_key:
        future_sessions = parse_future_sessions(sections[future_section_key])
    
    # Parse Open Threads
    threads_section_key = None
    for key in sections.keys():
        if 'open threads' in key or 'next imports' in key:
            threads_section_key = key
            break
    
    open_threads = []
    if threads_section_key:
        open_threads = extract_open_threads(sections[threads_section_key])
    
    # Classify entities (use full text for detection, then classify)
    entities = classify_entities(text)
    
    # Build notes
    notes = []
    
    if not sessions:
        notes.append("⚠️ No sessions detected in Campaign Ledger section")
    else:
        notes.append(f"✓ Detected {len(sessions)} sessions from ledger")
    
    if not canon_summary:
        notes.append("⚠️ No canon summary extracted from Canon Summary section")
    else:
        notes.append(f"✓ Extracted {len(canon_summary)} canon bullets")
    
    if entities["factions"]:
        notes.append(f"✓ Classified {len(entities['factions'])} factions")
    
    if entities["places"] or entities["artifacts"] or entities["concepts"]:
        entity_count = len(entities["places"]) + len(entities["artifacts"]) + len(entities["concepts"])
        notes.append(f"ℹ️ Detected {entity_count} non-faction entities")
    
    if future_sessions:
        notes.append(f"ℹ️ Found {len(future_sessions)} future sessions (not added to ledger)")
    
    if open_threads:
        notes.append(f"ℹ️ Found {len(open_threads)} open threads (not added to canon)")
    
    return {
        "sessions": sessions,
        "canon_summary": canon_summary,
        "factions": entities["factions"],
        "entities": {
            "places": entities["places"],
            "artifacts": entities["artifacts"],
            "concepts": entities["concepts"],
        },
        "future_sessions": future_sessions,
        "open_threads": open_threads,
        "notes": notes,
    }
