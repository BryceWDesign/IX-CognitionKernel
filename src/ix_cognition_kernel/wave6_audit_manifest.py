"""Wave 6 audit manifest.

After the maturity gate, reviewers need a deterministic inventory of the Wave 6
package: which artifacts were reviewed, which fingerprints anchor them, which
items still need evidence, and which claim boundary survived. This module is an
audit manifest, not a promotion engine. It cannot claim AGI, certification,
production readiness, or autonomous authority.
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

WAVE_SIX_AUDIT_ARTIFACT_SCHEMA_VERSION = "ix-cognition-kernel-wave6-audit-artifact-v1"
WAVE_SIX_AUDIT_MANIFEST_SCHEMA_VERSION = "ix-cognition-kernel-wave6-audit-manifest-v1"


class WaveSixAuditArtifactKind(StrEnum):
    """Artifact kinds expected in a complete Wave 6 audit manifest."""

    CONTRACT_BUNDLE = "contract-bundle"
    MASTER_LOOP_TRACE = "master-loop-trace"
    DONOR_TRACEABILITY_MAP = "donor-traceability-map"
    REALITY_CORRECTION_LEDGER = "reality-correction-ledger"
    FUTURE_REASONING_CHANGE_LEDGER = "future-reasoning-change-ledger"
    TRANSFER_NOVELTY_LEDGER = "transfer-novelty-ledger"
    FALSIFICATION_LEDGER = "falsification-ledger"
    HUMAN_REVIEW_DOCKET = "human-review-docket"
    INDEPENDENT_REVIEW_PACKET = "independent-review-packet"
    CHALLENGE_SUITE = "challenge-suite"
    REPLICATION_PROTOCOL = "replication-protocol"
    TRIAL_REPLAY_LEDGER = "trial-replay-ledger"
    EXTERNAL_VALIDATION_GATE = "external-validation-gate"
    REVIEW_SCORECARD = "review-scorecard"
    MATURITY_GATE = "maturity-gate"
    MATURITY_DECISION_RECORD = "maturity-decision-record"
    CLAIM_BOUNDARY_DECLARATION = "claim-boundary-declaration"


class WaveSixAuditFinding(StrEnum):
    """Finding attached to an audit manifest artifact."""

    ACCEPTED = "accepted"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKS_CLAIM = "blocks-claim"


class WaveSixAuditManifestDecision(StrEnum):
    """Final manifest decision."""

    ENTER_BOUNDED_WAVE_SIX_REVIEW = "enter-bounded-wave-six-review"
    CONTINUE_EVIDENCE_COLLECTION = "continue-evidence-collection"
    BLOCK_WAVE_SIX_INTERPRETATION = "block-wave-six-interpretation"


class WaveSixAuditManifestStatus(StrEnum):
    """Fail-closed status for a Wave 6 audit manifest."""

    READY_FOR_AUDIT_REVIEW = "ready-for-audit-review"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKED = "blocked"


WAVE_SIX_REQUIRED_AUDIT_ARTIFACT_KINDS: tuple[WaveSixAuditArtifactKind, ...] = (
    WaveSixAuditArtifactKind.CONTRACT_BUNDLE,
    WaveSixAuditArtifactKind.MASTER_LOOP_TRACE,
    WaveSixAuditArtifactKind.DONOR_TRACEABILITY_MAP,
    WaveSixAuditArtifactKind.REALITY_CORRECTION_LEDGER,
    WaveSixAuditArtifactKind.FUTURE_REASONING_CHANGE_LEDGER,
    WaveSixAuditArtifactKind.TRANSFER_NOVELTY_LEDGER,
    WaveSixAuditArtifactKind.FALSIFICATION_LEDGER,
    WaveSixAuditArtifactKind.HUMAN_REVIEW_DOCKET,
    WaveSixAuditArtifactKind.INDEPENDENT_REVIEW_PACKET,
    WaveSixAuditArtifactKind.CHALLENGE_SUITE,
    WaveSixAuditArtifactKind.REPLICATION_PROTOCOL,
    WaveSixAuditArtifactKind.TRIAL_REPLAY_LEDGER,
    WaveSixAuditArtifactKind.EXTERNAL_VALIDATION_GATE,
    WaveSixAuditArtifactKind.REVIEW_SCORECARD,
    WaveSixAuditArtifactKind.MATURITY_GATE,
    WaveSixAuditArtifactKind.MATURITY_DECISION_RECORD,
    WaveSixAuditArtifactKind.CLAIM_BOUNDARY_DECLARATION,
)


@dataclass(frozen=True, slots=True)
class WaveSixAuditArtifact:
    """One artifact reference inside the Wave 6 audit manifest."""

    artifact_id: str
    kind: WaveSixAuditArtifactKind
    artifact_fingerprint: str
    summary: str
    evidence_ids: tuple[str, ...]
    finding: WaveSixAuditFinding
    reviewer_questions: tuple[str, ...]
    source_system_id: str = "ix-cognition-kernel"
    requires_follow_up: bool = False
    blocks_claim: bool = False
    schema_version: str = WAVE_SIX_AUDIT_ARTIFACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate audit artifact identity, evidence, and finding semantics."""

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
            "source_system_id",
            _require_non_empty(self.source_system_id, "source_system_id"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Wave 6 audit artifacts require evidence ids.")
        if not self.reviewer_questions:
            raise ValueError("Wave 6 audit artifacts require reviewer questions.")
        if self.finding is WaveSixAuditFinding.ACCEPTED:
            if self.requires_follow_up:
                raise ValueError("Accepted audit artifacts cannot require follow-up.")
            if self.blocks_claim:
                raise ValueError("Accepted audit artifacts cannot block the claim.")
        if (
            self.finding is WaveSixAuditFinding.NEEDS_MORE_EVIDENCE
            and not self.requires_follow_up
        ):
            raise ValueError("Needs-more-evidence audit artifacts require follow-up.")
        if self.finding is WaveSixAuditFinding.BLOCKS_CLAIM and not self.blocks_claim:
            raise ValueError("Blocking audit artifacts must block the claim.")

    @property
    def accepted(self) -> bool:
        """Return whether this artifact is accepted."""

        return self.finding is WaveSixAuditFinding.ACCEPTED

    @property
    def needs_more_evidence(self) -> bool:
        """Return whether this artifact still needs evidence."""

        return self.finding is WaveSixAuditFinding.NEEDS_MORE_EVIDENCE

    @property
    def blocks_interpretation(self) -> bool:
        """Return whether this artifact blocks Wave 6 interpretation."""

        return self.blocks_claim or self.finding is WaveSixAuditFinding.BLOCKS_CLAIM

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic artifact payload for hashing and review."""

        return {
            "artifact_fingerprint": self.artifact_fingerprint,
            "artifact_id": self.artifact_id,
            "blocks_claim": self.blocks_claim,
            "evidence_ids": list(self.evidence_ids),
            "finding": self.finding.value,
            "kind": self.kind.value,
            "requires_follow_up": self.requires_follow_up,
            "reviewer_questions": list(self.reviewer_questions),
            "schema_version": self.schema_version,
            "source_system_id": self.source_system_id,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this artifact reference."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixAuditManifest:
    """Deterministic audit manifest for the bounded Wave 6 package."""

    manifest_id: str
    artifacts: tuple[WaveSixAuditArtifact, ...]
    decision: WaveSixAuditManifestDecision
    claim_boundary_statement: str
    generated_by_engine_id: str
    human_authority_id: str
    independent_reviewer_id: str
    required_artifact_kinds: tuple[WaveSixAuditArtifactKind, ...] = (
        WAVE_SIX_REQUIRED_AUDIT_ARTIFACT_KINDS
    )
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    allows_autonomous_authority: bool = False
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_AUDIT_MANIFEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate manifest identity, coverage, and claim boundary."""

        object.__setattr__(
            self,
            "manifest_id",
            _require_non_empty(self.manifest_id, "manifest_id"),
        )
        if not self.artifacts:
            raise ValueError("Wave 6 audit manifests require artifacts.")
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
            "independent_reviewer_id",
            _require_non_empty(self.independent_reviewer_id, "independent_reviewer_id"),
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
            _normalize_unique_text_tuple(self.notes, label="manifest note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if self.decision is WaveSixAuditManifestDecision.ENTER_BOUNDED_WAVE_SIX_REVIEW:
            if self.missing_artifact_kinds:
                raise ValueError("Ready audit manifests require every artifact kind.")
            if self.blocking_artifact_ids:
                raise ValueError("Ready audit manifests cannot include blockers.")
            if self.follow_up_artifact_ids:
                raise ValueError("Ready audit manifests cannot require follow-up.")
            if self.overclaim_present:
                raise ValueError("Ready audit manifests cannot contain overclaims.")
        if (
            self.decision is WaveSixAuditManifestDecision.BLOCK_WAVE_SIX_INTERPRETATION
            and not self.blocking_artifact_ids
            and not self.overclaim_present
        ):
            raise ValueError("Blocked audit manifests require a blocker or overclaim.")

    @property
    def artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids in deterministic order."""

        return tuple(artifact.artifact_id for artifact in self.artifacts)

    @property
    def present_artifact_kinds(self) -> tuple[WaveSixAuditArtifactKind, ...]:
        """Return required artifact kinds represented in the manifest."""

        present = {artifact.kind for artifact in self.artifacts}
        return tuple(kind for kind in self.required_artifact_kinds if kind in present)

    @property
    def missing_artifact_kinds(self) -> tuple[WaveSixAuditArtifactKind, ...]:
        """Return required artifact kinds missing from the manifest."""

        present = {artifact.kind for artifact in self.artifacts}
        return tuple(
            kind for kind in self.required_artifact_kinds if kind not in present
        )

    @property
    def accepted_artifact_ids(self) -> tuple[str, ...]:
        """Return accepted artifact ids."""

        return tuple(
            artifact.artifact_id for artifact in self.artifacts if artifact.accepted
        )

    @property
    def follow_up_artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids that still require follow-up evidence."""

        return tuple(
            artifact.artifact_id
            for artifact in self.artifacts
            if artifact.needs_more_evidence
        )

    @property
    def blocking_artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids that block Wave 6 interpretation."""

        return tuple(
            artifact.artifact_id
            for artifact in self.artifacts
            if artifact.blocks_interpretation
        )

    @property
    def overclaim_present(self) -> bool:
        """Return whether the manifest violates the claim boundary."""

        return (
            self.claims_agi
            or self.claims_production_ready
            or self.claims_certified
            or self.allows_autonomous_authority
        )

    @property
    def claim_boundary_statement_valid(self) -> bool:
        """Return whether the manifest statement preserves the allowed claim."""

        normalized = self.claim_boundary_statement.casefold()
        required = (
            "measured system-level cognition",
            "not an agi",
            "human",
            "independent review",
        )
        return all(fragment in normalized for fragment in required)

    @property
    def status(self) -> WaveSixAuditManifestStatus:
        """Return fail-closed manifest status."""

        if self.overclaim_present or self.blocking_artifact_ids:
            return WaveSixAuditManifestStatus.BLOCKED
        if (
            self.missing_artifact_kinds
            or self.follow_up_artifact_ids
            or not self.claim_boundary_statement_valid
        ):
            return WaveSixAuditManifestStatus.NEEDS_MORE_EVIDENCE
        return WaveSixAuditManifestStatus.READY_FOR_AUDIT_REVIEW

    @property
    def ready_for_audit_review(self) -> bool:
        """Return whether the manifest can enter audit review."""

        return self.status is WaveSixAuditManifestStatus.READY_FOR_AUDIT_REVIEW

    def artifact_for_kind(
        self,
        kind: WaveSixAuditArtifactKind,
    ) -> WaveSixAuditArtifact | None:
        """Return the artifact for a kind, if present."""

        for artifact in self.artifacts:
            if artifact.kind is kind:
                return artifact
        return None

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic manifest payload for hashing and review."""

        return {
            "accepted_artifact_ids": list(self.accepted_artifact_ids),
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
            "independent_reviewer_id": self.independent_reviewer_id,
            "manifest_id": self.manifest_id,
            "missing_artifact_kinds": [
                kind.value for kind in self.missing_artifact_kinds
            ],
            "notes": list(self.notes),
            "present_artifact_kinds": [
                kind.value for kind in self.present_artifact_kinds
            ],
            "required_artifact_kinds": [
                kind.value for kind in self.required_artifact_kinds
            ],
            "schema_version": self.schema_version,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this manifest."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_audit_manifest(
    *,
    manifest_id: str,
    artifacts: Iterable[WaveSixAuditArtifact],
    decision: WaveSixAuditManifestDecision,
    claim_boundary_statement: str,
    generated_by_engine_id: str,
    human_authority_id: str,
    independent_reviewer_id: str,
    notes: Iterable[str] = (),
) -> WaveSixAuditManifest:
    """Build a deterministic Wave 6 audit manifest."""

    return WaveSixAuditManifest(
        manifest_id=manifest_id,
        artifacts=tuple(artifacts),
        decision=decision,
        claim_boundary_statement=claim_boundary_statement,
        generated_by_engine_id=generated_by_engine_id,
        human_authority_id=human_authority_id,
        independent_reviewer_id=independent_reviewer_id,
        notes=tuple(notes),
    )


def required_wave_six_audit_artifact_kinds() -> tuple[WaveSixAuditArtifactKind, ...]:
    """Return required artifact kinds for a complete Wave 6 audit manifest."""

    return WAVE_SIX_REQUIRED_AUDIT_ARTIFACT_KINDS


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
