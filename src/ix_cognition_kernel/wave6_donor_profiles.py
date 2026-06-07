"""Canonical Wave 6 donor profiles.

The donor traceability map should not rely on ad-hoc strings scattered across
integration code. This module locks a small, deterministic profile catalog for
the seven uploaded donor repos so later Wave 6 commits can reference stable
source-system identities, loop-stage responsibilities, risks, and mitigations.
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
    WaveSixArtifactKind,
    WaveSixCapabilityArea,
    WaveSixLoopStage,
    WaveSixSourceSystem,
)
from ix_cognition_kernel.wave6_donor_traceability import (
    WaveSixDonorContribution,
    WaveSixDonorIntegrationRisk,
    WaveSixDonorTraceabilityMap,
    build_wave_six_donor_traceability_map,
)

E = TypeVar("E", bound=StrEnum)

WAVE_SIX_DONOR_PROFILE_SCHEMA_VERSION = "ix-cognition-kernel-wave6-donor-profile-v1"
WAVE_SIX_CANONICAL_DONOR_MAP_ID = "wave6-canonical-donor-traceability-map"


@dataclass(frozen=True, slots=True)
class WaveSixDonorProfile:
    """Stable profile for one donor repo's bounded Wave 6 role."""

    source_system: WaveSixSourceSystem
    repo_name: str
    primary_role: str
    supported_loop_stages: tuple[WaveSixLoopStage, ...]
    supplied_capability_areas: tuple[WaveSixCapabilityArea, ...]
    supplied_artifact_kinds: tuple[WaveSixArtifactKind, ...]
    default_integration_risks: tuple[WaveSixDonorIntegrationRisk, ...]
    mitigation_summary: str
    schema_version: str = WAVE_SIX_DONOR_PROFILE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate that the profile is explicit, bounded, and donor-only."""

        if self.source_system not in WAVE_SIX_DONOR_SOURCE_SYSTEMS:
            raise ValueError("Wave 6 donor profiles must use an expected donor source.")
        object.__setattr__(
            self, "repo_name", _require_non_empty(self.repo_name, "repo_name")
        )
        object.__setattr__(
            self,
            "primary_role",
            _require_non_empty(self.primary_role, "primary_role"),
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
            "default_integration_risks",
            _normalize_unique_enum_tuple(
                self.default_integration_risks, label="default integration risk"
            ),
        )
        object.__setattr__(
            self,
            "mitigation_summary",
            _require_non_empty(self.mitigation_summary, "mitigation_summary"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.supported_loop_stages:
            raise ValueError("Wave 6 donor profiles require loop-stage coverage.")
        if not self.supplied_capability_areas:
            raise ValueError("Wave 6 donor profiles require capability coverage.")
        if not self.supplied_artifact_kinds:
            raise ValueError("Wave 6 donor profiles require artifact coverage.")
        if not self.default_integration_risks:
            raise ValueError("Wave 6 donor profiles require named integration risks.")

    @property
    def profile_id(self) -> str:
        """Return the deterministic profile id for this donor."""

        return f"profile-{self.source_system.value}"

    def contribution_id(self) -> str:
        """Return the deterministic donor contribution id."""

        return f"canonical-{self.source_system.value}"

    def default_evidence_ids(self) -> tuple[str, ...]:
        """Return deterministic evidence ids for the donor profile."""

        return (
            f"wave6-donor-profile:{self.source_system.value}",
            f"wave6-donor-role:{self.source_system.value}",
        )

    def to_contribution(self) -> WaveSixDonorContribution:
        """Convert the profile into a review-gated donor contribution."""

        return WaveSixDonorContribution(
            contribution_id=self.contribution_id(),
            source_system=self.source_system,
            repo_name=self.repo_name,
            contribution_summary=f"{self.repo_name}: {self.primary_role}",
            supported_loop_stages=self.supported_loop_stages,
            supplied_capability_areas=self.supplied_capability_areas,
            supplied_artifact_kinds=self.supplied_artifact_kinds,
            evidence_ids=self.default_evidence_ids(),
            integration_risks=self.default_integration_risks,
            mitigation_summary=self.mitigation_summary,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic payload for profile hashing."""

        return {
            "default_evidence_ids": list(self.default_evidence_ids()),
            "default_integration_risks": [
                risk.value for risk in self.default_integration_risks
            ],
            "mitigation_summary": self.mitigation_summary,
            "primary_role": self.primary_role,
            "profile_id": self.profile_id,
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
        """Return deterministic SHA-256 fingerprint for this profile."""

        return _stable_sha256(self.canonical_payload())


def canonical_wave_six_donor_profiles() -> tuple[WaveSixDonorProfile, ...]:
    """Return the locked donor profile catalog in required donor order."""

    return (
        WaveSixDonorProfile(
            source_system=WaveSixSourceSystem.IX_FUNCTION,
            repo_name="IX-Function",
            primary_role=(
                "cross-domain transfer, negative controls, and falsification "
                "pressure for learned causal structures"
            ),
            supported_loop_stages=(
                WaveSixLoopStage.TRANSFER_CHECK,
                WaveSixLoopStage.FALSIFICATION,
            ),
            supplied_capability_areas=(
                WaveSixCapabilityArea.CROSS_DOMAIN_TRANSFER,
                WaveSixCapabilityArea.NOVELTY_PRESSURE,
                WaveSixCapabilityArea.FALSIFICATION_DISCIPLINE,
            ),
            supplied_artifact_kinds=(
                WaveSixArtifactKind.TRANSFER_NOVELTY_RECORD,
                WaveSixArtifactKind.FALSIFICATION_RECORD,
                WaveSixArtifactKind.DONOR_TRACEABILITY_MAP,
            ),
            default_integration_risks=(
                WaveSixDonorIntegrationRisk.SCHEMA_DRIFT,
                WaveSixDonorIntegrationRisk.DECORATIVE_HANDOFF,
            ),
            mitigation_summary=(
                "Bind transfer claims to explicit source-domain, target-domain, "
                "negative-control, and falsification records."
            ),
        ),
        WaveSixDonorProfile(
            source_system=WaveSixSourceSystem.IX_INTENT_REALITY_LOOP,
            repo_name="IX-IntentRealityLoop",
            primary_role=(
                "intent, permission, feedback, outcome delta, and memory binding "
                "without autonomous authority"
            ),
            supported_loop_stages=(
                WaveSixLoopStage.INTENT,
                WaveSixLoopStage.PERMISSION,
                WaveSixLoopStage.OUTCOME,
                WaveSixLoopStage.DELTA,
                WaveSixLoopStage.MEMORY_UPDATE,
            ),
            supplied_capability_areas=(
                WaveSixCapabilityArea.MASTER_LOOP,
                WaveSixCapabilityArea.REALITY_CORRECTED_REASONING,
                WaveSixCapabilityArea.FUTURE_REASONING_CHANGE,
            ),
            supplied_artifact_kinds=(
                WaveSixArtifactKind.MASTER_LOOP_CONTRACT,
                WaveSixArtifactKind.REALITY_CORRECTION_RECORD,
                WaveSixArtifactKind.FUTURE_REASONING_CHANGE_PROOF,
                WaveSixArtifactKind.DONOR_TRACEABILITY_MAP,
            ),
            default_integration_risks=(
                WaveSixDonorIntegrationRisk.MISSING_REALITY_CORRECTION,
                WaveSixDonorIntegrationRisk.OVERCLAIMED_CAPABILITY,
            ),
            mitigation_summary=(
                "Require explicit measured-reality signals before any future "
                "reasoning change can be counted."
            ),
        ),
        WaveSixDonorProfile(
            source_system=WaveSixSourceSystem.IX_BLACKFOX,
            repo_name="IX-BlackFox",
            primary_role=(
                "policy-gated execution control, evidence receipts, CI binding, "
                "and human review boundaries"
            ),
            supported_loop_stages=(
                WaveSixLoopStage.TRIAL,
                WaveSixLoopStage.FALSIFICATION,
                WaveSixLoopStage.HUMAN_REVIEW,
            ),
            supplied_capability_areas=(
                WaveSixCapabilityArea.HUMAN_AUTHORITY_PRESERVATION,
                WaveSixCapabilityArea.INDEPENDENT_REVIEW_READINESS,
                WaveSixCapabilityArea.FALSIFICATION_DISCIPLINE,
            ),
            supplied_artifact_kinds=(
                WaveSixArtifactKind.FALSIFICATION_RECORD,
                WaveSixArtifactKind.HUMAN_REVIEW_DOCKET,
                WaveSixArtifactKind.INDEPENDENT_REVIEW_PACKET,
                WaveSixArtifactKind.DONOR_TRACEABILITY_MAP,
            ),
            default_integration_risks=(
                WaveSixDonorIntegrationRisk.MESSY_GLUE_CODE,
                WaveSixDonorIntegrationRisk.MISSING_HUMAN_REVIEW,
            ),
            mitigation_summary=(
                "Treat model output as untrusted input and preserve fail-closed "
                "human approval gates."
            ),
        ),
        WaveSixDonorProfile(
            source_system=WaveSixSourceSystem.IX_BLACKFOX_COGNITION,
            repo_name="IX-BlackFox-Cognition",
            primary_role=(
                "belief, plan, memory, sentinel, authority, and self-improvement "
                "airlock primitives"
            ),
            supported_loop_stages=(
                WaveSixLoopStage.PREDICTION,
                WaveSixLoopStage.MEMORY_UPDATE,
                WaveSixLoopStage.HUMAN_REVIEW,
            ),
            supplied_capability_areas=(
                WaveSixCapabilityArea.MEASURED_SYSTEM_LEVEL_COGNITION,
                WaveSixCapabilityArea.REALITY_CORRECTED_REASONING,
                WaveSixCapabilityArea.HUMAN_AUTHORITY_PRESERVATION,
            ),
            supplied_artifact_kinds=(
                WaveSixArtifactKind.MEASURED_COGNITION_RECORD,
                WaveSixArtifactKind.FUTURE_REASONING_CHANGE_PROOF,
                WaveSixArtifactKind.HUMAN_REVIEW_DOCKET,
                WaveSixArtifactKind.DONOR_TRACEABILITY_MAP,
            ),
            default_integration_risks=(
                WaveSixDonorIntegrationRisk.DECORATIVE_HANDOFF,
                WaveSixDonorIntegrationRisk.OVERCLAIMED_CAPABILITY,
            ),
            mitigation_summary=(
                "Use cognition primitives only when future reasoning changes are "
                "observable in deterministic records."
            ),
        ),
        WaveSixDonorProfile(
            source_system=WaveSixSourceSystem.IX_BLACKFOX_WORLDTWIN,
            repo_name="IX-BlackFox-WorldTwin",
            primary_role=(
                "scenario assumptions, prediction receipts, simulated outcomes, "
                "and reality-delta comparison"
            ),
            supported_loop_stages=(
                WaveSixLoopStage.PREDICTION,
                WaveSixLoopStage.TRIAL,
                WaveSixLoopStage.OUTCOME,
                WaveSixLoopStage.DELTA,
            ),
            supplied_capability_areas=(
                WaveSixCapabilityArea.MEASURED_SYSTEM_LEVEL_COGNITION,
                WaveSixCapabilityArea.REALITY_CORRECTED_REASONING,
                WaveSixCapabilityArea.FUTURE_REASONING_CHANGE,
            ),
            supplied_artifact_kinds=(
                WaveSixArtifactKind.MEASURED_COGNITION_RECORD,
                WaveSixArtifactKind.REALITY_CORRECTION_RECORD,
                WaveSixArtifactKind.DONOR_TRACEABILITY_MAP,
            ),
            default_integration_risks=(
                WaveSixDonorIntegrationRisk.NON_DETERMINISTIC_EVIDENCE,
                WaveSixDonorIntegrationRisk.MISSING_REALITY_CORRECTION,
            ),
            mitigation_summary=(
                "Require deterministic prediction receipts and explicit "
                "prediction-vs-outcome deltas."
            ),
        ),
        WaveSixDonorProfile(
            source_system=WaveSixSourceSystem.IX_AUTONOMY_ASSURANCE_RUNTIME,
            repo_name="IX-Autonomy-Assurance-Case-Runtime",
            primary_role=(
                "assurance-case traceability, hazards, controls, safety gates, "
                "verification, and ledger discipline"
            ),
            supported_loop_stages=(
                WaveSixLoopStage.PERMISSION,
                WaveSixLoopStage.TRIAL,
                WaveSixLoopStage.FALSIFICATION,
                WaveSixLoopStage.HUMAN_REVIEW,
            ),
            supplied_capability_areas=(
                WaveSixCapabilityArea.FALSIFICATION_DISCIPLINE,
                WaveSixCapabilityArea.HUMAN_AUTHORITY_PRESERVATION,
                WaveSixCapabilityArea.INDEPENDENT_REVIEW_READINESS,
            ),
            supplied_artifact_kinds=(
                WaveSixArtifactKind.FALSIFICATION_RECORD,
                WaveSixArtifactKind.HUMAN_REVIEW_DOCKET,
                WaveSixArtifactKind.INDEPENDENT_REVIEW_PACKET,
                WaveSixArtifactKind.DONOR_TRACEABILITY_MAP,
            ),
            default_integration_risks=(
                WaveSixDonorIntegrationRisk.SCHEMA_DRIFT,
                WaveSixDonorIntegrationRisk.MISSING_HUMAN_REVIEW,
            ),
            mitigation_summary=(
                "Keep safety gates explicit and prevent assurance evidence from "
                "becoming a certification claim."
            ),
        ),
        WaveSixDonorProfile(
            source_system=WaveSixSourceSystem.IX_MAIN,
            repo_name="IX-main",
            primary_role=(
                "readable intent and behavior contracts that keep the master loop "
                "inspectable by humans"
            ),
            supported_loop_stages=(
                WaveSixLoopStage.INTENT,
                WaveSixLoopStage.PERMISSION,
                WaveSixLoopStage.HUMAN_REVIEW,
            ),
            supplied_capability_areas=(
                WaveSixCapabilityArea.MASTER_LOOP,
                WaveSixCapabilityArea.HUMAN_AUTHORITY_PRESERVATION,
                WaveSixCapabilityArea.INDEPENDENT_REVIEW_READINESS,
            ),
            supplied_artifact_kinds=(
                WaveSixArtifactKind.MASTER_LOOP_CONTRACT,
                WaveSixArtifactKind.CLAIM_BOUNDARY_DECLARATION,
                WaveSixArtifactKind.HUMAN_REVIEW_DOCKET,
                WaveSixArtifactKind.DONOR_TRACEABILITY_MAP,
            ),
            default_integration_risks=(
                WaveSixDonorIntegrationRisk.OVERCLAIMED_CAPABILITY,
                WaveSixDonorIntegrationRisk.MESSY_GLUE_CODE,
            ),
            mitigation_summary=(
                "Use readable contracts as review artifacts, not as proof of "
                "intelligence by themselves."
            ),
        ),
    )


def canonical_wave_six_donor_profile_for_source(
    source_system: WaveSixSourceSystem,
) -> WaveSixDonorProfile | None:
    """Return the canonical profile for a donor source, if present."""

    for profile in canonical_wave_six_donor_profiles():
        if profile.source_system is source_system:
            return profile
    return None


def build_canonical_wave_six_donor_traceability_map() -> WaveSixDonorTraceabilityMap:
    """Build the canonical donor traceability map from locked profiles."""

    return build_wave_six_donor_traceability_map(
        map_id=WAVE_SIX_CANONICAL_DONOR_MAP_ID,
        contributions=(
            profile.to_contribution()
            for profile in canonical_wave_six_donor_profiles()
        ),
        notes=(
            "Canonical donor map for the Wave 6 measured system-level cognition "
            "attempt; donor repos are profiled without direct runtime coupling.",
        ),
    )


def _require_non_empty(value: str, label: str) -> str:
    """Return stripped text or raise when empty."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


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


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
