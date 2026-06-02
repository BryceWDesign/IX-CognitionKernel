"""Governed Wave 3 engine coordinator for IX-CognitionKernel.

This module turns Wave 3 engine coordination records into a substrate-level
coordination result. It does not execute plans, mutate state, approve handoffs,
or claim Wave 3 readiness by itself. Its job is narrower and stricter: prove the
required engine records line up with reviewable artifact references and keep the
human-authority boundary intact before later tribunal, reward-audit, WorldTwin,
BlackFox, and assurance layers are added.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from ix_cognition_kernel.engines import engine_ids
from ix_cognition_kernel.wave3_contracts import (
    WaveThreeArtifactBundle,
    WaveThreeArtifactKind,
    WaveThreeArtifactRef,
    WaveThreeAuthorityState,
)
from ix_cognition_kernel.wave3_engine_coordination import EngineCoordinationBundle

WAVE_THREE_COORDINATION_SCHEMA_VERSION = "ix-cognition-kernel-wave3-coordinator-v1"


class WaveThreeCoordinationStatus(StrEnum):
    """Fail-closed status for the Wave 3 engine-coordination substrate."""

    READY_FOR_HUMAN_REVIEW = "ready-for-human-review"
    NEEDS_EVIDENCE = "needs-evidence"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class WaveThreeCoordinationResult:
    """Reviewable result produced by the governed Wave 3 engine coordinator."""

    coordination_id: str
    engine_bundle: EngineCoordinationBundle
    artifact_bundle: WaveThreeArtifactBundle
    required_engine_ids: tuple[str, ...] = engine_ids()
    required_artifact_kinds: tuple[WaveThreeArtifactKind, ...] = (
        WaveThreeArtifactKind.ENGINE_COORDINATION,
    )
    schema_version: str = WAVE_THREE_COORDINATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate substrate identity, coverage, and authority boundaries."""

        object.__setattr__(
            self,
            "coordination_id",
            _require_non_empty(self.coordination_id, "coordination_id"),
        )
        object.__setattr__(
            self,
            "required_engine_ids",
            _normalize_required_engine_ids(self.required_engine_ids),
        )
        object.__setattr__(
            self,
            "required_artifact_kinds",
            _normalize_required_artifact_kinds(self.required_artifact_kinds),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        _validate_engine_bundle_scope(
            self.engine_bundle,
            required_engine_ids=self.required_engine_ids,
        )
        _validate_artifact_bundle_scope(
            self.artifact_bundle,
            required_artifact_kinds=self.required_artifact_kinds,
        )
        _validate_engine_artifacts_match_records(
            engine_bundle=self.engine_bundle,
            artifact_bundle=self.artifact_bundle,
        )
        _validate_human_authority_boundary(self.artifact_bundle.artifacts)

    @property
    def status(self) -> WaveThreeCoordinationStatus:
        """Return the fail-closed coordination status."""

        if self.blocking_gaps:
            return WaveThreeCoordinationStatus.BLOCKED
        if self.readiness_gaps:
            return WaveThreeCoordinationStatus.NEEDS_EVIDENCE
        return WaveThreeCoordinationStatus.READY_FOR_HUMAN_REVIEW

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return all non-blocking gaps that prevent human-review readiness."""

        gaps: list[str] = []
        gaps.extend(self.engine_bundle.readiness_gaps)
        gaps.extend(self._artifact_bundle_gaps)
        if not self._has_exact_record_artifact_alignment:
            gaps.append("engine coordination records do not match artifact references")
        return tuple(gaps)

    @property
    def blocking_gaps(self) -> tuple[str, ...]:
        """Return gaps that block the substrate instead of asking for more evidence."""

        gaps: list[str] = []
        if self.engine_bundle.blocked_engine_ids:
            gaps.append(
                "blocked engine records: "
                f"{', '.join(self.engine_bundle.blocked_engine_ids)}"
            )
        if self.artifact_bundle.blocked_artifact_ids:
            gaps.append(
                "blocked artifact records: "
                f"{', '.join(self.artifact_bundle.blocked_artifact_ids)}"
            )
        gaps.extend(_automatic_execution_gaps(self.artifact_bundle.artifacts))
        return tuple(gaps)

    @property
    def ready_for_human_review(self) -> bool:
        """Return whether this coordination result may enter human review."""

        return self.status is WaveThreeCoordinationStatus.READY_FOR_HUMAN_REVIEW

    @property
    def permits_automatic_execution(self) -> bool:
        """Return whether this result permits automatic execution.

        The value is intentionally constant false. Wave 3 coordination produces
        reviewable evidence, not execution authority.
        """

        return False

    @property
    def human_authority_state(self) -> WaveThreeAuthorityState:
        """Return the aggregate human-authority state for the coordinator."""

        if self.status is WaveThreeCoordinationStatus.BLOCKED:
            return WaveThreeAuthorityState.BLOCKED
        return WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED

    @property
    def coordinated_engine_count(self) -> int:
        """Return count of engine records with complete coordination coverage."""

        return len(self.engine_bundle.complete_engine_ids)

    @property
    def required_engine_count(self) -> int:
        """Return the required engine count for this coordination result."""

        return len(self.required_engine_ids)

    @property
    def ready_artifact_count(self) -> int:
        """Return count of artifacts ready for human review."""

        return len(self.artifact_bundle.ready_for_human_review_artifact_ids)

    @property
    def review_summary(self) -> str:
        """Return a concise human-review summary for the coordination result."""

        return (
            f"{self.coordination_id}: {self.status.value}; "
            f"{self.coordinated_engine_count}/{self.required_engine_count} engines "
            f"coordinated; {self.ready_artifact_count} artifacts ready; "
            "automatic execution is not permitted."
        )

    @property
    def _artifact_bundle_gaps(self) -> tuple[str, ...]:
        """Return artifact-bundle-specific readiness gaps."""

        gaps: list[str] = []
        if self.artifact_bundle.missing_required_kinds:
            gaps.append(
                "missing required artifact kinds: "
                + ", ".join(
                    kind.value for kind in self.artifact_bundle.missing_required_kinds
                )
            )
        if not self.artifact_bundle.ready_for_human_review_artifact_ids:
            gaps.append("artifact bundle has no artifacts ready for human review")
        return tuple(gaps)

    @property
    def _has_exact_record_artifact_alignment(self) -> bool:
        """Return whether engine records and engine artifact refs align exactly."""

        expected = {
            f"engine-coordination:{engine_id}"
            for engine_id in self.engine_bundle.record_engine_ids
        }
        actual = {
            artifact.artifact_id
            for artifact in self.artifact_bundle.artifacts
            if artifact.kind is WaveThreeArtifactKind.ENGINE_COORDINATION
        }
        return expected == actual

    def artifact_by_engine_id(self, engine_id: str) -> WaveThreeArtifactRef:
        """Return the engine-coordination artifact for one engine id."""

        artifact_id = f"engine-coordination:{engine_id}"
        return self.artifact_bundle.artifact_by_id(artifact_id)

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "artifact_bundle_fingerprint": self.artifact_bundle.fingerprint(),
            "blocking_gaps": list(self.blocking_gaps),
            "coordination_id": self.coordination_id,
            "engine_bundle_fingerprint": self.engine_bundle.fingerprint(),
            "human_authority_state": self.human_authority_state.value,
            "permits_automatic_execution": self.permits_automatic_execution,
            "readiness_gaps": list(self.readiness_gaps),
            "required_artifact_kinds": [
                kind.value for kind in self.required_artifact_kinds
            ],
            "required_engine_ids": list(self.required_engine_ids),
            "review_summary": self.review_summary,
            "schema_version": self.schema_version,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this result."""

        return _stable_sha256(self.canonical_payload())


def coordinate_wave_three_engines(
    *,
    coordination_id: str,
    engine_bundle: EngineCoordinationBundle,
    artifact_bundle: WaveThreeArtifactBundle | None = None,
    required_engine_ids: tuple[str, ...] = engine_ids(),
) -> WaveThreeCoordinationResult:
    """Coordinate required Wave 3 engine records into reviewable artifacts."""

    resolved_artifact_bundle = artifact_bundle or engine_bundle.to_artifact_bundle(
        artifact_bundle_id=f"{coordination_id}:engine-artifacts"
    )
    return WaveThreeCoordinationResult(
        coordination_id=coordination_id,
        engine_bundle=engine_bundle,
        artifact_bundle=resolved_artifact_bundle,
        required_engine_ids=required_engine_ids,
    )


def _validate_engine_bundle_scope(
    engine_bundle: EngineCoordinationBundle, *, required_engine_ids: tuple[str, ...]
) -> None:
    """Validate that the engine bundle uses the coordinator's required scope."""

    if engine_bundle.required_engine_ids != required_engine_ids:
        raise ValueError(
            "Engine bundle required_engine_ids must match coordinator scope."
        )


def _validate_artifact_bundle_scope(
    artifact_bundle: WaveThreeArtifactBundle,
    *,
    required_artifact_kinds: tuple[WaveThreeArtifactKind, ...],
) -> None:
    """Validate artifact bundle kind coverage requested by this coordinator."""

    for kind in required_artifact_kinds:
        if kind not in artifact_bundle.required_kinds:
            raise ValueError(
                "Artifact bundle required_kinds must include coordinator kind: "
                f"{kind.value}"
            )


def _validate_engine_artifacts_match_records(
    *,
    engine_bundle: EngineCoordinationBundle,
    artifact_bundle: WaveThreeArtifactBundle,
) -> None:
    """Reject artifact bundles that do not exactly represent engine records."""

    expected_artifact_ids = {
        f"engine-coordination:{engine_id}"
        for engine_id in engine_bundle.record_engine_ids
    }
    actual_artifact_ids = {
        artifact.artifact_id
        for artifact in artifact_bundle.artifacts
        if artifact.kind is WaveThreeArtifactKind.ENGINE_COORDINATION
    }
    if expected_artifact_ids != actual_artifact_ids:
        raise ValueError(
            "Engine coordination artifacts must exactly match bundled engine records."
        )
    record_engine_ids = set(engine_bundle.record_engine_ids)
    for artifact in artifact_bundle.artifacts:
        if (
            artifact.kind is WaveThreeArtifactKind.ENGINE_COORDINATION
            and artifact.produced_by_engine_id not in record_engine_ids
        ):
            raise ValueError(
                "Engine coordination artifact produced_by_engine_id must match "
                "a bundled engine record."
            )


def _validate_human_authority_boundary(
    artifacts: tuple[WaveThreeArtifactRef, ...],
) -> None:
    """Validate that no artifact crosses the human-authority boundary."""

    gaps = _automatic_execution_gaps(artifacts)
    if gaps:
        raise ValueError(gaps[0])


def _automatic_execution_gaps(
    artifacts: tuple[WaveThreeArtifactRef, ...],
) -> tuple[str, ...]:
    """Return automatic-execution boundary violations."""

    return tuple(
        f"artifact {artifact.artifact_id} attempts to permit automatic execution"
        for artifact in artifacts
        if artifact.allowed_for_automatic_execution
    )


def _normalize_required_engine_ids(values: tuple[str, ...]) -> tuple[str, ...]:
    """Normalize required engine ids while preserving registry order."""

    if not values:
        raise ValueError("Coordinator requires at least one engine id.")
    known_engine_ids = set(engine_ids())
    seen: set[str] = set()
    normalized: list[str] = []
    for value in values:
        engine_id = _require_non_empty(value, "required_engine_id")
        if engine_id not in known_engine_ids:
            raise ValueError(f"Unknown required engine id: {engine_id}")
        if engine_id in seen:
            raise ValueError(f"Duplicate required_engine_id detected: {engine_id}")
        normalized.append(engine_id)
        seen.add(engine_id)
    return tuple(normalized)


def _normalize_required_artifact_kinds(
    values: tuple[WaveThreeArtifactKind, ...],
) -> tuple[WaveThreeArtifactKind, ...]:
    """Normalize required artifact kinds while rejecting duplicates."""

    if not values:
        raise ValueError("Coordinator requires at least one artifact kind.")
    seen: set[WaveThreeArtifactKind] = set()
    normalized: list[WaveThreeArtifactKind] = []
    for value in values:
        if value in seen:
            raise ValueError(
                f"Duplicate required artifact kind detected: {value.value}"
            )
        normalized.append(value)
        seen.add(value)
    return tuple(normalized)


def _require_non_empty(value: str, label: str) -> str:
    """Return stripped text or raise when empty."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
