"""Memory quarantine engine for IX-CognitionKernel Wave 2.

Wave 2 must not turn raw model output or single observations into durable memory.
This module keeps proposed memories in quarantine until provenance, evidence,
outcome linkage, contradiction checks, confidence, and expiry rules are satisfied.
It does not implement skill validation, long-term persistence, or autonomous
memory writes. It creates reviewable records showing why memory was accepted,
rejected, expired, or kept quarantined.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from ix_cognition_kernel.outcome import OutcomeLearningLedger, OutcomeLearningStatus


class MemoryCandidateKind(StrEnum):
    """Kind of proposed memory under quarantine review."""

    BELIEF_SUMMARY = "belief-summary"
    CAUSAL_LESSON = "causal-lesson"
    OUTCOME_SUMMARY = "outcome-summary"
    PROCEDURE_HINT = "procedure-hint"


class MemoryValidationStatus(StrEnum):
    """Validation status for a quarantined memory candidate."""

    QUARANTINED = "quarantined"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class MemoryQuarantinePolicy:
    """Policy gates for turning memory candidates into accepted memory."""

    minimum_confidence: float = 0.65
    expire_after_audit_gap: int = 6
    require_outcome_link: bool = True

    def __post_init__(self) -> None:
        """Validate quarantine policy thresholds."""

        if not 0.0 <= self.minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence must be between 0.0 and 1.0.")
        if self.expire_after_audit_gap < 0:
            raise ValueError("expire_after_audit_gap cannot be negative.")


DEFAULT_MEMORY_QUARANTINE_POLICY = MemoryQuarantinePolicy()


@dataclass(frozen=True, slots=True)
class MemoryCandidate:
    """Raw proposed memory that must pass quarantine before durable use."""

    candidate_id: str
    kind: MemoryCandidateKind
    content: str
    provenance: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    source_outcome_ids: tuple[str, ...]
    confidence: float
    proposed_audit_index: int
    contradiction_ids: tuple[str, ...] = ()
    unsafe_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate candidate identity, provenance, evidence, and risk signals."""

        if not self.candidate_id.strip():
            raise ValueError("Memory candidates require a non-empty candidate_id.")
        if not self.content.strip():
            raise ValueError("Memory candidates require non-empty content.")
        if not self.provenance:
            raise ValueError("Memory candidates require provenance.")
        if any(not entry.strip() for entry in self.provenance):
            raise ValueError("Memory candidate provenance entries cannot be empty.")
        _unique_ids(self.evidence_ids, label="memory candidate evidence_id")
        _unique_ids(self.source_outcome_ids, label="memory candidate outcome_id")
        _unique_ids(self.contradiction_ids, label="memory candidate contradiction_id")
        if any(not reason.strip() for reason in self.unsafe_reasons):
            raise ValueError("Memory candidate unsafe reasons cannot be empty.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Memory candidate confidence must be between 0.0 and 1.0.")
        if self.proposed_audit_index < 0:
            raise ValueError(
                "Memory candidate proposed_audit_index cannot be negative."
            )

    @property
    def has_known_risk(self) -> bool:
        """Return whether contradiction or unsafe storage risk is present."""

        return bool(self.contradiction_ids or self.unsafe_reasons)


