"""Integrated learnable cognition cycle for IX-CognitionKernel Wave 2.

Wave 2 only becomes real when the learning pieces work together. This module
runs a bounded, reviewable cycle that updates belief state, builds belief
history, compares predictions to observations, revises causal assumptions,
creates outcome learning records, evaluates memory quarantine, and validates
skill candidates. It does not execute plans, persist memory, call tools, bypass
human authority, or claim AGI.
"""

from __future__ import annotations

from dataclasses import dataclass

from ix_cognition_kernel.causal import SimpleCausalModel
from ix_cognition_kernel.history import BeliefHistory, build_belief_history
from ix_cognition_kernel.learning import (
    BeliefUpdateResult,
    UpdateLedger,
    apply_belief_updates,
)
from ix_cognition_kernel.memory import (
    MemoryCandidate,
    MemoryQuarantineLedger,
    evaluate_memory_quarantine,
)
from ix_cognition_kernel.observations import (
    ObservationLedger,
    PredictionComparisonLedger,
    compare_prediction_set_to_observations,
)
from ix_cognition_kernel.outcome import (
    OutcomeLearningLedger,
    OutcomeLearningRecord,
    OutcomeLearningStatus,
    build_outcome_learning_record,
    outcome_learning_ledger,
)
from ix_cognition_kernel.prediction import CausalPredictionSet
from ix_cognition_kernel.revision import CausalRevisionResult, revise_causal_assumptions
from ix_cognition_kernel.skills import (
    SkillCandidate,
    SkillReuseEvidenceRecord,
    SkillValidationLedger,
    evaluate_skill_candidates,
)
from ix_cognition_kernel.state import BeliefState


@dataclass(frozen=True, slots=True)
class LearnableCognitionCycleInput:
    """Inputs required to run one bounded Wave 2 learning cycle."""

    belief_state: BeliefState
    causal_model: SimpleCausalModel
    update_ledger: UpdateLedger
    prediction_set: CausalPredictionSet
    observation_ledger: ObservationLedger
    memory_candidates: tuple[MemoryCandidate, ...]
    skill_candidates: tuple[SkillCandidate, ...]
    skill_reuse_records: tuple[SkillReuseEvidenceRecord, ...]
    outcome_id: str
    outcome_summary: str
    outcome_evidence_ids: tuple[str, ...]
    current_audit_index: int

    def __post_init__(self) -> None:
        """Validate cycle identity, evidence, and audit bounds."""

        if not self.outcome_id.strip():
            raise ValueError("Learning cycle inputs require a non-empty outcome_id.")
        if not self.outcome_summary.strip():
            raise ValueError(
                "Learning cycle inputs require a non-empty outcome_summary."
            )
        if self.current_audit_index < 0:
            raise ValueError("Learning cycle current_audit_index cannot be negative.")
        if len(set(self.outcome_evidence_ids)) != len(self.outcome_evidence_ids):
            raise ValueError("Learning cycle outcome_evidence_ids must be unique.")
        if self.prediction_set.source_model_id != self.causal_model.model_id:
            raise ValueError(
                "Learning cycle prediction_set must reference the causal_model id."
            )


