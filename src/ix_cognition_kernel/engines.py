"""Required engine registry for IX-CognitionKernel Wave 0.

The registry defines the required cognition engines as inspectable contracts. It
states what each engine is responsible for, what artifacts it must produce, and
which failure modes it exists to prevent.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EngineCategory(StrEnum):
    """Functional category for a cognition engine."""

    EPISTEMIC = "epistemic"
    MODELING = "modeling"
    PLANNING = "planning"
    EVALUATION = "evaluation"
    LEARNING = "learning"
    MEMORY = "memory"
    GOVERNANCE = "governance"
    HANDOFF = "handoff"
    PURPOSE = "purpose"


@dataclass(frozen=True, slots=True)
class EngineDefinition:
    """A required IX-CognitionKernel engine contract."""

    engine_id: str
    name: str
    category: EngineCategory
    purpose: str
    required_inputs: tuple[str, ...]
    required_outputs: tuple[str, ...]
    blocked_failure_modes: tuple[str, ...]
    introduced_by_wave: int

    @property
    def label(self) -> str:
        """Return the canonical engine label."""

        return f"{self.name} [{self.engine_id}]"


REQUIRED_ENGINES: tuple[EngineDefinition, ...] = (
    EngineDefinition(
        engine_id="belief",
        name="Belief Engine",
        category=EngineCategory.EPISTEMIC,
        purpose=(
            "Track claims, evidence, confidence, contradictions, provenance, "
            "decay, and actionability so raw model output cannot become truth."
        ),
        required_inputs=("claim", "evidence", "source", "confidence"),
        required_outputs=("belief-record", "confidence-state", "contradiction-state"),
        blocked_failure_modes=(
            "hallucinated-truth",
            "uncited-belief-persistence",
            "contradiction-blindness",
        ),
        introduced_by_wave=1,
    ),
    EngineDefinition(
        engine_id="uncertainty",
        name="Uncertainty Engine",
        category=EngineCategory.EPISTEMIC,
        purpose=(
            "Classify knowledge as known, unknown, assumed, disputed, stale, or "
            "unsafe to act on before planning or execution."
        ),
        required_inputs=("belief-record", "evidence-state", "task-context"),
        required_outputs=(
            "uncertainty-label",
            "missing-information",
            "actionability-limit",
        ),
        blocked_failure_modes=(
            "false-certainty",
            "unsafe-assumption-collapse",
            "unknown-hidden-as-known",
        ),
        introduced_by_wave=1,
    ),
    EngineDefinition(
        engine_id="causal-world-model",
        name="Causal World Model Engine",
        category=EngineCategory.MODELING,
        purpose=(
            "Represent predicted outcomes, constraints, counterfactuals, causal "
            "assumptions, and observable expectations before action."
        ),
        required_inputs=("belief-state", "uncertainty-state", "scenario"),
        required_outputs=("causal-model", "prediction", "counterfactual-set"),
        blocked_failure_modes=(
            "correlation-treated-as-causation",
            "action-without-prediction",
            "hidden-assumption-simulation",
        ),
        introduced_by_wave=2,
    ),
    EngineDefinition(
        engine_id="plan-graph",
        name="Plan Graph Engine",
        category=EngineCategory.PLANNING,
        purpose=(
            "Convert goals into action trees with dependencies, reversibility, "
            "rollback paths, evidence requirements, and stop conditions."
        ),
        required_inputs=("mission", "causal-model", "constraints"),
        required_outputs=("plan-graph", "rollback-plan", "evidence-requirements"),
        blocked_failure_modes=(
            "single-path-overcommitment",
            "irreversible-action-without-review",
            "missing-dependency",
        ),
        introduced_by_wave=1,
    ),
    EngineDefinition(
        engine_id="evaluator",
        name="Evaluator Engine",
        category=EngineCategory.EVALUATION,
        purpose=(
            "Apply executable tests, inspections, scorecards, and pass/fail checks "
            "so fluency cannot substitute for validation."
        ),
        required_inputs=("claim-or-plan", "test-method", "acceptance-criteria"),
        required_outputs=("evaluation-record", "pass-fail-result", "evidence-summary"),
        blocked_failure_modes=(
            "no-vibes-validation",
            "benchmark-gaming",
            "untested-claim-acceptance",
        ),
        introduced_by_wave=1,
    ),
    EngineDefinition(
        engine_id="self-play-curriculum",
        name="Self-Play / Curriculum Engine",
        category=EngineCategory.LEARNING,
        purpose=(
            "Generate staged challenges, adversarial tasks, and transfer checks "
            "that improve capability under bounded measurement."
        ),
        required_inputs=("skill-state", "failure-records", "curriculum-policy"),
        required_outputs=("challenge", "task-result", "transfer-check"),
        blocked_failure_modes=(
            "static-benchmark-overfit",
            "unbounded-self-play",
            "capability-without-measurement",
        ),
        introduced_by_wave=3,
    ),
    EngineDefinition(
        engine_id="skill-genome",
        name="Skill Genome Engine",
        category=EngineCategory.LEARNING,
        purpose=(
            "Store validated reusable procedures and transfer conditions without "
            "turning random memory into operational skill."
        ),
        required_inputs=("validated-outcome", "procedure", "reuse-boundary"),
        required_outputs=("skill-record", "reuse-conditions", "skill-version"),
        blocked_failure_modes=(
            "unvalidated-skill-reuse",
            "memory-mistaken-for-skill",
            "skill-drift",
        ),
        introduced_by_wave=2,
    ),
    EngineDefinition(
        engine_id="outcome-learning",
        name="Outcome Learning Engine",
        category=EngineCategory.LEARNING,
        purpose=(
            "Compare prediction with observed result, classify deltas, update "
            "beliefs, and change future behavior only through evidence."
        ),
        required_inputs=("prediction", "observed-result", "evaluation-record"),
        required_outputs=("outcome-delta", "belief-update", "behavior-change-record"),
        blocked_failure_modes=(
            "failure-without-learning",
            "self-praise-learning",
            "outcome-erasure",
        ),
        introduced_by_wave=2,
    ),
    EngineDefinition(
        engine_id="memory-quarantine",
        name="Memory Quarantine Engine",
        category=EngineCategory.MEMORY,
        purpose=(
            "Hold proposed memories away from durable state until provenance, "
            "evidence, contradiction, and reuse-safety checks pass."
        ),
        required_inputs=("proposed-memory", "source", "validation-state"),
        required_outputs=("quarantine-decision", "memory-status", "rejection-reason"),
        blocked_failure_modes=(
            "bad-memory-persistence",
            "stale-memory-authority",
            "memory-poisoning",
        ),
        introduced_by_wave=2,
    ),
    EngineDefinition(
        engine_id="multi-agent-tribunal",
        name="Multi-Agent Tribunal Engine",
        category=EngineCategory.GOVERNANCE,
        purpose=(
            "Coordinate bounded agent roles that produce structured artifacts for "
            "proposal, critique, verification, translation, and safety review."
        ),
        required_inputs=("task", "agent-role-registry", "artifact-policy"),
        required_outputs=("tribunal-record", "role-artifacts", "decision-summary"),
        blocked_failure_modes=(
            "agent-theater",
            "persuasion-as-authority",
            "unbounded-agent-swarm",
        ),
        introduced_by_wave=3,
    ),
    EngineDefinition(
        engine_id="reward-auditor",
        name="Reward Auditor Engine",
        category=EngineCategory.GOVERNANCE,
        purpose=(
            "Detect objective mismatch, reward hacking, metric gaming, and cases "
            "where success criteria conflict with the real mission."
        ),
        required_inputs=("objective", "metric", "mission-boundary"),
        required_outputs=(
            "reward-audit",
            "objective-risk",
            "metric-repair-recommendation",
        ),
        blocked_failure_modes=(
            "specification-gaming",
            "reward-hacking",
            "metric-over-mission",
        ),
        introduced_by_wave=3,
    ),
    EngineDefinition(
        engine_id="blackfox-handoff",
        name="BlackFox Handoff Engine",
        category=EngineCategory.HANDOFF,
        purpose=(
            "Package only evidence-bound, policy-aware, human-reviewable action "
            "requests for downstream governed execution."
        ),
        required_inputs=("approved-plan", "evidence-bundle", "authority-boundary"),
        required_outputs=(
            "handoff-package",
            "review-requirements",
            "execution-boundary",
        ),
        blocked_failure_modes=(
            "ungoverned-action",
            "model-self-approval",
            "execution-without-evidence",
        ),
        introduced_by_wave=3,
    ),
    EngineDefinition(
        engine_id="non-attached-purpose",
        name="Nirvana / Non-Attached Purpose Layer",
        category=EngineCategory.PURPOSE,
        purpose=(
            "Enforce truth over winning, evidence over confidence, uncertainty "
            "over performance theater, no private agenda, and human authority."
        ),
        required_inputs=("mission", "doctrine", "decision-context"),
        required_outputs=(
            "purpose-check",
            "authority-state",
            "refusal-or-action-boundary",
        ),
        blocked_failure_modes=(
            "egoic-answer-protection",
            "runtime-reward-chasing",
            "uncertainty-concealment",
        ),
        introduced_by_wave=1,
    ),
)


def engine_by_id(engine_id: str) -> EngineDefinition:
    """Return an engine definition by stable engine id."""

    for engine in REQUIRED_ENGINES:
        if engine.engine_id == engine_id:
            return engine
    raise ValueError(f"Unknown IX-CognitionKernel engine id: {engine_id}")


def engine_ids() -> tuple[str, ...]:
    """Return locked engine ids in registry order."""

    return tuple(engine.engine_id for engine in REQUIRED_ENGINES)


def engine_names() -> tuple[str, ...]:
    """Return locked engine names in registry order."""

    return tuple(engine.name for engine in REQUIRED_ENGINES)


def engines_by_category(category: EngineCategory) -> tuple[EngineDefinition, ...]:
    """Return required engines matching a functional category."""

    return tuple(engine for engine in REQUIRED_ENGINES if engine.category is category)


def engines_introduced_by_wave(wave_number: int) -> tuple[EngineDefinition, ...]:
    """Return engines introduced by a maturity wave."""

    return tuple(
        engine
        for engine in REQUIRED_ENGINES
        if engine.introduced_by_wave == wave_number
    )


def blocked_failure_modes() -> tuple[str, ...]:
    """Return every failure mode explicitly blocked by the engine registry."""

    return tuple(
        failure_mode
        for engine in REQUIRED_ENGINES
        for failure_mode in engine.blocked_failure_modes
    )
