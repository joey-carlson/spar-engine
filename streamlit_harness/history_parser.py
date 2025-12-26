"""Campaign history parser for imports.

Version History:
- v0.5 (2025-12-25): Additive fallbacks for unstructured notes
- v0.4 (2025-12-25): Markdown-it-py + dateparser + rapidfuzz integration COMPLETE
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

v0.5 adds conservative fallbacks for unstructured notes:
- Unstructured date-based session detection
- Relaxed session header patterns (Game/Day/Episode/Part)
- Paragraph-based canon extraction
- Only activates when structured parsing yields insufficient results
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
    
    Uses markdown-it-py for robust structure parsing (handles heading variants).
    Falls back to regex if markdown-it-py unavailable.
    
    Returns dict mapping section name -> section content.
    Preserves section ordering for later processing.
    """
    if MARKDOWN_IT_AVAILABLE:
        return _markdown_it_split_sections(text)
    else:
        return _regex_split_sections(text)


def _markdown_it_split_sections(text: str) -> Dict[str, str]:
    """Split sections using markdown-it-py token parsing.
    
    Handles heading variants like "Canon Summary (Expanded)" robustly.
    Uses line mapping to extract original text directly.
    """
    md = MarkdownIt()
    tokens = md.parse(text)
    
    # Split text into lines for mapping
    text_lines = text.split('\n')
    
    sections = {}
    section_boundaries = []  # (heading, start_line, end_line)
    
    # Find all h2 headings and their line positions
    for i, token in enumerate(tokens):
        if token.type == 'heading_open' and token.tag == 'h2':
            # Get heading text from next inline token
            if i + 1 < len(tokens) and tokens[i + 1].type == 'inline':
                heading_text = tokens[i + 1].content.strip()
                
                # Normalize: remove (parens), lowercase
                normalized = heading_text.lower()
                normalized = re.sub(r'\s*\([^)]*\)\s*', '', normalized)
                normalized = normalized.strip()
                
                # Get line number from token map (0-indexed)
                if token.map:
                    start_line = token.map[0]
                    section_boundaries.append((normalized, start_line))
    
    # Extract content between section boundaries
    if not section_boundaries:
        # No h2 headings found, entire text is preamble
        sections["_preamble"] = text.strip()
        return sections
    
    # Preamble: before first h2
    if section_boundaries[0][1] > 0:
        preamble_lines = text_lines[:section_boundaries[0][1]]
        sections["_preamble"] = '\n'.join(preamble_lines).strip()
    
    # Extract each section's content
    for idx, (heading, start_line) in enumerate(section_boundaries):
        # Content starts after heading line
        content_start = start_line + 1
        
        # Content ends at next heading or end of document
        if idx + 1 < len(section_boundaries):
            content_end = section_boundaries[idx + 1][1]
        else:
            content_end = len(text_lines)
        
        # Extract lines
        content_lines = text_lines[content_start:content_end]
        sections[heading] = '\n'.join(content_lines).strip()
    
    return sections


