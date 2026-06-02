"""Wave 3 engine coordination records for IX-CognitionKernel.

Wave 3 requires more than a static engine registry. The governed substrate must
record whether each required engine received its required inputs, produced its
required outputs, covered the failure modes it exists to block, and carried
evidence before any later tribunal, WorldTwin, BlackFox handoff, or assurance
claim can treat the engine as coordinated.

These records are intentionally non-executable. They provide reviewable engine
coverage and artifact references only.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.engines import EngineDefinition, engine_by_id, engine_ids
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

T = TypeVar("T")
E = TypeVar("E", bound=StrEnum)

WAVE_THREE_ENGINE_COORDINATION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave3-engine-coordination-v1"
)
WAVE_THREE_ENGINE_COORDINATION_BUNDLE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave3-engine-coordination-bundle-v1"
)


class EngineCoordinationStatus(StrEnum):
    """Fail-closed status for one engine coordination record."""

    EVIDENCE_COMPLETE = "evidence-complete"
    NEEDS_EVIDENCE = "needs-evidence"
    BLOCKED = "blocked"


class EngineDependencyRelation(StrEnum):
    """Typed relation between two required engines."""

    REQUIRES = "requires"
    SUPPORTS = "supports"
    REVIEWS = "reviews"
    HANDS_OFF_TO = "hands-off-to"


@dataclass(frozen=True, slots=True)
class EngineDependency:
    """A typed dependency edge between required cognition engines."""

    upstream_engine_id: str
    downstream_engine_id: str
    relation: EngineDependencyRelation
    required_artifact_ids: tuple[str, ...]
    reason: str

    def __post_init__(self) -> None:
        """Validate dependency identity and artifact references."""

        object.__setattr__(
            self,
            "upstream_engine_id",
            _normalize_engine_id(self.upstream_engine_id),
        )
        object.__setattr__(
            self,
            "downstream_engine_id",
            _normalize_engine_id(self.downstream_engine_id),
        )
        if self.upstream_engine_id == self.downstream_engine_id:
            raise ValueError("Engine dependencies must connect two distinct engines.")
        object.__setattr__(
            self,
            "required_artifact_ids",
            _normalize_unique_text_tuple(
                self.required_artifact_ids,
                label="dependency required_artifact_id",
            ),
        )
        object.__setattr__(self, "reason", _require_non_empty(self.reason, "reason"))

    @property
    def dependency_key(self) -> tuple[str, str, str]:
        """Return the deterministic key for this engine dependency."""

        return (
            self.upstream_engine_id,
            self.downstream_engine_id,
            self.relation.value,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "downstream_engine_id": self.downstream_engine_id,
            "reason": self.reason,
            "relation": self.relation.value,
            "required_artifact_ids": list(self.required_artifact_ids),
            "upstream_engine_id": self.upstream_engine_id,
        }


@dataclass(frozen=True, slots=True)
class EngineCoordinationRecord:
    """Reviewable Wave 3 coverage record for one required cognition engine."""

    engine_id: str
    satisfied_input_names: tuple[str, ...]
    produced_output_names: tuple[str, ...]
    covered_failure_modes: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    status: EngineCoordinationStatus = EngineCoordinationStatus.NEEDS_EVIDENCE
    blocking_reasons: tuple[str, ...] = ()
    downstream_artifact_ids: tuple[str, ...] = ()
    schema_version: str = WAVE_THREE_ENGINE_COORDINATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate engine coverage against the locked engine registry."""

        object.__setattr__(self, "engine_id", _normalize_engine_id(self.engine_id))
        engine = self.engine_definition
        object.__setattr__(
            self,
            "satisfied_input_names",
            _normalize_unique_expected_values(
                self.satisfied_input_names,
                expected_values=engine.required_inputs,
                label="satisfied_input_name",
            ),
        )
        object.__setattr__(
            self,
            "produced_output_names",
            _normalize_unique_expected_values(
                self.produced_output_names,
                expected_values=engine.required_outputs,
                label="produced_output_name",
            ),
        )
        object.__setattr__(
            self,
            "covered_failure_modes",
            _normalize_unique_expected_values(
                self.covered_failure_modes,
                expected_values=engine.blocked_failure_modes,
                label="covered_failure_mode",
            ),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="engine evidence_id"),
        )
        object.__setattr__(
            self,
            "blocking_reasons",
            _normalize_unique_text_tuple(
                self.blocking_reasons,
                label="engine blocking_reason",
            ),
        )
        object.__setattr__(
            self,
            "downstream_artifact_ids",
            _normalize_unique_text_tuple(
                self.downstream_artifact_ids,
                label="engine downstream_artifact_id",
            ),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if (
            self.status is EngineCoordinationStatus.EVIDENCE_COMPLETE
            and not self.has_coordination_coverage
        ):
            raise ValueError(
                "Evidence-complete engine records require input, output, failure-mode, "
                "and evidence coverage."
            )
        if (
            self.status is EngineCoordinationStatus.BLOCKED
            and not self.blocking_reasons
        ):
            raise ValueError("Blocked engine records require blocking reasons.")
        if (
            self.status is not EngineCoordinationStatus.BLOCKED
            and self.blocking_reasons
        ):
            raise ValueError("Only blocked engine records may carry blocking reasons.")

    @property
    def engine_definition(self) -> EngineDefinition:
        """Return the locked engine registry definition for this record."""

        return engine_by_id(self.engine_id)

    @property
    def missing_required_inputs(self) -> tuple[str, ...]:
        """Return registry-required inputs not satisfied by this record."""

        return _missing_values(
            required=self.engine_definition.required_inputs,
            present=self.satisfied_input_names,
        )

    @property
    def missing_required_outputs(self) -> tuple[str, ...]:
        """Return registry-required outputs not produced by this record."""

        return _missing_values(
            required=self.engine_definition.required_outputs,
            present=self.produced_output_names,
        )

    @property
    def uncovered_failure_modes(self) -> tuple[str, ...]:
        """Return registry-blocked failure modes not covered by this record."""

        return _missing_values(
            required=self.engine_definition.blocked_failure_modes,
            present=self.covered_failure_modes,
        )

    @property
    def has_required_input_coverage(self) -> bool:
        """Return whether every required input is satisfied."""

        return not self.missing_required_inputs

    @property
    def has_required_output_coverage(self) -> bool:
        """Return whether every required output is produced."""

        return not self.missing_required_outputs

    @property
    def has_failure_mode_coverage(self) -> bool:
        """Return whether every blocked failure mode is covered."""

        return not self.uncovered_failure_modes

    @property
    def has_coordination_coverage(self) -> bool:
        """Return whether this engine has minimum Wave 3 coordination evidence."""

        return (
            self.has_required_input_coverage
            and self.has_required_output_coverage
            and self.has_failure_mode_coverage
            and bool(self.evidence_ids)
        )

    @property
    def blocks_progress(self) -> bool:
        """Return whether this engine blocks bundle readiness."""

        return self.status is EngineCoordinationStatus.BLOCKED

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return fail-closed gaps for this engine record."""

        gaps: list[str] = []
        if self.missing_required_inputs:
            gaps.append(
                f"{self.engine_id} missing required inputs: "
                f"{', '.join(self.missing_required_inputs)}"
            )
        if self.missing_required_outputs:
            gaps.append(
                f"{self.engine_id} missing required outputs: "
                f"{', '.join(self.missing_required_outputs)}"
            )
        if self.uncovered_failure_modes:
            gaps.append(
                f"{self.engine_id} missing failure-mode coverage: "
                f"{', '.join(self.uncovered_failure_modes)}"
            )
        if not self.evidence_ids:
            gaps.append(f"{self.engine_id} has no evidence ids")
        if self.blocks_progress:
            gaps.extend(
                f"{self.engine_id} blocked: {reason}"
                for reason in self.blocking_reasons
            )
        return tuple(gaps)

    def to_artifact_ref(self) -> WaveThreeArtifactRef:
        """Convert this record into a shared Wave 3 artifact reference."""

        if self.status is EngineCoordinationStatus.EVIDENCE_COMPLETE:
            decision = WaveThreeArtifactDecision.READY_FOR_HUMAN_REVIEW
            authority_state = WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
        elif self.status is EngineCoordinationStatus.BLOCKED:
            decision = WaveThreeArtifactDecision.BLOCKED
            authority_state = WaveThreeAuthorityState.BLOCKED
        else:
            decision = WaveThreeArtifactDecision.NEEDS_EVIDENCE
            authority_state = WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
        return WaveThreeArtifactRef(
            artifact_id=f"engine-coordination:{self.engine_id}",
            kind=WaveThreeArtifactKind.ENGINE_COORDINATION,
            source_system=WaveThreeSourceSystem.IX_COGNITION_KERNEL,
            summary=(
                f"Wave 3 coordination record for {self.engine_definition.label}: "
                f"{self.status.value}."
            ),
            produced_by_engine_id=self.engine_id,
            evidence_ids=self.evidence_ids,
            decision=decision,
            authority_state=authority_state,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "blocking_reasons": list(self.blocking_reasons),
            "covered_failure_modes": list(self.covered_failure_modes),
            "downstream_artifact_ids": list(self.downstream_artifact_ids),
            "engine_id": self.engine_id,
            "evidence_ids": list(self.evidence_ids),
            "produced_output_names": list(self.produced_output_names),
            "satisfied_input_names": list(self.satisfied_input_names),
            "schema_version": self.schema_version,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this record."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class EngineCoordinationBundle:
    """Deterministic Wave 3 bundle of required engine coordination records."""

    bundle_id: str
    records: tuple[EngineCoordinationRecord, ...]
    dependencies: tuple[EngineDependency, ...] = ()
    required_engine_ids: tuple[str, ...] = engine_ids()
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_THREE_ENGINE_COORDINATION_BUNDLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate bundle uniqueness, dependency coverage, and engine identity."""

        object.__setattr__(
            self, "bundle_id", _require_non_empty(self.bundle_id, "bundle_id")
        )
        if not self.records:
            raise ValueError("Engine coordination bundles require at least one record.")
        sorted_records = tuple(
            sorted(self.records, key=lambda record: record.engine_id)
        )
        sorted_dependencies = tuple(
            sorted(self.dependencies, key=lambda dependency: dependency.dependency_key)
        )
        record_ids = _unique_ids(
            (record.engine_id for record in sorted_records), label="engine_id"
        )
        _unique_ids(
            (dependency.dependency_key for dependency in sorted_dependencies),
            label="engine dependency",
        )
        object.__setattr__(
            self,
            "required_engine_ids",
            _normalize_required_engine_ids(self.required_engine_ids),
        )
        required_engine_set = set(self.required_engine_ids)
        for dependency in sorted_dependencies:
            if dependency.upstream_engine_id not in required_engine_set:
                raise ValueError(
                    "Engine dependency references non-required upstream engine: "
                    f"{dependency.upstream_engine_id}"
                )
            if dependency.downstream_engine_id not in required_engine_set:
                raise ValueError(
                    "Engine dependency references non-required downstream engine: "
                    f"{dependency.downstream_engine_id}"
                )
            if dependency.upstream_engine_id not in record_ids:
                raise ValueError(
                    "Engine dependency requires a bundled upstream record: "
                    f"{dependency.upstream_engine_id}"
                )
        object.__setattr__(self, "records", sorted_records)
        object.__setattr__(self, "dependencies", sorted_dependencies)
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="coordination bundle note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )

    @property
    def record_engine_ids(self) -> tuple[str, ...]:
        """Return engine ids represented by records in deterministic order."""

        return tuple(record.engine_id for record in self.records)

    @property
    def complete_engine_ids(self) -> tuple[str, ...]:
        """Return engine ids with complete coordination evidence."""

        return tuple(
            record.engine_id
            for record in self.records
            if record.has_coordination_coverage
        )

    @property
    def blocked_engine_ids(self) -> tuple[str, ...]:
        """Return engine ids whose records block progress."""

        return tuple(
            record.engine_id for record in self.records if record.blocks_progress
        )

    @property
    def missing_required_engine_ids(self) -> tuple[str, ...]:
        """Return required engines missing from the bundle."""

        present = set(self.record_engine_ids)
        return tuple(
            engine_id
            for engine_id in self.required_engine_ids
            if engine_id not in present
        )

    @property
    def incomplete_engine_ids(self) -> tuple[str, ...]:
        """Return represented engine ids lacking complete coverage."""

        return tuple(
            record.engine_id
            for record in self.records
            if not record.has_coordination_coverage
        )

    @property
    def dependency_map(self) -> Mapping[str, tuple[str, ...]]:
        """Return downstream engine ids mapped to required upstream engine ids."""

        mapped: dict[str, set[str]] = {}
        for dependency in self.dependencies:
            mapped.setdefault(dependency.downstream_engine_id, set()).add(
                dependency.upstream_engine_id
            )
        return {
            downstream_engine_id: tuple(sorted(upstream_engine_ids))
            for downstream_engine_id, upstream_engine_ids in sorted(mapped.items())
        }

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return bundle-level and record-level readiness gaps."""

        gaps: list[str] = []
        if self.missing_required_engine_ids:
            gaps.append(
                "missing required engine records: "
                f"{', '.join(self.missing_required_engine_ids)}"
            )
        for record in self.records:
            gaps.extend(record.readiness_gaps)
        return tuple(gaps)

    @property
    def is_complete_for_required_engines(self) -> bool:
        """Return whether all required engines have complete, unblocked records."""

        return not self.readiness_gaps

    def record_by_engine_id(self, engine_id: str) -> EngineCoordinationRecord:
        """Return one coordination record by engine id."""

        normalized_engine_id = _normalize_engine_id(engine_id)
        for record in self.records:
            if record.engine_id == normalized_engine_id:
                return record
        raise ValueError(f"Unknown coordinated engine id: {engine_id}")

    def to_artifact_bundle(self, *, artifact_bundle_id: str) -> WaveThreeArtifactBundle:
        """Convert engine coordination records into a shared artifact bundle."""

        artifacts = tuple(record.to_artifact_ref() for record in self.records)
        evidence_links = tuple(
            WaveThreeEvidenceLink(
                evidence_id=evidence_id,
                artifact_id=artifact.artifact_id,
                relation=WaveThreeEvidenceRelation.TESTS,
                summary=(
                    "Engine coordination evidence is linked to a reviewable "
                    "Wave 3 engine artifact."
                ),
                source_system=WaveThreeSourceSystem.LOCAL_TEST_SUITE,
            )
            for artifact in artifacts
            for evidence_id in artifact.evidence_ids
        )
        return WaveThreeArtifactBundle(
            bundle_id=artifact_bundle_id,
            artifacts=artifacts,
            evidence_links=evidence_links,
            required_kinds=(WaveThreeArtifactKind.ENGINE_COORDINATION,),
            notes=("Engine coordination artifacts are review records only.",),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "bundle_id": self.bundle_id,
            "dependencies": [
                dependency.canonical_payload() for dependency in self.dependencies
            ],
            "notes": list(self.notes),
            "records": [record.canonical_payload() for record in self.records],
            "required_engine_ids": list(self.required_engine_ids),
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this bundle."""

        return _stable_sha256(self.canonical_payload())


def complete_engine_coordination_record(
    engine_id: str,
    *,
    evidence_ids: tuple[str, ...],
    downstream_artifact_ids: tuple[str, ...] = (),
) -> EngineCoordinationRecord:
    """Create a complete coordination record from the locked engine registry."""

    engine = engine_by_id(engine_id)
    return EngineCoordinationRecord(
        engine_id=engine.engine_id,
        satisfied_input_names=engine.required_inputs,
        produced_output_names=engine.required_outputs,
        covered_failure_modes=engine.blocked_failure_modes,
        evidence_ids=evidence_ids,
        status=EngineCoordinationStatus.EVIDENCE_COMPLETE,
        downstream_artifact_ids=downstream_artifact_ids,
    )


def _normalize_engine_id(engine_id: str) -> str:
    """Normalize and validate a required engine id."""

    normalized = _require_non_empty(engine_id, "engine_id")
    engine_by_id(normalized)
    return normalized


def _normalize_required_engine_ids(values: Iterable[str]) -> tuple[str, ...]:
    """Normalize required engine ids without sorting away caller order."""

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        engine_id_value = _normalize_engine_id(value)
        if engine_id_value in seen:
            raise ValueError(
                f"Duplicate required_engine_id detected: {engine_id_value}"
            )
        normalized.append(engine_id_value)
        seen.add(engine_id_value)
    if not normalized:
        raise ValueError("Engine coordination bundles require required engine ids.")
    return tuple(normalized)


def _normalize_unique_expected_values(
    values: Iterable[str], *, expected_values: Iterable[str], label: str
) -> tuple[str, ...]:
    """Normalize values while rejecting values outside an engine registry tuple."""

    expected = tuple(expected_values)
    expected_set = set(expected)
    normalized = _normalize_unique_text_tuple(values, label=label)
    for value in normalized:
        if value not in expected_set:
            raise ValueError(f"Unknown {label} for engine registry: {value}")
    return tuple(value for value in expected if value in set(normalized))


def _missing_values(
    *, required: Iterable[str], present: Iterable[str]
) -> tuple[str, ...]:
    """Return required values not represented in present values."""

    present_set = set(present)
    return tuple(value for value in required if value not in present_set)


def _require_non_empty(value: str, label: str) -> str:
    """Return stripped text or raise when empty."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _normalize_unique_text_tuple(
    values: Iterable[str], *, label: str
) -> tuple[str, ...]:
    """Normalize text tuples while rejecting blanks and duplicates."""

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        stripped = _require_non_empty(value, label)
        if stripped in seen:
            raise ValueError(f"Duplicate {label} detected: {stripped}")
        normalized.append(stripped)
        seen.add(stripped)
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
