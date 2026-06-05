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
WAVE_FIVE_REVIEW_QUESTION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-review-question-v1"
)
WAVE_FIVE_REVIEW_RESPONSE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-review-response-v1"
)
WAVE_FIVE_REVIEW_PACKET_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-external-review-packet-v1"
)


class WaveFiveReviewPacketSectionKind(StrEnum):
    """Reviewer-facing sections required in the external packet."""

    EXECUTIVE_BOUNDARY = "executive-boundary"
    CLAIM_LIMITS = "claim-limits"
    EVIDENCE_INDEX = "evidence-index"
    VALIDATION_PROTOCOLS = "validation-protocols"
    REPRODUCIBILITY = "reproducibility"
    ADVERSARIAL_SAFETY = "adversarial-safety"
    LONG_HORIZON = "long-horizon"
    CROSS_DOMAIN_TRANSFER = "cross-domain-transfer"
    HUMAN_AUTHORITY = "human-authority"
    SAFE_REFUSAL = "safe-refusal"
    MEMORY_INTEGRITY = "memory-integrity"
    BENCHMARK_GAMING = "benchmark-gaming"
    WAVE_SIX_READINESS = "wave-six-readiness"
    DISSENT_AND_GAPS = "dissent-and-gaps"


class WaveFiveReviewQuestionKind(StrEnum):
    """Challenge questions reviewers must be able to answer or dispute."""

    SUFFICIENCY = "sufficiency"
    FALSIFIABILITY = "falsifiability"
    REPRODUCIBILITY = "reproducibility"
    SAFETY = "safety"
    AUTHORITY = "authority"
    OVERCLAIM = "overclaim"
    WAVE_SIX_GAP = "wave-six-gap"


class WaveFiveReviewResponseDisposition(StrEnum):
    """Disposition of a reviewer response."""

    ACCEPTED_WITH_BOUNDARIES = "accepted-with-boundaries"
    ACCEPTED_WITH_LIMITATIONS = "accepted-with-limitations"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    DISPUTED = "disputed"
    REJECTED = "rejected"


class WaveFiveReviewPacketState(StrEnum):
    """Review state of a Wave 5 external review packet."""

    INTERNAL_PACKET_READY = "internal-packet-ready"
    READY_FOR_EXTERNAL_REVIEW = "ready-for-external-review"
    UNDER_EXTERNAL_REVIEW = "under-external-review"
    EXTERNALLY_REVIEWED_WITH_BOUNDARIES = "externally-reviewed-with-boundaries"
    BLOCKED_BY_REVIEW_GAP = "blocked-by-review-gap"


class WaveFiveReviewGapSeverity(StrEnum):
    """Severity for visible packet gaps."""

    INFORMATIONAL = "informational"
    LIMITATION = "limitation"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKING = "blocking"


REQUIRED_REVIEW_PACKET_SECTION_KINDS: tuple[WaveFiveReviewPacketSectionKind, ...] = (
    WaveFiveReviewPacketSectionKind.EXECUTIVE_BOUNDARY,
    WaveFiveReviewPacketSectionKind.CLAIM_LIMITS,
    WaveFiveReviewPacketSectionKind.EVIDENCE_INDEX,
    WaveFiveReviewPacketSectionKind.VALIDATION_PROTOCOLS,
    WaveFiveReviewPacketSectionKind.REPRODUCIBILITY,
    WaveFiveReviewPacketSectionKind.ADVERSARIAL_SAFETY,
    WaveFiveReviewPacketSectionKind.LONG_HORIZON,
    WaveFiveReviewPacketSectionKind.CROSS_DOMAIN_TRANSFER,
    WaveFiveReviewPacketSectionKind.HUMAN_AUTHORITY,
    WaveFiveReviewPacketSectionKind.SAFE_REFUSAL,
    WaveFiveReviewPacketSectionKind.MEMORY_INTEGRITY,
    WaveFiveReviewPacketSectionKind.BENCHMARK_GAMING,
    WaveFiveReviewPacketSectionKind.WAVE_SIX_READINESS,
    WaveFiveReviewPacketSectionKind.DISSENT_AND_GAPS,
)

