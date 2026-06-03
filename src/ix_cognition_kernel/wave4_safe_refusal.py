"""Wave 4 safe-refusal records.

Wave 4 proto-candidate review must demonstrate that the system can preserve
uncertainty, detect unsafe or overclaiming requests, refuse bounded tasks when
needed, and return the refusal to human review instead of silently executing.
This module models those safe-refusal records as evidence-bound artifacts.
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
from ix_cognition_kernel.wave4_trials import (
    WaveFourControlledTask,
    WaveFourTrialMeasurement,
    WaveFourTrialOutcome,
    WaveFourTrialTaskKind,
)

T = TypeVar("T")

WAVE_FOUR_REFUSAL_TRIGGER_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-refusal-trigger-v1"
)
WAVE_FOUR_REFUSAL_ACTION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-refusal-action-v1"
)
WAVE_FOUR_SAFE_REFUSAL_RECORD_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave4-safe-refusal-record-v1"
)


class WaveFourRefusalTriggerKind(StrEnum):
    """Reasons a Wave 4 controlled task must be refused."""

    UNSAFE_TO_ACT = "unsafe-to-act"
    MISSING_EVIDENCE = "missing-evidence"
    CONTRADICTED_EVIDENCE = "contradicted-evidence"
    OVERCLAIM_REQUEST = "overclaim-request"
    AUTOMATIC_EXECUTION_REQUEST = "automatic-execution-request"
    POLICY_BOUNDARY = "policy-boundary"
    HUMAN_AUTHORITY_REQUIRED = "human-authority-required"


class WaveFourRefusalActionKind(StrEnum):
    """Actions taken by a safe-refusal record."""

    REFUSE_TASK = "refuse-task"
    PRESERVE_UNCERTAINTY = "preserve-uncertainty"
    ESCALATE_TO_HUMAN_REVIEW = "escalate-to-human-review"
    REQUEST_EVIDENCE = "request-evidence"
    BLOCK_EXECUTION = "block-execution"
    RECORD_AUDIT_TRAIL = "record-audit-trail"


class WaveFourSafeRefusalStatus(StrEnum):
    """Review status for a Wave 4 safe-refusal record."""

    READY_FOR_CONTROLLED_REVIEW = "ready-for-controlled-review"
    NEEDS_EVIDENCE = "needs-evidence"
    NEEDS_REPAIR = "needs-repair"
    BLOCKED = "blocked"


class WaveFourRefusalDecision(StrEnum):
    """Decision made by a Wave 4 safe-refusal record."""

    REFUSE_AND_ESCALATE = "refuse-and-escalate"
    HOLD_FOR_EVIDENCE = "hold-for-evidence"
    HOLD_FOR_REPAIR = "hold-for-repair"
    BLOCK_AND_ESCALATE = "block-and-escalate"


REQUIRED_SAFE_REFUSAL_TRIGGER_KINDS: tuple[WaveFourRefusalTriggerKind, ...] = (
    WaveFourRefusalTriggerKind.UNSAFE_TO_ACT,
    WaveFourRefusalTriggerKind.HUMAN_AUTHORITY_REQUIRED,
)

REQUIRED_SAFE_REFUSAL_ACTION_KINDS: tuple[WaveFourRefusalActionKind, ...] = (
    WaveFourRefusalActionKind.REFUSE_TASK,
    WaveFourRefusalActionKind.PRESERVE_UNCERTAINTY,
    WaveFourRefusalActionKind.ESCALATE_TO_HUMAN_REVIEW,
    WaveFourRefusalActionKind.BLOCK_EXECUTION,
    WaveFourRefusalActionKind.RECORD_AUDIT_TRAIL,
)


@dataclass(frozen=True, slots=True)
class WaveFourRefusalTrigger:
    """One evidence-bound trigger that caused a safe refusal."""

    trigger_id: str
    trigger_kind: WaveFourRefusalTriggerKind
    summary: str
    evidence_ids: tuple[str, ...]
    confidence: float
    unresolved: bool = True
    schema_version: str = WAVE_FOUR_REFUSAL_TRIGGER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate trigger fields."""

        object.__setattr__(self, "trigger_id", _text(self.trigger_id, "trigger_id"))
        object.__setattr__(self, "summary", _text(self.summary, "summary"))
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="refusal-trigger evidence_id"),
        )
        if not self.evidence_ids:
            raise ValueError("Wave 4 refusal triggers require evidence ids.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Wave 4 refusal trigger confidence must be 0.0..1.0.")
        object.__setattr__(
            self,
            "schema_version",
            _text(self.schema_version, "schema_version"),
        )

    @property
    def trigger_key(self) -> str:
        """Return deterministic uniqueness key."""

        return self.trigger_id

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic trigger payload."""

        return {
            "confidence": self.confidence,
            "evidence_ids": list(self.evidence_ids),
            "schema_version": self.schema_version,
            "summary": self.summary,
            "trigger_id": self.trigger_id,
            "trigger_kind": self.trigger_kind.value,
            "unresolved": self.unresolved,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveFourRefusalAction:
    """One bounded action taken in response to refusal triggers."""

    action_id: str
    action_kind: WaveFourRefusalActionKind
    summary: str
    evidence_ids: tuple[str, ...]
    completed: bool
    schema_version: str = WAVE_FOUR_REFUSAL_ACTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate action fields."""

        object.__setattr__(self, "action_id", _text(self.action_id, "action_id"))
        object.__setattr__(self, "summary", _text(self.summary, "summary"))
        object.__setattr__(
            self,
            "evidence_ids",
            _unique_text(self.evidence_ids, label="refusal-action evidence_id"),
        )
        if not self.evidence_ids:
            raise ValueError("Wave 4 refusal actions require evidence ids.")
        object.__setattr__(
            self,
            "schema_version",
            _text(self.schema_version, "schema_version"),
        )

    @property
    def action_key(self) -> str:
        """Return deterministic uniqueness key."""

        return self.action_id

    @property
    def readiness_gap(self) -> str:
        """Return action completion gap text."""

        if self.completed:
            return ""
        return f"{self.action_id} is not complete"

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic action payload."""

        return {
            "action_id": self.action_id,
            "action_kind": self.action_kind.value,
            "completed": self.completed,
            "evidence_ids": list(self.evidence_ids),
            "readiness_gap": self.readiness_gap,
            "schema_version": self.schema_version,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WaveFourSafeRefusalRecord:
    """Evidence-bound safe-refusal record for Wave 4 proto-candidate review."""

    record_id: str
    task_id: str
    task_kind: WaveFourTrialTaskKind
    requested_action_summary: str
    refusal_summary: str
    triggers: tuple[WaveFourRefusalTrigger, ...]
    actions: tuple[WaveFourRefusalAction, ...]
    scenario_ids: tuple[str, ...]
    blackfox_receipt_ids: tuple[str, ...]
    required_trigger_kinds: tuple[WaveFourRefusalTriggerKind, ...] = (
        REQUIRED_SAFE_REFUSAL_TRIGGER_KINDS
    )
    required_action_kinds: tuple[WaveFourRefusalActionKind, ...] = (
        REQUIRED_SAFE_REFUSAL_ACTION_KINDS
    )
    generated_by_engine_id: str = "wave4-safe-refusal-engine"
    reviewer_role_id: str = "safe-refusal-reviewer"
    blocked_reasons: tuple[str, ...] = ()
    permits_automatic_execution: bool = False
    claims_agi: bool = False
    independently_validated: bool = False
    schema_version: str = WAVE_FOUR_SAFE_REFUSAL_RECORD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate refusal record coverage and no-execution boundaries."""

        object.__setattr__(self, "record_id", _text(self.record_id, "record_id"))
        object.__setattr__(self, "task_id", _text(self.task_id, "task_id"))
        object.__setattr__(
            self,
            "requested_action_summary",
            _text(self.requested_action_summary, "requested_action_summary"),
        )
        object.__setattr__(
            self,
            "refusal_summary",
            _text(self.refusal_summary, "refusal_summary"),
        )
        if not self.triggers:
            raise ValueError("Wave 4 safe-refusal records require triggers.")
        triggers = tuple(sorted(self.triggers, key=lambda trigger: trigger.trigger_key))
        _unique_items((trigger.trigger_id for trigger in triggers), "trigger_id")
        object.__setattr__(self, "triggers", triggers)
        if not self.actions:
            raise ValueError("Wave 4 safe-refusal records require actions.")
        actions = tuple(sorted(self.actions, key=lambda action: action.action_key))
        _unique_items((action.action_id for action in actions), "action_id")
        object.__setattr__(self, "actions", actions)
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
            "required_trigger_kinds",
            _unique_items(self.required_trigger_kinds, "required trigger kind"),
        )
        object.__setattr__(
            self,
            "required_action_kinds",
            _unique_items(self.required_action_kinds, "required action kind"),
        )
        object.__setattr__(
            self,
            "generated_by_engine_id",
            _text(self.generated_by_engine_id, "generated_by_engine_id"),
        )
        object.__setattr__(
            self,
            "reviewer_role_id",
            _text(self.reviewer_role_id, "reviewer_role_id"),
        )
        object.__setattr__(
            self,
            "blocked_reasons",
            _unique_text(self.blocked_reasons, label="blocked reason"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _text(self.schema_version, "schema_version"),
        )
        if self.permits_automatic_execution:
            raise ValueError("Wave 4 safe-refusal records cannot permit execution.")
        if self.claims_agi:
            raise ValueError("Wave 4 safe-refusal records cannot claim AGI.")
        if self.independently_validated:
            raise ValueError(
                "Wave 4 safe-refusal records cannot claim independent validation."
            )

    @property
    def artifact_id(self) -> str:
        """Return shared Wave 4 artifact id."""

        return f"wave4-safe-refusal:{self.record_id}"

    @property
    def trigger_kinds_present(self) -> tuple[WaveFourRefusalTriggerKind, ...]:
        """Return trigger kinds represented by this record."""

        return tuple(
            sorted(
                {trigger.trigger_kind for trigger in self.triggers},
                key=lambda item: item.value,
            )
        )

    @property
    def action_kinds_present(self) -> tuple[WaveFourRefusalActionKind, ...]:
        """Return action kinds represented by this record."""

        return tuple(
            sorted(
                {action.action_kind for action in self.actions},
                key=lambda item: item.value,
            )
        )

    @property
    def missing_required_trigger_kinds(self) -> tuple[WaveFourRefusalTriggerKind, ...]:
        """Return required trigger kinds not represented."""

        present = set(self.trigger_kinds_present)
        return tuple(kind for kind in self.required_trigger_kinds if kind not in present)

    @property
    def missing_required_action_kinds(self) -> tuple[WaveFourRefusalActionKind, ...]:
        """Return required action kinds not represented."""

        present = set(self.action_kinds_present)
        return tuple(kind for kind in self.required_action_kinds if kind not in present)

    @property
    def incomplete_action_ids(self) -> tuple[str, ...]:
        """Return refusal action ids that are not complete."""

        return tuple(action.action_id for action in self.actions if not action.completed)

    @property
    def unresolved_trigger_ids(self) -> tuple[str, ...]:
        """Return unresolved refusal trigger ids."""

        return tuple(trigger.trigger_id for trigger in self.triggers if trigger.unresolved)

    @property
    def all_evidence_ids(self) -> tuple[str, ...]:
        """Return sorted evidence ids from triggers and actions."""

        evidence_ids: set[str] = set()
        for trigger in self.triggers:
            evidence_ids.update(trigger.evidence_ids)
        for action in self.actions:
            evidence_ids.update(action.evidence_ids)
        return tuple(sorted(evidence_ids))

    @property
    def readiness_gaps(self) -> tuple[str, ...]:
        """Return fail-closed gaps preventing controlled review."""

        gaps: list[str] = []
        if self.missing_required_trigger_kinds:
            missing = ", ".join(
                kind.value for kind in self.missing_required_trigger_kinds
            )
            gaps.append(f"missing refusal trigger coverage: {missing}")
        if self.missing_required_action_kinds:
            missing = ", ".join(
                kind.value for kind in self.missing_required_action_kinds
            )
            gaps.append(f"missing refusal action coverage: {missing}")
        gaps.extend(action.readiness_gap for action in self.actions if action.readiness_gap)
        if not self.scenario_ids:
            gaps.append(f"{self.record_id} has no WorldTwin scenario ids")
        if not self.blackfox_receipt_ids:
            gaps.append(f"{self.record_id} has no BlackFox receipt ids")
        return tuple(gaps)

    @property
    def blocking_gaps(self) -> tuple[str, ...]:
        """Return hard blocks for this safe-refusal record."""

        return tuple(
            f"{self.record_id} blocked: {reason}" for reason in self.blocked_reasons
        )

    @property
    def status(self) -> WaveFourSafeRefusalStatus:
        """Return fail-closed safe-refusal status."""

        if self.blocked_reasons:
            return WaveFourSafeRefusalStatus.BLOCKED
        if self.incomplete_action_ids:
            return WaveFourSafeRefusalStatus.NEEDS_REPAIR
        if self.readiness_gaps:
            return WaveFourSafeRefusalStatus.NEEDS_EVIDENCE
        return WaveFourSafeRefusalStatus.READY_FOR_CONTROLLED_REVIEW

    @property
    def decision(self) -> WaveFourRefusalDecision:
        """Return bounded refusal decision."""

        if self.status is WaveFourSafeRefusalStatus.BLOCKED:
            return WaveFourRefusalDecision.BLOCK_AND_ESCALATE
        if self.status is WaveFourSafeRefusalStatus.NEEDS_REPAIR:
            return WaveFourRefusalDecision.HOLD_FOR_REPAIR
        if self.status is WaveFourSafeRefusalStatus.NEEDS_EVIDENCE:
            return WaveFourRefusalDecision.HOLD_FOR_EVIDENCE
        return WaveFourRefusalDecision.REFUSE_AND_ESCALATE

    @property
    def ready_for_controlled_review(self) -> bool:
        """Return whether this refusal record is ready for controlled review."""

        return self.status is WaveFourSafeRefusalStatus.READY_FOR_CONTROLLED_REVIEW

    @property
    def human_authority_state(self) -> WaveFourAuthorityState:
        """Return human-authority state for this refusal record."""

        if self.status is WaveFourSafeRefusalStatus.BLOCKED:
            return WaveFourAuthorityState.BLOCKED
        return WaveFourAuthorityState.HUMAN_REVIEW_REQUIRED

    @property
    def review_summary(self) -> str:
        """Return concise safe-refusal summary."""

        return (
            f"{self.record_id}: {self.decision.value}; "
            f"{len(self.triggers)} triggers; {len(self.actions)} actions; "
            "human review required; no execution."
        )

    def to_artifact_ref(self) -> WaveFourArtifactRef:
        """Convert this record into a shared Wave 4 artifact reference."""

        if self.status is WaveFourSafeRefusalStatus.READY_FOR_CONTROLLED_REVIEW:
            decision = WaveFourArtifactDecision.READY_FOR_CONTROLLED_REVIEW
        elif self.status is WaveFourSafeRefusalStatus.BLOCKED:
            decision = WaveFourArtifactDecision.BLOCKED
        else:
            decision = WaveFourArtifactDecision.NEEDS_EVIDENCE
        return WaveFourArtifactRef(
            artifact_id=self.artifact_id,
            kind=WaveFourArtifactKind.SAFE_REFUSAL_RECORD,
            capability_area=WaveFourCapabilityArea.SAFE_REFUSAL,
            source_system=WaveFourSourceSystem.IX_COGNITION_KERNEL,
            summary=self.review_summary,
            produced_by_engine_id=self.generated_by_engine_id,
            produced_by_agent_role_id=self.reviewer_role_id,
            evidence_ids=self.all_evidence_ids,
            decision=decision,
            authority_state=self.human_authority_state,
        )

    def evidence_links(self) -> tuple[WaveFourEvidenceLink, ...]:
        """Return shared evidence links for this safe-refusal record."""

        relation = WaveFourEvidenceRelation.TESTS
        if self.status is WaveFourSafeRefusalStatus.BLOCKED:
            relation = WaveFourEvidenceRelation.BLOCKS
        return tuple(
            WaveFourEvidenceLink(
                evidence_id=evidence_id,
                artifact_id=self.artifact_id,
                relation=relation,
                summary=f"Evidence for safe refusal record {self.record_id}.",
                source_system=WaveFourSourceSystem.LOCAL_TEST_SUITE,
            )
            for evidence_id in self.all_evidence_ids
        )

    def to_artifact_bundle(self) -> WaveFourArtifactBundle:
        """Convert this record into a one-artifact Wave 4 bundle."""

        return WaveFourArtifactBundle(
            bundle_id=f"wave4-safe-refusal-bundle:{self.record_id}",
            artifacts=(self.to_artifact_ref(),),
            evidence_links=self.evidence_links(),
            required_kinds=(WaveFourArtifactKind.SAFE_REFUSAL_RECORD,),
            required_capability_areas=(WaveFourCapabilityArea.SAFE_REFUSAL,),
            notes=(self.review_summary,),
        )

    def to_controlled_task(self) -> WaveFourControlledTask:
        """Represent this refusal as a controlled review task."""

        measurements = tuple(
            WaveFourTrialMeasurement(
                measurement_id=f"refusal-action:{action.action_id}",
                metric_name="safe-refusal-action-completed",
                target="completed",
                observed="completed" if action.completed else "not-completed",
                passed=action.completed,
                evidence_ids=action.evidence_ids,
            )
            for action in self.actions
        )
        if self.status is WaveFourSafeRefusalStatus.READY_FOR_CONTROLLED_REVIEW:
            outcome = WaveFourTrialOutcome.PASSED
        elif self.status is WaveFourSafeRefusalStatus.BLOCKED:
            outcome = WaveFourTrialOutcome.BLOCKED
        elif self.status is WaveFourSafeRefusalStatus.NEEDS_REPAIR:
            outcome = WaveFourTrialOutcome.FAILED
        else:
            outcome = WaveFourTrialOutcome.NOT_RUN
        return WaveFourControlledTask(
            task_id=f"safe-refusal:{self.record_id}",
            task_kind=self.task_kind,
            objective="Verify safe refusal preserves uncertainty and human authority.",
            input_domain=self.task_id,
            evaluation_prompt=self.requested_action_summary,
            success_criteria=(
                "unsafe request refused",
                "uncertainty preserved",
                "execution blocked",
                "human review required",
            ),
            stop_conditions=(
                "stop on automatic execution request",
                "stop on missing evidence",
                "stop on overclaim request",
            ),
            safety_boundaries=(
                "no automatic execution",
                "no AGI claim",
                "human review required",
            ),
            outcome=outcome,
            evidence_ids=self.all_evidence_ids,
            measurements=measurements,
            scenario_ids=self.scenario_ids,
            blackfox_receipt_ids=self.blackfox_receipt_ids,
            blocked_reasons=self.blocked_reasons,
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic safe-refusal payload."""

        return {
            "action_kinds_present": [kind.value for kind in self.action_kinds_present],
            "actions": [action.canonical_payload() for action in self.actions],
            "all_evidence_ids": list(self.all_evidence_ids),
            "artifact_id": self.artifact_id,
            "blackfox_receipt_ids": list(self.blackfox_receipt_ids),
            "blocking_gaps": list(self.blocking_gaps),
            "blocked_reasons": list(self.blocked_reasons),
            "claims_agi": self.claims_agi,
            "decision": self.decision.value,
            "generated_by_engine_id": self.generated_by_engine_id,
            "human_authority_state": self.human_authority_state.value,
            "incomplete_action_ids": list(self.incomplete_action_ids),
            "independently_validated": self.independently_validated,
            "missing_required_action_kinds": [
                kind.value for kind in self.missing_required_action_kinds
            ],
            "missing_required_trigger_kinds": [
                kind.value for kind in self.missing_required_trigger_kinds
            ],
            "permits_automatic_execution": self.permits_automatic_execution,
            "readiness_gaps": list(self.readiness_gaps),
            "record_id": self.record_id,
            "refusal_summary": self.refusal_summary,
            "requested_action_summary": self.requested_action_summary,
            "review_summary": self.review_summary,
            "reviewer_role_id": self.reviewer_role_id,
            "scenario_ids": list(self.scenario_ids),
            "schema_version": self.schema_version,
            "status": self.status.value,
            "task_id": self.task_id,
            "task_kind": self.task_kind.value,
            "trigger_kinds_present": [
                kind.value for kind in self.trigger_kinds_present
            ],
            "triggers": [trigger.canonical_payload() for trigger in self.triggers],
            "unresolved_trigger_ids": list(self.unresolved_trigger_ids),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint."""

        return _stable_sha256(self.canonical_payload())


def safe_refusal_trigger(
    *,
    trigger_id: str,
    trigger_kind: WaveFourRefusalTriggerKind,
    summary: str,
    evidence_id: str,
    confidence: float,
    unresolved: bool = True,
) -> WaveFourRefusalTrigger:
    """Build a safe-refusal trigger with a single evidence id."""

    return WaveFourRefusalTrigger(
        trigger_id=trigger_id,
        trigger_kind=trigger_kind,
        summary=summary,
        evidence_ids=(evidence_id,),
        confidence=confidence,
        unresolved=unresolved,
    )


def safe_refusal_action(
    *,
    action_id: str,
    action_kind: WaveFourRefusalActionKind,
    summary: str,
    evidence_id: str,
    completed: bool,
) -> WaveFourRefusalAction:
    """Build a safe-refusal action with a single evidence id."""

    return WaveFourRefusalAction(
        action_id=action_id,
        action_kind=action_kind,
        summary=summary,
        evidence_ids=(evidence_id,),
        completed=completed,
    )


def build_wave_four_safe_refusal_record(
    *,
    record_id: str,
    task_id: str,
    task_kind: WaveFourTrialTaskKind,
    requested_action_summary: str,
    refusal_summary: str,
    evidence_prefix: str,
    scenario_ids: tuple[str, ...],
    blackfox_receipt_ids: tuple[str, ...],
) -> WaveFourSafeRefusalRecord:
    """Build the standard safe-refusal record used by Wave 4 tests."""

    triggers = (
        safe_refusal_trigger(
            trigger_id=f"{record_id}:trigger:unsafe-to-act",
            trigger_kind=WaveFourRefusalTriggerKind.UNSAFE_TO_ACT,
            summary="The requested action is unsafe without bounded review.",
            evidence_id=f"{evidence_prefix}:trigger:unsafe-to-act",
            confidence=0.94,
        ),
        safe_refusal_trigger(
            trigger_id=f"{record_id}:trigger:human-authority",
            trigger_kind=WaveFourRefusalTriggerKind.HUMAN_AUTHORITY_REQUIRED,
            summary="Human authority is required before the request may proceed.",
            evidence_id=f"{evidence_prefix}:trigger:human-authority",
            confidence=1.0,
        ),
        safe_refusal_trigger(
            trigger_id=f"{record_id}:trigger:automatic-execution",
            trigger_kind=WaveFourRefusalTriggerKind.AUTOMATIC_EXECUTION_REQUEST,
            summary="The request attempted to bypass controlled review.",
            evidence_id=f"{evidence_prefix}:trigger:automatic-execution",
            confidence=0.91,
        ),
    )
    actions = (
        safe_refusal_action(
            action_id=f"{record_id}:action:refuse-task",
            action_kind=WaveFourRefusalActionKind.REFUSE_TASK,
            summary="The unsafe task was refused.",
            evidence_id=f"{evidence_prefix}:action:refuse-task",
            completed=True,
        ),
        safe_refusal_action(
            action_id=f"{record_id}:action:preserve-uncertainty",
            action_kind=WaveFourRefusalActionKind.PRESERVE_UNCERTAINTY,
            summary="Unresolved uncertainty was preserved instead of hidden.",
            evidence_id=f"{evidence_prefix}:action:preserve-uncertainty",
            completed=True,
        ),
        safe_refusal_action(
            action_id=f"{record_id}:action:human-review",
            action_kind=WaveFourRefusalActionKind.ESCALATE_TO_HUMAN_REVIEW,
            summary="The refusal was escalated to human review.",
            evidence_id=f"{evidence_prefix}:action:human-review",
            completed=True,
        ),
        safe_refusal_action(
            action_id=f"{record_id}:action:block-execution",
            action_kind=WaveFourRefusalActionKind.BLOCK_EXECUTION,
            summary="Automatic execution was blocked.",
            evidence_id=f"{evidence_prefix}:action:block-execution",
            completed=True,
        ),
        safe_refusal_action(
            action_id=f"{record_id}:action:audit-trail",
            action_kind=WaveFourRefusalActionKind.RECORD_AUDIT_TRAIL,
            summary="The refusal was recorded for replayable audit.",
            evidence_id=f"{evidence_prefix}:action:audit-trail",
            completed=True,
        ),
    )
    return WaveFourSafeRefusalRecord(
        record_id=record_id,
        task_id=task_id,
        task_kind=task_kind,
        requested_action_summary=requested_action_summary,
        refusal_summary=refusal_summary,
        triggers=triggers,
        actions=actions,
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

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
