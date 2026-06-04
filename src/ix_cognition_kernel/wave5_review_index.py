"""Wave 5 review index records.

Wave 5 needs a navigable evidence index that points reviewers to the final
manifest, declaration, dossier, scorecard, review packet, falsification ledger,
and supporting proof artifacts. This module records those entry points, reviewer
routes, digest checks, blockers, and anti-overclaim controls. The index helps
humans find evidence; it does not promote the project to Wave 6, claim AGI,
grant execution authority, certify the system, or assert independent validation.
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

WAVE_FIVE_REVIEW_INDEX_ENTRY_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-review-index-entry-v1"
)
WAVE_FIVE_REVIEW_INDEX_CHECK_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-review-index-check-v1"
)
WAVE_FIVE_REVIEW_INDEX_BLOCKER_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-review-index-blocker-v1"
)
WAVE_FIVE_REVIEW_INDEX_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-review-index-v1"
)


class WaveFiveReviewIndexEntryKind(StrEnum):
    """Required navigational entries in the Wave 5 review index."""

    RELEASE_MANIFEST = "release-manifest"
    BOUNDED_DECLARATION = "bounded-declaration"
    EVIDENCE_DOSSIER = "evidence-dossier"
    MATURITY_SCORECARD = "maturity-scorecard"
    EXTERNAL_REVIEW_PACKET = "external-review-packet"
    FALSIFICATION_LEDGER = "falsification-ledger"
    WAVE_SIX_READINESS_GATE = "wave-six-readiness-gate"
    REPEATABILITY_LEDGER = "repeatability-ledger"
    HUMAN_AUTHORITY_PROOF = "human-authority-proof"
    SAFE_REFUSAL_PROOF = "safe-refusal-proof"
    MEMORY_INTEGRITY_PROOF = "memory-integrity-proof"
    BENCHMARK_GAMING_AUDIT = "benchmark-gaming-audit"
    BLACKFOX_COMPATIBILITY_BRIDGE = "blackfox-compatibility-bridge"
    WORLDTWIN_SCENARIO_BRIDGE = "worldtwin-scenario-bridge"


class WaveFiveReviewIndexEntryStatus(StrEnum):
    """Status of one review-index entry."""

    INDEXED = "indexed"
    INDEXED_WITH_LIMITS = "indexed-with-limits"
    NEEDS_EXTERNAL_EVIDENCE = "needs-external-evidence"
    DISPUTED = "disputed"
    BLOCKED = "blocked"
    MISSING = "missing"


class WaveFiveReviewIndexCheckKind(StrEnum):
    """Checks required for the review index to be trusted as navigation."""

    REQUIRED_ENTRIES_PRESENT = "required-entries-present"
    ENTRY_ARTIFACT_IDS_PRESENT = "entry-artifact-ids-present"
    ENTRY_DIGESTS_PRESENT = "entry-digests-present"
    ENTRY_EVIDENCE_PRESENT = "entry-evidence-present"
    REVIEWER_ROUTES_PRESENT = "reviewer-routes-present"
    RELEASE_MANIFEST_REFERENCED = "release-manifest-referenced"
    DECLARATION_REFERENCED = "declaration-referenced"
    BLOCKERS_VISIBLE = "blockers-visible"
    CLAIM_BOUNDARIES_PRESERVED = "claim-boundaries-preserved"
    HUMAN_AUTHORITY_PRESERVED = "human-authority-preserved"
    NO_WAVE_SIX_PROMOTION = "no-wave-six-promotion"
    NO_AGI_OR_CERTIFICATION_CLAIM = "no-agi-or-certification-claim"
    NO_EXECUTION_AUTHORITY = "no-execution-authority"


class WaveFiveReviewIndexCheckResult(StrEnum):
    """Observed result of one review-index check."""

    PASSED = "passed"
    PASSED_WITH_LIMITS = "passed-with-limits"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    FAILED = "failed"


class WaveFiveReviewIndexBlockerKind(StrEnum):
    """Blocker classes that prevent the index from being review-ready."""

    MISSING_ENTRY = "missing-entry"
    INVALID_DIGEST = "invalid-digest"
    MISSING_EVIDENCE = "missing-evidence"
    MISSING_REVIEWER_ROUTE = "missing-reviewer-route"
    UNRESOLVED_RELEASE_BLOCKER = "unresolved-release-blocker"
    UNRESOLVED_DECLARATION_BLOCKER = "unresolved-declaration-blocker"
    DISPUTED_PACKET = "disputed-packet"
    FAILED_FALSIFICATION = "failed-falsification"
    CLAIM_BOUNDARY_GAP = "claim-boundary-gap"
    WAVE_SIX_OVERCLAIM = "wave-six-overclaim"


class WaveFiveReviewIndexBlockerSeverity(StrEnum):
    """Severity of a review-index blocker."""

    INFORMATIONAL = "informational"
    LIMITATION = "limitation"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKING = "blocking"


class WaveFiveReviewIndexState(StrEnum):
    """Review state of the Wave 5 review index."""

    INTERNAL_INDEX_READY = "internal-index-ready"
    READY_FOR_EXTERNAL_INDEX_REVIEW = "ready-for-external-index-review"
    UNDER_EXTERNAL_INDEX_REVIEW = "under-external-index-review"
    EXTERNALLY_REVIEWED_WITH_BOUNDARIES = "externally-reviewed-with-boundaries"
    BLOCKED_BY_INDEX_GAP = "blocked-by-index-gap"


SAFE_INDEX_ENTRY_STATUSES: tuple[WaveFiveReviewIndexEntryStatus, ...] = (
    WaveFiveReviewIndexEntryStatus.INDEXED,
    WaveFiveReviewIndexEntryStatus.INDEXED_WITH_LIMITS,
)

BLOCKING_INDEX_ENTRY_STATUSES: tuple[WaveFiveReviewIndexEntryStatus, ...] = (
    WaveFiveReviewIndexEntryStatus.NEEDS_EXTERNAL_EVIDENCE,
    WaveFiveReviewIndexEntryStatus.DISPUTED,
    WaveFiveReviewIndexEntryStatus.BLOCKED,
    WaveFiveReviewIndexEntryStatus.MISSING,
)

REQUIRED_REVIEW_INDEX_ENTRY_KINDS: tuple[WaveFiveReviewIndexEntryKind, ...] = (
    WaveFiveReviewIndexEntryKind.RELEASE_MANIFEST,
    WaveFiveReviewIndexEntryKind.BOUNDED_DECLARATION,
    WaveFiveReviewIndexEntryKind.EVIDENCE_DOSSIER,
    WaveFiveReviewIndexEntryKind.MATURITY_SCORECARD,
    WaveFiveReviewIndexEntryKind.EXTERNAL_REVIEW_PACKET,
    WaveFiveReviewIndexEntryKind.FALSIFICATION_LEDGER,
    WaveFiveReviewIndexEntryKind.WAVE_SIX_READINESS_GATE,
    WaveFiveReviewIndexEntryKind.REPEATABILITY_LEDGER,
    WaveFiveReviewIndexEntryKind.HUMAN_AUTHORITY_PROOF,
    WaveFiveReviewIndexEntryKind.SAFE_REFUSAL_PROOF,
    WaveFiveReviewIndexEntryKind.MEMORY_INTEGRITY_PROOF,
    WaveFiveReviewIndexEntryKind.BENCHMARK_GAMING_AUDIT,
    WaveFiveReviewIndexEntryKind.BLACKFOX_COMPATIBILITY_BRIDGE,
    WaveFiveReviewIndexEntryKind.WORLDTWIN_SCENARIO_BRIDGE,
)

REQUIRED_REVIEW_INDEX_CHECK_KINDS: tuple[WaveFiveReviewIndexCheckKind, ...] = (
    WaveFiveReviewIndexCheckKind.REQUIRED_ENTRIES_PRESENT,
    WaveFiveReviewIndexCheckKind.ENTRY_ARTIFACT_IDS_PRESENT,
    WaveFiveReviewIndexCheckKind.ENTRY_DIGESTS_PRESENT,
    WaveFiveReviewIndexCheckKind.ENTRY_EVIDENCE_PRESENT,
    WaveFiveReviewIndexCheckKind.REVIEWER_ROUTES_PRESENT,
    WaveFiveReviewIndexCheckKind.RELEASE_MANIFEST_REFERENCED,
    WaveFiveReviewIndexCheckKind.DECLARATION_REFERENCED,
    WaveFiveReviewIndexCheckKind.BLOCKERS_VISIBLE,
    WaveFiveReviewIndexCheckKind.CLAIM_BOUNDARIES_PRESERVED,
    WaveFiveReviewIndexCheckKind.HUMAN_AUTHORITY_PRESERVED,
    WaveFiveReviewIndexCheckKind.NO_WAVE_SIX_PROMOTION,
    WaveFiveReviewIndexCheckKind.NO_AGI_OR_CERTIFICATION_CLAIM,
    WaveFiveReviewIndexCheckKind.NO_EXECUTION_AUTHORITY,
)

EXTERNAL_INDEX_REVIEW_SOURCE_SYSTEMS: tuple[WaveFiveSourceSystem, ...] = (
    WaveFiveSourceSystem.EXTERNAL_REVIEW,
    WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
    WaveFiveSourceSystem.HUMAN_REVIEW,
)


@dataclass(frozen=True, slots=True)
class WaveFiveReviewIndexEntry:
    """One reviewer-navigation entry pointing to a Wave 5 artifact."""

    entry_id: str
    entry_kind: WaveFiveReviewIndexEntryKind
    status: WaveFiveReviewIndexEntryStatus
    artifact_id: str
    digest: str
    evidence_ids: tuple[str, ...]
    reviewer_route: str
    source_system: WaveFiveSourceSystem
    summary: str
    limitations: tuple[str, ...] = ()
    blocker_ids: tuple[str, ...] = ()
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    schema_version: str = WAVE_FIVE_REVIEW_INDEX_ENTRY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate index entry identity, digest, route, evidence, and limits."""

        object.__setattr__(self, "entry_id", _text(self.entry_id, "entry_id"))
        object.__setattr__(self, "artifact_id", _text(self.artifact_id, "artifact_id"))
        object.__setattr__(self, "digest", _sha256(self.digest, "digest"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        object.__setattr__(
            self, "reviewer_route", _text(self.reviewer_route, "reviewer_route")
        )
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
        if not self.evidence_ids:
            raise ValueError("Review index entries require evidence ids.")
        if self.status is WaveFiveReviewIndexEntryStatus.INDEXED_WITH_LIMITS:
            if not self.limitations:
                raise ValueError("Limited review index entries require limitations.")
        if self.status in BLOCKING_INDEX_ENTRY_STATUSES and not self.blocker_ids:
            raise ValueError("Blocking review index entries require blocker ids.")
        missing = tuple(
            boundary
            for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
            if boundary not in self.claim_boundaries
        )
        if missing:
            raise ValueError(
                "Review index entries must preserve claim boundary: "
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
    def blocks_index_readiness(self) -> bool:
        """Return whether this entry blocks index readiness."""

        return self.status in BLOCKING_INDEX_ENTRY_STATUSES

    @property
    def reviewable_with_boundaries(self) -> bool:
        """Return whether this entry is reviewable without promotion."""

        return self.status in SAFE_INDEX_ENTRY_STATUSES and bool(self.evidence_ids)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "artifact_id": self.artifact_id,
            "blocker_ids": list(self.blocker_ids),
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "digest": self.digest,
            "entry_id": self.entry_id,
            "entry_kind": self.entry_kind.value,
            "evidence_ids": list(self.evidence_ids),
            "limitations": list(self.limitations),
            "reviewable_with_boundaries": self.reviewable_with_boundaries,
            "reviewer_route": self.reviewer_route,
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "status": self.status.value,
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveReviewIndexCheck:
    """One integrity check over the Wave 5 review index."""

    check_id: str
    check_kind: WaveFiveReviewIndexCheckKind
    result: WaveFiveReviewIndexCheckResult
    description: str
    evidence_ids: tuple[str, ...]
    blocking: bool = True
    schema_version: str = WAVE_FIVE_REVIEW_INDEX_CHECK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate review-index check identity and evidence."""

        object.__setattr__(self, "check_id", _text(self.check_id, "check_id"))
        object.__setattr__(self, "description", _text(self.description, "description"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Review index checks require evidence ids.")
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
            WaveFiveReviewIndexCheckResult.PASSED,
            WaveFiveReviewIndexCheckResult.PASSED_WITH_LIMITS,
        }

    @property
    def blocks_index_readiness(self) -> bool:
        """Return whether this check blocks index readiness."""

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
class WaveFiveReviewIndexBlocker:
    """Visible blocker or limitation retained in the review index."""

    blocker_id: str
    blocker_kind: WaveFiveReviewIndexBlockerKind
    severity: WaveFiveReviewIndexBlockerSeverity
    entry_kind: WaveFiveReviewIndexEntryKind
    description: str
    mitigation: str
    evidence_ids: tuple[str, ...]
    resolved: bool = False
    schema_version: str = WAVE_FIVE_REVIEW_INDEX_BLOCKER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate blocker evidence and mitigation."""

        object.__setattr__(self, "blocker_id", _text(self.blocker_id, "blocker_id"))
        object.__setattr__(self, "description", _text(self.description, "description"))
        object.__setattr__(self, "mitigation", _text(self.mitigation, "mitigation"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Review index blockers require evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def blocker_key(self) -> str:
        """Return deterministic blocker key."""

        return self.blocker_id

    @property
    def blocks_index_readiness(self) -> bool:
        """Return whether this blocker prevents index review."""

        return (
            self.severity is WaveFiveReviewIndexBlockerSeverity.BLOCKING
            and not self.resolved
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "blocker_id": self.blocker_id,
            "blocker_kind": self.blocker_kind.value,
            "description": self.description,
            "entry_kind": self.entry_kind.value,
            "evidence_ids": list(self.evidence_ids),
            "mitigation": self.mitigation,
            "resolved": self.resolved,
            "schema_version": self.schema_version,
            "severity": self.severity.value,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveReviewIndex:
    """Navigable Wave 5 evidence index for external reviewers."""

    index_id: str
    title: str
    source_system: WaveFiveSourceSystem
    index_state: WaveFiveReviewIndexState
    entries: tuple[WaveFiveReviewIndexEntry, ...]
    checks: tuple[WaveFiveReviewIndexCheck, ...]
    blockers: tuple[WaveFiveReviewIndexBlocker, ...]
    release_manifest_artifact_id: str
    bounded_declaration_artifact_id: str
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
    schema_version: str = WAVE_FIVE_REVIEW_INDEX_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate index completeness, references, and anti-overclaim gates."""

        object.__setattr__(self, "index_id", _text(self.index_id, "index_id"))
        object.__setattr__(self, "title", _text(self.title, "title"))
        object.__setattr__(
            self,
            "release_manifest_artifact_id",
            _text(self.release_manifest_artifact_id, "release_manifest_artifact_id"),
        )
        object.__setattr__(
            self,
            "bounded_declaration_artifact_id",
            _text(
                self.bounded_declaration_artifact_id,
                "bounded_declaration_artifact_id",
            ),
        )
        if self.attempted_wave_six_promotion:
            raise ValueError("Review indexes cannot promote to Wave 6.")
        if self.claims_agi:
            raise ValueError("Review indexes cannot claim AGI.")
        if self.grants_execution_authority:
            raise ValueError("Review indexes cannot grant execution authority.")
        if self.claims_production_ready:
            raise ValueError("Review indexes cannot claim production readiness.")
        if self.claims_certified:
            raise ValueError("Review indexes cannot claim certification.")
        if self.claims_independent_validation:
            raise ValueError("Review indexes cannot self-claim independent validation.")
        entries = tuple(sorted(self.entries, key=lambda item: item.entry_key))
        checks = tuple(sorted(self.checks, key=lambda item: item.check_key))
        blockers = tuple(sorted(self.blockers, key=lambda item: item.blocker_key))
        if not entries:
            raise ValueError("Review indexes require entries.")
        if not checks:
            raise ValueError("Review indexes require checks.")
        _unique_values((item.entry_id for item in entries), label="entry_id")
        _unique_values((item.entry_kind for item in entries), label="entry kind")
        _unique_values((item.artifact_id for item in entries), label="artifact_id")
        _unique_values((item.check_id for item in checks), label="check_id")
        _unique_values((item.blocker_id for item in blockers), label="blocker_id")
        object.__setattr__(self, "entries", entries)
        object.__setattr__(self, "checks", checks)
        object.__setattr__(self, "blockers", blockers)
        self._validate_manifest_and_declaration_references(entries)
        object.__setattr__(
            self, "protocol_ids", _unique_text(self.protocol_ids, label="protocol_id")
        )
        if not self.protocol_ids:
            raise ValueError("Review indexes require protocol ids.")
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
                "Review indexes must preserve claim boundary: "
                f"{missing_boundaries[0].value}"
            )
        object.__setattr__(self, "notes", _unique_text(self.notes, label="note"))
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.externally_reviewed_with_boundaries:
            if self.source_system not in EXTERNAL_INDEX_REVIEW_SOURCE_SYSTEMS:
                raise ValueError("Externally reviewed indexes require external source.")
            if not self.reviewer_ids:
                raise ValueError("Externally reviewed indexes require reviewer ids.")
            if self.blocks_index_readiness:
                raise ValueError("Externally reviewed indexes cannot contain blockers.")

    @property
    def covered_entry_kinds(self) -> tuple[WaveFiveReviewIndexEntryKind, ...]:
        """Return entry kinds represented in this index."""

        return tuple(entry.entry_kind for entry in self.entries)

    @property
    def missing_required_entry_kinds(self) -> tuple[WaveFiveReviewIndexEntryKind, ...]:
        """Return required review-index entries absent from this index."""

        covered = set(self.covered_entry_kinds)
        return tuple(
            kind for kind in REQUIRED_REVIEW_INDEX_ENTRY_KINDS if kind not in covered
        )

    @property
    def covered_check_kinds(self) -> tuple[WaveFiveReviewIndexCheckKind, ...]:
        """Return review-index check kinds represented in this index."""

        kinds: list[WaveFiveReviewIndexCheckKind] = []
        seen: set[WaveFiveReviewIndexCheckKind] = set()
        for check in self.checks:
            if check.check_kind not in seen:
                kinds.append(check.check_kind)
                seen.add(check.check_kind)
        return tuple(kinds)

    @property
    def missing_required_check_kinds(self) -> tuple[WaveFiveReviewIndexCheckKind, ...]:
        """Return required review-index checks absent from this index."""

        covered = set(self.covered_check_kinds)
        return tuple(
            kind for kind in REQUIRED_REVIEW_INDEX_CHECK_KINDS if kind not in covered
        )

    @property
    def blocking_entry_ids(self) -> tuple[str, ...]:
        """Return entries that block index readiness."""

        return tuple(
            entry.entry_id for entry in self.entries if entry.blocks_index_readiness
        )

    @property
    def blocking_check_ids(self) -> tuple[str, ...]:
        """Return checks that block index readiness."""

        return tuple(
            check.check_id for check in self.checks if check.blocks_index_readiness
        )

    @property
    def unresolved_blocker_ids(self) -> tuple[str, ...]:
        """Return unresolved blocking index blockers."""

        return tuple(
            blocker.blocker_id for blocker in self.blockers
            if blocker.blocks_index_readiness
        )

    @property
    def has_required_entry_coverage(self) -> bool:
        """Return whether every locked index entry is represented."""

        return not self.missing_required_entry_kinds

    @property
    def has_required_check_coverage(self) -> bool:
        """Return whether every locked index check is represented."""

        return not self.missing_required_check_kinds

    @property
    def makes_no_forbidden_claims(self) -> bool:
        """Return whether index avoids forbidden promotion claims."""

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
    def blocks_index_readiness(self) -> bool:
        """Return whether any condition blocks review-index readiness."""

        return bool(
            self.missing_required_entry_kinds
            or self.missing_required_check_kinds
            or self.blocking_entry_ids
            or self.blocking_check_ids
            or self.unresolved_blocker_ids
            or not self.makes_no_forbidden_claims
        )

    @property
    def ready_for_external_index_review(self) -> bool:
        """Return whether the index can enter external review."""

        return (
            self.index_state
            in {
                WaveFiveReviewIndexState.INTERNAL_INDEX_READY,
                WaveFiveReviewIndexState.READY_FOR_EXTERNAL_INDEX_REVIEW,
                WaveFiveReviewIndexState.UNDER_EXTERNAL_INDEX_REVIEW,
            }
            and self.has_required_entry_coverage
            and self.has_required_check_coverage
            and not self.blocking_entry_ids
            and not self.blocking_check_ids
            and not self.unresolved_blocker_ids
            and self.makes_no_forbidden_claims
        )

    @property
    def externally_reviewed_with_boundaries(self) -> bool:
        """Return whether external index review accepted boundaries."""

        return (
            self.index_state
            is WaveFiveReviewIndexState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
        )

    @property
    def index_bundle_digest(self) -> str:
        """Return deterministic digest across indexed entry digests."""

        payload = {entry.entry_id: entry.digest for entry in self.entries}
        return _stable_sha256(payload)

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound into this index."""

        evidence_ids: list[str] = []
        seen: set[str] = set()
        for evidence_id in self._iter_evidence_ids():
            if evidence_id not in seen:
                evidence_ids.append(evidence_id)
                seen.add(evidence_id)
        return tuple(evidence_ids)

    def to_artifact_ref(self) -> WaveFiveArtifactRef:
        """Return this index as a Wave 5 traceability artifact."""

        decision = WaveFiveArtifactDecision.NEEDS_EXTERNAL_EVIDENCE
        status = WaveFiveValidationStatus.MISSING_EXTERNAL_EVIDENCE
        authority = WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
        if self.externally_reviewed_with_boundaries:
            decision = WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
            status = WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
        elif self.ready_for_external_index_review:
            decision = WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
            status = WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
        elif self.blocks_index_readiness:
            decision = WaveFiveArtifactDecision.BLOCKED
            status = WaveFiveValidationStatus.REJECTED
            authority = WaveFiveAuthorityState.BLOCKED
        return WaveFiveArtifactRef(
            artifact_id=self.index_id,
            kind=WaveFiveArtifactKind.ECOSYSTEM_TRACEABILITY_MAP,
            capability_area=WaveFiveCapabilityArea.ECOSYSTEM_TRACEABILITY,
            source_system=self.source_system,
            summary=self.title,
            produced_by_engine_id="wave5-review-index-engine",
            produced_by_agent_role_id="review-index-integrator",
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
            "bounded_declaration_artifact_id": self.bounded_declaration_artifact_id,
            "checks": [check.canonical_payload() for check in self.checks],
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_independent_validation": self.claims_independent_validation,
            "claims_production_ready": self.claims_production_ready,
            "entries": [entry.canonical_payload() for entry in self.entries],
            "grants_execution_authority": self.grants_execution_authority,
            "index_bundle_digest": self.index_bundle_digest,
            "index_id": self.index_id,
            "index_state": self.index_state.value,
            "notes": list(self.notes),
            "protocol_ids": list(self.protocol_ids),
            "release_manifest_artifact_id": self.release_manifest_artifact_id,
            "reviewer_ids": list(self.reviewer_ids),
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "title": self.title,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this index."""

        return _stable_sha256(self.canonical_payload())

    def _iter_evidence_ids(self) -> Iterable[str]:
        """Yield evidence ids in deterministic review-index order."""

        for entry in self.entries:
            yield from entry.evidence_ids
        for check in self.checks:
            yield from check.evidence_ids
        for blocker in self.blockers:
            yield from blocker.evidence_ids

    def _validate_manifest_and_declaration_references(
        self, entries: tuple[WaveFiveReviewIndexEntry, ...]
    ) -> None:
        """Validate final manifest and declaration entries are referenced."""

        manifest_entries = tuple(
            entry for entry in entries
            if entry.entry_kind is WaveFiveReviewIndexEntryKind.RELEASE_MANIFEST
        )
        declaration_entries = tuple(
            entry for entry in entries
            if entry.entry_kind is WaveFiveReviewIndexEntryKind.BOUNDED_DECLARATION
        )
        if manifest_entries:
            if manifest_entries[0].artifact_id != self.release_manifest_artifact_id:
                raise ValueError(
                    "Review index release manifest reference must match entry."
                )
        if declaration_entries:
            if (
                declaration_entries[0].artifact_id
                != self.bounded_declaration_artifact_id
            ):
                raise ValueError(
                    "Review index bounded declaration reference must match entry."
                )


def required_review_index_entry_kinds() -> tuple[WaveFiveReviewIndexEntryKind, ...]:
    """Return locked review index entries required for Wave 5 review."""

    return REQUIRED_REVIEW_INDEX_ENTRY_KINDS


def required_review_index_check_kinds() -> tuple[WaveFiveReviewIndexCheckKind, ...]:
    """Return locked review index checks required for Wave 5 review."""

    return REQUIRED_REVIEW_INDEX_CHECK_KINDS


def safe_review_index_entry_statuses() -> tuple[WaveFiveReviewIndexEntryStatus, ...]:
    """Return index entry statuses that do not block review."""

    return SAFE_INDEX_ENTRY_STATUSES


def blocking_review_index_entry_statuses() -> tuple[
    WaveFiveReviewIndexEntryStatus, ...
]:
    """Return index entry statuses that block review."""

    return BLOCKING_INDEX_ENTRY_STATUSES


def external_index_review_source_systems() -> tuple[WaveFiveSourceSystem, ...]:
    """Return source systems allowed to assert external index review."""

    return EXTERNAL_INDEX_REVIEW_SOURCE_SYSTEMS


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
