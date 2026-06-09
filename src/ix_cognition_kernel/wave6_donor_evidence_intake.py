"""Wave 6 donor evidence intake contracts.

IX-CognitionKernel should not directly import or execute donor repositories. The
supporting repos provide evidence receipts; the Kernel validates those receipts
against locked donor profiles and keeps the result metadata-only until later
candidate assembly and human review layers decide what the evidence means.

This module is intentionally narrow: it accepts fingerprinted donor evidence
metadata, rejects authority or AGI overclaims, reports missing donor coverage,
and can convert accepted receipts into bounded Wave 6 contract artifacts. It
creates no runtime coupling to IX-Function, IX-IntentRealityLoop, IX-BlackFox,
IX-BlackFox-Cognition, IX-BlackFox-WorldTwin, or the assurance runtime.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.wave6_contracts import (
    WaveSixArtifactKind,
    WaveSixCapabilityArea,
    WaveSixContractArtifact,
    WaveSixDecisionState,
    WaveSixLoopStage,
    WaveSixSourceSystem,
)
from ix_cognition_kernel.wave6_donor_profiles import (
    WaveSixDonorProfile,
    canonical_wave_six_donor_profile_for_source,
)

T = TypeVar("T")

WAVE_SIX_DONOR_EVIDENCE_RECEIPT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-donor-evidence-receipt-v1"
)
WAVE_SIX_DONOR_EVIDENCE_INTAKE_BUNDLE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-donor-evidence-intake-bundle-v1"
)
WAVE_SIX_DONOR_EVIDENCE_INTAKE_ENGINE_ID = "wave6-donor-evidence-intake-engine"

WAVE_SIX_SUPPORTING_DONOR_SOURCE_SYSTEMS: tuple[WaveSixSourceSystem, ...] = (
    WaveSixSourceSystem.IX_FUNCTION,
    WaveSixSourceSystem.IX_INTENT_REALITY_LOOP,
    WaveSixSourceSystem.IX_BLACKFOX,
    WaveSixSourceSystem.IX_BLACKFOX_COGNITION,
    WaveSixSourceSystem.IX_BLACKFOX_WORLDTWIN,
    WaveSixSourceSystem.IX_AUTONOMY_ASSURANCE_RUNTIME,
)


class WaveSixDonorEvidenceIntakeStatus(StrEnum):
    """Fail-closed status for donor evidence intake."""

    NEEDS_MORE_DONOR_EVIDENCE = "needs-more-donor-evidence"
    READY_FOR_CANDIDATE_ASSEMBLY = "ready-for-candidate-assembly"


@dataclass(frozen=True, slots=True)
class WaveSixDonorEvidenceReceipt:
    """One metadata-only evidence receipt from a supporting donor repo."""

    receipt_id: str
    source_system: WaveSixSourceSystem
    repo_name: str
    evidence_id: str
    artifact_kind: WaveSixArtifactKind
    capability_area: WaveSixCapabilityArea
    loop_stages: tuple[WaveSixLoopStage, ...]
    artifact_fingerprint: str
    summary: str
    produced_by_engine_id: str
    human_review_required: bool = True
    metadata_only: bool = True
    allows_autonomous_execution: bool = False
    claims_agi: bool = False
    claims_production_ready: bool = False
    claims_certified: bool = False
    self_validated: bool = False
    validation_notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_DONOR_EVIDENCE_RECEIPT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate donor identity, coverage, and authority boundaries."""

        profile = _supporting_profile_for_source(self.source_system)
        object.__setattr__(
            self,
            "receipt_id",
            _require_non_empty(self.receipt_id, "receipt_id"),
        )
        object.__setattr__(
            self,
            "repo_name",
            _require_non_empty(self.repo_name, "repo_name"),
        )
        object.__setattr__(
            self,
            "evidence_id",
            _require_non_empty(self.evidence_id, "evidence_id"),
        )
        object.__setattr__(
            self,
            "loop_stages",
            _normalize_unique_enum_tuple(self.loop_stages, label="loop stage"),
        )
        object.__setattr__(
            self,
            "artifact_fingerprint",
            _require_sha256(self.artifact_fingerprint, "artifact_fingerprint"),
        )
        object.__setattr__(
            self,
            "summary",
            _require_non_empty(self.summary, "summary"),
        )
        object.__setattr__(
            self,
            "produced_by_engine_id",
            _require_non_empty(
                self.produced_by_engine_id,
                "produced_by_engine_id",
            ),
        )
        object.__setattr__(
            self,
            "validation_notes",
            _normalize_unique_text_tuple(
                self.validation_notes,
                label="validation note",
            ),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if self.repo_name != profile.repo_name:
            raise ValueError(
                "Donor evidence receipt repo name must match canonical profile "
                f"for {self.source_system.value}."
            )
        if self.artifact_kind not in profile.supplied_artifact_kinds:
            raise ValueError(
                "Donor evidence receipt artifact kind is not supplied by "
                f"{profile.repo_name}."
            )
        if self.capability_area not in profile.supplied_capability_areas:
            raise ValueError(
                "Donor evidence receipt capability area is not supplied by "
                f"{profile.repo_name}."
            )
        if not self.loop_stages:
            raise ValueError("Donor evidence receipts require loop-stage coverage.")
        for stage in self.loop_stages:
            if stage not in profile.supported_loop_stages:
                raise ValueError(
                    "Donor evidence receipt loop stage is not supported by "
                    f"{profile.repo_name}: {stage.value}"
                )
        if not self.human_review_required:
            raise ValueError("Donor evidence receipts must require human review.")
        if not self.metadata_only:
            raise ValueError("Donor evidence receipts must be metadata-only.")
        if self.allows_autonomous_execution:
            raise ValueError("Donor evidence receipts must not grant execution.")
        if self.claims_agi:
            raise ValueError("Donor evidence receipts must not claim AGI.")
        if self.claims_production_ready:
            raise ValueError("Donor evidence receipts must not claim production.")
        if self.claims_certified:
            raise ValueError("Donor evidence receipts must not claim certification.")
        if self.self_validated:
            raise ValueError("Donor evidence receipts must not be self-validated.")

    @property
    def profile(self) -> WaveSixDonorProfile:
        """Return the canonical donor profile for this receipt."""

        return _supporting_profile_for_source(self.source_system)

    def to_contract_artifact(self) -> WaveSixContractArtifact:
        """Convert this receipt into a bounded Wave 6 contract artifact."""

        return WaveSixContractArtifact(
            artifact_id=f"donor-evidence-artifact-{self.receipt_id}",
            kind=self.artifact_kind,
            capability_area=self.capability_area,
            source_system=self.source_system,
            summary=self.summary,
            loop_stages=self.loop_stages,
            evidence_ids=(self.evidence_id,),
            produced_by_engine_id=WAVE_SIX_DONOR_EVIDENCE_INTAKE_ENGINE_ID,
            decision=WaveSixDecisionState.NEEDS_MORE_EVIDENCE,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic payload for donor evidence review."""

        return {
            "allows_autonomous_execution": self.allows_autonomous_execution,
            "artifact_fingerprint": self.artifact_fingerprint,
            "artifact_kind": self.artifact_kind.value,
            "capability_area": self.capability_area.value,
            "claims_agi": self.claims_agi,
            "claims_certified": self.claims_certified,
            "claims_production_ready": self.claims_production_ready,
            "evidence_id": self.evidence_id,
            "human_review_required": self.human_review_required,
            "loop_stages": [stage.value for stage in self.loop_stages],
            "metadata_only": self.metadata_only,
            "produced_by_engine_id": self.produced_by_engine_id,
            "profile_fingerprint": self.profile.fingerprint(),
            "receipt_id": self.receipt_id,
            "repo_name": self.repo_name,
            "schema_version": self.schema_version,
            "self_validated": self.self_validated,
            "source_system": self.source_system.value,
            "summary": self.summary,
            "validation_notes": list(self.validation_notes),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this receipt."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixDonorEvidenceIntakeBundle:
    """Validated metadata intake for supporting donor evidence receipts."""

    intake_id: str
    receipts: tuple[WaveSixDonorEvidenceReceipt, ...]
    required_source_systems: tuple[WaveSixSourceSystem, ...] = (
        WAVE_SIX_SUPPORTING_DONOR_SOURCE_SYSTEMS
    )
    generated_by_engine_id: str = WAVE_SIX_DONOR_EVIDENCE_INTAKE_ENGINE_ID
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_DONOR_EVIDENCE_INTAKE_BUNDLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate deterministic receipt ordering and required donor set."""

        object.__setattr__(
            self,
            "intake_id",
            _require_non_empty(self.intake_id, "intake_id"),
        )
        if not self.receipts:
            raise ValueError("Donor evidence intake requires at least one receipt.")
        sorted_receipts = tuple(
            sorted(
                self.receipts,
                key=lambda receipt: receipt.receipt_id,
            )
        )
        _require_unique(
            (receipt.receipt_id for receipt in sorted_receipts),
            label="receipt_id",
        )
        _require_unique(
            (receipt.evidence_id for receipt in sorted_receipts),
            label="evidence_id",
        )
        _require_unique(
            (
                (receipt.source_system, receipt.artifact_kind)
                for receipt in sorted_receipts
            ),
            label="source artifact coverage",
        )
        object.__setattr__(self, "receipts", sorted_receipts)
        object.__setattr__(
            self,
            "required_source_systems",
            _normalize_unique_enum_tuple(
                self.required_source_systems,
                label="required source system",
            ),
        )
        object.__setattr__(
            self,
            "generated_by_engine_id",
            _require_non_empty(
                self.generated_by_engine_id,
                "generated_by_engine_id",
            ),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="intake note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        _require_supporting_source_systems(self.required_source_systems)

    @property
    def receipt_ids(self) -> tuple[str, ...]:
        """Return receipt ids in deterministic order."""

        return tuple(receipt.receipt_id for receipt in self.receipts)

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        """Return donor evidence ids in deterministic order."""

        return tuple(receipt.evidence_id for receipt in self.receipts)

    @property
    def source_systems_present(self) -> tuple[WaveSixSourceSystem, ...]:
        """Return required source systems represented by receipts."""

        present = {receipt.source_system for receipt in self.receipts}
        return tuple(
            source for source in self.required_source_systems if source in present
        )

    @property
    def missing_source_systems(self) -> tuple[WaveSixSourceSystem, ...]:
        """Return required supporting donor systems with no accepted receipt."""

        present = {receipt.source_system for receipt in self.receipts}
        return tuple(
            source for source in self.required_source_systems if source not in present
        )

    @property
    def missing_required_artifact_keys(self) -> tuple[str, ...]:
        """Return required source/artifact pairs not represented by receipts."""

        present = {
            (receipt.source_system, receipt.artifact_kind) for receipt in self.receipts
        }
        missing: list[str] = []
        for source in self.required_source_systems:
            profile = _supporting_profile_for_source(source)
            for artifact_kind in profile.supplied_artifact_kinds:
                if (source, artifact_kind) not in present:
                    missing.append(f"{source.value}:{artifact_kind.value}")
        return tuple(missing)

    @property
    def contract_artifacts(self) -> tuple[WaveSixContractArtifact, ...]:
        """Return bounded contract artifacts for accepted donor receipts."""

        return tuple(receipt.to_contract_artifact() for receipt in self.receipts)

    @property
    def ready_for_candidate_assembly(self) -> bool:
        """Return whether donor intake covers all required supporting evidence."""

        return (
            not self.missing_source_systems and not self.missing_required_artifact_keys
        )

    @property
    def status(self) -> WaveSixDonorEvidenceIntakeStatus:
        """Return fail-closed donor evidence intake status."""

        if self.ready_for_candidate_assembly:
            return WaveSixDonorEvidenceIntakeStatus.READY_FOR_CANDIDATE_ASSEMBLY
        return WaveSixDonorEvidenceIntakeStatus.NEEDS_MORE_DONOR_EVIDENCE

    def receipt_for_evidence_id(
        self,
        evidence_id: str,
    ) -> WaveSixDonorEvidenceReceipt | None:
        """Return the receipt for an evidence id, if present."""

        normalized = _require_non_empty(evidence_id, "evidence_id")
        for receipt in self.receipts:
            if receipt.evidence_id == normalized:
                return receipt
        return None

    def receipts_for_source(
        self,
        source_system: WaveSixSourceSystem,
    ) -> tuple[WaveSixDonorEvidenceReceipt, ...]:
        """Return accepted receipts for one supporting donor source."""

        _supporting_profile_for_source(source_system)
        return tuple(
            receipt
            for receipt in self.receipts
            if receipt.source_system is source_system
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic intake bundle payload for review and hashing."""

        return {
            "contract_artifact_ids": [
                artifact.artifact_id for artifact in self.contract_artifacts
            ],
            "evidence_ids": list(self.evidence_ids),
            "generated_by_engine_id": self.generated_by_engine_id,
            "intake_id": self.intake_id,
            "missing_required_artifact_keys": list(self.missing_required_artifact_keys),
            "missing_source_systems": [
                source.value for source in self.missing_source_systems
            ],
            "notes": list(self.notes),
            "ready_for_candidate_assembly": self.ready_for_candidate_assembly,
            "receipt_count": len(self.receipts),
            "receipts": [receipt.canonical_payload() for receipt in self.receipts],
            "required_source_systems": [
                source.value for source in self.required_source_systems
            ],
            "schema_version": self.schema_version,
            "source_systems_present": [
                source.value for source in self.source_systems_present
            ],
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this intake bundle."""

        return _stable_sha256(self.canonical_payload())


def supporting_wave_six_donor_source_systems() -> tuple[WaveSixSourceSystem, ...]:
    """Return supporting donor sources expected after IX handoff ingestion."""

    return WAVE_SIX_SUPPORTING_DONOR_SOURCE_SYSTEMS


def build_wave_six_donor_evidence_intake_bundle(
    *,
    intake_id: str,
    receipts: Iterable[WaveSixDonorEvidenceReceipt],
    notes: Iterable[str] = (),
) -> WaveSixDonorEvidenceIntakeBundle:
    """Build a deterministic donor evidence intake bundle."""

    return WaveSixDonorEvidenceIntakeBundle(
        intake_id=intake_id,
        receipts=tuple(receipts),
        notes=tuple(notes),
    )


def _supporting_profile_for_source(
    source_system: WaveSixSourceSystem,
) -> WaveSixDonorProfile:
    """Return a canonical profile for an allowed supporting donor source."""

    if source_system not in WAVE_SIX_SUPPORTING_DONOR_SOURCE_SYSTEMS:
        raise ValueError(
            "Donor evidence intake only accepts supporting donor sources; "
            f"received {source_system.value}."
        )
    profile = canonical_wave_six_donor_profile_for_source(source_system)
    if profile is None:
        raise ValueError(f"Missing canonical donor profile for {source_system.value}.")
    return profile


def _require_supporting_source_systems(
    source_systems: Iterable[WaveSixSourceSystem],
) -> None:
    """Require the bundle to track only the supporting donor source set."""

    allowed = set(WAVE_SIX_SUPPORTING_DONOR_SOURCE_SYSTEMS)
    for source in source_systems:
        if source not in allowed:
            raise ValueError(
                "Donor evidence intake required sources must be supporting donors."
            )


def _require_non_empty(value: str, label: str) -> str:
    """Return stripped text or raise when empty."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _require_sha256(value: str, label: str) -> str:
    """Require a deterministic SHA-256 fingerprint value."""

    normalized = _require_non_empty(value, label)
    if len(normalized) != 64:
        raise ValueError(f"{label} must be a SHA-256 fingerprint.")
    try:
        int(normalized, 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be hexadecimal.") from exc
    return normalized


def _normalize_unique_text_tuple(
    values: Iterable[str],
    *,
    label: str,
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


def _normalize_unique_enum_tuple(values: Iterable[T], *, label: str) -> tuple[T, ...]:
    """Return enum-like values as a tuple while rejecting duplicates."""

    normalized: list[T] = []
    seen: set[T] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value}")
        normalized.append(value)
        seen.add(value)
    return tuple(normalized)


def _require_unique(values: Iterable[T], *, label: str) -> None:
    """Reject duplicate values."""

    seen: set[T] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value}")
        seen.add(value)


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
