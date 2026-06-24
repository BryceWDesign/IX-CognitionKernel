"""Wave 7 experience compiler.

The experience compiler turns bounded observation-action traces into
reviewable learning material. It connects prediction, measured outcome, delta,
memory patch, and future-reasoning constraint without allowing unverifiable
experience to become trusted memory.

Wave 7 experience rules:

- prediction is not evidence,
- outcome must be measured before experience can be trusted,
- mismatch must produce a lesson,
- memory patches are quarantined by default,
- future reasoning changes must cite evidence,
- compiled experience can be ready for review but never self-authorized.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from ix_cognition_kernel.wave7_observation_action_schema import (
    ObservationActionTrace,
    OutcomeAlignment,
)

WAVE_SEVEN_PREDICTION_OUTCOME_DELTA_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-prediction-outcome-delta-v1"
)
WAVE_SEVEN_LEARNING_DELTA_SCHEMA_VERSION = "ix-cognition-kernel-wave7-learning-delta-v1"
WAVE_SEVEN_MEMORY_PATCH_SCHEMA_VERSION = "ix-cognition-kernel-wave7-memory-patch-v1"
WAVE_SEVEN_FUTURE_REASONING_CONSTRAINT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-future-reasoning-constraint-v1"
)
WAVE_SEVEN_EXPERIENCE_RECORD_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-experience-record-v1"
)
WAVE_SEVEN_EXPERIENCE_COMPILATION_REPORT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-experience-compilation-report-v1"
)


class LearningDeltaKind(StrEnum):
    """Kinds of learning created by measured experience."""

    CONFIRMATION = "confirmation"
    CORRECTION = "correction"
    LIMITATION = "limitation"
    CONTRADICTION = "contradiction"


class MemoryPatchStatus(StrEnum):
    """Reviewable status for a memory patch."""

    QUARANTINED = "quarantined"
    READY_FOR_REVIEW = "ready-for-review"
    REJECTED = "rejected"
    ACCEPTED_BY_HUMAN_REVIEW = "accepted-by-human-review"


class FutureConstraintStrength(StrEnum):
    """Strength of future reasoning constraint produced by experience."""

    ADVISORY = "advisory"
    REQUIRED_CHECK = "required-check"
    BLOCKING_RULE = "blocking-rule"


class ExperienceCompilationDecision(StrEnum):
    """Fail-closed decision for compiled Wave 7 experience."""

    RECORD_ONLY = "record-only"
    READY_FOR_REVIEW = "ready-for-review"
    NEEDS_MEASURED_OUTCOME = "needs-measured-outcome"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class PredictionOutcomeDelta:
    """Delta between a prediction and a measured outcome."""

    delta_id: str
    prediction_id: str
    predicted_outcome: str
    observed_outcome: str
    alignment: OutcomeAlignment
    delta_summary: str
    evidence_ids: tuple[str, ...]
    lesson: str = ""
    schema_version: str = WAVE_SEVEN_PREDICTION_OUTCOME_DELTA_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate prediction-outcome delta evidence."""

        object.__setattr__(
            self,
            "delta_id",
            _require_non_empty(self.delta_id, "delta_id"),
        )
        object.__setattr__(
            self,
            "prediction_id",
            _require_non_empty(self.prediction_id, "prediction_id"),
        )
        object.__setattr__(
            self,
            "predicted_outcome",
            _require_non_empty(self.predicted_outcome, "predicted_outcome"),
        )
        object.__setattr__(
            self,
            "observed_outcome",
            _require_non_empty(self.observed_outcome, "observed_outcome"),
        )
        object.__setattr__(
            self,
            "delta_summary",
            _require_non_empty(self.delta_summary, "delta_summary"),
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
            raise ValueError("Prediction-outcome deltas require evidence ids.")
        if self.alignment is OutcomeAlignment.NOT_MEASURED:
            raise ValueError("Prediction-outcome deltas require measured outcomes.")
        if (
            self.alignment
            in {
                OutcomeAlignment.PARTIAL,
                OutcomeAlignment.MISMATCHED,
            }
            and not self.lesson
        ):
            raise ValueError("Partial or mismatched deltas require a lesson.")

    @property
    def confirms_prediction(self) -> bool:
        """Return whether the observed outcome matched prediction."""

        return self.alignment is OutcomeAlignment.MATCHED

    @property
    def changes_future_reasoning(self) -> bool:
        """Return whether the delta contains a lesson."""

        return bool(self.lesson)

    @property
    def blocks_stronger_claim(self) -> bool:
        """Return whether this delta blocks stronger maturity claims."""

        return self.alignment is OutcomeAlignment.MISMATCHED

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic delta payload."""

        return {
            "alignment": self.alignment.value,
            "delta_id": self.delta_id,
            "delta_summary": self.delta_summary,
            "evidence_ids": list(self.evidence_ids),
            "lesson": self.lesson,
            "observed_outcome": self.observed_outcome,
            "predicted_outcome": self.predicted_outcome,
            "prediction_id": self.prediction_id,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this delta."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class LearningDelta:
    """Measured learning delta extracted from experience."""

    learning_id: str
    kind: LearningDeltaKind
    source_delta_id: str
    summary: str
    evidence_ids: tuple[str, ...]
    affected_belief_ids: tuple[str, ...]
    affected_skill_ids: tuple[str, ...] = ()
    schema_version: str = WAVE_SEVEN_LEARNING_DELTA_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate measured learning delta."""

        object.__setattr__(
            self,
            "learning_id",
            _require_non_empty(self.learning_id, "learning_id"),
        )
        object.__setattr__(
            self,
            "source_delta_id",
            _require_non_empty(self.source_delta_id, "source_delta_id"),
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
        object.__setattr__(
            self,
            "affected_belief_ids",
            _normalize_unique_text_tuple(
                self.affected_belief_ids, label="affected_belief_id"
            ),
        )
        object.__setattr__(
            self,
            "affected_skill_ids",
            _normalize_unique_text_tuple(
                self.affected_skill_ids, label="affected_skill_id"
            ),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Learning deltas require evidence ids.")
        if not self.affected_belief_ids and not self.affected_skill_ids:
            raise ValueError("Learning deltas require affected belief or skill ids.")

    @property
    def corrective(self) -> bool:
        """Return whether this learning delta corrects prior reasoning."""

        return self.kind in {
            LearningDeltaKind.CORRECTION,
            LearningDeltaKind.LIMITATION,
            LearningDeltaKind.CONTRADICTION,
        }

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic learning-delta payload."""

        return {
            "affected_belief_ids": list(self.affected_belief_ids),
            "affected_skill_ids": list(self.affected_skill_ids),
            "evidence_ids": list(self.evidence_ids),
            "kind": self.kind.value,
            "learning_id": self.learning_id,
            "schema_version": self.schema_version,
            "source_delta_id": self.source_delta_id,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this learning delta."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class MemoryPatch:
    """Evidence-bound memory patch produced by measured experience."""

    patch_id: str
    source_learning_id: str
    target_memory_id: str
    patch_summary: str
    evidence_ids: tuple[str, ...]
    status: MemoryPatchStatus = MemoryPatchStatus.QUARANTINED
    human_review_ref: str = ""
    self_approved: bool = False
    treats_memory_as_truth: bool = False
    schema_version: str = WAVE_SEVEN_MEMORY_PATCH_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate memory patch quarantine and approval discipline."""

        if self.self_approved:
            raise ValueError("Memory patches must not self-approve.")
        if self.treats_memory_as_truth:
            raise ValueError("Memory patches must not treat memory as truth.")
        object.__setattr__(
            self,
            "patch_id",
            _require_non_empty(self.patch_id, "patch_id"),
        )
        object.__setattr__(
            self,
            "source_learning_id",
            _require_non_empty(self.source_learning_id, "source_learning_id"),
        )
        object.__setattr__(
            self,
            "target_memory_id",
            _require_non_empty(self.target_memory_id, "target_memory_id"),
        )
        object.__setattr__(
            self,
            "patch_summary",
            _require_non_empty(self.patch_summary, "patch_summary"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "human_review_ref",
            _normalize_optional_text(self.human_review_ref),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Memory patches require evidence ids.")
        if (
            self.status is MemoryPatchStatus.ACCEPTED_BY_HUMAN_REVIEW
            and not self.human_review_ref
        ):
            raise ValueError("Accepted memory patches require human_review_ref.")
        if (
            self.status is not MemoryPatchStatus.ACCEPTED_BY_HUMAN_REVIEW
            and self.human_review_ref
        ):
            raise ValueError(
                "Only human-accepted memory patches may include review refs."
            )

    @property
    def quarantined(self) -> bool:
        """Return whether this patch remains quarantined."""

        return self.status is MemoryPatchStatus.QUARANTINED

    @property
    def accepted(self) -> bool:
        """Return whether this patch was accepted by human review."""

        return self.status is MemoryPatchStatus.ACCEPTED_BY_HUMAN_REVIEW

    @property
    def blocks_trusted_memory(self) -> bool:
        """Return whether this patch cannot support trusted memory."""

        return self.status in {
            MemoryPatchStatus.QUARANTINED,
            MemoryPatchStatus.REJECTED,
        }

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic memory-patch payload."""

        return {
            "evidence_ids": list(self.evidence_ids),
            "human_review_ref": self.human_review_ref,
            "patch_id": self.patch_id,
            "patch_summary": self.patch_summary,
            "schema_version": self.schema_version,
            "self_approved": self.self_approved,
            "source_learning_id": self.source_learning_id,
            "status": self.status.value,
            "target_memory_id": self.target_memory_id,
            "treats_memory_as_truth": self.treats_memory_as_truth,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this memory patch."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class FutureReasoningConstraint:
    """Constraint that changes future reasoning because reality corrected it."""

    constraint_id: str
    source_learning_id: str
    rule: str
    strength: FutureConstraintStrength
    applies_to_domains: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    authority_refs: tuple[str, ...]
    schema_version: str = WAVE_SEVEN_FUTURE_REASONING_CONSTRAINT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate future reasoning constraint evidence and authority."""

        object.__setattr__(
            self,
            "constraint_id",
            _require_non_empty(self.constraint_id, "constraint_id"),
        )
        object.__setattr__(
            self,
            "source_learning_id",
            _require_non_empty(self.source_learning_id, "source_learning_id"),
        )
        object.__setattr__(self, "rule", _require_non_empty(self.rule, "rule"))
        object.__setattr__(
            self,
            "applies_to_domains",
            _normalize_unique_text_tuple(
                self.applies_to_domains, label="applies_to_domain"
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
        if not self.applies_to_domains:
            raise ValueError("Future reasoning constraints require domains.")
        if not self.evidence_ids:
            raise ValueError("Future reasoning constraints require evidence ids.")
        if not self.authority_refs:
            raise ValueError("Future reasoning constraints require authority refs.")

    @property
    def blocks_future_action(self) -> bool:
        """Return whether this constraint is a blocking rule."""

        return self.strength is FutureConstraintStrength.BLOCKING_RULE

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic future-constraint payload."""

        return {
            "applies_to_domains": list(self.applies_to_domains),
            "authority_refs": list(self.authority_refs),
            "constraint_id": self.constraint_id,
            "evidence_ids": list(self.evidence_ids),
            "rule": self.rule,
            "schema_version": self.schema_version,
            "source_learning_id": self.source_learning_id,
            "strength": self.strength.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this constraint."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class ExperienceRecord:
    """Compiled record tying trace, delta, learning, patch, and constraints."""

    record_id: str
    trace: ObservationActionTrace
    delta: PredictionOutcomeDelta
    learning_delta: LearningDelta
    memory_patches: tuple[MemoryPatch, ...]
    future_constraints: tuple[FutureReasoningConstraint, ...]
    decision: ExperienceCompilationDecision
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SEVEN_EXPERIENCE_RECORD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate compiled experience linkage and fail-closed state."""

        object.__setattr__(
            self,
            "record_id",
            _require_non_empty(self.record_id, "record_id"),
        )
        object.__setattr__(
            self,
            "memory_patches",
            tuple(sorted(self.memory_patches, key=lambda patch: patch.patch_id)),
        )
        object.__setattr__(
            self,
            "future_constraints",
            tuple(
                sorted(
                    self.future_constraints,
                    key=lambda constraint: constraint.constraint_id,
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
        if not self.trace.measured:
            raise ValueError("Experience records require measured traces.")
        if not self.memory_patches:
            raise ValueError("Experience records require memory patches.")
        if not self.future_constraints:
            raise ValueError("Experience records require future constraints.")
        _ensure_unique(
            (patch.patch_id for patch in self.memory_patches), label="patch_id"
        )
        _ensure_unique(
            (constraint.constraint_id for constraint in self.future_constraints),
            label="constraint_id",
        )
        if self.delta.delta_id != self.learning_delta.source_delta_id:
            raise ValueError("Learning delta must reference the prediction delta.")
        for patch in self.memory_patches:
            if patch.source_learning_id != self.learning_delta.learning_id:
                raise ValueError("Memory patches must reference learning delta.")
        for constraint in self.future_constraints:
            if constraint.source_learning_id != self.learning_delta.learning_id:
                raise ValueError("Future constraints must reference learning delta.")
        if (
            self.decision is ExperienceCompilationDecision.READY_FOR_REVIEW
            and self.blocking_patch_ids
        ):
            raise ValueError("Review-ready experience cannot use rejected patches.")
        if (
            self.decision is ExperienceCompilationDecision.NEEDS_MEASURED_OUTCOME
            and self.trace.measured
        ):
            raise ValueError("Measured experience cannot need measured outcome.")

    @property
    def patch_ids(self) -> tuple[str, ...]:
        """Return memory patch ids."""

        return tuple(patch.patch_id for patch in self.memory_patches)

    @property
    def constraint_ids(self) -> tuple[str, ...]:
        """Return future reasoning constraint ids."""

        return tuple(constraint.constraint_id for constraint in self.future_constraints)

    @property
    def quarantined_patch_ids(self) -> tuple[str, ...]:
        """Return quarantined memory patch ids."""

        return tuple(
            patch.patch_id for patch in self.memory_patches if patch.quarantined
        )

    @property
    def accepted_patch_ids(self) -> tuple[str, ...]:
        """Return human-accepted memory patch ids."""

        return tuple(patch.patch_id for patch in self.memory_patches if patch.accepted)

    @property
    def blocking_patch_ids(self) -> tuple[str, ...]:
        """Return rejected patch ids that block review readiness."""

        return tuple(
            patch.patch_id
            for patch in self.memory_patches
            if patch.status is MemoryPatchStatus.REJECTED
        )

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound to this experience record."""

        evidence: list[str] = list(self.trace.evidence_ids)
        evidence.extend(self.delta.evidence_ids)
        evidence.extend(self.learning_delta.evidence_ids)
        for patch in self.memory_patches:
            evidence.extend(patch.evidence_ids)
        for constraint in self.future_constraints:
            evidence.extend(constraint.evidence_ids)
        return _dedupe_text_tuple(evidence, label="evidence_id")

    @property
    def changes_future_reasoning(self) -> bool:
        """Return whether compiled experience changes future reasoning."""

        return bool(self.future_constraints) and (
            self.delta.changes_future_reasoning
            or self.learning_delta.corrective
            or self.trace.changes_future_reasoning
        )

    @property
    def ready_for_review(self) -> bool:
        """Return whether compiled experience is ready for review."""

        return self.decision is ExperienceCompilationDecision.READY_FOR_REVIEW

    @property
    def blocks_claim(self) -> bool:
        """Return whether this record blocks stronger claims."""

        return (
            self.decision is ExperienceCompilationDecision.BLOCKED
            or bool(self.blocking_patch_ids)
            or self.delta.blocks_stronger_claim
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic experience-record payload."""

        return {
            "accepted_patch_ids": list(self.accepted_patch_ids),
            "blocking_patch_ids": list(self.blocking_patch_ids),
            "changes_future_reasoning": self.changes_future_reasoning,
            "constraint_fingerprints": [
                constraint.fingerprint() for constraint in self.future_constraints
            ],
            "decision": self.decision.value,
            "delta_fingerprint": self.delta.fingerprint(),
            "evidence_ids": list(self.evidence_ids),
            "learning_delta_fingerprint": self.learning_delta.fingerprint(),
            "notes": list(self.notes),
            "patch_fingerprints": [
                patch.fingerprint() for patch in self.memory_patches
            ],
            "quarantined_patch_ids": list(self.quarantined_patch_ids),
            "record_id": self.record_id,
            "schema_version": self.schema_version,
            "trace_fingerprint": self.trace.fingerprint(),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this record."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class ExperienceCompilationReport:
    """Review report for compiled Wave 7 experience records."""

    report_id: str
    records: tuple[ExperienceRecord, ...]
    decision: ExperienceCompilationDecision
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SEVEN_EXPERIENCE_COMPILATION_REPORT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate report and preserve unresolved experience blockers."""

        object.__setattr__(
            self,
            "report_id",
            _require_non_empty(self.report_id, "report_id"),
        )
        object.__setattr__(
            self,
            "records",
            tuple(sorted(self.records, key=lambda record: record.record_id)),
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
        if not self.records:
            raise ValueError("Experience compilation reports require records.")
        _ensure_unique((record.record_id for record in self.records), label="record_id")

    @property
    def record_ids(self) -> tuple[str, ...]:
        """Return compiled experience record ids."""

        return tuple(record.record_id for record in self.records)

    @property
    def review_ready_record_ids(self) -> tuple[str, ...]:
        """Return review-ready experience record ids."""

        return tuple(
            record.record_id for record in self.records if record.ready_for_review
        )

    @property
    def blocking_record_ids(self) -> tuple[str, ...]:
        """Return record ids that block stronger claims."""

        return tuple(record.record_id for record in self.records if record.blocks_claim)

    @property
    def future_reasoning_record_ids(self) -> tuple[str, ...]:
        """Return records that change future reasoning."""

        return tuple(
            record.record_id
            for record in self.records
            if record.changes_future_reasoning
        )

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound to this report."""

        evidence: list[str] = []
        for record in self.records:
            evidence.extend(record.evidence_ids)
        return _dedupe_text_tuple(evidence, label="evidence_id")

    @property
    def ready_for_review(self) -> bool:
        """Return whether the report is ready for review."""

        return (
            self.decision is ExperienceCompilationDecision.READY_FOR_REVIEW
            and bool(self.review_ready_record_ids)
            and not self.blocking_record_ids
        )

    @property
    def blocks_claim(self) -> bool:
        """Return whether this report blocks stronger experience claims."""

        return self.decision is ExperienceCompilationDecision.BLOCKED or bool(
            self.blocking_record_ids
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic report payload."""

        return {
            "blocking_record_ids": list(self.blocking_record_ids),
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "future_reasoning_record_ids": list(self.future_reasoning_record_ids),
            "notes": list(self.notes),
            "record_fingerprints": [record.fingerprint() for record in self.records],
            "record_ids": list(self.record_ids),
            "report_id": self.report_id,
            "review_ready_record_ids": list(self.review_ready_record_ids),
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this report."""

        return _stable_sha256(self.canonical_payload())


def compile_experience_record(
    *,
    record_id: str,
    trace: ObservationActionTrace,
    prediction_id: str,
    affected_belief_ids: Iterable[str],
    affected_skill_ids: Iterable[str] = (),
    target_memory_id: str,
    domains: Iterable[str],
    authority_refs: Iterable[str],
    notes: Iterable[str] = (),
) -> ExperienceRecord:
    """Compile a measured observation-action trace into Wave 7 experience."""

    if trace.outcome is None or not trace.outcome.measured:
        raise ValueError("Experience compilation requires a measured outcome.")

    delta = PredictionOutcomeDelta(
        delta_id=f"{record_id}-delta",
        prediction_id=prediction_id,
        predicted_outcome=trace.envelope.predicted_outcome,
        observed_outcome=trace.outcome.outcome_summary,
        alignment=trace.outcome.alignment,
        delta_summary=_delta_summary(trace.outcome.alignment),
        evidence_ids=trace.outcome.evidence_ids,
        lesson=trace.outcome.lesson,
    )
    learning_kind = _learning_kind_for_alignment(trace.outcome.alignment)
    learning = LearningDelta(
        learning_id=f"{record_id}-learning",
        kind=learning_kind,
        source_delta_id=delta.delta_id,
        summary=_learning_summary(learning_kind, trace.outcome.lesson),
        evidence_ids=delta.evidence_ids,
        affected_belief_ids=tuple(affected_belief_ids),
        affected_skill_ids=tuple(affected_skill_ids),
    )
    patch = MemoryPatch(
        patch_id=f"{record_id}-memory-patch",
        source_learning_id=learning.learning_id,
        target_memory_id=target_memory_id,
        patch_summary=_memory_patch_summary(learning_kind),
        evidence_ids=learning.evidence_ids,
        status=MemoryPatchStatus.QUARANTINED,
    )
    constraint = FutureReasoningConstraint(
        constraint_id=f"{record_id}-future-constraint",
        source_learning_id=learning.learning_id,
        rule=_future_constraint_rule(trace.outcome.alignment, trace.outcome.lesson),
        strength=_constraint_strength_for_alignment(trace.outcome.alignment),
        applies_to_domains=tuple(domains),
        evidence_ids=learning.evidence_ids,
        authority_refs=tuple(authority_refs),
    )
    decision = (
        ExperienceCompilationDecision.READY_FOR_REVIEW
        if trace.outcome.measured
        else ExperienceCompilationDecision.NEEDS_MEASURED_OUTCOME
    )
    return ExperienceRecord(
        record_id=record_id,
        trace=trace,
        delta=delta,
        learning_delta=learning,
        memory_patches=(patch,),
        future_constraints=(constraint,),
        decision=decision,
        notes=tuple(notes),
    )


def build_experience_compilation_report(
    *,
    report_id: str,
    records: Iterable[ExperienceRecord],
    decision: ExperienceCompilationDecision,
    notes: Iterable[str] = (),
) -> ExperienceCompilationReport:
    """Build a deterministic Wave 7 experience compilation report."""

    return ExperienceCompilationReport(
        report_id=report_id,
        records=tuple(records),
        decision=decision,
        notes=tuple(notes),
    )


def _learning_kind_for_alignment(alignment: OutcomeAlignment) -> LearningDeltaKind:
    if alignment is OutcomeAlignment.MATCHED:
        return LearningDeltaKind.CONFIRMATION
    if alignment is OutcomeAlignment.PARTIAL:
        return LearningDeltaKind.LIMITATION
    if alignment is OutcomeAlignment.MISMATCHED:
        return LearningDeltaKind.CORRECTION
    raise ValueError("Measured learning requires measured outcome alignment.")


def _constraint_strength_for_alignment(
    alignment: OutcomeAlignment,
) -> FutureConstraintStrength:
    if alignment is OutcomeAlignment.MATCHED:
        return FutureConstraintStrength.ADVISORY
    if alignment is OutcomeAlignment.PARTIAL:
        return FutureConstraintStrength.REQUIRED_CHECK
    if alignment is OutcomeAlignment.MISMATCHED:
        return FutureConstraintStrength.BLOCKING_RULE
    raise ValueError("Future constraints require measured outcome alignment.")


def _delta_summary(alignment: OutcomeAlignment) -> str:
    if alignment is OutcomeAlignment.MATCHED:
        return "Measured outcome matched the prediction."
    if alignment is OutcomeAlignment.PARTIAL:
        return "Measured outcome partially matched the prediction."
    if alignment is OutcomeAlignment.MISMATCHED:
        return "Measured outcome contradicted the prediction."
    return "Outcome was not measured."


def _learning_summary(kind: LearningDeltaKind, lesson: str) -> str:
    if kind is LearningDeltaKind.CONFIRMATION:
        return "Experience confirmed the bounded prediction."
    if lesson:
        return lesson
    return "Experience corrected future reasoning."


def _memory_patch_summary(kind: LearningDeltaKind) -> str:
    if kind is LearningDeltaKind.CONFIRMATION:
        return "Quarantine confirmation before trusting memory."
    if kind is LearningDeltaKind.LIMITATION:
        return "Quarantine limitation learned from partial outcome."
    if kind is LearningDeltaKind.CORRECTION:
        return "Quarantine correction learned from mismatched outcome."
    return "Quarantine contradiction before future reuse."


def _future_constraint_rule(alignment: OutcomeAlignment, lesson: str) -> str:
    if lesson:
        return lesson
    if alignment is OutcomeAlignment.MATCHED:
        return (
            "Future reasoning may reuse this bounded pattern only "
            "with matching evidence."
        )
    if alignment is OutcomeAlignment.PARTIAL:
        return "Future reasoning must check the missing condition before reuse."
    if alignment is OutcomeAlignment.MISMATCHED:
        return "Future reasoning must block this assumption until revalidated."
    return "Future reasoning must not update from unmeasured outcomes."


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