REQUIRED_REVIEW_QUESTION_KINDS: tuple[WaveFiveReviewQuestionKind, ...] = (
    WaveFiveReviewQuestionKind.SUFFICIENCY,
    WaveFiveReviewQuestionKind.FALSIFIABILITY,
    WaveFiveReviewQuestionKind.REPRODUCIBILITY,
    WaveFiveReviewQuestionKind.SAFETY,
    WaveFiveReviewQuestionKind.AUTHORITY,
    WaveFiveReviewQuestionKind.OVERCLAIM,
    WaveFiveReviewQuestionKind.WAVE_SIX_GAP,
)

SAFE_REVIEW_RESPONSE_DISPOSITIONS: tuple[WaveFiveReviewResponseDisposition, ...] = (
    WaveFiveReviewResponseDisposition.ACCEPTED_WITH_BOUNDARIES,
    WaveFiveReviewResponseDisposition.ACCEPTED_WITH_LIMITATIONS,
)

BLOCKING_REVIEW_RESPONSE_DISPOSITIONS: tuple[WaveFiveReviewResponseDisposition, ...] = (
    WaveFiveReviewResponseDisposition.NEEDS_MORE_EVIDENCE,
    WaveFiveReviewResponseDisposition.DISPUTED,
    WaveFiveReviewResponseDisposition.REJECTED,
)

EXTERNAL_REVIEW_PACKET_SOURCE_SYSTEMS: tuple[WaveFiveSourceSystem, ...] = (
    WaveFiveSourceSystem.EXTERNAL_REVIEW,
    WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
    WaveFiveSourceSystem.HUMAN_REVIEW,
)


