"""Outcome learning records for IX-CognitionKernel Wave 2.

Wave 2 needs learning outcomes to be explicit evidence-linked records rather
than vibes. This module ties together belief revisions, prediction comparisons,
and causal revisions into reviewable outcome-learning artifacts. It does not
create durable memory, validate skills, execute plans, or claim AGI.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from ix_cognition_kernel.history import BeliefHistory, BeliefRevisionKind
from ix_cognition_kernel.observations import (
    PredictionComparisonLedger,
)
from ix_cognition_kernel.revision import (
    CausalRevisionAction,
    CausalRevisionResult,
)


class OutcomeLearningStatus(StrEnum):
    """Governed status for an outcome learning record."""

    ACCEPTED = "accepted"
    BLOCKED = "blocked"
    NEEDS_EVIDENCE = "needs-evidence"


class OutcomePressure(StrEnum):
    """Summary of how outcome evidence pressured the cognition state."""

    CONFIRMED = "confirmed"
    CORRECTED = "corrected"
    MIXED = "mixed"
    INCONCLUSIVE = "inconclusive"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class OutcomeLearningRecord:
    """Evidence-linked record of what changed after an outcome."""

    outcome_id: str
    summary: str
    status: OutcomeLearningStatus
    pressure: OutcomePressure
    belief_revision_ids: tuple[str, ...]
    causal_revision_ids: tuple[str, ...]
    prediction_comparison_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    learning_summary: str
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate outcome identity, linkage, evidence, and reasons."""

        if not self.outcome_id.strip():
            raise ValueError("Outcome learning records require a non-empty outcome_id.")
        if not self.summary.strip():
            raise ValueError("Outcome learning records require a non-empty summary.")
        if not self.learning_summary.strip():
            raise ValueError(
                "Outcome learning records require a non-empty learning_summary."
            )
        _unique_ids(self.belief_revision_ids, label="belief_revision_id")
        _unique_ids(self.causal_revision_ids, label="causal_revision_id")
        _unique_ids(
            self.prediction_comparison_ids,
            label="prediction_comparison_id",
        )
        _unique_ids(self.evidence_ids, label="outcome evidence_id")
        if not self.reasons:
            raise ValueError("Outcome learning records require reasons.")
        if any(not reason.strip() for reason in self.reasons):
            raise ValueError("Outcome learning reasons cannot be empty.")
        if self.status is OutcomeLearningStatus.ACCEPTED:
            self._validate_accepted_record()
        if self.status is OutcomeLearningStatus.BLOCKED and (
            self.pressure is not OutcomePressure.BLOCKED
        ):
            raise ValueError("Blocked outcome records require blocked pressure.")
        if self.status is OutcomeLearningStatus.NEEDS_EVIDENCE and self.evidence_ids:
            raise ValueError(
                "Needs-evidence outcome records cannot contain evidence_ids."
            )

    @property
    def has_belief_learning(self) -> bool:
        """Return whether the outcome is linked to belief revisions."""

        return bool(self.belief_revision_ids)

    @property
    def has_causal_learning(self) -> bool:
        """Return whether the outcome is linked to causal revisions."""

        return bool(self.causal_revision_ids)

    @property
    def is_accepted(self) -> bool:
        """Return whether the outcome learning record was accepted."""

        return self.status is OutcomeLearningStatus.ACCEPTED

    @property
    def is_blocked(self) -> bool:
        """Return whether the outcome learning record was blocked."""

        return self.status is OutcomeLearningStatus.BLOCKED

    def _validate_accepted_record(self) -> None:
        """Validate stricter traceability requirements for accepted outcomes."""

        if not self.evidence_ids:
            raise ValueError("Accepted outcome learning records require evidence_ids.")
        if not (
            self.belief_revision_ids
            or self.causal_revision_ids
            or self.prediction_comparison_ids
        ):
            raise ValueError(
                "Accepted outcome learning records require linked revisions or "
                "prediction comparisons."
            )
        if self.pressure is OutcomePressure.BLOCKED:
            raise ValueError("Accepted outcome learning records cannot be blocked.")


