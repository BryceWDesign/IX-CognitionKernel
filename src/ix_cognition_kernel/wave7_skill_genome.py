"""Wave 7 skill genome.

The skill genome tracks measured capability growth as auditable genes. It keeps
skill evidence, failures, transfer attempts, staleness, authority boundaries,
and confidence visible without allowing a demonstrated skill to become
execution permission.

Wave 7 skill doctrine:

- skill is not authorization,
- transfer is measured separately from original-domain success,
- failure memory must remain visible,
- stale or revoked skills cannot support stronger maturity claims,
- confidence must be evidence-bound,
- no skill can self-authorize body or tool use.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

WAVE_SEVEN_SKILL_EVIDENCE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-skill-evidence-v1"
)
WAVE_SEVEN_SKILL_FAILURE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-skill-failure-v1"
)
WAVE_SEVEN_TRANSFER_ATTEMPT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-transfer-attempt-v1"
)
WAVE_SEVEN_SKILL_GENE_SCHEMA_VERSION = "ix-cognition-kernel-wave7-skill-gene-v1"
WAVE_SEVEN_SKILL_GENOME_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-skill-genome-v1"
)
WAVE_SEVEN_SKILL_GENOME_REPORT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave7-skill-genome-report-v1"
)


class SkillStatus(StrEnum):
    """Reviewable status for a measured skill gene."""

    UNPROVEN = "unproven"
    EMERGING = "emerging"
    DEMONSTRATED = "demonstrated"
    CONSTRAINED = "constrained"
    STALE = "stale"
    REVOKED = "revoked"


class SkillRisk(StrEnum):
    """Risk tier for a skill gene."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class SkillEvidenceKind(StrEnum):
    """Kinds of evidence that may support a skill."""

    MEASURED_OUTCOME = "measured-outcome"
    EXPERIENCE_RECORD = "experience-record"
    TRANSFER_ATTEMPT = "transfer-attempt"
    HUMAN_REVIEW = "human-review"
    FAILURE_ANALYSIS = "failure-analysis"


class TransferResult(StrEnum):
    """Measured result of a transfer attempt."""

    NOT_ATTEMPTED = "not-attempted"
    PASSED = "passed"
    PARTIAL = "partial"
    FAILED = "failed"
    BLOCKED = "blocked"


