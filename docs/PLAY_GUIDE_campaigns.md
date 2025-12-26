# Campaign Play Guide v0.1

**Last Updated**: 2025-12-25  
**Status**: Active

## What Are Campaigns?

Campaigns in SPAR Tool Engine are persistent world-state tracking systems that capture long-term consequences across multiple sessions. They transform one-shot complications into evolving narrative arcs.

### Why Use Campaigns?

**Without Campaigns:**
- Each session starts fresh
- No memory of past consequences
- Complications feel isolated
- Missing long-term pressure

**With Campaigns:**
- Consequences accumulate over time
- Past sessions influence future events
- Structured scars track lasting injuries
- Factions remember interactions
- Pressure and heat create narrative momentum

## Getting Started

### Creating Your First Campaign

1. Launch the Event Generator
2. Click **"Campaign Mode ⚡"** in the sidebar (collapsed by default)
3. On the landing page, click **"+ New Campaign"**
4. Enter campaign details:
   - **Name**: e.g., "The Wasteland Run"
   - **Initial Pressure**: 0-10 (start at 0-2 for gradual buildup)
   - **Initial Heat**: 0-10 (start at 0 for clean slate)
   - **Content Source**: Select complication pool (e.g., "core_complications.json")
5. Click **"Create Campaign"**

You now have an active campaign! The dashboard shows your campaign's current state.

### Understanding the Dashboard

**Header Stats:**
- **Pressure**: Long-term accumulation of unresolved problems (0-10)
- **Heat**: Immediate pursuit/attention level (0-10)
- **Sessions**: Total sessions played in this campaign
- **Bands**: Active long-arc narrative threads

**Session Ledger:**
- Chronological list of all sessions
- Shows date, pressure/heat at time, scars gained, canon events
- Click to expand session details

**Canon Summary:**
- Key narrative events from campaign history
- Bullet-point format for quick reference
- Derived from session finalizations

**Active Scars:**
- Structured lasting injuries/conditions
- Shows severity (1-5) and effect description
- Affects future complication selection

**Faction Tracker:**
- Known factions and their disposition (-5 to +5)
- Neutral (0), Hostile (negative), Allied (positive)
- Influences complication themes

## Using Context → Generator Flow (Flow A)

The "Apply to Generator" feature bridges campaign state → event generation:

1. **Open Campaign Dashboard** (if not already viewing)
2. Click **"Apply Context to Generator ⚡"** button
3. Campaign state is now active (yellow strip confirms)
4. **Switch to Event Generator tab** (top nav)
5. Notice the **"🔗 Context Applied"** indicator
6. Generator defaults are now influenced by campaign:
   - Severity weighted by pressure bands
   - Cooldowns aware of recent complications
   - Scar effects inform selection
7. **Generate events** as normal
8. When done, click **"Finalize This Session"** to capture results

**Context Applied Strip Explanation:**
- Yellow background: Campaign context is active
- Shows: Campaign name, pressure/heat, scar count, faction count
- Click name to return to campaign dashboard
- Click "✕ Clear" to deactivate context

## Finalizing Sessions (Flow B)

After generating complications with campaign context:

1. Click **"Finalize This Session"** (appears when context is active)
2. **Finalize Wizard** opens with three steps:

### Step 1: Review Generated Complications
- Shows all complications generated this session
- Grouped by severity
- Read-only review before decisions

### Step 2: Record Outcomes
Three input fields:

**Canon Bullets:**
- Key narrative events from this session
- One per line, markdown format
- Example: `- Survived ambush at Red Ridge`
- Example: `- Lost supplies in ravine crossing`

**New Scars:**
- Structured injuries with severity (1-5)
- Format: `<severity>: <effect description>`
- Example: `2: Dislocated shoulder - limited lifting`
- Example: `4: Radiation exposure - chronic weakness`
- Note: Scars are campaign-wide, not PC-specific

**Faction Updates:**
- Format: `<faction_name>:<±value>`
- Example: `Raiders:+2` (improved relations)
- Example: `Enclave:-3` (worsened relations)
- Combines with existing disposition

### Step 3: Confirm
- Reviews all changes before applying
- Shows pressure/heat deltas
- Click "Finalize" to commit session to campaign ledger

## Importing Campaign History (Flows C & D)

### Flow C: Import to Existing Campaign

Add past sessions to current campaign:

1. Open campaign dashboard
2. Click **"Import"** in Session Ledger section
3. **Paste Campaign History** (narrative text)
4. Click **"Parse"** to analyze the text
5. Parser detects:
   - Session dates (looks for date patterns)
   - Canon events (bullet points, significant events)
   - Faction references (@ mentions, organization names)
6. **Review and Correct Entity Classifications**:
   - Parser uses heuristics to classify entities as Factions/Places/Artifacts/Concepts
   - Use inline controls to correct misclassifications:
     - **Factions**: →Place, →Artifact, →Concept, ✕ (remove)
     - **Places**: ↑Faction (promote), →Artifact, →Concept, ✕
     - **Artifacts**: ↑Faction, →Place, →Concept, ✕
     - **Concepts**: ↑Faction, →Place, →Artifact, ✕
   - All corrections save to campaign-specific overrides file
   - Future imports automatically apply your corrections
   - No subdialogs required - all controls inline
7. **Optional: Download Parsed JSON**
   - Click "📥 Download Parsed JSON" to export raw parser output
   - Useful for debugging, analysis, or external processing
   - File format: `parsed_history_merge_YYYYMMDD_HHMMSS.json`
