"""Foundation state and evidence contracts for IX-CognitionKernel Wave 0.

Wave 0 does not implement the full cognition engines. It defines the state
contracts those engines must respect: claims need evidence, uncertainty cannot be
hidden, human authority is explicit, and action readiness is never granted by
model confidence alone.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from ix_cognition_kernel.doctrine import allows_agi_claim, current_wave


class EvidenceStatus(StrEnum):
    """Evidence state for a claim-supporting record."""

    ABSENT = "absent"
    PROPOSED = "proposed"
    PARTIAL = "partial"
    VERIFIED = "verified"
    CONTRADICTED = "contradicted"


class UncertaintyStatus(StrEnum):
    """Action-relevant uncertainty labels for claims and plans."""

    KNOWN = "known"
    UNKNOWN = "unknown"
    ASSUMED = "assumed"
    DISPUTED = "disputed"
    STALE = "stale"
    UNSAFE_TO_ACT = "unsafe-to-act"


class HumanAuthority(StrEnum):
    """Human authority state for a proposed action or handoff."""

    ABSENT = "absent"
    REQUIRED = "required"
    GRANTED = "granted"
    DENIED = "denied"


class ActionReadiness(StrEnum):
    """Readiness state before any action can leave the cognition layer."""

    BLOCKED = "blocked"
    NEEDS_EVIDENCE = "needs-evidence"
    NEEDS_HUMAN_AUTHORITY = "needs-human-authority"
    READY_FOR_HANDOFF = "ready-for-handoff"


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    """Evidence attached to one or more claims."""

    evidence_id: str
    summary: str
    status: EvidenceStatus
    sources: tuple[str, ...]
    supports_claim_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate that evidence records are identifiable and non-empty."""

        if not self.evidence_id.strip():
            raise ValueError("Evidence records require a non-empty evidence_id.")
        if not self.summary.strip():
            raise ValueError("Evidence records require a non-empty summary.")
        if self.status is EvidenceStatus.VERIFIED and not self.sources:
            raise ValueError("Verified evidence requires at least one source.")

    @property
    def is_verified(self) -> bool:
        """Return whether this evidence record is verified."""

        return self.status is EvidenceStatus.VERIFIED

    @property
    def is_contradictory(self) -> bool:
        """Return whether this evidence record contradicts a claim."""

        return self.status is EvidenceStatus.CONTRADICTED


@dataclass(frozen=True, slots=True)
class ClaimRecord:
    """A claim whose readiness depends on evidence and uncertainty."""

    claim_id: str
    statement: str
    confidence: float
    uncertainty: UncertaintyStatus
    evidence_ids: tuple[str, ...]
    contradicted_by: tuple[str, ...] = ()
    stale: bool = False

    def __post_init__(self) -> None:
        """Validate claim identity, statement, and confidence bounds."""

        if not self.claim_id.strip():
            raise ValueError("Claim records require a non-empty claim_id.")
        if not self.statement.strip():
            raise ValueError("Claim records require a non-empty statement.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Claim confidence must be between 0.0 and 1.0.")

    @property
    def has_blocking_uncertainty(self) -> bool:
        """Return whether the claim is blocked before evidence review."""

        return (
            self.uncertainty
            in {
                UncertaintyStatus.DISPUTED,
                UncertaintyStatus.STALE,
                UncertaintyStatus.UNSAFE_TO_ACT,
            }
            or self.stale
            or bool(self.contradicted_by)
        )


@dataclass(frozen=True, slots=True)
class ActionReadinessReport:
    """Result of assessing whether a claim can proceed toward handoff."""

    claim_id: str
    readiness: ActionReadiness
    reasons: tuple[str, ...]
    verified_evidence_ids: tuple[str, ...]
    authority: HumanAuthority

    @property
    def is_ready(self) -> bool:
        """Return whether the action is ready for governed handoff."""

        return self.readiness is ActionReadiness.READY_FOR_HANDOFF


