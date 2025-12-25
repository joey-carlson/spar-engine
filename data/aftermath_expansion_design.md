# Aftermath Tone Diversification - Design Notes

## Current Aftermath Content Analysis

**Existing Aftermath Entries** (10 pure aftermath):
1. aftermath_tracks_left_01 - wilderness, information/visibility/terrain
2. aftermath_wildlife_scatter_01 - wilderness, information/visibility
3. aftermath_storm_approach_01 - wilderness/sea, hazard/time_pressure  
4. aftermath_evidence_scatter_01 - city/ruins, information/opportunity
5. aftermath_sirens_converge_01 - city/industrial, time_pressure/visibility/social_friction
6. aftermath_structural_groan_01 - dungeon/ruins, terrain/hazard/time_pressure
7. aftermath_blame_spreads_01 - city/industrial, social_friction/visibility
8. aftermath_opportunity_window_01 - ruins/dungeon, opportunity/information
9. aftermath_sea_tide_shift_01 - sea, terrain/time_pressure
10. aftermath_sea_wreckage_01 - sea, information/opportunity/hazard

**Tag Distribution** (current aftermath):
- information: 7 entries
- time_pressure: 5 entries  
- visibility: 5 entries
- opportunity: 4 entries
- terrain: 4 entries
- hazard: 4 entries
- social_friction: 3 entries
- positioning: 2 entries
- cost: 0 entries (notable absence)
- attrition: 0 entries (good - avoiding this)

## Design Goals for New Entries

Add 10 new entries emphasizing:
- **social_friction** (fear, rumors, authority response) - underrepresented
- **information** (delayed revelations, implications) 
- **terrain** (lingering environmental changes)
- **opportunity** (non-urgent openings, leverage)
- **consequence** (explicit fallout without immediate danger)

Severity bands: 1-4 primary, occasional 5-6

## New Entry Designs

### 1. aftermath_rumor_spreads_01
- **Environment**: city, industrial, ruins
- **Tags**: social_friction, information, visibility
- **Severity**: 1-4
- **Theme**: Witnesses misinterpret what happened, rumors distort events
- **Tone**: "What people think happened vs what actually happened"

### 2. aftermath_authority_response_01
- **Environment**: city, industrial
- **Tags**: social_friction, information, time_pressure
- **Severity**: 2-5
- **Theme**: Official response forms, questions arise
- **Tone**: "Bureaucratic consequences take shape"

### 3. aftermath_fear_lingers_01
- **Environment**: city, wilderness, ruins
- **Tags**: social_friction, information
- **Severity**: 1-4
- **Theme**: Locals avoid the area, behavior patterns shift
- **Tone**: "What fear changes"

### 4. aftermath_revelation_delayed_01
- **Environment**: dungeon, ruins, planar
- **Tags**: information, opportunity, mystic
- **Severity**: 1-5
- **Theme**: Something becomes clear only after the dust settles
- **Tone**: "The answer was there all along"

### 5. aftermath_terrain_marked_01
- **Environment**: wilderness, ruins, dungeon
- **Tags**: terrain, information, visibility
- **Severity**: 1-4
- **Theme**: The fight changed the landscape permanently
- **Tone**: "What the place remembers"

### 6. aftermath_leverage_exposed_01
- **Environment**: city, ruins, industrial
- **Tags**: opportunity, information, social_friction
- **Severity**: 2-5
- **Theme**: Someone's vulnerability or resource becomes obvious
- **Tone**: "New leverage appears"

### 7. aftermath_quiet_too_quiet_01
- **Environment**: wilderness, dungeon, ruins
- **Tags**: information, visibility, positioning
- **Severity**: 1-4
- **Theme**: Unnatural silence suggests something watching/waiting
- **Tone**: "What absence means"

### 8. aftermath_alliance_shift_01
- **Environment**: city, industrial
- **Tags**: social_friction, opportunity, information
- **Severity**: 2-5
- **Theme**: Alliances re-form based on outcomes
- **Tone**: "Who stands where now"

### 9. aftermath_resource_revealed_01
- **Environment**: ruins, dungeon, wilderness
- **Tags**: opportunity, information, terrain
- **Severity**: 1-4
- **Theme**: Battle exposed something valuable/useful
- **Tone**: "Silver lining"

### 10. aftermath_authority_question_01
- **Environment**: city, industrial
- **Tags**: social_friction, information, visibility
- **Severity**: 2-4
- **Theme**: Officials ask questions, expect answers
- **Tone**: "Accountability demands"

## Validation Plan

After adding entries:
1. Run: Presets × (Approach/Engage/Aftermath) × Normal, batch 200
2. Observe:
   - Greater tag variety in Aftermath results
   - Reduced time_pressure+attrition dominance
   - No new repetition issues
   - Cutoff rates remain stable
