"""Wave 6 independent-review packet.

Wave 6 evidence must be reviewable outside the system that assembled it. This
module creates a deterministic packet for external reviewers with explicit
artifact fingerprints, reviewer questions, replication instructions, and a
clean claim boundary. It does not claim AGI, production readiness,
certification, or autonomous authority.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

T = TypeVar("T")
E = TypeVar("E", bound=StrEnum)

WAVE_SIX_INDEPENDENT_REVIEW_ARTIFACT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-independent-review-artifact-v1"
)
WAVE_SIX_INDEPENDENT_REVIEW_PACKET_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-independent-review-packet-v1"
)


class WaveSixIndependentReviewArtifactKind(StrEnum):
    """Artifact kinds required for independent Wave 6 review."""

    MASTER_LOOP_TRACE = "master-loop-trace"
    CONTRACT_BUNDLE = "contract-bundle"
    DONOR_TRACEABILITY_MAP = "donor-traceability-map"
    REALITY_CORRECTION_LEDGER = "reality-correction-ledger"
    FUTURE_REASONING_CHANGE_LEDGER = "future-reasoning-change-ledger"
    TRANSFER_NOVELTY_LEDGER = "transfer-novelty-ledger"
    FALSIFICATION_LEDGER = "falsification-ledger"
    HUMAN_REVIEW_DOCKET = "human-review-docket"
    CLAIM_BOUNDARY_DECLARATION = "claim-boundary-declaration"
    REPLICATION_INSTRUCTIONS = "replication-instructions"


class WaveSixIndependentReviewFinding(StrEnum):
    """Pre-review finding attached to one independent-review artifact."""

    ACCEPTED_FOR_EXTERNAL_REVIEW = "accepted-for-external-review"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    CONTRADICTED = "contradicted"
    BLOCKS_EXTERNAL_REVIEW = "blocks-external-review"


class WaveSixIndependentReviewDecision(StrEnum):
    """Final packet decision before external review."""

    READY_FOR_EXTERNAL_REVIEW = "ready-for-external-review"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


WAVE_SIX_REQUIRED_INDEPENDENT_REVIEW_ARTIFACT_KINDS: tuple[
    WaveSixIndependentReviewArtifactKind, ...
] = (
    WaveSixIndependentReviewArtifactKind.MASTER_LOOP_TRACE,
    WaveSixIndependentReviewArtifactKind.CONTRACT_BUNDLE,
    WaveSixIndependentReviewArtifactKind.DONOR_TRACEABILITY_MAP,
    WaveSixIndependentReviewArtifactKind.REALITY_CORRECTION_LEDGER,
    WaveSixIndependentReviewArtifactKind.FUTURE_REASONING_CHANGE_LEDGER,
    WaveSixIndependentReviewArtifactKind.TRANSFER_NOVELTY_LEDGER,
    WaveSixIndependentReviewArtifactKind.FALSIFICATION_LEDGER,
    WaveSixIndependentReviewArtifactKind.HUMAN_REVIEW_DOCKET,
    WaveSixIndependentReviewArtifactKind.CLAIM_BOUNDARY_DECLARATION,
    WaveSixIndependentReviewArtifactKind.REPLICATION_INSTRUCTIONS,
)


@dataclass(frozen=True, slots=True)
class WaveSixIndependentReviewArtifact:
    """One artifact submitted for independent Wave 6 review."""

    artifact_id: str
    kind: WaveSixIndependentReviewArtifactKind
    summary: str
    artifact_fingerprint: str
    evidence_ids: tuple[str, ...]
    reviewer_questions: tuple[str, ...]
    finding: WaveSixIndependentReviewFinding
    replication_notes: tuple[str, ...] = ()
    blocks_external_review: bool = False
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    allows_autonomous_authority: bool = False
    schema_version: str = WAVE_SIX_INDEPENDENT_REVIEW_ARTIFACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate review artifact identity, evidence, and claim boundaries."""

        if self.claims_agi:
            raise ValueError("Independent-review artifacts must not claim AGI.")
        if self.claims_production_ready:
            raise ValueError(
                "Independent-review artifacts must not claim production readiness."
            )
        if self.claims_certified:
            raise ValueError(
                "Independent-review artifacts must not claim certification."
            )
        if self.allows_autonomous_authority:
            raise ValueError(
                "Independent-review artifacts must not allow autonomous authority."
            )
        object.__setattr__(
            self,
            "artifact_id",
            _require_non_empty(self.artifact_id, "artifact_id"),
        )
        object.__setattr__(self, "summary", _require_non_empty(self.summary, "summary"))
        object.__setattr__(
            self,
            "artifact_fingerprint",
            _require_non_empty(self.artifact_fingerprint, "artifact_fingerprint"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "reviewer_questions",
            _normalize_unique_text_tuple(
                self.reviewer_questions,
                label="reviewer_question",
            ),
        )
        object.__setattr__(
            self,
            "replication_notes",
            _normalize_unique_text_tuple(
                self.replication_notes,
                label="replication_note",
            ),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Independent-review artifacts require evidence ids.")
        if not self.reviewer_questions:
            raise ValueError("Independent-review artifacts require reviewer questions.")
        if (
            self.finding
            in {
                WaveSixIndependentReviewFinding.CONTRADICTED,
                WaveSixIndependentReviewFinding.BLOCKS_EXTERNAL_REVIEW,
            }
            and not self.blocks_external_review
        ):
            raise ValueError(
                "Contradicting or blocking review artifacts must block review."
            )
        if (
            self.finding is WaveSixIndependentReviewFinding.NEEDS_MORE_EVIDENCE
            and self.blocks_external_review
        ):
            raise ValueError(
                "Needs-more-evidence artifacts should not be marked as blocking."
            )

    @property
    def accepted_for_external_review(self) -> bool:
        """Return whether this artifact is accepted for external review."""

        return (
            self.finding is WaveSixIndependentReviewFinding.ACCEPTED_FOR_EXTERNAL_REVIEW
        )

    @property
    def needs_more_evidence(self) -> bool:
        """Return whether this artifact needs more evidence."""

        return self.finding is WaveSixIndependentReviewFinding.NEEDS_MORE_EVIDENCE

    @property
    def blocks_review(self) -> bool:
        """Return whether this artifact blocks independent review."""

        return self.blocks_external_review or self.finding in {
            WaveSixIndependentReviewFinding.CONTRADICTED,
            WaveSixIndependentReviewFinding.BLOCKS_EXTERNAL_REVIEW,
        }

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic payload for hashing and review."""

        return {
            "allows_autonomous_authority": self.allows_autonomous_authority,
            "artifact_fingerprint": self.artifact_fingerprint,
            "artifact_id": self.artifact_id,
            "blocks_external_review": self.blocks_external_review,
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "evidence_ids": list(self.evidence_ids),
            "finding": self.finding.value,
            "kind": self.kind.value,
            "replication_notes": list(self.replication_notes),
            "reviewer_questions": list(self.reviewer_questions),
            "schema_version": self.schema_version,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this artifact."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixIndependentReviewPacket:
    """Independent-review packet for a Wave 6 evidence package."""

    packet_id: str
    title: str
    artifacts: tuple[WaveSixIndependentReviewArtifact, ...]
    claim_boundary_statement: str
    replication_instructions: tuple[str, ...]
    generated_by_engine_id: str
    decision: WaveSixIndependentReviewDecision
    required_artifact_kinds: tuple[WaveSixIndependentReviewArtifactKind, ...] = (
        WAVE_SIX_REQUIRED_INDEPENDENT_REVIEW_ARTIFACT_KINDS
    )
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    allows_autonomous_authority: bool = False
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_INDEPENDENT_REVIEW_PACKET_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate packet completeness and external-review claim boundary."""

        if self.claims_agi:
            raise ValueError("Independent-review packets must not claim AGI.")
        if self.claims_production_ready:
            raise ValueError(
                "Independent-review packets must not claim production readiness."
            )
        if self.claims_certified:
            raise ValueError("Independent-review packets must not claim certification.")
        if self.allows_autonomous_authority:
            raise ValueError(
                "Independent-review packets must not allow autonomous authority."
            )
        object.__setattr__(
            self,
            "packet_id",
            _require_non_empty(self.packet_id, "packet_id"),
        )
        object.__setattr__(self, "title", _require_non_empty(self.title, "title"))
        if not self.artifacts:
            raise ValueError(
                "Independent-review packets require at least one artifact."
            )
        sorted_artifacts = tuple(
            sorted(self.artifacts, key=lambda artifact: artifact.artifact_id)
        )
        _unique_ids(
            (artifact.artifact_id for artifact in sorted_artifacts),
            label="artifact_id",
        )
        object.__setattr__(self, "artifacts", sorted_artifacts)
        object.__setattr__(
            self,
            "claim_boundary_statement",
            _require_non_empty(
                self.claim_boundary_statement,
                "claim_boundary_statement",
            ),
        )
        object.__setattr__(
            self,
            "replication_instructions",
            _normalize_unique_text_tuple(
                self.replication_instructions,
                label="replication_instruction",
            ),
        )
        object.__setattr__(
            self,
            "generated_by_engine_id",
            _require_non_empty(self.generated_by_engine_id, "generated_by_engine_id"),
        )
        object.__setattr__(
            self,
            "required_artifact_kinds",
            _normalize_unique_enum_tuple(
                self.required_artifact_kinds,
                label="required artifact kind",
            ),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="packet note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.replication_instructions:
            raise ValueError(
                "Independent-review packets require replication instructions."
            )
        if self.decision is WaveSixIndependentReviewDecision.READY_FOR_EXTERNAL_REVIEW:
            if self.missing_artifact_kinds:
                raise ValueError(
                    "Ready packets require every independent-review artifact kind."
                )
            if self.blocking_artifact_ids:
                raise ValueError("Ready packets cannot include blocking artifacts.")
            if self.needs_more_evidence_artifact_ids:
                raise ValueError(
                    "Ready packets cannot include needs-more-evidence artifacts."
                )
        if (
            self.decision is WaveSixIndependentReviewDecision.BLOCKED
            and not self.blocking_artifact_ids
        ):
            raise ValueError("Blocked packets require at least one blocking artifact.")

    @property
    def artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids in deterministic order."""

        return tuple(artifact.artifact_id for artifact in self.artifacts)

    @property
    def present_artifact_kinds(
        self,
    ) -> tuple[WaveSixIndependentReviewArtifactKind, ...]:
        """Return required artifact kinds represented in the packet."""

        present = {artifact.kind for artifact in self.artifacts}
        return tuple(kind for kind in self.required_artifact_kinds if kind in present)

    @property
    def missing_artifact_kinds(
        self,
    ) -> tuple[WaveSixIndependentReviewArtifactKind, ...]:
        """Return required artifact kinds missing from the packet."""

        present = {artifact.kind for artifact in self.artifacts}
        return tuple(
            kind for kind in self.required_artifact_kinds if kind not in present
        )

    @property
    def accepted_artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids accepted for external review."""

        return tuple(
            artifact.artifact_id
            for artifact in self.artifacts
            if artifact.accepted_for_external_review
        )

    @property
    def needs_more_evidence_artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids that require more evidence."""

        return tuple(
            artifact.artifact_id
            for artifact in self.artifacts
            if artifact.needs_more_evidence
        )

    @property
    def blocking_artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids that block independent review."""

        return tuple(
            artifact.artifact_id
            for artifact in self.artifacts
            if artifact.blocks_review
        )

    @property
    def ready_for_external_review(self) -> bool:
        """Return whether the packet is ready for independent review."""

        return (
            self.decision is WaveSixIndependentReviewDecision.READY_FOR_EXTERNAL_REVIEW
            and not self.missing_artifact_kinds
            and not self.blocking_artifact_ids
            and not self.needs_more_evidence_artifact_ids
        )

    @property
    def blocks_external_review(self) -> bool:
        """Return whether the packet blocks external review."""

        return self.decision is WaveSixIndependentReviewDecision.BLOCKED or bool(
            self.blocking_artifact_ids
        )

    def artifact_for_kind(
        self, kind: WaveSixIndependentReviewArtifactKind
    ) -> WaveSixIndependentReviewArtifact | None:
        """Return the first artifact for a kind, if present."""

        for artifact in self.artifacts:
            if artifact.kind is kind:
                return artifact
        return None

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic packet payload for hashing and review."""

        return {
            "accepted_artifact_ids": list(self.accepted_artifact_ids),
            "allows_autonomous_authority": self.allows_autonomous_authority,
            "artifacts": [artifact.canonical_payload() for artifact in self.artifacts],
            "blocking_artifact_ids": list(self.blocking_artifact_ids),
            "claim_boundary_statement": self.claim_boundary_statement,
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "decision": self.decision.value,
            "generated_by_engine_id": self.generated_by_engine_id,
            "missing_artifact_kinds": [
                kind.value for kind in self.missing_artifact_kinds
            ],
            "needs_more_evidence_artifact_ids": list(
                self.needs_more_evidence_artifact_ids
            ),
            "notes": list(self.notes),
            "packet_id": self.packet_id,
            "replication_instructions": list(self.replication_instructions),
            "required_artifact_kinds": [
                kind.value for kind in self.required_artifact_kinds
            ],
            "schema_version": self.schema_version,
            "title": self.title,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this packet."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_independent_review_packet(
    *,
    packet_id: str,
    title: str,
    artifacts: Iterable[WaveSixIndependentReviewArtifact],
    claim_boundary_statement: str,
    replication_instructions: Iterable[str],
    generated_by_engine_id: str,
    decision: WaveSixIndependentReviewDecision,
    notes: Iterable[str] = (),
) -> WaveSixIndependentReviewPacket:
    """Build a deterministic Wave 6 independent-review packet."""

    return WaveSixIndependentReviewPacket(
        packet_id=packet_id,
        title=title,
        artifacts=tuple(artifacts),
        claim_boundary_statement=claim_boundary_statement,
        replication_instructions=tuple(replication_instructions),
        generated_by_engine_id=generated_by_engine_id,
        decision=decision,
        notes=tuple(notes),
    )


def required_wave_six_independent_review_artifact_kinds() -> tuple[
    WaveSixIndependentReviewArtifactKind, ...
]:
    """Return artifact kinds required for independent Wave 6 review."""

    return WAVE_SIX_REQUIRED_INDEPENDENT_REVIEW_ARTIFACT_KINDS


def _require_non_empty(value: str, label: str) -> str:
    """Return stripped text or raise when empty."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _normalize_unique_text_tuple(
    values: Iterable[str], *, label: str
) -> tuple[str, ...]:
    """Normalize text values while rejecting blanks and duplicates."""

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        stripped = _require_non_empty(value, label)
        if stripped in seen:
            raise ValueError(f"Duplicate {label} detected: {stripped}")
        normalized.append(stripped)
        seen.add(stripped)
    return tuple(normalized)


def _normalize_unique_enum_tuple(values: Iterable[E], *, label: str) -> tuple[E, ...]:
    """Return enum values as a tuple while rejecting duplicates."""

    normalized: list[E] = []
    seen: set[E] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value.value}")
        normalized.append(value)
        seen.add(value)
    return tuple(normalized)


def _unique_ids(values: Iterable[T], *, label: str) -> set[T]:
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