@dataclass(frozen=True, slots=True)
class OutcomeLearningLedger:
    """Ledger of outcome learning records."""

    records: tuple[OutcomeLearningRecord, ...]

    def __post_init__(self) -> None:
        """Reject duplicate outcome ids."""

        _unique_ids((record.outcome_id for record in self.records), label="outcome_id")

    @property
    def accepted_records(self) -> tuple[OutcomeLearningRecord, ...]:
        """Return accepted outcome learning records."""

        return tuple(record for record in self.records if record.is_accepted)

    @property
    def blocked_records(self) -> tuple[OutcomeLearningRecord, ...]:
        """Return blocked outcome learning records."""

        return tuple(record for record in self.records if record.is_blocked)

    @property
    def needs_evidence_records(self) -> tuple[OutcomeLearningRecord, ...]:
        """Return records still waiting on evidence."""

        return tuple(
            record
            for record in self.records
            if record.status is OutcomeLearningStatus.NEEDS_EVIDENCE
        )

    def record_by_id(self, outcome_id: str) -> OutcomeLearningRecord:
        """Return an outcome learning record by id."""

        for record in self.records:
            if record.outcome_id == outcome_id:
                return record
        raise ValueError(f"Unknown outcome_id: {outcome_id}")

    def records_for_belief_revision(
        self,
        revision_id: str,
    ) -> tuple[OutcomeLearningRecord, ...]:
        """Return outcome records linked to a belief revision id."""

        return tuple(
            record
            for record in self.records
            if revision_id in record.belief_revision_ids
        )

    def records_for_causal_revision(
        self,
        revision_id: str,
    ) -> tuple[OutcomeLearningRecord, ...]:
        """Return outcome records linked to a causal revision id."""

        return tuple(
            record
            for record in self.records
            if revision_id in record.causal_revision_ids
        )

    def records_for_prediction_comparison(
        self,
        comparison_id: str,
    ) -> tuple[OutcomeLearningRecord, ...]:
        """Return outcome records linked to a prediction comparison id."""

        return tuple(
            record
            for record in self.records
            if comparison_id in record.prediction_comparison_ids
        )


def build_outcome_learning_record(
    *,
    outcome_id: str,
    summary: str,
    belief_history: BeliefHistory,
    causal_revision_result: CausalRevisionResult,
    comparison_ledger: PredictionComparisonLedger,
    evidence_ids: tuple[str, ...],
) -> OutcomeLearningRecord:
    """Build an outcome learning record from Wave 2 revision artifacts."""

    pressure = _outcome_pressure(
        belief_history=belief_history,
        causal_revision_result=causal_revision_result,
        comparison_ledger=comparison_ledger,
    )
    status = _outcome_status(
        pressure=pressure,
        evidence_ids=evidence_ids,
        belief_history=belief_history,
        causal_revision_result=causal_revision_result,
        comparison_ledger=comparison_ledger,
    )
    return OutcomeLearningRecord(
        outcome_id=outcome_id,
        summary=summary,
        status=status,
        pressure=pressure,
        belief_revision_ids=tuple(
            revision.revision_id for revision in belief_history.all_revisions
        ),
        causal_revision_ids=tuple(
            revision.revision_id for revision in causal_revision_result.revisions
        ),
        prediction_comparison_ids=tuple(
            comparison.comparison_id for comparison in comparison_ledger.comparisons
        ),
        evidence_ids=evidence_ids,
        learning_summary=_learning_summary(
            pressure=pressure,
            belief_history=belief_history,
            causal_revision_result=causal_revision_result,
            comparison_ledger=comparison_ledger,
        ),
        reasons=_outcome_reasons(
            pressure=pressure,
            status=status,
            evidence_ids=evidence_ids,
            belief_history=belief_history,
            causal_revision_result=causal_revision_result,
            comparison_ledger=comparison_ledger,
        ),
    )


def outcome_learning_ledger(
    *records: OutcomeLearningRecord,
) -> OutcomeLearningLedger:
    """Create an outcome learning ledger from records."""

    return OutcomeLearningLedger(records=records)