def _regex_split_sections(text: str) -> Dict[str, str]:
    """Fallback regex-based section splitting."""
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
    
    # Vibe/Premise/Pitch: 1-2 bullets
    premise_content = find_subsection(['vibe', 'premise', 'pitch', 'one-sentence'])
    if premise_content:
        lines = [l.strip() for l in premise_content.split('\n') if l.strip() and len(l.strip()) > 30]
        bullets.extend([re.sub(r'^[\-\*•]\s*', '', l) for l in lines[:2]])
    
    # Core Themes: 1-2 bullets (if present in Campaign Overview format)
    themes_content = find_subsection(['core themes', 'theme'])
    if themes_content:
        lines = [l.strip() for l in themes_content.split('\n') if l.strip() and len(l.strip()) > 30]
        bullets.extend([re.sub(r'^[\-\*•]\s*', '', l) for l in lines[:2]])
    
    # Genre/Tone: 0-1 bullets (if present)
    genre_content = find_subsection(['genre', 'tone'])
    if genre_content:
        lines = [l.strip() for l in genre_content.split('\n') if l.strip() and len(l.strip()) > 30]
        if lines:
            bullets.append(re.sub(r'^[\-\*•]\s*', '', lines[0]))
    
    # Big Engine/Myth-arc/Long-haul problem: 1 bullet
    engine_content = find_subsection(['engine', 'myth-arc', 'myth arc', 'long-haul problem', 'long-haul'])
    if engine_content:
        lines = [l.strip() for l in engine_content.split('\n') if l.strip() and len(l.strip()) > 30]
        if lines:
            bullets.append(re.sub(r'^[\-\*•]\s*', '', lines[0]))
    
    # Player Characters / Party: 1 bullet (collapsed)
    pc_content = find_subsection(['player character', 'the party', 'party'])
    if pc_content:
        bullets.append("Party roster established (see full history for PC details)")
    
    # Major antagonists: 1-2 bullets
    antagonist_content = find_subsection(['antagonist', 'villain', 'threat'])
    if antagonist_content:
        lines = [l.strip() for l in antagonist_content.split('\n') if l.strip() and len(l.strip()) > 30]
        bullets.extend([re.sub(r'^[\-\*•]\s*', '', l) for l in lines[:2]])
    
    # Allied forces: 1 bullet
    ally_content = find_subsection(['allied forces', 'allies', 'major allied'])
    if ally_content:
        lines = [l.strip() for l in ally_content.split('\n') if l.strip() and len(l.strip()) > 30]
        if lines:
            bullets.append(re.sub(r'^[\-\*•]\s*', '', lines[0]))
    
    # Key NPCs/Powers/Guardians/Temporal entities: 2-3 bullets
    npc_content = find_subsection(['npc', 'powers in play', 'guardians', 'temporal', 'solstice', 'makers'])
    if npc_content:
        lines = [l.strip() for l in npc_content.split('\n') if l.strip() and len(l.strip()) > 30]
        bullets.extend([re.sub(r'^[\-\*•]\s*', '', l) for l in lines[:3]])
    
    # Major Artifacts: 2-3 bullets
    artifact_content = find_subsection(['artifact', 'mysteries', 'chronolens', 'component'])
    if artifact_content:
        lines = [l.strip() for l in artifact_content.split('\n') if l.strip() and len(l.strip()) > 30]
        bullets.extend([re.sub(r'^[\-\*•]\s*', '', l) for l in lines[:3]])
    
    # Cosmology/Backdrop: 0-1 bullets (if present)
    cosmology_content = find_subsection(['cosmology', 'backbone', 'frame twist', 'campaign frame'])
    if cosmology_content:
        lines = [l.strip() for l in cosmology_content.split('\n') if l.strip() and len(l.strip()) > 30]
        if lines:
            bullets.append(re.sub(r'^[\-\*•]\s*', '', lines[0]))
    
    # Current Situation/State: 1-2 bullets
    situation_content = find_subsection(['current situation', 'current state', 'state of play'])
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
    
    # Pattern 2: Addendum entries
    addendum_pattern = r'###\s+(\d{4}-\d{2}-\d{2})\s+[—–]\s+Addendum(?:\s+\([^)]+\))?\s+[—–]\s+([^\n]+)'
    
    for match in re.finditer(addendum_pattern, ledger_section):
        date_str = match.group(1)
        title = match.group(2).strip()
        
        # Normalize date with dateparser
        normalized_date = normalize_date(date_str)
        if not normalized_date:
            normalized_date = date_str
        
        # Get content after header
        content_start = match.end()
        content_end = ledger_section.find('\n###', content_start)
        if content_end == -1:
            content_end = len(ledger_section)
        
        raw_content = ledger_section[content_start:content_end].strip()
        
        # Extract bullets
        bullets = []
        lines = raw_content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if re.match(r'^[\-\*•]\s+', line):
                bullet_text = re.sub(r'^[\-\*•]\s+', '', line)
                bullets.append(bullet_text)
            elif bullets:
                bullets[-1] += " " + line
        
        sessions.append({
            "session_number": None,  # Addendums don't have session numbers
            "date": normalized_date,
            "title": title,
            "bullets": bullets,
            "content": raw_content,
        })
    
    # Sort by date for consistency
    sessions.sort(key=lambda s: s["date"])
    
    return sessions


