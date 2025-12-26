"""Campaign history parser for imports.

Version History:
- v0.4 (2025-12-25): Markdown-it-py + dateparser + rapidfuzz integration [IN PROGRESS]
- v0.3 (2025-12-25): Ledger field separation, canon synthesis, faction cleanup
- v0.2 (2025-12-25): Section-aware parsing with entity classification
- v0.1 (2025-12-25): Initial history parsing implementation

Provides section-aware parsing of structured campaign history documents into:
- Session entries with dates (from Campaign Ledger section only)
- Canon summary bullets (from Canon Summary section only)
- Faction extraction with entity classification
- Future sessions and open threads (separate buckets)

v0.4 adds production-grade dependencies:
- markdown-it-py: Structured markdown token parsing (replaces regex)
- dateparser: Flexible date normalization
- rapidfuzz: Fuzzy string matching for deduplication
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Import new dependencies with graceful fallback
try:
    from markdown_it import MarkdownIt
    MARKDOWN_IT_AVAILABLE = True
except ImportError:
    MARKDOWN_IT_AVAILABLE = False

try:
    import dateparser
    DATEPARSER_AVAILABLE = True
except ImportError:
    DATEPARSER_AVAILABLE = False

try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False


def normalize_date(date_str: str) -> Optional[str]:
    """Normalize date string to ISO YYYY-MM-DD format using dateparser.
    
    Returns None if date cannot be parsed.
    """
    if not DATEPARSER_AVAILABLE:
        # Fallback: try ISO format only
        if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
            return date_str
        return None
    
    try:
        parsed = dateparser.parse(date_str)
        if parsed:
            return parsed.strftime('%Y-%m-%d')
    except Exception:
        pass
    
    return None


def fuzzy_dedupe_entities(names: List[str], threshold: int = 85) -> List[str]:
    """Deduplicate entity names using fuzzy matching with rapidfuzz.
    
    Handles:
    - "The Solstice Pact" vs "Solstice Pact"
    - Case variations
    - Near-duplicates
    
    Returns deduplicated list, keeping best variant.
    """
    if not RAPIDFUZZ_AVAILABLE or not names:
        # Fallback: simple normalization
        return _simple_dedupe(names)
    
    # Normalize: strip "The " and lowercase for comparison
    normalized_map = {}
    for name in names:
        normalized = re.sub(r'^The\s+', '', name, flags=re.IGNORECASE).lower()
        if normalized not in normalized_map:
            normalized_map[normalized] = []
        normalized_map[normalized].append(name)
    
    # For each cluster, keep variant without "The " if available
    result = []
    for variants in normalized_map.values():
        without_the = [v for v in variants if not v.startswith('The ')]
        if without_the:
            result.append(without_the[0])
        else:
            result.append(variants[0])
    
    # Use rapidfuzz to catch near-duplicates across clusters
    if len(result) > 1:
        seen = set()
        final = []
        for name in sorted(result):  # Sort for determinism
            if name in seen:
                continue
            
            # Check if similar to any already added
            matches = process.extract(name, final, scorer=fuzz.ratio, limit=1)
            if matches and matches[0][1] >= threshold:
                seen.add(name)  # Too similar, skip
                continue
            
            final.append(name)
            seen.add(name)
        
        return sorted(final)
    
    return sorted(result)


def _simple_dedupe(names: List[str]) -> List[str]:
    """Fallback deduplication without rapidfuzz."""
    seen = {}
    for name in names:
        normalized = re.sub(r'^The\s+', '', name, flags=re.IGNORECASE)
        key = normalized.lower()
        if key not in seen:
            seen[key] = normalized
    return sorted(seen.values())


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
    
    Synthesizes structured bullets by subsection:
    - Premise: 1-2 bullets (vibe + myth-arc)
    - Player Characters: 1 bullet (collapsed roster)
    - Key NPCs/Powers: 2-3 bullets
    - Major Artifacts: 2-3 bullets  
    - Current Situation: 1-2 bullets
    
    Total target: 8-12 bullets
    """
    if not canon_section:
        return []
    
    bullets = []
    
    # Split by ### subsections
    subsections = re.split(r'\n###\s+(.+?)\n', canon_section)
    
    # Track subsections for structured synthesis
    subsection_content = {}
    for i in range(1, len(subsections), 2):
        if i + 1 < len(subsections):
            heading = subsections[i].strip().lower()
            content = subsections[i + 1].strip()
            subsection_content[heading] = content
    
    # Helper to find subsection by partial key match
    def find_subsection(keywords: List[str]) -> Optional[str]:
        for key in subsection_content.keys():
            if any(kw in key for kw in keywords):
                return subsection_content[key]
        return None
    
    # Premise: 1-2 bullets (combine vibe + myth-arc)
    premise_content = find_subsection(['premise'])
    if premise_content:
        lines = [l.strip() for l in premise_content.split('\n') if l.strip() and len(l.strip()) > 30]
        bullets.extend([re.sub(r'^[\-\*•]\s*', '', l) for l in lines[:2]])
    
    # Player Characters: 1 bullet (collapsed)
    pc_content = find_subsection(['player character'])
    if pc_content:
        # Just note that there's a party, don't enumerate
        bullets.append("Party roster established (see full history for PC details)")
    
    # Key NPCs/Powers: 2-3 bullets
    npc_content = find_subsection(['npc', 'powers in play'])
    if npc_content:
        lines = [l.strip() for l in npc_content.split('\n') if l.strip() and len(l.strip()) > 30]
        bullets.extend([re.sub(r'^[\-\*•]\s*', '', l) for l in lines[:3]])
    
    # Major Artifacts: 2-3 bullets
    artifact_content = find_subsection(['artifact', 'mysteries'])
    if artifact_content:
        lines = [l.strip() for l in artifact_content.split('\n') if l.strip() and len(l.strip()) > 30]
        bullets.extend([re.sub(r'^[\-\*•]\s*', '', l) for l in lines[:3]])
    
    # Cosmology: 0-1 bullets (if present and significant)
    cosmology_content = find_subsection(['cosmology', 'backbone'])
    if cosmology_content:
        lines = [l.strip() for l in cosmology_content.split('\n') if l.strip() and len(l.strip()) > 30]
        if lines:
            bullets.append(re.sub(r'^[\-\*•]\s*', '', lines[0]))
    
    # Current Situation: 1-2 bullets
    situation_content = find_subsection(['current situation'])
    if situation_content:
        lines = [l.strip() for l in situation_content.split('\n') if l.strip() and len(l.strip()) > 30]
        bullets.extend([re.sub(r'^[\-\*•]\s*', '', l) for l in lines[:2]])
    
    # Limit to 12 bullets max
    return bullets[:12]


