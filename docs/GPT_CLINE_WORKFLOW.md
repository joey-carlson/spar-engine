# GPT-Cline Collaborative Workflow
Version: v1.0  
Date: 2025-12-22

## Overview

This document establishes the collaborative workflow between ChatGPT (Designer persona) and Cline (Developer/QA persona) for the SPAR Tool Engine project.

## Roles and Responsibilities

### ChatGPT (Designer Persona)
**Strengths:**
- Creative and analytical work
- Full context of all RPG work (SPAR and D&D)
- Game design and narrative architecture
- Content design and balance decisions
- Feature prioritization and requirements

**Responsibilities:**
- Define feature requirements and specifications
- Design content entries and event structures
- Make game design decisions (severity bands, tag systems, etc.)
- Provide narrative and thematic guidance
- Review and approve architectural changes
- Prioritize features and content packs

### Cline (Developer/QA Persona)
**Strengths:**
- Code implementation and testing
- Technical architecture execution
- Debugging and troubleshooting
- Git workflow management
- Test automation and validation

**Responsibilities:**
- Implement features based on GPT specifications
- Write and maintain tests (gist + unit + integration)
- Debug issues and fix bugs
- Maintain Git repository sync
- Ensure code follows engineering rules
- Validate implementations match specifications

## Communication Protocol

### From GPT to Cline
When passing work from GPT to Cline, provide:

1. **Clear Feature Specification**
   - What needs to be built/changed
   - Why it's needed
   - Expected behavior/outputs
   
2. **Technical Requirements**
   - Data structures involved
   - Integration points
   - Performance constraints
   
3. **Acceptance Criteria**
   - How to validate success
   - Test scenarios to implement
   - Edge cases to handle

**Format Example:**
```
FEATURE: Add Tension Pool Distribution Mode
SPEC: [detailed specification from GPT]
TECHNICAL REQUIREMENTS:
- Modify severity.py to add tension_pool() function
- Update models.py with TensionPoolConfig
- Integration point: engine.generate_event()
ACCEPTANCE CRITERIA:
- Tension accumulates discretely
- Burst releases reduce tension
- Tests validate distribution shape
```

### From Cline to GPT
When reporting back to GPT, provide:

1. **Implementation Summary**
   - What was built/changed
   - Files modified
   - Key decisions made
   
2. **Test Results**
   - All tests passing/failing
   - Coverage achieved
   - Edge cases discovered
   
3. **Questions or Design Decisions**
   - Ambiguities found during implementation
   - Alternative approaches considered
   - Recommendations for GPT review

**Format Example:**
```
IMPLEMENTATION COMPLETE: Tension Pool Distribution
FILES MODIFIED:
- spar_engine/severity.py: Added tension_pool()
- spar_engine/models.py: Added TensionPoolConfig
- tests/test_tension_pool.py: Full test coverage
TEST RESULTS: All tests passing (15/15)
QUESTIONS:
- Should tension decay over time or only on burst?
- Max tension value: 100 or configurable?
```

## Current Project Status

### Completed (v0.1)
- ✅ Core engine with truncated heavy-tail distribution
- ✅ CLI interface with full parameter support
- ✅ Streamlit debug harness
- ✅ Pytest suite (gist + unit + distribution tests)
- ✅ System-agnostic architecture
- ✅ Documentation (contract, engineering rules, context)
- ✅ Git repository synchronized with GitHub

### Architecture Overview
```
spar_tool_engine/
├── spar_engine/           # Core engine package
│   ├── engine.py         # Main generation logic
│   ├── models.py         # Data structures
│   ├── severity.py       # Distribution sampling
│   ├── cutoff.py         # Cutoff handling
│   ├── content.py        # Content loading/filtering
│   ├── state.py          # State management
│   └── rng.py           # Seedable RNG wrapper
├── streamlit_harness/    # Debug UI
├── tests/                # Test suite
├── data/                 # Content packs
└── docs/                 # Documentation
```

### Key Design Principles
1. **Engine is system-agnostic** - No D&D mechanics in core
2. **Narrative pressure over mechanical randomness**
3. **Heavy-tail distributions with finite-size cutoffs**
4. **Stateful with observable pressure accumulation**
5. **Safe by default, configurable for spikiness**

## Workflow Best Practices

### Git Workflow
- Commit early and often
- Follow Conventional Commits format
- Always build/test before committing
- Keep local and GitHub synced regularly
- Never push broken code

### Development Cycle
1. GPT provides feature specification
2. Cline implements with tests
3. Cline validates against acceptance criteria
4. Cline reports results to GPT
5. GPT reviews and provides feedback or next task
6. Commit and sync to GitHub

### Testing Philosophy
- Every feature needs at least one gist test
- Distribution sanity tests for probabilistic features
- Tests describe behavior, not implementation
- Use deterministic seeded RNG for reproducibility

## Next Steps (Awaiting GPT Direction)

Immediate possibilities:
1. **Content Expansion** - Add more complications to starter pack
2. **Tension Pool Mode** - Alternative distribution system
3. **D&D Adapter** - System-specific mechanics layer
4. **State Delta Application** - Pure function to apply state changes
5. **Enhanced Cutoff Fiction** - Better omen/hook conversions

## Document Maintenance

This workflow document should be:
- Updated when roles or responsibilities change
- Referenced when handoffs feel unclear
- Versioned when significant process changes occur

---

**Status**: Active workflow established  
**Last Updated**: 2025-12-22  
**Maintained By**: Both GPT and Cline collaboratively
