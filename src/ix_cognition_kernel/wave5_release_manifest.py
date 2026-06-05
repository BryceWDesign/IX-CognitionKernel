"""Wave 5 release manifest and evidence-bundle seal records.

Wave 5 needs a final machine-readable manifest that ties together the evidence
bundle without changing the meaning of the evidence. This module records the
required artifact families, deterministic fingerprints, manifest integrity
checks, unresolved release blockers, and anti-overclaim controls. A release
manifest can make the Wave 5 package reviewable; it cannot promote the repo to
Wave 6, claim AGI, grant execution authority, certify anything, or self-claim
independent validation.
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

WAVE_FIVE_MANIFEST_ENTRY_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-manifest-entry-v1"
)
WAVE_FIVE_MANIFEST_CHECK_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-manifest-integrity-check-v1"
)
WAVE_FIVE_RELEASE_BLOCKER_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-release-blocker-v1"
)
WAVE_FIVE_RELEASE_MANIFEST_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-release-manifest-v1"
)


class WaveFiveManifestArtifactFamily(StrEnum):
    """Artifact families required in the Wave 5 release manifest."""

    FOUNDATION_CONTRACTS = "foundation-contracts"
    EXTERNAL_PROTOCOLS = "external-protocols"
    REVIEWER_ATTESTATIONS = "reviewer-attestations"
    REPRODUCIBILITY = "reproducibility"
    REPEATABILITY = "repeatability"
    ADVERSARIAL_SAFETY = "adversarial-safety"
    LONG_HORIZON = "long-horizon"
    CROSS_DOMAIN_TRANSFER = "cross-domain-transfer"
    BENCHMARK_GAMING = "benchmark-gaming"
    MEMORY_INTEGRITY = "memory-integrity"
    SAFE_REFUSAL = "safe-refusal"
    HUMAN_AUTHORITY = "human-authority"
    BLACKFOX_BRIDGE = "blackfox-bridge"
    WORLDTWIN_BRIDGE = "worldtwin-bridge"
    WAVE_SIX_READINESS = "wave-six-readiness"
    FALSIFICATION_LEDGER = "falsification-ledger"
    EVIDENCE_DOSSIER = "evidence-dossier"
    MATURITY_SCORECARD = "maturity-scorecard"
    EXTERNAL_REVIEW_PACKET = "external-review-packet"


class WaveFiveManifestEntryStatus(StrEnum):
    """Status of one manifest entry."""

    SEALED = "sealed"
    SEALED_WITH_LIMITS = "sealed-with-limits"
    NEEDS_EXTERNAL_EVIDENCE = "needs-external-evidence"
    DISPUTED = "disputed"
    BLOCKED = "blocked"
    MISSING = "missing"


class WaveFiveManifestIntegrityCheckKind(StrEnum):
    """Integrity checks required for the release manifest."""

    REQUIRED_FAMILIES_PRESENT = "required-families-present"
    ENTRY_DIGESTS_PRESENT = "entry-digests-present"
    ENTRY_EVIDENCE_PRESENT = "entry-evidence-present"
    MANIFEST_FINGERPRINT_STABLE = "manifest-fingerprint-stable"
    BLOCKERS_VISIBLE = "blockers-visible"
    CLAIM_BOUNDARIES_PRESERVED = "claim-boundaries-preserved"
    HUMAN_AUTHORITY_PRESERVED = "human-authority-preserved"
    NO_WAVE_SIX_PROMOTION = "no-wave-six-promotion"
    NO_AGI_OR_CERTIFICATION_CLAIM = "no-agi-or-certification-claim"
    NO_EXECUTION_AUTHORITY = "no-execution-authority"
    NO_SELF_CLAIMED_INDEPENDENT_VALIDATION = "no-self-claimed-independent-validation"


class WaveFiveManifestCheckResult(StrEnum):
    """Observed result of one manifest integrity check."""

    PASSED = "passed"
    PASSED_WITH_LIMITS = "passed-with-limits"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    FAILED = "failed"


class WaveFiveReleaseBlockerKind(StrEnum):
    """Blockers that prevent bounded release of the Wave 5 package."""

    MISSING_ARTIFACT_FAMILY = "missing-artifact-family"
    INVALID_DIGEST = "invalid-digest"
    MISSING_EVIDENCE = "missing-evidence"
    DISPUTED_EVIDENCE = "disputed-evidence"
    UNRESOLVED_FALSIFICATION = "unresolved-falsification"
    HUMAN_AUTHORITY_GAP = "human-authority-gap"
    SAFE_REFUSAL_GAP = "safe-refusal-gap"
    CLAIM_BOUNDARY_GAP = "claim-boundary-gap"
    WAVE_SIX_OVERCLAIM = "wave-six-overclaim"
    INDEPENDENT_VALIDATION_OVERCLAIM = "independent-validation-overclaim"


class WaveFiveReleaseBlockerSeverity(StrEnum):
    """Severity of a release blocker."""

    INFORMATIONAL = "informational"
    LIMITATION = "limitation"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKING = "blocking"


class WaveFiveReleaseManifestState(StrEnum):
    """Review state of a Wave 5 release manifest."""

    INTERNAL_MANIFEST_READY = "internal-manifest-ready"
    READY_FOR_EXTERNAL_RELEASE_REVIEW = "ready-for-external-release-review"
    UNDER_EXTERNAL_RELEASE_REVIEW = "under-external-release-review"
    EXTERNALLY_REVIEWED_WITH_BOUNDARIES = "externally-reviewed-with-boundaries"
    BLOCKED_BY_RELEASE_GAP = "blocked-by-release-gap"


SAFE_MANIFEST_ENTRY_STATUSES: tuple[WaveFiveManifestEntryStatus, ...] = (
    WaveFiveManifestEntryStatus.SEALED,
    WaveFiveManifestEntryStatus.SEALED_WITH_LIMITS,
)

BLOCKING_MANIFEST_ENTRY_STATUSES: tuple[WaveFiveManifestEntryStatus, ...] = (
    WaveFiveManifestEntryStatus.NEEDS_EXTERNAL_EVIDENCE,
    WaveFiveManifestEntryStatus.DISPUTED,
    WaveFiveManifestEntryStatus.BLOCKED,
    WaveFiveManifestEntryStatus.MISSING,
)

REQUIRED_MANIFEST_ARTIFACT_FAMILIES: tuple[WaveFiveManifestArtifactFamily, ...] = (
    WaveFiveManifestArtifactFamily.FOUNDATION_CONTRACTS,
    WaveFiveManifestArtifactFamily.EXTERNAL_PROTOCOLS,
    WaveFiveManifestArtifactFamily.REVIEWER_ATTESTATIONS,
    WaveFiveManifestArtifactFamily.REPRODUCIBILITY,
    WaveFiveManifestArtifactFamily.REPEATABILITY,
    WaveFiveManifestArtifactFamily.ADVERSARIAL_SAFETY,
    WaveFiveManifestArtifactFamily.LONG_HORIZON,
    WaveFiveManifestArtifactFamily.CROSS_DOMAIN_TRANSFER,
    WaveFiveManifestArtifactFamily.BENCHMARK_GAMING,
    WaveFiveManifestArtifactFamily.MEMORY_INTEGRITY,
    WaveFiveManifestArtifactFamily.SAFE_REFUSAL,
    WaveFiveManifestArtifactFamily.HUMAN_AUTHORITY,
    WaveFiveManifestArtifactFamily.BLACKFOX_BRIDGE,
    WaveFiveManifestArtifactFamily.WORLDTWIN_BRIDGE,
    WaveFiveManifestArtifactFamily.WAVE_SIX_READINESS,
    WaveFiveManifestArtifactFamily.FALSIFICATION_LEDGER,
    WaveFiveManifestArtifactFamily.EVIDENCE_DOSSIER,
    WaveFiveManifestArtifactFamily.MATURITY_SCORECARD,
    WaveFiveManifestArtifactFamily.EXTERNAL_REVIEW_PACKET,
)

REQUIRED_MANIFEST_CHECK_KINDS: tuple[WaveFiveManifestIntegrityCheckKind, ...] = (
    WaveFiveManifestIntegrityCheckKind.REQUIRED_FAMILIES_PRESENT,
    WaveFiveManifestIntegrityCheckKind.ENTRY_DIGESTS_PRESENT,
    WaveFiveManifestIntegrityCheckKind.ENTRY_EVIDENCE_PRESENT,
    WaveFiveManifestIntegrityCheckKind.MANIFEST_FINGERPRINT_STABLE,
    WaveFiveManifestIntegrityCheckKind.BLOCKERS_VISIBLE,
    WaveFiveManifestIntegrityCheckKind.CLAIM_BOUNDARIES_PRESERVED,
    WaveFiveManifestIntegrityCheckKind.HUMAN_AUTHORITY_PRESERVED,
    WaveFiveManifestIntegrityCheckKind.NO_WAVE_SIX_PROMOTION,
    WaveFiveManifestIntegrityCheckKind.NO_AGI_OR_CERTIFICATION_CLAIM,
    WaveFiveManifestIntegrityCheckKind.NO_EXECUTION_AUTHORITY,
    WaveFiveManifestIntegrityCheckKind.NO_SELF_CLAIMED_INDEPENDENT_VALIDATION,
)

EXTERNAL_RELEASE_REVIEW_SOURCE_SYSTEMS: tuple[WaveFiveSourceSystem, ...] = (
    WaveFiveSourceSystem.EXTERNAL_REVIEW,
    WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
    WaveFiveSourceSystem.HUMAN_REVIEW,
)


@dataclass(frozen=True, slots=True)
class WaveFiveReleaseManifestEntry:
    """One artifact-family entry in the Wave 5 release manifest."""

    entry_id: str
    artifact_family: WaveFiveManifestArtifactFamily
    status: WaveFiveManifestEntryStatus
    artifact_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    digest: str
    summary: str
    limitations: tuple[str, ...] = ()
    blocker_ids: tuple[str, ...] = ()
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    schema_version: str = WAVE_FIVE_MANIFEST_ENTRY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate manifest-entry references, digest, and boundaries."""

        object.__setattr__(self, "entry_id", _text(self.entry_id, "entry_id"))
        object.__setattr__(
            self, "artifact_ids", _unique_text(self.artifact_ids, label="artifact_id")
        )
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        object.__setattr__(self, "digest", _sha256(self.digest, "digest"))
        object.__setattr__(self, "summary", _text(self.summary, "summary"))
        object.__setattr__(
            self, "limitations", _unique_text(self.limitations, label="limitation")
        )
        object.__setattr__(
            self, "blocker_ids", _unique_text(self.blocker_ids, label="blocker_id")
        )
        object.__setattr__(
            self,
            "claim_boundaries",
            _unique_enum(self.claim_boundaries, label="claim boundary"),
        )
        if not self.artifact_ids:
            raise ValueError("Release manifest entries require artifact ids.")
        if not self.evidence_ids:
            raise ValueError("Release manifest entries require evidence ids.")
        if (
            self.status is WaveFiveManifestEntryStatus.SEALED_WITH_LIMITS
            and not self.limitations
        ):
            raise ValueError("Limited manifest entries require limitations.")
        if self.status in BLOCKING_MANIFEST_ENTRY_STATUSES and not self.blocker_ids:
            raise ValueError("Blocking manifest entries require blocker ids.")
        missing = tuple(
            boundary
            for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
            if boundary not in self.claim_boundaries
        )
        if missing:
            raise ValueError(
                "Manifest entries must preserve claim boundary: "
                f"{missing[0].value}"
            )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def entry_key(self) -> str:
        """Return deterministic entry key."""

        return self.entry_id

    @property
    def blocks_release(self) -> bool:
        """Return whether this entry blocks release manifest readiness."""

        return self.status in BLOCKING_MANIFEST_ENTRY_STATUSES

    @property
    def sealed_with_boundaries(self) -> bool:
        """Return whether this entry is sealed without promotion."""

        return self.status in SAFE_MANIFEST_ENTRY_STATUSES and bool(self.evidence_ids)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "artifact_family": self.artifact_family.value,
            "artifact_ids": list(self.artifact_ids),
            "blocker_ids": list(self.blocker_ids),
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "digest": self.digest,
            "entry_id": self.entry_id,
            "evidence_ids": list(self.evidence_ids),
            "limitations": list(self.limitations),
            "schema_version": self.schema_version,
            "sealed_with_boundaries": self.sealed_with_boundaries,
            "source_system": self.source_system.value,
            "status": self.status.value,
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveReleaseManifestIntegrityCheck:
    """One integrity check over the release manifest."""

    check_id: str
    check_kind: WaveFiveManifestIntegrityCheckKind
    result: WaveFiveManifestCheckResult
    description: str
    evidence_ids: tuple[str, ...]
    blocking: bool = True
    schema_version: str = WAVE_FIVE_MANIFEST_CHECK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate manifest-check evidence."""

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
        """Return whether check passed without erasing limits."""

        return self.result in {
            WaveFiveManifestCheckResult.PASSED,
            WaveFiveManifestCheckResult.PASSED_WITH_LIMITS,
        }

    @property
    def blocks_release(self) -> bool:
        """Return whether this check blocks release readiness."""

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
    """Visible blocker that prevents bounded release."""

    blocker_id: str
    blocker_kind: WaveFiveReleaseBlockerKind
    severity: WaveFiveReleaseBlockerSeverity
    artifact_family: WaveFiveManifestArtifactFamily
    description: str
    mitigation: str
    evidence_ids: tuple[str, ...]
    resolved: bool = False
    schema_version: str = WAVE_FIVE_RELEASE_BLOCKER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate release-blocker identity and evidence."""

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
    def blocks_release(self) -> bool:
        """Return whether this unresolved blocker prevents release."""

        return (
            self.severity is WaveFiveReleaseBlockerSeverity.BLOCKING
            and not self.resolved
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "artifact_family": self.artifact_family.value,
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
    """Final Wave 5 release manifest for bounded external review."""

    manifest_id: str
    title: str
    source_system: WaveFiveSourceSystem
    manifest_state: WaveFiveReleaseManifestState
    entries: tuple[WaveFiveReleaseManifestEntry, ...]
    integrity_checks: tuple[WaveFiveReleaseManifestIntegrityCheck, ...]
    blockers: tuple[WaveFiveReleaseBlocker, ...]
    evidence_dossier_artifact_id: str
    maturity_scorecard_artifact_id: str
    external_review_packet_artifact_id: str
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
        """Validate manifest completeness and anti-overclaim boundaries."""

        object.__setattr__(self, "manifest_id", _text(self.manifest_id, "manifest_id"))
        object.__setattr__(self, "title", _text(self.title, "title"))
        object.__setattr__(
            self,
            "evidence_dossier_artifact_id",
            _text(self.evidence_dossier_artifact_id, "evidence_dossier_artifact_id"),
        )
        object.__setattr__(
            self,
            "maturity_scorecard_artifact_id",
            _text(
                self.maturity_scorecard_artifact_id,
                "maturity_scorecard_artifact_id",
            ),
        )
        object.__setattr__(
            self,
            "external_review_packet_artifact_id",
            _text(
                self.external_review_packet_artifact_id,
                "external_review_packet_artifact_id",
            ),
        )
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
        entries = tuple(sorted(self.entries, key=lambda item: item.entry_key))
        checks = tuple(sorted(self.integrity_checks, key=lambda item: item.check_key))
        blockers = tuple(sorted(self.blockers, key=lambda item: item.blocker_key))
        if not entries:
            raise ValueError("Release manifests require entries.")
        if not checks:
            raise ValueError("Release manifests require integrity checks.")
        _unique_values((item.entry_id for item in entries), label="entry_id")
        _unique_values(
            (item.artifact_family for item in entries), label="artifact family"
        )
        _unique_values((item.check_id for item in checks), label="check_id")
        _unique_values((item.blocker_id for item in blockers), label="blocker_id")
        object.__setattr__(self, "entries", entries)
        object.__setattr__(self, "integrity_checks", checks)
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
            if self.blocks_release:
                raise ValueError(
                    "Externally reviewed release manifests cannot contain blockers."
                )

    @property
    def covered_artifact_families(self) -> tuple[WaveFiveManifestArtifactFamily, ...]:
        """Return artifact families represented in this manifest."""

        return tuple(entry.artifact_family for entry in self.entries)

    @property
    def missing_required_artifact_families(
        self,
    ) -> tuple[WaveFiveManifestArtifactFamily, ...]:
        """Return required artifact families absent from this manifest."""

        covered = set(self.covered_artifact_families)
        return tuple(
            family
            for family in REQUIRED_MANIFEST_ARTIFACT_FAMILIES
            if family not in covered
        )

    @property
    def covered_check_kinds(self) -> tuple[WaveFiveManifestIntegrityCheckKind, ...]:
        """Return integrity-check kinds represented in this manifest."""

        kinds: list[WaveFiveManifestIntegrityCheckKind] = []
        seen: set[WaveFiveManifestIntegrityCheckKind] = set()
        for check in self.integrity_checks:
            if check.check_kind not in seen:
                kinds.append(check.check_kind)
                seen.add(check.check_kind)
        return tuple(kinds)

    @property
    def missing_required_check_kinds(
        self,
    ) -> tuple[WaveFiveManifestIntegrityCheckKind, ...]:
        """Return required manifest checks absent from this manifest."""

        covered = set(self.covered_check_kinds)
        return tuple(
            kind for kind in REQUIRED_MANIFEST_CHECK_KINDS if kind not in covered
        )

    @property
    def blocking_entry_ids(self) -> tuple[str, ...]:
        """Return manifest entries that block release."""

        return tuple(entry.entry_id for entry in self.entries if entry.blocks_release)

    @property
    def blocking_check_ids(self) -> tuple[str, ...]:
        """Return integrity checks that block release."""

        return tuple(
            check.check_id for check in self.integrity_checks if check.blocks_release
        )

    @property
    def unresolved_blocker_ids(self) -> tuple[str, ...]:
        """Return unresolved blocking release blockers."""

        return tuple(
            blocker.blocker_id for blocker in self.blockers if blocker.blocks_release
        )

    @property
    def has_required_family_coverage(self) -> bool:
        """Return whether every locked artifact family is represented."""

        return not self.missing_required_artifact_families

    @property
    def has_required_check_coverage(self) -> bool:
        """Return whether every locked manifest check is represented."""

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
    def blocks_release(self) -> bool:
        """Return whether any condition blocks bounded release."""

        return bool(
            self.missing_required_artifact_families
            or self.missing_required_check_kinds
            or self.blocking_entry_ids
            or self.blocking_check_ids
            or self.unresolved_blocker_ids
            or not self.makes_no_forbidden_claims
        )

    @property
    def ready_for_external_release_review(self) -> bool:
        """Return whether manifest can enter external release review."""

        return (
            self.manifest_state
            in {
                WaveFiveReleaseManifestState.INTERNAL_MANIFEST_READY,
                WaveFiveReleaseManifestState.READY_FOR_EXTERNAL_RELEASE_REVIEW,
                WaveFiveReleaseManifestState.UNDER_EXTERNAL_RELEASE_REVIEW,
            }
            and self.has_required_family_coverage
            and self.has_required_check_coverage
            and not self.blocking_entry_ids
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
    def manifest_bundle_digest(self) -> str:
        """Return deterministic digest across manifest entry digests."""

        payload = {entry.entry_id: entry.digest for entry in self.entries}
        return _stable_sha256(payload)

    @property
    def all_artifact_ids(self) -> tuple[str, ...]:
        """Return all artifact ids referenced by the manifest."""

        artifact_ids: list[str] = []
        seen: set[str] = set()
        for entry in self.entries:
            for artifact_id in entry.artifact_ids:
                if artifact_id not in seen:
                    artifact_ids.append(artifact_id)
                    seen.add(artifact_id)
        return tuple(artifact_ids)

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound into the manifest."""

        evidence_ids: list[str] = []
        seen: set[str] = set()
        for evidence_id in self._iter_evidence_ids():
            if evidence_id not in seen:
                evidence_ids.append(evidence_id)
                seen.add(evidence_id)
        return tuple(evidence_ids)

    def to_artifact_ref(self) -> WaveFiveArtifactRef:
        """Return this manifest as a Wave 5 release artifact."""

        decision = WaveFiveArtifactDecision.NEEDS_EXTERNAL_EVIDENCE
        status = WaveFiveValidationStatus.MISSING_EXTERNAL_EVIDENCE
        authority = WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
        if self.externally_reviewed_with_boundaries:
            decision = WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
            status = WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
        elif self.ready_for_external_release_review:
            decision = WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
            status = WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
        elif self.blocks_release:
            decision = WaveFiveArtifactDecision.BLOCKED
            status = WaveFiveValidationStatus.REJECTED
            authority = WaveFiveAuthorityState.BLOCKED
        return WaveFiveArtifactRef(
            artifact_id=self.manifest_id,
            kind=WaveFiveArtifactKind.RELEASE_MANIFEST,
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
            "attempted_wave_six_promotion": self.attempted_wave_six_promotion,
            "blockers": [blocker.canonical_payload() for blocker in self.blockers],
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_independent_validation": self.claims_independent_validation,
            "claims_production_ready": self.claims_production_ready,
            "entries": [entry.canonical_payload() for entry in self.entries],
            "evidence_dossier_artifact_id": self.evidence_dossier_artifact_id,
            "external_review_packet_artifact_id": (
                self.external_review_packet_artifact_id
            ),
            "grants_execution_authority": self.grants_execution_authority,
            "integrity_checks": [
                check.canonical_payload() for check in self.integrity_checks
            ],
            "manifest_bundle_digest": self.manifest_bundle_digest,
            "manifest_id": self.manifest_id,
            "manifest_state": self.manifest_state.value,
            "maturity_scorecard_artifact_id": self.maturity_scorecard_artifact_id,
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

        for entry in self.entries:
            yield from entry.evidence_ids
        for check in self.integrity_checks:
            yield from check.evidence_ids
        for blocker in self.blockers:
            yield from blocker.evidence_ids


def required_manifest_artifact_families() -> tuple[
    WaveFiveManifestArtifactFamily, ...
]:
    """Return locked artifact families required for Wave 5 manifest release."""

    return REQUIRED_MANIFEST_ARTIFACT_FAMILIES


def required_manifest_check_kinds() -> tuple[WaveFiveManifestIntegrityCheckKind, ...]:
    """Return locked manifest checks required for Wave 5 manifest release."""

    return REQUIRED_MANIFEST_CHECK_KINDS


def safe_manifest_entry_statuses() -> tuple[WaveFiveManifestEntryStatus, ...]:
    """Return manifest entry statuses that do not block release."""

    return SAFE_MANIFEST_ENTRY_STATUSES


def blocking_manifest_entry_statuses() -> tuple[WaveFiveManifestEntryStatus, ...]:
    """Return manifest entry statuses that block release."""

    return BLOCKING_MANIFEST_ENTRY_STATUSES


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

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
