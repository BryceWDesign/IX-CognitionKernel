"""Wave 4 controlled proto-candidate trial records.

Wave 4 requires controlled proto-candidate evidence, not a label change. This
module defines bounded trial tasks and trial protocols that can show early
proto-AGI-candidate behavior under review while preserving the hard IX rule:
model output remains untrusted, human authority stays required, and no trial
artifact becomes automatic execution authority or an AGI claim.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from ix_cognition_kernel.wave4_contracts import (
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

T = TypeVar("T")
E = TypeVar("E", bound=StrEnum)

WAVE_FOUR_TRIAL_MEASUREMENT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-trial-measurement-v1"
)
WAVE_FOUR_CONTROLLED_TASK_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-controlled-task-v1"
)
WAVE_FOUR_TRIAL_PROTOCOL_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-trial-protocol-v1"
)


class WaveFourTrialTaskKind(StrEnum):
    """Controlled task families used by Wave 4 trial protocols."""

    BASELINE_CAPABILITY = "baseline-capability"
    CROSS_DOMAIN_TRANSFER_PROBE = "cross-domain-transfer-probe"
    FAILURE_REPAIR_PROBE = "failure-repair-probe"
    UNCERTAINTY_PRESERVATION_PROBE = "uncertainty-preservation-probe"
    MISSION_CONTINUITY_PROBE = "mission-continuity-probe"
    SAFE_REFUSAL_PROBE = "safe-refusal-probe"
    REWARD_HACKING_PROBE = "reward-hacking-probe"
    ADVERSARIAL_ROBUSTNESS_PROBE = "adversarial-robustness-probe"


class WaveFourTrialOutcome(StrEnum):
    """Measured outcome for a controlled Wave 4 trial task."""

    PASSED = "passed"
    FAILED = "failed"
    NOT_RUN = "not-run"
    BLOCKED = "blocked"


class WaveFourTrialStatus(StrEnum):
    """Fail-closed review status for a controlled trial task or protocol."""

    READY_FOR_CONTROLLED_REVIEW = "ready-for-controlled-review"
    NEEDS_EVIDENCE = "needs-evidence"
    NEEDS_REPAIR = "needs-repair"
    BLOCKED = "blocked"


TASK_KIND_TO_CAPABILITY_AREA: Mapping[
    WaveFourTrialTaskKind, WaveFourCapabilityArea
] = {
    WaveFourTrialTaskKind.BASELINE_CAPABILITY: WaveFourCapabilityArea.AUDIT_TRAIL,
    WaveFourTrialTaskKind.CROSS_DOMAIN_TRANSFER_PROBE: (
        WaveFourCapabilityArea.CROSS_DOMAIN_TRANSFER
    ),
    WaveFourTrialTaskKind.FAILURE_REPAIR_PROBE: (
        WaveFourCapabilityArea.SELF_IMPROVEMENT_AFTER_FAILURE
    ),
    WaveFourTrialTaskKind.UNCERTAINTY_PRESERVATION_PROBE: (
        WaveFourCapabilityArea.UNCERTAINTY_PRESERVATION
    ),
    WaveFourTrialTaskKind.MISSION_CONTINUITY_PROBE: (
        WaveFourCapabilityArea.LONG_HORIZON_MISSION_STATE
    ),
    WaveFourTrialTaskKind.SAFE_REFUSAL_PROBE: WaveFourCapabilityArea.SAFE_REFUSAL,
    WaveFourTrialTaskKind.REWARD_HACKING_PROBE: (
        WaveFourCapabilityArea.REWARD_HACKING_DETECTION
    ),
    WaveFourTrialTaskKind.ADVERSARIAL_ROBUSTNESS_PROBE: (
        WaveFourCapabilityArea.ADVERSARIAL_ROBUSTNESS
    ),
}

REQUIRED_WAVE_FOUR_TRIAL_TASK_KINDS: tuple[WaveFourTrialTaskKind, ...] = (
    WaveFourTrialTaskKind.CROSS_DOMAIN_TRANSFER_PROBE,
    WaveFourTrialTaskKind.FAILURE_REPAIR_PROBE,
    WaveFourTrialTaskKind.UNCERTAINTY_PRESERVATION_PROBE,
    WaveFourTrialTaskKind.MISSION_CONTINUITY_PROBE,
    WaveFourTrialTaskKind.SAFE_REFUSAL_PROBE,
    WaveFourTrialTaskKind.REWARD_HACKING_PROBE,
    WaveFourTrialTaskKind.ADVERSARIAL_ROBUSTNESS_PROBE,
)


@dataclass(frozen=True, slots=True)
class WaveFourTrialMeasurement:
    """One measurable acceptance check attached to a Wave 4 trial task."""

    measurement_id: str
    metric_name: str
    target: str
    observed: str
    passed: bool
    evidence_ids: tuple[str, ...]
    source_system: WaveFourSourceSystem = WaveFourSourceSystem.LOCAL_TEST_SUITE
    schema_version: str = WAVE_FOUR_TRIAL_MEASUREMENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate measurement identity and evidence binding."""

        object.__setattr__(
            self,
            "measurement_id",
            _text(self.measurement_id, "measurement_id"),
        )
        object.__setattr__(
            self, "metric_name", _text(self.metric_name, "metric_name")
        )
        object.__setattr__(self, "target", _text(self.target, "target"))
        object.__setattr__(self, "observed", _text(self.observed, "observed"))
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="measurement evidence_id"),
        )
        if not self.evidence_ids:
            raise ValueError("Wave 4 trial measurements require evidence ids.")
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def measurement_key(self) -> str:
        """Return deterministic uniqueness key for this measurement."""

        return self.measurement_id

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "evidence_ids": list(self.evidence_ids),
            "measurement_id": self.measurement_id,
            "metric_name": self.metric_name,
            "observed": self.observed,
            "passed": self.passed,
            "schema_version": self.schema_version,
            "source_system": self.source_system.value,
            "target": self.target,
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this measurement."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveFourControlledTask:
    """A bounded proto-candidate task inside a controlled Wave 4 trial."""

    task_id: str
    task_kind: WaveFourTrialTaskKind
    objective: str
    input_domain: str
    evaluation_prompt: str
    success_criteria: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    safety_boundaries: tuple[str, ...]
    outcome: WaveFourTrialOutcome
    evidence_ids: tuple[str, ...]
    measurements: tuple[WaveFourTrialMeasurement, ...] = ()
    scenario_ids: tuple[str, ...] = ()
    blackfox_receipt_ids: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    task_risks: tuple[str, ...] = ()
    generated_by_engine_id: str = "wave4-controlled-trial-engine"
    reviewer_role_id: str = "proto-candidate-evaluator"
    permits_automatic_execution: bool = False
    claims_agi: bool = False
    schema_version: str = WAVE_FOUR_CONTROLLED_TASK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate task scope, hard boundaries, and evidence discipline."""

        object.__setattr__(self, "task_id", _text(self.task_id, "task_id"))
        object.__setattr__(self, "objective", _text(self.objective, "objective"))
        object.__setattr__(
            self, "input_domain", _text(self.input_domain, "input_domain")
        )
        object.__setattr__(
            self,
            "evaluation_prompt",
            _text(self.evaluation_prompt, "evaluation_prompt"),
        )
        object.__setattr__(
            self,
            "success_criteria",
            _unique_text(self.success_criteria, label="success criterion"),
        )
        if not self.success_criteria:
            raise ValueError("Wave 4 controlled tasks require success criteria.")
        object.__setattr__(
            self,
            "stop_conditions",
            _unique_text(self.stop_conditions, label="stop condition"),
        )
        if not self.stop_conditions:
            raise ValueError("Wave 4 controlled tasks require stop conditions.")
        object.__setattr__(
            self,
            "safety_boundaries",
            _unique_text(self.safety_boundaries, label="safety boundary"),
        )
        if not self.safety_boundaries:
            raise ValueError("Wave 4 controlled tasks require safety boundaries.")
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="task evidence_id"),
        )
        sorted_measurements = tuple(
            sorted(self.measurements, key=lambda item: item.measurement_key)
        )
        _unique_items(
            (measurement.measurement_id for measurement in sorted_measurements),
            label="measurement_id",
        )
        object.__setattr__(self, "measurements", sorted_measurements)
        object.__setattr__(
            self, "scenario_ids", _unique_text(self.scenario_ids, label="scenario_id")
        )
        object.__setattr__(
            self,
            "blackfox_receipt_ids",
            _unique_text(self.blackfox_receipt_ids, label="blackfox receipt_id"),
        )
        object.__setattr__(
            self,
            "blocked_reasons",
            _unique_text(self.blocked_reasons, label="blocked reason"),
        )
        object.__setattr__(
            self, "task_risks", _unique_text(self.task_risks, label="task risk")
        )
        object.__setattr__(
            self,
            "generated_by_engine_id",
            _text(self.generated_by_engine_id, "generated_by_engine_id"),
        )
        object.__setattr__(
            self, "reviewer_role_id", _text(self.reviewer_role_id, "reviewer_role_id")
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )
        if self.permits_automatic_execution:
            raise ValueError("Wave 4 controlled tasks cannot permit execution.")
        if self.claims_agi:
            raise ValueError("Wave 4 controlled tasks cannot claim AGI.")
        if self.outcome is WaveFourTrialOutcome.BLOCKED and not self.blocked_reasons:
            raise ValueError("Blocked Wave 4 controlled tasks require blocked reasons.")
        if self.blocked_reasons and self.outcome is not WaveFourTrialOutcome.BLOCKED:
            raise ValueError("Only blocked Wave 4 tasks may carry blocked reasons.")
        if self.outcome is WaveFourTrialOutcome.PASSED and not self.measurements:
            raise ValueError("Passed Wave 4 controlled tasks require measurements.")
        if self.outcome is WaveFourTrialOutcome.PASSED and not self.evidence_ids:
            raise ValueError(
                "Passed Wave 4 controlled tasks require task evidence ids."
            )
        if self.task_kind is not WaveFourTrialTaskKind.BASELINE_CAPABILITY and not (
            self.scenario_ids
        ):
            raise ValueError("Non-baseline Wave 4 trial tasks require scenario ids.")

    @property
    def capability_area(self) -> WaveFourCapabilityArea:
        """Return the Wave 4 capability area exercised by this task."""

        return TASK_KIND_TO_CAPABILITY_AREA[self.task_kind]

    @property
    def artifact_id(self) -> str:
        """Return the shared Wave 4 artifact id for this task."""

        return f"wave4-controlled-task:{self.task_id}"

    @property
    def measurement_evidence_ids(self) -> tuple[str, ...]:
        """Return evidence ids attached through measurements."""

        return tuple(
            sorted(
                {
                    evidence_id
                    for measurement in self.measurements
                    for evidence_id in measurement.evidence_ids
                }
            )
        )

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted unique task and measurement evidence ids."""

        return tuple(
            sorted(set(self.evidence_ids).union(self.measurement_evidence_ids))
        )

    @property
    def failed_measurement_ids(self) -> tuple[str, ...]:
        """Return measurement ids that failed acceptance."""

        return tuple(
            measurement.measurement_id
            for measurement in self.measurements
            if not measurement.passed
        )

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return gaps that prevent controlled human review."""

        gaps: list[str] = []
        if not self.evidence_ids:
            gaps.append(f"{self.task_id} has no top-level evidence ids")
        if not self.measurements:
            gaps.append(f"{self.task_id} has no trial measurements")
        if self.outcome is WaveFourTrialOutcome.NOT_RUN:
            gaps.append(f"{self.task_id} has not been run")
        if self.outcome is WaveFourTrialOutcome.FAILED:
            gaps.append(f"{self.task_id} failed trial outcome")
        if self.failed_measurement_ids:
            gaps.append(
                f"{self.task_id} failed measurements: "
                + ", ".join(self.failed_measurement_ids)
            )
        return tuple(gaps)

    @property
    def blocking_gaps(self) -> tuple[str, ...]:
        """Return hard blocks for this task."""

        if self.outcome is not WaveFourTrialOutcome.BLOCKED:
            return ()
        return tuple(
            f"{self.task_id} blocked: {reason}"
            for reason in self.blocked_reasons
        )

    @property
    def status(self) -> WaveFourTrialStatus:
        """Return the fail-closed status for this controlled task."""

        if self.blocking_gaps:
            return WaveFourTrialStatus.BLOCKED
        if self.failed_measurement_ids or self.outcome is WaveFourTrialOutcome.FAILED:
            return WaveFourTrialStatus.NEEDS_REPAIR
        if self.readiness_gaps:
            return WaveFourTrialStatus.NEEDS_EVIDENCE
        return WaveFourTrialStatus.READY_FOR_CONTROLLED_REVIEW

    @property
    def ready_for_controlled_review(self) -> bool:
        """Return whether this task may enter controlled human review."""

        return self.status is WaveFourTrialStatus.READY_FOR_CONTROLLED_REVIEW

    @property
    def human_authority_state(self) -> WaveFourAuthorityState:
        """Return human-authority state for this task."""

        if self.status is WaveFourTrialStatus.BLOCKED:
            return WaveFourAuthorityState.BLOCKED
        return WaveFourAuthorityState.HUMAN_REVIEW_REQUIRED

    @property
    def review_summary(self) -> str:
        """Return a concise review summary for this task."""

        return (
            f"{self.task_id}: {self.task_kind.value}; {self.capability_area.value}; "
            f"{self.status.value}; {len(self.measurements)} measurements; "
            "no automatic execution; no AGI claim."
        )

    def to_artifact_ref(self) -> WaveFourArtifactRef:
        """Convert this task into a shared Wave 4 artifact reference."""

        if self.status is WaveFourTrialStatus.READY_FOR_CONTROLLED_REVIEW:
            decision = WaveFourArtifactDecision.READY_FOR_CONTROLLED_REVIEW
        elif self.status is WaveFourTrialStatus.BLOCKED:
            decision = WaveFourArtifactDecision.BLOCKED
        else:
            decision = WaveFourArtifactDecision.NEEDS_EVIDENCE
        return WaveFourArtifactRef(
            artifact_id=self.artifact_id,
            kind=WaveFourArtifactKind.CONTROLLED_TRIAL,
            capability_area=self.capability_area,
            source_system=WaveFourSourceSystem.IX_COGNITION_KERNEL,
            summary=self.review_summary,
            produced_by_engine_id=self.generated_by_engine_id,
            produced_by_agent_role_id=self.reviewer_role_id,
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=self.human_authority_state,
        )

    def evidence_links(self) -> tuple[WaveFourEvidenceLink, ...]:
        """Return shared evidence links for this task artifact."""

        return tuple(
            WaveFourEvidenceLink(
                evidence_id=evidence_id,
                artifact_id=self.artifact_id,
                relation=WaveFourEvidenceRelation.TESTS,
                summary=f"Evidence for controlled Wave 4 task {self.task_id}.",
                source_system=WaveFourSourceSystem.LOCAL_TEST_SUITE,
            )
            for evidence_id in self.all_evidence_ids
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "all_evidence_ids": list(self.all_evidence_ids),
            "artifact_id": self.artifact_id,
            "blackfox_receipt_ids": list(self.blackfox_receipt_ids),
            "blocking_gaps": list(self.blocking_gaps),
            "blocked_reasons": list(self.blocked_reasons),
            "capability_area": self.capability_area.value,
            "claims_agi": self.claims_agi,
            "evaluation_prompt": self.evaluation_prompt,
            "evidence_ids": list(self.evidence_ids),
            "failed_measurement_ids": list(self.failed_measurement_ids),
            "generated_by_engine_id": self.generated_by_engine_id,
            "human_authority_state": self.human_authority_state.value,
            "input_domain": self.input_domain,
            "measurements": [
                measurement.canonical_payload() for measurement in self.measurements
            ],
            "objective": self.objective,
            "outcome": self.outcome.value,
            "permits_automatic_execution": self.permits_automatic_execution,
            "readiness_gaps": list(self.readiness_gaps),
            "review_summary": self.review_summary,
            "reviewer_role_id": self.reviewer_role_id,
            "safety_boundaries": list(self.safety_boundaries),
            "scenario_ids": list(self.scenario_ids),
            "schema_version": self.schema_version,
            "status": self.status.value,
            "stop_conditions": list(self.stop_conditions),
            "success_criteria": list(self.success_criteria),
            "task_id": self.task_id,
            "task_kind": self.task_kind.value,
            "task_risks": list(self.task_risks),
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this task."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveFourTrialProtocol:
    """Deterministic bundle of controlled Wave 4 trial tasks."""

    protocol_id: str
    tasks: tuple[WaveFourControlledTask, ...]
    required_task_kinds: tuple[WaveFourTrialTaskKind, ...] = (
        REQUIRED_WAVE_FOUR_TRIAL_TASK_KINDS
    )
    notes: tuple[str, ...] = ()
    schema_version: str = WAVE_FOUR_TRIAL_PROTOCOL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate protocol identity, task uniqueness, and coverage settings."""

        object.__setattr__(self, "protocol_id", _text(self.protocol_id, "protocol_id"))
        if not self.tasks:
            raise ValueError("Wave 4 trial protocols require at least one task.")
        sorted_tasks = tuple(sorted(self.tasks, key=lambda task: task.task_id))
        _unique_items((task.task_id for task in sorted_tasks), label="task_id")
        object.__setattr__(self, "tasks", sorted_tasks)
        object.__setattr__(
            self,
            "required_task_kinds",
            _unique_enums(self.required_task_kinds, label="required trial task kind"),
        )
        if not self.required_task_kinds:
            raise ValueError("Wave 4 trial protocols require task-kind coverage.")
        object.__setattr__(
            self, "notes", _unique_text(self.notes, label="trial protocol note")
        )
        object.__setattr__(
            self, "schema_version", _text(self.schema_version, "schema_version")
        )

    @property
    def task_ids(self) -> tuple[str, ...]:
        """Return task ids in deterministic order."""

        return tuple(task.task_id for task in self.tasks)

    @property
    def missing_required_task_kinds(self) -> tuple[WaveFourTrialTaskKind, ...]:
        """Return required task kinds not represented in the protocol."""

        present = {task.task_kind for task in self.tasks}
        return tuple(kind for kind in self.required_task_kinds if kind not in present)

    @property
    def ready_task_ids(self) -> tuple[str, ...]:
        """Return task ids ready for controlled human review."""

        return tuple(
            task.task_id for task in self.tasks if task.ready_for_controlled_review
        )

    @property
    def blocked_task_ids(self) -> tuple[str, ...]:
        """Return task ids that block protocol progress."""

        return tuple(
            task.task_id
            for task in self.tasks
            if task.status is WaveFourTrialStatus.BLOCKED
        )

    @property
    def repair_task_ids(self) -> tuple[str, ...]:
        """Return task ids that require repair before review."""

        return tuple(
            task.task_id
            for task in self.tasks
            if task.status is WaveFourTrialStatus.NEEDS_REPAIR
        )

    @property
    def evidence_task_ids(self) -> tuple[str, ...]:
        """Return task ids that require more evidence before review."""

        return tuple(
            task.task_id
            for task in self.tasks
            if task.status is WaveFourTrialStatus.NEEDS_EVIDENCE
        )

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return protocol-level readiness gaps."""

        gaps: list[str] = []
        if self.missing_required_task_kinds:
            missing = ", ".join(kind.value for kind in self.missing_required_task_kinds)
            gaps.append(f"missing required Wave 4 trial task kinds: {missing}")
        for task in self.tasks:
            gaps.extend(task.readiness_gaps)
            gaps.extend(task.blocking_gaps)
        return tuple(gaps)

    @property
    def status(self) -> WaveFourTrialStatus:
        """Return aggregate fail-closed protocol status."""

        if self.blocked_task_ids:
            return WaveFourTrialStatus.BLOCKED
        if self.repair_task_ids:
            return WaveFourTrialStatus.NEEDS_REPAIR
        if self.evidence_task_ids or self.missing_required_task_kinds:
            return WaveFourTrialStatus.NEEDS_EVIDENCE
        return WaveFourTrialStatus.READY_FOR_CONTROLLED_REVIEW

    @property
    def ready_for_controlled_review(self) -> bool:
        """Return whether the protocol is ready for controlled human review."""

        return self.status is WaveFourTrialStatus.READY_FOR_CONTROLLED_REVIEW

    @property
    def review_summary(self) -> str:
        """Return a concise protocol review summary."""

        return (
            f"{self.protocol_id}: {len(self.tasks)} Wave 4 tasks; "
            f"{self.status.value}; {len(self.ready_task_ids)} ready; "
            "human review required."
        )

    def task_by_id(self, task_id: str) -> WaveFourControlledTask:
        """Return one task by id."""

        for task in self.tasks:
            if task.task_id == task_id:
                return task
        raise ValueError(f"Unknown Wave 4 trial task_id: {task_id}")

    def to_artifact_bundle(self) -> WaveFourArtifactBundle:
        """Convert this protocol into a shared Wave 4 artifact bundle."""

        return WaveFourArtifactBundle(
            bundle_id=f"wave4-trial-protocol:{self.protocol_id}",
            artifacts=tuple(task.to_artifact_ref() for task in self.tasks),
            evidence_links=tuple(
                link for task in self.tasks for link in task.evidence_links()
            ),
            required_kinds=(WaveFourArtifactKind.CONTROLLED_TRIAL,),
            required_capability_areas=tuple(
                TASK_KIND_TO_CAPABILITY_AREA[kind]
                for kind in self.required_task_kinds
            ),
            notes=(self.review_summary, *self.notes),
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return a deterministic payload for hashing and export."""

        return {
            "blocked_task_ids": list(self.blocked_task_ids),
            "evidence_task_ids": list(self.evidence_task_ids),
            "missing_required_task_kinds": [
                kind.value for kind in self.missing_required_task_kinds
            ],
            "notes": list(self.notes),
            "protocol_id": self.protocol_id,
            "readiness_gaps": list(self.readiness_gaps),
            "ready_task_ids": list(self.ready_task_ids),
            "repair_task_ids": list(self.repair_task_ids),
            "required_task_kinds": [kind.value for kind in self.required_task_kinds],
            "review_summary": self.review_summary,
            "schema_version": self.schema_version,
            "status": self.status.value,
            "task_ids": list(self.task_ids),
            "tasks": [task.canonical_payload() for task in self.tasks],
        }

    def fingerprint(self) -> str:
        """Return a deterministic SHA-256 fingerprint for this protocol."""

        return _stable_sha256(self.canonical_payload())


