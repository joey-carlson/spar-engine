from __future__ import annotations

from .models import Constraints, EngineState, PartyBand, RarityMode, ScenePhase
from .rng import TraceRNG


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def compute_alpha(rarity_mode: RarityMode, constraints: Constraints) -> float:
    """Return a Zipf-like exponent alpha.

    Lower alpha -> fatter tail (more big severities).
    Higher alpha -> steeper drop (mostly small severities).

    Derived from:
    - rarity_mode (calm/normal/spiky)
    - morphology-like constraints (confinement, connectivity, visibility)
    """
    c = constraints.clamped()
    base = {"calm": 2.2, "normal": 1.6, "spiky": 1.2}[rarity_mode]
    morph = (c.confinement + c.visibility - c.connectivity)  # [-1, 2]
    alpha = base - 0.35 * morph
    return _clamp(alpha, 0.8, 3.0)


def compute_severity_cap(
    party_band: PartyBand,
    phase: ScenePhase,
    constraints: Constraints,
    state: EngineState,
    *,
    rarity_mode: RarityMode = "normal",
) -> int:
    """Compute a hard severity cap for the current scene.

    This is the finite-size cutoff safety rail: severities above cap are converted.

    v0.1 tuning:
    - spiky: lower cap a bit (more conversions), especially in high-morphology scenes
    - calm: raise cap a bit (fewer conversions)
    """
    base_by_band = {
        "low": {"approach": 6, "engage": 7, "aftermath": 6},
        "mid": {"approach": 7, "engage": 8, "aftermath": 7},
        "high": {"approach": 8, "engage": 9, "aftermath": 8},
        "unknown": {"approach": 7, "engage": 8, "aftermath": 7},
    }
    base = int(base_by_band[party_band][phase])

    c = constraints.clamped()
    morph = (c.confinement + c.visibility - c.connectivity)  # [-1, 2]
    adj = round(_clamp(morph, -1.0, 2.0) * 0.75)
    cap = base + adj

    tension = int(state.clocks.get("tension", 0))
    heat = int(state.clocks.get("heat", 0))
    if tension >= 9:
        cap += 1
    if heat >= 9:
        cap += 1

    if rarity_mode == "spiky":
        if morph >= 0.9:
            cap -= 1
        if morph >= 1.4:
            cap -= 1
    elif rarity_mode == "calm":
        cap += 1

    return int(_clamp(cap, 3, 10))


def sample_severity(rng: TraceRNG, alpha: float, lo: int = 1, hi: int = 10) -> int:
    severities = list(range(lo, hi + 1))
    weights = [1.0 / (s ** alpha) for s in severities]
    s = rng.weighted_choice(severities, weights, label=f"severity(zipf,alpha={alpha:.2f})")
    return int(s)
