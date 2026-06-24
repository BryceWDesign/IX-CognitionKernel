"""Wave 7 prediction-outcome lifecycle.

This module makes the prediction -> trial -> measured outcome -> delta ->
experience path explicit. It is intentionally separate from the experience
compiler so Wave 7 can inspect the prediction lifecycle before memory updates,
future constraints, or organism scorecards are allowed to treat the result as
mature.

Lifecycle doctrine:

- prediction is not truth,
- confidence is not evidence,
- assumptions must remain visible,
- trials must be bounded,
- unmeasured outcomes cannot produce trusted learning,
- mismatches must preserve corrective lessons,
- deployment authority is never created by the lifecycle itself.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from ix_cognition_kernel.wave7_experience_compiler import ExperienceRecord
from ix_cognition_kernel.wave7_observation_action_schema import (
    ObservationActionTrace,
    OutcomeAlignment,
)

WAVE_SEVEN_BOUNDED_PREDICTION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-bounded-prediction-v1"
)
WAVE_SEVEN_PREDICTION_EVIDENCE_GATE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-prediction-evidence-gate-v1"
)
WAVE_SEVEN_TRIAL_PLAN_SCHEMA_VERSION = "ix-cognition-kernel-wave7-trial-plan-v1"
WAVE_SEVEN_OUTCOME_DELTA_REVIEW_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-outcome-delta-review-v1"
)
WAVE_SEVEN_PREDICTION_OUTCOME_LIFECYCLE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-prediction-outcome-lifecycle-v1"
)
WAVE_SEVEN_PREDICTION_LIFECYCLE_REPORT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-prediction-lifecycle-report-v1"
)


class PredictionConfidence(StrEnum):
    """Evidence-aware confidence tier for a bounded prediction."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class PredictionLifecycleDecision(StrEnum):
    """Fail-closed decision for a prediction-outcome lifecycle."""

    DRAFT = "draft"
    READY_FOR_REVIEW = "ready-for-review"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    NEEDS_MEASURED_OUTCOME = "needs-measured-outcome"
    BLOCKED = "blocked"


class TrialBoundary(StrEnum):
    """Boundary type for a prediction trial plan."""

    SIMULATION_ONLY = "simulation-only"
    REVIEW_PACKET_ONLY = "review-packet-only"
    OBSERVATION_ONLY = "observation-only"
    HUMAN_REVIEW_ONLY = "human-review-only"


class OutcomeDeltaSeverity(StrEnum):
    """Severity of prediction-outcome delta."""

    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    BLOCKING = "blocking"


