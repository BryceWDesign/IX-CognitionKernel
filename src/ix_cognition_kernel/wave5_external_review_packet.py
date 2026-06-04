"""Wave 5 external review packet records.

Wave 5 should be reviewable by outside humans without pretending that internal
scorecards, dossiers, or readiness gates are independent validation. This module
packages the Wave 5 evidence into a reviewer-facing packet with review
instructions, challenge questions, dissent capture, and gap handling. A packet can
be ready for external review; it cannot declare Wave 6, AGI, certification,
production readiness, autonomous execution, or independent validation.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.wave5_contracts import (
    WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES,
    WaveFiveArtifactDecision,
    WaveFiveArtifactKind,
    WaveFiveArtifactRef,
    WaveFiveAuthorityState,
    WaveFiveCapabilityArea,
    WaveFiveClaimBoundary,
    WaveFiveSourceSystem,
    WaveFiveValidationStatus,
)

T = TypeVar("T")
E = TypeVar("E", bound=StrEnum)

WAVE_FIVE_REVIEW_SECTION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-review-packet-section-v1"
)
WAVE_FIVE_REVIEW_CHALLENGE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-review-challenge-v1"
)
WAVE_FIVE_REVIEW_DISPOSITION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-review-disposition-v1"
)
WAVE_FIVE_EXTERNAL_REVIEW_PACKET_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-external-review-packet-v1"
)


class WaveFiveReviewPacketSectionKind(StrEnum):
    """Sections required in a Wave 5 external review packet."""

    REVIEWER_INSTRUCTIONS = "reviewer-instructions"
    EVIDENCE_DOSSIER = "evidence-dossier"
    MATURITY_SCORECARD = "maturity-scorecard"
    WAVE_SIX_READINESS_GATE = "wave-six-readiness-gate"
    REPEATABILITY_LEDGER = "repeatability-ledger"
    SAFE_REFUSAL_PROOF = "safe-refusal-proof"
    HUMAN_AUTHORITY_PROOF = "human-authority-proof"
    MEMORY_INTEGRITY_PROOF = "memory-integrity-proof"
    BENCHMARK_GAMING_AUDIT = "benchmark-gaming-audit"
    BLACKFOX_WORLDTWIN_BRIDGES = "blackfox-worldtwin-bridges"
    CLAIM_BOUNDARY_NOTICE = "claim-boundary-notice"
    DISSENT_AND_GAP_LOG = "dissent-and-gap-log"


class WaveFiveReviewPacketSectionStatus(StrEnum):
    """Status of one external review packet section."""

    INCLUDED = "included"
    INCLUDED_WITH_LIMITS = "included-with-limits"
    NEEDS_EXTERNAL_EVIDENCE = "needs-external-evidence"
    DISPUTED = "disputed"
    BLOCKED = "blocked"
    MISSING = "missing"


class WaveFiveReviewChallengeKind(StrEnum):
    """Reviewer challenge classes required for Wave 5 external review."""

    REPRODUCE_EVIDENCE = "reproduce-evidence"
    ATTACK_CLAIM_BOUNDARIES = "attack-claim-boundaries"
    CHECK_AUTHORITY_PRESERVATION = "check-authority-preservation"
    CHECK_SAFE_REFUSAL = "check-safe-refusal"
    CHECK_MEMORY_INTEGRITY = "check-memory-integrity"
    CHECK_BENCHMARK_CONTAMINATION = "check-benchmark-contamination"
    CHECK_TRANSFER_GENERALITY = "check-transfer-generality"
    CHECK_SCENARIO_FALSIFIABILITY = "check-scenario-falsifiability"
    RECORD_DISSENT = "record-dissent"
    BLOCK_WAVE_SIX_IF_NEEDED = "block-wave-six-if-needed"


class WaveFiveReviewChallengeStatus(StrEnum):
    """Status of one reviewer challenge."""

    READY = "ready"
    READY_WITH_LIMITS = "ready-with-limits"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


class WaveFiveReviewDispositionKind(StrEnum):
    """Disposition of a review packet after reviewer handling."""

    PACKET_READY_FOR_EXTERNAL_REVIEW = "packet-ready-for-external-review"
    EXTERNAL_REVIEW_IN_PROGRESS = "external-review-in-progress"
    EXTERNALLY_REVIEWED_WITH_BOUNDARIES = "externally-reviewed-with-boundaries"
    ACCEPTED_AS_LIMITED_EVIDENCE = "accepted-as-limited-evidence"
    DISPUTED_BY_REVIEWER = "disputed-by-reviewer"
    BLOCKED_BEFORE_WAVE_SIX = "blocked-before-wave-six"


class WaveFiveExternalReviewPacketState(StrEnum):
    """State of the Wave 5 external review packet."""

    INTERNAL_PACKET_READY = "internal-packet-ready"
    READY_FOR_EXTERNAL_REVIEW = "ready-for-external-review"
    UNDER_EXTERNAL_REVIEW = "under-external-review"
    EXTERNALLY_REVIEWED_WITH_BOUNDARIES = "externally-reviewed-with-boundaries"
    BLOCKED_BY_REVIEW_GAP = "blocked-by-review-gap"


SAFE_REVIEW_SECTION_STATUSES: tuple[WaveFiveReviewPacketSectionStatus, ...] = (
    WaveFiveReviewPacketSectionStatus.INCLUDED,
    WaveFiveReviewPacketSectionStatus.INCLUDED_WITH_LIMITS,
)

BLOCKING_REVIEW_SECTION_STATUSES: tuple[WaveFiveReviewPacketSectionStatus, ...] = (
    WaveFiveReviewPacketSectionStatus.NEEDS_EXTERNAL_EVIDENCE,
    WaveFiveReviewPacketSectionStatus.DISPUTED,
    WaveFiveReviewPacketSectionStatus.BLOCKED,
    WaveFiveReviewPacketSectionStatus.MISSING,
)

REQUIRED_REVIEW_PACKET_SECTIONS: tuple[WaveFiveReviewPacketSectionKind, ...] = (
    WaveFiveReviewPacketSectionKind.REVIEWER_INSTRUCTIONS,
    WaveFiveReviewPacketSectionKind.EVIDENCE_DOSSIER,
    WaveFiveReviewPacketSectionKind.MATURITY_SCORECARD,
    WaveFiveReviewPacketSectionKind.WAVE_SIX_READINESS_GATE,
    WaveFiveReviewPacketSectionKind.REPEATABILITY_LEDGER,
    WaveFiveReviewPacketSectionKind.SAFE_REFUSAL_PROOF,
    WaveFiveReviewPacketSectionKind.HUMAN_AUTHORITY_PROOF,
    WaveFiveReviewPacketSectionKind.MEMORY_INTEGRITY_PROOF,
    WaveFiveReviewPacketSectionKind.BENCHMARK_GAMING_AUDIT,
    WaveFiveReviewPacketSectionKind.BLACKFOX_WORLDTWIN_BRIDGES,
    WaveFiveReviewPacketSectionKind.CLAIM_BOUNDARY_NOTICE,
    WaveFiveReviewPacketSectionKind.DISSENT_AND_GAP_LOG,
)

REQUIRED_REVIEW_CHALLENGES: tuple[WaveFiveReviewChallengeKind, ...] = (
    WaveFiveReviewChallengeKind.REPRODUCE_EVIDENCE,
    WaveFiveReviewChallengeKind.ATTACK_CLAIM_BOUNDARIES,
    WaveFiveReviewChallengeKind.CHECK_AUTHORITY_PRESERVATION,
    WaveFiveReviewChallengeKind.CHECK_SAFE_REFUSAL,
    WaveFiveReviewChallengeKind.CHECK_MEMORY_INTEGRITY,
    WaveFiveReviewChallengeKind.CHECK_BENCHMARK_CONTAMINATION,
    WaveFiveReviewChallengeKind.CHECK_TRANSFER_GENERALITY,
    WaveFiveReviewChallengeKind.CHECK_SCENARIO_FALSIFIABILITY,
    WaveFiveReviewChallengeKind.RECORD_DISSENT,
    WaveFiveReviewChallengeKind.BLOCK_WAVE_SIX_IF_NEEDED,
)

EXTERNAL_REVIEW_PACKET_SOURCE_SYSTEMS: tuple[WaveFiveSourceSystem, ...] = (
    WaveFiveSourceSystem.EXTERNAL_REVIEW,
    WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
    WaveFiveSourceSystem.HUMAN_REVIEW,
)


@dataclass(frozen=True, slots=True)
class WaveFiveReviewPacketSection:
    """One evidence section packaged for external review."""

    section_id: str
    section_kind: WaveFiveReviewPacketSectionKind
    status: WaveFiveReviewPacketSectionStatus
    artifact_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    reviewer_instruction: str
    limitations: tuple[str, ...] = ()
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    schema_version: str = WAVE_FIVE_REVIEW_SECTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate section evidence, reviewer instruction, and boundaries."""

        object.__setattr__(self, "section_id", _text(self.section_id, "section_id"))
        object.__setattr__(
            self, "artifact_ids", _unique_text(self.artifact_ids, label="artifact_id")
        )
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        object.__setattr__(
            self,
            "reviewer_instruction",
            _text(self.reviewer_instruction, "reviewer_instruction"),
        )
        object.__setattr__(
            self, "limitations", _unique_text(self.limitations, label="limitation")
        )
        object.__setattr__(
            self,
            "claim_boundaries",
            _unique_enum(self.claim_boundaries, label="claim boundary"),
        )
        if not self.artifact_ids:
            raise ValueError("Review packet sections require artifact ids.")
        if not self.evidence_ids:
            raise ValueError("Review packet sections require evidence ids.")
        if self.status is WaveFiveReviewPacketSectionStatus.INCLUDED_WITH_LIMITS:
            if not self.limitations:
                raise ValueError("Limited review packet sections require limits.")
        missing = tuple(
            boundary
            for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
            if boundary not in self.claim_boundaries
        )
        if missing:
            raise ValueError(
                "Review packet sections must preserve claim boundary: "
                f"{missing[0].value}"
            )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def section_key(self) -> str:
        """Return deterministic section key."""

        return self.section_id

    @property
    def blocks_packet_readiness(self) -> bool:
        """Return whether this section blocks external review."""

        return self.status in BLOCKING_REVIEW_SECTION_STATUSES

    @property
    def reviewable_with_boundaries(self) -> bool:
        """Return whether this section is reviewable without promotion."""

        return self.status in SAFE_REVIEW_SECTION_STATUSES and bool(self.evidence_ids)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "artifact_ids": list(self.artifact_ids),
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "evidence_ids": list(self.evidence_ids),
            "limitations": list(self.limitations),
            "reviewable_with_boundaries": self.reviewable_with_boundaries,
            "reviewer_instruction": self.reviewer_instruction,
            "schema_version": self.schema_version,
            "section_id": self.section_id,
            "section_kind": self.section_kind.value,
            "status": self.status.value,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveReviewerChallenge:
    """One explicit challenge reviewers must apply to the packet."""

    challenge_id: str
    challenge_kind: WaveFiveReviewChallengeKind
    status: WaveFiveReviewChallengeStatus
    prompt: str
    expected_evidence_ids: tuple[str, ...]
    blocking: bool = True
    schema_version: str = WAVE_FIVE_REVIEW_CHALLENGE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate reviewer challenge evidence expectations."""

        object.__setattr__(
            self, "challenge_id", _text(self.challenge_id, "challenge_id")
        )
        object.__setattr__(self, "prompt", _text(self.prompt, "prompt"))
        object.__setattr__(
            self,
            "expected_evidence_ids",
            _unique_text(
                self.expected_evidence_ids,
                label="expected evidence_id",
            ),
        )
        if not self.expected_evidence_ids:
            raise ValueError("Reviewer challenges require expected evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def challenge_key(self) -> str:
        """Return deterministic challenge key."""

        return self.challenge_id

    @property
    def ready_for_review(self) -> bool:
        """Return whether this challenge can be issued to reviewers."""

        return self.status in {
            WaveFiveReviewChallengeStatus.READY,
            WaveFiveReviewChallengeStatus.READY_WITH_LIMITS,
        }

    @property
    def blocks_packet_readiness(self) -> bool:
        """Return whether this challenge blocks packet readiness."""

        return self.blocking and not self.ready_for_review

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "blocking": self.blocking,
            "challenge_id": self.challenge_id,
            "challenge_kind": self.challenge_kind.value,
            "expected_evidence_ids": list(self.expected_evidence_ids),
            "prompt": self.prompt,
            "schema_version": self.schema_version,
            "status": self.status.value,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveReviewDisposition:
    """Reviewer-facing disposition that preserves dissent and blockers."""

    disposition_id: str
    disposition_kind: WaveFiveReviewDispositionKind
    reviewer_ids: tuple[str, ...]
    summary: str
    evidence_ids: tuple[str, ...]
    dissent_ids: tuple[str, ...] = ()
    blocker_ids: tuple[str, ...] = ()
    schema_version: str = WAVE_FIVE_REVIEW_DISPOSITION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate disposition reviewer evidence and blocker visibility."""

        object.__setattr__(
            self,
            "disposition_id",
            _text(self.disposition_id, "disposition_id"),
        )
        object.__setattr__(
            self, "reviewer_ids", _unique_text(self.reviewer_ids, label="reviewer_id")
        )
        object.__setattr__(self, "summary", _text(self.summary, "summary"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        object.__setattr__(
            self, "dissent_ids", _unique_text(self.dissent_ids, label="dissent_id")
        )
        object.__setattr__(
            self, "blocker_ids", _unique_text(self.blocker_ids, label="blocker_id")
        )
        if self.disposition_kind in {
            WaveFiveReviewDispositionKind.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
            WaveFiveReviewDispositionKind.ACCEPTED_AS_LIMITED_EVIDENCE,
            WaveFiveReviewDispositionKind.DISPUTED_BY_REVIEWER,
            WaveFiveReviewDispositionKind.BLOCKED_BEFORE_WAVE_SIX,
        }:
            if not self.reviewer_ids:
                raise ValueError("External review dispositions require reviewers.")
        if not self.evidence_ids:
            raise ValueError("Review dispositions require evidence ids.")
        if self.disposition_kind is WaveFiveReviewDispositionKind.DISPUTED_BY_REVIEWER:
            if not self.dissent_ids:
                raise ValueError("Disputed review dispositions require dissent ids.")
        if (
            self.disposition_kind
            is WaveFiveReviewDispositionKind.BLOCKED_BEFORE_WAVE_SIX
        ):
            if not self.blocker_ids:
                raise ValueError("Blocked review dispositions require blockers.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def disposition_key(self) -> str:
        """Return deterministic disposition key."""

        return self.disposition_id

    @property
    def blocks_packet_readiness(self) -> bool:
        """Return whether this disposition blocks Wave 6 readiness."""

        return self.disposition_kind in {
            WaveFiveReviewDispositionKind.DISPUTED_BY_REVIEWER,
            WaveFiveReviewDispositionKind.BLOCKED_BEFORE_WAVE_SIX,
        }

    @property
    def externally_reviewed_with_boundaries(self) -> bool:
        """Return whether reviewers accepted the packet with boundaries."""

        return (
            self.disposition_kind
            is WaveFiveReviewDispositionKind.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "blocker_ids": list(self.blocker_ids),
            "disposition_id": self.disposition_id,
            "disposition_kind": self.disposition_kind.value,
            "dissent_ids": list(self.dissent_ids),
            "evidence_ids": list(self.evidence_ids),
            "reviewer_ids": list(self.reviewer_ids),
            "schema_version": self.schema_version,
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveExternalReviewPacket:
    """External review packet for Wave 5 evidence and Wave 6 readiness."""

    packet_id: str
    title: str
    source_system: WaveFiveSourceSystem
    packet_state: WaveFiveExternalReviewPacketState
    sections: tuple[WaveFiveReviewPacketSection, ...]
    challenges: tuple[WaveFiveReviewerChallenge, ...]
    dispositions: tuple[WaveFiveReviewDisposition, ...]
    protocol_ids: tuple[str, ...]
    reviewer_ids: tuple[str, ...] = ()
    attempted_wave_six_promotion: bool = False
    claims_agi: bool = False
    grants_execution_authority: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    claims_independent_validation: bool = False
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_FIVE_EXTERNAL_REVIEW_PACKET_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate packet completeness and anti-overclaim gates."""

        object.__setattr__(self, "packet_id", _text(self.packet_id, "packet_id"))
        object.__setattr__(self, "title", _text(self.title, "title"))
        if self.attempted_wave_six_promotion:
            raise ValueError("External review packets cannot promote to Wave 6.")
        if self.claims_agi:
            raise ValueError("External review packets cannot claim AGI.")
        if self.grants_execution_authority:
            raise ValueError("External review packets cannot grant execution.")
        if self.claims_production_ready:
            raise ValueError("External review packets cannot claim production.")
        if self.claims_certified:
            raise ValueError("External review packets cannot claim certification.")
        if self.claims_independent_validation:
            raise ValueError(
                "External review packets cannot self-claim independent validation."
            )
        sections = tuple(sorted(self.sections, key=lambda item: item.section_key))
        challenges = tuple(
            sorted(self.challenges, key=lambda item: item.challenge_key)
        )
        dispositions = tuple(
            sorted(self.dispositions, key=lambda item: item.disposition_key)
        )
        if not sections:
            raise ValueError("External review packets require sections.")
        if not challenges:
            raise ValueError("External review packets require challenges.")
        if not dispositions:
            raise ValueError("External review packets require dispositions.")
        _unique_values((item.section_id for item in sections), label="section_id")
        _unique_values((item.section_kind for item in sections), label="section kind")
        _unique_values(
            (item.challenge_id for item in challenges),
            label="challenge_id",
        )
        _unique_values(
            (item.challenge_kind for item in challenges),
            label="challenge kind",
        )
        _unique_values(
            (item.disposition_id for item in dispositions),
            label="disposition_id",
        )
        object.__setattr__(self, "sections", sections)
        object.__setattr__(self, "challenges", challenges)
        object.__setattr__(self, "dispositions", dispositions)
        object.__setattr__(
            self, "protocol_ids", _unique_text(self.protocol_ids, label="protocol_id")
        )
        if not self.protocol_ids:
            raise ValueError("External review packets require protocol ids.")
        object.__setattr__(
            self, "reviewer_ids", _unique_text(self.reviewer_ids, label="reviewer_id")
        )
        object.__setattr__(
            self,
            "claim_boundaries",
            _unique_enum(self.claim_boundaries, label="claim boundary"),
        )
        missing_boundaries = tuple(
            boundary
            for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
            if boundary not in self.claim_boundaries
        )
        if missing_boundaries:
            raise ValueError(
                "External review packets must preserve claim boundary: "
                f"{missing_boundaries[0].value}"
            )
        object.__setattr__(self, "notes", _unique_text(self.notes, label="note"))
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.externally_reviewed_with_boundaries:
            if self.source_system not in EXTERNAL_REVIEW_PACKET_SOURCE_SYSTEMS:
                raise ValueError(
                    "Externally reviewed packets require external source."
                )
            if not self.reviewer_ids:
                raise ValueError(
                    "Externally reviewed packets require reviewer ids."
                )
            if self.blocks_packet_readiness:
                raise ValueError(
                    "Externally reviewed packets cannot contain blockers."
                )

    @property
    def covered_section_kinds(self) -> tuple[WaveFiveReviewPacketSectionKind, ...]:
        """Return packet section kinds represented in this packet."""

        return tuple(section.section_kind for section in self.sections)

    @property
    def missing_required_section_kinds(
        self,
    ) -> tuple[WaveFiveReviewPacketSectionKind, ...]:
        """Return required packet sections absent from this packet."""

        covered = set(self.covered_section_kinds)
        return tuple(
            kind for kind in REQUIRED_REVIEW_PACKET_SECTIONS if kind not in covered
        )

    @property
    def covered_challenge_kinds(self) -> tuple[WaveFiveReviewChallengeKind, ...]:
        """Return challenge kinds represented in this packet."""

        return tuple(challenge.challenge_kind for challenge in self.challenges)

    @property
    def missing_required_challenge_kinds(
        self,
    ) -> tuple[WaveFiveReviewChallengeKind, ...]:
        """Return required reviewer challenges absent from this packet."""

        covered = set(self.covered_challenge_kinds)
        return tuple(kind for kind in REQUIRED_REVIEW_CHALLENGES if kind not in covered)

    @property
    def blocking_section_ids(self) -> tuple[str, ...]:
        """Return packet sections that block review readiness."""

        return tuple(
            section.section_id
            for section in self.sections
            if section.blocks_packet_readiness
        )

    @property
    def blocking_challenge_ids(self) -> tuple[str, ...]:
        """Return reviewer challenges that block packet readiness."""

        return tuple(
            challenge.challenge_id
            for challenge in self.challenges
            if challenge.blocks_packet_readiness
        )

    @property
    def blocking_disposition_ids(self) -> tuple[str, ...]:
        """Return review dispositions that block readiness."""

        return tuple(
            disposition.disposition_id
            for disposition in self.dispositions
            if disposition.blocks_packet_readiness
        )

    @property
    def has_required_section_coverage(self) -> bool:
        """Return whether every locked section is represented."""

        return not self.missing_required_section_kinds

    @property
    def has_required_challenge_coverage(self) -> bool:
        """Return whether every locked challenge is represented."""

        return not self.missing_required_challenge_kinds

    @property
    def makes_no_forbidden_claims(self) -> bool:
        """Return whether packet avoids forbidden Wave 6 claims."""

        return not any(
            (
                self.attempted_wave_six_promotion,
                self.claims_agi,
                self.grants_execution_authority,
                self.claims_production_ready,
                self.claims_certified,
                self.claims_independent_validation,
            )
        )

    @property
    def blocks_packet_readiness(self) -> bool:
        """Return whether any packet condition blocks external review."""

        return bool(
            self.missing_required_section_kinds
            or self.missing_required_challenge_kinds
            or self.blocking_section_ids
            or self.blocking_challenge_ids
            or self.blocking_disposition_ids
            or not self.makes_no_forbidden_claims
        )

    @property
    def ready_for_external_review(self) -> bool:
        """Return whether packet can enter external review."""

        return (
            self.packet_state
            in {
                WaveFiveExternalReviewPacketState.INTERNAL_PACKET_READY,
                WaveFiveExternalReviewPacketState.READY_FOR_EXTERNAL_REVIEW,
                WaveFiveExternalReviewPacketState.UNDER_EXTERNAL_REVIEW,
            }
            and self.has_required_section_coverage
            and self.has_required_challenge_coverage
            and not self.blocking_section_ids
            and not self.blocking_challenge_ids
            and not self.blocking_disposition_ids
            and self.makes_no_forbidden_claims
        )

    @property
    def externally_reviewed_with_boundaries(self) -> bool:
        """Return whether external reviewers accepted boundaries."""

        return (
            self.packet_state
            is WaveFiveExternalReviewPacketState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound into this packet."""

        evidence_ids: list[str] = []
        seen: set[str] = set()
        for evidence_id in self._iter_evidence_ids():
            if evidence_id not in seen:
                evidence_ids.append(evidence_id)
                seen.add(evidence_id)
        return tuple(evidence_ids)

    def to_artifact_ref(self) -> WaveFiveArtifactRef:
        """Return this packet as a Wave 5 traceability artifact."""

        decision = WaveFiveArtifactDecision.NEEDS_EXTERNAL_EVIDENCE
        status = WaveFiveValidationStatus.MISSING_EXTERNAL_EVIDENCE
        authority = WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
        if self.externally_reviewed_with_boundaries:
            decision = WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
            status = WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
        elif self.ready_for_external_review:
            decision = WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
            status = WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
        elif self.blocks_packet_readiness:
            decision = WaveFiveArtifactDecision.BLOCKED
            status = WaveFiveValidationStatus.REJECTED
            authority = WaveFiveAuthorityState.BLOCKED
        return WaveFiveArtifactRef(
            artifact_id=self.packet_id,
            kind=WaveFiveArtifactKind.ECOSYSTEM_TRACEABILITY_MAP,
            capability_area=WaveFiveCapabilityArea.ECOSYSTEM_TRACEABILITY,
            source_system=self.source_system,
            summary=self.title,
            produced_by_engine_id="wave5-external-review-packet-engine",
            produced_by_agent_role_id="external-review-packet-builder",
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=authority,
            validation_status=status,
            claim_boundaries=self.claim_boundaries,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "attempted_wave_six_promotion": self.attempted_wave_six_promotion,
            "challenges": [item.canonical_payload() for item in self.challenges],
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_independent_validation": self.claims_independent_validation,
            "claims_production_ready": self.claims_production_ready,
            "dispositions": [item.canonical_payload() for item in self.dispositions],
            "grants_execution_authority": self.grants_execution_authority,
            "notes": list(self.notes),
            "packet_id": self.packet_id,
            "packet_state": self.packet_state.value,
            "protocol_ids": list(self.protocol_ids),
            "reviewer_ids": list(self.reviewer_ids),
            "schema_version": self.schema_version,
            "sections": [item.canonical_payload() for item in self.sections],
            "source_system": self.source_system.value,
            "title": self.title,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this packet."""

        return _stable_sha256(self.canonical_payload())

    def _iter_evidence_ids(self) -> Iterable[str]:
        """Yield evidence ids in deterministic packet traversal order."""

        for section in self.sections:
            yield from section.evidence_ids
        for challenge in self.challenges:
            yield from challenge.expected_evidence_ids
        for disposition in self.dispositions:
            yield from disposition.evidence_ids


def required_review_packet_sections() -> tuple[WaveFiveReviewPacketSectionKind, ...]:
    """Return locked sections required in the external review packet."""

    return REQUIRED_REVIEW_PACKET_SECTIONS


def required_reviewer_challenges() -> tuple[WaveFiveReviewChallengeKind, ...]:
    """Return locked reviewer challenges required for Wave 5 packet review."""

    return REQUIRED_REVIEW_CHALLENGES


def safe_review_section_statuses() -> tuple[WaveFiveReviewPacketSectionStatus, ...]:
    """Return packet section statuses that do not block review."""

    return SAFE_REVIEW_SECTION_STATUSES


def blocking_review_section_statuses() -> tuple[
    WaveFiveReviewPacketSectionStatus, ...
]:
    """Return packet section statuses that block review."""

    return BLOCKING_REVIEW_SECTION_STATUSES


def external_review_packet_source_systems() -> tuple[WaveFiveSourceSystem, ...]:
    """Return source systems allowed to assert external packet review."""

    return EXTERNAL_REVIEW_PACKET_SOURCE_SYSTEMS


def _text(value: str, label: str) -> str:
    """Return stripped text or raise when empty."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _unique_text(values: Iterable[str], *, label: str) -> tuple[str, ...]:
    """Normalize text values while rejecting blanks and duplicates."""

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = _text(value, label)
        if item in seen:
            raise ValueError(f"Duplicate {label} detected: {item}")
        normalized.append(item)
        seen.add(item)
    return tuple(normalized)


def _unique_enum(values: Iterable[E], *, label: str) -> tuple[E, ...]:
    """Return enum values while rejecting duplicates."""

    normalized: list[E] = []
    seen: set[E] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value.value}")
        normalized.append(value)
        seen.add(value)
    return tuple(normalized)


def _unique_values(values: Iterable[T], *, label: str) -> set[T]:
    """Return unique values while rejecting duplicates."""

    seen: set[T] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value}")
        seen.add(value)
    return seen


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()
