"""Wave 4 controlled proto-candidate trial bundle records.

Wave 4 is earned only when the separate evidence layers can be assembled into a
single controlled proto-candidate trial bundle: cross-domain transfer, bounded
repair after failure, uncertainty preservation, long-horizon mission state, safe
refusal, reward-audit discipline, adversarial robustness, and replayable audit
trail evidence. This module performs that integration without creating automatic
execution authority, AGI claims, or independent-validation claims.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.wave4_contracts import (
    WAVE_FOUR_REQUIRED_ARTIFACT_KINDS,
    WAVE_FOUR_REQUIRED_CAPABILITY_AREAS,
    WaveFourArtifactBundle,
    WaveFourArtifactDecision,
    WaveFourArtifactKind,
    WaveFourArtifactRef,
    WaveFourAuthorityState,
    WaveFourCapabilityArea,
    WaveFourEvidenceLink,
    WaveFourEvidenceRelation,
    WaveFourSourceSystem,
)
from ix_cognition_kernel.wave4_trials import (
    REQUIRED_WAVE_FOUR_TRIAL_TASK_KINDS,
    WaveFourControlledTask,
    WaveFourTrialProtocol,
    WaveFourTrialStatus,
    WaveFourTrialTaskKind,
)

T = TypeVar("T")

WAVE_FOUR_PROTO_CANDIDATE_BUNDLE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-proto-candidate-bundle-v1"
)

REQUIRED_WAVE_FOUR_PROTO_TASK_KINDS: tuple[WaveFourTrialTaskKind, ...] = (
    *REQUIRED_WAVE_FOUR_TRIAL_TASK_KINDS,
    WaveFourTrialTaskKind.BASELINE_CAPABILITY,
)


class WaveFourProtoCandidateStatus(StrEnum):
    """Fail-closed review status for an integrated Wave 4 bundle."""

    READY_FOR_CONTROLLED_REVIEW = "ready-for-controlled-review"
    NEEDS_EVIDENCE = "needs-evidence"
    NEEDS_REPAIR = "needs-repair"
    BLOCKED = "blocked"


class WaveFourProtoCandidateOutcome(StrEnum):
    """Measured outcome for a controlled Wave 4 proto-candidate bundle."""

    PROTO_CANDIDATE_REVIEW_READY = "proto-candidate-review-ready"
    PROTO_CANDIDATE_NEEDS_EVIDENCE = "proto-candidate-needs-evidence"
    PROTO_CANDIDATE_NEEDS_REPAIR = "proto-candidate-needs-repair"
    PROTO_CANDIDATE_BLOCKED = "proto-candidate-blocked"


@dataclass(frozen=True, slots=True)
class WaveFourProtoCandidateTrialBundle:
    """Integrated Wave 4 trial and artifact evidence bundle."""

    bundle_id: str
    trial_protocol: WaveFourTrialProtocol
    artifact_bundles: tuple[WaveFourArtifactBundle, ...]
    scenario_ids: tuple[str, ...]
    blackfox_receipt_ids: tuple[str, ...]
    review_owner_role_id: str = "proto-candidate-review-owner"
    generated_by_engine_id: str = "wave4-proto-candidate-bundle-engine"
    notes: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    required_task_kinds: tuple[WaveFourTrialTaskKind, ...] = (
        REQUIRED_WAVE_FOUR_PROTO_TASK_KINDS
    )
    required_artifact_kinds: tuple[WaveFourArtifactKind, ...] = (
        WAVE_FOUR_REQUIRED_ARTIFACT_KINDS
    )
    required_capability_areas: tuple[WaveFourCapabilityArea, ...] = (
        WAVE_FOUR_REQUIRED_CAPABILITY_AREAS
    )
    permits_automatic_execution: bool = False
    claims_agi: bool = False
    independently_validated: bool = False
    schema_version: str = WAVE_FOUR_PROTO_CANDIDATE_BUNDLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate integration coverage and anti-overclaim boundaries."""

        object.__setattr__(self, "bundle_id", _text(self.bundle_id, "bundle_id"))
        if not self.artifact_bundles:
            raise ValueError("Wave 4 proto-candidate bundles require artifacts.")
        sorted_bundles = tuple(
            sorted(self.artifact_bundles, key=lambda item: item.bundle_id)
        )
        _unique_items((bundle.bundle_id for bundle in sorted_bundles), "bundle_id")
        object.__setattr__(self, "artifact_bundles", sorted_bundles)
        object.__setattr__(
            self,
            "scenario_ids",
            _unique_text(self.scenario_ids, label="scenario_id"),
        )
        object.__setattr__(
            self,
            "blackfox_receipt_ids",
            _unique_text(self.blackfox_receipt_ids, label="blackfox receipt_id"),
        )
        object.__setattr__(
            self,
            "review_owner_role_id",
            _text(self.review_owner_role_id, "review_owner_role_id"),
        )
        object.__setattr__(
            self,
            "generated_by_engine_id",
            _text(self.generated_by_engine_id, "generated_by_engine_id"),
        )
        object.__setattr__(
            self, "notes", _unique_text(self.notes, label="proto-candidate note")
        )
        object.__setattr__(
            self,
            "blocked_reasons",
            _unique_text(self.blocked_reasons, label="blocked reason"),
        )
        object.__setattr__(
            self,
            "required_task_kinds",
            _unique_items(self.required_task_kinds, "required task kind"),
        )
        object.__setattr__(
            self,
            "required_artifact_kinds",
            _unique_items(self.required_artifact_kinds, "required artifact kind"),
        )
        object.__setattr__(
            self,
            "required_capability_areas",
            _unique_items(
                self.required_capability_areas, "required capability area"
            ),
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.permits_automatic_execution:
            raise ValueError("Wave 4 proto-candidate bundles cannot permit execution.")
        if self.claims_agi:
            raise ValueError("Wave 4 proto-candidate bundles cannot claim AGI.")
        if self.independently_validated:
            raise ValueError(
                "Wave 4 proto-candidate bundles cannot claim independent validation."
            )
        if self.blocked_reasons and self.trial_protocol.tasks:
            raise ValueError(
                "Blocked Wave 4 proto-candidate bundles cannot carry trial tasks."
            )

    @property
    def artifact_id(self) -> str:
        """Return shared Wave 4 artifact id for this integration bundle."""

        return f"wave4-proto-candidate-bundle:{self.bundle_id}"

    @property
    def controlled_tasks(self) -> tuple[WaveFourControlledTask, ...]:
        """Return controlled tasks in protocol order."""

        return self.trial_protocol.tasks

    @property
    def artifact_refs(self) -> tuple[WaveFourArtifactRef, ...]:
        """Return artifact refs across all artifact bundles."""

        artifacts = tuple(
            artifact
            for bundle in self.artifact_bundles
            for artifact in bundle.artifacts
        )
        _unique_items((artifact.artifact_id for artifact in artifacts), "artifact_id")
        return tuple(sorted(artifacts, key=lambda item: item.artifact_id))

    @property
    def evidence_links(self) -> tuple[WaveFourEvidenceLink, ...]:
        """Return evidence links across all artifact bundles."""

        links = tuple(
            link for bundle in self.artifact_bundles for link in bundle.evidence_links
        )
        _unique_items((link.link_key for link in links), "evidence link")
        return tuple(sorted(links, key=lambda item: item.link_key))

    @property
    def task_kinds_present(self) -> tuple[WaveFourTrialTaskKind, ...]:
        """Return controlled task kinds represented in the protocol."""

        return tuple(
            sorted(
                {task.task_kind for task in self.controlled_tasks},
                key=lambda item: item.value,
            )
        )

    @property
    def artifact_kinds_present(self) -> tuple[WaveFourArtifactKind, ...]:
        """Return artifact kinds represented by artifact refs."""

        return tuple(
            sorted(
                {artifact.kind for artifact in self.artifact_refs},
                key=lambda item: item.value,
            )
        )

    @property
    def capability_areas_present(self) -> tuple[WaveFourCapabilityArea, ...]:
        """Return Wave 4 capability areas represented by artifact refs."""

        return tuple(
            sorted(
                {artifact.capability_area for artifact in self.artifact_refs},
                key=lambda item: item.value,
            )
        )

    @property
    def missing_required_task_kinds(self) -> tuple[WaveFourTrialTaskKind, ...]:
        """Return required task kinds not represented by the protocol."""

        present = set(self.task_kinds_present)
        return tuple(kind for kind in self.required_task_kinds if kind not in present)

    @property
    def missing_required_artifact_kinds(self) -> tuple[WaveFourArtifactKind, ...]:
        """Return required artifact kinds not represented by artifact refs."""

        present = set(self.artifact_kinds_present)
        return tuple(
            kind for kind in self.required_artifact_kinds if kind not in present
        )

    @property
    def missing_required_capability_areas(self) -> tuple[WaveFourCapabilityArea, ...]:
        """Return required capability areas not represented by artifact refs."""

        present = set(self.capability_areas_present)
        return tuple(
            area for area in self.required_capability_areas if area not in present
        )

    @property
    def ready_task_ids(self) -> tuple[str, ...]:
        """Return controlled task ids ready for review."""

        return self.trial_protocol.ready_task_ids

    @property
    def repair_task_ids(self) -> tuple[str, ...]:
        """Return controlled task ids needing repair."""

        return self.trial_protocol.repair_task_ids

    @property
    def evidence_task_ids(self) -> tuple[str, ...]:
        """Return controlled task ids needing more evidence."""

        return self.trial_protocol.evidence_task_ids

    @property
    def blocked_task_ids(self) -> tuple[str, ...]:
        """Return controlled task ids blocked by the protocol."""

        return self.trial_protocol.blocked_task_ids

    @property
    def blocked_artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids marked blocked across artifact bundles."""

        return tuple(
            artifact_id
            for bundle in self.artifact_bundles
            for artifact_id in bundle.blocked_artifact_ids
        )

    @property
    def not_ready_artifact_ids(self) -> tuple[str, ...]:
        """Return artifact ids that are not ready for controlled review."""

        ready = {
            artifact_id
            for bundle in self.artifact_bundles
            for artifact_id in bundle.ready_for_controlled_review_artifact_ids
        }
        return tuple(
            artifact.artifact_id
            for artifact in self.artifact_refs
            if artifact.artifact_id not in ready
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted evidence ids from tasks, artifacts, and links."""

        evidence_ids: set[str] = set()
        for task in self.controlled_tasks:
            evidence_ids.update(task.all_evidence_ids)
        for artifact in self.artifact_refs:
            evidence_ids.update(artifact.evidence_ids)
        for link in self.evidence_links:
            evidence_ids.add(link.evidence_id)
        return tuple(sorted(evidence_ids))

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return fail-closed gaps preventing proto-candidate review."""

        gaps: list[str] = []
        if (
            self.trial_protocol.status
            is not WaveFourTrialStatus.READY_FOR_CONTROLLED_REVIEW
        ):
            gaps.extend(self.trial_protocol.readiness_gaps)
        if self.missing_required_task_kinds:
            missing = ", ".join(
                kind.value for kind in self.missing_required_task_kinds
            )
            gaps.append(f"missing proto-candidate task coverage: {missing}")
        if self.missing_required_artifact_kinds:
            missing = ", ".join(
                kind.value for kind in self.missing_required_artifact_kinds
            )
            gaps.append(f"missing proto-candidate artifact coverage: {missing}")
        if self.missing_required_capability_areas:
            missing = ", ".join(
                area.value for area in self.missing_required_capability_areas
            )
            gaps.append(f"missing proto-candidate capability coverage: {missing}")
        if self.not_ready_artifact_ids:
            not_ready = ", ".join(self.not_ready_artifact_ids)
            gaps.append(f"artifact refs not ready for review: {not_ready}")
        if not self.scenario_ids:
            gaps.append(f"{self.bundle_id} has no WorldTwin scenario ids")
        if not self.blackfox_receipt_ids:
            gaps.append(f"{self.bundle_id} has no BlackFox receipt ids")
        return tuple(gaps)

    @property
    def blocking_gaps(self) -> tuple[str, ...]:
        """Return hard blocks for this proto-candidate bundle."""

        gaps = [
            f"{self.bundle_id} blocked: {reason}"
            for reason in self.blocked_reasons
        ]
        gaps.extend(f"blocked task: {task_id}" for task_id in self.blocked_task_ids)
        gaps.extend(
            f"blocked artifact: {artifact_id}"
            for artifact_id in self.blocked_artifact_ids
        )
        return tuple(gaps)

    @property
    def status(self) -> WaveFourProtoCandidateStatus:
        """Return fail-closed status for the integrated bundle."""

        if self.blocking_gaps:
            return WaveFourProtoCandidateStatus.BLOCKED
        if self.repair_task_ids:
            return WaveFourProtoCandidateStatus.NEEDS_REPAIR
        if self.readiness_gaps or self.evidence_task_ids:
            return WaveFourProtoCandidateStatus.NEEDS_EVIDENCE
        return WaveFourProtoCandidateStatus.READY_FOR_CONTROLLED_REVIEW

    @property
    def outcome(self) -> WaveFourProtoCandidateOutcome:
        """Return measured outcome for the integrated bundle."""

        if self.status is WaveFourProtoCandidateStatus.BLOCKED:
            return WaveFourProtoCandidateOutcome.PROTO_CANDIDATE_BLOCKED
        if self.status is WaveFourProtoCandidateStatus.NEEDS_REPAIR:
            return WaveFourProtoCandidateOutcome.PROTO_CANDIDATE_NEEDS_REPAIR
        if self.status is WaveFourProtoCandidateStatus.NEEDS_EVIDENCE:
            return WaveFourProtoCandidateOutcome.PROTO_CANDIDATE_NEEDS_EVIDENCE
        return WaveFourProtoCandidateOutcome.PROTO_CANDIDATE_REVIEW_READY

    @property
    def ready_for_controlled_review(self) -> bool:
        """Return whether this integrated bundle may enter human review."""

        return self.status is WaveFourProtoCandidateStatus.READY_FOR_CONTROLLED_REVIEW

    @property
    def human_authority_state(self) -> WaveFourAuthorityState:
        """Return human-authority state for the integrated bundle."""

        if self.status is WaveFourProtoCandidateStatus.BLOCKED:
            return WaveFourAuthorityState.BLOCKED
        return WaveFourAuthorityState.HUMAN_REVIEW_REQUIRED

    @property
    def review_summary(self) -> str:
        """Return concise proto-candidate bundle summary."""

        return (
            f"{self.bundle_id}: {len(self.controlled_tasks)} controlled tasks; "
            f"{len(self.artifact_refs)} artifacts; {self.status.value}; "
            "human review required; no AGI claim."
        )

    def to_artifact_ref(self) -> WaveFourArtifactRef:
        """Convert this integration bundle into a shared Wave 4 artifact ref."""

        if self.status is WaveFourProtoCandidateStatus.READY_FOR_CONTROLLED_REVIEW:
            decision = WaveFourArtifactDecision.READY_FOR_CONTROLLED_REVIEW
        elif self.status is WaveFourProtoCandidateStatus.BLOCKED:
            decision = WaveFourArtifactDecision.BLOCKED
        else:
            decision = WaveFourArtifactDecision.NEEDS_EVIDENCE
        return WaveFourArtifactRef(
            artifact_id=self.artifact_id,
            kind=WaveFourArtifactKind.CONTROLLED_TRIAL,
            capability_area=WaveFourCapabilityArea.AUDIT_TRAIL,
            source_system=WaveFourSourceSystem.IX_COGNITION_KERNEL,
            summary=self.review_summary,
            produced_by_engine_id=self.generated_by_engine_id,
            produced_by_agent_role_id=self.review_owner_role_id,
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=self.human_authority_state,
        )

    def evidence_links_for_bundle_ref(self) -> tuple[WaveFourEvidenceLink, ...]:
        """Return evidence links for the integration artifact ref."""

        relation = WaveFourEvidenceRelation.TESTS
        if self.status is WaveFourProtoCandidateStatus.BLOCKED:
            relation = WaveFourEvidenceRelation.BLOCKS
        return tuple(
            WaveFourEvidenceLink(
                evidence_id=evidence_id,
                artifact_id=self.artifact_id,
                relation=relation,
                summary=f"Evidence for Wave 4 proto-candidate bundle {self.bundle_id}.",
                source_system=WaveFourSourceSystem.LOCAL_TEST_SUITE,
            )
            for evidence_id in self.all_evidence_ids
        )

    def to_artifact_bundle(self) -> WaveFourArtifactBundle:
        """Convert this integration bundle into a shared Wave 4 artifact bundle."""

        return WaveFourArtifactBundle(
            bundle_id=f"wave4-proto-candidate-artifacts:{self.bundle_id}",
            artifacts=(*self.artifact_refs, self.to_artifact_ref()),
            evidence_links=(
                *self.evidence_links,
                *self.evidence_links_for_bundle_ref(),
            ),
            required_kinds=self.required_artifact_kinds,
            required_capability_areas=self.required_capability_areas,
            notes=(self.review_summary, *self.notes),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic proto-candidate bundle payload."""

        return {
            "all_evidence_ids": list(self.all_evidence_ids),
            "artifact_bundles": [
                bundle.canonical_payload() for bundle in self.artifact_bundles
            ],
            "artifact_id": self.artifact_id,
            "artifact_ids": [artifact.artifact_id for artifact in self.artifact_refs],
            "artifact_kinds_present": [
                kind.value for kind in self.artifact_kinds_present
            ],
            "blackfox_receipt_ids": list(self.blackfox_receipt_ids),
            "blocking_gaps": list(self.blocking_gaps),
            "blocked_reasons": list(self.blocked_reasons),
            "bundle_id": self.bundle_id,
            "capability_areas_present": [
                area.value for area in self.capability_areas_present
            ],
            "claims_agi": self.claims_agi,
            "controlled_task_ids": list(self.trial_protocol.task_ids),
            "generated_by_engine_id": self.generated_by_engine_id,
            "human_authority_state": self.human_authority_state.value,
            "independently_validated": self.independently_validated,
            "missing_required_artifact_kinds": [
                kind.value for kind in self.missing_required_artifact_kinds
            ],
            "missing_required_capability_areas": [
                area.value for area in self.missing_required_capability_areas
            ],
            "missing_required_task_kinds": [
                kind.value for kind in self.missing_required_task_kinds
            ],
            "not_ready_artifact_ids": list(self.not_ready_artifact_ids),
            "notes": list(self.notes),
            "outcome": self.outcome.value,
            "permits_automatic_execution": self.permits_automatic_execution,
            "readiness_gaps": list(self.readiness_gaps),
            "required_artifact_kinds": [
                kind.value for kind in self.required_artifact_kinds
            ],
            "required_capability_areas": [
                area.value for area in self.required_capability_areas
            ],
            "required_task_kinds": [kind.value for kind in self.required_task_kinds],
            "review_owner_role_id": self.review_owner_role_id,
            "review_summary": self.review_summary,
            "scenario_ids": list(self.scenario_ids),
            "schema_version": self.schema_version,
            "status": self.status.value,
            "task_kinds_present": [kind.value for kind in self.task_kinds_present],
            "trial_protocol": self.trial_protocol.canonical_payload(),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint."""

        return _stable_sha256(self.canonical_payload())


def _text(value: str, label: str) -> str:
    """Return stripped text or raise when empty."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _unique_text(values: Iterable[str], *, label: str) -> tuple[str, ...]:
    """Normalize text values while rejecting blanks and duplicates."""

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        stripped = _text(value, label)
        if stripped in seen:
            raise ValueError(f"Duplicate {label} detected: {stripped}")
        normalized.append(stripped)
        seen.add(stripped)
    return tuple(normalized)


def _unique_items(values: Iterable[T], label: str) -> tuple[T, ...]:
    """Return tuple of unique items while rejecting duplicates."""

    normalized: list[T] = []
    seen: set[T] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value}")
        normalized.append(value)
        seen.add(value)
    return tuple(normalized)


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    """Return deterministic SHA-256 over a canonical JSON payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()
