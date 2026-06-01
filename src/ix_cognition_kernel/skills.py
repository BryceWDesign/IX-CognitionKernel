"""Validated skill records for IX-CognitionKernel Wave 2.

Wave 2 must not treat accepted memory as reusable skill. A skill candidate only
becomes validated after accepted memory provenance, accepted outcome linkage,
explicit applicability conditions, failure modes, and successful reuse evidence
all pass review. This module creates reviewable skill validation records without
executing procedures or granting autonomous authority.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from ix_cognition_kernel.memory import (
    MemoryQuarantineLedger,
    MemoryValidationStatus,
)
from ix_cognition_kernel.outcome import OutcomeLearningLedger, OutcomeLearningStatus


class SkillCandidateKind(StrEnum):
    """Kind of reusable procedure under validation."""

    PROCEDURE = "procedure"
    EVALUATION_CHECK = "evaluation-check"
    RECOVERY_PATTERN = "recovery-pattern"
    CAUSAL_HEURISTIC = "causal-heuristic"


class SkillValidationStatus(StrEnum):
    """Validation status for a skill candidate."""

    CANDIDATE = "candidate"
    VALIDATED = "validated"
    NEEDS_REUSE_EVIDENCE = "needs-reuse-evidence"
    REJECTED = "rejected"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class SkillValidationPolicy:
    """Policy gates for validating reusable skills."""

    minimum_confidence: float = 0.7
    minimum_successful_reuse_records: int = 1
    require_accepted_memory: bool = True
    require_accepted_outcomes: bool = True

    def __post_init__(self) -> None:
        """Validate skill validation policy thresholds."""

        if not 0.0 <= self.minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence must be between 0.0 and 1.0.")
        if self.minimum_successful_reuse_records < 1:
            raise ValueError("minimum_successful_reuse_records must be at least 1.")


DEFAULT_SKILL_VALIDATION_POLICY = SkillValidationPolicy()


@dataclass(frozen=True, slots=True)
class SkillCandidate:
    """Reusable-skill candidate that must be validated before reuse."""

    skill_id: str
    kind: SkillCandidateKind
    name: str
    procedure_steps: tuple[str, ...]
    applicability_conditions: tuple[str, ...]
    failure_modes: tuple[str, ...]
    source_memory_candidate_ids: tuple[str, ...]
    source_outcome_ids: tuple[str, ...]
    confidence: float
    provenance: tuple[str, ...]
    proposed_audit_index: int

    def __post_init__(self) -> None:
        """Validate skill identity, structure, provenance, and confidence."""

        if not self.skill_id.strip():
            raise ValueError("Skill candidates require a non-empty skill_id.")
        if not self.name.strip():
            raise ValueError("Skill candidates require a non-empty name.")
        if not self.procedure_steps:
            raise ValueError("Skill candidates require procedure_steps.")
        if any(not step.strip() for step in self.procedure_steps):
            raise ValueError("Skill candidate procedure_steps cannot be empty.")
        if not self.applicability_conditions:
            raise ValueError("Skill candidates require applicability_conditions.")
        if any(not condition.strip() for condition in self.applicability_conditions):
            raise ValueError(
                "Skill candidate applicability_conditions cannot be empty."
            )
        if not self.failure_modes:
            raise ValueError("Skill candidates require failure_modes.")
        if any(not mode.strip() for mode in self.failure_modes):
            raise ValueError("Skill candidate failure_modes cannot be empty.")
        if not self.source_memory_candidate_ids:
            raise ValueError("Skill candidates require source_memory_candidate_ids.")
        if not self.source_outcome_ids:
            raise ValueError("Skill candidates require source_outcome_ids.")
        _unique_ids(self.source_memory_candidate_ids, label="skill source_memory_id")
        _unique_ids(self.source_outcome_ids, label="skill source_outcome_id")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Skill candidate confidence must be between 0.0 and 1.0.")
        if not self.provenance:
            raise ValueError("Skill candidates require provenance.")
        if any(not entry.strip() for entry in self.provenance):
            raise ValueError("Skill candidate provenance entries cannot be empty.")
        if self.proposed_audit_index < 0:
            raise ValueError("Skill candidate proposed_audit_index cannot be negative.")


@dataclass(frozen=True, slots=True)
class SkillReuseEvidenceRecord:
    """Evidence that a skill candidate was reused under stated conditions."""

    reuse_id: str
    skill_id: str
    outcome_id: str
    evidence_ids: tuple[str, ...]
    succeeded: bool
    audit_index: int
    applicability_condition_ids: tuple[str, ...]
    failure_mode_ids: tuple[str, ...]
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate reuse evidence identity, outcome linkage, and reasons."""

        if not self.reuse_id.strip():
            raise ValueError("Skill reuse evidence requires a non-empty reuse_id.")
        if not self.skill_id.strip():
            raise ValueError("Skill reuse evidence requires a non-empty skill_id.")
        if not self.outcome_id.strip():
            raise ValueError("Skill reuse evidence requires a non-empty outcome_id.")
        if self.audit_index < 0:
            raise ValueError("Skill reuse evidence audit_index cannot be negative.")
        _unique_ids(self.evidence_ids, label="skill reuse evidence_id")
        _unique_ids(
            self.applicability_condition_ids,
            label="skill applicability_condition_id",
        )
        _unique_ids(self.failure_mode_ids, label="skill failure_mode_id")
        if not self.reasons:
            raise ValueError("Skill reuse evidence records require reasons.")
        if any(not reason.strip() for reason in self.reasons):
            raise ValueError("Skill reuse evidence reasons cannot be empty.")
        if self.succeeded and not self.evidence_ids:
            raise ValueError("Successful skill reuse evidence requires evidence_ids.")
        if self.succeeded and not self.applicability_condition_ids:
            raise ValueError(
                "Successful skill reuse evidence requires applicability_condition_ids."
            )
        if not self.succeeded and not self.failure_mode_ids:
            raise ValueError("Failed skill reuse evidence requires failure_mode_ids.")