@dataclass(frozen=True, slots=True)
class WaveFiveReviewPacketSection:
    """One reviewer-facing section in an external review packet."""

    section_id: str
    section_kind: WaveFiveReviewPacketSectionKind
    title: str
    summary: str
    artifact_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    limitations: tuple[str, ...] = ()
    required_reviewer_actions: tuple[str, ...] = ()
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    schema_version: str = WAVE_FIVE_REVIEW_SECTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate review-packet section references and boundaries."""

        object.__setattr__(self, "section_id", _text(self.section_id, "section_id"))
        object.__setattr__(self, "title", _text(self.title, "title"))
        object.__setattr__(self, "summary", _text(self.summary, "summary"))
        object.__setattr__(
            self, "artifact_ids", _unique_text(self.artifact_ids, label="artifact_id")
        )
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        object.__setattr__(
            self, "limitations", _unique_text(self.limitations, label="limitation")
        )
        object.__setattr__(
            self,
            "required_reviewer_actions",
            _unique_text(
                self.required_reviewer_actions,
                label="required reviewer action",
            ),
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
        if not self.required_reviewer_actions:
            raise ValueError("Review packet sections require reviewer actions.")
        missing_boundaries = tuple(
            boundary
            for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
            if boundary not in self.claim_boundaries
        )
        if missing_boundaries:
            raise ValueError(
                "Review packet sections must preserve claim boundary: "
                f"{missing_boundaries[0].value}"
            )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def section_key(self) -> str:
        """Return deterministic section key."""

        return self.section_id

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "artifact_ids": list(self.artifact_ids),
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "evidence_ids": list(self.evidence_ids),
            "limitations": list(self.limitations),
            "required_reviewer_actions": list(self.required_reviewer_actions),
            "schema_version": self.schema_version,
            "section_id": self.section_id,
            "section_kind": self.section_kind.value,
            "summary": self.summary,
            "title": self.title,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveReviewQuestion:
    """Challenge question that external reviewers should evaluate."""

    question_id: str
    question_kind: WaveFiveReviewQuestionKind
    question: str
    expected_evidence_ids: tuple[str, ...]
    blocks_if_unanswered: bool = True
    schema_version: str = WAVE_FIVE_REVIEW_QUESTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate challenge-question identity and evidence references."""

        object.__setattr__(self, "question_id", _text(self.question_id, "question_id"))
        object.__setattr__(self, "question", _text(self.question, "question"))
        object.__setattr__(
            self,
            "expected_evidence_ids",
            _unique_text(
                self.expected_evidence_ids,
                label="expected evidence_id",
            ),
        )
        if not self.expected_evidence_ids:
            raise ValueError("Review questions require expected evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def question_key(self) -> str:
        """Return deterministic question key."""

        return self.question_id

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "blocks_if_unanswered": self.blocks_if_unanswered,
            "expected_evidence_ids": list(self.expected_evidence_ids),
            "question": self.question,
            "question_id": self.question_id,
            "question_kind": self.question_kind.value,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveReviewResponse:
    """External or human response to a review-packet challenge question."""

    response_id: str
    question_id: str
    reviewer_id: str
    disposition: WaveFiveReviewResponseDisposition
    rationale: str
    evidence_ids: tuple[str, ...]
    reviewer_source_system: WaveFiveSourceSystem
    limitations: tuple[str, ...] = ()
    schema_version: str = WAVE_FIVE_REVIEW_RESPONSE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate review response identity and reviewer provenance."""

        object.__setattr__(self, "response_id", _text(self.response_id, "response_id"))
        object.__setattr__(self, "question_id", _text(self.question_id, "question_id"))
        object.__setattr__(self, "reviewer_id", _text(self.reviewer_id, "reviewer_id"))
        object.__setattr__(self, "rationale", _text(self.rationale, "rationale"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        object.__setattr__(
            self, "limitations", _unique_text(self.limitations, label="limitation")
        )
        if not self.evidence_ids:
            raise ValueError("Review responses require evidence ids.")
        if (
            self.disposition
            is WaveFiveReviewResponseDisposition.ACCEPTED_WITH_LIMITATIONS
            and not self.limitations
        ):
            raise ValueError("Limited review acceptance requires limitations.")
        if self.reviewer_source_system not in EXTERNAL_REVIEW_PACKET_SOURCE_SYSTEMS:
            raise ValueError("Review responses require external or human review source.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def response_key(self) -> str:
        """Return deterministic response key."""

        return self.response_id

    @property
    def blocks_packet_readiness(self) -> bool:
        """Return whether this response blocks external review closure."""

        return self.disposition in BLOCKING_REVIEW_RESPONSE_DISPOSITIONS

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "disposition": self.disposition.value,
            "evidence_ids": list(self.evidence_ids),
            "limitations": list(self.limitations),
            "question_id": self.question_id,
            "rationale": self.rationale,
            "response_id": self.response_id,
            "reviewer_id": self.reviewer_id,
            "reviewer_source_system": self.reviewer_source_system.value,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveExternalReviewPacket:
    """Reviewer-facing Wave 5 evidence packet."""

    packet_id: str
    title: str
    source_system: WaveFiveSourceSystem
    packet_state: WaveFiveReviewPacketState
    sections: tuple[WaveFiveReviewPacketSection, ...]
    questions: tuple[WaveFiveReviewQuestion, ...]
    responses: tuple[WaveFiveReviewResponse, ...]
    reviewer_instructions: tuple[str, ...]
    gap_summaries: tuple[str, ...]
    reviewer_ids: tuple[str, ...] = ()
    claims_agi: bool = False
    claims_wave_six: bool = False
    claims_certified: bool = False
    grants_execution_authority: bool = False
    claims_independent_validation: bool = False
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_FIVE_REVIEW_PACKET_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate packet completeness, reviewer provenance, and boundaries."""

        object.__setattr__(self, "packet_id", _text(self.packet_id, "packet_id"))
        object.__setattr__(self, "title", _text(self.title, "title"))
        if self.claims_agi:
            raise ValueError("External review packets cannot claim AGI.")
        if self.claims_wave_six:
            raise ValueError("External review packets cannot claim Wave 6.")
        if self.claims_certified:
            raise ValueError("External review packets cannot claim certification.")
        if self.grants_execution_authority:
            raise ValueError("External review packets cannot grant execution authority.")
        if self.claims_independent_validation:
            raise ValueError(
                "External review packets cannot self-claim independent validation."
            )
        sections = tuple(sorted(self.sections, key=lambda item: item.section_key))
        questions = tuple(sorted(self.questions, key=lambda item: item.question_key))
        responses = tuple(sorted(self.responses, key=lambda item: item.response_key))
        if not sections:
            raise ValueError("External review packets require sections.")
        if not questions:
            raise ValueError("External review packets require questions.")
        _unique_values((item.section_id for item in sections), label="section_id")
        _unique_values((item.section_kind for item in sections), label="section kind")
        question_ids = _unique_values(
            (item.question_id for item in questions), label="question_id"
        )
        _unique_values((item.response_id for item in responses), label="response_id")
        for response in responses:
            if response.question_id not in question_ids:
                raise ValueError(
                    "Review responses must reference packet questions: "
                    f"{response.question_id}"
                )
        object.__setattr__(self, "sections", sections)
        object.__setattr__(self, "questions", questions)
        object.__setattr__(self, "responses", responses)
        object.__setattr__(
            self,
            "reviewer_instructions",
            _unique_text(
                self.reviewer_instructions,
                label="reviewer instruction",
            ),
        )
        object.__setattr__(
            self,
            "gap_summaries",
            _unique_text(self.gap_summaries, label="gap summary"),
        )
        if not self.reviewer_instructions:
            raise ValueError("External review packets require reviewer instructions.")
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
                    "Externally reviewed packets require external review source."
                )
            if not self.reviewer_ids:
                raise ValueError(
                    "Externally reviewed packets require reviewer ids."
                )
            if self.blocks_packet_readiness:
                raise ValueError(
                    "Externally reviewed packets cannot contain blocking responses."
                )

    @property
    def covered_section_kinds(self) -> tuple[WaveFiveReviewPacketSectionKind, ...]:
        """Return packet section kinds represented in the packet."""

        return tuple(section.section_kind for section in self.sections)

    @property
    def missing_required_section_kinds(
        self,
    ) -> tuple[WaveFiveReviewPacketSectionKind, ...]:
        """Return required packet sections absent from the packet."""

        covered = set(self.covered_section_kinds)
        return tuple(
            kind for kind in REQUIRED_REVIEW_PACKET_SECTION_KINDS if kind not in covered
        )

    @property
    def covered_question_kinds(self) -> tuple[WaveFiveReviewQuestionKind, ...]:
        """Return question kinds represented in the packet."""

        kinds: list[WaveFiveReviewQuestionKind] = []
        seen: set[WaveFiveReviewQuestionKind] = set()
        for question in self.questions:
            if question.question_kind not in seen:
                kinds.append(question.question_kind)
                seen.add(question.question_kind)
        return tuple(kinds)

    @property
    def missing_required_question_kinds(self) -> tuple[WaveFiveReviewQuestionKind, ...]:
        """Return required challenge-question kinds absent from the packet."""

        covered = set(self.covered_question_kinds)
        return tuple(
            kind for kind in REQUIRED_REVIEW_QUESTION_KINDS if kind not in covered
        )

    @property
    def blocking_response_ids(self) -> tuple[str, ...]:
        """Return review responses that block packet closure."""

        return tuple(
            response.response_id
            for response in self.responses
            if response.blocks_packet_readiness
        )

    @property
    def unanswered_blocking_question_ids(self) -> tuple[str, ...]:
        """Return blocking questions without reviewer responses."""

        responded = {response.question_id for response in self.responses}
        return tuple(
            question.question_id
            for question in self.questions
            if question.blocks_if_unanswered and question.question_id not in responded
        )

    @property
    def has_required_section_coverage(self) -> bool:
        """Return whether every locked packet section is represented."""

        return not self.missing_required_section_kinds

    @property
    def has_required_question_coverage(self) -> bool:
        """Return whether every locked challenge-question kind is represented."""

        return not self.missing_required_question_kinds

    @property
    def makes_no_forbidden_claims(self) -> bool:
        """Return whether packet avoids forbidden maturity claims."""

        return not any(
            (
                self.claims_agi,
                self.claims_wave_six,
                self.claims_certified,
                self.grants_execution_authority,
                self.claims_independent_validation,
            )
        )

    @property
    def blocks_packet_readiness(self) -> bool:
        """Return whether any condition blocks packet readiness."""

        return bool(
            self.missing_required_section_kinds
            or self.missing_required_question_kinds
            or self.blocking_response_ids
            or self.unanswered_blocking_question_ids
            or not self.makes_no_forbidden_claims
        )

    @property
    def ready_for_external_review(self) -> bool:
        """Return whether packet can enter external review."""

        return (
            self.packet_state
            in {
                WaveFiveReviewPacketState.INTERNAL_PACKET_READY,
                WaveFiveReviewPacketState.READY_FOR_EXTERNAL_REVIEW,
                WaveFiveReviewPacketState.UNDER_EXTERNAL_REVIEW,
            }
            and self.has_required_section_coverage
            and self.has_required_question_coverage
            and not self.blocking_response_ids
            and not self.unanswered_blocking_question_ids
            and self.makes_no_forbidden_claims
        )

    @property
    def externally_reviewed_with_boundaries(self) -> bool:
        """Return whether external review accepted the packet with boundaries."""

        return (
            self.packet_state
            is WaveFiveReviewPacketState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
        )

    @property
    def all_artifact_ids(self) -> tuple[str, ...]:
        """Return all artifact ids referenced by packet sections."""

        artifact_ids: list[str] = []
        seen: set[str] = set()
        for section in self.sections:
            for artifact_id in section.artifact_ids:
                if artifact_id not in seen:
                    artifact_ids.append(artifact_id)
                    seen.add(artifact_id)
        return tuple(artifact_ids)

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids referenced by packet contents."""

        evidence_ids: list[str] = []
        seen: set[str] = set()
        for evidence_id in self._iter_evidence_ids():
            if evidence_id not in seen:
                evidence_ids.append(evidence_id)
                seen.add(evidence_id)
        return tuple(evidence_ids)

    def to_artifact_ref(self) -> WaveFiveArtifactRef:
        """Return this packet as a Wave 5 review-board artifact."""

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
            kind=WaveFiveArtifactKind.REVIEW_BOARD_DOCKET,
            capability_area=WaveFiveCapabilityArea.INDEPENDENT_REVIEW,
            source_system=self.source_system,
            summary=self.title,
            produced_by_engine_id="wave5-external-review-packet-engine",
            produced_by_agent_role_id="review-packet-coordinator",
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=authority,
            validation_status=status,
            claim_boundaries=self.claim_boundaries,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_independent_validation": self.claims_independent_validation,
            "claims_wave_six": self.claims_wave_six,
            "gap_summaries": list(self.gap_summaries),
            "grants_execution_authority": self.grants_execution_authority,
            "notes": list(self.notes),
            "packet_id": self.packet_id,
            "packet_state": self.packet_state.value,
            "questions": [question.canonical_payload() for question in self.questions],
            "responses": [
                response.canonical_payload() for response in self.responses
            ],
            "reviewer_ids": list(self.reviewer_ids),
            "reviewer_instructions": list(self.reviewer_instructions),
            "schema_version": self.schema_version,
            "sections": [section.canonical_payload() for section in self.sections],
            "source_system": self.source_system.value,
            "title": self.title,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this review packet."""

        return _stable_sha256(self.canonical_payload())

    def _iter_evidence_ids(self) -> Iterable[str]:
        """Yield evidence ids in deterministic packet traversal order."""

        for section in self.sections:
            yield from section.evidence_ids
        for question in self.questions:
            yield from question.expected_evidence_ids
        for response in self.responses:
            yield from response.evidence_ids


def required_review_packet_section_kinds() -> tuple[WaveFiveReviewPacketSectionKind, ...]:
    """Return locked review-packet sections required for Wave 5 review."""

    return REQUIRED_REVIEW_PACKET_SECTION_KINDS


def required_review_question_kinds() -> tuple[WaveFiveReviewQuestionKind, ...]:
    """Return locked challenge-question kinds required for Wave 5 review."""

    return REQUIRED_REVIEW_QUESTION_KINDS


def safe_review_response_dispositions() -> tuple[WaveFiveReviewResponseDisposition, ...]:
    """Return review responses that do not block packet closure."""

    return SAFE_REVIEW_RESPONSE_DISPOSITIONS


def blocking_review_response_dispositions() -> tuple[
    WaveFiveReviewResponseDisposition, ...
]:
    """Return review responses that block packet closure."""

    return BLOCKING_REVIEW_RESPONSE_DISPOSITIONS


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

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