@dataclass(frozen=True, slots=True)
class LearnableCognitionCycleResult:
    """Integrated result of one bounded Wave 2 learning cycle."""

    cycle_input: LearnableCognitionCycleInput
    belief_update_result: BeliefUpdateResult
    belief_history: BeliefHistory
    prediction_comparison_ledger: PredictionComparisonLedger
    causal_revision_result: CausalRevisionResult
    outcome_record: OutcomeLearningRecord
    outcome_ledger: OutcomeLearningLedger
    memory_ledger: MemoryQuarantineLedger
    skill_ledger: SkillValidationLedger

    @property
    def after_belief_state(self) -> BeliefState:
        """Return belief state after evidence-driven updates."""

        return self.belief_update_result.after_state

    @property
    def after_causal_model(self) -> SimpleCausalModel:
        """Return causal model after prediction-comparison revisions."""

        return self.causal_revision_result.after_model

    @property
    def changed_belief_ids(self) -> tuple[str, ...]:
        """Return belief ids changed during this cycle."""

        return self.belief_update_result.changed_belief_ids

    @property
    def changed_assumption_ids(self) -> tuple[str, ...]:
        """Return causal assumption ids changed during this cycle."""

        return self.causal_revision_result.changed_assumption_ids

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return fail-closed gaps in the integrated Wave 2 cycle."""

        gaps: list[str] = []
        if not self.belief_update_result.updates:
            gaps.append("belief-update-result has no belief updates")
        if not self.belief_history.all_revisions:
            gaps.append("belief-history has no revisions")
        if not self.prediction_comparison_ledger.comparisons:
            gaps.append("prediction-comparison-ledger has no comparisons")
        if not self.causal_revision_result.revisions:
            gaps.append("causal-revision-result has no revisions")
        if self.outcome_record.status is not OutcomeLearningStatus.ACCEPTED:
            gaps.append("outcome-learning-record is not accepted")
        if self.memory_ledger.blocking_validations:
            gaps.append("memory-quarantine-ledger has blocking validations")
        if self.cycle_input.memory_candidates and len(
            self.memory_ledger.accepted_candidates
        ) != len(self.cycle_input.memory_candidates):
            gaps.append("memory-quarantine-ledger did not accept every candidate")
        if self.skill_ledger.blocking_validations:
            gaps.append("skill-validation-ledger has blocking validations")
        if self.cycle_input.skill_candidates and len(
            self.skill_ledger.validated_candidates
        ) != len(self.cycle_input.skill_candidates):
            gaps.append("skill-validation-ledger did not validate every candidate")
        return tuple(gaps)

    @property
    def is_complete_learning_cycle(self) -> bool:
        """Return whether the integrated cycle has no readiness gaps."""

        return not self.readiness_gaps


def run_learnable_cognition_cycle(
    cycle_input: LearnableCognitionCycleInput,
) -> LearnableCognitionCycleResult:
    """Run one integrated, reviewable Wave 2 learning cycle."""

    belief_update_result = apply_belief_updates(
        cycle_input.belief_state,
        cycle_input.update_ledger,
        current_audit_index=cycle_input.current_audit_index,
    )
    belief_history = build_belief_history(belief_update_result)
    prediction_comparison_ledger = compare_prediction_set_to_observations(
        prediction_set=cycle_input.prediction_set,
        observations=cycle_input.observation_ledger,
    )
    causal_revision_result = revise_causal_assumptions(
        cycle_input.causal_model,
        prediction_comparison_ledger,
    )
    outcome_record = build_outcome_learning_record(
        outcome_id=cycle_input.outcome_id,
        summary=cycle_input.outcome_summary,
        belief_history=belief_history,
        causal_revision_result=causal_revision_result,
        comparison_ledger=prediction_comparison_ledger,
        evidence_ids=cycle_input.outcome_evidence_ids,
    )
    outcome_ledger = outcome_learning_ledger(outcome_record)
    memory_ledger = evaluate_memory_quarantine(
        candidates=cycle_input.memory_candidates,
        outcome_ledger=outcome_ledger,
        current_audit_index=cycle_input.current_audit_index,
    )
    skill_ledger = evaluate_skill_candidates(
        candidates=cycle_input.skill_candidates,
        reuse_records=cycle_input.skill_reuse_records,
        memory_ledger=memory_ledger,
        outcome_ledger=outcome_ledger,
    )
    return LearnableCognitionCycleResult(
        cycle_input=cycle_input,
        belief_update_result=belief_update_result,
        belief_history=belief_history,
        prediction_comparison_ledger=prediction_comparison_ledger,
        causal_revision_result=causal_revision_result,
        outcome_record=outcome_record,
        outcome_ledger=outcome_ledger,
        memory_ledger=memory_ledger,
        skill_ledger=skill_ledger,
    )
