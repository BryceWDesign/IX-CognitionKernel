"""Wave 3 readiness snapshot for IX-CognitionKernel.

Wave 3 is only earned when the integrated substrate is ready for a readiness
snapshot and the snapshot itself preserves the same boundaries: human review is
required, automatic execution is forbidden, AGI is not certified, and every
required Wave 3 validation artifact is represented. This module records the
maturity claim; it does not deploy, execute, certify, or advance beyond Wave 3.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.doctrine import (
    WaveDefinition,
    allows_agi_claim,
    wave_by_number,
)
from ix_cognition_kernel.wave3_contracts import (
    WaveThreeArtifactBundle,
    WaveThreeArtifactDecision,
    WaveThreeArtifactKind,
    WaveThreeArtifactRef,
    WaveThreeAuthorityState,
    WaveThreeEvidenceLink,
    WaveThreeEvidenceRelation,
    WaveThreeSourceSystem,
)
from ix_cognition_kernel.wave3_substrate import (
    WaveThreeSubstrateResult,
    WaveThreeSubstrateStatus,
)

T = TypeVar("T")

WAVE_THREE_READINESS_SCHEMA_VERSION = "ix-cognition-kernel-wave3-readiness-v1"

WAVE_THREE_REQUIRED_VALIDATION_ARTIFACT_IDS: tuple[str, ...] = (
    "engine-coordination-records",
    "25-agent-role-artifacts",
    "multi-agent-tribunal-flow",
    "reward-auditor-records",
    "self-play-curriculum-tasks",
    "evaluator-driven-discovery-records",
    "memory-quarantine-role-integration",
    "skill-genome-update-governance",
    "worldtwin-scenario-reasoning",
    "blackfox-handoff-packages",
    "assurance-style-evidence-records",
    "integrated-wave3-substrate-result",
    "adversarial-wave3-failure-scenarios",
)


class WaveThreeReadinessStatus(StrEnum):
    """Fail-closed status for a Wave 3 readiness snapshot."""

    WAVE_THREE_READY = "wave-three-ready"
    NEEDS_EVIDENCE = "needs-evidence"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class WaveThreeReadinessSnapshot:
    """Fail-closed readiness snapshot for the Wave 3 maturity claim."""

    project_name: str
    maturity_wave: WaveDefinition
    substrate_result: WaveThreeSubstrateResult
    validation_artifact_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_THREE_READINESS_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate snapshot identity and minimum Wave 3 evidence structure."""

        object.__setattr__(
            self, "project_name", _text(self.project_name, "project_name")
        )
        if self.project_name != "IX-CognitionKernel":
            raise ValueError("Wave 3 snapshots must use IX-CognitionKernel.")
        if self.maturity_wave.number != 3:
            raise ValueError("Wave 3 readiness snapshots must target Wave 3.")
        object.__setattr__(
            self,
            "validation_artifact_ids",
            _unique_text(
                self.validation_artifact_ids,
                label="validation_artifact_id",
            ),
        )
        missing = tuple(
            artifact_id
            for artifact_id in WAVE_THREE_REQUIRED_VALIDATION_ARTIFACT_IDS
            if artifact_id not in self.validation_artifact_ids
        )
        if missing:
            raise ValueError(
                "Wave 3 readiness snapshots require validation artifact coverage: "
                f"{missing[0]}"
            )
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="readiness evidence_id"),
        )
        object.__setattr__(
            self, "notes", _unique_text(self.notes, label="readiness note")
        )
        object.__setattr__(
            self,
            "schema_version",
            _text(self.schema_version, "schema_version"),
        )

    @property
    def artifact_id(self) -> str:
        """Return the shared Wave 3 artifact id for this readiness snapshot."""

        return "readiness-snapshot:wave-3"

    @property
    def wave_label(self) -> str:
        """Return the Wave 3 maturity label."""

        return self.maturity_wave.label

    @property
    def substrate_artifact_count(self) -> int:
        """Return the number of substrate artifacts covered by the snapshot."""

        return len(self.substrate_result.artifact_ids)

    @property
    def substrate_evidence_count(self) -> int:
        """Return the number of substrate evidence ids covered by the snapshot."""

        return len(self.substrate_result.all_evidence_ids)

    @property
    def represented_substrate_artifact_kinds(self) -> tuple[WaveThreeArtifactKind, ...]:
        """Return artifact kinds represented by the integrated substrate."""

        return self.substrate_result.represented_artifact_kinds

    @property
    def missing_substrate_artifact_kinds(self) -> tuple[WaveThreeArtifactKind, ...]:
        """Return substrate artifact kinds missing before Wave 3 readiness."""

        return self.substrate_result.missing_required_artifact_kinds

    @property
    def permits_automatic_execution(self) -> bool:
        """Return whether this readiness snapshot permits automatic execution."""

        return False

    @property
    def certifies_agi(self) -> bool:
        """Return whether this readiness snapshot certifies AGI."""

        return False

    @property
    def permits_agi_claim(self) -> bool:
        """Return whether this Wave 3 snapshot permits an AGI claim."""

        return allows_agi_claim(self.maturity_wave.number, overwhelming_evidence=False)

    @property
    def human_authority_state(self) -> WaveThreeAuthorityState:
        """Return aggregate human-authority state for this readiness snapshot."""

        if self.status is WaveThreeReadinessStatus.BLOCKED:
            return WaveThreeAuthorityState.BLOCKED
        return WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return non-blocking gaps preventing a Wave 3 readiness claim."""

        gaps: list[str] = []
        if not self.evidence_ids:
            gaps.append("Wave 3 readiness snapshot has no top-level evidence ids")
        if self.substrate_result.status is WaveThreeSubstrateStatus.NEEDS_EVIDENCE:
            gaps.append("integrated Wave 3 substrate still needs evidence")
        if self.missing_substrate_artifact_kinds:
            gaps.append(
                "Wave 3 readiness missing substrate artifact kinds: "
                + ", ".join(
                    kind.value for kind in self.missing_substrate_artifact_kinds
                )
            )
        gaps.extend(self.substrate_result.readiness_gaps)
        if self.permits_agi_claim:
            gaps.append("maturity-state improperly permits AGI claim")
        if self.certifies_agi:
            gaps.append("readiness snapshot improperly certifies AGI")
        if self.permits_automatic_execution:
            gaps.append("readiness snapshot improperly permits automatic execution")
        return tuple(_dedupe_preserve_order(gaps))

    @property
    def blocking_gaps(self) -> tuple[str, ...]:
        """Return blocking gaps that stop Wave 3 readiness."""

        gaps: list[str] = []
        if self.substrate_result.status is WaveThreeSubstrateStatus.BLOCKED:
            gaps.append("integrated Wave 3 substrate is blocked")
        gaps.extend(self.substrate_result.blocking_gaps)
        return tuple(_dedupe_preserve_order(gaps))

    @property
    def status(self) -> WaveThreeReadinessStatus:
        """Return the fail-closed Wave 3 readiness status."""

        if self.blocking_gaps:
            return WaveThreeReadinessStatus.BLOCKED
        if self.readiness_gaps:
            return WaveThreeReadinessStatus.NEEDS_EVIDENCE
        return WaveThreeReadinessStatus.WAVE_THREE_READY

    @property
    def is_wave_three_ready(self) -> bool:
        """Return whether the snapshot earns the Wave 3 maturity claim."""

        return self.status is WaveThreeReadinessStatus.WAVE_THREE_READY

    @property
    def review_summary(self) -> str:
        """Return a concise human-review summary for the readiness snapshot."""

        return (
            f"{self.wave_label}: {self.status.value}; "
            f"{self.substrate_artifact_count} substrate artifacts, "
            f"{self.substrate_evidence_count} substrate evidence ids; "
            "automatic execution and AGI certification are not permitted."
        )

    def to_artifact_ref(self) -> WaveThreeArtifactRef:
        """Convert this snapshot into a shared Wave 3 artifact reference."""

        if self.status is WaveThreeReadinessStatus.WAVE_THREE_READY:
            decision = WaveThreeArtifactDecision.READY_FOR_HUMAN_REVIEW
            authority_state = WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
        elif self.status is WaveThreeReadinessStatus.BLOCKED:
            decision = WaveThreeArtifactDecision.BLOCKED
            authority_state = WaveThreeAuthorityState.BLOCKED
        else:
            decision = WaveThreeArtifactDecision.NEEDS_EVIDENCE
            authority_state = WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
        return WaveThreeArtifactRef(
            artifact_id=self.artifact_id,
            kind=WaveThreeArtifactKind.READINESS_SNAPSHOT,
            source_system=WaveThreeSourceSystem.IX_COGNITION_KERNEL,
            summary=self.review_summary,
            produced_by_engine_id="evaluator",
            produced_by_agent_role_id="verifier",
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=authority_state,
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted unique readiness and substrate evidence ids."""

        return tuple(
            sorted(set(self.evidence_ids).union(self.substrate_result.all_evidence_ids))
        )

    def to_artifact_bundle(self, *, artifact_bundle_id: str) -> WaveThreeArtifactBundle:
        """Convert this snapshot into a shared artifact bundle."""

        artifact = self.to_artifact_ref()
        return WaveThreeArtifactBundle(
            bundle_id=artifact_bundle_id,
            artifacts=(artifact,),
            evidence_links=tuple(
                WaveThreeEvidenceLink(
                    evidence_id=evidence_id,
                    artifact_id=artifact.artifact_id,
                    relation=WaveThreeEvidenceRelation.REVIEWS,
                    summary=(
                        "Wave 3 readiness evidence reviews the integrated substrate "
                        "without execution authority, AGI certification, or "
                        "deployment approval."
                    ),
                    source_system=WaveThreeSourceSystem.LOCAL_TEST_SUITE,
                )
                for evidence_id in artifact.evidence_ids
            ),
            required_kinds=(WaveThreeArtifactKind.READINESS_SNAPSHOT,),
            notes=(
                "Wave 3 readiness snapshots are bounded maturity evidence, "
                "not AGI certification or deployment approval.",
            ),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "all_evidence_ids": list(self.all_evidence_ids),
            "artifact_id": self.artifact_id,
            "blocking_gaps": list(self.blocking_gaps),
            "certifies_agi": self.certifies_agi,
            "evidence_ids": list(self.evidence_ids),
            "human_authority_state": self.human_authority_state.value,
            "is_wave_three_ready": self.is_wave_three_ready,
            "maturity_wave": self.wave_label,
            "notes": list(self.notes),
            "permits_agi_claim": self.permits_agi_claim,
            "permits_automatic_execution": self.permits_automatic_execution,
            "project_name": self.project_name,
            "readiness_gaps": list(self.readiness_gaps),
            "represented_substrate_artifact_kinds": [
                kind.value for kind in self.represented_substrate_artifact_kinds
            ],
            "review_summary": self.review_summary,
            "schema_version": self.schema_version,
            "status": self.status.value,
            "substrate_fingerprint": self.substrate_result.fingerprint(),
            "validation_artifact_ids": list(self.validation_artifact_ids),
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this snapshot."""

        return _stable_sha256(self.canonical_payload())


def wave_three_readiness_snapshot(
    *,
    substrate_result: WaveThreeSubstrateResult,
    validation_artifact_ids: tuple[
        str, ...
    ] = WAVE_THREE_REQUIRED_VALIDATION_ARTIFACT_IDS,
    evidence_ids: tuple[str, ...] = ("wave3-readiness-evidence",),
    notes: tuple[str, ...] = (),
) -> WaveThreeReadinessSnapshot:
    """Create a Wave 3 readiness snapshot from an integrated substrate result."""

    return WaveThreeReadinessSnapshot(
        project_name="IX-CognitionKernel",
        maturity_wave=wave_by_number(3),
        substrate_result=substrate_result,
        validation_artifact_ids=validation_artifact_ids,
        evidence_ids=evidence_ids,
        notes=notes,
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
