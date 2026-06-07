"""Wave 6 evidence package aggregator.

Wave 6 cannot be a pile of unrelated ledgers. This module joins the core
measured-cognition evidence surfaces into one deterministic package status while
keeping the integration clean: upstream ledgers remain independently testable,
and this package only reads their review states and fingerprints. It does not
execute donor repos or claim AGI.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, TypeVar

T = TypeVar("T")
E = TypeVar("E", bound=StrEnum)


class RealityCorrectionLedgerLike(Protocol):
    """Structural protocol for the reality-correction ledger."""

    @property
    def blocking_record_ids(self) -> tuple[str, ...]:
        """Return correction records that block interpretation."""

    @property
    def ready_for_wave_six_memory_update(self) -> bool:
        """Return whether reality correction can support memory update."""

    def fingerprint(self) -> str:
        """Return deterministic ledger fingerprint."""


class FutureReasoningLedgerLike(Protocol):
    """Structural protocol for the future-reasoning proof ledger."""

    @property
    def blocked_proof_ids(self) -> tuple[str, ...]:
        """Return future-reasoning proofs that block interpretation."""

    @property
    def ready_for_wave_six_review(self) -> bool:
        """Return whether future-reasoning proofs can support review."""

    def fingerprint(self) -> str:
        """Return deterministic ledger fingerprint."""


class TransferNoveltyLedgerLike(Protocol):
    """Structural protocol for the transfer-novelty ledger."""

    @property
    def blocked_record_ids(self) -> tuple[str, ...]:
        """Return transfer records that block interpretation."""

    @property
    def ready_for_wave_six_review(self) -> bool:
        """Return whether transfer evidence can support review."""

    def fingerprint(self) -> str:
        """Return deterministic ledger fingerprint."""


class FalsificationLedgerLike(Protocol):
    """Structural protocol for the falsification ledger."""

    @property
    def blocking_result_ids(self) -> tuple[str, ...]:
        """Return falsification results that block interpretation."""

    @property
    def ready_for_wave_six_review(self) -> bool:
        """Return whether falsification evidence can support review."""

    def fingerprint(self) -> str:
        """Return deterministic ledger fingerprint."""


class HumanReviewDocketLike(Protocol):
    """Structural protocol for the human-review docket."""

    @property
    def blocks_wave_six_claim(self) -> bool:
        """Return whether human review blocks interpretation."""

    @property
    def approves_bounded_wave_six_review(self) -> bool:
        """Return whether human review approves bounded review."""

    def fingerprint(self) -> str:
        """Return deterministic docket fingerprint."""


class IndependentReviewPacketLike(Protocol):
    """Structural protocol for the independent-review packet."""

    @property
    def blocks_external_review(self) -> bool:
        """Return whether external review is blocked."""

    @property
    def ready_for_external_review(self) -> bool:
        """Return whether the packet can enter external review."""

    def fingerprint(self) -> str:
        """Return deterministic packet fingerprint."""


class ClaimBoundaryAssessmentLike(Protocol):
    """Structural protocol for the claim-boundary assessment."""

    @property
    def blocked_declaration_ids(self) -> tuple[str, ...]:
        """Return declarations that block interpretation."""

    @property
    def ready_for_wave_six_review(self) -> bool:
        """Return whether claim boundaries can support review."""

    def fingerprint(self) -> str:
        """Return deterministic assessment fingerprint."""


WAVE_SIX_EVIDENCE_REFERENCE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-evidence-reference-v1"
)
WAVE_SIX_EVIDENCE_PACKAGE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-evidence-package-v1"
)


class WaveSixEvidenceSurface(StrEnum):
    """Evidence surfaces required for a bounded Wave 6 package."""

    MASTER_LOOP_TRACE = "master-loop-trace"
    CONTRACT_BUNDLE = "contract-bundle"
    DONOR_TRACEABILITY_MAP = "donor-traceability-map"
    REALITY_CORRECTION_LEDGER = "reality-correction-ledger"
    FUTURE_REASONING_CHANGE_LEDGER = "future-reasoning-change-ledger"
    TRANSFER_NOVELTY_LEDGER = "transfer-novelty-ledger"
    FALSIFICATION_LEDGER = "falsification-ledger"
    HUMAN_REVIEW_DOCKET = "human-review-docket"
    INDEPENDENT_REVIEW_PACKET = "independent-review-packet"
    CLAIM_BOUNDARY_ASSESSMENT = "claim-boundary-assessment"


class WaveSixEvidencePackageBlocker(StrEnum):
    """Reasons a Wave 6 evidence package cannot advance."""

    MISSING_REQUIRED_SURFACE = "missing-required-surface"
    REALITY_CORRECTION_NOT_READY = "reality-correction-not-ready"
    FUTURE_REASONING_NOT_READY = "future-reasoning-not-ready"
    TRANSFER_NOVELTY_NOT_READY = "transfer-novelty-not-ready"
    FALSIFICATION_NOT_READY = "falsification-not-ready"
    HUMAN_REVIEW_NOT_APPROVED = "human-review-not-approved"
    INDEPENDENT_REVIEW_NOT_READY = "independent-review-not-ready"
    CLAIM_BOUNDARY_NOT_READY = "claim-boundary-not-ready"
    CLAIM_BLOCKED = "claim-blocked"
    OVERCLAIM_PRESENT = "overclaim-present"


class WaveSixEvidencePackageStatus(StrEnum):
    """Fail-closed package status."""

    BLOCKED = "blocked"
    NEEDS_MORE_EVIDENCE = "needs-more-evidence"
    READY_FOR_EXTERNAL_REVIEW = "ready-for-external-review"


WAVE_SIX_REQUIRED_EVIDENCE_SURFACES: tuple[WaveSixEvidenceSurface, ...] = (
    WaveSixEvidenceSurface.MASTER_LOOP_TRACE,
    WaveSixEvidenceSurface.CONTRACT_BUNDLE,
    WaveSixEvidenceSurface.DONOR_TRACEABILITY_MAP,
    WaveSixEvidenceSurface.REALITY_CORRECTION_LEDGER,
    WaveSixEvidenceSurface.FUTURE_REASONING_CHANGE_LEDGER,
    WaveSixEvidenceSurface.TRANSFER_NOVELTY_LEDGER,
    WaveSixEvidenceSurface.FALSIFICATION_LEDGER,
    WaveSixEvidenceSurface.HUMAN_REVIEW_DOCKET,
    WaveSixEvidenceSurface.INDEPENDENT_REVIEW_PACKET,
    WaveSixEvidenceSurface.CLAIM_BOUNDARY_ASSESSMENT,
)


@dataclass(frozen=True, slots=True)
class WaveSixEvidenceReference:
    """Fingerprint reference to one evidence surface."""

    reference_id: str
    surface: WaveSixEvidenceSurface
    artifact_fingerprint: str
    evidence_ids: tuple[str, ...]
    summary: str
    schema_version: str = WAVE_SIX_EVIDENCE_REFERENCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Normalize evidence reference fields."""

        object.__setattr__(
            self,
            "reference_id",
            _require_non_empty(self.reference_id, "reference_id"),
        )
        object.__setattr__(
            self,
            "artifact_fingerprint",
            _require_non_empty(
                self.artifact_fingerprint,
                "artifact_fingerprint",
            ),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "summary",
            _require_non_empty(self.summary, "summary"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Wave 6 evidence references require evidence ids.")

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic payload for hashing and review."""

        return {
            "artifact_fingerprint": self.artifact_fingerprint,
            "evidence_ids": list(self.evidence_ids),
            "reference_id": self.reference_id,
            "schema_version": self.schema_version,
            "summary": self.summary,
            "surface": self.surface.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this reference."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixEvidencePackage:
    """Aggregated Wave 6 evidence package for external review."""

    package_id: str
    references: tuple[WaveSixEvidenceReference, ...]
    reality_correction_ledger: RealityCorrectionLedgerLike
    future_reasoning_ledger: FutureReasoningLedgerLike
    transfer_novelty_ledger: TransferNoveltyLedgerLike
    falsification_ledger: FalsificationLedgerLike
    human_review_docket: HumanReviewDocketLike
    independent_review_packet: IndependentReviewPacketLike
    claim_boundary_assessment: ClaimBoundaryAssessmentLike
    required_surfaces: tuple[WaveSixEvidenceSurface, ...] = (
        WAVE_SIX_REQUIRED_EVIDENCE_SURFACES
    )
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    allows_autonomous_authority: bool = False
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_EVIDENCE_PACKAGE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate package identity, references, and overclaim boundaries."""

        object.__setattr__(
            self,
            "package_id",
            _require_non_empty(self.package_id, "package_id"),
        )
        if not self.references:
            raise ValueError("Wave 6 evidence packages require references.")
        sorted_references = tuple(
            sorted(self.references, key=lambda reference: reference.reference_id)
        )
        _unique_ids(
            (reference.reference_id for reference in sorted_references),
            label="reference_id",
        )
        object.__setattr__(self, "references", sorted_references)
        object.__setattr__(
            self,
            "required_surfaces",
            _normalize_unique_enum_tuple(
                self.required_surfaces,
                label="required evidence surface",
            ),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="package note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )

    @property
    def reference_ids(self) -> tuple[str, ...]:
        """Return evidence reference ids in deterministic order."""

        return tuple(reference.reference_id for reference in self.references)

    @property
    def present_surfaces(self) -> tuple[WaveSixEvidenceSurface, ...]:
        """Return required evidence surfaces represented by references."""

        present = {reference.surface for reference in self.references}
        return tuple(
            surface for surface in self.required_surfaces if surface in present
        )

    @property
    def missing_surfaces(self) -> tuple[WaveSixEvidenceSurface, ...]:
        """Return required evidence surfaces missing from the package."""

        present = {reference.surface for reference in self.references}
        return tuple(
            surface for surface in self.required_surfaces if surface not in present
        )

    @property
    def blocked_by_ledgers(self) -> bool:
        """Return whether any evidence ledger or review artifact blocks the package."""

        return bool(
            self.reality_correction_ledger.blocking_record_ids
            or self.future_reasoning_ledger.blocked_proof_ids
            or self.transfer_novelty_ledger.blocked_record_ids
            or self.falsification_ledger.blocking_result_ids
            or self.human_review_docket.blocks_wave_six_claim
            or self.independent_review_packet.blocks_external_review
            or self.claim_boundary_assessment.blocked_declaration_ids
        )

    @property
    def overclaim_present(self) -> bool:
        """Return whether the package itself violates the claim boundary."""

        return (
            self.claims_agi
            or self.claims_production_ready
            or self.claims_certified
            or self.allows_autonomous_authority
        )

    @property
    def blockers(self) -> tuple[WaveSixEvidencePackageBlocker, ...]:
        """Return deterministic blockers that prevent external review readiness."""

        blockers: list[WaveSixEvidencePackageBlocker] = []
        if self.missing_surfaces:
            blockers.append(WaveSixEvidencePackageBlocker.MISSING_REQUIRED_SURFACE)
        if self.overclaim_present:
            blockers.append(WaveSixEvidencePackageBlocker.OVERCLAIM_PRESENT)
        if self.blocked_by_ledgers:
            blockers.append(WaveSixEvidencePackageBlocker.CLAIM_BLOCKED)
        if not self.reality_correction_ledger.ready_for_wave_six_memory_update:
            blockers.append(
                WaveSixEvidencePackageBlocker.REALITY_CORRECTION_NOT_READY
            )
        if not self.future_reasoning_ledger.ready_for_wave_six_review:
            blockers.append(WaveSixEvidencePackageBlocker.FUTURE_REASONING_NOT_READY)
        if not self.transfer_novelty_ledger.ready_for_wave_six_review:
            blockers.append(WaveSixEvidencePackageBlocker.TRANSFER_NOVELTY_NOT_READY)
        if not self.falsification_ledger.ready_for_wave_six_review:
            blockers.append(WaveSixEvidencePackageBlocker.FALSIFICATION_NOT_READY)
        if not self.human_review_docket.approves_bounded_wave_six_review:
            blockers.append(WaveSixEvidencePackageBlocker.HUMAN_REVIEW_NOT_APPROVED)
        if not self.independent_review_packet.ready_for_external_review:
            blockers.append(WaveSixEvidencePackageBlocker.INDEPENDENT_REVIEW_NOT_READY)
        if not self.claim_boundary_assessment.ready_for_wave_six_review:
            blockers.append(WaveSixEvidencePackageBlocker.CLAIM_BOUNDARY_NOT_READY)
        return tuple(blockers)

    @property
    def status(self) -> WaveSixEvidencePackageStatus:
        """Return fail-closed evidence package status."""

        if self.overclaim_present or self.blocked_by_ledgers:
            return WaveSixEvidencePackageStatus.BLOCKED
        if self.blockers:
            return WaveSixEvidencePackageStatus.NEEDS_MORE_EVIDENCE
        return WaveSixEvidencePackageStatus.READY_FOR_EXTERNAL_REVIEW

    @property
    def ready_for_external_review(self) -> bool:
        """Return whether the package is ready for external review."""

        return self.status is WaveSixEvidencePackageStatus.READY_FOR_EXTERNAL_REVIEW

    def reference_for_surface(
        self,
        surface: WaveSixEvidenceSurface,
    ) -> WaveSixEvidenceReference | None:
        """Return the first evidence reference for a surface, if present."""

        for reference in self.references:
            if reference.surface is surface:
                return reference
        return None

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic package payload for hashing and review."""

        return {
            "allows_autonomous_authority": self.allows_autonomous_authority,
            "blockers": [blocker.value for blocker in self.blockers],
            "claim_boundary_assessment_fingerprint": (
                self.claim_boundary_assessment.fingerprint()
            ),
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "falsification_ledger_fingerprint": self.falsification_ledger.fingerprint(),
            "future_reasoning_ledger_fingerprint": (
                self.future_reasoning_ledger.fingerprint()
            ),
            "human_review_docket_fingerprint": self.human_review_docket.fingerprint(),
            "independent_review_packet_fingerprint": (
                self.independent_review_packet.fingerprint()
            ),
            "missing_surfaces": [surface.value for surface in self.missing_surfaces],
            "notes": list(self.notes),
            "package_id": self.package_id,
            "present_surfaces": [surface.value for surface in self.present_surfaces],
            "reality_correction_ledger_fingerprint": (
                self.reality_correction_ledger.fingerprint()
            ),
            "references": [
                reference.canonical_payload() for reference in self.references
            ],
            "required_surfaces": [surface.value for surface in self.required_surfaces],
            "schema_version": self.schema_version,
            "status": self.status.value,
            "transfer_novelty_ledger_fingerprint": (
                self.transfer_novelty_ledger.fingerprint()
            ),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this evidence package."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_evidence_package(
    *,
    package_id: str,
    references: Iterable[WaveSixEvidenceReference],
    reality_correction_ledger: RealityCorrectionLedgerLike,
    future_reasoning_ledger: FutureReasoningLedgerLike,
    transfer_novelty_ledger: TransferNoveltyLedgerLike,
    falsification_ledger: FalsificationLedgerLike,
    human_review_docket: HumanReviewDocketLike,
    independent_review_packet: IndependentReviewPacketLike,
    claim_boundary_assessment: ClaimBoundaryAssessmentLike,
    notes: Iterable[str] = (),
) -> WaveSixEvidencePackage:
    """Build a deterministic Wave 6 evidence package."""

    return WaveSixEvidencePackage(
        package_id=package_id,
        references=tuple(references),
        reality_correction_ledger=reality_correction_ledger,
        future_reasoning_ledger=future_reasoning_ledger,
        transfer_novelty_ledger=transfer_novelty_ledger,
        falsification_ledger=falsification_ledger,
        human_review_docket=human_review_docket,
        independent_review_packet=independent_review_packet,
        claim_boundary_assessment=claim_boundary_assessment,
        notes=tuple(notes),
    )


def required_wave_six_evidence_surfaces() -> tuple[WaveSixEvidenceSurface, ...]:
    """Return surfaces required for a complete Wave 6 evidence package."""

    return WAVE_SIX_REQUIRED_EVIDENCE_SURFACES


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
