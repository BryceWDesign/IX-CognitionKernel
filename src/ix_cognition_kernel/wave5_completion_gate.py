"""Wave 5 completion gate records.

Wave 5 needs one final programmatic gate that can say the review package is
complete enough to be handed to external reviewers while still preserving the
real claim boundary: this is not Wave 6, not AGI, not certification, not
production readiness, not independent validation, and not execution authority.
This module records final artifacts, completion checks, blockers, human signoff,
and deterministic fingerprints for that bounded completion state.
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

WAVE_FIVE_COMPLETION_ARTIFACT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-completion-artifact-v1"
)
WAVE_FIVE_COMPLETION_CHECK_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-completion-check-v1"
)
WAVE_FIVE_COMPLETION_BLOCKER_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-completion-blocker-v1"
)
WAVE_FIVE_COMPLETION_GATE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-completion-gate-v1"
)


class WaveFiveCompletionArtifactKind(StrEnum):
    """Final artifacts required before bounded Wave 5 completion."""

    REVIEW_INDEX = "review-index"
    BOUNDED_DECLARATION = "bounded-declaration"
    RELEASE_MANIFEST = "release-manifest"
    EVIDENCE_DOSSIER = "evidence-dossier"
    MATURITY_SCORECARD = "maturity-scorecard"
    EXTERNAL_REVIEW_PACKET = "external-review-packet"
    FALSIFICATION_LEDGER = "falsification-ledger"
    WAVE_SIX_READINESS_GATE = "wave-six-readiness-gate"
    REPEATABILITY_LEDGER = "repeatability-ledger"
    BLACKFOX_COMPATIBILITY_BRIDGE = "blackfox-compatibility-bridge"
    WORLDTWIN_SCENARIO_BRIDGE = "worldtwin-scenario-bridge"
    HUMAN_AUTHORITY_PROOF = "human-authority-proof"
    SAFE_REFUSAL_PROOF = "safe-refusal-proof"
    MEMORY_INTEGRITY_PROOF = "memory-integrity-proof"
    BENCHMARK_GAMING_AUDIT = "benchmark-gaming-audit"


class WaveFiveCompletionArtifactStatus(StrEnum):
    """Status of one final completion artifact."""

    COMPLETE = "complete"
    COMPLETE_WITH_LIMITS = "complete-with-limits"
    NEEDS_EXTERNAL_EVIDENCE = "needs-external-evidence"
    DISPUTED = "disputed"
    BLOCKED = "blocked"
    MISSING = "missing"


class WaveFiveCompletionCheckKind(StrEnum):
    """Checks required before the Wave 5 package can be called complete."""

    REQUIRED_ARTIFACTS_PRESENT = "required-artifacts-present"
    FINAL_DIGESTS_PRESENT = "final-digests-present"
    FINAL_EVIDENCE_PRESENT = "final-evidence-present"
    REVIEW_INDEX_BOUND = "review-index-bound"
    BOUNDED_DECLARATION_BOUND = "bounded-declaration-bound"
    RELEASE_MANIFEST_BOUND = "release-manifest-bound"
    COMPLETION_BLOCKERS_VISIBLE = "completion-blockers-visible"
    CLAIM_BOUNDARIES_PRESERVED = "claim-boundaries-preserved"
    HUMAN_AUTHORITY_PRESERVED = "human-authority-preserved"
    HUMAN_SIGNOFF_PRESENT = "human-signoff-present"
    NO_WAVE_SIX_PROMOTION = "no-wave-six-promotion"
    NO_AGI_OR_CERTIFICATION_CLAIM = "no-agi-or-certification-claim"
    NO_EXECUTION_AUTHORITY = "no-execution-authority"
    NO_SELF_CLAIMED_INDEPENDENT_VALIDATION = (
        "no-self-claimed-independent-validation"
    )


class WaveFiveCompletionCheckResult(StrEnum):
    """Observed result of one completion-gate check."""

    PASSED = "passed"
    PASSED_WITH_LIMITS = "passed-with-limits"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    FAILED = "failed"


class WaveFiveCompletionBlockerKind(StrEnum):
    """Blockers that prevent bounded Wave 5 completion."""

    MISSING_FINAL_ARTIFACT = "missing-final-artifact"
    INVALID_FINAL_DIGEST = "invalid-final-digest"
    MISSING_FINAL_EVIDENCE = "missing-final-evidence"
    REVIEW_INDEX_GAP = "review-index-gap"
    DECLARATION_GAP = "declaration-gap"
    RELEASE_MANIFEST_GAP = "release-manifest-gap"
    FAILED_FALSIFICATION = "failed-falsification"
    UNRESOLVED_DISPUTE = "unresolved-dispute"
    HUMAN_SIGNOFF_GAP = "human-signoff-gap"
    CLAIM_BOUNDARY_GAP = "claim-boundary-gap"
    WAVE_SIX_OVERCLAIM = "wave-six-overclaim"


class WaveFiveCompletionBlockerSeverity(StrEnum):
    """Severity of a completion blocker."""

    INFORMATIONAL = "informational"
    LIMITATION = "limitation"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKING = "blocking"


class WaveFiveCompletionState(StrEnum):
    """Review state of the final bounded Wave 5 completion gate."""

    INTERNAL_COMPLETION_READY = "internal-completion-ready"
    READY_FOR_EXTERNAL_COMPLETION_REVIEW = "ready-for-external-completion-review"
    UNDER_EXTERNAL_COMPLETION_REVIEW = "under-external-completion-review"
    EXTERNALLY_REVIEWED_WITH_BOUNDARIES = "externally-reviewed-with-boundaries"
    BLOCKED_BY_COMPLETION_GAP = "blocked-by-completion-gap"


SAFE_COMPLETION_ARTIFACT_STATUSES: tuple[WaveFiveCompletionArtifactStatus, ...] = (
    WaveFiveCompletionArtifactStatus.COMPLETE,
    WaveFiveCompletionArtifactStatus.COMPLETE_WITH_LIMITS,
)

BLOCKING_COMPLETION_ARTIFACT_STATUSES: tuple[
    WaveFiveCompletionArtifactStatus, ...
] = (
    WaveFiveCompletionArtifactStatus.NEEDS_EXTERNAL_EVIDENCE,
    WaveFiveCompletionArtifactStatus.DISPUTED,
    WaveFiveCompletionArtifactStatus.BLOCKED,
    WaveFiveCompletionArtifactStatus.MISSING,
)

REQUIRED_COMPLETION_ARTIFACT_KINDS: tuple[WaveFiveCompletionArtifactKind, ...] = (
    WaveFiveCompletionArtifactKind.REVIEW_INDEX,
    WaveFiveCompletionArtifactKind.BOUNDED_DECLARATION,
    WaveFiveCompletionArtifactKind.RELEASE_MANIFEST,
    WaveFiveCompletionArtifactKind.EVIDENCE_DOSSIER,
    WaveFiveCompletionArtifactKind.MATURITY_SCORECARD,
    WaveFiveCompletionArtifactKind.EXTERNAL_REVIEW_PACKET,
    WaveFiveCompletionArtifactKind.FALSIFICATION_LEDGER,
    WaveFiveCompletionArtifactKind.WAVE_SIX_READINESS_GATE,
    WaveFiveCompletionArtifactKind.REPEATABILITY_LEDGER,
    WaveFiveCompletionArtifactKind.BLACKFOX_COMPATIBILITY_BRIDGE,
    WaveFiveCompletionArtifactKind.WORLDTWIN_SCENARIO_BRIDGE,
    WaveFiveCompletionArtifactKind.HUMAN_AUTHORITY_PROOF,
    WaveFiveCompletionArtifactKind.SAFE_REFUSAL_PROOF,
    WaveFiveCompletionArtifactKind.MEMORY_INTEGRITY_PROOF,
    WaveFiveCompletionArtifactKind.BENCHMARK_GAMING_AUDIT,
)

REQUIRED_COMPLETION_CHECK_KINDS: tuple[WaveFiveCompletionCheckKind, ...] = (
    WaveFiveCompletionCheckKind.REQUIRED_ARTIFACTS_PRESENT,
    WaveFiveCompletionCheckKind.FINAL_DIGESTS_PRESENT,
    WaveFiveCompletionCheckKind.FINAL_EVIDENCE_PRESENT,
    WaveFiveCompletionCheckKind.REVIEW_INDEX_BOUND,
    WaveFiveCompletionCheckKind.BOUNDED_DECLARATION_BOUND,
    WaveFiveCompletionCheckKind.RELEASE_MANIFEST_BOUND,
    WaveFiveCompletionCheckKind.COMPLETION_BLOCKERS_VISIBLE,
    WaveFiveCompletionCheckKind.CLAIM_BOUNDARIES_PRESERVED,
    WaveFiveCompletionCheckKind.HUMAN_AUTHORITY_PRESERVED,
    WaveFiveCompletionCheckKind.HUMAN_SIGNOFF_PRESENT,
    WaveFiveCompletionCheckKind.NO_WAVE_SIX_PROMOTION,
    WaveFiveCompletionCheckKind.NO_AGI_OR_CERTIFICATION_CLAIM,
    WaveFiveCompletionCheckKind.NO_EXECUTION_AUTHORITY,
    WaveFiveCompletionCheckKind.NO_SELF_CLAIMED_INDEPENDENT_VALIDATION,
)

EXTERNAL_COMPLETION_REVIEW_SOURCE_SYSTEMS: tuple[WaveFiveSourceSystem, ...] = (
    WaveFiveSourceSystem.EXTERNAL_REVIEW,
    WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
    WaveFiveSourceSystem.HUMAN_REVIEW,
)


@dataclass(frozen=True, slots=True)
class WaveFiveCompletionArtifactRecord:
    """One final artifact required by the bounded Wave 5 completion gate."""

    artifact_id: str
    artifact_kind: WaveFiveCompletionArtifactKind
    status: WaveFiveCompletionArtifactStatus
    digest: str
    evidence_ids: tuple[str, ...]
    source_system: WaveFiveSourceSystem
    summary: str
    limitations: tuple[str, ...] = ()
    blocker_ids: tuple[str, ...] = ()
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    schema_version: str = WAVE_FIVE_COMPLETION_ARTIFACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate final artifact digest, evidence, status, and boundaries."""

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
            self, "blocker_ids", _unique_text(self.blocker_ids, label="blocker_id")
        )
        object.__setattr__(
            self,
            "claim_boundaries",
            _unique_enum(self.claim_boundaries, label="claim boundary"),
        )
        if not self.evidence_ids:
            raise ValueError("Completion artifact records require evidence ids.")
        if self.status is WaveFiveCompletionArtifactStatus.COMPLETE_WITH_LIMITS:
            if not self.limitations:
                raise ValueError("Limited completion artifacts require limitations.")
        if self.status in BLOCKING_COMPLETION_ARTIFACT_STATUSES:
            if not self.blocker_ids:
                raise ValueError("Blocking completion artifacts require blocker ids.")
        missing = tuple(
            boundary
            for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
            if boundary not in self.claim_boundaries
        )
        if missing:
            raise ValueError(
                "Completion artifact records must preserve claim boundary: "
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
    def blocks_completion(self) -> bool:
        """Return whether this artifact blocks bounded completion."""

        return self.status in BLOCKING_COMPLETION_ARTIFACT_STATUSES

    @property
    def complete_with_boundaries(self) -> bool:
        """Return whether artifact is complete without promotion."""

        return self.status in SAFE_COMPLETION_ARTIFACT_STATUSES and bool(
            self.evidence_ids
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "artifact_id": self.artifact_id,
            "artifact_kind": self.artifact_kind.value,
            "blocker_ids": list(self.blocker_ids),
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "complete_with_boundaries": self.complete_with_boundaries,
            "digest": self.digest,
            "evidence_ids": list(self.evidence_ids),
            "limitations": list(self.limitations),
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "status": self.status.value,
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveCompletionCheck:
    """One final check over the bounded Wave 5 completion package."""

    check_id: str
    check_kind: WaveFiveCompletionCheckKind
    result: WaveFiveCompletionCheckResult
    description: str
    evidence_ids: tuple[str, ...]
    blocking: bool = True
    schema_version: str = WAVE_FIVE_COMPLETION_CHECK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate completion-check identity and evidence."""

        object.__setattr__(self, "check_id", _text(self.check_id, "check_id"))
        object.__setattr__(self, "description", _text(self.description, "description"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Completion checks require evidence ids.")
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
            WaveFiveCompletionCheckResult.PASSED,
            WaveFiveCompletionCheckResult.PASSED_WITH_LIMITS,
        }

    @property
    def blocks_completion(self) -> bool:
        """Return whether this check blocks bounded completion."""

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
class WaveFiveCompletionBlocker:
    """Visible blocker retained before bounded Wave 5 completion."""

    blocker_id: str
    blocker_kind: WaveFiveCompletionBlockerKind
    severity: WaveFiveCompletionBlockerSeverity
    artifact_kind: WaveFiveCompletionArtifactKind
    description: str
    mitigation: str
    evidence_ids: tuple[str, ...]
    resolved: bool = False
    schema_version: str = WAVE_FIVE_COMPLETION_BLOCKER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate completion-blocker evidence and mitigation."""

        object.__setattr__(self, "blocker_id", _text(self.blocker_id, "blocker_id"))
        object.__setattr__(self, "description", _text(self.description, "description"))
        object.__setattr__(self, "mitigation", _text(self.mitigation, "mitigation"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Completion blockers require evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def blocker_key(self) -> str:
        """Return deterministic blocker key."""

        return self.blocker_id

    @property
    def blocks_completion(self) -> bool:
        """Return whether this blocker prevents bounded completion."""

        return (
            self.severity is WaveFiveCompletionBlockerSeverity.BLOCKING
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
class WaveFiveCompletionGate:
    """Final fail-closed bounded Wave 5 completion gate."""

    completion_id: str
    title: str
    source_system: WaveFiveSourceSystem
    completion_state: WaveFiveCompletionState
    artifacts: tuple[WaveFiveCompletionArtifactRecord, ...]
    checks: tuple[WaveFiveCompletionCheck, ...]
    blockers: tuple[WaveFiveCompletionBlocker, ...]
    review_index_artifact_id: str
    bounded_declaration_artifact_id: str
    protocol_ids: tuple[str, ...]
    reviewer_ids: tuple[str, ...] = ()
    human_signoff_ids: tuple[str, ...] = ()
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
    schema_version: str = WAVE_FIVE_COMPLETION_GATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate completion coverage and anti-overclaim boundaries."""

        object.__setattr__(
            self, "completion_id", _text(self.completion_id, "completion_id")
        )
        object.__setattr__(self, "title", _text(self.title, "title"))
        object.__setattr__(
            self,
            "review_index_artifact_id",
            _text(self.review_index_artifact_id, "review_index_artifact_id"),
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
            raise ValueError("Completion gates cannot promote to Wave 6.")
        if self.claims_agi:
            raise ValueError("Completion gates cannot claim AGI.")
        if self.grants_execution_authority:
            raise ValueError("Completion gates cannot grant execution authority.")
        if self.claims_production_ready:
            raise ValueError("Completion gates cannot claim production readiness.")
        if self.claims_certified:
            raise ValueError("Completion gates cannot claim certification.")
        if self.claims_independent_validation:
            raise ValueError(
                "Completion gates cannot self-claim independent validation."
            )
        artifacts = tuple(sorted(self.artifacts, key=lambda item: item.artifact_key))
        checks = tuple(sorted(self.checks, key=lambda item: item.check_key))
        blockers = tuple(sorted(self.blockers, key=lambda item: item.blocker_key))
        if not artifacts:
            raise ValueError("Completion gates require artifacts.")
        if not checks:
            raise ValueError("Completion gates require checks.")
        _unique_values((item.artifact_id for item in artifacts), label="artifact_id")
        _unique_values(
            (item.artifact_kind for item in artifacts), label="artifact kind"
        )
        _unique_values((item.check_id for item in checks), label="check_id")
        _unique_values((item.blocker_id for item in blockers), label="blocker_id")
        object.__setattr__(self, "artifacts", artifacts)
        object.__setattr__(self, "checks", checks)
        object.__setattr__(self, "blockers", blockers)
        self._validate_required_final_references(artifacts)
        object.__setattr__(
            self, "protocol_ids", _unique_text(self.protocol_ids, label="protocol_id")
        )
        if not self.protocol_ids:
            raise ValueError("Completion gates require protocol ids.")
        object.__setattr__(
            self, "reviewer_ids", _unique_text(self.reviewer_ids, label="reviewer_id")
        )
        object.__setattr__(
            self,
            "human_signoff_ids",
            _unique_text(self.human_signoff_ids, label="human_signoff_id"),
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
                "Completion gates must preserve claim boundary: "
                f"{missing_boundaries[0].value}"
            )
        object.__setattr__(self, "notes", _unique_text(self.notes, label="note"))
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.externally_reviewed_with_boundaries:
            if self.source_system not in EXTERNAL_COMPLETION_REVIEW_SOURCE_SYSTEMS:
                raise ValueError(
                    "Externally reviewed completion gates require external source."
                )
            if not self.reviewer_ids:
                raise ValueError(
                    "Externally reviewed completion gates require reviewer ids."
                )
            if self.blocks_completion:
                raise ValueError(
                    "Externally reviewed completion gates cannot contain blockers."
                )

    @property
    def covered_artifact_kinds(self) -> tuple[WaveFiveCompletionArtifactKind, ...]:
        """Return final artifact kinds represented in this gate."""

        return tuple(artifact.artifact_kind for artifact in self.artifacts)

    @property
    def missing_required_artifact_kinds(
        self,
    ) -> tuple[WaveFiveCompletionArtifactKind, ...]:
        """Return final required artifacts absent from this gate."""

        covered = set(self.covered_artifact_kinds)
        return tuple(
            kind for kind in REQUIRED_COMPLETION_ARTIFACT_KINDS if kind not in covered
        )

    @property
    def covered_check_kinds(self) -> tuple[WaveFiveCompletionCheckKind, ...]:
        """Return completion check kinds represented in this gate."""

        kinds: list[WaveFiveCompletionCheckKind] = []
        seen: set[WaveFiveCompletionCheckKind] = set()
        for check in self.checks:
            if check.check_kind not in seen:
                kinds.append(check.check_kind)
                seen.add(check.check_kind)
        return tuple(kinds)

    @property
    def missing_required_check_kinds(self) -> tuple[WaveFiveCompletionCheckKind, ...]:
        """Return required completion checks absent from this gate."""

        covered = set(self.covered_check_kinds)
        return tuple(
            kind for kind in REQUIRED_COMPLETION_CHECK_KINDS if kind not in covered
        )

    @property
    def blocking_artifact_ids(self) -> tuple[str, ...]:
        """Return final artifacts that block bounded completion."""

        return tuple(
            artifact.artifact_id for artifact in self.artifacts
            if artifact.blocks_completion
        )

    @property
    def blocking_check_ids(self) -> tuple[str, ...]:
        """Return checks that block bounded completion."""

        return tuple(check.check_id for check in self.checks if check.blocks_completion)

    @property
    def unresolved_blocker_ids(self) -> tuple[str, ...]:
        """Return unresolved blocking completion blockers."""

        return tuple(
            blocker.blocker_id for blocker in self.blockers
            if blocker.blocks_completion
        )

    @property
    def has_required_artifact_coverage(self) -> bool:
        """Return whether every locked final artifact is represented."""

        return not self.missing_required_artifact_kinds

    @property
    def has_required_check_coverage(self) -> bool:
        """Return whether every locked completion check is represented."""

        return not self.missing_required_check_kinds

    @property
    def has_human_signoff(self) -> bool:
        """Return whether at least one human signoff is attached."""

        return bool(self.human_signoff_ids)

    @property
    def makes_no_forbidden_claims(self) -> bool:
        """Return whether completion gate avoids forbidden promotion claims."""

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
    def blocks_completion(self) -> bool:
        """Return whether any condition blocks bounded Wave 5 completion."""

        return bool(
            self.missing_required_artifact_kinds
            or self.missing_required_check_kinds
            or self.blocking_artifact_ids
            or self.blocking_check_ids
            or self.unresolved_blocker_ids
            or not self.has_human_signoff
            or not self.makes_no_forbidden_claims
        )

    @property
    def ready_for_external_completion_review(self) -> bool:
        """Return whether final Wave 5 package can enter external review."""

        return (
            self.completion_state
            in {
                WaveFiveCompletionState.INTERNAL_COMPLETION_READY,
                WaveFiveCompletionState.READY_FOR_EXTERNAL_COMPLETION_REVIEW,
                WaveFiveCompletionState.UNDER_EXTERNAL_COMPLETION_REVIEW,
            }
            and self.has_required_artifact_coverage
            and self.has_required_check_coverage
            and not self.blocking_artifact_ids
            and not self.blocking_check_ids
            and not self.unresolved_blocker_ids
            and self.has_human_signoff
            and self.makes_no_forbidden_claims
        )

    @property
    def externally_reviewed_with_boundaries(self) -> bool:
        """Return whether external completion review accepted boundaries."""

        return (
            self.completion_state
            is WaveFiveCompletionState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
        )

    @property
    def completion_bundle_digest(self) -> str:
        """Return deterministic digest across final artifact digests."""

        payload = {artifact.artifact_id: artifact.digest for artifact in self.artifacts}
        return _stable_sha256(payload)

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound into this completion gate."""

        evidence_ids: list[str] = []
        seen: set[str] = set()
        for evidence_id in self._iter_evidence_ids():
            if evidence_id not in seen:
                evidence_ids.append(evidence_id)
                seen.add(evidence_id)
        return tuple(evidence_ids)

    def to_artifact_ref(self) -> WaveFiveArtifactRef:
        """Return this completion gate as a Wave 5 traceability artifact."""

        decision = WaveFiveArtifactDecision.NEEDS_EXTERNAL_EVIDENCE
        status = WaveFiveValidationStatus.MISSING_EXTERNAL_EVIDENCE
        authority = WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
        if self.externally_reviewed_with_boundaries:
            decision = WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
            status = WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
        elif self.ready_for_external_completion_review:
            decision = WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
            status = WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
        elif self.blocks_completion:
            decision = WaveFiveArtifactDecision.BLOCKED
            status = WaveFiveValidationStatus.REJECTED
            authority = WaveFiveAuthorityState.BLOCKED
        return WaveFiveArtifactRef(
            artifact_id=self.completion_id,
            kind=WaveFiveArtifactKind.ECOSYSTEM_TRACEABILITY_MAP,
            capability_area=WaveFiveCapabilityArea.ECOSYSTEM_TRACEABILITY,
            source_system=self.source_system,
            summary=self.title,
            produced_by_engine_id="wave5-completion-gate-engine",
            produced_by_agent_role_id="completion-gate-reviewer",
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=authority,
            validation_status=status,
            claim_boundaries=self.claim_boundaries,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "artifacts": [item.canonical_payload() for item in self.artifacts],
            "attempted_wave_six_promotion": self.attempted_wave_six_promotion,
            "blockers": [item.canonical_payload() for item in self.blockers],
            "bounded_declaration_artifact_id": self.bounded_declaration_artifact_id,
            "checks": [item.canonical_payload() for item in self.checks],
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_independent_validation": self.claims_independent_validation,
            "claims_production_ready": self.claims_production_ready,
            "completion_bundle_digest": self.completion_bundle_digest,
            "completion_id": self.completion_id,
            "completion_state": self.completion_state.value,
            "grants_execution_authority": self.grants_execution_authority,
            "human_signoff_ids": list(self.human_signoff_ids),
            "notes": list(self.notes),
            "protocol_ids": list(self.protocol_ids),
            "review_index_artifact_id": self.review_index_artifact_id,
            "reviewer_ids": list(self.reviewer_ids),
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "title": self.title,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this completion gate."""

        return _stable_sha256(self.canonical_payload())

    def _iter_evidence_ids(self) -> Iterable[str]:
        """Yield evidence ids in deterministic completion-gate order."""

        for artifact in self.artifacts:
            yield from artifact.evidence_ids
        for check in self.checks:
            yield from check.evidence_ids
        for blocker in self.blockers:
            yield from blocker.evidence_ids

    def _validate_required_final_references(
        self, artifacts: tuple[WaveFiveCompletionArtifactRecord, ...]
    ) -> None:
        """Validate final review index and declaration artifact references."""

        index_artifacts = tuple(
            artifact for artifact in artifacts
            if artifact.artifact_kind is WaveFiveCompletionArtifactKind.REVIEW_INDEX
        )
        declaration_artifacts = tuple(
            artifact for artifact in artifacts
            if (
                artifact.artifact_kind
                is WaveFiveCompletionArtifactKind.BOUNDED_DECLARATION
            )
        )
        if index_artifacts:
            if index_artifacts[0].artifact_id != self.review_index_artifact_id:
                raise ValueError(
                    "Completion gate review index reference must match artifact."
                )
        if declaration_artifacts:
            if (
                declaration_artifacts[0].artifact_id
                != self.bounded_declaration_artifact_id
            ):
                raise ValueError(
                    "Completion gate bounded declaration reference must match artifact."
                )


def required_completion_artifact_kinds() -> tuple[WaveFiveCompletionArtifactKind, ...]:
    """Return locked final artifacts required for bounded Wave 5 completion."""

    return REQUIRED_COMPLETION_ARTIFACT_KINDS


def required_completion_check_kinds() -> tuple[WaveFiveCompletionCheckKind, ...]:
    """Return locked checks required for bounded Wave 5 completion."""

    return REQUIRED_COMPLETION_CHECK_KINDS


def safe_completion_artifact_statuses() -> tuple[
    WaveFiveCompletionArtifactStatus, ...
]:
    """Return final artifact statuses that do not block completion."""

    return SAFE_COMPLETION_ARTIFACT_STATUSES


def blocking_completion_artifact_statuses() -> tuple[
    WaveFiveCompletionArtifactStatus, ...
]:
    """Return final artifact statuses that block completion."""

    return BLOCKING_COMPLETION_ARTIFACT_STATUSES


def external_completion_review_source_systems() -> tuple[WaveFiveSourceSystem, ...]:
    """Return source systems allowed to assert external completion review."""

    return EXTERNAL_COMPLETION_REVIEW_SOURCE_SYSTEMS


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