def extract_artifacts_from_section(artifacts_section: str) -> List[str]:
    """Extract artifact names from Major Artifacts section.
    
    Looks for patterns like:
    - The Chronolens: description
    - Bryannas's Ring: description (double possessive)
    - Control lever / rod (compound with slash)
    - Infernal Device of Lum the Mad: description
    """
    if not artifacts_section:
        return []
    
    artifacts = []
    
    # Pattern 1: Possessives including double-s forms: "Bryannas's Ring"
    pattern1 = r'([A-Z][a-z]+\'s(?:s)?\s+(?:Ring|Device|Crown|Staff|Sword|Orb|[A-Z][a-z]+))'
    for match in re.finditer(pattern1, artifacts_section):
        artifacts.append(match.group(1).strip())
    
    # Pattern 2: "The X:" format
    pattern2 = r'The\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*):'
    for match in re.finditer(pattern2, artifacts_section):
        artifacts.append(match.group(1).strip())
    
    # Pattern 3: "Infernal Device of X" - complex "of" phrases
    pattern3 = r'((?:Infernal\s+)?Device\s+of\s+[A-Z][a-z]+(?:\s+[a-z]+)?(?:\s+[A-Z][a-z]+)?)'
    for match in re.finditer(pattern3, artifacts_section, re.IGNORECASE):
        artifacts.append(match.group(1).strip())
    
    # Pattern 4: Compound forms with slashes: "Control lever / rod"
    pattern4 = r'(Control\s+(?:lever|rod)(?:\s*/\s*(?:lever|rod))?)'
    for match in re.finditer(pattern4, artifacts_section, re.IGNORECASE):
        # Normalize: "Control lever / rod" → "Control lever"
        normalized = match.group(1).replace(' / ', ' ').strip()
        artifacts.append(normalized)
    
    # Pattern 5: Specific artifact names mentioned in text
    specific_artifacts = ['Chronal Prism', 'Chronolens']
    for artifact in specific_artifacts:
        if artifact in artifacts_section:
            artifacts.append(artifact)
    
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
    section_headers = ['Future Sessions', 'Open Threads', 'Campaign Ledger', 'Canon Summary', 'Parser Index', 'Key Entities']
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
    
    # Add explicit Astral Elves detection if context suggests faction
    if 'Astral Elves' not in filtered and 'Astral Elf' in text:
        # Check if mentioned in faction context
        if any(term in text for term in ['Astral Elf forces', 'Astral Elf splinter', 'Astral Elven']):
            filtered['Astral Elves'] = 1  # Add with minimum frequency
    
    # Classification patterns
    faction_keywords = [
        'pact', 'guild', 'order', 'watch', 'cult', 'consortium',
        'guardians', 'makers', 'council', 'alliance', 'league', 'gang'
    ]
    
    # Hard demoters: if entity contains these, force to places
    place_demoters = [
        'tunnels', 'citadel', 'staircase', 'archives', 'sphere',
        'chamber', 'fortress', 'ship', 'city'
    ]
    
    place_keywords = [
        'citadel', 'city', 'fortress', 'bral', 'sphere', 'staircase',
        'tower', 'palace', 'keep', 'sanctum', 'archives', 'spires',
        'tunnels', 'chamber', 'ruins'
    ]
    
    artifact_keywords = [
        'lens', 'ring', 'device', 'crown', 'scepter', 'amulet',
        'orb', 'staff', 'sword', 'crystal', 'prism', 'lever', 'rod'
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
        
        # HARD DEMOTION: Force to places if contains place demoters
        if any(demoter in entity_lower for demoter in place_demoters):
            places.append(normalized)
            continue
        
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


def detect_unstructured_sessions(text: str) -> List[Dict[str, Any]]:
    """Fallback: detect sessions from unstructured text using date patterns.
    
    Scans for date patterns anywhere in text. When found, treats following
    content as session until next date or major break.
    
    Only used when structured parsing yields no sessions.
    """
    sessions = []
    
    # Pattern: ISO dates or common formats
    # Look for dates at start of lines or after markers
    date_pattern = r'(?:^|\n)(?:\*\*)?(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}|\w+ \d{1,2},? \d{4})'
    
    lines = text.split('\n')
    date_positions = []
    
    for i, line in enumerate(lines):
        match = re.search(date_pattern, line)
        if match:
            date_str = match.group(1)
            normalized = normalize_date(date_str)
            if normalized:
                date_positions.append((i, normalized, line))
    
    # Create sessions from date blocks
    for idx, (line_num, date, date_line) in enumerate(date_positions):
        # Extract title: first sentence after date, or use date line content
        title_match = re.search(r'(?:Session \d+|Game \d+|Day \d+)?\s*[—–:]?\s*([^:\n]{10,80})', date_line)
        title = title_match.group(1).strip() if title_match else "Imported Session"
        
        # Determine content range
        start_line = line_num + 1
        end_line = date_positions[idx + 1][0] if idx + 1 < len(date_positions) else len(lines)
        
        # Extract content
        content_lines = lines[start_line:end_line]
        content = '\n'.join(content_lines).strip()
        
        # Extract bullets if present
        bullets = []
        for line in content_lines:
            line = line.strip()
            if re.match(r'^[\-\*•]\s+', line):
                bullets.append(re.sub(r'^[\-\*•]\s+', '', line))
        
        # Only add if has substantive content (>50 chars)
        if len(content) > 50:
            sessions.append({
                "session_number": None,
                "date": date,
                "title": title[:80],  # Cap length
                "bullets": bullets if bullets else [],
                "content": content[:500],  # Cap for storage
            })
    
    return sessions


def detect_relaxed_session_headers(text: str) -> List[Dict[str, Any]]:
    """Fallback: detect sessions from relaxed header patterns.
    
    Supports: "Game 5", "Day 1", "Episode 3", "Part II"
    Only counts as session if followed by 2+ substantive lines.
    
    Only used when date-based detection yields no sessions.
    """
    sessions = []
    
    # Pattern: Game/Day/Episode/Part + number
    header_pattern = r'(?:^|\n)((?:Game|Day|Episode|Part|Session)\s+(?:\d+|I+|[IVX]+))(?:\s*[—–:]\s*([^\n]{0,80}))?'
    
    lines = text.split('\n')
    
    for match in re.finditer(header_pattern, text, re.IGNORECASE):
        header = match.group(1)
        title_suffix = match.group(2) if match.group(2) else ""
        
        # Find position in text
        pos = match.start()
        line_num = text[:pos].count('\n')
        
        # Check if followed by substantive content
        following_lines = lines[line_num + 1:line_num + 10]
        substantive = [l.strip() for l in following_lines if len(l.strip()) > 20]
        
        # Require at least 2 substantive lines to avoid false positives
        if len(substantive) >= 2:
            title = f"{header} {title_suffix}".strip()
            
            # Extract content until next header or end
            content_lines = []
            for i in range(line_num + 1, min(line_num + 50, len(lines))):
                line = lines[i].strip()
                if re.match(header_pattern, line, re.IGNORECASE):
                    break
                if line:
                    content_lines.append(line)
            
            content = '\n'.join(content_lines[:20])  # Cap at 20 lines
            
            sessions.append({
                "session_number": None,
                "date": "Unknown",
                "title": title[:80],
                "bullets": [],
                "content": content,
            })
    
    return sessions


def extract_paragraph_canon(text: str, min_bullets: int = 4) -> List[str]:
    """Fallback: extract canon bullets from opening paragraphs.
    
    Converts first 5-10 sentences into bullet points.
    Only used when structured extraction yields < min_bullets.
    """
    bullets = []
    
    # Get first 3-5 paragraphs (up to 2000 chars)
    paragraphs = text.split('\n\n')
    opening_text = '\n\n'.join(paragraphs[:5])[:2000]
    
    # Split into sentences
    sentences = re.split(r'[.!?]+\s+', opening_text)
    
    for sentence in sentences[:10]:
        sentence = sentence.strip()
        
        # Skip short sentences, headers, meta text
        if len(sentence) < 30:
            continue
        if sentence.startswith('#'):
            continue
        if any(skip in sentence.lower() for skip in ['import', 'use:', 'notes for']):
            continue
        
        # Clean and cap length
        cleaned = sentence[:160]
        if len(cleaned) >= 40:  # Minimum substance
            bullets.append(cleaned)
        
        if len(bullets) >= min_bullets:
            break
    
    # Dedupe with rapidfuzz if available
    if RAPIDFUZZ_AVAILABLE and len(bullets) > 1:
        final = []
        for bullet in bullets:
            # Check similarity to already added
            if not final:
                final.append(bullet)
                continue
            
            matches = process.extract(bullet, final, scorer=fuzz.ratio, limit=1)
            if not matches or matches[0][1] < 80:  # Different enough
                final.append(bullet)
        
        return final[:min_bullets]
    
    return bullets[:min_bullets]


def extract_from_parser_index(text: str) -> Optional[Dict[str, List[str]]]:
    """Extract entities from Parser-Friendly Index section if present.
    
    Looks for sections containing "Parser-Friendly Index" or similar.
    Parses structured lists under category headings like:
    - Artifacts:
    - Groups:
    - Places:
    
    Returns dict with extracted categories, or None if no index found.
    Flexible enough to handle various user formats.
    """
    sections = split_by_sections(text)
    
    # Look for index section (flexible matching)
    index_key = None
    for key in sections.keys():
        if 'parser' in key and 'index' in key:
            index_key = key
            break
        if 'key entities' in key:
            index_key = key
            break
    
    if not index_key:
        return None
    
    index_section = sections[index_key]
    result = {
        "factions": [],
        "places": [],
        "artifacts": [],
        "concepts": [],
    }
    
    # Parse category blocks
    # Look for patterns like "Artifacts:" or "Groups:" followed by bullet lists
    category_pattern = r'(Artifacts?|Groups?|Factions?|Places?|Concepts?|Powers?):\s*\n((?:[\-\*•]\s*.+\n?)+)'
    
    for match in re.finditer(category_pattern, index_section, re.IGNORECASE | re.MULTILINE):
        category = match.group(1).lower().rstrip('s')  # Normalize to singular
        items_block = match.group(2)
        
        # Extract items from bullet list
        items = []
        for line in items_block.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Remove bullet marker
            cleaned = re.sub(r'^[\-\*•]\s*', '', line)
            
            # Handle parenthetical notes: "Chronolens (Chronosphere, legacy term)"
            # Keep main name, strip notes
            main_name = re.split(r'\s*\(', cleaned)[0].strip()
            
            if main_name:
                items.append(main_name)
        
        # Map category to result keys
        if category in ['group', 'faction']:
            result["factions"].extend(items)
        elif category == 'place':
            result["places"].extend(items)
        elif category == 'artifact':
            result["artifacts"].extend(items)
        elif category in ['concept', 'power']:
            result["concepts"].extend(items)
    
    # Return None if no categories found
    if not any(result.values()):
        return None
    
    return result


def parse_campaign_history(text: str, campaign_id: Optional[str] = None) -> Dict[str, Any]:
    """Parse structured campaign history into components.
    
    This parser is section-aware and respects document structure:
    1. Splits by top-level headings (##)
    2. Extracts content from appropriate sections only
    3. Classifies entities (factions vs places vs artifacts)
    4. Applies per-campaign import overrides if campaign_id provided
    
    Args:
        text: Campaign history markdown text
        campaign_id: Optional campaign ID for loading import overrides
    
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
    
    # Parse Canon Summary (flexible section matching)
    # Try standard names first, then synonyms
    canon_section_key = None
    canon_synonyms = ['canon summary', 'campaign overview', 'campaign bible']
    for synonym in canon_synonyms:
        for key in sections.keys():
            if synonym in key:
                canon_section_key = key
                break
        if canon_section_key:
            break
    
    canon_summary = []
    canon_source = None
    if canon_section_key:
        canon_summary = extract_canon_from_section(sections[canon_section_key])
        # Record which section was used
        if 'canon summary' in canon_section_key:
            canon_source = "Canon Summary"
        elif 'campaign overview' in canon_section_key:
            canon_source = "Campaign Overview"
        elif 'campaign bible' in canon_section_key:
            canon_source = "Campaign Bible"
    
    # Parse Sessions (flexible section matching)
    # Try standard names first, then synonyms
    ledger_section_key = None
    ledger_synonyms = ['campaign ledger', 'sessionized history', 'session log', 'session journal']
    for synonym in ledger_synonyms:
        for key in sections.keys():
            if synonym in key:
                ledger_section_key = key
                break
        if ledger_section_key:
            break
    
    sessions = []
    ledger_source = None
    if ledger_section_key:
        sessions = parse_ledger_sessions(sections[ledger_section_key])
        # Record which section was used
        if 'campaign ledger' in ledger_section_key:
            ledger_source = "Campaign Ledger"
        elif 'session log' in ledger_section_key:
            ledger_source = "Session Log"
        elif 'session journal' in ledger_section_key:
            ledger_source = "Session Journal"
    
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
    
    # v0.5 FALLBACK TRIGGER: Check if structured parsing yielded insufficient results
    needs_session_fallback = len(sessions) == 0 and (not canon_section_key and not ledger_section_key)
    needs_canon_fallback = len(canon_summary) < 4
    
    fallback_notes = []
    
    # Fallback Layer 1: Unstructured date-based session detection
    if needs_session_fallback:
        unstructured_sessions = detect_unstructured_sessions(text)
        if unstructured_sessions:
            sessions = unstructured_sessions
            ledger_source = "Unstructured (date-based)"
            fallback_notes.append("🔄 Fallback: unstructured session detection")
    
    # Fallback Layer 2: Relaxed session headers (if still no sessions)
    if len(sessions) == 0:
        relaxed_sessions = detect_relaxed_session_headers(text)
        if relaxed_sessions:
            sessions = relaxed_sessions
            ledger_source = "Relaxed headers"
            fallback_notes.append("🔄 Fallback: relaxed session headers")
    
    # Fallback Layer 3: Paragraph-based canon extraction
    if needs_canon_fallback:
        paragraph_canon = extract_paragraph_canon(text, min_bullets=4)
        if paragraph_canon:
            canon_summary = paragraph_canon
            canon_source = "Opening paragraphs"
            fallback_notes.append("🔄 Fallback: paragraph canon extraction")
    
    # Try to extract from Parser-Friendly Index first (high confidence)
    index_entities = extract_from_parser_index(text)
    
    if index_entities:
        # Index found - use it as primary source
        entities = index_entities
        notes_prefix = "📋 Using Parser-Friendly Index"
    else:
        # Fall back to heuristic classification
        canon_section_text = sections.get(canon_section_key, "") if canon_section_key else None
        entities = classify_entities(text, canon_section=canon_section_text)
        notes_prefix = "🔍 Using heuristic classification"
    
    # Build initial result
    result = {
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
    }
    
    # Apply import overrides if campaign_id provided
    if campaign_id:
        from streamlit_harness.import_overrides import ImportOverrides
        overrides = ImportOverrides.load(campaign_id)
        result = overrides.apply_to_parsed(result)
    
    # Build notes
    notes = [notes_prefix]  # Add source indicator first
    
    # Add fallback indicators if any were used
    notes.extend(fallback_notes)
    
    # Add section source indicators
    if canon_source:
        notes.append(f"📖 Canon from: {canon_source}")
    if ledger_source:
        notes.append(f"📅 Sessions from: {ledger_source}")
    
    if not sessions:
        notes.append("⚠️ No sessions detected")
    else:
        notes.append(f"✓ Detected {len(sessions)} sessions")
    
    if not canon_summary:
        notes.append("⚠️ No canon summary extracted")
    else:
        notes.append(f"✓ Extracted {len(canon_summary)} canon bullets")
    
    if result["factions"]:
        notes.append(f"✓ Classified {len(result['factions'])} factions")
    
    entities_result = result["entities"]
    if entities_result["places"] or entities_result["artifacts"] or entities_result["concepts"]:
        entity_count = len(entities_result["places"]) + len(entities_result["artifacts"]) + len(entities_result["concepts"])
        notes.append(f"ℹ️ Detected {entity_count} non-faction entities")
    
    if future_sessions:
        notes.append(f"ℹ️ Found {len(future_sessions)} future sessions (not added to ledger)")
    
    if open_threads:
        notes.append(f"ℹ️ Found {len(open_threads)} open threads (not added to canon)")
    
    if campaign_id:
        notes.append("ℹ️ Import overrides applied (if any)")
    
    result["notes"] = notes
    return result