def _outcome_pressure(
    *,
    belief_history: BeliefHistory,
    causal_revision_result: CausalRevisionResult,
    comparison_ledger: PredictionComparisonLedger,
) -> OutcomePressure:
    """Classify how outcome artifacts pressured cognition state."""

    if (
        belief_history.blocking_revisions
        or causal_revision_result.blocking_revisions
        or comparison_ledger.blocked_comparisons
    ):
        return OutcomePressure.BLOCKED

    matched = bool(comparison_ledger.matched_comparisons)
    diverged = bool(comparison_ledger.diverged_comparisons)
    corrective_belief = any(
        revision.kind
        in {
            BeliefRevisionKind.WEAKENED,
            BeliefRevisionKind.NEEDS_EVIDENCE,
            BeliefRevisionKind.CONTRADICTED,
            BeliefRevisionKind.STALE,
        }
        for revision in belief_history.all_revisions
    )
    corrective_causal = any(
        revision.action
        in {
            CausalRevisionAction.WEAKENED,
            CausalRevisionAction.DISPUTED,
            CausalRevisionAction.BLOCKED,
            CausalRevisionAction.RETIRED,
        }
        for revision in causal_revision_result.revisions
    )

    if matched and (diverged or corrective_belief or corrective_causal):
        return OutcomePressure.MIXED
    if diverged or corrective_belief or corrective_causal:
        return OutcomePressure.CORRECTED
    if matched or belief_history.all_revisions or causal_revision_result.revisions:
        return OutcomePressure.CONFIRMED
    return OutcomePressure.INCONCLUSIVE


def _outcome_status(
    *,
    pressure: OutcomePressure,
    evidence_ids: tuple[str, ...],
    belief_history: BeliefHistory,
    causal_revision_result: CausalRevisionResult,
    comparison_ledger: PredictionComparisonLedger,
) -> OutcomeLearningStatus:
    """Classify outcome learning status from pressure and evidence."""

    if pressure is OutcomePressure.BLOCKED:
        return OutcomeLearningStatus.BLOCKED
    has_links = bool(
        belief_history.all_revisions
        or causal_revision_result.revisions
        or comparison_ledger.comparisons
    )
    if not evidence_ids or not has_links:
        return OutcomeLearningStatus.NEEDS_EVIDENCE
    return OutcomeLearningStatus.ACCEPTED


def _learning_summary(
    *,
    pressure: OutcomePressure,
    belief_history: BeliefHistory,
    causal_revision_result: CausalRevisionResult,
    comparison_ledger: PredictionComparisonLedger,
) -> str:
    """Return a deterministic learning summary."""

    return (
        f"Outcome pressure={pressure.value}; "
        f"belief_revisions={len(belief_history.all_revisions)}; "
        f"causal_revisions={len(causal_revision_result.revisions)}; "
        f"prediction_comparisons={len(comparison_ledger.comparisons)}."
    )


def _outcome_reasons(
    *,
    pressure: OutcomePressure,
    status: OutcomeLearningStatus,
    evidence_ids: tuple[str, ...],
    belief_history: BeliefHistory,
    causal_revision_result: CausalRevisionResult,
    comparison_ledger: PredictionComparisonLedger,
) -> tuple[str, ...]:
    """Return deterministic reasons for outcome learning status."""

    reasons = [
        f"Outcome learning status is {status.value} under {pressure.value} pressure."
    ]
    if not evidence_ids:
        reasons.append("Outcome learning lacks evidence ids.")
    if belief_history.blocking_revisions:
        reasons.append("Belief history contains blocking revisions.")
    if causal_revision_result.blocking_revisions:
        reasons.append("Causal revision result contains blocking revisions.")
    if comparison_ledger.blocked_comparisons:
        reasons.append("Prediction comparison ledger contains blocked comparisons.")
    if comparison_ledger.diverged_comparisons:
        reasons.append(
            "Prediction comparisons include divergence from expected outcome."
        )
    if comparison_ledger.matched_comparisons:
        reasons.append("Prediction comparisons include matched expected outcome.")
    return tuple(reasons)


def _unique_ids(values: Iterable[str], *, label: str) -> set[str]:
    """Return unique ids while rejecting duplicates and blank values."""

    seen: set[str] = set()
    for value in values:
        if not value.strip():
            raise ValueError(f"{label} values cannot be empty.")
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value}")
        seen.add(value)
    return seen