@dataclass(frozen=True, slots=True)
class BoundedPrediction:
    """Prediction with explicit assumptions, uncertainty, and claim scope."""

    prediction_id: str
    subject_id: str
    predicted_outcome: str
    claim_scope: str
    assumptions: tuple[str, ...]
    uncertainty_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    confidence: PredictionConfidence = PredictionConfidence.LOW
    claims_truth: bool = False
    grants_execution_authority: bool = False
    schema_version: str = WAVE_SEVEN_BOUNDED_PREDICTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate prediction boundaries and reject authority inflation."""

        if self.claims_truth:
            raise ValueError("Bounded predictions must not claim truth.")
        if self.grants_execution_authority:
            raise ValueError("Bounded predictions must not grant execution authority.")
        object.__setattr__(
            self,
            "prediction_id",
            _require_non_empty(self.prediction_id, "prediction_id"),
        )
        object.__setattr__(
            self,
            "subject_id",
            _require_non_empty(self.subject_id, "subject_id"),
        )
        object.__setattr__(
            self,
            "predicted_outcome",
            _require_non_empty(self.predicted_outcome, "predicted_outcome"),
        )
        object.__setattr__(
            self,
            "claim_scope",
            _require_non_empty(self.claim_scope, "claim_scope"),
        )
        object.__setattr__(
            self,
            "assumptions",
            _normalize_unique_text_tuple(self.assumptions, label="assumption"),
        )
        object.__setattr__(
            self,
            "uncertainty_ids",
            _normalize_unique_text_tuple(self.uncertainty_ids, label="uncertainty_id"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.assumptions:
            raise ValueError("Bounded predictions require assumptions.")
        if not self.uncertainty_ids:
            raise ValueError("Bounded predictions require uncertainty ids.")
        if not self.evidence_ids:
            raise ValueError("Bounded predictions require evidence ids.")

    @property
    def review_required(self) -> bool:
        """Return whether prediction confidence requires review before use."""

        return self.confidence is PredictionConfidence.HIGH

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic prediction payload."""

        return {
            "assumptions": list(self.assumptions),
            "claim_scope": self.claim_scope,
            "claims_truth": self.claims_truth,
            "confidence": self.confidence.value,
            "evidence_ids": list(self.evidence_ids),
            "grants_execution_authority": self.grants_execution_authority,
            "predicted_outcome": self.predicted_outcome,
            "prediction_id": self.prediction_id,
            "schema_version": self.schema_version,
            "subject_id": self.subject_id,
            "uncertainty_ids": list(self.uncertainty_ids),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this prediction."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class PredictionEvidenceGate:
    """Evidence gate that controls whether a prediction may enter trial."""

    gate_id: str
    prediction_id: str
    required_evidence_ids: tuple[str, ...]
    supplied_evidence_ids: tuple[str, ...]
    authority_refs: tuple[str, ...]
    evidence_notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SEVEN_PREDICTION_EVIDENCE_GATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate prediction evidence gate."""

        object.__setattr__(
            self,
            "gate_id",
            _require_non_empty(self.gate_id, "gate_id"),
        )
        object.__setattr__(
            self,
            "prediction_id",
            _require_non_empty(self.prediction_id, "prediction_id"),
        )
        object.__setattr__(
            self,
            "required_evidence_ids",
            _normalize_unique_text_tuple(
                self.required_evidence_ids, label="required_evidence_id"
            ),
        )
        object.__setattr__(
            self,
            "supplied_evidence_ids",
            _normalize_unique_text_tuple(
                self.supplied_evidence_ids, label="supplied_evidence_id"
            ),
        )
        object.__setattr__(
            self,
            "authority_refs",
            _normalize_unique_text_tuple(self.authority_refs, label="authority_ref"),
        )
        object.__setattr__(
            self,
            "evidence_notes",
            _normalize_unique_text_tuple(self.evidence_notes, label="evidence_note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.required_evidence_ids:
            raise ValueError("Prediction evidence gates require evidence ids.")
        if not self.authority_refs:
            raise ValueError("Prediction evidence gates require authority refs.")

    @property
    def missing_evidence_ids(self) -> tuple[str, ...]:
        """Return required evidence ids not supplied."""

        supplied = set(self.supplied_evidence_ids)
        return tuple(
            evidence_id
            for evidence_id in self.required_evidence_ids
            if evidence_id not in supplied
        )

    @property
    def satisfied(self) -> bool:
        """Return whether all required evidence is present."""

        return not self.missing_evidence_ids

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic evidence-gate payload."""

        return {
            "authority_refs": list(self.authority_refs),
            "evidence_notes": list(self.evidence_notes),
            "gate_id": self.gate_id,
            "missing_evidence_ids": list(self.missing_evidence_ids),
            "prediction_id": self.prediction_id,
            "required_evidence_ids": list(self.required_evidence_ids),
            "schema_version": self.schema_version,
            "supplied_evidence_ids": list(self.supplied_evidence_ids),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this gate."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class PredictionTrialPlan:
    """Bounded trial plan used to test a prediction."""

    trial_id: str
    prediction_id: str
    boundary: TrialBoundary
    operation: str
    success_criteria: tuple[str, ...]
    failure_criteria: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    authority_refs: tuple[str, ...]
    permits_deployment: bool = False
    schema_version: str = WAVE_SEVEN_TRIAL_PLAN_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate trial plan boundaries."""

        if self.permits_deployment:
            raise ValueError("Prediction trial plans must not permit deployment.")
        object.__setattr__(
            self,
            "trial_id",
            _require_non_empty(self.trial_id, "trial_id"),
        )
        object.__setattr__(
            self,
            "prediction_id",
            _require_non_empty(self.prediction_id, "prediction_id"),
        )
        object.__setattr__(
            self,
            "operation",
            _require_non_empty(self.operation, "operation"),
        )
        object.__setattr__(
            self,
            "success_criteria",
            _normalize_unique_text_tuple(
                self.success_criteria, label="success_criterion"
            ),
        )
        object.__setattr__(
            self,
            "failure_criteria",
            _normalize_unique_text_tuple(
                self.failure_criteria, label="failure_criterion"
            ),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "authority_refs",
            _normalize_unique_text_tuple(self.authority_refs, label="authority_ref"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.success_criteria:
            raise ValueError("Prediction trial plans require success criteria.")
        if not self.failure_criteria:
            raise ValueError("Prediction trial plans require failure criteria.")
        if not self.evidence_ids:
            raise ValueError("Prediction trial plans require evidence ids.")
        if not self.authority_refs:
            raise ValueError("Prediction trial plans require authority refs.")

    @property
    def simulation_only(self) -> bool:
        """Return whether the trial is simulation-only."""

        return self.boundary is TrialBoundary.SIMULATION_ONLY

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic trial-plan payload."""

        return {
            "authority_refs": list(self.authority_refs),
            "boundary": self.boundary.value,
            "evidence_ids": list(self.evidence_ids),
            "failure_criteria": list(self.failure_criteria),
            "operation": self.operation,
            "permits_deployment": self.permits_deployment,
            "prediction_id": self.prediction_id,
            "schema_version": self.schema_version,
            "success_criteria": list(self.success_criteria),
            "trial_id": self.trial_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this trial plan."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class OutcomeDeltaReview:
    """Review summary of how a measured outcome changed the prediction."""

    review_id: str
    prediction_id: str
    trace_id: str
    alignment: OutcomeAlignment
    severity: OutcomeDeltaSeverity
    summary: str
    evidence_ids: tuple[str, ...]
    lesson: str = ""
    schema_version: str = WAVE_SEVEN_OUTCOME_DELTA_REVIEW_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate outcome-delta review evidence and lesson discipline."""

        object.__setattr__(
            self,
            "review_id",
            _require_non_empty(self.review_id, "review_id"),
        )
        object.__setattr__(
            self,
            "prediction_id",
            _require_non_empty(self.prediction_id, "prediction_id"),
        )
        object.__setattr__(
            self,
            "trace_id",
            _require_non_empty(self.trace_id, "trace_id"),
        )
        object.__setattr__(
            self,
            "summary",
            _require_non_empty(self.summary, "summary"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(self, "lesson", _normalize_optional_text(self.lesson))
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Outcome delta reviews require evidence ids.")
        if self.alignment is OutcomeAlignment.NOT_MEASURED:
            raise ValueError("Outcome delta reviews require measured outcomes.")
        if self.severity is OutcomeDeltaSeverity.NONE and (
            self.alignment is not OutcomeAlignment.MATCHED
        ):
            raise ValueError("Only matched outcomes may have no delta severity.")
        if (
            self.severity
            in {
                OutcomeDeltaSeverity.MODERATE,
                OutcomeDeltaSeverity.HIGH,
                OutcomeDeltaSeverity.BLOCKING,
            }
            and not self.lesson
        ):
            raise ValueError("Material delta reviews require a lesson.")

    @property
    def blocks_claim(self) -> bool:
        """Return whether this review blocks stronger maturity claims."""

        return self.severity in {
            OutcomeDeltaSeverity.HIGH,
            OutcomeDeltaSeverity.BLOCKING,
        }

    @property
    def changes_future_reasoning(self) -> bool:
        """Return whether the review contains a lesson."""

        return bool(self.lesson)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic outcome-review payload."""

        return {
            "alignment": self.alignment.value,
            "evidence_ids": list(self.evidence_ids),
            "lesson": self.lesson,
            "prediction_id": self.prediction_id,
            "review_id": self.review_id,
            "schema_version": self.schema_version,
            "severity": self.severity.value,
            "summary": self.summary,
            "trace_id": self.trace_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this review."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class PredictionOutcomeLifecycle:
    """Complete lifecycle tying prediction, gate, trial, trace, and experience."""

    lifecycle_id: str
    prediction: BoundedPrediction
    evidence_gate: PredictionEvidenceGate
    trial_plan: PredictionTrialPlan
    trace: ObservationActionTrace | None
    outcome_review: OutcomeDeltaReview | None
    experience_record: ExperienceRecord | None
    decision: PredictionLifecycleDecision
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SEVEN_PREDICTION_OUTCOME_LIFECYCLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate lifecycle linkage and fail-closed status."""

        object.__setattr__(
            self,
            "lifecycle_id",
            _require_non_empty(self.lifecycle_id, "lifecycle_id"),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if self.evidence_gate.prediction_id != self.prediction.prediction_id:
            raise ValueError("Evidence gate must reference prediction id.")
        if self.trial_plan.prediction_id != self.prediction.prediction_id:
            raise ValueError("Trial plan must reference prediction id.")
        if self.outcome_review:
            if self.outcome_review.prediction_id != self.prediction.prediction_id:
                raise ValueError("Outcome review must reference prediction id.")
            if self.trace and self.outcome_review.trace_id != self.trace.trace_id:
                raise ValueError("Outcome review must reference trace id.")
        if (
            self.experience_record
            and self.trace
            and self.experience_record.trace.trace_id != self.trace.trace_id
        ):
            raise ValueError("Experience record must reference trace id.")
        if self.decision is PredictionLifecycleDecision.READY_FOR_REVIEW:
            if not self.trace or not self.trace.measured:
                raise ValueError("Review-ready lifecycle requires measured trace.")
            if not self.outcome_review:
                raise ValueError("Review-ready lifecycle requires outcome review.")
            if not self.experience_record:
                raise ValueError("Review-ready lifecycle requires experience record.")
            if not self.evidence_gate.satisfied:
                raise ValueError("Review-ready lifecycle requires satisfied gate.")
        if (
            self.decision is PredictionLifecycleDecision.NEEDS_MEASURED_OUTCOME
            and self.trace
            and self.trace.measured
        ):
            raise ValueError("Measured lifecycle cannot need measured outcome.")
        if (
            self.decision is PredictionLifecycleDecision.BLOCKED
            and not self.blocking_reason_ids
        ):
            raise ValueError("Blocked lifecycle requires blocking reasons.")

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound to this lifecycle."""

        evidence: list[str] = list(self.prediction.evidence_ids)
        evidence.extend(self.evidence_gate.supplied_evidence_ids)
        evidence.extend(self.trial_plan.evidence_ids)
        if self.trace:
            evidence.extend(self.trace.evidence_ids)
        if self.outcome_review:
            evidence.extend(self.outcome_review.evidence_ids)
        if self.experience_record:
            evidence.extend(self.experience_record.evidence_ids)
        return _dedupe_text_tuple(evidence, label="evidence_id")

    @property
    def missing_evidence_ids(self) -> tuple[str, ...]:
        """Return missing evidence ids from the prediction gate."""

        return self.evidence_gate.missing_evidence_ids

    @property
    def blocking_reason_ids(self) -> tuple[str, ...]:
        """Return lifecycle reasons that block stronger claims."""

        reasons: list[str] = []
        if self.missing_evidence_ids:
            reasons.append("missing-prediction-evidence")
        if self.prediction.claims_truth:
            reasons.append("prediction-claims-truth")
        if self.prediction.grants_execution_authority:
            reasons.append("prediction-grants-execution-authority")
        if self.trace and self.trace.blocks_claim:
            reasons.append("trace-blocks-claim")
        if self.outcome_review and self.outcome_review.blocks_claim:
            reasons.append("outcome-delta-blocks-claim")
        if self.experience_record and self.experience_record.blocks_claim:
            reasons.append("experience-blocks-claim")
        return _dedupe_text_tuple(reasons, label="blocking_reason_id")

    @property
    def measured(self) -> bool:
        """Return whether lifecycle has a measured trace."""

        return bool(self.trace and self.trace.measured)

    @property
    def ready_for_review(self) -> bool:
        """Return whether lifecycle is ready for human review."""

        return (
            self.decision is PredictionLifecycleDecision.READY_FOR_REVIEW
            and self.measured
            and not self.missing_evidence_ids
        )

    @property
    def blocks_claim(self) -> bool:
        """Return whether lifecycle blocks stronger maturity claims."""

        return self.decision is PredictionLifecycleDecision.BLOCKED or bool(
            self.blocking_reason_ids
        )

    @property
    def changes_future_reasoning(self) -> bool:
        """Return whether measured outcome changed future reasoning."""

        return bool(
            (self.outcome_review and self.outcome_review.changes_future_reasoning)
            or (
                self.experience_record
                and self.experience_record.changes_future_reasoning
            )
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic lifecycle payload."""

        return {
            "blocking_reason_ids": list(self.blocking_reason_ids),
            "changes_future_reasoning": self.changes_future_reasoning,
            "decision": self.decision.value,
            "evidence_gate_fingerprint": self.evidence_gate.fingerprint(),
            "evidence_ids": list(self.evidence_ids),
            "experience_record_fingerprint": self.experience_record.fingerprint()
            if self.experience_record
            else "",
            "lifecycle_id": self.lifecycle_id,
            "measured": self.measured,
            "missing_evidence_ids": list(self.missing_evidence_ids),
            "notes": list(self.notes),
            "outcome_review_fingerprint": self.outcome_review.fingerprint()
            if self.outcome_review
            else "",
            "prediction_fingerprint": self.prediction.fingerprint(),
            "ready_for_review": self.ready_for_review,
            "schema_version": self.schema_version,
            "trace_fingerprint": self.trace.fingerprint() if self.trace else "",
            "trial_plan_fingerprint": self.trial_plan.fingerprint(),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this lifecycle."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class PredictionLifecycleReport:
    """Review report for Wave 7 prediction-outcome lifecycles."""

    report_id: str
    lifecycles: tuple[PredictionOutcomeLifecycle, ...]
    decision: PredictionLifecycleDecision
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SEVEN_PREDICTION_LIFECYCLE_REPORT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate lifecycle report and preserve blockers."""

        object.__setattr__(
            self,
            "report_id",
            _require_non_empty(self.report_id, "report_id"),
        )
        object.__setattr__(
            self,
            "lifecycles",
            tuple(
                sorted(
                    self.lifecycles,
                    key=lambda lifecycle: lifecycle.lifecycle_id,
                )
            ),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.lifecycles:
            raise ValueError("Prediction lifecycle reports require lifecycles.")
        _ensure_unique(
            (lifecycle.lifecycle_id for lifecycle in self.lifecycles),
            label="lifecycle_id",
        )

    @property
    def lifecycle_ids(self) -> tuple[str, ...]:
        """Return lifecycle ids in this report."""

        return tuple(lifecycle.lifecycle_id for lifecycle in self.lifecycles)

    @property
    def review_ready_lifecycle_ids(self) -> tuple[str, ...]:
        """Return lifecycle ids ready for review."""

        return tuple(
            lifecycle.lifecycle_id
            for lifecycle in self.lifecycles
            if lifecycle.ready_for_review
        )

    @property
    def blocking_lifecycle_ids(self) -> tuple[str, ...]:
        """Return lifecycle ids blocking stronger claims."""

        return tuple(
            lifecycle.lifecycle_id
            for lifecycle in self.lifecycles
            if lifecycle.blocks_claim
        )

    @property
    def future_reasoning_lifecycle_ids(self) -> tuple[str, ...]:
        """Return lifecycle ids that changed future reasoning."""

        return tuple(
            lifecycle.lifecycle_id
            for lifecycle in self.lifecycles
            if lifecycle.changes_future_reasoning
        )

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound to this report."""

        evidence: list[str] = []
        for lifecycle in self.lifecycles:
            evidence.extend(lifecycle.evidence_ids)
        return _dedupe_text_tuple(evidence, label="evidence_id")

    @property
    def ready_for_review(self) -> bool:
        """Return whether this report is ready for review."""

        return (
            self.decision is PredictionLifecycleDecision.READY_FOR_REVIEW
            and bool(self.review_ready_lifecycle_ids)
            and not self.blocking_lifecycle_ids
        )

    @property
    def blocks_claim(self) -> bool:
        """Return whether this report blocks stronger prediction claims."""

        return self.decision is PredictionLifecycleDecision.BLOCKED or bool(
            self.blocking_lifecycle_ids
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic report payload."""

        return {
            "blocking_lifecycle_ids": list(self.blocking_lifecycle_ids),
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "future_reasoning_lifecycle_ids": list(self.future_reasoning_lifecycle_ids),
            "lifecycle_fingerprints": [
                lifecycle.fingerprint() for lifecycle in self.lifecycles
            ],
            "lifecycle_ids": list(self.lifecycle_ids),
            "notes": list(self.notes),
            "report_id": self.report_id,
            "review_ready_lifecycle_ids": list(self.review_ready_lifecycle_ids),
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this report."""

        return _stable_sha256(self.canonical_payload())


def build_outcome_delta_review(
    *,
    review_id: str,
    prediction: BoundedPrediction,
    trace: ObservationActionTrace,
) -> OutcomeDeltaReview:
    """Build an outcome-delta review from a measured trace."""

    if trace.outcome is None or not trace.outcome.measured:
        raise ValueError("Outcome delta review requires a measured trace.")
    severity = _severity_for_alignment(trace.outcome.alignment)
    lesson = trace.outcome.lesson
    return OutcomeDeltaReview(
        review_id=review_id,
        prediction_id=prediction.prediction_id,
        trace_id=trace.trace_id,
        alignment=trace.outcome.alignment,
        severity=severity,
        summary=_review_summary(trace.outcome.alignment),
        evidence_ids=trace.outcome.evidence_ids,
        lesson=lesson,
    )


def build_prediction_outcome_lifecycle(
    *,
    lifecycle_id: str,
    prediction: BoundedPrediction,
    evidence_gate: PredictionEvidenceGate,
    trial_plan: PredictionTrialPlan,
    trace: ObservationActionTrace | None = None,
    experience_record: ExperienceRecord | None = None,
    notes: Iterable[str] = (),
) -> PredictionOutcomeLifecycle:
    """Build a Wave 7 prediction-outcome lifecycle with fail-closed decision."""

    outcome_review = (
        build_outcome_delta_review(
            review_id=f"{lifecycle_id}-outcome-review",
            prediction=prediction,
            trace=trace,
        )
        if trace and trace.measured
        else None
    )
    if not evidence_gate.satisfied:
        decision = PredictionLifecycleDecision.NEEDS_MORE_EVIDENCE
    elif trace is None or not trace.measured:
        decision = PredictionLifecycleDecision.NEEDS_MEASURED_OUTCOME
    elif (
        outcome_review
        and outcome_review.blocks_claim
        or experience_record
        and experience_record.blocks_claim
    ):
        decision = PredictionLifecycleDecision.BLOCKED
    elif experience_record is None:
        decision = PredictionLifecycleDecision.NEEDS_MORE_EVIDENCE
    else:
        decision = PredictionLifecycleDecision.READY_FOR_REVIEW

    return PredictionOutcomeLifecycle(
        lifecycle_id=lifecycle_id,
        prediction=prediction,
        evidence_gate=evidence_gate,
        trial_plan=trial_plan,
        trace=trace,
        outcome_review=outcome_review,
        experience_record=experience_record,
        decision=decision,
        notes=tuple(notes),
    )


def build_prediction_lifecycle_report(
    *,
    report_id: str,
    lifecycles: Iterable[PredictionOutcomeLifecycle],
    decision: PredictionLifecycleDecision,
    notes: Iterable[str] = (),
) -> PredictionLifecycleReport:
    """Build a deterministic Wave 7 prediction lifecycle report."""

    return PredictionLifecycleReport(
        report_id=report_id,
        lifecycles=tuple(lifecycles),
        decision=decision,
        notes=tuple(notes),
    )


def _severity_for_alignment(alignment: OutcomeAlignment) -> OutcomeDeltaSeverity:
    if alignment is OutcomeAlignment.MATCHED:
        return OutcomeDeltaSeverity.NONE
    if alignment is OutcomeAlignment.PARTIAL:
        return OutcomeDeltaSeverity.MODERATE
    if alignment is OutcomeAlignment.MISMATCHED:
        return OutcomeDeltaSeverity.BLOCKING
    raise ValueError("Outcome delta severity requires measured alignment.")


def _review_summary(alignment: OutcomeAlignment) -> str:
    if alignment is OutcomeAlignment.MATCHED:
        return "Measured outcome matched the bounded prediction."
    if alignment is OutcomeAlignment.PARTIAL:
        return "Measured outcome partially matched the bounded prediction."
    if alignment is OutcomeAlignment.MISMATCHED:
        return "Measured outcome contradicted the bounded prediction."
    return "Outcome was not measured."


def _require_non_empty(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _normalize_optional_text(value: str) -> str:
    return value.strip()


def _normalize_unique_text_tuple(
    values: Iterable[str], *, label: str
) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _require_non_empty(value, label)
        if text in seen:
            raise ValueError(f"Duplicate {label}: {text}")
        seen.add(text)
        normalized.append(text)
    return tuple(sorted(normalized))


def _dedupe_text_tuple(values: Iterable[str], *, label: str) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _require_non_empty(value, label)
        if text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return tuple(sorted(normalized))


def _ensure_unique(values: Iterable[str], *, label: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label}: {value}")
        seen.add(value)


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
