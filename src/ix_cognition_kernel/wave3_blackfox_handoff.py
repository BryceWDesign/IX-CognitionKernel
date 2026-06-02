"""Wave 3 BlackFox handoff package records for IX-CognitionKernel.

The BlackFox handoff layer packages cognition evidence for a downstream governed
execution/control plane without becoming execution authority. The package mirrors
IX-BlackFox donor discipline: model output is untrusted input, policy gates and
review requirements remain explicit, rollback evidence stays attached, and human
authority is required before any operational system may act.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

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

WAVE_THREE_BLACKFOX_BOUNDARY_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave3-blackfox-boundary-v1"
)
WAVE_THREE_BLACKFOX_REVIEW_REQUIREMENT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave3-blackfox-review-requirement-v1"
)
WAVE_THREE_BLACKFOX_ROLLBACK_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave3-blackfox-rollback-v1"
)
WAVE_THREE_BLACKFOX_HANDOFF_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave3-blackfox-handoff-v1"
)
WAVE_THREE_BLACKFOX_HANDOFF_BUNDLE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave3-blackfox-handoff-bundle-v1"
)


class BlackFoxHandoffBoundaryKind(StrEnum):
    """Boundary families expected by a BlackFox-style review handoff."""

    POLICY_GATE = "policy-gate"
    WORKSPACE_ISOLATION = "workspace-isolation"
    EGRESS_CONTROL = "egress-control"
    TEST_ALLOWLIST = "test-allowlist"
    HUMAN_REVIEW = "human-review"
    ROLLBACK = "rollback"


class BlackFoxReviewRequirementKind(StrEnum):
    """Review requirements that must stay visible in a handoff package."""

    HUMAN_APPROVAL = "human-approval"
    POLICY_REVIEW = "policy-review"
    EVIDENCE_REPLAY = "evidence-replay"
    ROLLBACK_REVIEW = "rollback-review"
    NO_SELF_APPROVAL = "no-self-approval"


class BlackFoxHandoffStatus(StrEnum):
    """Fail-closed status for a BlackFox handoff package."""

    READY_FOR_HUMAN_REVIEW = "ready-for-human-review"
    NEEDS_EVIDENCE = "needs-evidence"
    NEEDS_REPAIR = "needs-repair"
    BLOCKED = "blocked"


REQUIRED_BLACKFOX_BOUNDARY_KINDS: tuple[BlackFoxHandoffBoundaryKind, ...] = (
    BlackFoxHandoffBoundaryKind.POLICY_GATE,
    BlackFoxHandoffBoundaryKind.WORKSPACE_ISOLATION,
    BlackFoxHandoffBoundaryKind.EGRESS_CONTROL,
    BlackFoxHandoffBoundaryKind.TEST_ALLOWLIST,
    BlackFoxHandoffBoundaryKind.HUMAN_REVIEW,
    BlackFoxHandoffBoundaryKind.ROLLBACK,
)

REQUIRED_BLACKFOX_REVIEW_REQUIREMENT_KINDS: tuple[
    BlackFoxReviewRequirementKind, ...
] = (
    BlackFoxReviewRequirementKind.HUMAN_APPROVAL,
    BlackFoxReviewRequirementKind.POLICY_REVIEW,
    BlackFoxReviewRequirementKind.EVIDENCE_REPLAY,
    BlackFoxReviewRequirementKind.ROLLBACK_REVIEW,
    BlackFoxReviewRequirementKind.NO_SELF_APPROVAL,
)


@dataclass(frozen=True, slots=True)
class BlackFoxExecutionBoundary:
    """A boundary that prevents a handoff from becoming executable authority."""

    boundary_id: str
    kind: BlackFoxHandoffBoundaryKind
    description: str
    evidence_ids: tuple[str, ...]
    enforced: bool = True
    schema_version: str = WAVE_THREE_BLACKFOX_BOUNDARY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate boundary identity, evidence, and enforcement state."""

        object.__setattr__(self, "boundary_id", _text(self.boundary_id, "boundary_id"))
        object.__setattr__(
            self, "description", _text(self.description, "boundary description")
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="boundary evidence_id"),
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.enforced and not self.evidence_ids:
            raise ValueError("Enforced BlackFox boundaries require evidence ids.")

    @property
    def boundary_key(self) -> tuple[str, str]:
        """Return deterministic uniqueness key for this boundary."""

        return (self.boundary_id, self.kind.value)

    @property
    def readiness_gap(self) -> str:
        """Return the boundary gap when enforcement is absent."""

        if self.enforced:
            return ""
        return f"BlackFox boundary is not enforced: {self.boundary_id}"

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "boundary_id": self.boundary_id,
            "description": self.description,
            "enforced": self.enforced,
            "evidence_ids": list(self.evidence_ids),
            "kind": self.kind.value,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class BlackFoxReviewRequirement:
    """A required human-review condition for a BlackFox handoff package."""

    requirement_id: str
    requirement_kind: BlackFoxReviewRequirementKind
    reviewer_role: str
    description: str
    evidence_ids: tuple[str, ...]
    satisfied: bool = True
    forbids_model_or_system_self_approval: bool = True
    schema_version: str = WAVE_THREE_BLACKFOX_REVIEW_REQUIREMENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate review requirement evidence and anti-self-approval rule."""

        object.__setattr__(
            self, "requirement_id", _text(self.requirement_id, "requirement_id")
        )
        object.__setattr__(
            self, "reviewer_role", _text(self.reviewer_role, "reviewer_role")
        )
        object.__setattr__(
            self, "description", _text(self.description, "requirement description")
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="requirement evidence_id"),
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if not self.forbids_model_or_system_self_approval:
            raise ValueError(
                "BlackFox review requirements must forbid model/system self-approval."
            )
        if self.satisfied and not self.evidence_ids:
            raise ValueError(
                "Satisfied BlackFox review requirements require evidence ids."
            )

    @property
    def requirement_key(self) -> tuple[str, str]:
        """Return deterministic uniqueness key for this requirement."""

        return (self.requirement_id, self.requirement_kind.value)

    @property
    def readiness_gap(self) -> str:
        """Return the requirement gap when the requirement is unsatisfied."""

        if self.satisfied:
            return ""
        return f"BlackFox review requirement is unsatisfied: {self.requirement_id}"

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "description": self.description,
            "evidence_ids": list(self.evidence_ids),
            "forbids_model_or_system_self_approval": (
                self.forbids_model_or_system_self_approval
            ),
            "requirement_id": self.requirement_id,
            "requirement_kind": self.requirement_kind.value,
            "reviewer_role": self.reviewer_role,
            "satisfied": self.satisfied,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class BlackFoxRollbackReference:
    """Rollback reference that must travel with a review handoff."""

    rollback_id: str
    description: str
    trigger_conditions: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    validated: bool = True
    schema_version: str = WAVE_THREE_BLACKFOX_ROLLBACK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate rollback reference, triggers, and evidence."""

        object.__setattr__(self, "rollback_id", _text(self.rollback_id, "rollback_id"))
        object.__setattr__(
            self, "description", _text(self.description, "rollback description")
        )
        object.__setattr__(
            self,
            "trigger_conditions",
            _unique_text(self.trigger_conditions, label="rollback trigger condition"),
        )
        if not self.trigger_conditions:
            raise ValueError("BlackFox rollback references require trigger conditions.")
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="rollback evidence_id"),
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.validated and not self.evidence_ids:
            raise ValueError(
                "Validated BlackFox rollback references require evidence ids."
            )

    @property
    def rollback_key(self) -> str:
        """Return deterministic uniqueness key for this rollback reference."""

        return self.rollback_id

    @property
    def readiness_gap(self) -> str:
        """Return the rollback gap when validation is absent."""

        if self.validated:
            return ""
        return f"BlackFox rollback reference is not validated: {self.rollback_id}"

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "description": self.description,
            "evidence_ids": list(self.evidence_ids),
            "rollback_id": self.rollback_id,
            "schema_version": self.schema_version,
            "trigger_conditions": list(self.trigger_conditions),
            "validated": self.validated,
        }


