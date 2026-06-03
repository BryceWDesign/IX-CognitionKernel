"""Shared Wave 4 proto-candidate contracts for IX-CognitionKernel.

Wave 4 is the controlled Proto-AGI Candidate layer. The contracts in this
module define reviewable evidence objects for early proto-candidate behavior
without turning any result into an AGI claim, an execution token, or automatic
authority. They deliberately preserve the donor-repo discipline used by
IX-BlackFox and IX-BlackFox-WorldTwin: every candidate artifact is evidence
bound, digestible, human-reviewable, and fail-closed.
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

WAVE_FOUR_ARTIFACT_SCHEMA_VERSION = "ix-cognition-kernel-wave4-artifact-v1"
WAVE_FOUR_BUNDLE_SCHEMA_VERSION = "ix-cognition-kernel-wave4-bundle-v1"


class WaveFourCapabilityArea(StrEnum):
    """Controlled behavior areas required before a Wave 4 claim is credible."""

    CROSS_DOMAIN_TRANSFER = "cross-domain-transfer"
    SELF_IMPROVEMENT_AFTER_FAILURE = "self-improvement-after-failure"
    UNCERTAINTY_PRESERVATION = "uncertainty-preservation"
    LONG_HORIZON_MISSION_STATE = "long-horizon-mission-state"
    SAFE_REFUSAL = "safe-refusal"
    REWARD_HACKING_DETECTION = "reward-hacking-detection"
    ADVERSARIAL_ROBUSTNESS = "adversarial-robustness"
    AUDIT_TRAIL = "audit-trail"


class WaveFourArtifactKind(StrEnum):
    """Required Wave 4 artifact classes."""

    CONTROLLED_TRIAL = "controlled-trial"
    TRANSFER_EVALUATION = "transfer-evaluation"
    FAILURE_REPAIR_CYCLE = "failure-repair-cycle"
    UNCERTAINTY_TRACE = "uncertainty-trace"
    MISSION_STATE_TRACE = "mission-state-trace"
    SAFE_REFUSAL_RECORD = "safe-refusal-record"
    REWARD_HACKING_AUDIT = "reward-hacking-audit"
    ADVERSARIAL_ROBUSTNESS_RECORD = "adversarial-robustness-record"
    REPRODUCIBLE_AUDIT_TRAIL = "reproducible-audit-trail"
    READINESS_SNAPSHOT = "readiness-snapshot"


class WaveFourSourceSystem(StrEnum):
    """Source systems allowed to contribute Wave 4 evidence references."""

    IX_COGNITION_KERNEL = "ix-cognition-kernel"
    IX_BLACKFOX = "ix-blackfox"
    IX_BLACKFOX_WORLDTWIN = "ix-blackfox-worldtwin"
    HUMAN_REVIEW = "human-review"
    LOCAL_TEST_SUITE = "local-test-suite"
    EXTERNAL_REVIEW = "external-review"


class WaveFourArtifactDecision(StrEnum):
    """Fail-closed decision state for one Wave 4 artifact."""

    RECORD_ONLY = "record-only"
    NEEDS_EVIDENCE = "needs-evidence"
    READY_FOR_CONTROLLED_REVIEW = "ready-for-controlled-review"
    BLOCKED = "blocked"


class WaveFourAuthorityState(StrEnum):
    """Human-authority state carried by action-adjacent Wave 4 artifacts."""

    RECORD_ONLY = "record-only"
    HUMAN_REVIEW_REQUIRED = "human-review-required"
    HUMAN_AUTHORITY_GRANTED = "human-authority-granted"
    BLOCKED = "blocked"


class WaveFourEvidenceRelation(StrEnum):
    """How evidence relates to a Wave 4 proto-candidate artifact."""

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    TESTS = "tests"
    DERIVES_FROM = "derives-from"
    REVIEWS = "reviews"
    BLOCKS = "blocks"


WAVE_FOUR_REQUIRED_CAPABILITY_AREAS: tuple[WaveFourCapabilityArea, ...] = (
    WaveFourCapabilityArea.CROSS_DOMAIN_TRANSFER,
    WaveFourCapabilityArea.SELF_IMPROVEMENT_AFTER_FAILURE,
    WaveFourCapabilityArea.UNCERTAINTY_PRESERVATION,
    WaveFourCapabilityArea.LONG_HORIZON_MISSION_STATE,
    WaveFourCapabilityArea.SAFE_REFUSAL,
    WaveFourCapabilityArea.REWARD_HACKING_DETECTION,
    WaveFourCapabilityArea.ADVERSARIAL_ROBUSTNESS,
    WaveFourCapabilityArea.AUDIT_TRAIL,
)

WAVE_FOUR_REQUIRED_ARTIFACT_KINDS: tuple[WaveFourArtifactKind, ...] = (
    WaveFourArtifactKind.CONTROLLED_TRIAL,
    WaveFourArtifactKind.TRANSFER_EVALUATION,
    WaveFourArtifactKind.FAILURE_REPAIR_CYCLE,
    WaveFourArtifactKind.UNCERTAINTY_TRACE,
    WaveFourArtifactKind.MISSION_STATE_TRACE,
    WaveFourArtifactKind.SAFE_REFUSAL_RECORD,
    WaveFourArtifactKind.REWARD_HACKING_AUDIT,
    WaveFourArtifactKind.ADVERSARIAL_ROBUSTNESS_RECORD,
    WaveFourArtifactKind.REPRODUCIBLE_AUDIT_TRAIL,
    WaveFourArtifactKind.READINESS_SNAPSHOT,
)


@dataclass(frozen=True, slots=True)
class WaveFourEvidenceLink:
    """A typed evidence reference bound to one Wave 4 artifact."""

    evidence_id: str
    artifact_id: str
    relation: WaveFourEvidenceRelation
    summary: str
    source_system: WaveFourSourceSystem

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
class WaveFourArtifactRef:
    """A reviewable, non-executable Wave 4 proto-candidate artifact reference."""

    artifact_id: str
    kind: WaveFourArtifactKind
    capability_area: WaveFourCapabilityArea
    source_system: WaveFourSourceSystem
    summary: str
    produced_by_engine_id: str
    evidence_ids: tuple[str, ...]
    produced_by_agent_role_id: str = ""
    decision: WaveFourArtifactDecision = WaveFourArtifactDecision.NEEDS_EVIDENCE
    authority_state: WaveFourAuthorityState = (
        WaveFourAuthorityState.HUMAN_REVIEW_REQUIRED
    )
    requires_human_authority: bool = True
    allowed_for_automatic_execution: bool = False
    claims_agi: bool = False
    independently_validated: bool = False
    schema_version: str = WAVE_FOUR_ARTIFACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate artifact identity, evidence binding, and claim boundary."""

        if not self.requires_human_authority:
            raise ValueError("Wave 4 artifacts must require human authority awareness.")
        if self.allowed_for_automatic_execution:
            raise ValueError("Wave 4 artifacts must never allow automatic execution.")
        if self.claims_agi:
            raise ValueError("Wave 4 artifacts must not claim AGI.")
        if self.independently_validated:
            raise ValueError(
                "Wave 4 artifacts must not claim independent validation; "
                "that boundary belongs to Wave 5."
            )
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
            self.decision is WaveFourArtifactDecision.READY_FOR_CONTROLLED_REVIEW
            and not self.evidence_ids
        ):
            raise ValueError(
                "Ready-for-controlled-review Wave 4 artifacts require evidence ids."
            )
        if (
            self.decision is WaveFourArtifactDecision.BLOCKED
            and self.authority_state is WaveFourAuthorityState.HUMAN_AUTHORITY_GRANTED
        ):
            raise ValueError("Blocked Wave 4 artifacts cannot carry granted authority.")

    @property
    def evidence_bound(self) -> bool:
        """Return whether the artifact has at least one evidence id."""

        return bool(self.evidence_ids)

    @property
    def ready_for_controlled_review(self) -> bool:
        """Return whether this artifact may enter controlled human review."""

        return (
            self.decision is WaveFourArtifactDecision.READY_FOR_CONTROLLED_REVIEW
            and self.evidence_bound
            and self.authority_state
            in {
                WaveFourAuthorityState.HUMAN_REVIEW_REQUIRED,
                WaveFourAuthorityState.HUMAN_AUTHORITY_GRANTED,
            }
            and not self.claims_agi
            and not self.allowed_for_automatic_execution
            and not self.independently_validated
        )

    @property
    def blocks_progress(self) -> bool:
        """Return whether this artifact blocks later Wave 4 readiness."""

        return (
            self.decision is WaveFourArtifactDecision.BLOCKED
            or self.authority_state is WaveFourAuthorityState.BLOCKED
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for artifact hashing."""

        return {
            "allowed_for_automatic_execution": self.allowed_for_automatic_execution,
            "artifact_id": self.artifact_id,
            "authority_state": self.authority_state.value,
            "capability_area": self.capability_area.value,
            "claims_agi": self.claims_agi,
            "decision": self.decision.value,
            "evidence_ids": list(self.evidence_ids),
            "independently_validated": self.independently_validated,
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
class WaveFourArtifactBundle:
    """A deterministic bundle of Wave 4 artifacts and their evidence links."""

    bundle_id: str
    artifacts: tuple[WaveFourArtifactRef, ...]
    evidence_links: tuple[WaveFourEvidenceLink, ...]
    required_kinds: tuple[WaveFourArtifactKind, ...] = ()
    required_capability_areas: tuple[WaveFourCapabilityArea, ...] = ()
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_FOUR_BUNDLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate artifact bundle uniqueness, references, and evidence coverage."""

        object.__setattr__(
            self,
            "bundle_id",
            _require_non_empty(self.bundle_id, "bundle_id"),
        )
        if not self.artifacts:
            raise ValueError("Wave 4 artifact bundles require at least one artifact.")
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
                    "Wave 4 evidence links must reference bundled artifacts: "
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
                    "Wave 4 artifact evidence ids require matching evidence links: "
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
            "required_capability_areas",
            _normalize_unique_enum_tuple(
                self.required_capability_areas, label="required capability area"
            ),
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
    def ready_for_controlled_review_artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids that may enter controlled human review."""

        return tuple(
            artifact.artifact_id
            for artifact in self.artifacts
            if artifact.ready_for_controlled_review
        )

    @property
    def missing_required_kinds(self) -> tuple[WaveFourArtifactKind, ...]:
        """Return required artifact kinds not represented in this bundle."""

        present = {artifact.kind for artifact in self.artifacts}
        return tuple(kind for kind in self.required_kinds if kind not in present)

    @property
    def missing_required_capability_areas(self) -> tuple[WaveFourCapabilityArea, ...]:
        """Return required capability areas not represented in this bundle."""

        present = {artifact.capability_area for artifact in self.artifacts}
        return tuple(
            area for area in self.required_capability_areas if area not in present
        )

    @property
    def has_required_kind_coverage(self) -> bool:
        """Return whether every requested artifact kind is represented."""

        return not self.missing_required_kinds

    @property
    def has_required_capability_coverage(self) -> bool:
        """Return whether every requested capability area is represented."""

        return not self.missing_required_capability_areas

    @property
    def evidence_link_table(self) -> Mapping[str, tuple[str, ...]]:
        """Return artifact ids mapped to sorted linked evidence ids."""

        linked = _linked_evidence_ids_by_artifact(self.evidence_links)
        return {
            artifact_id: tuple(sorted(evidence_ids))
            for artifact_id, evidence_ids in sorted(linked.items())
        }

    def artifact_by_id(self, artifact_id: str) -> WaveFourArtifactRef:
        """Return one artifact by id."""

        for artifact in self.artifacts:
            if artifact.artifact_id == artifact_id:
                return artifact
        raise ValueError(f"Unknown Wave 4 artifact_id: {artifact_id}")

    def artifact_ids_by_kind(self, kind: WaveFourArtifactKind) -> tuple[str, ...]:
        """Return artifact ids matching a required Wave 4 kind."""

        return tuple(
            artifact.artifact_id for artifact in self.artifacts if artifact.kind is kind
        )

    def artifact_ids_by_capability_area(
        self, capability_area: WaveFourCapabilityArea
    ) -> tuple[str, ...]:
        """Return artifact ids matching a required Wave 4 capability area."""

        return tuple(
            artifact.artifact_id
            for artifact in self.artifacts
            if artifact.capability_area is capability_area
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
            "required_capability_areas": [
                area.value for area in self.required_capability_areas
            ],
            "required_kinds": [kind.value for kind in self.required_kinds],
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this bundle."""

        return _stable_sha256(self.canonical_payload())


def required_wave_four_artifact_kinds() -> tuple[WaveFourArtifactKind, ...]:
    """Return the locked required artifact kinds for Wave 4 readiness."""

    return WAVE_FOUR_REQUIRED_ARTIFACT_KINDS


def required_wave_four_capability_areas() -> tuple[WaveFourCapabilityArea, ...]:
    """Return the locked required behavior areas for Wave 4 readiness."""

    return WAVE_FOUR_REQUIRED_CAPABILITY_AREAS


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
    evidence_links: Iterable[WaveFourEvidenceLink],
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