def parse_ledger_sessions(ledger_section: str) -> List[Dict[str, Any]]:
    """Parse sessions from Campaign Ledger section.
    
    Expected format:
    ### YYYY-MM-DD — Session N — Title
    - Bullet points...
    
    Returns list of sessions with actual dates, clean titles, and bullets.
    Uses dateparser for flexible date normalization.
    """
    if not ledger_section:
        return []
    
    sessions = []
    
    # Pattern for session headers: ### YYYY-MM-DD — Session N — Title
    session_pattern = r'###\s+(\d{4}-\d{2}-\d{2})\s+[—–]\s+Session\s+(\d+)(?:\s+\(Current\))?\s+[—–]\s+([^\n]+)'
    
    for match in re.finditer(session_pattern, ledger_section):
        date_str = match.group(1)
        session_num = int(match.group(2))
        title = match.group(3).strip()
        
        # Normalize date with dateparser
        normalized_date = normalize_date(date_str)
        if not normalized_date:
            normalized_date = date_str  # Keep original if normalization fails
        
        # Get content after header line (everything until next ### or end)
        content_start = match.end()
        content_end = ledger_section.find('\n###', content_start)
        if content_end == -1:
            content_end = len(ledger_section)
        
        raw_content = ledger_section[content_start:content_end].strip()
        
        # Extract bullet points from content
        bullets = []
        lines = raw_content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line starts with bullet marker
            if re.match(r'^[\-\*•]\s+', line):
                # Remove bullet marker
                bullet_text = re.sub(r'^[\-\*•]\s+', '', line)
                bullets.append(bullet_text)
            elif bullets:
                # Continuation of previous bullet (multi-line)
                bullets[-1] += " " + line
        
        sessions.append({
            "session_number": session_num,
            "date": normalized_date,  # Normalized via dateparser
            "title": title,  # Clean title only
            "bullets": bullets,  # Structured bullet list
            "content": raw_content,  # Raw text for reference
        })
    
    # Sort by date for consistency
    sessions.sort(key=lambda s: s["date"])
    
    return sessions


