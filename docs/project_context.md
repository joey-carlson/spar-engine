# SPAR Procedural Engine – Project Context & Status
Version: v0.1-context
Date: 2025-12-22

## 1. Project Overview

This project is the early-stage development of a **procedural encounter complication engine** intended to serve as the core system behind multiple tabletop roleplaying game (TTRPG) projects.

The guiding decision is:

> **SPAR is the engine. Individual game systems (e.g., D&D) are adapters and content packs layered on top.**

This ensures long-term flexibility, reuse, and consistency across systems while keeping mechanics separate from procedural logic.

---

## 2. How This Started

The project began with a conceptual question:

- Is there a meaningful connection between **random roll tables in TTRPGs** and **self-organized criticality / heavy-tailed systems** studied in physics?

This was motivated by a research paper on **self-organized criticality in fragmentation**, which demonstrated that:
- Outputs often follow **power-law (heavy-tail) distributions**
- Macro constraints (shape/topology) matter more than micro details (material)
- Real systems require **finite-size cutoffs** to prevent runaway outcomes

That insight mapped cleanly onto TTRPG design problems:
- Many small complications, few large ones
- Situation structure (confined vs populated vs open) should affect outcome volatility
- Campaigns need safety rails to prevent random tables from derailing play

---

## 3. Key Design Decisions

### 3.1 Engine vs Adapter Split

- **Engine responsibilities**
  - State tracking (tension, heat, etc.)
  - Severity distributions
  - Cutoff logic
  - Content filtering and selection
  - Narrative-first outputs

- **Adapter responsibilities**
  - Translating engine outputs into system mechanics
  - Applying DCs, damage, difficulty bands, etc.
  - Handling system-specific resources

This keeps the engine **system-agnostic** and reusable.

---

### 3.2 Encounter Complications First

The first concrete use case chosen was:

> **Encounter complications**, not encounters themselves.

This allowed focus on:
- Pacing
- Escalation
- Narrative pressure
- Emergent scene dynamics

without entangling combat math or stat blocks.

---

## 4. Formalization & Governance

To prevent drift and technical debt, two foundational documents were created early:

### 4.1 SPAR Engine v0.1 Contract
Defines:
- Inputs (scene context, state, selection filters)
- Outputs (severity, effect vectors, fiction, state deltas)
- Cutoff behavior
- Severity bands and expectations

This is the **authoritative engine interface**.

---

### 4.2 SPAR Tool Engineering Rules v0.1

Modeled after a "ClineRules" file, this document defines:
- Design philosophy
- Architecture boundaries
- Testing strategy
- Versioning rules
- Collaboration expectations

This document governs *how* work is done, not just *what* is built.

---

## 5. Current Implementation Status

### 5.1 Engine Core (Completed for v0.1)

Implemented as a Python package:

- Deterministic, seedable RNG with trace output
- Truncated heavy-tail severity sampler
- Scene-based severity caps (finite-size cutoffs)
- Tag-, environment-, and phase-based content filtering
- Cooldown-based anti-repetition logic
- Minimal starter content pack
- Pytest suite (gist tests, unit tests, distribution sanity tests)

The engine is **engine-first**, with no UI or system mechanics embedded.

---

### 5.2 CLI Interface (Completed)

A thin CLI wrapper (`engine.py`) allows:

- Running the engine from the terminal
- Passing scene and morphology parameters as flags
- Generating single or multiple events
- Forcing specific event IDs
- Emitting human-readable output or JSONL
- Inspecting RNG traces for debugging

Shell usage assumes **zsh**.

This enables rapid testing, scripting, and experimentation without UI overhead.

---

## 6. What Exists Right Now

At this point, the project includes:

- Engine core (v0.1)
- CLI runner
- Streamlit UI for rapid prototyping
- Starter content pack
- README with usage instructions
- Engineering rules document
- Engine contract document
- Automated tests
- Public GitHub repository: https://github.com/joey-carlson/spar-engine

The engine is functional, deterministic, and safe by default with multiple interface options.

---

## 7. What Has *Not* Been Built Yet (By Design)

- No system adapters (D&D mapping, SPAR-native mapping)
- No persistent campaign state across CLI runs
- No content authoring UI
- No React web interface (Streamlit serves as prototyping platform)
- No public deployment or packaging

These are explicitly deferred until engine behavior is validated.

---

## 8. Immediate Next Steps (Planned)

Short-term (v0.x):
1. Add a pure function to apply `StateDelta` to `EngineState`
2. Improve cutoff conversions with omen- and hook-specific fiction
3. Expand and refine the starter content pack
4. Build a **Streamlit debug harness** for visualization and tuning

Medium-term:
- Implement D&D encounter complication adapter
- Add tension-pool distribution mode
- Introduce persistent state handling
- Begin React-based UI exploration

---

## 9. Project Philosophy (Summary)

- Narrative pressure > mechanical randomness
- Many small events, few big ones
- Safety rails are features, not compromises
- Engines create situations, players create solutions
- Systems interpret outcomes, not the engine

---

## 10. Status Summary

**Current state:**
Engine v0.1 complete with CLI and Streamlit UI interfaces. Public GitHub repository established.

**Confidence level:**
High for core architecture and interfaces, moderate for content tuning (expected).

**Readiness:**
Ready for expanded content development, system adapter creation, and community contributions.

---

End of document.