@dataclass(frozen=True, slots=True)
class MemoryValidationRecord:
    """Review record explaining a memory candidate's quarantine status."""

    validation_id: str
    candidate_id: str
    status: MemoryValidationStatus
    evidence_ids: tuple[str, ...]
    outcome_ids: tuple[str, ...]
    reviewer_role_id: str
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate validation identity, linkage, reviewer, and reasons."""

        if not self.validation_id.strip():
            raise ValueError(
                "Memory validation records require a non-empty validation_id."
            )
        if not self.candidate_id.strip():
            raise ValueError(
                "Memory validation records require a non-empty candidate_id."
            )
        if not self.reviewer_role_id.strip():
            raise ValueError(
                "Memory validation records require a non-empty reviewer_role_id."
            )
        _unique_ids(self.evidence_ids, label="memory validation evidence_id")
        _unique_ids(self.outcome_ids, label="memory validation outcome_id")
        if not self.reasons:
            raise ValueError("Memory validation records require reasons.")
        if any(not reason.strip() for reason in self.reasons):
            raise ValueError("Memory validation reasons cannot be empty.")
        if self.status is MemoryValidationStatus.ACCEPTED:
            self._validate_accepted_record()

    @property
    def is_accepted(self) -> bool:
        """Return whether the candidate was accepted as durable memory."""

        return self.status is MemoryValidationStatus.ACCEPTED

    @property
    def is_blocking_status(self) -> bool:
        """Return whether the candidate cannot currently become durable memory."""

        return self.status in {
            MemoryValidationStatus.REJECTED,
            MemoryValidationStatus.EXPIRED,
        }

    def _validate_accepted_record(self) -> None:
        """Validate stricter accepted-memory traceability rules."""

        if not self.evidence_ids:
            raise ValueError("Accepted memory validation records require evidence_ids.")
        if not self.outcome_ids:
            raise ValueError("Accepted memory validation records require outcome_ids.")


@dataclass(frozen=True, slots=True)
class MemoryQuarantineLedger:
    """Ledger of memory candidates and their quarantine validation records."""

    candidates: tuple[MemoryCandidate, ...]
    validations: tuple[MemoryValidationRecord, ...]

    def __post_init__(self) -> None:
        """Reject duplicate candidates, duplicate validations, and bad references."""

        candidate_ids = _unique_ids(
            (candidate.candidate_id for candidate in self.candidates),
            label="memory candidate_id",
        )
        _unique_ids(
            (validation.validation_id for validation in self.validations),
            label="memory validation_id",
        )
        seen_validation_candidates: set[str] = set()
        for validation in self.validations:
            if validation.candidate_id not in candidate_ids:
                raise ValueError(
                    f"Memory validation {validation.validation_id} references "
                    f"unknown candidate_id: {validation.candidate_id}"
                )
            if validation.candidate_id in seen_validation_candidates:
                raise ValueError(
                    "Memory quarantine ledger cannot contain multiple validations "
                    f"for candidate_id: {validation.candidate_id}"
                )
            seen_validation_candidates.add(validation.candidate_id)

    @property
    def accepted_candidates(self) -> tuple[MemoryCandidate, ...]:
        """Return candidates accepted as durable memory."""

        return self._candidates_for_status(MemoryValidationStatus.ACCEPTED)

    @property
    def quarantined_candidates(self) -> tuple[MemoryCandidate, ...]:
        """Return candidates still held in quarantine."""

        return self._candidates_for_status(MemoryValidationStatus.QUARANTINED)

    @property
    def rejected_candidates(self) -> tuple[MemoryCandidate, ...]:
        """Return candidates rejected by quarantine review."""

        return self._candidates_for_status(MemoryValidationStatus.REJECTED)

    @property
    def expired_candidates(self) -> tuple[MemoryCandidate, ...]:
        """Return candidates expired before validation."""

        return self._candidates_for_status(MemoryValidationStatus.EXPIRED)

    @property
    def blocking_validations(self) -> tuple[MemoryValidationRecord, ...]:
        """Return rejected or expired memory validation records."""

        return tuple(
            validation
            for validation in self.validations
            if validation.is_blocking_status
        )

    def candidate_by_id(self, candidate_id: str) -> MemoryCandidate:
        """Return a memory candidate by id."""

        for candidate in self.candidates:
            if candidate.candidate_id == candidate_id:
                return candidate
        raise ValueError(f"Unknown memory candidate_id: {candidate_id}")

    def validation_for_candidate(self, candidate_id: str) -> MemoryValidationRecord:
        """Return the validation record for a candidate id."""

        for validation in self.validations:
            if validation.candidate_id == candidate_id:
                return validation
        raise ValueError(f"Unknown memory validation candidate_id: {candidate_id}")

    def _candidates_for_status(
        self,
        status: MemoryValidationStatus,
    ) -> tuple[MemoryCandidate, ...]:
        """Return candidates whose validation has a given status."""

        candidate_by_id = {
            candidate.candidate_id: candidate for candidate in self.candidates
        }
        return tuple(
            candidate_by_id[validation.candidate_id]
            for validation in self.validations
            if validation.status is status
        )


def evaluate_memory_quarantine(
    *,
    candidates: tuple[MemoryCandidate, ...],
    outcome_ledger: OutcomeLearningLedger,
    current_audit_index: int,
    reviewer_role_id: str = "memory-integrity-specialist",
    policy: MemoryQuarantinePolicy = DEFAULT_MEMORY_QUARANTINE_POLICY,
) -> MemoryQuarantineLedger:
    """Evaluate memory candidates through quarantine gates."""

    if current_audit_index < 0:
        raise ValueError("current_audit_index cannot be negative.")
    if not reviewer_role_id.strip():
        raise ValueError("reviewer_role_id cannot be empty.")

    validations = tuple(
        evaluate_memory_candidate(
            candidate=candidate,
            outcome_ledger=outcome_ledger,
            current_audit_index=current_audit_index,
            reviewer_role_id=reviewer_role_id,
            policy=policy,
            validation_index=index,
        )
        for index, candidate in enumerate(candidates)
    )
    return MemoryQuarantineLedger(candidates=candidates, validations=validations)


def evaluate_memory_candidate(
    *,
    candidate: MemoryCandidate,
    outcome_ledger: OutcomeLearningLedger,
    current_audit_index: int,
    reviewer_role_id: str = "memory-integrity-specialist",
    policy: MemoryQuarantinePolicy = DEFAULT_MEMORY_QUARANTINE_POLICY,
    validation_index: int = 0,
) -> MemoryValidationRecord:
    """Evaluate one memory candidate without writing durable memory."""

    if current_audit_index < candidate.proposed_audit_index:
        raise ValueError("current_audit_index cannot precede candidate proposal.")

    status, reasons = _memory_status_and_reasons(
        candidate=candidate,
        outcome_ledger=outcome_ledger,
        current_audit_index=current_audit_index,
        policy=policy,
    )
    return MemoryValidationRecord(
        validation_id=f"memory-validation-{validation_index:03d}",
        candidate_id=candidate.candidate_id,
        status=status,
        evidence_ids=candidate.evidence_ids
        if status is MemoryValidationStatus.ACCEPTED
        else (),
        outcome_ids=candidate.source_outcome_ids
        if status is MemoryValidationStatus.ACCEPTED
        else (),
        reviewer_role_id=reviewer_role_id,
        reasons=tuple(reasons),
    )


def _memory_status_and_reasons(
    *,
    candidate: MemoryCandidate,
    outcome_ledger: OutcomeLearningLedger,
    current_audit_index: int,
    policy: MemoryQuarantinePolicy,
) -> tuple[MemoryValidationStatus, list[str]]:
    """Return quarantine status and reasons for one candidate."""

    reasons: list[str] = []
    age = current_audit_index - candidate.proposed_audit_index
    if policy.expire_after_audit_gap and age >= policy.expire_after_audit_gap:
        reasons.append(
            f"Memory candidate expired after audit gap {age} without acceptance."
        )
        return MemoryValidationStatus.EXPIRED, reasons
    if candidate.unsafe_reasons:
        reasons.append("Memory candidate contains unsafe-to-store reasons.")
        return MemoryValidationStatus.REJECTED, reasons
    if candidate.contradiction_ids:
        reasons.append("Memory candidate has unresolved contradiction ids.")
        return MemoryValidationStatus.REJECTED, reasons
    if candidate.confidence < policy.minimum_confidence:
        reasons.append(
            f"Memory candidate confidence {candidate.confidence} is below minimum "
            f"{policy.minimum_confidence}."
        )
        return MemoryValidationStatus.QUARANTINED, reasons
    if not candidate.evidence_ids:
        reasons.append("Memory candidate lacks evidence ids.")
        return MemoryValidationStatus.QUARANTINED, reasons
    if policy.require_outcome_link and not candidate.source_outcome_ids:
        reasons.append("Memory candidate lacks required outcome linkage.")
        return MemoryValidationStatus.QUARANTINED, reasons

    linked_outcomes = tuple(
        outcome_ledger.record_by_id(outcome_id)
        for outcome_id in candidate.source_outcome_ids
    )
    blocked_or_unaccepted = tuple(
        outcome
        for outcome in linked_outcomes
        if outcome.status is not OutcomeLearningStatus.ACCEPTED
    )
    if blocked_or_unaccepted:
        reasons.append("Memory candidate links to non-accepted outcome learning.")
        return MemoryValidationStatus.REJECTED, reasons

    reasons.append("Memory candidate passed quarantine gates for durable use.")
    return MemoryValidationStatus.ACCEPTED, reasons


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