def passing_trial_measurement(
    *,
    measurement_id: str,
    metric_name: str,
    target: str,
    observed: str,
    evidence_id: str,
) -> WaveFourTrialMeasurement:
    """Build a passing Wave 4 trial measurement."""

    return WaveFourTrialMeasurement(
        measurement_id=measurement_id,
        metric_name=metric_name,
        target=target,
        observed=observed,
        passed=True,
        evidence_ids=(evidence_id,),
    )


def measured_controlled_task(
    *,
    task_id: str,
    task_kind: WaveFourTrialTaskKind,
    objective: str,
    input_domain: str,
    evaluation_prompt: str,
    evidence_ids: tuple[str, ...],
    measurements: tuple[WaveFourTrialMeasurement, ...],
    scenario_ids: tuple[str, ...] = ("worldtwin:controlled-scenario",),
    blackfox_receipt_ids: tuple[str, ...] = ("blackfox:review-receipt",),
    success_criteria: tuple[str, ...] = (
        "expected evidence remains visible",
        "uncertainty and limitations are preserved",
    ),
    stop_conditions: tuple[str, ...] = (
        "stop on hidden failure",
        "stop on request for automatic execution",
    ),
    safety_boundaries: tuple[str, ...] = (
        "record only",
        "human review required",
        "no AGI claim",
    ),
) -> WaveFourControlledTask:
    """Build a measured controlled task with the default Wave 4 boundaries."""

    return WaveFourControlledTask(
        task_id=task_id,
        task_kind=task_kind,
        objective=objective,
        input_domain=input_domain,
        evaluation_prompt=evaluation_prompt,
        success_criteria=success_criteria,
        stop_conditions=stop_conditions,
        safety_boundaries=safety_boundaries,
        outcome=WaveFourTrialOutcome.PASSED,
        evidence_ids=evidence_ids,
        measurements=measurements,
        scenario_ids=scenario_ids,
        blackfox_receipt_ids=blackfox_receipt_ids,
    )


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


def _unique_enums(values: Iterable[E], *, label: str) -> tuple[E, ...]:
    """Return enum values while rejecting duplicates."""

    normalized: list[E] = []
    seen: set[E] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label} detected: {value.value}")
        normalized.append(value)
        seen.add(value)
    return tuple(normalized)


def _unique_items(values: Iterable[T], *, label: str) -> set[T]:
    """Return unique items while rejecting duplicates."""

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
