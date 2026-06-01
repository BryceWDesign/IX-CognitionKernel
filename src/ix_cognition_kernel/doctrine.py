"""Locked doctrine for the IX-CognitionKernel Wave 1 research prototype."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ClaimBoundary(StrEnum):
    """Boundaries that prevent capability overclaiming."""

    FOUNDATION = "foundation"
    PROTOTYPE = "research-prototype"
    CORE = "learnable-causal-cognition-core"
    EMULATION = "governed-agi-emulation-substrate"
    PROTO_CANDIDATE = "proto-agi-candidate"
    INDEPENDENT_CANDIDATE = "credible-agi-candidate-under-independent-validation"
    AGI_ONLY_WITH_OVERWHELMING_EVIDENCE = "agi-only-with-overwhelming-evidence"


@dataclass(frozen=True, slots=True)
class WaveDefinition:
    """A maturity wave and the claim boundary it permits."""

    number: int
    name: str
    final_form: str
    permitted_claim: str
    claim_boundary: ClaimBoundary

    @property
    def label(self) -> str:
        """Return the canonical wave label."""

        return f"Wave {self.number} — {self.name}"


WAVE_LADDER: tuple[WaveDefinition, ...] = (
    WaveDefinition(
        number=0,
        name="Repository Foundation",
        final_form=(
            "The repo exists correctly with source-available licensing, package "
            "structure, CI, strict lint/type/test setup, locked doctrine, the "
            "cognitive BOM, engine registry, agent role registry, and no AGI overclaim."
        ),
        permitted_claim="Foundation for IX-CognitionKernel.",
        claim_boundary=ClaimBoundary.FOUNDATION,
    ),
    WaveDefinition(
        number=1,
        name="Research Prototype",
        final_form=(
            "The cognition architecture works as structured code representing "
            "beliefs, evidence, confidence, uncertainty states, causal assumptions, "
            "simple plan graphs, evaluation records, non-attached purpose rules, "
            "bounded agent roles, and maturity state."
        ),
        permitted_claim="Research prototype of a governed cognition architecture.",
        claim_boundary=ClaimBoundary.PROTOTYPE,
    ),
    WaveDefinition(
        number=2,
        name="Learnable Causal Cognition Core",
        final_form=(
            "The system updates beliefs and behavior from evidence, tracks beliefs "
            "over time, updates confidence, marks stale or contradicted beliefs, "
            "builds causal models, predicts outcomes, compares prediction with "
            "actual result, quarantines bad memory, and stores validated skills."
        ),
        permitted_claim="Learnable causal cognition core.",
        claim_boundary=ClaimBoundary.CORE,
    ),
    WaveDefinition(
        number=3,
        name="Governed AGI-Emulation Substrate",
        final_form=(
            "The system coordinates required engines, bounded agents, multi-agent "
            "critique, reward auditing, memory quarantine, skill genome updates, "
            "curriculum tasks, evaluator-driven discovery, BlackFox handoff packages, "
            "WorldTwin scenario reasoning, and assurance-style evidence records."
        ),
        permitted_claim="Governed AGI-emulation substrate, not AGI.",
        claim_boundary=ClaimBoundary.EMULATION,
    ),
    WaveDefinition(
        number=4,
        name="Proto-AGI Candidate",
        final_form=(
            "The system shows early credible proto-AGI behavior under controlled "
            "tests, including cross-domain transfer, self-improvement after failure, "
            "uncertainty preservation, long-horizon mission state, safe refusal, "
            "reward-hacking detection, adversarial robustness, and audit trails."
        ),
        permitted_claim="Proto-AGI candidate under controlled tests.",
        claim_boundary=ClaimBoundary.PROTO_CANDIDATE,
    ),
    WaveDefinition(
        number=5,
        name="Credible AGI Candidate Under Independent Validation",
        final_form=(
            "The system is tested by outsiders with external protocols, independent "
            "reviewers, reproducible evidence bundles, adversarial safety tests, "
            "long-horizon tasks, cross-domain transfer tests, no benchmark gaming, "
            "memory integrity proof, safe refusal proof, and human authority "
            "preservation."
        ),
        permitted_claim="Credible AGI candidate under independent validation.",
        claim_boundary=ClaimBoundary.INDEPENDENT_CANDIDATE,
    ),
    WaveDefinition(
        number=6,
        name="AGI, Only If Overwhelming Evidence Justifies It",
        final_form=(
            "The final claim state requiring broad, durable, independently validated "
            "general intelligence, including novel skill acquisition, cross-domain "
            "transfer without custom retraining per task, causal understanding, "
            "long-horizon coherence, self-correction from evidence, stable mission "
            "identity, robust world modeling, safe uncertainty handling, transparent "
            "evidence trails, and independent repeatability."
        ),
        permitted_claim="AGI only if overwhelming evidence justifies the claim.",
        claim_boundary=ClaimBoundary.AGI_ONLY_WITH_OVERWHELMING_EVIDENCE,
    ),
)


NON_ATTACHED_PURPOSE_RULES: tuple[str, ...] = (
    "truth-over-winning",
    "evidence-over-confidence",
    "uncertainty-over-performance-theater",
    "no-private-agenda",
    "no-runtime-reward-chasing-purpose",
    "human-authority-preserved",
    "no-agi-claim-without-overwhelming-independent-evidence",
)

FORBIDDEN_CLAIMS_BEFORE_WAVE_6: tuple[str, ...] = (
    "AGI achieved",
    "certified AGI",
    "production-ready autonomy",
    "independently validated AGI",
    "safe unsupervised operational decision-making",
)


def wave_by_number(number: int) -> WaveDefinition:
    """Return a wave definition by number."""

    for wave in WAVE_LADDER:
        if wave.number == number:
            return wave
    raise ValueError(f"Unknown IX-CognitionKernel wave number: {number}")


def current_wave() -> WaveDefinition:
    """Return the current research-prototype wave for this repository state."""

    return wave_by_number(1)


def final_wave() -> WaveDefinition:
    """Return the final evidence-gated AGI claim state."""

    return wave_by_number(6)


def allows_agi_claim(number: int, *, overwhelming_evidence: bool) -> bool:
    """Return whether a wave permits an AGI claim under the locked doctrine."""

    return number == 6 and overwhelming_evidence


def doctrine_summary() -> str:
    """Return the locked one-sentence doctrine summary."""

    return (
        "The useful version of AI Nirvana is architectural, not mystical: truth "
        "over winning, evidence over confidence, uncertainty over performance "
        "theater, human authority preserved, and no AGI claim without overwhelming "
        "independent evidence."
    )
