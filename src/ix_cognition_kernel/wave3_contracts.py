"""Shared Wave 3 artifact contracts for IX-CognitionKernel.

Wave 3 is the governed AGI-emulation substrate layer. This module defines the
portable evidence artifacts later engines use to coordinate bounded agents,
reward audits, curriculum tasks, WorldTwin scenario reasoning, BlackFox handoff
packages, and assurance records.

These contracts intentionally mirror the donor-repo boundary discipline: a Wave
3 artifact can be reviewed, fingerprinted, blocked, or handed toward human
review, but it is never an execution token and it never permits automatic
authority.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

T = TypeVar("T")
E = TypeVar("E", bound=StrEnum)

WAVE_THREE_ARTIFACT_SCHEMA_VERSION = "ix-cognition-kernel-wave3-artifact-v1"
WAVE_THREE_BUNDLE_SCHEMA_VERSION = "ix-cognition-kernel-wave3-bundle-v1"


class WaveThreeArtifactKind(StrEnum):
    """Required Wave 3 artifact classes."""

    ENGINE_COORDINATION = "engine-coordination"
    ROLE_ARTIFACT = "role-artifact"
    TRIBUNAL_RECORD = "tribunal-record"
    REWARD_AUDIT = "reward-audit"
    CURRICULUM_TASK = "curriculum-task"
    DISCOVERY_RECORD = "discovery-record"
    MEMORY_QUARANTINE_DECISION = "memory-quarantine-decision"
    SKILL_GENOME_UPDATE = "skill-genome-update"
    WORLDTWIN_SCENARIO = "worldtwin-scenario"
    BLACKFOX_HANDOFF = "blackfox-handoff"
    ASSURANCE_RECORD = "assurance-record"
    READINESS_SNAPSHOT = "readiness-snapshot"


class WaveThreeSourceSystem(StrEnum):
    """Source systems allowed to contribute Wave 3 evidence references."""

    IX_COGNITION_KERNEL = "ix-cognition-kernel"
    IX_BLACKFOX = "ix-blackfox"
    IX_BLACKFOX_COGNITION = "ix-blackfox-cognition"
    IX_BLACKFOX_WORLDTWIN = "ix-blackfox-worldtwin"
    HUMAN_REVIEW = "human-review"
    LOCAL_TEST_SUITE = "local-test-suite"
    EXTERNAL_REVIEW = "external-review"


class WaveThreeArtifactDecision(StrEnum):
    """Fail-closed decision state for one Wave 3 artifact."""

    RECORD_ONLY = "record-only"
    NEEDS_EVIDENCE = "needs-evidence"
    READY_FOR_HUMAN_REVIEW = "ready-for-human-review"
    BLOCKED = "blocked"


class WaveThreeAuthorityState(StrEnum):
    """Human-authority state carried by action-adjacent Wave 3 artifacts."""

    RECORD_ONLY = "record-only"
    HUMAN_REVIEW_REQUIRED = "human-review-required"
    HUMAN_AUTHORITY_GRANTED = "human-authority-granted"
    BLOCKED = "blocked"


class WaveThreeEvidenceRelation(StrEnum):
    """How evidence relates to a Wave 3 artifact."""

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    TESTS = "tests"
    DERIVES_FROM = "derives-from"
    REVIEWS = "reviews"
    BLOCKS = "blocks"


WAVE_THREE_REQUIRED_ARTIFACT_KINDS: tuple[WaveThreeArtifactKind, ...] = (
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
    WaveThreeArtifactKind.READINESS_SNAPSHOT,
)


@dataclass(frozen=True, slots=True)
class WaveThreeEvidenceLink:
    """A typed evidence reference bound to one Wave 3 artifact."""

    evidence_id: str
    artifact_id: str
    relation: WaveThreeEvidenceRelation
    summary: str
    source_system: WaveThreeSourceSystem

    def __post_init__(self) -> None:
        """Validate evidence-link identity and reviewability."""

        object.__setattr__(
            self,
            "evidence_id",
            _require_non_empty(self.evidence_id, "evidence_id"),
        )
        object.__setattr__(
            self,
            "artifact_id",
            _require_non_empty(self.artifact_id, "artifact_id"),
        )
        object.__setattr__(
            self,
            "summary",
            _require_non_empty(self.summary, "evidence link summary"),
        )

    @property
    def link_key(self) -> tuple[str, str, str]:
        """Return the unique key for this evidence-artifact relation."""

        return (self.evidence_id, self.artifact_id, self.relation.value)

    def canonical_payload(self) -> dict[str, str]:
        """Return a deterministic payload for evidence-link hashing."""

        return {
            "artifact_id": self.artifact_id,
            "evidence_id": self.evidence_id,
            "relation": self.relation.value,
            "source_system": self.source_system.value,
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class WaveThreeArtifactRef:
    """A reviewable, non-executable Wave 3 artifact reference."""

    artifact_id: str
    kind: WaveThreeArtifactKind
    source_system: WaveThreeSourceSystem
    summary: str
    produced_by_engine_id: str
    evidence_ids: tuple[str, ...]
    produced_by_agent_role_id: str = ""
    decision: WaveThreeArtifactDecision = WaveThreeArtifactDecision.NEEDS_EVIDENCE
    authority_state: WaveThreeAuthorityState = (
        WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
    )
    requires_human_authority: bool = True
    allowed_for_automatic_execution: bool = False
    schema_version: str = WAVE_THREE_ARTIFACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate artifact identity, evidence binding, and authority boundary."""

        if not self.requires_human_authority:
            raise ValueError("Wave 3 artifacts must require human authority awareness.")
        if self.allowed_for_automatic_execution:
            raise ValueError("Wave 3 artifacts must never allow automatic execution.")
        object.__setattr__(
            self,
            "artifact_id",
            _require_non_empty(self.artifact_id, "artifact_id"),
        )
        object.__setattr__(
            self,
            "summary",
            _require_non_empty(self.summary, "artifact summary"),
        )
        object.__setattr__(
            self,
            "produced_by_engine_id",
            _require_non_empty(self.produced_by_engine_id, "produced_by_engine_id"),
        )
        object.__setattr__(
            self,
            "produced_by_agent_role_id",
            self.produced_by_agent_role_id.strip(),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(
                self.evidence_ids, label="artifact evidence_id"
            ),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "artifact schema_version"),
        )
        if (
            self.decision is WaveThreeArtifactDecision.READY_FOR_HUMAN_REVIEW
            and not self.evidence_ids
        ):
            raise ValueError("Ready-for-review Wave 3 artifacts require evidence ids.")
        if (
            self.decision is WaveThreeArtifactDecision.BLOCKED
            and self.authority_state is WaveThreeAuthorityState.HUMAN_AUTHORITY_GRANTED
        ):
            raise ValueError("Blocked Wave 3 artifacts cannot carry granted authority.")

    @property
    def evidence_bound(self) -> bool:
        """Return whether the artifact has at least one evidence id."""

        return bool(self.evidence_ids)

    @property
    def ready_for_human_review(self) -> bool:
        """Return whether this artifact may enter human review."""

        return (
            self.decision is WaveThreeArtifactDecision.READY_FOR_HUMAN_REVIEW
            and self.evidence_bound
            and self.authority_state
            in {
                WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED,
                WaveThreeAuthorityState.HUMAN_AUTHORITY_GRANTED,
            }
        )

    @property
    def blocks_progress(self) -> bool:
        """Return whether this artifact blocks later Wave 3 readiness."""

        return (
            self.decision is WaveThreeArtifactDecision.BLOCKED
            or self.authority_state is WaveThreeAuthorityState.BLOCKED
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for artifact hashing."""

        return {
            "allowed_for_automatic_execution": self.allowed_for_automatic_execution,
            "artifact_id": self.artifact_id,
            "authority_state": self.authority_state.value,
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "kind": self.kind.value,
            "produced_by_agent_role_id": self.produced_by_agent_role_id,
            "produced_by_engine_id": self.produced_by_engine_id,
            "requires_human_authority": self.requires_human_authority,
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this artifact."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveThreeArtifactBundle:
    """A deterministic bundle of Wave 3 artifacts and their evidence links."""

    bundle_id: str
    artifacts: tuple[WaveThreeArtifactRef, ...]
    evidence_links: tuple[WaveThreeEvidenceLink, ...]
    required_kinds: tuple[WaveThreeArtifactKind, ...] = ()
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_THREE_BUNDLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate artifact bundle uniqueness, references, and evidence coverage."""

        object.__setattr__(
            self,
            "bundle_id",
            _require_non_empty(self.bundle_id, "bundle_id"),
        )
        if not self.artifacts:
            raise ValueError("Wave 3 artifact bundles require at least one artifact.")
        sorted_artifacts = tuple(
            sorted(self.artifacts, key=lambda artifact: artifact.artifact_id)
        )
        sorted_links = tuple(
            sorted(self.evidence_links, key=lambda link: link.link_key)
        )
        artifact_ids = _unique_ids(
            (artifact.artifact_id for artifact in sorted_artifacts),
            label="artifact_id",
        )
        _unique_ids((link.link_key for link in sorted_links), label="evidence link")
        for link in sorted_links:
            if link.artifact_id not in artifact_ids:
                raise ValueError(
                    "Wave 3 evidence links must reference bundled artifacts: "
                    f"{link.artifact_id}"
                )
        linked_evidence_ids_by_artifact = _linked_evidence_ids_by_artifact(sorted_links)
        for artifact in sorted_artifacts:
            linked_ids = linked_evidence_ids_by_artifact.get(
                artifact.artifact_id, set()
            )
            missing_links = tuple(
                evidence_id
                for evidence_id in artifact.evidence_ids
                if evidence_id not in linked_ids
            )
            if missing_links:
                raise ValueError(
                    "Wave 3 artifact evidence ids require matching evidence links: "
                    f"{artifact.artifact_id}:{missing_links[0]}"
                )
        object.__setattr__(self, "artifacts", sorted_artifacts)
        object.__setattr__(self, "evidence_links", sorted_links)
        object.__setattr__(
            self,
            "required_kinds",
            _normalize_unique_enum_tuple(self.required_kinds, label="required kind"),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_unique_text_tuple(self.notes, label="bundle note"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "bundle schema_version"),
        )

    @property
    def artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids in deterministic bundle order."""

        return tuple(artifact.artifact_id for artifact in self.artifacts)

    @property
    def blocked_artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids that block progress."""

        return tuple(
            artifact.artifact_id
            for artifact in self.artifacts
            if artifact.blocks_progress
        )

    @property
    def ready_for_human_review_artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids that may enter human review."""

        return tuple(
            artifact.artifact_id
            for artifact in self.artifacts
            if artifact.ready_for_human_review
        )

    @property
    def missing_required_kinds(self) -> tuple[WaveThreeArtifactKind, ...]:
        """Return required artifact kinds not represented in this bundle."""

        present = {artifact.kind for artifact in self.artifacts}
        return tuple(kind for kind in self.required_kinds if kind not in present)

    @property
    def has_required_kind_coverage(self) -> bool:
        """Return whether every requested artifact kind is represented."""

        return not self.missing_required_kinds

    @property
    def evidence_link_table(self) -> Mapping[str, tuple[str, ...]]:
        """Return artifact ids mapped to sorted linked evidence ids."""

        linked = _linked_evidence_ids_by_artifact(self.evidence_links)
        return {
            artifact_id: tuple(sorted(evidence_ids))
            for artifact_id, evidence_ids in sorted(linked.items())
        }

    def artifact_by_id(self, artifact_id: str) -> WaveThreeArtifactRef:
        """Return one artifact by id."""

        for artifact in self.artifacts:
            if artifact.artifact_id == artifact_id:
                return artifact
        raise ValueError(f"Unknown Wave 3 artifact_id: {artifact_id}")

    def artifact_ids_by_kind(self, kind: WaveThreeArtifactKind) -> tuple[str, ...]:
        """Return artifact ids matching a required Wave 3 kind."""

        return tuple(
            artifact.artifact_id for artifact in self.artifacts if artifact.kind is kind
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for bundle hashing."""

        return {
            "artifacts": [artifact.canonical_payload() for artifact in self.artifacts],
            "bundle_id": self.bundle_id,
            "evidence_links": [
                link.canonical_payload() for link in self.evidence_links
            ],
            "notes": list(self.notes),
            "required_kinds": [kind.value for kind in self.required_kinds],
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this bundle."""

        return _stable_sha256(self.canonical_payload())


def required_wave_three_artifact_kinds() -> tuple[WaveThreeArtifactKind, ...]:
    """Return the locked required artifact kinds for Wave 3 readiness."""

    return WAVE_THREE_REQUIRED_ARTIFACT_KINDS


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


def _normalize_unique_enum_tuple(values: Iterable[E], *, label: str) -> tuple[E, ...]:
    """Return a tuple of enum values while rejecting duplicates."""

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


def _linked_evidence_ids_by_artifact(
    evidence_links: Iterable[WaveThreeEvidenceLink],
) -> dict[str, set[str]]:
    """Group evidence ids by linked artifact id."""

    grouped: dict[str, set[str]] = {}
    for link in evidence_links:
        grouped.setdefault(link.artifact_id, set()).add(link.evidence_id)
    return grouped


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