class SkillGenomeDecision(StrEnum):
    """Fail-closed decision for a skill genome report."""

    RECORD_ONLY = "record-only"
    READY_FOR_REVIEW = "ready-for-review"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class SkillEvidence:
    """Evidence supporting or limiting a measured skill."""

    evidence_id: str
    kind: SkillEvidenceKind
    summary: str
    source_record_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    confidence_delta: float
    measured: bool = True
    schema_version: str = WAVE_SEVEN_SKILL_EVIDENCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate skill evidence and confidence delta."""

        object.__setattr__(
            self,
            "evidence_id",
            _require_non_empty(self.evidence_id, "evidence_id"),
        )
        object.__setattr__(
            self,
            "summary",
            _require_non_empty(self.summary, "summary"),
        )
        object.__setattr__(
            self,
            "source_record_ids",
            _normalize_unique_text_tuple(
                self.source_record_ids, label="source_record_id"
            ),
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
        if not -1.0 <= self.confidence_delta <= 1.0:
            raise ValueError("Skill evidence confidence_delta must be -1.0 to 1.0.")
        if not self.evidence_ids:
            raise ValueError("Skill evidence requires evidence ids.")
        if self.measured and not self.source_record_ids:
            raise ValueError("Measured skill evidence requires source record ids.")
        if not self.measured and self.confidence_delta > 0.0:
            raise ValueError("Unmeasured evidence cannot increase confidence.")

    @property
    def supports_skill(self) -> bool:
        """Return whether this evidence increases skill confidence."""

        return self.measured and self.confidence_delta > 0.0

    @property
    def weakens_skill(self) -> bool:
        """Return whether this evidence decreases skill confidence."""

        return self.confidence_delta < 0.0

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic skill-evidence payload."""

        return {
            "confidence_delta": self.confidence_delta,
            "evidence_id": self.evidence_id,
            "evidence_ids": list(self.evidence_ids),
            "kind": self.kind.value,
            "measured": self.measured,
            "schema_version": self.schema_version,
            "source_record_ids": list(self.source_record_ids),
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this evidence."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class SkillFailure:
    """Persistent failure memory attached to a skill gene."""

    failure_id: str
    summary: str
    domain: str
    affected_operations: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    unresolved: bool = True
    corrective_action: str = ""
    schema_version: str = WAVE_SEVEN_SKILL_FAILURE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate failure memory and corrective state."""

        object.__setattr__(
            self,
            "failure_id",
            _require_non_empty(self.failure_id, "failure_id"),
        )
        object.__setattr__(
            self,
            "summary",
            _require_non_empty(self.summary, "summary"),
        )
        object.__setattr__(
            self,
            "domain",
            _require_non_empty(self.domain, "domain"),
        )
        object.__setattr__(
            self,
            "affected_operations",
            _normalize_unique_text_tuple(
                self.affected_operations, label="affected_operation"
            ),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "corrective_action",
            _normalize_optional_text(self.corrective_action),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.affected_operations:
            raise ValueError("Skill failures require affected operations.")
        if not self.evidence_ids:
            raise ValueError("Skill failures require evidence ids.")
        if not self.unresolved and not self.corrective_action:
            raise ValueError("Resolved skill failures require corrective_action.")

    @property
    def blocks_transfer_claim(self) -> bool:
        """Return whether this failure blocks transfer claims."""

        return self.unresolved

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic skill-failure payload."""

        return {
            "affected_operations": list(self.affected_operations),
            "corrective_action": self.corrective_action,
            "domain": self.domain,
            "evidence_ids": list(self.evidence_ids),
            "failure_id": self.failure_id,
            "schema_version": self.schema_version,
            "summary": self.summary,
            "unresolved": self.unresolved,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this failure."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class TransferAttempt:
    """Measured attempt to transfer a skill into a new domain or task family."""

    transfer_id: str
    source_domain: str
    target_domain: str
    task_family: str
    result: TransferResult
    source_skill_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    lesson: str = ""
    schema_version: str = WAVE_SEVEN_TRANSFER_ATTEMPT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate transfer attempt and lesson discipline."""

        object.__setattr__(
            self,
            "transfer_id",
            _require_non_empty(self.transfer_id, "transfer_id"),
        )
        object.__setattr__(
            self,
            "source_domain",
            _require_non_empty(self.source_domain, "source_domain"),
        )
        object.__setattr__(
            self,
            "target_domain",
            _require_non_empty(self.target_domain, "target_domain"),
        )
        object.__setattr__(
            self,
            "task_family",
            _require_non_empty(self.task_family, "task_family"),
        )
        object.__setattr__(
            self,
            "source_skill_ids",
            _normalize_unique_text_tuple(
                self.source_skill_ids, label="source_skill_id"
            ),
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
        if not self.source_skill_ids:
            raise ValueError("Transfer attempts require source skill ids.")
        if not self.evidence_ids:
            raise ValueError("Transfer attempts require evidence ids.")
        if self.result is TransferResult.NOT_ATTEMPTED:
            raise ValueError("Transfer attempts must have an attempted result.")
        if self.result in {
            TransferResult.PARTIAL,
            TransferResult.FAILED,
            TransferResult.BLOCKED,
        } and not self.lesson:
            raise ValueError("Partial, failed, or blocked transfer needs lesson.")

    @property
    def passed(self) -> bool:
        """Return whether transfer passed."""

        return self.result is TransferResult.PASSED

    @property
    def blocks_generalization_claim(self) -> bool:
        """Return whether this transfer blocks stronger generalization claims."""

        return self.result in {TransferResult.FAILED, TransferResult.BLOCKED}

    @property
    def changes_future_reasoning(self) -> bool:
        """Return whether this transfer produced a lesson."""

        return bool(self.lesson)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic transfer-attempt payload."""

        return {
            "evidence_ids": list(self.evidence_ids),
            "lesson": self.lesson,
            "result": self.result.value,
            "schema_version": self.schema_version,
            "source_domain": self.source_domain,
            "source_skill_ids": list(self.source_skill_ids),
            "target_domain": self.target_domain,
            "task_family": self.task_family,
            "transfer_id": self.transfer_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this transfer."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class SkillGene:
    """One auditable capability gene in the Wave 7 skill genome."""

    skill_id: str
    name: str
    domain: str
    operations: tuple[str, ...]
    status: SkillStatus
    risk: SkillRisk
    evidence: tuple[SkillEvidence, ...]
    failures: tuple[SkillFailure, ...]
    transfer_attempts: tuple[TransferAttempt, ...]
    authority_refs: tuple[str, ...]
    confidence: float
    stale_reason: str = ""
    revoked_reason: str = ""
    claims_authorization: bool = False
    schema_version: str = WAVE_SEVEN_SKILL_GENE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate skill gene and prevent authorization claims."""

        if self.claims_authorization:
            raise ValueError("Skill genes must not claim authorization.")
        object.__setattr__(
            self,
            "skill_id",
            _require_non_empty(self.skill_id, "skill_id"),
        )
        object.__setattr__(self, "name", _require_non_empty(self.name, "name"))
        object.__setattr__(
            self,
            "domain",
            _require_non_empty(self.domain, "domain"),
        )
        object.__setattr__(
            self,
            "operations",
            _normalize_unique_text_tuple(self.operations, label="operation"),
        )
        object.__setattr__(
            self,
            "evidence",
            tuple(sorted(self.evidence, key=lambda item: item.evidence_id)),
        )
        object.__setattr__(
            self,
            "failures",
            tuple(sorted(self.failures, key=lambda item: item.failure_id)),
        )
        object.__setattr__(
            self,
            "transfer_attempts",
            tuple(
                sorted(
                    self.transfer_attempts,
                    key=lambda attempt: attempt.transfer_id,
                )
            ),
        )
        object.__setattr__(
            self,
            "authority_refs",
            _normalize_unique_text_tuple(self.authority_refs, label="authority_ref"),
        )
        object.__setattr__(
            self,
            "stale_reason",
            _normalize_optional_text(self.stale_reason),
        )
        object.__setattr__(
            self,
            "revoked_reason",
            _normalize_optional_text(self.revoked_reason),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Skill confidence must be between 0.0 and 1.0.")
        if not self.operations:
            raise ValueError("Skill genes require operations.")
        if not self.authority_refs:
            raise ValueError("Skill genes require authority refs.")
        _ensure_unique((item.evidence_id for item in self.evidence), label="evidence_id")
        _ensure_unique((item.failure_id for item in self.failures), label="failure_id")
        _ensure_unique(
            (item.transfer_id for item in self.transfer_attempts),
            label="transfer_id",
        )
        if self.status is SkillStatus.UNPROVEN and self.confidence > 0.0:
            raise ValueError("Unproven skills must have zero confidence.")
        if self.status is SkillStatus.REVOKED and self.confidence > 0.0:
            raise ValueError("Revoked skills must have zero confidence.")
        if self.status is SkillStatus.STALE and not self.stale_reason:
            raise ValueError("Stale skills require stale_reason.")
        if self.status is SkillStatus.REVOKED and not self.revoked_reason:
            raise ValueError("Revoked skills require revoked_reason.")
        if self.status in {
            SkillStatus.EMERGING,
            SkillStatus.DEMONSTRATED,
            SkillStatus.CONSTRAINED,
        } and not self.evidence:
            raise ValueError("Active skill genes require evidence.")

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound to this skill gene."""

        evidence_ids: list[str] = []
        for evidence in self.evidence:
            evidence_ids.extend(evidence.evidence_ids)
        for failure in self.failures:
            evidence_ids.extend(failure.evidence_ids)
        for transfer in self.transfer_attempts:
            evidence_ids.extend(transfer.evidence_ids)
        return _normalize_unique_text_tuple(evidence_ids, label="evidence_id")

    @property
    def failure_ids(self) -> tuple[str, ...]:
        """Return failure ids attached to this skill gene."""

        return tuple(failure.failure_id for failure in self.failures)

    @property
    def unresolved_failure_ids(self) -> tuple[str, ...]:
        """Return unresolved failure ids."""

        return tuple(
            failure.failure_id for failure in self.failures if failure.unresolved
        )

    @property
    def transfer_ids(self) -> tuple[str, ...]:
        """Return transfer attempt ids."""

        return tuple(attempt.transfer_id for attempt in self.transfer_attempts)

    @property
    def passed_transfer_ids(self) -> tuple[str, ...]:
        """Return passed transfer attempt ids."""

        return tuple(
            attempt.transfer_id for attempt in self.transfer_attempts if attempt.passed
        )

    @property
    def blocked_transfer_ids(self) -> tuple[str, ...]:
        """Return transfers blocking generalization claims."""

        return tuple(
            attempt.transfer_id
            for attempt in self.transfer_attempts
            if attempt.blocks_generalization_claim
        )

    @property
    def needs_more_evidence(self) -> bool:
        """Return whether this skill needs more evidence."""

        return self.status in {SkillStatus.UNPROVEN, SkillStatus.STALE}

    @property
    def needs_review(self) -> bool:
        """Return whether this skill needs human review before stronger claims."""

        return (
            self.status is SkillStatus.CONSTRAINED
            or self.risk in {SkillRisk.HIGH, SkillRisk.CRITICAL}
            or bool(self.unresolved_failure_ids)
        )

    @property
    def blocks_claim(self) -> bool:
        """Return whether this skill blocks stronger maturity claims."""

        return (
            self.status is SkillStatus.REVOKED
            or bool(self.unresolved_failure_ids)
            or bool(self.blocked_transfer_ids)
        )

    @property
    def transfer_demonstrated(self) -> bool:
        """Return whether the skill has at least one passed transfer attempt."""

        return bool(self.passed_transfer_ids)

    @property
    def changes_future_reasoning(self) -> bool:
        """Return whether failure or transfer lessons changed future reasoning."""

        return any(failure.corrective_action for failure in self.failures) or any(
            attempt.changes_future_reasoning for attempt in self.transfer_attempts
        )

    def supports_operation(self, operation: str) -> bool:
        """Return whether this skill covers the requested operation."""

        return operation.strip() in self.operations

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic skill-gene payload."""

        return {
            "authority_refs": list(self.authority_refs),
            "blocked_transfer_ids": list(self.blocked_transfer_ids),
            "claims_authorization": self.claims_authorization,
            "confidence": self.confidence,
            "domain": self.domain,
            "evidence_fingerprints": [item.fingerprint() for item in self.evidence],
            "evidence_ids": list(self.evidence_ids),
            "failure_fingerprints": [item.fingerprint() for item in self.failures],
            "name": self.name,
            "operations": list(self.operations),
            "passed_transfer_ids": list(self.passed_transfer_ids),
            "revoked_reason": self.revoked_reason,
            "risk": self.risk.value,
            "schema_version": self.schema_version,
            "skill_id": self.skill_id,
            "stale_reason": self.stale_reason,
            "status": self.status.value,
            "transfer_fingerprints": [
                item.fingerprint() for item in self.transfer_attempts
            ],
            "unresolved_failure_ids": list(self.unresolved_failure_ids),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this skill gene."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class SkillGenome:
    """Collection of Wave 7 skill genes and capability memory."""

    genome_id: str
    skills: tuple[SkillGene, ...]
    doctrine_ids: tuple[str, ...]
    authority_refs: tuple[str, ...]
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SEVEN_SKILL_GENOME_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate skill genome and preserve capability boundaries."""

        object.__setattr__(
            self,
            "genome_id",
            _require_non_empty(self.genome_id, "genome_id"),
        )
        object.__setattr__(
            self,
            "skills",
            tuple(sorted(self.skills, key=lambda skill: skill.skill_id)),
        )
        object.__setattr__(
            self,
            "doctrine_ids",
            _normalize_unique_text_tuple(self.doctrine_ids, label="doctrine_id"),
        )
        object.__setattr__(
            self,
            "authority_refs",
            _normalize_unique_text_tuple(self.authority_refs, label="authority_ref"),
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
        if not self.skills:
            raise ValueError("Skill genomes require skills.")
        if not self.doctrine_ids:
            raise ValueError("Skill genomes require doctrine ids.")
        if not self.authority_refs:
            raise ValueError("Skill genomes require authority refs.")
        _ensure_unique((skill.skill_id for skill in self.skills), label="skill_id")

    @property
    def skill_ids(self) -> tuple[str, ...]:
        """Return skill ids in this genome."""

        return tuple(skill.skill_id for skill in self.skills)

    @property
    def demonstrated_skill_ids(self) -> tuple[str, ...]:
        """Return demonstrated skill ids."""

        return tuple(
            skill.skill_id
            for skill in self.skills
            if skill.status is SkillStatus.DEMONSTRATED
        )

    @property
    def constrained_skill_ids(self) -> tuple[str, ...]:
        """Return constrained skill ids."""

        return tuple(
            skill.skill_id
            for skill in self.skills
            if skill.status is SkillStatus.CONSTRAINED
        )

    @property
    def stale_skill_ids(self) -> tuple[str, ...]:
        """Return stale skill ids."""

        return tuple(
            skill.skill_id for skill in self.skills if skill.status is SkillStatus.STALE
        )

    @property
    def revoked_skill_ids(self) -> tuple[str, ...]:
        """Return revoked skill ids."""

        return tuple(
            skill.skill_id
            for skill in self.skills
            if skill.status is SkillStatus.REVOKED
        )

    @property
    def review_skill_ids(self) -> tuple[str, ...]:
        """Return skill ids needing review."""

        return tuple(skill.skill_id for skill in self.skills if skill.needs_review)

    @property
    def blocking_skill_ids(self) -> tuple[str, ...]:
        """Return skill ids blocking stronger claims."""

        return tuple(skill.skill_id for skill in self.skills if skill.blocks_claim)

    @property
    def transfer_demonstrated_skill_ids(self) -> tuple[str, ...]:
        """Return skill ids with demonstrated transfer."""

        return tuple(
            skill.skill_id for skill in self.skills if skill.transfer_demonstrated
        )

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound to this genome."""

        evidence_ids: list[str] = []
        for skill in self.skills:
            evidence_ids.extend(skill.evidence_ids)
        return _normalize_unique_text_tuple(evidence_ids, label="evidence_id")

    @property
    def blocks_claim(self) -> bool:
        """Return whether this genome blocks stronger skill claims."""

        return bool(self.blocking_skill_ids)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic skill-genome payload."""

        return {
            "authority_refs": list(self.authority_refs),
            "blocking_skill_ids": list(self.blocking_skill_ids),
            "constrained_skill_ids": list(self.constrained_skill_ids),
            "demonstrated_skill_ids": list(self.demonstrated_skill_ids),
            "doctrine_ids": list(self.doctrine_ids),
            "evidence_ids": list(self.evidence_ids),
            "genome_id": self.genome_id,
            "notes": list(self.notes),
            "review_skill_ids": list(self.review_skill_ids),
            "revoked_skill_ids": list(self.revoked_skill_ids),
            "schema_version": self.schema_version,
            "skill_fingerprints": [skill.fingerprint() for skill in self.skills],
            "skill_ids": list(self.skill_ids),
            "stale_skill_ids": list(self.stale_skill_ids),
            "transfer_demonstrated_skill_ids": list(
                self.transfer_demonstrated_skill_ids
            ),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this genome."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class SkillGenomeReport:
    """Review report for Wave 7 skill genome state."""

    report_id: str
    genome: SkillGenome
    decision: SkillGenomeDecision
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SEVEN_SKILL_GENOME_REPORT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate report and fail closed on overclaiming."""

        object.__setattr__(
            self,
            "report_id",
            _require_non_empty(self.report_id, "report_id"),
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
        if (
            self.decision is SkillGenomeDecision.READY_FOR_REVIEW
            and self.genome.blocks_claim
        ):
            raise ValueError("Review-ready skill genome cannot have blockers.")
        if (
            self.decision is SkillGenomeDecision.READY_FOR_REVIEW
            and not self.genome.evidence_ids
        ):
            raise ValueError("Review-ready skill genome requires evidence.")

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return report evidence ids."""

        return self.genome.evidence_ids

    @property
    def ready_for_review(self) -> bool:
        """Return whether this report is ready for review."""

        return (
            self.decision is SkillGenomeDecision.READY_FOR_REVIEW
            and not self.genome.blocks_claim
            and bool(self.evidence_ids)
        )

    @property
    def blocks_claim(self) -> bool:
        """Return whether this report blocks stronger skill claims."""

        return (
            self.decision is SkillGenomeDecision.BLOCKED
            or self.genome.blocks_claim
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic skill-genome-report payload."""

        return {
            "blocks_claim": self.blocks_claim,
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "genome_fingerprint": self.genome.fingerprint(),
            "notes": list(self.notes),
            "ready_for_review": self.ready_for_review,
            "report_id": self.report_id,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this report."""

        return _stable_sha256(self.canonical_payload())


def build_skill_genome(
    *,
    genome_id: str,
    skills: Iterable[SkillGene],
    doctrine_ids: Iterable[str],
    authority_refs: Iterable[str],
    notes: Iterable[str] = (),
) -> SkillGenome:
    """Build a deterministic Wave 7 skill genome."""

    return SkillGenome(
        genome_id=genome_id,
        skills=tuple(skills),
        doctrine_ids=tuple(doctrine_ids),
        authority_refs=tuple(authority_refs),
        notes=tuple(notes),
    )


def build_skill_genome_report(
    *,
    report_id: str,
    genome: SkillGenome,
    decision: SkillGenomeDecision,
    notes: Iterable[str] = (),
) -> SkillGenomeReport:
    """Build a deterministic Wave 7 skill genome report."""

    return SkillGenomeReport(
        report_id=report_id,
        genome=genome,
        decision=decision,
        notes=tuple(notes),
    )


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


def _ensure_unique(values: Iterable[str], *, label: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label}: {value}")
        seen.add(value)


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()
