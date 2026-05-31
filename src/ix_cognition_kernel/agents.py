"""Bounded agent role registry for IX-CognitionKernel Wave 0.

The registry defines 25 agent roles as structured governance participants. These
roles are not autonomous personas and do not gain authority by persuasion. Each
role is bounded by required artifacts, activation rules, and authority limits.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AgentTier(StrEnum):
    """Operational tier for an agent role."""

    CORE = "core"
    GOVERNANCE = "governance"
    SPECIALIST = "specialist"


class ArtifactKind(StrEnum):
    """Structured artifact class produced or consumed by agent roles."""

    MISSION_BOUNDARY = "mission-boundary"
    BELIEF_RECORD = "belief-record"
    UNCERTAINTY_LEDGER = "uncertainty-ledger"
    WORLD_MODEL = "world-model"
    PLAN_GRAPH = "plan-graph"
    FAILURE_MODE_REPORT = "failure-mode-report"
    EVIDENCE_CHECK = "evidence-check"
    HANDOFF_PACKAGE = "handoff-package"
    OUTCOME_DELTA = "outcome-delta"
    TRANSLATION_RECORD = "translation-record"
    REWARD_AUDIT = "reward-audit"
    TOOL_SAFETY_REVIEW = "tool-safety-review"
    SPECIALIST_ROUTING_DECISION = "specialist-routing-decision"
    CODE_REVIEW_RECORD = "code-review-record"
    THREAT_MODEL = "threat-model"
    PHYSICAL_VALIDATION_RECORD = "physical-validation-record"
    FORMAL_CHECK_RECORD = "formal-check-record"
    PROVENANCE_RECORD = "provenance-record"
    MEMORY_INTEGRITY_DECISION = "memory-integrity-decision"
    SIMULATION_CRITIQUE = "simulation-critique"
    HUMAN_REVIEW_USABILITY_REPORT = "human-review-usability-report"
    LICENSE_COMPLIANCE_REVIEW = "license-compliance-review"
    RESOURCE_BUDGET_REVIEW = "resource-budget-review"
    ROLLBACK_PLAN = "rollback-plan"
    DECEPTION_MONITOR_REPORT = "deception-monitor-report"


@dataclass(frozen=True, slots=True)
class AgentRole:
    """A bounded agent role with required artifacts and authority limits."""

    role_id: str
    name: str
    tier: AgentTier
    mission: str
    activation_rule: str
    required_inputs: tuple[ArtifactKind, ...]
    required_outputs: tuple[ArtifactKind, ...]
    authority_limits: tuple[str, ...]
    paired_engines: tuple[str, ...]

    @property
    def label(self) -> str:
        """Return the canonical agent-role label."""

        return f"{self.name} [{self.role_id}]"


AGENT_ROLES: tuple[AgentRole, ...] = (
    AgentRole(
        role_id="mission-governor",
        name="Mission Governor",
        tier=AgentTier.CORE,
        mission=(
            "Preserve mission doctrine, human authority, forbidden-action "
            "boundaries, and the no-AGI-overclaim rule."
        ),
        activation_rule="Always active at the start and end of every cognition cycle.",
        required_inputs=(),
        required_outputs=(ArtifactKind.MISSION_BOUNDARY,),
        authority_limits=(
            "May block or bound action; may not execute tools or approve itself.",
        ),
        paired_engines=("non-attached-purpose",),
    ),
    AgentRole(
        role_id="belief-curator",
        name="Belief Curator",
        tier=AgentTier.CORE,
        mission=(
            "Maintain claims, confidence, evidence, contradictions, provenance, "
            "decay, and actionability."
        ),
        activation_rule="Always active whenever a claim may affect planning or memory.",
        required_inputs=(ArtifactKind.PROVENANCE_RECORD,),
        required_outputs=(ArtifactKind.BELIEF_RECORD,),
        authority_limits=(
            "May update belief records; may not treat unevaluated text as truth.",
        ),
        paired_engines=("belief",),
    ),
    AgentRole(
        role_id="unknowns-hunter",
        name="Unknowns Hunter",
        tier=AgentTier.CORE,
        mission=(
            "Expose known, unknown, assumed, disputed, stale, and unsafe-to-act "
            "states before planning."
        ),
        activation_rule="Always active before a plan graph is accepted.",
        required_inputs=(ArtifactKind.BELIEF_RECORD,),
        required_outputs=(ArtifactKind.UNCERTAINTY_LEDGER,),
        authority_limits=(
            "May mark action unsafe due to uncertainty; may not erase uncertainty.",
        ),
        paired_engines=("uncertainty",),
    ),
    AgentRole(
        role_id="world-modeler",
        name="World Modeler",
        tier=AgentTier.CORE,
        mission=(
            "Build causal assumptions, constraints, predicted outcomes, and "
            "counterfactuals before action."
        ),
        activation_rule=(
            "Active when a task requires prediction or consequence testing."
        ),
        required_inputs=(ArtifactKind.BELIEF_RECORD, ArtifactKind.UNCERTAINTY_LEDGER),
        required_outputs=(ArtifactKind.WORLD_MODEL,),
        authority_limits=(
            "May propose predictions; may not claim reality confirmed them.",
        ),
        paired_engines=("causal-world-model",),
    ),
    AgentRole(
        role_id="planner",
        name="Planner",
        tier=AgentTier.CORE,
        mission=(
            "Create action trees with dependencies, rollback paths, evidence "
            "requirements, reversibility, and stop conditions."
        ),
        activation_rule="Active when a mission boundary permits planning.",
        required_inputs=(ArtifactKind.MISSION_BOUNDARY, ArtifactKind.WORLD_MODEL),
        required_outputs=(ArtifactKind.PLAN_GRAPH,),
        authority_limits=(
            "May propose plans; may not execute, self-approve, or bypass review.",
        ),
        paired_engines=("plan-graph",),
    ),
    AgentRole(
        role_id="skeptic-red-team",
        name="Skeptic / Red Team",
        tier=AgentTier.CORE,
        mission=(
            "Attack plans, claims, assumptions, and incentives to identify failure "
            "modes before approval."
        ),
        activation_rule="Always active before verification or handoff.",
        required_inputs=(ArtifactKind.PLAN_GRAPH, ArtifactKind.UNCERTAINTY_LEDGER),
        required_outputs=(ArtifactKind.FAILURE_MODE_REPORT,),
        authority_limits=(
            "May block readiness by evidence; may not replace verification results.",
        ),
        paired_engines=("reward-auditor", "evaluator"),
    ),
    AgentRole(
        role_id="verifier",
        name="Verifier",
        tier=AgentTier.CORE,
        mission=(
            "Check whether tests, inspections, citations, evidence, and pass/fail "
            "criteria support the claim or plan."
        ),
        activation_rule="Always active before memory update or action handoff.",
        required_inputs=(ArtifactKind.PLAN_GRAPH, ArtifactKind.FAILURE_MODE_REPORT),
        required_outputs=(ArtifactKind.EVIDENCE_CHECK,),
        authority_limits=(
            "May certify evidence state; may not create missing evidence.",
        ),
        paired_engines=("evaluator",),
    ),
    AgentRole(
        role_id="execution-liaison",
        name="Execution Liaison",
        tier=AgentTier.CORE,
        mission=(
            "Package approved plans into bounded, human-reviewable BlackFox "
            "handoff requests."
        ),
        activation_rule=(
            "Active only after verification passes and authority is present."
        ),
        required_inputs=(ArtifactKind.PLAN_GRAPH, ArtifactKind.EVIDENCE_CHECK),
        required_outputs=(ArtifactKind.HANDOFF_PACKAGE,),
        authority_limits=(
            "May package handoffs; may not execute them or approve model output.",
        ),
        paired_engines=("blackfox-handoff",),
    ),
    AgentRole(
        role_id="learning-archivist",
        name="Learning Archivist",
        tier=AgentTier.CORE,
        mission=(
            "Compare prediction with result, classify outcome deltas, and preserve "
            "validated learning without corrupting durable memory."
        ),
        activation_rule="Active after an evaluated outcome exists.",
        required_inputs=(ArtifactKind.WORLD_MODEL, ArtifactKind.EVIDENCE_CHECK),
        required_outputs=(ArtifactKind.OUTCOME_DELTA,),
        authority_limits=(
            "May propose learning updates; may not bypass memory quarantine.",
        ),
        paired_engines=("outcome-learning", "skill-genome"),
    ),
    AgentRole(
        role_id="translator-interpreter",
        name="Translator / Interpreter",
        tier=AgentTier.GOVERNANCE,
        mission=(
            "Render compressed internal state, shorthand, and tribunal artifacts "
            "into human-readable review language."
        ),
        activation_rule="Active when internal communication affects human review.",
        required_inputs=(ArtifactKind.PLAN_GRAPH, ArtifactKind.FAILURE_MODE_REPORT),
        required_outputs=(ArtifactKind.TRANSLATION_RECORD,),
        authority_limits=(
            "May translate meaning; may not hide uncertainty or alter evidence.",
        ),
        paired_engines=("multi-agent-tribunal",),
    ),
    AgentRole(
        role_id="reward-auditor",
        name="Reward Auditor",
        tier=AgentTier.GOVERNANCE,
        mission=(
            "Detect objective mismatch, specification gaming, reward hacking, and "
            "metric-over-mission behavior."
        ),
        activation_rule="Active when success criteria or scoring affect behavior.",
        required_inputs=(ArtifactKind.MISSION_BOUNDARY, ArtifactKind.PLAN_GRAPH),
        required_outputs=(ArtifactKind.REWARD_AUDIT,),
        authority_limits=(
            "May block bad objectives; may not redefine mission without authority.",
        ),
        paired_engines=("reward-auditor",),
    ),
    AgentRole(
        role_id="tool-safety-officer",
        name="Tool-Safety Officer",
        tier=AgentTier.GOVERNANCE,
        mission=(
            "Review tool permission, reversibility, sandboxing, side effects, and "
            "authority boundaries."
        ),
        activation_rule="Active before any tool or external action handoff.",
        required_inputs=(ArtifactKind.MISSION_BOUNDARY, ArtifactKind.PLAN_GRAPH),
        required_outputs=(ArtifactKind.TOOL_SAFETY_REVIEW,),
        authority_limits=("May deny unsafe tool use; may not execute tools directly.",),
        paired_engines=("blackfox-handoff", "non-attached-purpose"),
    ),
    AgentRole(
        role_id="domain-specialist-router",
        name="Domain Specialist Router",
        tier=AgentTier.GOVERNANCE,
        mission=(
            "Summon specialist roles only when the task exceeds the core council's "
            "domain competence."
        ),
        activation_rule=(
            "Active when task domain, risk, or uncertainty requires expertise."
        ),
        required_inputs=(ArtifactKind.UNCERTAINTY_LEDGER,),
        required_outputs=(ArtifactKind.SPECIALIST_ROUTING_DECISION,),
        authority_limits=(
            "May route to specialists; may not let specialists bypass core review.",
        ),
        paired_engines=("multi-agent-tribunal",),
    ),
    AgentRole(
        role_id="software-engineering-specialist",
        name="Software Engineering Specialist",
        tier=AgentTier.SPECIALIST,
        mission=(
            "Assess code architecture, tests, linting, types, dependency impact, CI, "
            "and patch correctness."
        ),
        activation_rule="Summoned for software, repo, CI, or code-repair tasks.",
        required_inputs=(ArtifactKind.PLAN_GRAPH,),
        required_outputs=(ArtifactKind.CODE_REVIEW_RECORD,),
        authority_limits=(
            "May advise code changes; may not weaken tests or self-approve patches.",
        ),
        paired_engines=("evaluator", "blackfox-handoff"),
    ),
    AgentRole(
        role_id="security-threat-specialist",
        name="Security / Threat Specialist",
        tier=AgentTier.SPECIALIST,
        mission=(
            "Identify misuse paths, injection risk, secret exposure, privilege "
            "risk, supply-chain weakness, and unsafe authority."
        ),
        activation_rule="Summoned for security-sensitive code, tools, data, or agents.",
        required_inputs=(ArtifactKind.PLAN_GRAPH, ArtifactKind.TOOL_SAFETY_REVIEW),
        required_outputs=(ArtifactKind.THREAT_MODEL,),
        authority_limits=(
            "May block unsafe paths; may not provide offensive operational steps.",
        ),
        paired_engines=("reward-auditor", "blackfox-handoff"),
    ),
    AgentRole(
        role_id="science-physics-specialist",
        name="Science / Physics Specialist",
        tier=AgentTier.SPECIALIST,
        mission=(
            "Check energy accounting, measurement validity, physical constraints, "
            "controls, and no-claim-without-proof discipline."
        ),
        activation_rule=(
            "Summoned for physical-world, energy, sensor, or experiment tasks."
        ),
        required_inputs=(ArtifactKind.WORLD_MODEL, ArtifactKind.EVIDENCE_CHECK),
        required_outputs=(ArtifactKind.PHYSICAL_VALIDATION_RECORD,),
        authority_limits=(
            "May reject unmeasured physical claims; may not certify hardware safety.",
        ),
        paired_engines=("causal-world-model", "evaluator"),
    ),
    AgentRole(
        role_id="math-formal-methods-specialist",
        name="Math / Formal Methods Specialist",
        tier=AgentTier.SPECIALIST,
        mission=(
            "Check invariants, logical consistency, edge cases, numerical validity, "
            "and proof obligations."
        ),
        activation_rule=(
            "Summoned when formal constraints or mathematical validity matter."
        ),
        required_inputs=(ArtifactKind.PLAN_GRAPH, ArtifactKind.EVIDENCE_CHECK),
        required_outputs=(ArtifactKind.FORMAL_CHECK_RECORD,),
        authority_limits=(
            "May identify proof gaps; may not claim proof without a checkable method.",
        ),
        paired_engines=("evaluator",),
    ),
    AgentRole(
        role_id="data-provenance-specialist",
        name="Data / Provenance Specialist",
        tier=AgentTier.SPECIALIST,
        mission=(
            "Track source lineage, timestamps, dataset quality, transformations, "
            "and evidence-chain integrity."
        ),
        activation_rule="Summoned when external data or evidence lineage matters.",
        required_inputs=(ArtifactKind.BELIEF_RECORD,),
        required_outputs=(ArtifactKind.PROVENANCE_RECORD,),
        authority_limits=(
            "May assess provenance; may not invent missing source lineage.",
        ),
        paired_engines=("belief", "evaluator"),
    ),
    AgentRole(
        role_id="memory-integrity-specialist",
        name="Memory Integrity Specialist",
        tier=AgentTier.SPECIALIST,
        mission=(
            "Decide whether proposed memories should be stored, quarantined, "
            "decayed, corrected, or rejected."
        ),
        activation_rule="Summoned before durable memory or skill updates.",
        required_inputs=(ArtifactKind.OUTCOME_DELTA, ArtifactKind.PROVENANCE_RECORD),
        required_outputs=(ArtifactKind.MEMORY_INTEGRITY_DECISION,),
        authority_limits=(
            "May quarantine memory; may not force unvalidated memory persistence.",
        ),
        paired_engines=("memory-quarantine", "skill-genome"),
    ),
    AgentRole(
        role_id="simulation-worldtwin-critic",
        name="Simulation / WorldTwin Critic",
        tier=AgentTier.SPECIALIST,
        mission=(
            "Attack simulations for missing variables, unrealistic assumptions, "
            "overfit scenarios, and fragile conclusions."
        ),
        activation_rule="Summoned whenever simulation or WorldTwin reasoning is used.",
        required_inputs=(ArtifactKind.WORLD_MODEL,),
        required_outputs=(ArtifactKind.SIMULATION_CRITIQUE,),
        authority_limits=(
            "May downgrade simulation confidence; may not treat simulation as reality.",
        ),
        paired_engines=("causal-world-model", "evaluator"),
    ),
    AgentRole(
        role_id="human-factors-ux-specialist",
        name="Human Factors / UX Specialist",
        tier=AgentTier.SPECIALIST,
        mission=(
            "Ensure human reviewers can understand, challenge, and decide from the "
            "system's artifacts without automation bias."
        ),
        activation_rule="Summoned for human review, dashboards, reports, or approvals.",
        required_inputs=(ArtifactKind.TRANSLATION_RECORD, ArtifactKind.EVIDENCE_CHECK),
        required_outputs=(ArtifactKind.HUMAN_REVIEW_USABILITY_REPORT,),
        authority_limits=(
            "May improve review clarity; may not remove critical uncertainty.",
        ),
        paired_engines=("multi-agent-tribunal", "blackfox-handoff"),
    ),
    AgentRole(
        role_id="legal-licensing-compliance-specialist",
        name="Legal / Licensing / Compliance Specialist",
        tier=AgentTier.SPECIALIST,
        mission=(
            "Check license posture, attribution, source-available boundaries, "
            "compliance wording, and false-affiliation risk."
        ),
        activation_rule=(
            "Summoned for publication, licensing, reuse, or compliance tasks."
        ),
        required_inputs=(ArtifactKind.MISSION_BOUNDARY,),
        required_outputs=(ArtifactKind.LICENSE_COMPLIANCE_REVIEW,),
        authority_limits=(
            "May flag legal risk; may not provide formal legal representation.",
        ),
        paired_engines=("non-attached-purpose",),
    ),
    AgentRole(
        role_id="cost-budget-resource-controller",
        name="Cost / Budget / Resource Controller",
        tier=AgentTier.SPECIALIST,
        mission=(
            "Track compute, token, time, energy, hardware, and opportunity costs "
            "so tests remain proportionate and useful."
        ),
        activation_rule="Summoned when resource cost or budget constraints matter.",
        required_inputs=(ArtifactKind.PLAN_GRAPH,),
        required_outputs=(ArtifactKind.RESOURCE_BUDGET_REVIEW,),
        authority_limits=(
            "May recommend cheaper tests; may not override safety requirements.",
        ),
        paired_engines=("self-play-curriculum", "evaluator"),
    ),
    AgentRole(
        role_id="recovery-rollback-planner",
        name="Recovery / Rollback Planner",
        tier=AgentTier.SPECIALIST,
        mission=(
            "Plan restore points, safe states, reversal paths, failure containment, "
            "and recovery validation before risky action."
        ),
        activation_rule="Summoned when actions may alter code, systems, or state.",
        required_inputs=(ArtifactKind.PLAN_GRAPH, ArtifactKind.TOOL_SAFETY_REVIEW),
        required_outputs=(ArtifactKind.ROLLBACK_PLAN,),
        authority_limits=(
            "May block irreversible action; may not execute recovery directly.",
        ),
        paired_engines=("plan-graph", "blackfox-handoff"),
    ),
    AgentRole(
        role_id="adversarial-prompt-deception-monitor",
        name="Adversarial Prompt / Deception Monitor",
        tier=AgentTier.SPECIALIST,
        mission=(
            "Detect prompt injection, tool-output manipulation, collusion, hidden "
            "instructions, deceptive reasoning, and alignment-faking risk."
        ),
        activation_rule=(
            "Summoned for adversarial input, tools, agents, or high-risk review."
        ),
        required_inputs=(ArtifactKind.PLAN_GRAPH, ArtifactKind.FAILURE_MODE_REPORT),
        required_outputs=(ArtifactKind.DECEPTION_MONITOR_REPORT,),
        authority_limits=(
            "May force review escalation; may not accuse deception without evidence.",
        ),
        paired_engines=("reward-auditor", "multi-agent-tribunal"),
    ),
)


def agent_by_id(role_id: str) -> AgentRole:
    """Return an agent role by stable role id."""

    for role in AGENT_ROLES:
        if role.role_id == role_id:
            return role
    raise ValueError(f"Unknown IX-CognitionKernel agent role id: {role_id}")


def agent_ids() -> tuple[str, ...]:
    """Return locked agent ids in registry order."""

    return tuple(role.role_id for role in AGENT_ROLES)


def agent_names() -> tuple[str, ...]:
    """Return locked agent names in registry order."""

    return tuple(role.name for role in AGENT_ROLES)


def agents_by_tier(tier: AgentTier) -> tuple[AgentRole, ...]:
    """Return all agent roles matching a tier."""

    return tuple(role for role in AGENT_ROLES if role.tier is tier)


def required_output_artifacts() -> tuple[ArtifactKind, ...]:
    """Return every output artifact required by the agent role registry."""

    return tuple(artifact for role in AGENT_ROLES for artifact in role.required_outputs)


def roles_paired_with_engine(engine_id: str) -> tuple[AgentRole, ...]:
    """Return roles paired with a cognition engine id."""

    return tuple(role for role in AGENT_ROLES if engine_id in role.paired_engines)
