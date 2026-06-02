"""Integrated Wave 3 substrate result for IX-CognitionKernel.

Wave 3 is earned only when the separately tested governance layers coordinate as
one reviewable substrate: engine coordination, bounded role tribunal, reward
audit, curriculum, discovery, memory quarantine, skill genome governance,
WorldTwin scenario reasoning, BlackFox handoff, and assurance evidence. This
module integrates those records without creating execution authority or claiming
AGI. The result is ready only for a later readiness snapshot, not deployment.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, TypeVar

from ix_cognition_kernel.wave3_agent_artifacts import RoleArtifactBundle
from ix_cognition_kernel.wave3_assurance import AssuranceRecordBundle
from ix_cognition_kernel.wave3_blackfox_handoff import BlackFoxHandoffBundle
from ix_cognition_kernel.wave3_contracts import (
    WaveThreeArtifactBundle,
    WaveThreeArtifactKind,
    WaveThreeArtifactRef,
    WaveThreeAuthorityState,
)
from ix_cognition_kernel.wave3_coordinator import (
    WaveThreeCoordinationResult,
    WaveThreeCoordinationStatus,
)
from ix_cognition_kernel.wave3_curriculum import CurriculumTaskBundle
from ix_cognition_kernel.wave3_discovery import DiscoveryRecordBundle
from ix_cognition_kernel.wave3_memory_integration import MemoryRoleDecisionBundle
from ix_cognition_kernel.wave3_reward_audit import RewardAuditRecord
from ix_cognition_kernel.wave3_skill_governance import SkillGenomeUpdateBundle
from ix_cognition_kernel.wave3_tribunal import TribunalDecisionRecord
from ix_cognition_kernel.wave3_worldtwin import WorldTwinScenarioBundle

T = TypeVar("T")

WAVE_THREE_SUBSTRATE_SCHEMA_VERSION = "ix-cognition-kernel-wave3-substrate-v1"

CORE_WAVE_THREE_ARTIFACT_KINDS: tuple[WaveThreeArtifactKind, ...] = (
    WaveThreeArtifactKind.ENGINE_COORDINATION,
    WaveThreeArtifactKind.ROLE_ARTIFACT,
    WaveThreeArtifactKind.TRIBUNAL_RECORD,
    WaveThreeArtifactKind.REWARD_AUDIT,
    WaveThreeArtifactKind.CURRICULUM_TASK,
    WaveThreeArtifactKind.DISCOVERY_RECORD,
    WaveThreeArtifactKind.MEMORY_QUARANTINE_DECISION,
    WaveThreeArtifactKind.SKILL_GENOME_UPDATE,
    WaveThreeArtifactKind.WORLDTWIN_SCENARIO,
    WaveThreeArtifactKind.BLACKFOX_HANDOFF,
    WaveThreeArtifactKind.ASSURANCE_RECORD,
)


class WaveThreeSubstrateStatus(StrEnum):
    """Fail-closed status for the integrated Wave 3 substrate."""

    READY_FOR_READINESS_SNAPSHOT = "ready-for-readiness-snapshot"
    NEEDS_EVIDENCE = "needs-evidence"
    BLOCKED = "blocked"


class _ArtifactBundleProducer(Protocol):
    """Protocol for records that can export a shared artifact bundle."""

    def to_artifact_bundle(self, *, artifact_bundle_id: str) -> WaveThreeArtifactBundle:
        """Return a shared Wave 3 artifact bundle."""


@dataclass(frozen=True, slots=True)
class WaveThreeSubstrateResult:
    """Integrated, review-only Wave 3 substrate coordination result."""

    substrate_id: str
    coordination_result: WaveThreeCoordinationResult
    role_artifact_bundle: RoleArtifactBundle
    tribunal_record: TribunalDecisionRecord
    reward_audit: RewardAuditRecord
    curriculum_bundle: CurriculumTaskBundle
    discovery_bundle: DiscoveryRecordBundle
    memory_decision_bundle: MemoryRoleDecisionBundle
    skill_update_bundle: SkillGenomeUpdateBundle
    worldtwin_bundle: WorldTwinScenarioBundle
    blackfox_handoff_bundle: BlackFoxHandoffBundle
    assurance_bundle: AssuranceRecordBundle
    evidence_ids: tuple[str, ...]
    required_artifact_kinds: tuple[WaveThreeArtifactKind, ...] = (
        CORE_WAVE_THREE_ARTIFACT_KINDS
    )
    schema_version: str = WAVE_THREE_SUBSTRATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate substrate identity, artifact coverage, and review boundary."""

        object.__setattr__(
            self, "substrate_id", _text(self.substrate_id, "substrate_id")
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="substrate evidence_id"),
        )
        object.__setattr__(
            self,
            "required_artifact_kinds",
            _unique_artifact_kinds(
                self.required_artifact_kinds, label="required artifact kind"
            ),
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        _validate_no_automatic_execution(self.component_artifact_bundles)
        _validate_human_authority_boundary(self.component_artifact_bundles)

    @property
    def component_artifact_bundles(self) -> tuple[WaveThreeArtifactBundle, ...]:
        """Return all shared artifact bundles represented by the substrate."""

        bundles = (
            self.coordination_result.artifact_bundle,
            self.role_artifact_bundle.to_artifact_bundle(
                artifact_bundle_id=f"{self.substrate_id}:role-artifacts"
            ),
            self.tribunal_record.to_artifact_bundle(
                artifact_bundle_id=f"{self.substrate_id}:tribunal-artifacts"
            ),
            self.reward_audit.to_artifact_bundle(
                artifact_bundle_id=f"{self.substrate_id}:reward-artifacts"
            ),
            self.curriculum_bundle.to_artifact_bundle(
                artifact_bundle_id=f"{self.substrate_id}:curriculum-artifacts"
            ),
            self.discovery_bundle.to_artifact_bundle(
                artifact_bundle_id=f"{self.substrate_id}:discovery-artifacts"
            ),
            self.memory_decision_bundle.to_artifact_bundle(
                artifact_bundle_id=f"{self.substrate_id}:memory-artifacts"
            ),
            self.skill_update_bundle.to_artifact_bundle(
                artifact_bundle_id=f"{self.substrate_id}:skill-artifacts"
            ),
            self.worldtwin_bundle.to_artifact_bundle(
                artifact_bundle_id=f"{self.substrate_id}:worldtwin-artifacts"
            ),
            self.blackfox_handoff_bundle.to_artifact_bundle(
                artifact_bundle_id=f"{self.substrate_id}:blackfox-artifacts"
            ),
            self.assurance_bundle.to_artifact_bundle(
                artifact_bundle_id=f"{self.substrate_id}:assurance-artifacts"
            ),
        )
        return tuple(sorted(bundles, key=lambda bundle: bundle.bundle_id))

    @property
    def artifacts(self) -> tuple[WaveThreeArtifactRef, ...]:
        """Return all artifact refs from all component bundles."""

        return tuple(
            artifact
            for bundle in self.component_artifact_bundles
            for artifact in bundle.artifacts
        )

    @property
    def artifact_ids(self) -> tuple[str, ...]:
        """Return all artifact ids in deterministic order."""

        return tuple(sorted(artifact.artifact_id for artifact in self.artifacts))

    @property
    def represented_artifact_kinds(self) -> tuple[WaveThreeArtifactKind, ...]:
        """Return represented artifact kinds in required-kind order."""

        present = {artifact.kind for artifact in self.artifacts}
        required_order = tuple(
            kind for kind in self.required_artifact_kinds if kind in present
        )
        extra_order = tuple(
            sorted(
                (kind for kind in present if kind not in set(required_order)),
                key=lambda kind: kind.value,
            )
        )
        return required_order + extra_order

    @property
    def missing_required_artifact_kinds(self) -> tuple[WaveThreeArtifactKind, ...]:
        """Return required artifact kinds missing from the integrated substrate."""

        present = {artifact.kind for artifact in self.artifacts}
        return tuple(
            kind for kind in self.required_artifact_kinds if kind not in present
        )

    @property
    def blocked_artifact_ids(self) -> tuple[str, ...]:
        """Return component artifact ids that block substrate progress."""

        return tuple(
            artifact.artifact_id
            for artifact in self.artifacts
            if artifact.blocks_progress
        )

    @property
    def non_reviewable_artifact_ids(self) -> tuple[str, ...]:
        """Return component artifact ids not ready for human review."""

        return tuple(
            artifact.artifact_id
            for artifact in self.artifacts
            if not artifact.ready_for_human_review
        )

    @property
    def executable_artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids that incorrectly attempt automatic execution."""

        return tuple(
            artifact.artifact_id
            for artifact in self.artifacts
            if artifact.allowed_for_automatic_execution
        )

    @property
    def component_fingerprints(self) -> Mapping[str, str]:
        """Return deterministic fingerprints for each component bundle."""

        return {
            bundle.bundle_id: bundle.fingerprint()
            for bundle in self.component_artifact_bundles
        }

    @property
    def component_readiness_gaps(self) -> tuple[str, ...]:
        """Return readiness gaps from every component record and bundle."""

        gaps: list[str] = []
        gaps.extend(self.coordination_result.readiness_gaps)
        gaps.extend(self.coordination_result.blocking_gaps)
        gaps.extend(self.role_artifact_bundle.readiness_gaps)
        gaps.extend(self.tribunal_record.readiness_gaps)
        gaps.extend(self.tribunal_record.blocking_gaps)
        gaps.extend(self.reward_audit.readiness_gaps)
        gaps.extend(self.reward_audit.blocking_gaps)
        gaps.extend(self.curriculum_bundle.readiness_gaps)
        gaps.extend(self.discovery_bundle.readiness_gaps)
        gaps.extend(self.memory_decision_bundle.readiness_gaps)
        gaps.extend(self.skill_update_bundle.readiness_gaps)
        gaps.extend(self.worldtwin_bundle.readiness_gaps)
        gaps.extend(self.blackfox_handoff_bundle.readiness_gaps)
        gaps.extend(self.assurance_bundle.readiness_gaps)
        return tuple(gaps)

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted unique substrate and component evidence ids."""

        artifact_evidence = {
            evidence_id
            for artifact in self.artifacts
            for evidence_id in artifact.evidence_ids
        }
        bundle_evidence = {
            link.evidence_id
            for bundle in self.component_artifact_bundles
            for link in bundle.evidence_links
        }
        return tuple(
            sorted(set(self.evidence_ids).union(artifact_evidence, bundle_evidence))
        )

    @property
    def permits_automatic_execution(self) -> bool:
        """Return whether the integrated substrate permits automatic execution."""

        return False

    @property
    def certifies_agi(self) -> bool:
        """Return whether the integrated substrate certifies AGI."""

        return False

    @property
    def human_authority_state(self) -> WaveThreeAuthorityState:
        """Return aggregate human-authority state for the substrate."""

        if self.status is WaveThreeSubstrateStatus.BLOCKED:
            return WaveThreeAuthorityState.BLOCKED
        return WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return non-blocking gaps that prevent readiness-snapshot preparation."""

        gaps: list[str] = []
        if not self.evidence_ids:
            gaps.append(f"{self.substrate_id} has no top-level evidence ids")
        if self.missing_required_artifact_kinds:
            gaps.append(
                "integrated substrate missing artifact kinds: "
                + ", ".join(kind.value for kind in self.missing_required_artifact_kinds)
            )
        if self.non_reviewable_artifact_ids:
            gaps.append(
                "integrated substrate has non-reviewable artifacts: "
                + ", ".join(self.non_reviewable_artifact_ids)
            )
        gaps.extend(self.component_readiness_gaps)
        return tuple(_dedupe_preserve_order(gaps))

    @property
    def blocking_gaps(self) -> tuple[str, ...]:
        """Return blocking gaps that stop substrate progress."""

        gaps: list[str] = []
        if self.blocked_artifact_ids:
            gaps.append(
                "integrated substrate has blocked artifacts: "
                + ", ".join(self.blocked_artifact_ids)
            )
        if self.executable_artifact_ids:
            gaps.append(
                "integrated substrate artifacts attempted automatic execution: "
                + ", ".join(self.executable_artifact_ids)
            )
        if self.coordination_result.status is WaveThreeCoordinationStatus.BLOCKED:
            gaps.append("engine coordination result is blocked")
        return tuple(_dedupe_preserve_order(gaps))

    @property
    def status(self) -> WaveThreeSubstrateStatus:
        """Return the fail-closed integrated substrate status."""

        if self.blocking_gaps:
            return WaveThreeSubstrateStatus.BLOCKED
        if self.readiness_gaps:
            return WaveThreeSubstrateStatus.NEEDS_EVIDENCE
        return WaveThreeSubstrateStatus.READY_FOR_READINESS_SNAPSHOT

    @property
    def ready_for_readiness_snapshot(self) -> bool:
        """Return whether a Wave 3 readiness snapshot can be produced next."""

        return self.status is WaveThreeSubstrateStatus.READY_FOR_READINESS_SNAPSHOT

    @property
    def review_summary(self) -> str:
        """Return a concise human-review summary for the integrated substrate."""

        return (
            f"{self.substrate_id}: {self.status.value}; "
            f"{len(self.artifacts)} artifacts, "
            f"{len(self.represented_artifact_kinds)}/"
            f"{len(self.required_artifact_kinds)} artifact kinds represented; "
            "automatic execution and AGI certification "
            "are not permitted."
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "all_evidence_ids": list(self.all_evidence_ids),
            "artifact_ids": list(self.artifact_ids),
            "blocking_gaps": list(self.blocking_gaps),
            "certifies_agi": self.certifies_agi,
            "component_fingerprints": dict(self.component_fingerprints),
            "human_authority_state": self.human_authority_state.value,
            "missing_required_artifact_kinds": [
                kind.value for kind in self.missing_required_artifact_kinds
            ],
            "permits_automatic_execution": self.permits_automatic_execution,
            "readiness_gaps": list(self.readiness_gaps),
            "represented_artifact_kinds": [
                kind.value for kind in self.represented_artifact_kinds
            ],
            "required_artifact_kinds": [
                kind.value for kind in self.required_artifact_kinds
            ],
            "review_summary": self.review_summary,
            "schema_version": self.schema_version,
            "status": self.status.value,
            "substrate_id": self.substrate_id,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this substrate result."""

        return _stable_sha256(self.canonical_payload())


def _validate_no_automatic_execution(
    bundles: tuple[WaveThreeArtifactBundle, ...],
) -> None:
    """Reject component artifacts that attempt automatic execution."""

    executable = tuple(
        artifact.artifact_id
        for bundle in bundles
        for artifact in bundle.artifacts
        if artifact.allowed_for_automatic_execution
    )
    if executable:
        raise ValueError(
            "Wave 3 substrate components must not allow automatic execution: "
            + ", ".join(executable)
        )


def _validate_human_authority_boundary(
    bundles: tuple[WaveThreeArtifactBundle, ...],
) -> None:
    """Reject component artifacts that bypass human-authority awareness."""

    bypasses = tuple(
        artifact.artifact_id
        for bundle in bundles
        for artifact in bundle.artifacts
        if not artifact.requires_human_authority
    )
    if bypasses:
        raise ValueError(
            "Wave 3 substrate components must require human authority: "
            + ", ".join(bypasses)
        )


def _text(value: str, label: str) -> str:
    """Return stripped text or raise when empty."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _unique_text(values: Iterable[str], *, label: str) -> tuple[str, ...]:
    """Normalize text tuples while rejecting blanks and duplicates."""

    normalized = tuple(_text(value, label) for value in values)
    _unique_values(normalized, label=label)
    return normalized


def _unique_artifact_kinds(
    values: Iterable[WaveThreeArtifactKind], *, label: str
) -> tuple[WaveThreeArtifactKind, ...]:
    """Normalize artifact-kind tuples while rejecting duplicates."""

    normalized = tuple(values)
    if not normalized:
        raise ValueError("Wave 3 substrate requires artifact kinds.")
    _unique_values(normalized, label=label)
    return normalized


def _unique_values(values: Iterable[T], *, label: str) -> set[T]:
    """Return unique values while rejecting duplicates."""

    seen: set[T] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value}")
        seen.add(value)
    return seen


def _dedupe_preserve_order(values: Iterable[str]) -> tuple[str, ...]:
    """Return unique text values while preserving first occurrence order."""

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            normalized.append(value)
            seen.add(value)
    return tuple(normalized)


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
