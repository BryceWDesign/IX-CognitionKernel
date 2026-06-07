"""Wave 6 contract-bundle assembly.

This module keeps Wave 6 integration clean by assembling contract coverage from
explicit blueprints plus the canonical donor traceability map. It does not import
or execute donor repos. It creates a deterministic review surface the readiness
gate can consume without ad-hoc strings or hidden coupling.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.wave6_contracts import (
    WAVE_SIX_REQUIRED_LOOP_STAGES,
    WaveSixArtifactKind,
    WaveSixCapabilityArea,
    WaveSixContractArtifact,
    WaveSixContractBundle,
    WaveSixDecisionState,
    WaveSixLoopStage,
    WaveSixSourceSystem,
)
from ix_cognition_kernel.wave6_donor_profiles import (
    build_canonical_wave_six_donor_traceability_map,
)
from ix_cognition_kernel.wave6_donor_traceability import WaveSixDonorTraceabilityMap

E = TypeVar("E", bound=StrEnum)

WAVE_SIX_CONTRACT_BLUEPRINT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-contract-blueprint-v1"
)
WAVE_SIX_CONTRACT_ASSEMBLY_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-contract-assembly-v1"
)
WAVE_SIX_CANONICAL_CONTRACT_BUNDLE_ID = "wave6-canonical-contract-bundle"
WAVE_SIX_CANONICAL_CONTRACT_ASSEMBLY_ID = "wave6-canonical-contract-assembly"


class WaveSixContractAssemblyStatus(StrEnum):
    """Deterministic contract assembly status."""

    BLOCKED = "blocked"
    INCOMPLETE = "incomplete"
    READY_FOR_READINESS_GATE = "ready-for-readiness-gate"


@dataclass(frozen=True, slots=True)
class WaveSixContractBlueprint:
    """Blueprint for one core Wave 6 contract artifact."""

    blueprint_id: str
    artifact_kind: WaveSixArtifactKind
    capability_area: WaveSixCapabilityArea
    source_system: WaveSixSourceSystem
    loop_stages: tuple[WaveSixLoopStage, ...]
    summary: str
    evidence_ids: tuple[str, ...]
    produced_by_engine_id: str = "wave6-contract-assembly-engine"
    decision: WaveSixDecisionState = WaveSixDecisionState.READY_FOR_WAVE_SIX_LOOP
    schema_version: str = WAVE_SIX_CONTRACT_BLUEPRINT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate explicit artifact-generation inputs."""

        object.__setattr__(
            self,
            "blueprint_id",
            _require_non_empty(self.blueprint_id, "blueprint_id"),
        )
        object.__setattr__(
            self,
            "summary",
            _require_non_empty(self.summary, "summary"),
        )
        object.__setattr__(
            self,
            "loop_stages",
            _normalize_unique_enum_tuple(self.loop_stages, label="loop stage"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "produced_by_engine_id",
            _require_non_empty(self.produced_by_engine_id, "produced_by_engine_id"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.loop_stages:
            raise ValueError("Contract blueprints require at least one loop stage.")
        if not self.evidence_ids:
            raise ValueError("Contract blueprints require evidence ids.")

    @property
    def artifact_id(self) -> str:
        """Return deterministic artifact id produced by this blueprint."""

        return f"contract-artifact-{self.blueprint_id}"

    def to_artifact(self) -> WaveSixContractArtifact:
        """Convert this blueprint into a reviewable contract artifact."""

        return WaveSixContractArtifact(
            artifact_id=self.artifact_id,
            kind=self.artifact_kind,
            capability_area=self.capability_area,
            source_system=self.source_system,
            summary=self.summary,
            loop_stages=self.loop_stages,
            evidence_ids=self.evidence_ids,
            produced_by_engine_id=self.produced_by_engine_id,
            decision=self.decision,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic payload for hashing and review."""

        return {
            "artifact_id": self.artifact_id,
            "artifact_kind": self.artifact_kind.value,
            "blueprint_id": self.blueprint_id,
            "capability_area": self.capability_area.value,
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "loop_stages": [stage.value for stage in self.loop_stages],
            "produced_by_engine_id": self.produced_by_engine_id,
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this blueprint."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixContractAssembly:
    """Assembled Wave 6 contract surface for the readiness gate."""

    assembly_id: str
    donor_map: WaveSixDonorTraceabilityMap
    core_blueprints: tuple[WaveSixContractBlueprint, ...]
    bundle_id: str = WAVE_SIX_CANONICAL_CONTRACT_BUNDLE_ID
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_CONTRACT_ASSEMBLY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Normalize assembly identity and blueprint ordering."""

        object.__setattr__(
            self,
            "assembly_id",
            _require_non_empty(self.assembly_id, "assembly_id"),
        )
        object.__setattr__(
            self,
            "bundle_id",
            _require_non_empty(self.bundle_id, "bundle_id"),
        )
        if not self.core_blueprints:
            raise ValueError("Wave 6 contract assembly requires core blueprints.")
        sorted_blueprints = tuple(
            sorted(self.core_blueprints, key=lambda blueprint: blueprint.blueprint_id)
        )
        _require_unique_text(
            (blueprint.blueprint_id for blueprint in sorted_blueprints),
            label="blueprint_id",
        )
        object.__setattr__(self, "core_blueprints", sorted_blueprints)
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="assembly note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )

    @property
    def core_artifacts(self) -> tuple[WaveSixContractArtifact, ...]:
        """Return artifacts produced from core blueprints."""

        return tuple(blueprint.to_artifact() for blueprint in self.core_blueprints)

    @property
    def donor_artifacts(self) -> tuple[WaveSixContractArtifact, ...]:
        """Return donor traceability artifacts."""

        return self.donor_map.to_contract_artifacts()

    @property
    def all_artifacts(self) -> tuple[WaveSixContractArtifact, ...]:
        """Return all artifacts feeding the contract bundle."""

        return (*self.core_artifacts, *self.donor_artifacts)

    @property
    def contract_bundle(self) -> WaveSixContractBundle:
        """Return the assembled contract bundle."""

        return WaveSixContractBundle(
            bundle_id=self.bundle_id,
            artifacts=self.all_artifacts,
            notes=(
                "Assembled from core Wave 6 blueprints and canonical donor "
                "traceability artifacts; this is not an AGI claim.",
                *self.notes,
            ),
        )

    @property
    def missing_artifact_kinds(self) -> tuple[WaveSixArtifactKind, ...]:
        """Return required artifact kinds missing from the assembled bundle."""

        return self.contract_bundle.missing_artifact_kinds

    @property
    def missing_capability_areas(self) -> tuple[WaveSixCapabilityArea, ...]:
        """Return required capability areas missing from the assembled bundle."""

        return self.contract_bundle.missing_capability_areas

    @property
    def missing_loop_stages(self) -> tuple[WaveSixLoopStage, ...]:
        """Return required loop stages missing from the assembled bundle."""

        return self.contract_bundle.missing_loop_stages

    @property
    def blocked_artifact_ids(self) -> tuple[str, ...]:
        """Return artifacts that block Wave 6 progress."""

        return self.contract_bundle.blocked_artifact_ids

    @property
    def status(self) -> WaveSixContractAssemblyStatus:
        """Return fail-closed assembly status."""

        if self.blocked_artifact_ids or self.donor_map.blocked_contribution_ids:
            return WaveSixContractAssemblyStatus.BLOCKED
        if (
            self.missing_artifact_kinds
            or self.missing_capability_areas
            or self.missing_loop_stages
            or self.donor_map.missing_source_systems
        ):
            return WaveSixContractAssemblyStatus.INCOMPLETE
        return WaveSixContractAssemblyStatus.READY_FOR_READINESS_GATE

    @property
    def ready_for_readiness_gate(self) -> bool:
        """Return whether the assembled bundle can enter readiness assessment."""

        return self.status is WaveSixContractAssemblyStatus.READY_FOR_READINESS_GATE

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic payload for review and hashing."""

        bundle = self.contract_bundle
        return {
            "assembly_id": self.assembly_id,
            "blocked_artifact_ids": list(self.blocked_artifact_ids),
            "bundle_fingerprint": bundle.fingerprint(),
            "bundle_id": self.bundle_id,
            "core_blueprints": [
                blueprint.canonical_payload() for blueprint in self.core_blueprints
            ],
            "donor_map_fingerprint": self.donor_map.fingerprint(),
            "missing_artifact_kinds": [
                kind.value for kind in self.missing_artifact_kinds
            ],
            "missing_capability_areas": [
                area.value for area in self.missing_capability_areas
            ],
            "missing_loop_stages": [stage.value for stage in self.missing_loop_stages],
            "notes": list(self.notes),
            "schema_version": self.schema_version,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this assembly."""

        return _stable_sha256(self.canonical_payload())


def canonical_wave_six_contract_blueprints() -> tuple[WaveSixContractBlueprint, ...]:
    """Return the locked core artifact blueprints for Wave 6."""

    return (
        WaveSixContractBlueprint(
            blueprint_id="01-master-loop-contract",
            artifact_kind=WaveSixArtifactKind.MASTER_LOOP_CONTRACT,
            capability_area=WaveSixCapabilityArea.MASTER_LOOP,
            source_system=WaveSixSourceSystem.IX_MAIN,
            loop_stages=(WaveSixLoopStage.INTENT, WaveSixLoopStage.PERMISSION),
            summary="Readable contract for the bounded Wave 6 master loop.",
            evidence_ids=("wave6-blueprint:master-loop-contract",),
        ),
        WaveSixContractBlueprint(
            blueprint_id="02-measured-cognition-record",
            artifact_kind=WaveSixArtifactKind.MEASURED_COGNITION_RECORD,
            capability_area=WaveSixCapabilityArea.MEASURED_SYSTEM_LEVEL_COGNITION,
            source_system=WaveSixSourceSystem.IX_BLACKFOX_COGNITION,
            loop_stages=(WaveSixLoopStage.PREDICTION,),
            summary="Measured cognition record for prediction-before-outcome review.",
            evidence_ids=("wave6-blueprint:measured-cognition-record",),
        ),
        WaveSixContractBlueprint(
            blueprint_id="03-reality-correction-record",
            artifact_kind=WaveSixArtifactKind.REALITY_CORRECTION_RECORD,
            capability_area=WaveSixCapabilityArea.REALITY_CORRECTED_REASONING,
            source_system=WaveSixSourceSystem.IX_INTENT_REALITY_LOOP,
            loop_stages=(WaveSixLoopStage.OUTCOME, WaveSixLoopStage.DELTA),
            summary=(
                "Reality-correction record comparing expected "
                "and measured outcome."
            ),
            evidence_ids=("wave6-blueprint:reality-correction-record",),
        ),
        WaveSixContractBlueprint(
            blueprint_id="04-future-reasoning-change-proof",
            artifact_kind=WaveSixArtifactKind.FUTURE_REASONING_CHANGE_PROOF,
            capability_area=WaveSixCapabilityArea.FUTURE_REASONING_CHANGE,
            source_system=WaveSixSourceSystem.IX_INTENT_REALITY_LOOP,
            loop_stages=(WaveSixLoopStage.MEMORY_UPDATE,),
            summary="Proof that measured reality changed future reasoning.",
            evidence_ids=("wave6-blueprint:future-reasoning-change-proof",),
        ),
        WaveSixContractBlueprint(
            blueprint_id="05-transfer-novelty-record",
            artifact_kind=WaveSixArtifactKind.TRANSFER_NOVELTY_RECORD,
            capability_area=WaveSixCapabilityArea.CROSS_DOMAIN_TRANSFER,
            source_system=WaveSixSourceSystem.IX_FUNCTION,
            loop_stages=(WaveSixLoopStage.TRANSFER_CHECK,),
            summary="Cross-domain transfer and novelty-pressure record.",
            evidence_ids=("wave6-blueprint:transfer-novelty-record",),
        ),
        WaveSixContractBlueprint(
            blueprint_id="06-falsification-record",
            artifact_kind=WaveSixArtifactKind.FALSIFICATION_RECORD,
            capability_area=WaveSixCapabilityArea.NOVELTY_PRESSURE,
            source_system=WaveSixSourceSystem.IX_FUNCTION,
            loop_stages=(WaveSixLoopStage.FALSIFICATION,),
            summary="Falsification record with negative-control pressure.",
            evidence_ids=("wave6-blueprint:falsification-record",),
        ),
        WaveSixContractBlueprint(
            blueprint_id="07-human-review-docket",
            artifact_kind=WaveSixArtifactKind.HUMAN_REVIEW_DOCKET,
            capability_area=WaveSixCapabilityArea.HUMAN_AUTHORITY_PRESERVATION,
            source_system=WaveSixSourceSystem.IX_BLACKFOX,
            loop_stages=(WaveSixLoopStage.HUMAN_REVIEW,),
            summary="Human-review docket preserving authority and review gates.",
            evidence_ids=("wave6-blueprint:human-review-docket",),
        ),
        WaveSixContractBlueprint(
            blueprint_id="08-donor-traceability-map",
            artifact_kind=WaveSixArtifactKind.DONOR_TRACEABILITY_MAP,
            capability_area=WaveSixCapabilityArea.DONOR_TRACEABILITY,
            source_system=WaveSixSourceSystem.IX_COGNITION_KERNEL,
            loop_stages=WAVE_SIX_REQUIRED_LOOP_STAGES,
            summary="Kernel-owned map from donor profiles to loop responsibilities.",
            evidence_ids=("wave6-blueprint:donor-traceability-map",),
        ),
        WaveSixContractBlueprint(
            blueprint_id="09-independent-review-packet",
            artifact_kind=WaveSixArtifactKind.INDEPENDENT_REVIEW_PACKET,
            capability_area=WaveSixCapabilityArea.FALSIFICATION_DISCIPLINE,
            source_system=WaveSixSourceSystem.INDEPENDENT_EVALUATOR,
            loop_stages=(WaveSixLoopStage.FALSIFICATION, WaveSixLoopStage.HUMAN_REVIEW),
            summary="Independent-review packet for falsification-ready inspection.",
            evidence_ids=("wave6-blueprint:independent-review-packet",),
        ),
        WaveSixContractBlueprint(
            blueprint_id="10-claim-boundary-declaration",
            artifact_kind=WaveSixArtifactKind.CLAIM_BOUNDARY_DECLARATION,
            capability_area=WaveSixCapabilityArea.INDEPENDENT_REVIEW_READINESS,
            source_system=WaveSixSourceSystem.HUMAN_REVIEW,
            loop_stages=(WaveSixLoopStage.HUMAN_REVIEW,),
            summary="Declaration that Wave 6 is not an AGI or production claim.",
            evidence_ids=("wave6-blueprint:claim-boundary-declaration",),
        ),
    )


def build_canonical_wave_six_contract_assembly() -> WaveSixContractAssembly:
    """Build the canonical Wave 6 contract assembly."""

    return WaveSixContractAssembly(
        assembly_id=WAVE_SIX_CANONICAL_CONTRACT_ASSEMBLY_ID,
        donor_map=build_canonical_wave_six_donor_traceability_map(),
        core_blueprints=canonical_wave_six_contract_blueprints(),
        notes=(
            "The assembly is a readiness input for measured system-level cognition, "
            "not a declaration that AGI has been achieved.",
        ),
    )


def build_wave_six_contract_assembly(
    *,
    assembly_id: str,
    donor_map: WaveSixDonorTraceabilityMap,
    core_blueprints: Iterable[WaveSixContractBlueprint],
    bundle_id: str = WAVE_SIX_CANONICAL_CONTRACT_BUNDLE_ID,
    notes: Iterable[str] = (),
) -> WaveSixContractAssembly:
    """Build a Wave 6 contract assembly from explicit parts."""

    return WaveSixContractAssembly(
        assembly_id=assembly_id,
        donor_map=donor_map,
        core_blueprints=tuple(core_blueprints),
        bundle_id=bundle_id,
        notes=tuple(notes),
    )


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


def _require_unique_text(values: Iterable[str], *, label: str) -> None:
    """Reject duplicate text values."""

    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value}")
        seen.add(value)


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
