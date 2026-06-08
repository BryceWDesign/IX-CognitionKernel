"""Wave 6 release manifest.

A Wave 6 package may need to leave the development repo as a review handoff.
This module records what can be exported, who may review it, which artifacts are
included, and which claim boundaries are preserved. It is a release manifest,
not a product launch, certification, deployment approval, or AGI claim.
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

WAVE_SIX_RELEASE_ARTIFACT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-release-artifact-v1"
)
WAVE_SIX_RELEASE_MANIFEST_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-release-manifest-v1"
)


class WaveSixReleaseAudience(StrEnum):
    """Allowed audiences for a bounded Wave 6 review release."""

    INTERNAL_REVIEWER = "internal-reviewer"
    HUMAN_AUTHORITY = "human-authority"
    INDEPENDENT_EVALUATOR = "independent-evaluator"
    REPLICATION_REVIEWER = "replication-reviewer"
    AUDIT_REVIEWER = "audit-reviewer"


class WaveSixReleaseArtifactKind(StrEnum):
    """Artifact kinds expected in a Wave 6 review release."""

    AUDIT_MANIFEST = "audit-manifest"
    MATURITY_DECISION_RECORD = "maturity-decision-record"
    EXTERNAL_VALIDATION_GATE = "external-validation-gate"
    EVIDENCE_PACKAGE = "evidence-package"
    REVIEW_SCORECARD = "review-scorecard"
    REPLICATION_PROTOCOL = "replication-protocol"
    CHALLENGE_SUITE = "challenge-suite"
    CLAIM_BOUNDARY_DECLARATION = "claim-boundary-declaration"
    README_SUMMARY = "readme-summary"


class WaveSixReleaseFinding(StrEnum):
    """Release finding for one artifact."""

    INCLUDED = "included"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKS_RELEASE = "blocks-release"


class WaveSixReleaseDecision(StrEnum):
    """Final release decision for the bounded Wave 6 handoff."""

    RELEASE_FOR_BOUNDED_REVIEW = "release-for-bounded-review"
    HOLD_FOR_MORE_EVIDENCE = "hold-for-more-evidence"
    BLOCK_RELEASE = "block-release"


class WaveSixReleaseStatus(StrEnum):
    """Fail-closed release status."""

    READY_FOR_BOUNDED_REVIEW_RELEASE = "ready-for-bounded-review-release"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


WAVE_SIX_REQUIRED_RELEASE_AUDIENCES: tuple[WaveSixReleaseAudience, ...] = (
    WaveSixReleaseAudience.HUMAN_AUTHORITY,
    WaveSixReleaseAudience.INDEPENDENT_EVALUATOR,
    WaveSixReleaseAudience.REPLICATION_REVIEWER,
    WaveSixReleaseAudience.AUDIT_REVIEWER,
)

WAVE_SIX_REQUIRED_RELEASE_ARTIFACT_KINDS: tuple[WaveSixReleaseArtifactKind, ...] = (
    WaveSixReleaseArtifactKind.AUDIT_MANIFEST,
    WaveSixReleaseArtifactKind.MATURITY_DECISION_RECORD,
    WaveSixReleaseArtifactKind.EXTERNAL_VALIDATION_GATE,
    WaveSixReleaseArtifactKind.EVIDENCE_PACKAGE,
    WaveSixReleaseArtifactKind.REVIEW_SCORECARD,
    WaveSixReleaseArtifactKind.REPLICATION_PROTOCOL,
    WaveSixReleaseArtifactKind.CHALLENGE_SUITE,
    WaveSixReleaseArtifactKind.CLAIM_BOUNDARY_DECLARATION,
    WaveSixReleaseArtifactKind.README_SUMMARY,
)


@dataclass(frozen=True, slots=True)
class WaveSixReleaseArtifact:
    """One artifact included in a bounded Wave 6 release manifest."""

    artifact_id: str
    kind: WaveSixReleaseArtifactKind
    artifact_fingerprint: str
    source_path: str
    summary: str
    evidence_ids: tuple[str, ...]
    finding: WaveSixReleaseFinding = WaveSixReleaseFinding.INCLUDED
    reviewer_questions: tuple[str, ...] = ()
    requires_follow_up: bool = False
    blocks_release: bool = False
    schema_version: str = WAVE_SIX_RELEASE_ARTIFACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate artifact identity, evidence, and release finding semantics."""

        object.__setattr__(
            self,
            "artifact_id",
            _require_non_empty(self.artifact_id, "artifact_id"),
        )
        object.__setattr__(
            self,
            "artifact_fingerprint",
            _require_non_empty(self.artifact_fingerprint, "artifact_fingerprint"),
        )
        object.__setattr__(
            self,
            "source_path",
            _require_non_empty(self.source_path, "source_path"),
        )
        object.__setattr__(self, "summary", _require_non_empty(self.summary, "summary"))
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
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Wave 6 release artifacts require evidence ids.")
        if self.finding is WaveSixReleaseFinding.INCLUDED:
            if self.requires_follow_up:
                raise ValueError("Included release artifacts cannot require follow-up.")
            if self.blocks_release:
                raise ValueError("Included release artifacts cannot block release.")
        if (
            self.finding is WaveSixReleaseFinding.NEEDS_MORE_EVIDENCE
            and not self.requires_follow_up
        ):
            raise ValueError("Needs-more-evidence release artifacts require follow-up.")
        if (
            self.finding is WaveSixReleaseFinding.BLOCKS_RELEASE
            and not self.blocks_release
        ):
            raise ValueError("Blocking release artifacts must block release.")

    @property
    def included(self) -> bool:
        """Return whether this artifact is included for bounded review."""

        return self.finding is WaveSixReleaseFinding.INCLUDED

    @property
    def needs_more_evidence(self) -> bool:
        """Return whether this artifact needs more evidence before release."""

        return self.finding is WaveSixReleaseFinding.NEEDS_MORE_EVIDENCE

    @property
    def blocks_bounded_release(self) -> bool:
        """Return whether this artifact blocks bounded review release."""

        return (
            self.blocks_release or self.finding is WaveSixReleaseFinding.BLOCKS_RELEASE
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic artifact payload for hashing and review."""

        return {
            "artifact_fingerprint": self.artifact_fingerprint,
            "artifact_id": self.artifact_id,
            "blocks_release": self.blocks_release,
            "evidence_ids": list(self.evidence_ids),
            "finding": self.finding.value,
            "kind": self.kind.value,
            "requires_follow_up": self.requires_follow_up,
            "reviewer_questions": list(self.reviewer_questions),
            "schema_version": self.schema_version,
            "source_path": self.source_path,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this release artifact."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixReleaseManifest:
    """Deterministic release manifest for bounded Wave 6 review handoff."""

    manifest_id: str
    release_version: str
    artifacts: tuple[WaveSixReleaseArtifact, ...]
    allowed_audiences: tuple[WaveSixReleaseAudience, ...]
    decision: WaveSixReleaseDecision
    claim_boundary_statement: str
    generated_by_engine_id: str
    human_authority_id: str
    required_artifact_kinds: tuple[WaveSixReleaseArtifactKind, ...] = (
        WAVE_SIX_REQUIRED_RELEASE_ARTIFACT_KINDS
    )
    required_audiences: tuple[WaveSixReleaseAudience, ...] = (
        WAVE_SIX_REQUIRED_RELEASE_AUDIENCES
    )
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    allows_autonomous_authority: bool = False
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_RELEASE_MANIFEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate release inventory, audiences, and claim boundaries."""

        object.__setattr__(
            self,
            "manifest_id",
            _require_non_empty(self.manifest_id, "manifest_id"),
        )
        object.__setattr__(
            self,
            "release_version",
            _require_non_empty(self.release_version, "release_version"),
        )
        if not self.artifacts:
            raise ValueError("Wave 6 release manifests require artifacts.")
        sorted_artifacts = tuple(
            sorted(self.artifacts, key=lambda artifact: artifact.artifact_id)
        )
        _unique_ids(
            (artifact.artifact_id for artifact in sorted_artifacts),
            label="artifact_id",
        )
        _unique_ids(
            (artifact.kind for artifact in sorted_artifacts),
            label="artifact kind",
        )
        object.__setattr__(self, "artifacts", sorted_artifacts)
        object.__setattr__(
            self,
            "allowed_audiences",
            _normalize_unique_enum_tuple(
                self.allowed_audiences,
                label="allowed audience",
            ),
        )
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
            "generated_by_engine_id",
            _require_non_empty(self.generated_by_engine_id, "generated_by_engine_id"),
        )
        object.__setattr__(
            self,
            "human_authority_id",
            _require_non_empty(self.human_authority_id, "human_authority_id"),
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
            "required_audiences",
            _normalize_unique_enum_tuple(
                self.required_audiences,
                label="required audience",
            ),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="manifest note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.allowed_audiences:
            raise ValueError("Wave 6 release manifests require allowed audiences.")
        if self.decision is WaveSixReleaseDecision.RELEASE_FOR_BOUNDED_REVIEW:
            if self.missing_artifact_kinds:
                raise ValueError("Release-ready manifests require every artifact kind.")
            if self.missing_required_audiences:
                raise ValueError("Release-ready manifests require every audience.")
            if self.follow_up_artifact_ids:
                raise ValueError("Release-ready manifests cannot require follow-up.")
            if self.blocking_artifact_ids:
                raise ValueError("Release-ready manifests cannot include blockers.")
            if self.overclaim_present:
                raise ValueError("Release-ready manifests cannot contain overclaims.")
            if not self.claim_boundary_statement_valid:
                raise ValueError(
                    "Release-ready manifests require valid claim boundary."
                )
        if (
            self.decision is WaveSixReleaseDecision.BLOCK_RELEASE
            and not self.blocking_artifact_ids
            and not self.overclaim_present
        ):
            raise ValueError("Blocked release manifests require blocker or overclaim.")

    @property
    def artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids in deterministic order."""

        return tuple(artifact.artifact_id for artifact in self.artifacts)

    @property
    def present_artifact_kinds(self) -> tuple[WaveSixReleaseArtifactKind, ...]:
        """Return required artifact kinds represented in the manifest."""

        present = {artifact.kind for artifact in self.artifacts}
        return tuple(kind for kind in self.required_artifact_kinds if kind in present)

    @property
    def missing_artifact_kinds(self) -> tuple[WaveSixReleaseArtifactKind, ...]:
        """Return required artifact kinds missing from the manifest."""

        present = {artifact.kind for artifact in self.artifacts}
        return tuple(
            kind for kind in self.required_artifact_kinds if kind not in present
        )

    @property
    def missing_required_audiences(self) -> tuple[WaveSixReleaseAudience, ...]:
        """Return required release audiences not represented."""

        present = set(self.allowed_audiences)
        return tuple(
            audience for audience in self.required_audiences if audience not in present
        )

    @property
    def included_artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids included for bounded review."""

        return tuple(
            artifact.artifact_id for artifact in self.artifacts if artifact.included
        )

    @property
    def follow_up_artifact_ids(self) -> tuple[str, ...]:
        """Return artifacts requiring more evidence before release."""

        return tuple(
            artifact.artifact_id
            for artifact in self.artifacts
            if artifact.needs_more_evidence
        )

    @property
    def blocking_artifact_ids(self) -> tuple[str, ...]:
        """Return artifacts that block release."""

        return tuple(
            artifact.artifact_id
            for artifact in self.artifacts
            if artifact.blocks_bounded_release
        )

    @property
    def overclaim_present(self) -> bool:
        """Return whether this manifest violates the claim boundary."""

        return (
            self.claims_agi
            or self.claims_production_ready
            or self.claims_certified
            or self.allows_autonomous_authority
        )

    @property
    def claim_boundary_statement_valid(self) -> bool:
        """Return whether the release statement preserves bounded review only."""

        normalized = self.claim_boundary_statement.casefold()
        required = (
            "measured system-level cognition",
            "bounded review",
            "not an agi",
            "human",
        )
        return all(fragment in normalized for fragment in required)

    @property
    def status(self) -> WaveSixReleaseStatus:
        """Return fail-closed release manifest status."""

        if self.overclaim_present or self.blocking_artifact_ids:
            return WaveSixReleaseStatus.BLOCKED
        if (
            self.missing_artifact_kinds
            or self.missing_required_audiences
            or self.follow_up_artifact_ids
            or not self.claim_boundary_statement_valid
        ):
            return WaveSixReleaseStatus.NEEDS_MORE_EVIDENCE
        return WaveSixReleaseStatus.READY_FOR_BOUNDED_REVIEW_RELEASE

    @property
    def ready_for_bounded_review_release(self) -> bool:
        """Return whether the manifest can be released for bounded review."""

        return self.status is WaveSixReleaseStatus.READY_FOR_BOUNDED_REVIEW_RELEASE

    def artifact_for_kind(
        self,
        kind: WaveSixReleaseArtifactKind,
    ) -> WaveSixReleaseArtifact | None:
        """Return the release artifact for a kind, if present."""

        for artifact in self.artifacts:
            if artifact.kind is kind:
                return artifact
        return None

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic release manifest payload."""

        return {
            "allowed_audiences": [
                audience.value for audience in self.allowed_audiences
            ],
            "allows_autonomous_authority": self.allows_autonomous_authority,
            "artifact_ids": list(self.artifact_ids),
            "artifacts": [artifact.canonical_payload() for artifact in self.artifacts],
            "blocking_artifact_ids": list(self.blocking_artifact_ids),
            "claim_boundary_statement": self.claim_boundary_statement,
            "claim_boundary_statement_valid": self.claim_boundary_statement_valid,
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "decision": self.decision.value,
            "follow_up_artifact_ids": list(self.follow_up_artifact_ids),
            "generated_by_engine_id": self.generated_by_engine_id,
            "human_authority_id": self.human_authority_id,
            "included_artifact_ids": list(self.included_artifact_ids),
            "manifest_id": self.manifest_id,
            "missing_artifact_kinds": [
                kind.value for kind in self.missing_artifact_kinds
            ],
            "missing_required_audiences": [
                audience.value for audience in self.missing_required_audiences
            ],
            "notes": list(self.notes),
            "present_artifact_kinds": [
                kind.value for kind in self.present_artifact_kinds
            ],
            "release_version": self.release_version,
            "required_artifact_kinds": [
                kind.value for kind in self.required_artifact_kinds
            ],
            "required_audiences": [
                audience.value for audience in self.required_audiences
            ],
            "schema_version": self.schema_version,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this release manifest."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_release_manifest(
    *,
    manifest_id: str,
    release_version: str,
    artifacts: Iterable[WaveSixReleaseArtifact],
    allowed_audiences: Iterable[WaveSixReleaseAudience],
    decision: WaveSixReleaseDecision,
    claim_boundary_statement: str,
    generated_by_engine_id: str,
    human_authority_id: str,
    notes: Iterable[str] = (),
) -> WaveSixReleaseManifest:
    """Build a deterministic bounded-review release manifest."""

    return WaveSixReleaseManifest(
        manifest_id=manifest_id,
        release_version=release_version,
        artifacts=tuple(artifacts),
        allowed_audiences=tuple(allowed_audiences),
        decision=decision,
        claim_boundary_statement=claim_boundary_statement,
        generated_by_engine_id=generated_by_engine_id,
        human_authority_id=human_authority_id,
        notes=tuple(notes),
    )


def required_wave_six_release_artifact_kinds() -> tuple[
    WaveSixReleaseArtifactKind, ...
]:
    """Return required artifact kinds for a Wave 6 release manifest."""

    return WAVE_SIX_REQUIRED_RELEASE_ARTIFACT_KINDS


def required_wave_six_release_audiences() -> tuple[WaveSixReleaseAudience, ...]:
    """Return required audiences for a bounded Wave 6 review release."""

    return WAVE_SIX_REQUIRED_RELEASE_AUDIENCES


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