8. **Merge to Campaign**:
   - Sessions added to ledger
   - Canon appended to summary
   - New factions added to tracker
   - Existing state preserved

### Flow D: Import to New Campaign

Create campaign from existing narrative:

1. From landing page, click **"Import Campaign History"**
2. Enter campaign name
3. Paste campaign history text
4. Click **"Parse History"** to analyze the text
5. Parser extracts structure (sessions, canon, factions)
6. **Review and Correct Entity Classifications**:
   - Parser uses heuristics to classify entities as Factions/Places/Artifacts/Concepts
   - Use inline controls to correct misclassifications:
     - **Factions**: →Place, →Artifact, →Concept, ✕ (remove)
     - **Places**: ↑Faction (promote), →Artifact, →Concept, ✕
     - **Artifacts**: ↑Faction, →Place, →Concept, ✕
     - **Concepts**: ↑Faction, →Place, →Artifact, ✕
   - All corrections save to campaign-specific overrides file
   - Future imports automatically apply your corrections
   - No subdialogs required - all controls inline
7. **Optional: Download Parsed JSON**
   - Click "📥 Download Parsed JSON" to export raw parser output
   - Useful for debugging, analysis, or external processing
   - File format: `parsed_history_YYYYMMDD_HHMMSS.json`
8. Click **"Create from History"**
9. Campaign created with:
   - Session ledger populated
   - Canon summary extracted
   - Faction tracker initialized
   - Pressure/heat at defaults (0)

## Managing Campaigns

### Switching Between Campaigns

- Campaign selector dropdown (top of sidebar)
- Select from list of all campaigns
- Dashboard updates to show selected campaign

### Viewing Campaign History

- Session ledger shows all sessions chronologically
- Click session to expand details
- Canon summary provides narrative overview
- Scar and faction sections show current state

### Campaign Persistence

- Campaigns saved in `campaigns/` directory
- One JSON file per campaign
- Auto-saved on every change
- Backup before major operations

## Tips and Best Practices

### Starting Fresh
- Begin pressure/heat at 0 for gradual buildup
- Let first few sessions establish baseline
- Add scars sparingly at first

### Managing Pressure
- Pressure 0-3: Relatively calm, slow burn
- Pressure 4-6: Moderate tension, complications brewing
- Pressure 7-10: High stakes, urgent problems
- Pressure decays slowly over sessions

### Managing Heat
- Heat 0-3: Low visibility, laying low
- Heat 4-6: Drawing attention, probing responses
- Heat 7-10: Active pursuit, urgent threats
- Heat decays faster than pressure

### Recording Scars
- Be specific about mechanical effects
- Severity 1-2: Minor hindrances
- Severity 3: Significant limitation
- Severity 4-5: Major debilitation
- Don't over-scar early in campaign

### Faction Management
- Track only significant factions
- Disposition -5 to +5 (neutral = 0)
- Small changes (±1-2) for minor interactions
- Large changes (±3-5) for major events
- Factions influence future complications

### Canon Summary
- Focus on "what happened" not "how players felt"
- One bullet per major event
- Chronological order preferred
- Keep it concise (2-4 bullets per session)

### Content Sources
- Start with "core_complications.json"
- Add modular content packs as needed
- Review available complications before session
- Understand severity distribution

### Using Inline Entity Classification Controls

When importing campaign history, the parser classifies entities automatically using heuristics. Use inline controls to correct:

**Common Corrections:**
- Places misclassified as factions (e.g., "Maker Tunnels" → demote to Place)
- Generic names needing faction promotion (e.g., "The Makers" → stays Faction)
- Artifacts with generic names (e.g., "The Ring" → add context via removal + manual entry)

**Best Practices:**
- Review Factions list first - these drive campaign mechanics
- Only promote to Faction if entity has agency (can act, react, remember)
- Use Remove (✕) for obvious false positives (section headers, meta text)
- Corrections persist automatically - no "Save" button needed
- Future imports to same campaign apply your corrections

**Persistence Behavior:**
- Overrides stored in `campaigns/{campaign_id}_import_overrides.json`
- One file per campaign, tracks all corrections
- Next import automatically applies: promotes, demotes, lateral moves, ignores
- Corrections are deterministic - same input + overrides = same result

## Troubleshooting

### "No campaigns found" message
- Create first campaign with "+ New Campaign"
- Check campaigns/ directory exists

### Context not applying to generator
- Verify "Context Applied" strip is visible
- Confirm you clicked "Apply Context to Generator"
- Check browser console for errors

### Parser not detecting sessions
- Ensure dates are recognizable format
- Try bullet points for clearer structure
- Check preview to see what was parsed

### Finalize wizard not appearing
- Context must be active (apply from dashboard first)
- Generate at least one complication
- Check for errors in console

## Next Steps

After mastering basic campaign usage:
1. Experiment with different pressure/heat starting points
2. Track multiple campaigns for different story arcs
3. Use import feature to migrate existing narratives
4. Explore how scar severity affects future complications
5. Observe long-arc bands (SHADOW_OPS, NETWORK_DECAY, etc.)

## Feedback and Support

Campaign mechanics are v0.2 and actively evolving. Report issues or suggestions by:
- Documenting unexpected behavior
- Noting missing features
- Describing desired workflow improvements

---

**Version**: Campaign Mechanics v0.2  
**Integration Flows**: A, B, C, D (Complete)  
**Guide Version**: 0.1
