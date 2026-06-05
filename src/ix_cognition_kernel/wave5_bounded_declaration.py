"""Wave 5 bounded maturity declaration records.

Wave 5 needs a final declaration gate that can say the Wave 5 review package is
complete enough for bounded external scrutiny without changing the claim state.
This module records required declaration inputs, declaration checks, human-review
signoff, unresolved blockers, deterministic fingerprints, and anti-overclaim
controls. A passing declaration can identify a bounded Wave 5 review package; it
cannot declare Wave 6, AGI, production readiness, certification, independent
validation, or autonomous execution authority.
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

WAVE_FIVE_DECLARATION_INPUT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-declaration-input-v1"
)
WAVE_FIVE_DECLARATION_CHECK_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-declaration-check-v1"
)
WAVE_FIVE_DECLARATION_BLOCKER_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-declaration-blocker-v1"
)
WAVE_FIVE_BOUNDED_DECLARATION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave5-bounded-declaration-v1"
)


class WaveFiveDeclarationInputKind(StrEnum):
    """Inputs required before a bounded Wave 5 declaration can be reviewed."""

    RELEASE_MANIFEST = "release-manifest"
    EVIDENCE_DOSSIER = "evidence-dossier"
    MATURITY_SCORECARD = "maturity-scorecard"
    EXTERNAL_REVIEW_PACKET = "external-review-packet"
    FALSIFICATION_LEDGER = "falsification-ledger"
    WAVE_SIX_READINESS_GATE = "wave-six-readiness-gate"
    REPEATABILITY_LEDGER = "repeatability-ledger"
    SAFE_REFUSAL_PROOF = "safe-refusal-proof"
    HUMAN_AUTHORITY_PROOF = "human-authority-proof"
    MEMORY_INTEGRITY_PROOF = "memory-integrity-proof"
    BENCHMARK_GAMING_AUDIT = "benchmark-gaming-audit"
    ECOSYSTEM_BRIDGE_PROOFS = "ecosystem-bridge-proofs"


class WaveFiveDeclarationInputStatus(StrEnum):
    """Status of one declaration input."""

    REVIEWABLE = "reviewable"
    REVIEWABLE_WITH_LIMITS = "reviewable-with-limits"
    NEEDS_EXTERNAL_EVIDENCE = "needs-external-evidence"
    DISPUTED = "disputed"
    BLOCKED = "blocked"
    MISSING = "missing"


class WaveFiveDeclarationCheckKind(StrEnum):
    """Checks required for the bounded Wave 5 declaration gate."""

    REQUIRED_INPUTS_PRESENT = "required-inputs-present"
    INPUT_DIGESTS_PRESENT = "input-digests-present"
    EVIDENCE_IDS_PRESENT = "evidence-ids-present"
    RELEASE_MANIFEST_BOUND = "release-manifest-bound"
    SCORECARD_BOUND = "scorecard-bound"
    FALSIFICATION_LEDGER_BOUND = "falsification-ledger-bound"
    EXTERNAL_REVIEW_PACKET_BOUND = "external-review-packet-bound"
    CLAIM_BOUNDARIES_PRESERVED = "claim-boundaries-preserved"
    HUMAN_AUTHORITY_PRESERVED = "human-authority-preserved"
    NO_WAVE_SIX_PROMOTION = "no-wave-six-promotion"
    NO_AGI_OR_CERTIFICATION_CLAIM = "no-agi-or-certification-claim"
    NO_EXECUTION_AUTHORITY = "no-execution-authority"


class WaveFiveDeclarationCheckResult(StrEnum):
    """Observed result of one bounded declaration check."""

    PASSED = "passed"
    PASSED_WITH_LIMITS = "passed-with-limits"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    FAILED = "failed"


class WaveFiveDeclarationBlockerKind(StrEnum):
    """Blockers that prevent a bounded Wave 5 declaration."""

    MISSING_INPUT = "missing-input"
    INVALID_INPUT_DIGEST = "invalid-input-digest"
    UNRESOLVED_RELEASE_BLOCKER = "unresolved-release-blocker"
    FAILED_FALSIFICATION = "failed-falsification"
    DISPUTED_REVIEW_PACKET = "disputed-review-packet"
    SCORECARD_BELOW_THRESHOLD = "scorecard-below-threshold"
    AUTHORITY_GAP = "authority-gap"
    SAFE_REFUSAL_GAP = "safe-refusal-gap"
    CLAIM_BOUNDARY_GAP = "claim-boundary-gap"
    WAVE_SIX_OVERCLAIM = "wave-six-overclaim"


class WaveFiveDeclarationBlockerSeverity(StrEnum):
    """Severity of a declaration blocker."""

    INFORMATIONAL = "informational"
    LIMITATION = "limitation"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    BLOCKING = "blocking"


class WaveFiveBoundedDeclarationState(StrEnum):
    """Review state of a bounded Wave 5 declaration."""

    INTERNAL_DECLARATION_READY = "internal-declaration-ready"
    READY_FOR_EXTERNAL_DECLARATION_REVIEW = "ready-for-external-declaration-review"
    UNDER_EXTERNAL_DECLARATION_REVIEW = "under-external-declaration-review"
    EXTERNALLY_REVIEWED_WITH_BOUNDARIES = "externally-reviewed-with-boundaries"
    BLOCKED_BY_DECLARATION_GAP = "blocked-by-declaration-gap"


SAFE_DECLARATION_INPUT_STATUSES: tuple[WaveFiveDeclarationInputStatus, ...] = (
    WaveFiveDeclarationInputStatus.REVIEWABLE,
    WaveFiveDeclarationInputStatus.REVIEWABLE_WITH_LIMITS,
)

BLOCKING_DECLARATION_INPUT_STATUSES: tuple[WaveFiveDeclarationInputStatus, ...] = (
    WaveFiveDeclarationInputStatus.NEEDS_EXTERNAL_EVIDENCE,
    WaveFiveDeclarationInputStatus.DISPUTED,
    WaveFiveDeclarationInputStatus.BLOCKED,
    WaveFiveDeclarationInputStatus.MISSING,
)

REQUIRED_DECLARATION_INPUT_KINDS: tuple[WaveFiveDeclarationInputKind, ...] = (
    WaveFiveDeclarationInputKind.RELEASE_MANIFEST,
    WaveFiveDeclarationInputKind.EVIDENCE_DOSSIER,
    WaveFiveDeclarationInputKind.MATURITY_SCORECARD,
    WaveFiveDeclarationInputKind.EXTERNAL_REVIEW_PACKET,
    WaveFiveDeclarationInputKind.FALSIFICATION_LEDGER,
    WaveFiveDeclarationInputKind.WAVE_SIX_READINESS_GATE,
    WaveFiveDeclarationInputKind.REPEATABILITY_LEDGER,
    WaveFiveDeclarationInputKind.SAFE_REFUSAL_PROOF,
    WaveFiveDeclarationInputKind.HUMAN_AUTHORITY_PROOF,
    WaveFiveDeclarationInputKind.MEMORY_INTEGRITY_PROOF,
    WaveFiveDeclarationInputKind.BENCHMARK_GAMING_AUDIT,
    WaveFiveDeclarationInputKind.ECOSYSTEM_BRIDGE_PROOFS,
)

REQUIRED_DECLARATION_CHECK_KINDS: tuple[WaveFiveDeclarationCheckKind, ...] = (
    WaveFiveDeclarationCheckKind.REQUIRED_INPUTS_PRESENT,
    WaveFiveDeclarationCheckKind.INPUT_DIGESTS_PRESENT,
    WaveFiveDeclarationCheckKind.EVIDENCE_IDS_PRESENT,
    WaveFiveDeclarationCheckKind.RELEASE_MANIFEST_BOUND,
    WaveFiveDeclarationCheckKind.SCORECARD_BOUND,
    WaveFiveDeclarationCheckKind.FALSIFICATION_LEDGER_BOUND,
    WaveFiveDeclarationCheckKind.EXTERNAL_REVIEW_PACKET_BOUND,
    WaveFiveDeclarationCheckKind.CLAIM_BOUNDARIES_PRESERVED,
    WaveFiveDeclarationCheckKind.HUMAN_AUTHORITY_PRESERVED,
    WaveFiveDeclarationCheckKind.NO_WAVE_SIX_PROMOTION,
    WaveFiveDeclarationCheckKind.NO_AGI_OR_CERTIFICATION_CLAIM,
    WaveFiveDeclarationCheckKind.NO_EXECUTION_AUTHORITY,
)

EXTERNAL_DECLARATION_REVIEW_SOURCE_SYSTEMS: tuple[WaveFiveSourceSystem, ...] = (
    WaveFiveSourceSystem.EXTERNAL_REVIEW,
    WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
    WaveFiveSourceSystem.HUMAN_REVIEW,
)


@dataclass(frozen=True, slots=True)
class WaveFiveDeclarationInputRecord:
    """One input artifact bound into the bounded Wave 5 declaration."""

    input_id: str
    input_kind: WaveFiveDeclarationInputKind
    status: WaveFiveDeclarationInputStatus
    digest: str
    evidence_ids: tuple[str, ...]
    source_system: WaveFiveSourceSystem
    summary: str
    limitations: tuple[str, ...] = ()
    reviewer_ids: tuple[str, ...] = ()
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    )
    schema_version: str = WAVE_FIVE_DECLARATION_INPUT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate input digest, evidence, limitations, and boundaries."""

        object.__setattr__(self, "input_id", _text(self.input_id, "input_id"))
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
            raise ValueError("Declaration input records require evidence ids.")
        if (
            self.status is WaveFiveDeclarationInputStatus.REVIEWABLE_WITH_LIMITS
            and not self.limitations
        ):
            raise ValueError("Limited declaration inputs require limitations.")
        missing = tuple(
            boundary
            for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
            if boundary not in self.claim_boundaries
        )
        if missing:
            raise ValueError(
                "Declaration input records must preserve claim boundary: "
                f"{missing[0].value}"
            )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def input_key(self) -> str:
        """Return deterministic input key."""

        return self.input_id

    @property
    def blocks_declaration_readiness(self) -> bool:
        """Return whether this input blocks bounded declaration readiness."""

        return self.status in BLOCKING_DECLARATION_INPUT_STATUSES

    @property
    def reviewable_with_boundaries(self) -> bool:
        """Return whether this input is reviewable without promotion."""

        return self.status in SAFE_DECLARATION_INPUT_STATUSES and bool(
            self.evidence_ids
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "digest": self.digest,
            "evidence_ids": list(self.evidence_ids),
            "input_id": self.input_id,
            "input_kind": self.input_kind.value,
            "limitations": list(self.limitations),
            "reviewable_with_boundaries": self.reviewable_with_boundaries,
            "reviewer_ids": list(self.reviewer_ids),
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "status": self.status.value,
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveBoundedDeclarationCheck:
    """One check over the bounded Wave 5 declaration."""

    check_id: str
    check_kind: WaveFiveDeclarationCheckKind
    result: WaveFiveDeclarationCheckResult
    description: str
    evidence_ids: tuple[str, ...]
    blocking: bool = True
    schema_version: str = WAVE_FIVE_DECLARATION_CHECK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate declaration-check evidence."""

        object.__setattr__(self, "check_id", _text(self.check_id, "check_id"))
        object.__setattr__(self, "description", _text(self.description, "description"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Bounded declaration checks require evidence ids.")
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
            WaveFiveDeclarationCheckResult.PASSED,
            WaveFiveDeclarationCheckResult.PASSED_WITH_LIMITS,
        }

    @property
    def blocks_declaration_readiness(self) -> bool:
        """Return whether this check blocks declaration readiness."""

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
class WaveFiveBoundedDeclarationBlocker:
    """Visible blocker retained before any bounded declaration is accepted."""

    blocker_id: str
    blocker_kind: WaveFiveDeclarationBlockerKind
    severity: WaveFiveDeclarationBlockerSeverity
    input_kind: WaveFiveDeclarationInputKind
    description: str
    mitigation: str
    evidence_ids: tuple[str, ...]
    resolved: bool = False
    schema_version: str = WAVE_FIVE_DECLARATION_BLOCKER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate blocker evidence and mitigation."""

        object.__setattr__(self, "blocker_id", _text(self.blocker_id, "blocker_id"))
        object.__setattr__(self, "description", _text(self.description, "description"))
        object.__setattr__(self, "mitigation", _text(self.mitigation, "mitigation"))
        object.__setattr__(
            self, "evidence_ids", _unique_text(self.evidence_ids, label="evidence_id")
        )
        if not self.evidence_ids:
            raise ValueError("Bounded declaration blockers require evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def blocker_key(self) -> str:
        """Return deterministic blocker key."""

        return self.blocker_id

    @property
    def blocks_declaration_readiness(self) -> bool:
        """Return whether this blocker prevents bounded declaration review."""

        return (
            self.severity is WaveFiveDeclarationBlockerSeverity.BLOCKING
            and not self.resolved
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic export payload."""

        return {
            "blocker_id": self.blocker_id,
            "blocker_kind": self.blocker_kind.value,
            "description": self.description,
            "evidence_ids": list(self.evidence_ids),
            "input_kind": self.input_kind.value,
            "mitigation": self.mitigation,
            "resolved": self.resolved,
            "schema_version": self.schema_version,
            "severity": self.severity.value,
        }


@dataclass(frozen=True, slots=True)
class WaveFiveBoundedDeclaration:
    """Final bounded Wave 5 declaration gate."""

    declaration_id: str
    title: str
    source_system: WaveFiveSourceSystem
    declaration_state: WaveFiveBoundedDeclarationState
    inputs: tuple[WaveFiveDeclarationInputRecord, ...]
    checks: tuple[WaveFiveBoundedDeclarationCheck, ...]
    blockers: tuple[WaveFiveBoundedDeclarationBlocker, ...]
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
    schema_version: str = WAVE_FIVE_BOUNDED_DECLARATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate declaration completeness and anti-promotion boundaries."""

        object.__setattr__(
            self, "declaration_id", _text(self.declaration_id, "declaration_id")
        )
        object.__setattr__(self, "title", _text(self.title, "title"))
        if self.attempted_wave_six_promotion:
            raise ValueError("Bounded declarations cannot promote to Wave 6.")
        if self.claims_agi:
            raise ValueError("Bounded declarations cannot claim AGI.")
        if self.grants_execution_authority:
            raise ValueError("Bounded declarations cannot grant execution authority.")
        if self.claims_production_ready:
            raise ValueError("Bounded declarations cannot claim production readiness.")
        if self.claims_certified:
            raise ValueError("Bounded declarations cannot claim certification.")
        if self.claims_independent_validation:
            raise ValueError(
                "Bounded declarations cannot self-claim independent validation."
            )
        inputs = tuple(sorted(self.inputs, key=lambda item: item.input_key))
        checks = tuple(sorted(self.checks, key=lambda item: item.check_key))
        blockers = tuple(sorted(self.blockers, key=lambda item: item.blocker_key))
        if not inputs:
            raise ValueError("Bounded declarations require inputs.")
        if not checks:
            raise ValueError("Bounded declarations require checks.")
        _unique_values((item.input_id for item in inputs), label="input_id")
        _unique_values((item.input_kind for item in inputs), label="input kind")
        _unique_values((item.check_id for item in checks), label="check_id")
        _unique_values((item.blocker_id for item in blockers), label="blocker_id")
        object.__setattr__(self, "inputs", inputs)
        object.__setattr__(self, "checks", checks)
        object.__setattr__(self, "blockers", blockers)
        object.__setattr__(
            self, "protocol_ids", _unique_text(self.protocol_ids, label="protocol_id")
        )
        if not self.protocol_ids:
            raise ValueError("Bounded declarations require protocol ids.")
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
                "Bounded declarations must preserve claim boundary: "
                f"{missing_boundaries[0].value}"
            )
        object.__setattr__(self, "notes", _unique_text(self.notes, label="note"))
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.externally_reviewed_with_boundaries:
            if self.source_system not in EXTERNAL_DECLARATION_REVIEW_SOURCE_SYSTEMS:
                raise ValueError(
                    "Externally reviewed declarations require external source."
                )
            if not self.reviewer_ids:
                raise ValueError(
                    "Externally reviewed declarations require reviewer ids."
                )
            if self.blocks_declaration_readiness:
                raise ValueError(
                    "Externally reviewed declarations cannot contain blockers."
                )

    @property
    def covered_input_kinds(self) -> tuple[WaveFiveDeclarationInputKind, ...]:
        """Return declaration input kinds represented in this declaration."""

        return tuple(input_record.input_kind for input_record in self.inputs)

    @property
    def missing_required_input_kinds(
        self,
    ) -> tuple[WaveFiveDeclarationInputKind, ...]:
        """Return required declaration inputs absent from this declaration."""

        covered = set(self.covered_input_kinds)
        return tuple(
            kind for kind in REQUIRED_DECLARATION_INPUT_KINDS if kind not in covered
        )

    @property
    def covered_check_kinds(self) -> tuple[WaveFiveDeclarationCheckKind, ...]:
        """Return declaration check kinds represented in this declaration."""

        kinds: list[WaveFiveDeclarationCheckKind] = []
        seen: set[WaveFiveDeclarationCheckKind] = set()
        for check in self.checks:
            if check.check_kind not in seen:
                kinds.append(check.check_kind)
                seen.add(check.check_kind)
        return tuple(kinds)

    @property
    def missing_required_check_kinds(self) -> tuple[WaveFiveDeclarationCheckKind, ...]:
        """Return required declaration checks absent from this declaration."""

        covered = set(self.covered_check_kinds)
        return tuple(
            kind for kind in REQUIRED_DECLARATION_CHECK_KINDS if kind not in covered
        )

    @property
    def blocking_input_ids(self) -> tuple[str, ...]:
        """Return declaration inputs that block declaration readiness."""

        return tuple(
            item.input_id for item in self.inputs if item.blocks_declaration_readiness
        )

    @property
    def blocking_check_ids(self) -> tuple[str, ...]:
        """Return declaration checks that block readiness."""

        return tuple(
            check.check_id
            for check in self.checks
            if check.blocks_declaration_readiness
        )

    @property
    def unresolved_blocker_ids(self) -> tuple[str, ...]:
        """Return unresolved blocking declaration blockers."""

        return tuple(
            blocker.blocker_id
            for blocker in self.blockers
            if blocker.blocks_declaration_readiness
        )

    @property
    def has_required_input_coverage(self) -> bool:
        """Return whether every locked declaration input is represented."""

        return not self.missing_required_input_kinds

    @property
    def has_required_check_coverage(self) -> bool:
        """Return whether every locked declaration check is represented."""

        return not self.missing_required_check_kinds

    @property
    def has_human_signoff(self) -> bool:
        """Return whether at least one human signoff is recorded."""

        return bool(self.human_signoff_ids)

    @property
    def makes_no_forbidden_claims(self) -> bool:
        """Return whether declaration avoids forbidden promotion claims."""

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
    def blocks_declaration_readiness(self) -> bool:
        """Return whether any condition blocks bounded declaration review."""

        return bool(
            self.missing_required_input_kinds
            or self.missing_required_check_kinds
            or self.blocking_input_ids
            or self.blocking_check_ids
            or self.unresolved_blocker_ids
            or not self.has_human_signoff
            or not self.makes_no_forbidden_claims
        )

    @property
    def ready_for_external_declaration_review(self) -> bool:
        """Return whether declaration can enter external review."""

        return (
            self.declaration_state
            in {
                WaveFiveBoundedDeclarationState.INTERNAL_DECLARATION_READY,
                WaveFiveBoundedDeclarationState.READY_FOR_EXTERNAL_DECLARATION_REVIEW,
                WaveFiveBoundedDeclarationState.UNDER_EXTERNAL_DECLARATION_REVIEW,
            }
            and self.has_required_input_coverage
            and self.has_required_check_coverage
            and not self.blocking_input_ids
            and not self.blocking_check_ids
            and not self.unresolved_blocker_ids
            and self.has_human_signoff
            and self.makes_no_forbidden_claims
        )

    @property
    def externally_reviewed_with_boundaries(self) -> bool:
        """Return whether external declaration review accepted boundaries."""

        return (
            self.declaration_state
            is WaveFiveBoundedDeclarationState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
        )

    @property
    def declaration_bundle_digest(self) -> str:
        """Return deterministic digest across declaration input digests."""

        payload = {item.input_id: item.digest for item in self.inputs}
        return _stable_sha256(payload)

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return all evidence ids bound into this declaration."""

        evidence_ids: list[str] = []
        seen: set[str] = set()
        for evidence_id in self._iter_evidence_ids():
            if evidence_id not in seen:
                evidence_ids.append(evidence_id)
                seen.add(evidence_id)
        return tuple(evidence_ids)

    def to_artifact_ref(self) -> WaveFiveArtifactRef:
        """Return this declaration as a Wave 5 traceability artifact."""

        decision = WaveFiveArtifactDecision.NEEDS_EXTERNAL_EVIDENCE
        status = WaveFiveValidationStatus.MISSING_EXTERNAL_EVIDENCE
        authority = WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
        if self.externally_reviewed_with_boundaries:
            decision = WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
            status = WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
        elif self.ready_for_external_declaration_review:
            decision = WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
            status = WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
        elif self.blocks_declaration_readiness:
            decision = WaveFiveArtifactDecision.BLOCKED
            status = WaveFiveValidationStatus.REJECTED
            authority = WaveFiveAuthorityState.BLOCKED
        return WaveFiveArtifactRef(
            artifact_id=self.declaration_id,
            kind=WaveFiveArtifactKind.ECOSYSTEM_TRACEABILITY_MAP,
            capability_area=WaveFiveCapabilityArea.ECOSYSTEM_TRACEABILITY,
            source_system=self.source_system,
            summary=self.title,
            produced_by_engine_id="wave5-bounded-declaration-engine",
            produced_by_agent_role_id="bounded-declaration-reviewer",
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
            "checks": [check.canonical_payload() for check in self.checks],
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_independent_validation": self.claims_independent_validation,
            "claims_production_ready": self.claims_production_ready,
            "declaration_bundle_digest": self.declaration_bundle_digest,
            "declaration_id": self.declaration_id,
            "declaration_state": self.declaration_state.value,
            "grants_execution_authority": self.grants_execution_authority,
            "human_signoff_ids": list(self.human_signoff_ids),
            "inputs": [item.canonical_payload() for item in self.inputs],
            "notes": list(self.notes),
            "protocol_ids": list(self.protocol_ids),
            "reviewer_ids": list(self.reviewer_ids),
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "title": self.title,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this declaration."""

        return _stable_sha256(self.canonical_payload())

    def _iter_evidence_ids(self) -> Iterable[str]:
        """Yield evidence ids in deterministic declaration traversal order."""

        for item in self.inputs:
            yield from item.evidence_ids
        for check in self.checks:
            yield from check.evidence_ids
        for blocker in self.blockers:
            yield from blocker.evidence_ids


def required_declaration_input_kinds() -> tuple[WaveFiveDeclarationInputKind, ...]:
    """Return locked declaration inputs required for Wave 5 declaration."""

    return REQUIRED_DECLARATION_INPUT_KINDS


def required_declaration_check_kinds() -> tuple[WaveFiveDeclarationCheckKind, ...]:
    """Return locked declaration checks required for Wave 5 declaration."""

    return REQUIRED_DECLARATION_CHECK_KINDS


def safe_declaration_input_statuses() -> tuple[WaveFiveDeclarationInputStatus, ...]:
    """Return declaration input statuses that do not block review."""

    return SAFE_DECLARATION_INPUT_STATUSES


def blocking_declaration_input_statuses() -> tuple[WaveFiveDeclarationInputStatus, ...]:
    """Return declaration input statuses that block review."""

    return BLOCKING_DECLARATION_INPUT_STATUSES


def external_declaration_review_source_systems() -> tuple[WaveFiveSourceSystem, ...]:
    """Return source systems allowed to assert external declaration review."""

    return EXTERNAL_DECLARATION_REVIEW_SOURCE_SYSTEMS


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