@dataclass(frozen=True, slots=True)
class SkillValidationRecord:
    """Review record explaining a skill candidate validation result."""

    validation_id: str
    skill_id: str
    status: SkillValidationStatus
    source_memory_candidate_ids: tuple[str, ...]
    source_outcome_ids: tuple[str, ...]
    reuse_evidence_ids: tuple[str, ...]
    reviewer_role_id: str
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate validation identity, traceability, reviewer, and reasons."""

        if not self.validation_id.strip():
            raise ValueError(
                "Skill validation records require a non-empty validation_id."
            )
        if not self.skill_id.strip():
            raise ValueError("Skill validation records require a non-empty skill_id.")
        if not self.reviewer_role_id.strip():
            raise ValueError(
                "Skill validation records require a non-empty reviewer_role_id."
            )
        _unique_ids(
            self.source_memory_candidate_ids,
            label="skill validation source_memory_id",
        )
        _unique_ids(self.source_outcome_ids, label="skill validation outcome_id")
        _unique_ids(self.reuse_evidence_ids, label="skill validation reuse_id")
        if not self.reasons:
            raise ValueError("Skill validation records require reasons.")
        if any(not reason.strip() for reason in self.reasons):
            raise ValueError("Skill validation reasons cannot be empty.")
        if self.status is SkillValidationStatus.VALIDATED:
            self._validate_validated_record()

    @property
    def is_validated(self) -> bool:
        """Return whether this record validates reusable skill status."""

        return self.status is SkillValidationStatus.VALIDATED

    @property
    def is_blocking_status(self) -> bool:
        """Return whether this validation prevents skill reuse."""

        return self.status in {
            SkillValidationStatus.REJECTED,
            SkillValidationStatus.BLOCKED,
        }

    def _validate_validated_record(self) -> None:
        """Validate stricter requirements for reusable skill validation."""

        if not self.source_memory_candidate_ids:
            raise ValueError("Validated skill records require source memory ids.")
        if not self.source_outcome_ids:
            raise ValueError("Validated skill records require source outcome ids.")
        if not self.reuse_evidence_ids:
            raise ValueError("Validated skill records require reuse evidence ids.")


@dataclass(frozen=True, slots=True)
class SkillValidationLedger:
    """Ledger of skill candidates, reuse evidence, and validation records."""

    candidates: tuple[SkillCandidate, ...]
    reuse_records: tuple[SkillReuseEvidenceRecord, ...]
    validations: tuple[SkillValidationRecord, ...]

    def __post_init__(self) -> None:
        """Reject duplicate ids and invalid validation/reuse references."""

        candidate_ids = _unique_ids(
            (candidate.skill_id for candidate in self.candidates),
            label="skill_id",
        )
        _unique_ids(
            (reuse.reuse_id for reuse in self.reuse_records),
            label="skill reuse_id",
        )
        _unique_ids(
            (validation.validation_id for validation in self.validations),
            label="skill validation_id",
        )
        for reuse in self.reuse_records:
            if reuse.skill_id not in candidate_ids:
                raise ValueError(
                    f"Skill reuse {reuse.reuse_id} references unknown skill_id: "
                    f"{reuse.skill_id}"
                )
        seen_validation_skills: set[str] = set()
        for validation in self.validations:
            if validation.skill_id not in candidate_ids:
                raise ValueError(
                    f"Skill validation {validation.validation_id} references "
                    f"unknown skill_id: {validation.skill_id}"
                )
            if validation.skill_id in seen_validation_skills:
                raise ValueError(
                    "Skill validation ledger cannot contain multiple validations "
                    f"for skill_id: {validation.skill_id}"
                )
            seen_validation_skills.add(validation.skill_id)

    @property
    def validated_candidates(self) -> tuple[SkillCandidate, ...]:
        """Return skill candidates validated for reuse."""

        return self._candidates_for_status(SkillValidationStatus.VALIDATED)

    @property
    def candidates_needing_reuse_evidence(self) -> tuple[SkillCandidate, ...]:
        """Return candidates that still need successful reuse evidence."""

        return self._candidates_for_status(SkillValidationStatus.NEEDS_REUSE_EVIDENCE)

    @property
    def rejected_candidates(self) -> tuple[SkillCandidate, ...]:
        """Return rejected skill candidates."""

        return self._candidates_for_status(SkillValidationStatus.REJECTED)

    @property
    def blocked_candidates(self) -> tuple[SkillCandidate, ...]:
        """Return blocked skill candidates."""

        return self._candidates_for_status(SkillValidationStatus.BLOCKED)

    @property
    def blocking_validations(self) -> tuple[SkillValidationRecord, ...]:
        """Return rejected or blocked skill validation records."""

        return tuple(
            validation
            for validation in self.validations
            if validation.is_blocking_status
        )

    def candidate_by_id(self, skill_id: str) -> SkillCandidate:
        """Return a skill candidate by id."""

        for candidate in self.candidates:
            if candidate.skill_id == skill_id:
                return candidate
        raise ValueError(f"Unknown skill_id: {skill_id}")

    def validation_for_skill(self, skill_id: str) -> SkillValidationRecord:
        """Return the validation record for a skill id."""

        for validation in self.validations:
            if validation.skill_id == skill_id:
                return validation
        raise ValueError(f"Unknown skill validation skill_id: {skill_id}")

    def reuse_records_for_skill(
        self,
        skill_id: str,
    ) -> tuple[SkillReuseEvidenceRecord, ...]:
        """Return reuse evidence records for a skill id."""

        return tuple(
            reuse for reuse in self.reuse_records if reuse.skill_id == skill_id
        )

    def _candidates_for_status(
        self,
        status: SkillValidationStatus,
    ) -> tuple[SkillCandidate, ...]:
        """Return candidates whose validation has a given status."""

        candidate_by_id = {
            candidate.skill_id: candidate for candidate in self.candidates
        }
        return tuple(
            candidate_by_id[validation.skill_id]
            for validation in self.validations
            if validation.status is status
        )


def evaluate_skill_candidates(
    *,
    candidates: tuple[SkillCandidate, ...],
    reuse_records: tuple[SkillReuseEvidenceRecord, ...],
    memory_ledger: MemoryQuarantineLedger,
    outcome_ledger: OutcomeLearningLedger,
    reviewer_role_id: str = "learning-archivist",
    policy: SkillValidationPolicy = DEFAULT_SKILL_VALIDATION_POLICY,
) -> SkillValidationLedger:
    """Evaluate skill candidates through validation gates."""

    if not reviewer_role_id.strip():
        raise ValueError("reviewer_role_id cannot be empty.")

    validations = tuple(
        evaluate_skill_candidate(
            candidate=candidate,
            reuse_records=tuple(
                reuse for reuse in reuse_records if reuse.skill_id == candidate.skill_id
            ),
            memory_ledger=memory_ledger,
            outcome_ledger=outcome_ledger,
            reviewer_role_id=reviewer_role_id,
            policy=policy,
            validation_index=index,
        )
        for index, candidate in enumerate(candidates)
    )
    return SkillValidationLedger(
        candidates=candidates,
        reuse_records=reuse_records,
        validations=validations,
    )


def evaluate_skill_candidate(
    *,
    candidate: SkillCandidate,
    reuse_records: tuple[SkillReuseEvidenceRecord, ...],
    memory_ledger: MemoryQuarantineLedger,
    outcome_ledger: OutcomeLearningLedger,
    reviewer_role_id: str = "learning-archivist",
    policy: SkillValidationPolicy = DEFAULT_SKILL_VALIDATION_POLICY,
    validation_index: int = 0,
) -> SkillValidationRecord:
    """Evaluate one skill candidate without granting execution authority."""

    status, reasons = _skill_status_and_reasons(
        candidate=candidate,
        reuse_records=reuse_records,
        memory_ledger=memory_ledger,
        outcome_ledger=outcome_ledger,
        policy=policy,
    )
    successful_reuse_ids = tuple(
        reuse.reuse_id
        for reuse in reuse_records
        if reuse.skill_id == candidate.skill_id and reuse.succeeded
    )
    return SkillValidationRecord(
        validation_id=f"skill-validation-{validation_index:03d}",
        skill_id=candidate.skill_id,
        status=status,
        source_memory_candidate_ids=candidate.source_memory_candidate_ids
        if status is SkillValidationStatus.VALIDATED
        else (),
        source_outcome_ids=candidate.source_outcome_ids
        if status is SkillValidationStatus.VALIDATED
        else (),
        reuse_evidence_ids=successful_reuse_ids
        if status is SkillValidationStatus.VALIDATED
        else (),
        reviewer_role_id=reviewer_role_id,
        reasons=tuple(reasons),
    )


def _skill_status_and_reasons(
    *,
    candidate: SkillCandidate,
    reuse_records: tuple[SkillReuseEvidenceRecord, ...],
    memory_ledger: MemoryQuarantineLedger,
    outcome_ledger: OutcomeLearningLedger,
    policy: SkillValidationPolicy,
) -> tuple[SkillValidationStatus, list[str]]:
    """Return skill validation status and reasons."""

    reasons: list[str] = []
    if candidate.confidence < policy.minimum_confidence:
        reasons.append(
            f"Skill candidate confidence {candidate.confidence} is below minimum "
            f"{policy.minimum_confidence}."
        )
        return SkillValidationStatus.NEEDS_REUSE_EVIDENCE, reasons

    memory_status = _memory_validation_status(candidate, memory_ledger)
    if memory_status is not None:
        reasons.append(memory_status)
        return SkillValidationStatus.BLOCKED, reasons

    outcome_status = _outcome_validation_status(candidate, outcome_ledger)
    if outcome_status is not None:
        reasons.append(outcome_status)
        return SkillValidationStatus.BLOCKED, reasons

    skill_reuse = tuple(
        reuse for reuse in reuse_records if reuse.skill_id == candidate.skill_id
    )
    failed_reuse = tuple(reuse for reuse in skill_reuse if not reuse.succeeded)
    if failed_reuse:
        reasons.append("Skill candidate has failed reuse evidence.")
        return SkillValidationStatus.REJECTED, reasons

    successful_reuse = tuple(reuse for reuse in skill_reuse if reuse.succeeded)
    if len(successful_reuse) < policy.minimum_successful_reuse_records:
        reasons.append("Skill candidate lacks required successful reuse evidence.")
        return SkillValidationStatus.NEEDS_REUSE_EVIDENCE, reasons

    reuse_outcome_status = _reuse_outcome_validation_status(
        successful_reuse, outcome_ledger
    )
    if reuse_outcome_status is not None:
        reasons.append(reuse_outcome_status)
        return SkillValidationStatus.BLOCKED, reasons

    reasons.append("Skill candidate passed validation gates for reusable status.")
    return SkillValidationStatus.VALIDATED, reasons


def _memory_validation_status(
    candidate: SkillCandidate,
    memory_ledger: MemoryQuarantineLedger,
) -> str | None:
    """Return blocking memory reason, if one exists."""

    for memory_id in candidate.source_memory_candidate_ids:
        validation = memory_ledger.validation_for_candidate(memory_id)
        if validation.status is not MemoryValidationStatus.ACCEPTED:
            return "Skill candidate source memory is not accepted."
    return None


def _outcome_validation_status(
    candidate: SkillCandidate,
    outcome_ledger: OutcomeLearningLedger,
) -> str | None:
    """Return blocking source-outcome reason, if one exists."""

    for outcome_id in candidate.source_outcome_ids:
        outcome = outcome_ledger.record_by_id(outcome_id)
        if outcome.status is not OutcomeLearningStatus.ACCEPTED:
            return "Skill candidate source outcome is not accepted."
    return None


def _reuse_outcome_validation_status(
    reuse_records: tuple[SkillReuseEvidenceRecord, ...],
    outcome_ledger: OutcomeLearningLedger,
) -> str | None:
    """Return blocking reuse-outcome reason, if one exists."""

    for reuse in reuse_records:
        outcome = outcome_ledger.record_by_id(reuse.outcome_id)
        if outcome.status is not OutcomeLearningStatus.ACCEPTED:
            return "Skill reuse evidence links to non-accepted outcome."
    return None


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