def extract_artifacts_from_section(artifacts_section: str) -> List[str]:
    """Extract artifact names from Major Artifacts section.
    
    Looks for patterns like:
    - The Chronolens: description
    - Bryannas's Ring: description
    - Infernal Device of...: description
    """
    if not artifacts_section:
        return []
    
    artifacts = []
    
    # Pattern 1: "The X:" or "X's Y:"
    pattern1 = r'(?:The\s+)?([A-Z][a-z]+(?:\'s\s+[A-Z][a-z]+)?(?:\s+[A-Z][a-z]+)*):'
    for match in re.finditer(pattern1, artifacts_section):
        artifact_name = match.group(1).strip()
        # Remove leading "The " if present
        artifact_name = re.sub(r'^The\s+', '', artifact_name)
        artifacts.append(artifact_name)
    
    # Pattern 2: "Device of X" or "X of Y"
    pattern2 = r'((?:Device|Ring|Crown|Staff|Sword|Orb)\s+of\s+[A-Z][a-z]+(?:\s+[a-z]+)?(?:\s+[A-Z][a-z]+)?)'
    for match in re.finditer(pattern2, artifacts_section):
        artifacts.append(match.group(1).strip())
    
    return list(set(artifacts))  # Deduplicate


def classify_entities(text: str, canon_section: Optional[str] = None) -> Dict[str, List[str]]:
    """Classify capitalized entities as factions, places, artifacts, or concepts.
    
    Args:
        text: Full text for entity detection
        canon_section: Canon Summary section for artifact extraction
    
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
    
    # Filter out section headers and meta terms
    section_headers = ['Future Sessions', 'Open Threads', 'Campaign Ledger', 'Canon Summary']
    arc_markers = ['Spiral', 'Projected', 'Expected']
    
    filtered = {}
    for name, count in frequent.items():
        # Skip section headers
        if name in section_headers:
            continue
        # Skip arc titles
        if any(marker in name for marker in arc_markers):
            continue
        filtered[name] = count
    
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
    
    for entity in filtered.keys():
        entity_lower = entity.lower()
        
        # Normalize: strip leading "The "
        normalized = re.sub(r'^The\s+', '', entity)
        
        # Check each category
        if any(kw in entity_lower for kw in faction_keywords):
            factions.append(normalized)
        elif any(kw in entity_lower for kw in place_keywords):
            places.append(normalized)
        elif any(kw in entity_lower for kw in artifact_keywords):
            artifacts.append(normalized)
        elif any(kw in entity_lower for kw in concept_keywords):
            concepts.append(normalized)
        # If no match, default to faction if it looks organizational
        elif entity.endswith('s') or ' of ' in entity_lower:
            # Plurals or "X of Y" patterns suggest groups
            factions.append(normalized)
    
    # Extract artifacts from Major Artifacts section if available
    if canon_section:
        sections = split_by_sections(text)
        canon_key = next((k for k in sections.keys() if 'canon summary' in k), None)
        if canon_key:
            artifact_key = None
            # Check for Major Artifacts subsection
            subsections = re.split(r'\n###\s+(.+?)\n', sections[canon_key])
            for i in range(1, len(subsections), 2):
                if i + 1 < len(subsections):
                    heading = subsections[i].strip().lower()
                    if 'artifact' in heading or 'mysteries' in heading:
                        artifact_section = subsections[i + 1]
                        extracted = extract_artifacts_from_section(artifact_section)
                        artifacts.extend(extracted)
                        break
    
    # Apply fuzzy deduplication using rapidfuzz
    return {
        "factions": fuzzy_dedupe_entities(factions),
        "places": fuzzy_dedupe_entities(places),
        "artifacts": fuzzy_dedupe_entities(artifacts),
        "concepts": fuzzy_dedupe_entities(concepts),
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
    
    # Classify entities (use full text for detection, pass canon section for artifacts)
    canon_section_text = sections.get(canon_section_key, "") if canon_section_key else None
    entities = classify_entities(text, canon_section=canon_section_text)
    
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
