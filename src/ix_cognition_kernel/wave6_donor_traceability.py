"""Wave 6 donor traceability map.

Wave 6 should not become messy glue code. This module records what each donor
repo is allowed to contribute to the measured system-level cognition attempt,
which loop stages it supports, which artifacts it can justify, and which
integration risks remain. It does not import or execute donor repos; it creates a
stable review map so later commits can integrate them through explicit contracts.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.wave6_contracts import (
    WAVE_SIX_DONOR_SOURCE_SYSTEMS,
    WAVE_SIX_REQUIRED_CLAIM_BOUNDARIES,
    WaveSixArtifactKind,
    WaveSixCapabilityArea,
    WaveSixClaimBoundary,
    WaveSixContractArtifact,
    WaveSixDecisionState,
    WaveSixLoopStage,
    WaveSixSourceSystem,
)

E = TypeVar("E", bound=StrEnum)
T = TypeVar("T")

WAVE_SIX_DONOR_CONTRIBUTION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-donor-contribution-v1"
)
WAVE_SIX_DONOR_TRACEABILITY_MAP_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave6-donor-traceability-map-v1"
)


class WaveSixDonorIntegrationRisk(StrEnum):
    """Known risks when donor repos are combined into Wave 6."""

    SCHEMA_DRIFT = "schema-drift"
    DECORATIVE_HANDOFF = "decorative-handoff"
    MESSY_GLUE_CODE = "messy-glue-code"
    NON_DETERMINISTIC_EVIDENCE = "non-deterministic-evidence"
    OVERCLAIMED_CAPABILITY = "overclaimed-capability"
    MISSING_REALITY_CORRECTION = "missing-reality-correction"
    MISSING_HUMAN_REVIEW = "missing-human-review"


@dataclass(frozen=True, slots=True)
class WaveSixDonorContribution:
    """One donor repo's bounded Wave 6 contribution."""

    contribution_id: str
    source_system: WaveSixSourceSystem
    repo_name: str
    contribution_summary: str
    supported_loop_stages: tuple[WaveSixLoopStage, ...]
    supplied_capability_areas: tuple[WaveSixCapabilityArea, ...]
    supplied_artifact_kinds: tuple[WaveSixArtifactKind, ...]
    evidence_ids: tuple[str, ...]
    integration_risks: tuple[WaveSixDonorIntegrationRisk, ...]
    mitigation_summary: str
    produced_by_engine_id: str = "wave6-donor-traceability-engine"
    decision: WaveSixDecisionState = WaveSixDecisionState.NEEDS_MORE_EVIDENCE
    claim_boundaries: tuple[WaveSixClaimBoundary, ...] = (
        WAVE_SIX_REQUIRED_CLAIM_BOUNDARIES
    )
    schema_version: str = WAVE_SIX_DONOR_CONTRIBUTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Normalize the contribution and enforce non-theatrical handoff data."""

        object.__setattr__(
            self,
            "contribution_id",
            _require_non_empty(self.contribution_id, "contribution_id"),
        )
        object.__setattr__(
            self, "repo_name", _require_non_empty(self.repo_name, "repo_name")
        )
        object.__setattr__(
            self,
            "contribution_summary",
            _require_non_empty(self.contribution_summary, "contribution_summary"),
        )
        object.__setattr__(
            self,
            "supported_loop_stages",
            _normalize_unique_enum_tuple(
                self.supported_loop_stages, label="supported loop stage"
            ),
        )
        object.__setattr__(
            self,
            "supplied_capability_areas",
            _normalize_unique_enum_tuple(
                self.supplied_capability_areas, label="supplied capability area"
            ),
        )
        object.__setattr__(
            self,
            "supplied_artifact_kinds",
            _normalize_unique_enum_tuple(
                self.supplied_artifact_kinds, label="supplied artifact kind"
            ),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "integration_risks",
            _normalize_unique_enum_tuple(
                self.integration_risks, label="integration risk"
            ),
        )
        object.__setattr__(
            self,
            "mitigation_summary",
            _require_non_empty(self.mitigation_summary, "mitigation_summary"),
        )
        object.__setattr__(
            self,
            "produced_by_engine_id",
            _require_non_empty(self.produced_by_engine_id, "produced_by_engine_id"),
        )
        object.__setattr__(
            self,
            "claim_boundaries",
            _normalize_unique_enum_tuple(self.claim_boundaries, label="claim boundary"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if self.source_system not in WAVE_SIX_DONOR_SOURCE_SYSTEMS:
            raise ValueError(
                "Wave 6 donor contributions must come from an expected donor source."
            )
        if not self.supported_loop_stages:
            raise ValueError("Donor contributions require at least one loop stage.")
        if not self.supplied_capability_areas:
            raise ValueError("Donor contributions require capability coverage.")
        if not self.supplied_artifact_kinds:
            raise ValueError("Donor contributions require artifact coverage.")
        if not self.evidence_ids:
            raise ValueError("Donor contributions require evidence ids.")
        if not self.integration_risks:
            raise ValueError("Donor contributions must name integration risks.")
        missing_boundaries = tuple(
            boundary
            for boundary in WAVE_SIX_REQUIRED_CLAIM_BOUNDARIES
            if boundary not in self.claim_boundaries
        )
        if missing_boundaries:
            raise ValueError(
                "Donor contributions must preserve required claim boundary: "
                f"{missing_boundaries[0].value}"
            )

    @property
    def review_ready(self) -> bool:
        """Return whether this contribution can be used in Wave 6 review."""

        return self.decision in {
            WaveSixDecisionState.READY_FOR_WAVE_SIX_LOOP,
            WaveSixDecisionState.READY_FOR_INDEPENDENT_REVIEW,
        }

    @property
    def blocked(self) -> bool:
        """Return whether this donor contribution blocks progress."""

        return self.decision is WaveSixDecisionState.BLOCKED

    def to_contract_artifact(self) -> WaveSixContractArtifact:
        """Convert the donor contribution into a Wave 6 contract artifact."""

        return WaveSixContractArtifact(
            artifact_id=f"donor-artifact-{self.contribution_id}",
            kind=WaveSixArtifactKind.DONOR_TRACEABILITY_MAP,
            capability_area=WaveSixCapabilityArea.DONOR_TRACEABILITY,
            source_system=self.source_system,
            summary=self.contribution_summary,
            loop_stages=self.supported_loop_stages,
            evidence_ids=self.evidence_ids,
            produced_by_engine_id=self.produced_by_engine_id,
            decision=self.decision,
            claim_boundaries=self.claim_boundaries,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic payload for donor traceability review."""

        return {
            "claim_boundaries": [boundary.value for boundary in self.claim_boundaries],
            "contribution_id": self.contribution_id,
            "contribution_summary": self.contribution_summary,
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "integration_risks": [risk.value for risk in self.integration_risks],
            "mitigation_summary": self.mitigation_summary,
            "produced_by_engine_id": self.produced_by_engine_id,
            "repo_name": self.repo_name,
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "supplied_artifact_kinds": [
                kind.value for kind in self.supplied_artifact_kinds
            ],
            "supplied_capability_areas": [
                area.value for area in self.supplied_capability_areas
            ],
            "supported_loop_stages": [
                stage.value for stage in self.supported_loop_stages
            ],
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this contribution."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveSixDonorTraceabilityMap:
    """Deterministic map of donor repos into the Wave 6 attempt."""

    map_id: str
    contributions: tuple[WaveSixDonorContribution, ...]
    required_donor_sources: tuple[WaveSixSourceSystem, ...] = (
        WAVE_SIX_DONOR_SOURCE_SYSTEMS
    )
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_SIX_DONOR_TRACEABILITY_MAP_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate donor map uniqueness and deterministic ordering."""

        object.__setattr__(self, "map_id", _require_non_empty(self.map_id, "map_id"))
        if not self.contributions:
            raise ValueError(
                "Donor traceability maps require at least one contribution."
            )
        sorted_contributions = tuple(
            sorted(
                self.contributions,
                key=lambda contribution: contribution.contribution_id,
            )
        )
        _unique_ids(
            (contribution.contribution_id for contribution in sorted_contributions),
            label="contribution_id",
        )
        _unique_ids(
            (contribution.source_system for contribution in sorted_contributions),
            label="source_system",
        )
        object.__setattr__(self, "contributions", sorted_contributions)
        object.__setattr__(
            self,
            "required_donor_sources",
            _normalize_unique_enum_tuple(
                self.required_donor_sources, label="required donor source"
            ),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="donor map note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )

    @property
    def contribution_ids(self) -> tuple[str, ...]:
        """Return contribution ids in deterministic order."""

        return tuple(
            contribution.contribution_id for contribution in self.contributions
        )

    @property
    def source_systems_present(self) -> tuple[WaveSixSourceSystem, ...]:
        """Return donor source systems present in deterministic order."""

        present = {contribution.source_system for contribution in self.contributions}
        return tuple(
            source for source in self.required_donor_sources if source in present
        )

    @property
    def missing_source_systems(self) -> tuple[WaveSixSourceSystem, ...]:
        """Return required donor systems not represented in the map."""

        present = {contribution.source_system for contribution in self.contributions}
        return tuple(
            source for source in self.required_donor_sources if source not in present
        )

    @property
    def blocked_contribution_ids(self) -> tuple[str, ...]:
        """Return blocked donor contribution ids."""

        return tuple(
            contribution.contribution_id
            for contribution in self.contributions
            if contribution.blocked
        )

    @property
    def review_ready_contribution_ids(self) -> tuple[str, ...]:
        """Return donor contribution ids ready for review."""

        return tuple(
            contribution.contribution_id
            for contribution in self.contributions
            if contribution.review_ready
        )

    @property
    def all_required_sources_present(self) -> bool:
        """Return whether every expected donor repo is represented."""

        return not self.missing_source_systems

    @property
    def has_no_blocked_contributions(self) -> bool:
        """Return whether no donor contribution blocks the map."""

        return not self.blocked_contribution_ids

    @property
    def ready_for_contract_bundle(self) -> bool:
        """Return whether donor artifacts may feed contract-bundle assembly."""

        return self.all_required_sources_present and self.has_no_blocked_contributions

    @property
    def represented_loop_stages(self) -> tuple[WaveSixLoopStage, ...]:
        """Return loop stages represented by donor contributions."""

        represented = {
            stage
            for contribution in self.contributions
            for stage in contribution.supported_loop_stages
        }
        return tuple(stage for stage in WaveSixLoopStage if stage in represented)

    @property
    def represented_capability_areas(self) -> tuple[WaveSixCapabilityArea, ...]:
        """Return capability areas represented by donor contributions."""

        represented = {
            area
            for contribution in self.contributions
            for area in contribution.supplied_capability_areas
        }
        return tuple(area for area in WaveSixCapabilityArea if area in represented)

    @property
    def represented_artifact_kinds(self) -> tuple[WaveSixArtifactKind, ...]:
        """Return artifact kinds represented by donor contributions."""

        represented = {
            kind
            for contribution in self.contributions
            for kind in contribution.supplied_artifact_kinds
        }
        return tuple(kind for kind in WaveSixArtifactKind if kind in represented)

    def contribution_for_source(
        self, source_system: WaveSixSourceSystem
    ) -> WaveSixDonorContribution | None:
        """Return the donor contribution for a source system, if present."""

        for contribution in self.contributions:
            if contribution.source_system is source_system:
                return contribution
        return None

    def to_contract_artifacts(self) -> tuple[WaveSixContractArtifact, ...]:
        """Return donor traceability artifacts for contract bundle assembly."""

        return tuple(
            contribution.to_contract_artifact() for contribution in self.contributions
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic payload for hashing and review."""

        return {
            "blocked_contribution_ids": list(self.blocked_contribution_ids),
            "contributions": [
                contribution.canonical_payload() for contribution in self.contributions
            ],
            "map_id": self.map_id,
            "missing_source_systems": [
                source.value for source in self.missing_source_systems
            ],
            "notes": list(self.notes),
            "ready_for_contract_bundle": self.ready_for_contract_bundle,
            "required_donor_sources": [
                source.value for source in self.required_donor_sources
            ],
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this donor map."""

        return _stable_sha256(self.canonical_payload())


def build_wave_six_donor_traceability_map(
    *,
    map_id: str,
    contributions: Iterable[WaveSixDonorContribution],
    notes: Iterable[str] = (),
) -> WaveSixDonorTraceabilityMap:
    """Build a deterministic donor traceability map."""

    return WaveSixDonorTraceabilityMap(
        map_id=map_id,
        contributions=tuple(contributions),
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