@dataclass(frozen=True, slots=True)
class FoundationStateSnapshot:
    """Wave 0 snapshot of doctrine, claims, evidence, and readiness state."""

    project_name: str
    wave_number: int
    wave_label: str
    claims: tuple[ClaimRecord, ...]
    evidence: tuple[EvidenceRecord, ...]
    readiness_reports: tuple[ActionReadinessReport, ...]

    @property
    def permits_agi_claim(self) -> bool:
        """Return whether this foundation state permits an AGI claim."""

        return allows_agi_claim(self.wave_number, overwhelming_evidence=False)


def evidence_index(records: Iterable[EvidenceRecord]) -> dict[str, EvidenceRecord]:
    """Index evidence by id while rejecting duplicate evidence identifiers."""

    indexed: dict[str, EvidenceRecord] = {}
    for record in records:
        if record.evidence_id in indexed:
            raise ValueError(f"Duplicate evidence_id detected: {record.evidence_id}")
        indexed[record.evidence_id] = record
    return indexed


def verified_evidence_for_claim(
    claim: ClaimRecord,
    evidence_by_id: dict[str, EvidenceRecord],
) -> tuple[EvidenceRecord, ...]:
    """Return verified evidence records that support a claim."""

    verified: list[EvidenceRecord] = []
    for evidence_id in claim.evidence_ids:
        record = evidence_by_id.get(evidence_id)
        if record is None:
            continue
        if record.is_verified and claim.claim_id in record.supports_claim_ids:
            verified.append(record)
    return tuple(verified)


def assess_action_readiness(
    claim: ClaimRecord,
    evidence_by_id: dict[str, EvidenceRecord],
    authority: HumanAuthority,
) -> ActionReadinessReport:
    """Assess readiness for a claim to become a governed handoff candidate."""

    verified_records = verified_evidence_for_claim(claim, evidence_by_id)
    verified_ids = tuple(record.evidence_id for record in verified_records)

    if claim.has_blocking_uncertainty:
        return ActionReadinessReport(
            claim_id=claim.claim_id,
            readiness=ActionReadiness.BLOCKED,
            reasons=("Claim has blocking uncertainty, contradiction, or staleness.",),
            verified_evidence_ids=verified_ids,
            authority=authority,
        )

    if claim.uncertainty in {UncertaintyStatus.UNKNOWN, UncertaintyStatus.ASSUMED}:
        return ActionReadinessReport(
            claim_id=claim.claim_id,
            readiness=ActionReadiness.NEEDS_EVIDENCE,
            reasons=("Claim remains unknown or assumed and needs evidence.",),
            verified_evidence_ids=verified_ids,
            authority=authority,
        )

    if not verified_ids:
        return ActionReadinessReport(
            claim_id=claim.claim_id,
            readiness=ActionReadiness.NEEDS_EVIDENCE,
            reasons=("Claim has no verified supporting evidence.",),
            verified_evidence_ids=verified_ids,
            authority=authority,
        )

    if authority is not HumanAuthority.GRANTED:
        return ActionReadinessReport(
            claim_id=claim.claim_id,
            readiness=ActionReadiness.NEEDS_HUMAN_AUTHORITY,
            reasons=("Human authority is required before handoff.",),
            verified_evidence_ids=verified_ids,
            authority=authority,
        )

    return ActionReadinessReport(
        claim_id=claim.claim_id,
        readiness=ActionReadiness.READY_FOR_HANDOFF,
        reasons=("Verified evidence and human authority are present.",),
        verified_evidence_ids=verified_ids,
        authority=authority,
    )


def foundation_snapshot(
    claims: tuple[ClaimRecord, ...],
    evidence: tuple[EvidenceRecord, ...],
    *,
    authority: HumanAuthority,
) -> FoundationStateSnapshot:
    """Create a Wave 0 foundation snapshot with readiness reports."""

    wave = current_wave()
    indexed = evidence_index(evidence)
    reports = tuple(
        assess_action_readiness(claim, indexed, authority) for claim in claims
    )
    return FoundationStateSnapshot(
        project_name="IX-CognitionKernel",
        wave_number=wave.number,
        wave_label=wave.label,
        claims=claims,
        evidence=evidence,
        readiness_reports=reports,
    )
