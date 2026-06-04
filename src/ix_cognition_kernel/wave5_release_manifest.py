"""Wave 5 release manifest and evidence-bundle seal records.

Wave 5 needs a final machine-readable manifest that ties together the evidence
bundle without changing the meaning of the evidence. This module records the
required artifact families, deterministic fingerprints, manifest integrity
checks, unresolved release blockers, and anti-overclaim controls. A release
manifest can make the Wave 5 package reviewable; it cannot promote the repo to
Wave 6, claim AGI, grant execution authority, certify the system, or replace
external validation.
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

WAVE_FIVE_RELEASE_ARTIFACT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-release-artifact-v1"
)
WAVE_FIVE_RELEASE_CHECK_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-release-check-v1"
)
WAVE_FIVE_RELEASE_BLOCKER_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-release-blocker-v1"
)
WAVE_FIVE_RELEASE_MANIFEST_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-release-manifest-v1"
)


class WaveFiveReleaseArtifactKind(StrEnum):
    """Required artifacts in the final Wave 5 evidence bundle."""

    EXTERNAL_PROTOCOL_SUITE = "external-protocol-suite"
    INDEPENDENT_REVIEWER_REGISTRY = "independent-reviewer-registry"
    REPRODUCIBILITY_BUNDLE = "reproducibility-bundle"
    ADVERSARIAL_SAFETY_BUNDLE = "adversarial-safety-bundle"
    LONG_HORIZON_EVIDENCE_BUNDLE = "long-horizon-evidence-bundle"
    CROSS_DOMAIN_TRANSFER_BUNDLE = "cross-domain-transfer-bundle"
    BENCHMARK_GAMING_AUDIT = "benchmark-gaming-audit"
    MEMORY_INTEGRITY_PROOF = "memory-integrity-proof"
    SAFE_REFUSAL_PROOF = "safe-refusal-proof"
    HUMAN_AUTHORITY_PROOF = "human-authority-proof"
    REPEATABILITY_LEDGER = "repeatability-ledger"
    BLACKFOX_COMPATIBILITY_HANDOFF = "blackfox-compatibility-handoff"
    WORLDTWIN_SCENARIO_BRIDGE = "worldtwin-scenario-bridge"
    WAVE_SIX_READINESS_GATE = "wave-six-readiness-gate"
    EVIDENCE_DOSSIER = "evidence-dossier"
    MATURITY_SCORECARD = "maturity-scorecard"
    EXTERNAL_REVIEW_PACKET = "external-review-packet"
    FALSIFICATION_LEDGER = "falsification-ledger"


class WaveFiveReleaseArtifactStatus(StrEnum):
    """Status of one release-manifest artifact."""

    INCLUDED = "included"
    INCLUDED_WITH_LIMITS = "included-with-limits"
    NEEDS_EXTERNAL_EVIDENCE = "needs-external-evidence"
    DISPUTED = "disputed"
    BLOCKED = "blocked"
    MISSING = "missing"


class WaveFiveReleaseCheckKind(StrEnum):
    """Checks required before the Wave 5 bundle can be reviewed."""

    REQUIRED_ARTIFACTS_PRESENT = "required-artifacts-present"
    ARTIFACT_DIGESTS_PRESENT = "artifact-digests-present"
    ARTIFACT_EVIDENCE_PRESENT = "artifact-evidence-present"
    MANIFEST_FINGERPRINT_STABLE = "manifest-fingerprint-stable"
    CLAIM_BOUNDARIES_PRESERVED = "claim-boundaries-preserved"
    HUMAN_AUTHORITY_PRESERVED = "human-authority-preserved"
    EXTERNAL_REVIEW_PATH_PRESENT = "external-review-path-present"
    RELEASE_BLOCKERS_VISIBLE = "release-blockers-visible"
    NO_WAVE_SIX_PROMOTION = "no-wave-six-promotion"
    NO_AGI_OR_CERTIFICATION_CLAIM = "no-agi-or-certification-claim"
    NO_EXECUTION_AUTHORITY = "no-execution-authority"


class WaveFiveReleaseCheckResult(StrEnum):
    """Observed result of one release-manifest check."""

    PASSED = "passed"
    PASSED_WITH_LIMITS = "passed-with-limits"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    FAILED = "failed"


class WaveFiveReleaseBlockerKind(StrEnum):
    """Blockers that prevent a clean Wave 5 release bundle."""

    MISSING_ARTIFACT = "missing-artifact"
    INVALID_DIGEST = "invalid-digest"
    MISSING_EVIDENCE = "missing-evidence"
    UNRESOLVED_DISPUTE = "unresolved-dispute"
    FAILED_FALSIFICATION = "failed-falsification"
    AUTHORITY_GAP = "authority-gap"
    CLAIM_BOUNDARY_GAP = "claim-boundary-gap"
    REVIEW_PACKET_GAP = "review-packet-gap"
    WAVE_SIX_OVERCLAIM = "wave-six-overclaim"


class WaveFiveReleaseBlockerSeverity(StrEnum):
    """Severity of a release-manifest blocker."""

    INFORMATIONAL = "informational"
    LIMITATION = "limitation"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKING = "blocking"


class WaveFiveReleaseManifestState(StrEnum):
    """Review state of the Wave 5 release manifest."""

    INTERNAL_MANIFEST_READY = "internal-manifest-ready"
    READY_FOR_EXTERNAL_RELEASE_REVIEW = "ready-for-external-release-review"
    UNDER_EXTERNAL_RELEASE_REVIEW = "under-external-release-review"
    EXTERNALLY_REVIEWED_WITH_BOUNDARIES = "externally-reviewed-with-boundaries"
    BLOCKED_BY_RELEASE_GAP = "blocked-by-release-gap"


SAFE_RELEASE_ARTIFACT_STATUSES: tuple[WaveFiveReleaseArtifactStatus, ...] = (
    WaveFiveReleaseArtifactStatus.INCLUDED,
    WaveFiveReleaseArtifactStatus.INCLUDED_WITH_LIMITS,
)

BLOCKING_RELEASE_ARTIFACT_STATUSES: tuple[WaveFiveReleaseArtifactStatus, ...] = (
    WaveFiveReleaseArtifactStatus.NEEDS_EXTERNAL_EVIDENCE,
    WaveFiveReleaseArtifactStatus.DISPUTED,
    WaveFiveReleaseArtifactStatus.BLOCKED,
    WaveFiveReleaseArtifactStatus.MISSING,
)

REQUIRED_RELEASE_ARTIFACT_KINDS: tuple[WaveFiveReleaseArtifactKind, ...] = (
    WaveFiveReleaseArtifactKind.EXTERNAL_PROTOCOL_SUITE,
    WaveFiveReleaseArtifactKind.INDEPENDENT_REVIEWER_REGISTRY,
    WaveFiveReleaseArtifactKind.REPRODUCIBILITY_BUNDLE,
    WaveFiveReleaseArtifactKind.ADVERSARIAL_SAFETY_BUNDLE,
    WaveFiveReleaseArtifactKind.LONG_HORIZON_EVIDENCE_BUNDLE,
    WaveFiveReleaseArtifactKind.CROSS_DOMAIN_TRANSFER_BUNDLE,
    WaveFiveReleaseArtifactKind.BENCHMARK_GAMING_AUDIT,
    WaveFiveReleaseArtifactKind.MEMORY_INTEGRITY_PROOF,
    WaveFiveReleaseArtifactKind.SAFE_REFUSAL_PROOF,
    WaveFiveReleaseArtifactKind.HUMAN_AUTHORITY_PROOF,
    WaveFiveReleaseArtifactKind.REPEATABILITY_LEDGER,
    WaveFiveReleaseArtifactKind.BLACKFOX_COMPATIBILITY_HANDOFF,
    WaveFiveReleaseArtifactKind.WORLDTWIN_SCENARIO_BRIDGE,
    WaveFiveReleaseArtifactKind.WAVE_SIX_READINESS_GATE,
    WaveFiveReleaseArtifactKind.EVIDENCE_DOSSIER,
    WaveFiveReleaseArtifactKind.MATURITY_SCORECARD,
    WaveFiveReleaseArtifactKind.EXTERNAL_REVIEW_PACKET,
    WaveFiveReleaseArtifactKind.FALSIFICATION_LEDGER,
)

REQUIRED_RELEASE_CHECK_KINDS: tuple[WaveFiveReleaseCheckKind, ...] = (
    WaveFiveReleaseCheckKind.REQUIRED_ARTIFACTS_PRESENT,
    WaveFiveReleaseCheckKind.ARTIFACT_DIGESTS_PRESENT,
    WaveFiveReleaseCheckKind.ARTIFACT_EVIDENCE_PRESENT,
    WaveFiveReleaseCheckKind.MANIFEST_FINGERPRINT_STABLE,
    WaveFiveReleaseCheckKind.CLAIM_BOUNDARIES_PRESERVED,
    WaveFiveReleaseCheckKind.HUMAN_AUTHORITY_PRESERVED,
    WaveFiveReleaseCheckKind.EXTERNAL_REVIEW_PATH_PRESENT,
    WaveFiveReleaseCheckKind.RELEASE_BLOCKERS_VISIBLE,
    WaveFiveReleaseCheckKind.NO_WAVE_SIX_PROMOTION,
    WaveFiveReleaseCheckKind.NO_AGI_OR_CERTIFICATION_CLAIM,
    WaveFiveReleaseCheckKind.NO_EXECUTION_AUTHORITY,
)

EXTERNAL_RELEASE_REVIEW_SOURCE_SYSTEMS: tuple[WaveFiveSourceSystem, ...] = (
    WaveFiveSourceSystem.EXTERNAL_REVIEW,
    WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
    WaveFiveSourceSystem.HUMAN_REVIEW,
)


@dataclass(frozen=True, slots=True)
class WaveFiveReleaseArtifactRecord:
    """One artifact sealed into the final Wave 5 release manifest."""

    artifact_id: str
    artifact_kind: WaveFiveReleaseArtifactKind
    status: WaveFiveReleaseArtifactStatus
    digest: str
    evidence_ids: tuple[str, ...]
    source_system: WaveFiveSourceSystem
    summary: str
    limitations: tuple[str, ...] = ()
    reviewer_ids: tuple[str, ...] = ()
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    schema_version: str = WAVE_FIVE_RELEASE_ARTIFACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate artifact digest, evidence, and claim boundaries."""

        object.__setattr__(self, "artifact_id", _text(self.artifact_id, "artifact_id"))
        object.__setattr__(self, "digest", _sha256(self.digest, "digest"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        object.__setattr__(self, "summary", _text(self.summary, "summary"))
        object.__setattr__(
            self, "limitations", _unique_text(self.limitations, label="limitation")
        )
        object.__setattr__(
            self, "reviewer_ids", _unique_text(self.reviewer_ids, label="reviewer_id")
        )
        object.__setattr__(
            self,
            "claim_boundaries",
            _unique_enum(self.claim_boundaries, label="claim boundary"),
        )
        if not self.evidence_ids:
            raise ValueError("Release artifact records require evidence ids.")
        if self.status is WaveFiveReleaseArtifactStatus.INCLUDED_WITH_LIMITS:
            if not self.limitations:
                raise ValueError("Limited release artifacts require limitations.")
        missing = tuple(
            boundary
            for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
            if boundary not in self.claim_boundaries
        )
        if missing:
            raise ValueError(
                "Release artifact records must preserve claim boundary: "
                f"{missing[0].value}"
            )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def artifact_key(self) -> str:
        """Return deterministic artifact key."""

        return self.artifact_id

    @property
    def blocks_release_readiness(self) -> bool:
        """Return whether this artifact blocks release readiness."""

        return self.status in BLOCKING_RELEASE_ARTIFACT_STATUSES

    @property
    def reviewable_with_boundaries(self) -> bool:
        """Return whether artifact is reviewable without promotion."""

        return self.status in SAFE_RELEASE_ARTIFACT_STATUSES and bool(self.evidence_ids)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "artifact_id": self.artifact_id,
            "artifact_kind": self.artifact_kind.value,
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "digest": self.digest,
            "evidence_ids": list(self.evidence_ids),
            "limitations": list(self.limitations),
            "reviewable_with_boundaries": self.reviewable_with_boundaries,
            "reviewer_ids": list(self.reviewer_ids),
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "status": self.status.value,
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveReleaseManifestCheck:
    """One integrity check over the final release manifest."""

    check_id: str
    check_kind: WaveFiveReleaseCheckKind
    result: WaveFiveReleaseCheckResult
    description: str
    evidence_ids: tuple[str, ...]
    blocking: bool = True
    schema_version: str = WAVE_FIVE_RELEASE_CHECK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate release-check identity and evidence."""

        object.__setattr__(self, "check_id", _text(self.check_id, "check_id"))
        object.__setattr__(self, "description", _text(self.description, "description"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Release manifest checks require evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def check_key(self) -> str:
        """Return deterministic check key."""

        return self.check_id

    @property
    def passed_with_boundaries(self) -> bool:
        """Return whether this check passed without erasing limits."""

        return self.result in {
            WaveFiveReleaseCheckResult.PASSED,
            WaveFiveReleaseCheckResult.PASSED_WITH_LIMITS,
        }

    @property
    def blocks_release_readiness(self) -> bool:
        """Return whether this check blocks release review."""

        return self.blocking and not self.passed_with_boundaries

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "blocking": self.blocking,
            "check_id": self.check_id,
            "check_kind": self.check_kind.value,
            "description": self.description,
            "evidence_ids": list(self.evidence_ids),
            "result": self.result.value,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveReleaseBlocker:
    """Visible blocker or limitation retained in the release manifest."""

    blocker_id: str
    blocker_kind: WaveFiveReleaseBlockerKind
    severity: WaveFiveReleaseBlockerSeverity
    artifact_kind: WaveFiveReleaseArtifactKind
    description: str
    mitigation: str
    evidence_ids: tuple[str, ...]
    resolved: bool = False
    schema_version: str = WAVE_FIVE_RELEASE_BLOCKER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate release blocker evidence and mitigation."""

        object.__setattr__(self, "blocker_id", _text(self.blocker_id, "blocker_id"))
        object.__setattr__(self, "description", _text(self.description, "description"))
        object.__setattr__(self, "mitigation", _text(self.mitigation, "mitigation"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Release blockers require evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def blocker_key(self) -> str:
        """Return deterministic blocker key."""

        return self.blocker_id

    @property
    def blocks_release_readiness(self) -> bool:
        """Return whether this blocker prevents release review."""

        return (
            self.severity is WaveFiveReleaseBlockerSeverity.BLOCKING
            and not self.resolved
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "artifact_kind": self.artifact_kind.value,
            "blocker_id": self.blocker_id,
            "blocker_kind": self.blocker_kind.value,
            "description": self.description,
            "evidence_ids": list(self.evidence_ids),
            "mitigation": self.mitigation,
            "resolved": self.resolved,
            "schema_version": self.schema_version,
            "severity": self.severity.value,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveReleaseManifest:
    """Final Wave 5 release manifest for evidence-bundle review."""

    manifest_id: str
    title: str
    source_system: WaveFiveSourceSystem
    manifest_state: WaveFiveReleaseManifestState
    artifacts: tuple[WaveFiveReleaseArtifactRecord, ...]
    checks: tuple[WaveFiveReleaseManifestCheck, ...]
    blockers: tuple[WaveFiveReleaseBlocker, ...]
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
    schema_version: str = WAVE_FIVE_RELEASE_MANIFEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate manifest completeness and anti-promotion boundaries."""

        object.__setattr__(self, "manifest_id", _text(self.manifest_id, "manifest_id"))
        object.__setattr__(self, "title", _text(self.title, "title"))
        if self.attempted_wave_six_promotion:
            raise ValueError("Release manifests cannot promote to Wave 6.")
        if self.claims_agi:
            raise ValueError("Release manifests cannot claim AGI.")
        if self.grants_execution_authority:
            raise ValueError("Release manifests cannot grant execution authority.")
        if self.claims_production_ready:
            raise ValueError("Release manifests cannot claim production readiness.")
        if self.claims_certified:
            raise ValueError("Release manifests cannot claim certification.")
        if self.claims_independent_validation:
            raise ValueError(
                "Release manifests cannot self-claim independent validation."
            )
        artifacts = tuple(sorted(self.artifacts, key=lambda item: item.artifact_key))
        checks = tuple(sorted(self.checks, key=lambda item: item.check_key))
        blockers = tuple(sorted(self.blockers, key=lambda item: item.blocker_key))
        if not artifacts:
            raise ValueError("Release manifests require artifacts.")
        if not checks:
            raise ValueError("Release manifests require checks.")
        _unique_values((item.artifact_id for item in artifacts), label="artifact_id")
        _unique_values(
            (item.artifact_kind for item in artifacts), label="artifact kind"
        )
        _unique_values((item.check_id for item in checks), label="check_id")
        _unique_values((item.blocker_id for item in blockers), label="blocker_id")
        object.__setattr__(self, "artifacts", artifacts)
        object.__setattr__(self, "checks", checks)
        object.__setattr__(self, "blockers", blockers)
        object.__setattr__(
            self, "protocol_ids", _unique_text(self.protocol_ids, label="protocol_id")
        )
        if not self.protocol_ids:
            raise ValueError("Release manifests require protocol ids.")
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
                "Release manifests must preserve claim boundary: "
                f"{missing_boundaries[0].value}"
            )
        object.__setattr__(self, "notes", _unique_text(self.notes, label="note"))
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.externally_reviewed_with_boundaries:
            if self.source_system not in EXTERNAL_RELEASE_REVIEW_SOURCE_SYSTEMS:
                raise ValueError(
                    "Externally reviewed release manifests require external source."
                )
            if not self.reviewer_ids:
                raise ValueError(
                    "Externally reviewed release manifests require reviewer ids."
                )
            if self.blocks_release_readiness:
                raise ValueError(
                    "Externally reviewed release manifests cannot contain blockers."
                )

    @property
    def covered_artifact_kinds(self) -> tuple[WaveFiveReleaseArtifactKind, ...]:
        """Return artifact kinds represented in this manifest."""

        return tuple(artifact.artifact_kind for artifact in self.artifacts)

    @property
    def missing_required_artifact_kinds(
        self,
    ) -> tuple[WaveFiveReleaseArtifactKind, ...]:
        """Return required release artifacts absent from this manifest."""

        covered = set(self.covered_artifact_kinds)
        return tuple(
            kind for kind in REQUIRED_RELEASE_ARTIFACT_KINDS if kind not in covered
        )

    @property
    def covered_check_kinds(self) -> tuple[WaveFiveReleaseCheckKind, ...]:
        """Return release check kinds represented in this manifest."""

        kinds: list[WaveFiveReleaseCheckKind] = []
        seen: set[WaveFiveReleaseCheckKind] = set()
        for check in self.checks:
            if check.check_kind not in seen:
                kinds.append(check.check_kind)
                seen.add(check.check_kind)
        return tuple(kinds)

    @property
    def missing_required_check_kinds(self) -> tuple[WaveFiveReleaseCheckKind, ...]:
        """Return required release checks absent from this manifest."""

        covered = set(self.covered_check_kinds)
        return tuple(
            kind for kind in REQUIRED_RELEASE_CHECK_KINDS if kind not in covered
        )

    @property
    def blocking_artifact_ids(self) -> tuple[str, ...]:
        """Return artifacts that block release readiness."""

        return tuple(
            artifact.artifact_id
            for artifact in self.artifacts
            if artifact.blocks_release_readiness
        )

    @property
    def blocking_check_ids(self) -> tuple[str, ...]:
        """Return checks that block release readiness."""

        return tuple(
            check.check_id for check in self.checks if check.blocks_release_readiness
        )

    @property
    def unresolved_blocker_ids(self) -> tuple[str, ...]:
        """Return unresolved blocking release blockers."""

        return tuple(
            blocker.blocker_id
            for blocker in self.blockers
            if blocker.blocks_release_readiness
        )

    @property
    def has_required_artifact_coverage(self) -> bool:
        """Return whether every locked release artifact is represented."""

        return not self.missing_required_artifact_kinds

    @property
    def has_required_check_coverage(self) -> bool:
        """Return whether every locked release check is represented."""

        return not self.missing_required_check_kinds

    @property
    def makes_no_forbidden_claims(self) -> bool:
        """Return whether manifest avoids forbidden promotion claims."""

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
    def blocks_release_readiness(self) -> bool:
        """Return whether any condition blocks release review."""

        return bool(
            self.missing_required_artifact_kinds
            or self.missing_required_check_kinds
            or self.blocking_artifact_ids
            or self.blocking_check_ids
            or self.unresolved_blocker_ids
            or not self.makes_no_forbidden_claims
        )

    @property
    def ready_for_external_release_review(self) -> bool:
        """Return whether the release manifest can enter external review."""

        return (
            self.manifest_state
            in {
                WaveFiveReleaseManifestState.INTERNAL_MANIFEST_READY,
                WaveFiveReleaseManifestState.READY_FOR_EXTERNAL_RELEASE_REVIEW,
                WaveFiveReleaseManifestState.UNDER_EXTERNAL_RELEASE_REVIEW,
            }
            and self.has_required_artifact_coverage
            and self.has_required_check_coverage
            and not self.blocking_artifact_ids
            and not self.blocking_check_ids
            and not self.unresolved_blocker_ids
            and self.makes_no_forbidden_claims
        )

    @property
    def externally_reviewed_with_boundaries(self) -> bool:
        """Return whether external release review accepted boundaries."""

        return (
            self.manifest_state
            is WaveFiveReleaseManifestState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
        )

    @property
    def bundle_digest(self) -> str:
        """Return deterministic digest across artifact digests."""

        payload = {
            artifact.artifact_id: artifact.digest for artifact in self.artifacts
        }
        return _stable_sha256(payload)

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound into this manifest."""

        evidence_ids: list[str] = []
        seen: set[str] = set()
        for evidence_id in self._iter_evidence_ids():
            if evidence_id not in seen:
                evidence_ids.append(evidence_id)
                seen.add(evidence_id)
        return tuple(evidence_ids)

    def to_artifact_ref(self) -> WaveFiveArtifactRef:
        """Return this manifest as a Wave 5 traceability artifact."""

        decision = WaveFiveArtifactDecision.NEEDS_EXTERNAL_EVIDENCE
        status = WaveFiveValidationStatus.MISSING_EXTERNAL_EVIDENCE
        authority = WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
        if self.externally_reviewed_with_boundaries:
            decision = WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
            status = WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
        elif self.ready_for_external_release_review:
            decision = WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
            status = WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
        elif self.blocks_release_readiness:
            decision = WaveFiveArtifactDecision.BLOCKED
            status = WaveFiveValidationStatus.REJECTED
            authority = WaveFiveAuthorityState.BLOCKED
        return WaveFiveArtifactRef(
            artifact_id=self.manifest_id,
            kind=WaveFiveArtifactKind.ECOSYSTEM_TRACEABILITY_MAP,
            capability_area=WaveFiveCapabilityArea.ECOSYSTEM_TRACEABILITY,
            source_system=self.source_system,
            summary=self.title,
            produced_by_engine_id="wave5-release-manifest-engine",
            produced_by_agent_role_id="release-manifest-reviewer",
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=authority,
            validation_status=status,
            claim_boundaries=self.claim_boundaries,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "artifacts": [artifact.canonical_payload() for artifact in self.artifacts],
            "attempted_wave_six_promotion": self.attempted_wave_six_promotion,
            "blockers": [blocker.canonical_payload() for blocker in self.blockers],
            "bundle_digest": self.bundle_digest,
            "checks": [check.canonical_payload() for check in self.checks],
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_independent_validation": self.claims_independent_validation,
            "claims_production_ready": self.claims_production_ready,
            "grants_execution_authority": self.grants_execution_authority,
            "manifest_id": self.manifest_id,
            "manifest_state": self.manifest_state.value,
            "notes": list(self.notes),
            "protocol_ids": list(self.protocol_ids),
            "reviewer_ids": list(self.reviewer_ids),
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "title": self.title,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this manifest."""

        return _stable_sha256(self.canonical_payload())

    def _iter_evidence_ids(self) -> Iterable[str]:
        """Yield evidence ids in deterministic manifest traversal order."""

        for artifact in self.artifacts:
            yield from artifact.evidence_ids
        for check in self.checks:
            yield from check.evidence_ids
        for blocker in self.blockers:
            yield from blocker.evidence_ids


def required_release_artifact_kinds() -> tuple[WaveFiveReleaseArtifactKind, ...]:
    """Return locked release artifacts required for Wave 5 manifest review."""

    return REQUIRED_RELEASE_ARTIFACT_KINDS


def required_release_check_kinds() -> tuple[WaveFiveReleaseCheckKind, ...]:
    """Return locked release checks required for Wave 5 manifest review."""

    return REQUIRED_RELEASE_CHECK_KINDS


def safe_release_artifact_statuses() -> tuple[WaveFiveReleaseArtifactStatus, ...]:
    """Return release statuses that do not block review."""

    return SAFE_RELEASE_ARTIFACT_STATUSES


def blocking_release_artifact_statuses() -> tuple[WaveFiveReleaseArtifactStatus, ...]:
    """Return release statuses that block review."""

    return BLOCKING_RELEASE_ARTIFACT_STATUSES


def external_release_review_source_systems() -> tuple[WaveFiveSourceSystem, ...]:
    """Return source systems allowed to assert external release review."""

    return EXTERNAL_RELEASE_REVIEW_SOURCE_SYSTEMS


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


def _sha256(value: str, label: str) -> str:
    """Return a normalized SHA-256 digest or raise when malformed."""

    normalized = _text(value, label).lower()
    if len(normalized) != 64:
        raise ValueError(f"{label} must be a 64-character SHA-256 digest.")
    try:
        int(normalized, 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be hexadecimal.") from exc
    return normalized


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()
