"""Structured Wave 3 agent-role artifacts for IX-CognitionKernel.

Wave 3 turns the locked 25-agent registry into reviewable artifacts. These
records do not simulate personalities, grant agent authority, or let a role win
by persuasion. They bind each bounded role to registry-required inputs, registry
-required outputs, paired engines, evidence ids, and explicit authority limits so
later tribunal flow can reason over real artifacts instead of agent theater.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.agents import AgentRole, ArtifactKind, agent_by_id, agent_ids
from ix_cognition_kernel.engines import engine_by_id
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

WAVE_THREE_ROLE_ARTIFACT_SCHEMA_VERSION = "ix-cognition-kernel-wave3-role-artifact-v1"
WAVE_THREE_ROLE_ARTIFACT_BUNDLE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave3-role-artifact-bundle-v1"
)


class RoleArtifactStatus(StrEnum):
    """Fail-closed status for one bounded role artifact."""

    READY_FOR_TRIBUNAL = "ready-for-tribunal"
    NEEDS_EVIDENCE = "needs-evidence"
    BLOCKED = "blocked"


class RoleArtifactAuthority(StrEnum):
    """Authority boundary carried by a bounded agent-role artifact."""

    REVIEW_ONLY = "review-only"
    MAY_BLOCK_WITH_EVIDENCE = "may-block-with-evidence"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class RoleArtifactRecord:
    """Reviewable artifact produced by one bounded agent role."""

    role_id: str
    produced_output_artifacts: tuple[ArtifactKind, ...]
    consumed_input_artifacts: tuple[ArtifactKind, ...]
    evidence_ids: tuple[str, ...]
    rationale: str
    status: RoleArtifactStatus = RoleArtifactStatus.NEEDS_EVIDENCE
    authority: RoleArtifactAuthority = RoleArtifactAuthority.REVIEW_ONLY
    paired_engine_ids: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    schema_version: str = WAVE_THREE_ROLE_ARTIFACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate the artifact against the locked agent-role registry."""

        object.__setattr__(self, "role_id", _normalize_role_id(self.role_id))
        role = self.role
        object.__setattr__(
            self,
            "produced_output_artifacts",
            _normalize_artifact_subset(
                self.produced_output_artifacts,
                allowed=role.required_outputs,
                label="produced_output_artifact",
            ),
        )
        object.__setattr__(
            self,
            "consumed_input_artifacts",
            _normalize_artifact_subset(
                self.consumed_input_artifacts,
                allowed=role.required_inputs,
                label="consumed_input_artifact",
            ),
        )
        object.__setattr__(
            self,
            "paired_engine_ids",
            _normalize_paired_engine_ids(
                self.paired_engine_ids or role.paired_engines,
                allowed=role.paired_engines,
            ),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="role evidence_id"),
        )
        object.__setattr__(
            self, "rationale", _require_non_empty(self.rationale, "rationale")
        )
        object.__setattr__(
            self,
            "blocking_reasons",
            _normalize_unique_text_tuple(
                self.blocking_reasons,
                label="role blocking_reason",
            ),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if (
            self.status is RoleArtifactStatus.READY_FOR_TRIBUNAL
            and not self.is_complete
        ):
            raise ValueError(
                "Ready-for-tribunal role artifacts require input coverage, output "
                "coverage, paired-engine coverage, evidence ids, and rationale."
            )
        if self.status is RoleArtifactStatus.BLOCKED and not self.blocking_reasons:
            raise ValueError("Blocked role artifacts require blocking reasons.")
        if self.status is not RoleArtifactStatus.BLOCKED and self.blocking_reasons:
            raise ValueError("Only blocked role artifacts may carry blocking reasons.")
        if (
            self.status is RoleArtifactStatus.BLOCKED
            and self.authority is not RoleArtifactAuthority.BLOCKED
        ):
            raise ValueError("Blocked role artifacts must carry blocked authority.")

    @property
    def role(self) -> AgentRole:
        """Return the locked registry role represented by this artifact."""

        return agent_by_id(self.role_id)

    @property
    def artifact_id(self) -> str:
        """Return the shared Wave 3 artifact id for this role record."""

        return f"role-artifact:{self.role_id}"

    @property
    def missing_required_inputs(self) -> tuple[ArtifactKind, ...]:
        """Return role-required input artifact kinds not consumed."""

        return _missing_artifacts(
            required=self.role.required_inputs,
            present=self.consumed_input_artifacts,
        )

    @property
    def missing_required_outputs(self) -> tuple[ArtifactKind, ...]:
        """Return role-required output artifact kinds not produced."""

        return _missing_artifacts(
            required=self.role.required_outputs,
            present=self.produced_output_artifacts,
        )

    @property
    def missing_paired_engines(self) -> tuple[str, ...]:
        """Return registry-paired engines not represented in this artifact."""

        present = set(self.paired_engine_ids)
        return tuple(
            engine_id
            for engine_id in self.role.paired_engines
            if engine_id not in present
        )

    @property
    def has_input_coverage(self) -> bool:
        """Return whether every role-required input artifact is consumed."""

        return not self.missing_required_inputs

    @property
    def has_output_coverage(self) -> bool:
        """Return whether every role-required output artifact is produced."""

        return not self.missing_required_outputs

    @property
    def has_paired_engine_coverage(self) -> bool:
        """Return whether every registry-paired engine is represented."""

        return not self.missing_paired_engines

    @property
    def is_complete(self) -> bool:
        """Return whether this role artifact has complete tribunal-ready coverage."""

        return (
            self.has_input_coverage
            and self.has_output_coverage
            and self.has_paired_engine_coverage
            and bool(self.evidence_ids)
            and bool(self.rationale)
        )

    @property
    def blocks_progress(self) -> bool:
        """Return whether this role artifact blocks tribunal progress."""

        return self.status is RoleArtifactStatus.BLOCKED

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return fail-closed gaps for this role artifact."""

        gaps: list[str] = []
        if self.missing_required_inputs:
            gaps.append(
                f"{self.role_id} missing required inputs: "
                + ", ".join(kind.value for kind in self.missing_required_inputs)
            )
        if self.missing_required_outputs:
            gaps.append(
                f"{self.role_id} missing required outputs: "
                + ", ".join(kind.value for kind in self.missing_required_outputs)
            )
        if self.missing_paired_engines:
            gaps.append(
                f"{self.role_id} missing paired engines: "
                + ", ".join(self.missing_paired_engines)
            )
        if not self.evidence_ids:
            gaps.append(f"{self.role_id} has no evidence ids")
        if self.blocks_progress:
            gaps.extend(
                f"{self.role_id} blocked: {reason}" for reason in self.blocking_reasons
            )
        return tuple(gaps)

    def to_artifact_ref(self) -> WaveThreeArtifactRef:
        """Convert this record into a shared Wave 3 artifact reference."""

        if self.status is RoleArtifactStatus.READY_FOR_TRIBUNAL:
            decision = WaveThreeArtifactDecision.READY_FOR_HUMAN_REVIEW
            authority_state = WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
        elif self.status is RoleArtifactStatus.BLOCKED:
            decision = WaveThreeArtifactDecision.BLOCKED
            authority_state = WaveThreeAuthorityState.BLOCKED
        else:
            decision = WaveThreeArtifactDecision.NEEDS_EVIDENCE
            authority_state = WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
        return WaveThreeArtifactRef(
            artifact_id=self.artifact_id,
            kind=WaveThreeArtifactKind.ROLE_ARTIFACT,
            source_system=WaveThreeSourceSystem.IX_COGNITION_KERNEL,
            summary=f"Wave 3 role artifact for {self.role.label}: {self.status.value}.",
            produced_by_engine_id="multi-agent-tribunal",
            produced_by_agent_role_id=self.role_id,
            evidence_ids=self.evidence_ids,
            decision=decision,
            authority_state=authority_state,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "artifact_id": self.artifact_id,
            "authority": self.authority.value,
            "blocking_reasons": list(self.blocking_reasons),
            "consumed_input_artifacts": [
                kind.value for kind in self.consumed_input_artifacts
            ],
            "evidence_ids": list(self.evidence_ids),
            "paired_engine_ids": list(self.paired_engine_ids),
            "produced_output_artifacts": [
                kind.value for kind in self.produced_output_artifacts
            ],
            "rationale": self.rationale,
            "role_id": self.role_id,
            "schema_version": self.schema_version,
            "status": self.status.value,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this role artifact."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class RoleArtifactBundle:
    """Deterministic bundle of bounded role artifacts for Wave 3 tribunal use."""

    bundle_id: str
    records: tuple[RoleArtifactRecord, ...]
    required_role_ids: tuple[str, ...] = agent_ids()
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_THREE_ROLE_ARTIFACT_BUNDLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate role coverage, uniqueness, and review-only authority."""

        object.__setattr__(
            self, "bundle_id", _require_non_empty(self.bundle_id, "bundle_id")
        )
        if not self.records:
            raise ValueError("Role artifact bundles require at least one record.")
        sorted_records = tuple(sorted(self.records, key=lambda record: record.role_id))
        record_ids = _unique_ids(
            (record.role_id for record in sorted_records), label="role_id"
        )
        object.__setattr__(
            self,
            "required_role_ids",
            _normalize_required_role_ids(self.required_role_ids),
        )
        for role_id in record_ids:
            if role_id not in self.required_role_ids:
                raise ValueError(
                    f"Role artifact bundle contains non-required role: {role_id}"
                )
        object.__setattr__(self, "records", sorted_records)
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="role artifact bundle note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )

    @property
    def record_role_ids(self) -> tuple[str, ...]:
        """Return represented role ids in deterministic order."""

        return tuple(record.role_id for record in self.records)

    @property
    def complete_role_ids(self) -> tuple[str, ...]:
        """Return role ids with complete artifact coverage."""

        return tuple(record.role_id for record in self.records if record.is_complete)

    @property
    def blocked_role_ids(self) -> tuple[str, ...]:
        """Return role ids whose artifacts block progress."""

        return tuple(
            record.role_id for record in self.records if record.blocks_progress
        )

    @property
    def missing_required_role_ids(self) -> tuple[str, ...]:
        """Return required roles not represented in the bundle."""

        present = set(self.record_role_ids)
        return tuple(
            role_id for role_id in self.required_role_ids if role_id not in present
        )

    @property
    def incomplete_role_ids(self) -> tuple[str, ...]:
        """Return represented role ids lacking complete coverage."""

        return tuple(
            record.role_id for record in self.records if not record.is_complete
        )

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return bundle-level and record-level readiness gaps."""

        gaps: list[str] = []
        if self.missing_required_role_ids:
            gaps.append(
                "missing required role artifacts: "
                + ", ".join(self.missing_required_role_ids)
            )
        for record in self.records:
            gaps.extend(record.readiness_gaps)
        return tuple(gaps)

    @property
    def is_complete_for_required_roles(self) -> bool:
        """Return whether every required role has complete, unblocked coverage."""

        return not self.readiness_gaps

    def record_by_role_id(self, role_id: str) -> RoleArtifactRecord:
        """Return one role artifact record by role id."""

        normalized_role_id = _normalize_role_id(role_id)
        for record in self.records:
            if record.role_id == normalized_role_id:
                return record
        raise ValueError(f"Unknown role artifact id: {role_id}")

    def to_artifact_bundle(self, *, artifact_bundle_id: str) -> WaveThreeArtifactBundle:
        """Convert role records into a shared Wave 3 artifact bundle."""

        artifacts = tuple(record.to_artifact_ref() for record in self.records)
        evidence_links = tuple(
            WaveThreeEvidenceLink(
                evidence_id=evidence_id,
                artifact_id=artifact.artifact_id,
                relation=WaveThreeEvidenceRelation.SUPPORTS,
                summary=(
                    "Role artifact evidence is linked to a bounded, review-only "
                    "Wave 3 agent-role artifact."
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
            required_kinds=(WaveThreeArtifactKind.ROLE_ARTIFACT,),
            notes=(
                "Agent-role artifacts are review records, not autonomous authority.",
            ),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "bundle_id": self.bundle_id,
            "notes": list(self.notes),
            "records": [record.canonical_payload() for record in self.records],
            "required_role_ids": list(self.required_role_ids),
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this bundle."""

        return _stable_sha256(self.canonical_payload())


def complete_role_artifact_record(
    role_id: str, *, evidence_ids: tuple[str, ...]
) -> RoleArtifactRecord:
    """Create a complete tribunal-ready artifact from the locked role registry."""

    role = agent_by_id(role_id)
    return RoleArtifactRecord(
        role_id=role.role_id,
        produced_output_artifacts=role.required_outputs,
        consumed_input_artifacts=role.required_inputs,
        evidence_ids=evidence_ids,
        rationale=(
            f"{role.label} produced its registry-required review artifact under "
            "bounded Wave 3 tribunal authority."
        ),
        status=RoleArtifactStatus.READY_FOR_TRIBUNAL,
        authority=RoleArtifactAuthority.MAY_BLOCK_WITH_EVIDENCE,
        paired_engine_ids=role.paired_engines,
    )


def _normalize_role_id(role_id: str) -> str:
    """Normalize and validate a role id."""

    normalized = _require_non_empty(role_id, "role_id")
    agent_by_id(normalized)
    return normalized


def _normalize_required_role_ids(values: Iterable[str]) -> tuple[str, ...]:
    """Normalize required role ids without sorting away registry order."""

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        role_id = _normalize_role_id(value)
        if role_id in seen:
            raise ValueError(f"Duplicate required_role_id detected: {role_id}")
        normalized.append(role_id)
        seen.add(role_id)
    if not normalized:
        raise ValueError("Role artifact bundles require required role ids.")
    return tuple(normalized)


def _normalize_artifact_subset(
    values: Iterable[ArtifactKind], *, allowed: Iterable[ArtifactKind], label: str
) -> tuple[ArtifactKind, ...]:
    """Normalize an ArtifactKind tuple while rejecting values outside the role."""

    allowed_tuple = tuple(allowed)
    allowed_set = set(allowed_tuple)
    normalized = _normalize_unique_enum_tuple(values, label=label)
    for value in normalized:
        if value not in allowed_set:
            raise ValueError(f"Unknown {label} for role registry: {value.value}")
    return tuple(value for value in allowed_tuple if value in set(normalized))


def _normalize_paired_engine_ids(
    values: Iterable[str], *, allowed: Iterable[str]
) -> tuple[str, ...]:
    """Normalize paired engine ids while rejecting engines outside the role."""

    allowed_tuple = tuple(allowed)
    allowed_set = set(allowed_tuple)
    normalized = _normalize_unique_text_tuple(values, label="paired_engine_id")
    for value in normalized:
        engine_by_id(value)
        if value not in allowed_set:
            raise ValueError(f"Unknown paired_engine_id for role registry: {value}")
    return tuple(value for value in allowed_tuple if value in set(normalized))


def _missing_artifacts(
    *, required: Iterable[ArtifactKind], present: Iterable[ArtifactKind]
) -> tuple[ArtifactKind, ...]:
    """Return required artifact kinds not represented in present values."""

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


def _normalize_unique_enum_tuple(
    values: Iterable[ArtifactKind], *, label: str
) -> tuple[ArtifactKind, ...]:
    """Normalize ArtifactKind tuples while rejecting duplicates."""

    normalized: list[ArtifactKind] = []
    seen: set[ArtifactKind] = set()
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
