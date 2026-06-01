"""Evaluation records for IX-CognitionKernel Wave 1 preparation.

This module represents evaluation state only. It does not execute tests, certify
claims, approve plans, or authorize handoffs. Wave 1 needs evaluation records to
capture acceptance criteria, reviewed artifacts, evidence, reasons, and
fail-closed outcomes as structured cognition state.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum


class EvaluationStatus(StrEnum):
    """Governed outcome state for an evaluation record."""

    NOT_RUN = "not-run"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    NEEDS_EVIDENCE = "needs-evidence"


@dataclass(frozen=True, slots=True)
class AcceptanceCriterion:
    """A reviewable criterion used to judge a cognition artifact."""

    criterion_id: str
    description: str
    required: bool
    satisfied: bool
    evidence_ids: tuple[str, ...]
    reason: str | None = None

    def __post_init__(self) -> None:
        """Validate criterion identity, description, and evidence linkage."""

        if not self.criterion_id.strip():
            raise ValueError("Acceptance criteria require a non-empty criterion_id.")
        if not self.description.strip():
            raise ValueError("Acceptance criteria require a non-empty description.")
        _unique_ids(self.evidence_ids, label="criterion evidence_id")
        if self.required and not self.satisfied and not _has_text(self.reason):
            raise ValueError(
                "Unsatisfied required acceptance criteria require a reason."
            )
        if self.satisfied and not self.evidence_ids:
            raise ValueError("Satisfied acceptance criteria require evidence ids.")

    @property
    def blocks_pass(self) -> bool:
        """Return whether this criterion prevents a passing evaluation."""

        return self.required and not self.satisfied


@dataclass(frozen=True, slots=True)
class EvaluationRecord:
    """A structured evaluation result for Wave 1 cognition artifacts."""

    evaluation_id: str
    title: str
    evaluated_artifact_ids: tuple[str, ...]
    criteria: tuple[AcceptanceCriterion, ...]
    status: EvaluationStatus
    evidence_ids: tuple[str, ...]
    reasons: tuple[str, ...]
    evaluator_role_id: str

    def __post_init__(self) -> None:
        """Validate evaluation identity, artifacts, criteria, and status rules."""

        if not self.evaluation_id.strip():
            raise ValueError("Evaluation records require a non-empty evaluation_id.")
        if not self.title.strip():
            raise ValueError("Evaluation records require a non-empty title.")
        if not self.evaluator_role_id.strip():
            raise ValueError(
                "Evaluation records require a non-empty evaluator_role_id."
            )
        if not self.evaluated_artifact_ids:
            raise ValueError("Evaluation records require evaluated artifact ids.")
        if not self.criteria:
            raise ValueError("Evaluation records require acceptance criteria.")
        _unique_ids(self.evaluated_artifact_ids, label="evaluated_artifact_id")
        _unique_ids(self.evidence_ids, label="evaluation evidence_id")
        _unique_ids(
            (criterion.criterion_id for criterion in self.criteria),
            label="criterion_id",
        )

        if self.status is EvaluationStatus.PASSED:
            self._validate_passed_record()
        if (
            self.status
            in {
                EvaluationStatus.FAILED,
                EvaluationStatus.BLOCKED,
                EvaluationStatus.NEEDS_EVIDENCE,
            }
            and not self.reasons
        ):
            raise ValueError(f"{self.status.value} evaluations require reasons.")
        if self.status is EvaluationStatus.NOT_RUN and (
            self.evidence_ids or self.reasons
        ):
            raise ValueError("not-run evaluations cannot contain evidence or reasons.")

    @property
    def unsatisfied_required_criteria(self) -> tuple[AcceptanceCriterion, ...]:
        """Return required criteria that are not satisfied."""

        return tuple(criterion for criterion in self.criteria if criterion.blocks_pass)

    @property
    def is_passing(self) -> bool:
        """Return whether this evaluation passed all required criteria."""

        return self.status is EvaluationStatus.PASSED

    @property
    def blocks_progress(self) -> bool:
        """Return whether this evaluation prevents progress to later review."""

        return self.status in {
            EvaluationStatus.FAILED,
            EvaluationStatus.BLOCKED,
            EvaluationStatus.NEEDS_EVIDENCE,
        }

    def covers_artifact(self, artifact_id: str) -> bool:
        """Return whether this evaluation covers an artifact id."""

        return artifact_id in self.evaluated_artifact_ids

    def _validate_passed_record(self) -> None:
        """Validate the additional evidence rules for passing records."""

        if not self.evidence_ids:
            raise ValueError("Passed evaluations require evidence ids.")
        if self.unsatisfied_required_criteria:
            raise ValueError(
                "Passed evaluations cannot contain unsatisfied required criteria."
            )


@dataclass(frozen=True, slots=True)
class EvaluationLedger:
    """Container for evaluation records and artifact coverage queries."""

    records: tuple[EvaluationRecord, ...]

    def __post_init__(self) -> None:
        """Reject duplicate evaluation ids."""

        _unique_ids(
            (record.evaluation_id for record in self.records), label="evaluation_id"
        )

    @property
    def passing_records(self) -> tuple[EvaluationRecord, ...]:
        """Return evaluations that passed."""

        return tuple(record for record in self.records if record.is_passing)

    @property
    def blocking_records(self) -> tuple[EvaluationRecord, ...]:
        """Return evaluations that block progress."""

        return tuple(record for record in self.records if record.blocks_progress)

    @property
    def needs_evidence_records(self) -> tuple[EvaluationRecord, ...]:
        """Return evaluations waiting on more evidence."""

        return tuple(
            record
            for record in self.records
            if record.status is EvaluationStatus.NEEDS_EVIDENCE
        )

    def record_by_id(self, evaluation_id: str) -> EvaluationRecord:
        """Return an evaluation record by id."""

        for record in self.records:
            if record.evaluation_id == evaluation_id:
                return record
        raise ValueError(f"Unknown evaluation_id: {evaluation_id}")

    def records_for_artifact(self, artifact_id: str) -> tuple[EvaluationRecord, ...]:
        """Return all evaluation records covering an artifact id."""

        return tuple(
            record for record in self.records if record.covers_artifact(artifact_id)
        )

    def artifact_is_passing(self, artifact_id: str) -> bool:
        """Return whether an artifact has coverage and no blocking evaluations."""

        covered = self.records_for_artifact(artifact_id)
        return bool(covered) and all(record.is_passing for record in covered)


def _unique_ids(values: Iterable[str], *, label: str) -> set[str]:
    """Return unique ids while rejecting duplicates."""

    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value}")
        seen.add(value)
    return seen


def _has_text(value: str | None) -> bool:
    """Return whether an optional string contains non-whitespace text."""

    return value is not None and bool(value.strip())