@dataclass(frozen=True, slots=True)
class BlackFoxHandoffPackage:
    """Review-only handoff package from cognition to a BlackFox-style boundary."""

    handoff_id: str
    subject: str
    cognition_artifact_ids: tuple[str, ...]
    evidence_bundle_ids: tuple[str, ...]
    execution_boundaries: tuple[BlackFoxExecutionBoundary, ...]
    review_requirements: tuple[BlackFoxReviewRequirement, ...]
    rollback_references: tuple[BlackFoxRollbackReference, ...]
    evidence_ids: tuple[str, ...]
    requested_blackfox_scope: str = "human-review-bundle"
    produced_by_engine_id: str = "blackfox-handoff"
    produced_by_agent_role_id: str = "execution-liaison"
    target_system: str = "IX-BlackFox"
    requires_human_authority: bool = True
    allowed_for_automatic_execution: bool = False
    schema_version: str = WAVE_THREE_BLACKFOX_HANDOFF_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate handoff scope, review evidence, rollback, and authority."""

        if not self.requires_human_authority:
            raise ValueError("BlackFox handoff packages must require human authority.")
        if self.allowed_for_automatic_execution:
            raise ValueError(
                "BlackFox handoff packages must never allow automatic execution."
            )
        object.__setattr__(self, "handoff_id", _text(self.handoff_id, "handoff_id"))
        object.__setattr__(self, "subject", _text(self.subject, "subject"))
        object.__setattr__(
            self,
            "cognition_artifact_ids",
            _unique_text(self.cognition_artifact_ids, label="cognition artifact_id"),
        )
        if not self.cognition_artifact_ids:
            raise ValueError("BlackFox handoff packages require cognition artifacts.")
        object.__setattr__(
            self,
            "evidence_bundle_ids",
            _unique_text(self.evidence_bundle_ids, label="evidence bundle_id"),
        )
        if not self.evidence_bundle_ids:
            raise ValueError("BlackFox handoff packages require evidence bundle ids.")
        boundaries = tuple(
            sorted(self.execution_boundaries, key=lambda item: item.boundary_key)
        )
        requirements = tuple(
            sorted(self.review_requirements, key=lambda item: item.requirement_key)
        )
        rollbacks = tuple(
            sorted(self.rollback_references, key=lambda item: item.rollback_key)
        )
        if not boundaries:
            raise ValueError("BlackFox handoff packages require execution boundaries.")
        if not requirements:
            raise ValueError("BlackFox handoff packages require review requirements.")
        if not rollbacks:
            raise ValueError("BlackFox handoff packages require rollback references.")
        _unique_values((item.boundary_id for item in boundaries), label="boundary_id")
        _unique_values((item.kind for item in boundaries), label="boundary kind")
        _unique_values(
            (item.requirement_id for item in requirements), label="requirement_id"
        )
        _unique_values(
            (item.requirement_kind for item in requirements),
            label="review requirement kind",
        )
        _unique_values((item.rollback_id for item in rollbacks), label="rollback_id")
        object.__setattr__(self, "execution_boundaries", boundaries)
        object.__setattr__(self, "review_requirements", requirements)
        object.__setattr__(self, "rollback_references", rollbacks)
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="handoff evidence_id"),
        )
        object.__setattr__(
            self,
            "requested_blackfox_scope",
            _text(self.requested_blackfox_scope, "requested_blackfox_scope"),
        )
        object.__setattr__(
            self,
            "produced_by_engine_id",
            _text(self.produced_by_engine_id, "produced_by_engine_id"),
        )
        if self.produced_by_engine_id != "blackfox-handoff":
            raise ValueError("BlackFox handoffs must be produced by blackfox-handoff.")
        object.__setattr__(
            self,
            "produced_by_agent_role_id",
            _text(self.produced_by_agent_role_id, "produced_by_agent_role_id"),
        )
        if self.produced_by_agent_role_id != "execution-liaison":
            raise ValueError("BlackFox handoffs must be produced by execution-liaison.")
        object.__setattr__(
            self, "target_system", _text(self.target_system, "target_system")
        )
        if self.target_system != "IX-BlackFox":
            raise ValueError("BlackFox handoff target_system must be IX-BlackFox.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def artifact_id(self) -> str:
        """Return the shared Wave 3 artifact id for this handoff package."""

        return f"blackfox-handoff:{self.handoff_id}"

    @property
    def represented_boundary_kinds(self) -> tuple[BlackFoxHandoffBoundaryKind, ...]:
        """Return represented boundary kinds in required-kind order when possible."""

        present = {boundary.kind for boundary in self.execution_boundaries}
        required_order = tuple(
            kind for kind in REQUIRED_BLACKFOX_BOUNDARY_KINDS if kind in present
        )
        extra_order = tuple(
            sorted(
                (kind for kind in present if kind not in set(required_order)),
                key=lambda kind: kind.value,
            )
        )
        return required_order + extra_order

    @property
    def represented_review_requirement_kinds(
        self,
    ) -> tuple[BlackFoxReviewRequirementKind, ...]:
        """Return represented review requirement kinds in required-kind order."""

        present = {item.requirement_kind for item in self.review_requirements}
        required_order = tuple(
            kind
            for kind in REQUIRED_BLACKFOX_REVIEW_REQUIREMENT_KINDS
            if kind in present
        )
        extra_order = tuple(
            sorted(
                (kind for kind in present if kind not in set(required_order)),
                key=lambda kind: kind.value,
            )
        )
        return required_order + extra_order

    @property
    def missing_required_boundary_kinds(
        self,
    ) -> tuple[BlackFoxHandoffBoundaryKind, ...]:
        """Return required BlackFox boundary kinds not represented."""

        present = {boundary.kind for boundary in self.execution_boundaries}
        return tuple(
            kind for kind in REQUIRED_BLACKFOX_BOUNDARY_KINDS if kind not in present
        )

    @property
    def missing_required_review_requirement_kinds(
        self,
    ) -> tuple[BlackFoxReviewRequirementKind, ...]:
        """Return required BlackFox review requirement kinds not represented."""

        present = {item.requirement_kind for item in self.review_requirements}
        return tuple(
            kind
            for kind in REQUIRED_BLACKFOX_REVIEW_REQUIREMENT_KINDS
            if kind not in present
        )

    @property
    def unenforced_boundary_ids(self) -> tuple[str, ...]:
        """Return boundary ids not currently enforced."""

        return tuple(
            boundary.boundary_id
            for boundary in self.execution_boundaries
            if not boundary.enforced
        )

    @property
    def unsatisfied_requirement_ids(self) -> tuple[str, ...]:
        """Return review requirement ids not currently satisfied."""

        return tuple(
            requirement.requirement_id
            for requirement in self.review_requirements
            if not requirement.satisfied
        )

    @property
    def unvalidated_rollback_ids(self) -> tuple[str, ...]:
        """Return rollback ids not currently validated."""

        return tuple(
            rollback.rollback_id
            for rollback in self.rollback_references
            if not rollback.validated
        )

    @property
    def boundary_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted unique evidence ids from boundaries."""

        return tuple(
            sorted(
                evidence_id
                for boundary in self.execution_boundaries
                for evidence_id in boundary.evidence_ids
            )
        )

    @property
    def requirement_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted unique evidence ids from review requirements."""

        return tuple(
            sorted(
                evidence_id
                for requirement in self.review_requirements
                for evidence_id in requirement.evidence_ids
            )
        )

    @property
    def rollback_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted unique evidence ids from rollback references."""

        return tuple(
            sorted(
                evidence_id
                for rollback in self.rollback_references
                for evidence_id in rollback.evidence_ids
            )
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted unique package and component evidence ids."""

        return tuple(
            sorted(
                set(self.evidence_ids).union(
                    self.boundary_evidence_ids,
                    self.requirement_evidence_ids,
                    self.rollback_evidence_ids,
                )
            )
        )

    @property
    def permits_automatic_execution(self) -> bool:
        """Return whether this package permits automatic execution."""

        return False

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return non-blocking gaps that prevent human-review readiness."""

        gaps: list[str] = []
        if not self.evidence_ids:
            gaps.append(f"{self.handoff_id} has no top-level evidence ids")
        if self.missing_required_boundary_kinds:
            gaps.append(
                "missing BlackFox boundary kinds: "
                + ", ".join(kind.value for kind in self.missing_required_boundary_kinds)
            )
        if self.missing_required_review_requirement_kinds:
            gaps.append(
                "missing BlackFox review requirement kinds: "
                + ", ".join(
                    kind.value
                    for kind in self.missing_required_review_requirement_kinds
                )
            )
        if self.unsatisfied_requirement_ids:
            gaps.append(
                "unsatisfied BlackFox review requirements: "
                + ", ".join(self.unsatisfied_requirement_ids)
            )
        if self.unvalidated_rollback_ids:
            gaps.append(
                "unvalidated BlackFox rollback references: "
                + ", ".join(self.unvalidated_rollback_ids)
            )
        return tuple(gaps)

    @property
    def blocking_gaps(self) -> tuple[str, ...]:
        """Return blocking gaps that stop handoff progress."""

        if not self.unenforced_boundary_ids:
            return ()
        return (
            "unenforced BlackFox execution boundaries: "
            + ", ".join(self.unenforced_boundary_ids),
        )

    @property
    def status(self) -> BlackFoxHandoffStatus:
        """Return the fail-closed BlackFox handoff status."""

        if self.blocking_gaps:
            return BlackFoxHandoffStatus.BLOCKED
        if self.unvalidated_rollback_ids or self.unsatisfied_requirement_ids:
            return BlackFoxHandoffStatus.NEEDS_REPAIR
        if self.readiness_gaps:
            return BlackFoxHandoffStatus.NEEDS_EVIDENCE
        return BlackFoxHandoffStatus.READY_FOR_HUMAN_REVIEW

    @property
    def ready_for_human_review(self) -> bool:
        """Return whether this handoff may enter human review."""

        return self.status is BlackFoxHandoffStatus.READY_FOR_HUMAN_REVIEW

    @property
    def human_authority_state(self) -> WaveThreeAuthorityState:
        """Return aggregate human-authority state for this handoff package."""

        if self.status is BlackFoxHandoffStatus.BLOCKED:
            return WaveThreeAuthorityState.BLOCKED
        return WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED

    @property
    def review_summary(self) -> str:
        """Return a concise human-review summary."""

        return (
            f"{self.handoff_id}: {self.status.value}; "
            f"{len(self.cognition_artifact_ids)} cognition artifacts, "
            f"{len(self.execution_boundaries)} boundaries, "
            f"{len(self.review_requirements)} review requirements; "
            "automatic execution is not permitted."
        )

    def to_artifact_ref(self) -> WaveThreeArtifactRef:
        """Convert this handoff package into a shared Wave 3 artifact reference."""

        if self.status is BlackFoxHandoffStatus.READY_FOR_HUMAN_REVIEW:
            decision = WaveThreeArtifactDecision.READY_FOR_HUMAN_REVIEW
            authority_state = WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
        elif self.status is BlackFoxHandoffStatus.BLOCKED:
            decision = WaveThreeArtifactDecision.BLOCKED
            authority_state = WaveThreeAuthorityState.BLOCKED
        else:
            decision = WaveThreeArtifactDecision.NEEDS_EVIDENCE
            authority_state = WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
        return WaveThreeArtifactRef(
            artifact_id=self.artifact_id,
            kind=WaveThreeArtifactKind.BLACKFOX_HANDOFF,
            source_system=WaveThreeSourceSystem.IX_BLACKFOX,
            summary=self.review_summary,
            produced_by_engine_id=self.produced_by_engine_id,
            produced_by_agent_role_id=self.produced_by_agent_role_id,
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=authority_state,
        )

    def to_artifact_bundle(self, *, artifact_bundle_id: str) -> WaveThreeArtifactBundle:
        """Convert this handoff package into a shared artifact bundle."""

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
                        "BlackFox handoff evidence preserves policy gates, review "
                        "requirements, rollback, and human-authority boundaries."
                    ),
                    source_system=WaveThreeSourceSystem.IX_BLACKFOX,
                )
                for evidence_id in artifact.evidence_ids
            ),
            required_kinds=(WaveThreeArtifactKind.BLACKFOX_HANDOFF,),
            notes=(
                "BlackFox handoff artifacts are human-review packages, "
                "not execution tokens.",
            ),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "all_evidence_ids": list(self.all_evidence_ids),
            "allowed_for_automatic_execution": self.allowed_for_automatic_execution,
            "artifact_id": self.artifact_id,
            "blocking_gaps": list(self.blocking_gaps),
            "cognition_artifact_ids": list(self.cognition_artifact_ids),
            "evidence_bundle_ids": list(self.evidence_bundle_ids),
            "evidence_ids": list(self.evidence_ids),
            "execution_boundaries": [
                item.canonical_payload() for item in self.execution_boundaries
            ],
            "handoff_id": self.handoff_id,
            "human_authority_state": self.human_authority_state.value,
            "permits_automatic_execution": self.permits_automatic_execution,
            "produced_by_agent_role_id": self.produced_by_agent_role_id,
            "produced_by_engine_id": self.produced_by_engine_id,
            "readiness_gaps": list(self.readiness_gaps),
            "requested_blackfox_scope": self.requested_blackfox_scope,
            "requires_human_authority": self.requires_human_authority,
            "review_requirements": [
                item.canonical_payload() for item in self.review_requirements
            ],
            "review_summary": self.review_summary,
            "rollback_references": [
                item.canonical_payload() for item in self.rollback_references
            ],
            "schema_version": self.schema_version,
            "status": self.status.value,
            "subject": self.subject,
            "target_system": self.target_system,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this handoff package."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class BlackFoxHandoffBundle:
    """Deterministic bundle of BlackFox handoff packages."""

    bundle_id: str
    packages: tuple[BlackFoxHandoffPackage, ...]
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_THREE_BLACKFOX_HANDOFF_BUNDLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate handoff package uniqueness and bundle reviewability."""

        object.__setattr__(self, "bundle_id", _text(self.bundle_id, "bundle_id"))
        if not self.packages:
            raise ValueError("BlackFox handoff bundles require at least one package.")
        packages = tuple(sorted(self.packages, key=lambda item: item.handoff_id))
        _unique_values((package.handoff_id for package in packages), label="handoff_id")
        object.__setattr__(self, "packages", packages)
        object.__setattr__(
            self,
            "notes",
            _unique_text(self.notes, label="BlackFox handoff bundle note"),
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def handoff_ids(self) -> tuple[str, ...]:
        """Return handoff ids in deterministic order."""

        return tuple(package.handoff_id for package in self.packages)

    @property
    def ready_handoff_ids(self) -> tuple[str, ...]:
        """Return package ids ready for human review."""

        return tuple(
            package.handoff_id
            for package in self.packages
            if package.ready_for_human_review
        )

    @property
    def blocked_handoff_ids(self) -> tuple[str, ...]:
        """Return blocked handoff package ids."""

        return tuple(
            package.handoff_id
            for package in self.packages
            if package.status is BlackFoxHandoffStatus.BLOCKED
        )

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return bundle-level and package-level gaps."""

        gaps: list[str] = []
        for package in self.packages:
            gaps.extend(package.readiness_gaps)
            gaps.extend(package.blocking_gaps)
        return tuple(gaps)

    @property
    def is_complete_for_human_review(self) -> bool:
        """Return whether every BlackFox handoff is review-ready."""

        return not self.readiness_gaps and len(self.ready_handoff_ids) == len(
            self.packages
        )

    def handoff_by_id(self, handoff_id: str) -> BlackFoxHandoffPackage:
        """Return one BlackFox handoff package by id."""

        normalized = _text(handoff_id, "handoff_id")
        for package in self.packages:
            if package.handoff_id == normalized:
                return package
        raise ValueError(f"Unknown BlackFox handoff_id: {handoff_id}")

    def to_artifact_bundle(self, *, artifact_bundle_id: str) -> WaveThreeArtifactBundle:
        """Convert BlackFox handoffs into a shared artifact bundle."""

        artifacts = tuple(package.to_artifact_ref() for package in self.packages)
        return WaveThreeArtifactBundle(
            bundle_id=artifact_bundle_id,
            artifacts=artifacts,
            evidence_links=tuple(
                WaveThreeEvidenceLink(
                    evidence_id=evidence_id,
                    artifact_id=artifact.artifact_id,
                    relation=WaveThreeEvidenceRelation.REVIEWS,
                    summary=(
                        "BlackFox handoff bundle evidence preserves policy, "
                        "review, rollback, and no-execution boundaries."
                    ),
                    source_system=WaveThreeSourceSystem.IX_BLACKFOX,
                )
                for artifact in artifacts
                for evidence_id in artifact.evidence_ids
            ),
            required_kinds=(WaveThreeArtifactKind.BLACKFOX_HANDOFF,),
            notes=("BlackFox handoff bundles remain review-only artifacts.",),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "bundle_id": self.bundle_id,
            "notes": list(self.notes),
            "packages": [package.canonical_payload() for package in self.packages],
            "readiness_gaps": list(self.readiness_gaps),
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this bundle."""

        return _stable_sha256(self.canonical_payload())


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


def _unique_enum(values: Iterable[E], *, label: str) -> tuple[E, ...]:
    """Normalize enum tuples while rejecting duplicates."""

    normalized = tuple(values)
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


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
