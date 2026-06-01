"""Wave 1 research prototype snapshot for IX-CognitionKernel.

This module ties the Wave 1 structured records together without changing the
package's public maturity identity yet. The snapshot is an integration object: it
can hold beliefs, evidence, causal assumptions, simple plan graphs, evaluation
records, non-attached purpose checks, bounded agent roles, and the Wave 1
maturity state as reviewable code.

It does not execute plans, learn from outcomes, persist durable memory, produce
BlackFox handoffs, or claim AGI.
"""

from __future__ import annotations

from dataclasses import dataclass

from ix_cognition_kernel.agents import AgentRole, agent_by_id
from ix_cognition_kernel.causal import SimpleCausalModel
from ix_cognition_kernel.doctrine import (
    WaveDefinition,
    allows_agi_claim,
    wave_by_number,
)
from ix_cognition_kernel.evaluation import EvaluationLedger
from ix_cognition_kernel.planning import SimplePlanGraph
from ix_cognition_kernel.purpose import NonAttachedPurposeAssessment
from ix_cognition_kernel.state import BeliefState, EvidenceRecord

WAVE_ONE_REQUIRED_ARTIFACT_IDS: tuple[str, ...] = (
    "belief-state",
    "causal-model",
    "plan-graph",
    "evaluation-ledger",
    "purpose-assessment",
    "bounded-agent-roles",
    "maturity-state",
)

WAVE_ONE_REQUIRED_ROLE_IDS: tuple[str, ...] = (
    "mission-governor",
    "belief-curator",
    "unknowns-hunter",
    "world-modeler",
    "planner",
    "verifier",
)


@dataclass(frozen=True, slots=True)
class ResearchPrototypeSnapshot:
    """Integrated Wave 1 cognition snapshot with fail-closed readiness checks."""

    project_name: str
    maturity_wave: WaveDefinition
    belief_state: BeliefState
    causal_model: SimpleCausalModel
    plan_graph: SimplePlanGraph
    evaluation_ledger: EvaluationLedger
    purpose_assessment: NonAttachedPurposeAssessment
    agent_role_ids: tuple[str, ...]
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate the Wave 1 snapshot's identity and structural completeness."""

        if self.project_name != "IX-CognitionKernel":
            raise ValueError(
                "Research prototype snapshots must use IX-CognitionKernel."
            )
        if self.maturity_wave.number != 1:
            raise ValueError("Research prototype snapshots must target Wave 1.")
        if not self.belief_state.beliefs:
            raise ValueError("Research prototype snapshots require beliefs.")
        if not self.belief_state.evidence:
            raise ValueError("Research prototype snapshots require evidence.")
        if not self.causal_model.assumptions:
            raise ValueError("Research prototype snapshots require causal assumptions.")
        if not self.plan_graph.nodes:
            raise ValueError("Research prototype snapshots require plan graph nodes.")
        if not self.evaluation_ledger.records:
            raise ValueError("Research prototype snapshots require evaluation records.")
        self._validate_agent_roles()

    @property
    def wave_label(self) -> str:
        """Return the target Wave 1 maturity label."""

        return self.maturity_wave.label

    @property
    def evidence_records(self) -> tuple[EvidenceRecord, ...]:
        """Return the evidence records attached to the belief state."""

        return self.belief_state.evidence

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return evidence ids attached to this integrated snapshot."""

        return tuple(record.evidence_id for record in self.evidence_records)

    @property
    def bounded_agent_roles(self) -> tuple[AgentRole, ...]:
        """Return the bounded agent roles represented by this snapshot."""

        return tuple(agent_by_id(role_id) for role_id in self.agent_role_ids)

    @property
    def missing_required_role_ids(self) -> tuple[str, ...]:
        """Return required Wave 1 role ids missing from the snapshot."""

        present = set(self.agent_role_ids)
        return tuple(
            role_id for role_id in WAVE_ONE_REQUIRED_ROLE_IDS if role_id not in present
        )

    @property
    def missing_required_artifact_evaluations(self) -> tuple[str, ...]:
        """Return required Wave 1 artifacts without passing evaluation coverage."""

        return tuple(
            artifact_id
            for artifact_id in WAVE_ONE_REQUIRED_ARTIFACT_IDS
            if not self.evaluation_ledger.artifact_is_passing(artifact_id)
        )

    @property
    def permits_agi_claim(self) -> bool:
        """Return whether this Wave 1 snapshot permits an AGI claim."""

        return allows_agi_claim(
            self.maturity_wave.number,
            overwhelming_evidence=False,
        )

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return fail-closed gaps that prevent a clean Wave 1 readiness claim."""

        gaps: list[str] = []
        if self.belief_state.beliefs_requiring_evidence:
            gaps.append("belief-state has beliefs requiring evidence")
        if self.belief_state.blocked_beliefs:
            gaps.append("belief-state has blocked beliefs")
        if self.causal_model.assumptions_requiring_evidence:
            gaps.append("causal-model has assumptions requiring evidence")
        if self.causal_model.blocked_assumptions:
            gaps.append("causal-model has blocked assumptions")
        if self.causal_model.observations_still_needed:
            gaps.append("causal-model has required observations still needed")
        if self.plan_graph.unmet_evidence_requirements:
            gaps.append("plan-graph has unmet evidence requirements")
        if self.plan_graph.blocked_nodes:
            gaps.append("plan-graph has blocked nodes")
        if self.evaluation_ledger.blocking_records:
            gaps.append("evaluation-ledger has blocking records")
        if self.purpose_assessment.violations:
            gaps.append("purpose-assessment has doctrine violations")
        if self.missing_required_role_ids:
            gaps.append("bounded-agent-roles missing required Wave 1 roles")
        if self.missing_required_artifact_evaluations:
            gaps.append("evaluation-ledger missing required artifact coverage")
        if self.permits_agi_claim:
            gaps.append("maturity-state improperly permits AGI claim")
        return tuple(gaps)

    @property
    def is_wave_one_ready(self) -> bool:
        """Return whether the snapshot is structurally ready for a Wave 1 claim."""

        return not self.readiness_gaps

    def _validate_agent_roles(self) -> None:
        """Validate agent role ids and duplicate role references."""

        if not self.agent_role_ids:
            raise ValueError("Research prototype snapshots require agent role ids.")
        seen: set[str] = set()
        for role_id in self.agent_role_ids:
            if role_id in seen:
                raise ValueError(f"Duplicate agent role id detected: {role_id}")
            agent_by_id(role_id)
            seen.add(role_id)


def wave_one_research_prototype_snapshot(
    *,
    belief_state: BeliefState,
    causal_model: SimpleCausalModel,
    plan_graph: SimplePlanGraph,
    evaluation_ledger: EvaluationLedger,
    purpose_assessment: NonAttachedPurposeAssessment,
    agent_role_ids: tuple[str, ...] = WAVE_ONE_REQUIRED_ROLE_IDS,
    notes: tuple[str, ...] = (),
) -> ResearchPrototypeSnapshot:
    """Create an integrated Wave 1 research prototype snapshot."""

    return ResearchPrototypeSnapshot(
        project_name="IX-CognitionKernel",
        maturity_wave=wave_by_number(1),
        belief_state=belief_state,
        causal_model=causal_model,
        plan_graph=plan_graph,
        evaluation_ledger=evaluation_ledger,
        purpose_assessment=purpose_assessment,
        agent_role_ids=agent_role_ids,
        notes=notes,
    )
