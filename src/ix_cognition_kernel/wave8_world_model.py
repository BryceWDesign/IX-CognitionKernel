"""Wave 8 durable world-model formation.

This module adds the first durable world-model surface for the Recursive
Reality-Corrected Learner. It does not allow a model to convert a memory into a
truth claim. A world-model rule must remain evidence-bound, revisable,
contradictable, replayable, and scoped to bounded task families.

World-model doctrine:

- a rule is not truth,
- an observation is not the world,
- one success is not a durable rule,
- contradictions must remain attached,
- transfer evidence strengthens a rule,
- revoked and contradicted rules must not be applied,
- a world model cannot certify AGI or broad competence.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from ix_cognition_kernel.wave8_task_suite import TaskFamily, UnknownTaskInstance
from ix_cognition_kernel.wave8_transfer_challenge import (
    TransferBand,
    TransferTrialRecord,
    TransferTrialStatus,
)

WAVE_EIGHT_WORLD_RULE_SCHEMA_VERSION = "ix-cognition-kernel-wave8-world-rule-v1"
WAVE_EIGHT_WORLD_UPDATE_SCHEMA_VERSION = "ix-cognition-kernel-wave8-world-update-v1"
WAVE_EIGHT_WORLD_SNAPSHOT_SCHEMA_VERSION = "ix-cognition-kernel-wave8-world-snapshot-v1"
WAVE_EIGHT_WORLD_APPLICATION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-world-application-v1"
)


class WorldRuleKind(StrEnum):
    """Kinds of bounded world-model rules."""

    TRANSITION = "transition"
    CONSTRAINT = "constraint"
    EXCEPTION = "exception"
    CAUSAL_LINK = "causal-link"
    FAILURE_BOUNDARY = "failure-boundary"


class WorldRuleConfidence(StrEnum):
    """Evidence status for a bounded world-model rule."""

    HYPOTHESIS = "hypothesis"
    SUPPORTED = "supported"
    TRANSFER_SUPPORTED = "transfer-supported"
    CONTRADICTED = "contradicted"
    REVOKED = "revoked"


class WorldModelUpdateDecision(StrEnum):
    """Fail-closed update decision for a candidate world rule."""

    RECORD_HYPOTHESIS = "record-hypothesis"
    PROMOTE_SUPPORTED_RULE = "promote-supported-rule"
    PROMOTE_TRANSFER_SUPPORTED_RULE = "promote-transfer-supported-rule"
    QUARANTINE_CONTRADICTION = "quarantine-contradiction"
    REVOKE_CONTRADICTED_RULE = "revoke-contradicted-rule"
    BLOCK_OVERCLAIM = "block-overclaim"


class WorldRuleApplicationDecision(StrEnum):
    """Decision for applying a world-model rule to a bounded task."""

    APPLICATION_READY = "application-ready"
    NEEDS_ACTION_ALIGNMENT = "needs-action-alignment"
    NEEDS_FEATURE_ALIGNMENT = "needs-feature-alignment"
    BLOCKED_CONTRADICTED = "blocked-contradicted"
    BLOCKED_REVOKED = "blocked-revoked"
    BLOCKED_OVERCLAIM = "blocked-overclaim"


@dataclass(frozen=True, slots=True)
class WorldModelRule:
    """Evidence-bound bounded world-model rule."""

    rule_id: str
    family: TaskFamily
    kind: WorldRuleKind
    statement: str
    antecedent_features: tuple[str, ...]
    action_ids: tuple[str, ...]
    expected_consequences: tuple[str, ...]
    exception_features: tuple[str, ...]
    source_trial_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    confidence: WorldRuleConfidence = WorldRuleConfidence.HYPOTHESIS
    schema_version: str = WAVE_EIGHT_WORLD_RULE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate world-model rule scope and evidence."""

        object.__setattr__(
            self,
            "rule_id",
            _require_non_empty(self.rule_id, "rule_id"),
        )
        object.__setattr__(
            self,
            "statement",
            _require_non_empty(self.statement, "statement"),
        )
        _reject_overclaiming_text(self.statement, "statement")
        object.__setattr__(
            self,
            "antecedent_features",
            _normalize_unique_text_tuple(
                self.antecedent_features,
                label="antecedent_feature",
            ),
        )
        object.__setattr__(
            self,
            "action_ids",
            _normalize_unique_text_tuple(self.action_ids, label="action_id"),
        )
        object.__setattr__(
            self,
            "expected_consequences",
            _normalize_unique_text_tuple(
                self.expected_consequences,
                label="expected_consequence",
            ),
        )
        object.__setattr__(
            self,
            "exception_features",
            _dedupe_text_tuple(self.exception_features, label="exception_feature"),
        )
        object.__setattr__(
            self,
            "source_trial_ids",
            _normalize_unique_text_tuple(self.source_trial_ids, label="source_trial_id"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.antecedent_features:
            raise ValueError("World-model rules require antecedent features.")
        if not self.action_ids:
            raise ValueError("World-model rules require action ids.")
        if not self.expected_consequences:
            raise ValueError("World-model rules require expected consequences.")
        if not self.source_trial_ids:
            raise ValueError("World-model rules require source trial ids.")
        if not self.evidence_ids:
            raise ValueError("World-model rules require evidence ids.")

    @property
    def active(self) -> bool:
        """Return whether the rule may be considered for application."""

        return self.confidence not in {
            WorldRuleConfidence.CONTRADICTED,
            WorldRuleConfidence.REVOKED,
        }

    @property
    def transfer_supported(self) -> bool:
        """Return whether the rule has transfer-supported confidence."""

        return self.confidence is WorldRuleConfidence.TRANSFER_SUPPORTED

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic world-rule payload."""

        return {
            "action_ids": list(self.action_ids),
            "antecedent_features": list(self.antecedent_features),
            "confidence": self.confidence.value,
            "evidence_ids": list(self.evidence_ids),
            "exception_features": list(self.exception_features),
            "expected_consequences": list(self.expected_consequences),
            "family": self.family.value,
            "kind": self.kind.value,
            "rule_id": self.rule_id,
            "schema_version": self.schema_version,
            "source_trial_ids": list(self.source_trial_ids),
            "statement": self.statement,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this rule."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WorldModelUpdateRecord:
    """Evidence-bound update record for a world-model rule."""

    update_id: str
    rule: WorldModelRule
    supporting_trial_ids: tuple[str, ...]
    contradicting_trial_ids: tuple[str, ...]
    decision: WorldModelUpdateDecision
    findings: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_WORLD_UPDATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate world-model update evidence."""

        object.__setattr__(
            self,
            "update_id",
            _require_non_empty(self.update_id, "update_id"),
        )
        object.__setattr__(
            self,
            "supporting_trial_ids",
            _dedupe_text_tuple(self.supporting_trial_ids, label="supporting_trial_id"),
        )
        object.__setattr__(
            self,
            "contradicting_trial_ids",
            _dedupe_text_tuple(
                self.contradicting_trial_ids,
                label="contradicting_trial_id",
            ),
        )
        object.__setattr__(
            self,
            "findings",
            _dedupe_text_tuple(self.findings, label="finding"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if (
            self.decision
            not in {
                WorldModelUpdateDecision.PROMOTE_SUPPORTED_RULE,
                WorldModelUpdateDecision.PROMOTE_TRANSFER_SUPPORTED_RULE,
            }
            and not self.findings
        ):
            raise ValueError("Non-promoted world-model updates require findings.")
        if (
            self.decision is WorldModelUpdateDecision.QUARANTINE_CONTRADICTION
            and not self.contradicting_trial_ids
        ):
            raise ValueError("Contradiction updates require contradicting trial ids.")

    @property
    def promoted(self) -> bool:
        """Return whether the rule was promoted."""

        return self.decision in {
            WorldModelUpdateDecision.PROMOTE_SUPPORTED_RULE,
            WorldModelUpdateDecision.PROMOTE_TRANSFER_SUPPORTED_RULE,
        }

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic update payload."""

        return {
            "contradicting_trial_ids": list(self.contradicting_trial_ids),
            "decision": self.decision.value,
            "findings": list(self.findings),
            "rule_fingerprint": self.rule.fingerprint(),
            "schema_version": self.schema_version,
            "supporting_trial_ids": list(self.supporting_trial_ids),
            "update_id": self.update_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this update."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WorldModelSnapshot:
    """Durable bounded world-model snapshot."""

    snapshot_id: str
    purpose: str
    rules: tuple[WorldModelRule, ...]
    update_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_WORLD_SNAPSHOT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate snapshot rule identity and evidence."""

        object.__setattr__(
            self,
            "snapshot_id",
            _require_non_empty(self.snapshot_id, "snapshot_id"),
        )
        object.__setattr__(
            self,
            "purpose",
            _require_non_empty(self.purpose, "purpose"),
        )
        _reject_overclaiming_text(self.purpose, "purpose")
        object.__setattr__(
            self,
            "rules",
            tuple(self.rules),
        )
        object.__setattr__(
            self,
            "update_ids",
            _normalize_unique_text_tuple(self.update_ids, label="update_id"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.rules:
            raise ValueError("World-model snapshots require rules.")
        if not self.update_ids:
            raise ValueError("World-model snapshots require update ids.")
        if not self.evidence_ids:
            raise ValueError("World-model snapshots require evidence ids.")
        seen: set[str] = set()
        for rule in self.rules:
            if rule.rule_id in seen:
                raise ValueError(f"Duplicate rule_id: {rule.rule_id}")
            seen.add(rule.rule_id)

    @property
    def active_rules(self) -> tuple[WorldModelRule, ...]:
        """Return active rules in deterministic order."""

        return tuple(rule for rule in self.rules if rule.active)

    @property
    def transfer_supported_rule_count(self) -> int:
        """Return count of transfer-supported rules."""

        return sum(1 for rule in self.rules if rule.transfer_supported)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic snapshot payload."""

        return {
            "evidence_ids": list(self.evidence_ids),
            "purpose": self.purpose,
            "rule_fingerprints": [rule.fingerprint() for rule in self.rules],
            "schema_version": self.schema_version,
            "snapshot_id": self.snapshot_id,
            "update_ids": list(self.update_ids),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this snapshot."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class WorldRuleApplicationPlan:
    """Plan for applying a world-model rule to a bounded task."""

    plan_id: str
    rule: WorldModelRule
    task: UnknownTaskInstance
    decision: WorldRuleApplicationDecision
    matched_features: tuple[str, ...]
    matched_actions: tuple[str, ...]
    findings: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_WORLD_APPLICATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate application-plan payload."""

        object.__setattr__(
            self,
            "plan_id",
            _require_non_empty(self.plan_id, "plan_id"),
        )
        object.__setattr__(
            self,
            "matched_features",
            _dedupe_text_tuple(self.matched_features, label="matched_feature"),
        )
        object.__setattr__(
            self,
            "matched_actions",
            _dedupe_text_tuple(self.matched_actions, label="matched_action"),
        )
        object.__setattr__(
            self,
            "findings",
            _dedupe_text_tuple(self.findings, label="finding"),
        )
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if self.decision is not WorldRuleApplicationDecision.APPLICATION_READY:
            if not self.findings:
                raise ValueError("Non-ready world-rule applications require findings.")

    @property
    def ready(self) -> bool:
        """Return whether the rule may be applied to the task."""

        return self.decision is WorldRuleApplicationDecision.APPLICATION_READY

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic application-plan payload."""

        return {
            "decision": self.decision.value,
            "findings": list(self.findings),
            "matched_actions": list(self.matched_actions),
            "matched_features": list(self.matched_features),
            "plan_id": self.plan_id,
            "rule_fingerprint": self.rule.fingerprint(),
            "schema_version": self.schema_version,
            "task_fingerprint": self.task.fingerprint(),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this plan."""

        return _stable_sha256(self.canonical_payload())


def derive_world_rule_from_trials(
    *,
    rule_id: str,
    statement: str,
    family: TaskFamily,
    trials: Iterable[TransferTrialRecord],
    evidence_ids: Iterable[str],
    kind: WorldRuleKind = WorldRuleKind.TRANSITION,
) -> WorldModelRule:
    """Derive a bounded world-model rule from transfer-trial evidence."""

    trial_tuple = tuple(trials)
    if not trial_tuple:
        raise ValueError("World-rule derivation requires transfer trials.")
    antecedents = tuple(
        feature
        for trial in trial_tuple
        for feature in trial.task.initial_observation.visible_features
    )
    action_ids = tuple(
        operation
        for trial in trial_tuple
        if (operation := _expected_operation_from_task(trial.task))
    )
    expected_consequences = tuple(
        feature for trial in trial_tuple for feature in trial.expected_feature_ids
    )
    exception_features = tuple(
        feature
        for trial in trial_tuple
        if trial.status is TransferTrialStatus.REPLAYABLE_FAIL
        for feature in trial.observed_feature_ids
    )
    confidence = _confidence_from_trials(trial_tuple)
    combined_evidence = (
        *tuple(evidence_ids),
        *tuple(trial.fingerprint() for trial in trial_tuple),
    )
    return WorldModelRule(
        rule_id=rule_id,
        family=family,
        kind=kind,
        statement=statement,
        antecedent_features=antecedents,
        action_ids=action_ids,
        expected_consequences=expected_consequences,
        exception_features=exception_features,
        source_trial_ids=tuple(trial.trial_id for trial in trial_tuple),
        evidence_ids=combined_evidence,
        confidence=confidence,
    )


def build_world_model_update(
    *,
    update_id: str,
    rule: WorldModelRule,
    trials: Iterable[TransferTrialRecord],
) -> WorldModelUpdateRecord:
    """Build a fail-closed world-model update from trial evidence."""

    trial_tuple = tuple(trials)
    supporting = tuple(
        trial.trial_id
        for trial in trial_tuple
        if trial.status is TransferTrialStatus.REPLAYABLE_PASS
    )
    contradicting = tuple(
        trial.trial_id
        for trial in trial_tuple
        if trial.status is TransferTrialStatus.REPLAYABLE_FAIL
    )
    findings: list[str] = []
    if not supporting:
        findings.append("missing-supporting-trial")
    if contradicting:
        findings.append("contradicting-trial-present")
    if any(trial.status is TransferTrialStatus.BLOCKED for trial in trial_tuple):
        findings.append("blocked-trial-present")
    if any(
        trial.status is TransferTrialStatus.NEEDS_MEASURED_RESULT
        for trial in trial_tuple
    ):
        findings.append("unmeasured-trial-present")
    if _rule_contains_overclaim(rule):
        findings.append("world-rule-overclaims-scope")

    if "world-rule-overclaims-scope" in findings:
        decision = WorldModelUpdateDecision.BLOCK_OVERCLAIM
    elif "blocked-trial-present" in findings:
        decision = WorldModelUpdateDecision.REVOKE_CONTRADICTED_RULE
    elif "contradicting-trial-present" in findings:
        decision = WorldModelUpdateDecision.QUARANTINE_CONTRADICTION
    elif "unmeasured-trial-present" in findings or "missing-supporting-trial" in findings:
        decision = WorldModelUpdateDecision.RECORD_HYPOTHESIS
    elif _has_transfer_support(trial_tuple):
        decision = WorldModelUpdateDecision.PROMOTE_TRANSFER_SUPPORTED_RULE
    else:
        findings.append("missing-transfer-support")
        decision = WorldModelUpdateDecision.PROMOTE_SUPPORTED_RULE

    return WorldModelUpdateRecord(
        update_id=update_id,
        rule=rule,
        supporting_trial_ids=supporting,
        contradicting_trial_ids=contradicting,
        decision=decision,
        findings=tuple(findings),
    )


def build_world_model_snapshot(
    *,
    snapshot_id: str,
    purpose: str,
    updates: Iterable[WorldModelUpdateRecord],
    evidence_ids: Iterable[str],
) -> WorldModelSnapshot:
    """Build a durable world-model snapshot from updates."""

    update_tuple = tuple(updates)
    if not update_tuple:
        raise ValueError("World-model snapshots require updates.")
    return WorldModelSnapshot(
        snapshot_id=snapshot_id,
        purpose=purpose,
        rules=tuple(update.rule for update in update_tuple),
        update_ids=tuple(update.update_id for update in update_tuple),
        evidence_ids=tuple(evidence_ids),
    )


def plan_world_rule_application(
    *,
    plan_id: str,
    rule: WorldModelRule,
    task: UnknownTaskInstance,
) -> WorldRuleApplicationPlan:
    """Plan evidence-bound application of a world-model rule to a task."""

    matched_features = _intersection(
        rule.antecedent_features,
        task.initial_observation.visible_features,
    )
    task_operations = tuple(
        feature.removeprefix("operation:")
        for feature in task.expected_outcome_features
        if feature.startswith("operation:")
    )
    matched_actions = _intersection(rule.action_ids, task_operations)
    findings: list[str] = []
    if rule.confidence is WorldRuleConfidence.REVOKED:
        findings.append("world-rule-revoked")
        decision = WorldRuleApplicationDecision.BLOCKED_REVOKED
    elif rule.confidence is WorldRuleConfidence.CONTRADICTED:
        findings.append("world-rule-contradicted")
        decision = WorldRuleApplicationDecision.BLOCKED_CONTRADICTED
    elif _rule_contains_overclaim(rule):
        findings.append("world-rule-overclaims-scope")
        decision = WorldRuleApplicationDecision.BLOCKED_OVERCLAIM
    elif not matched_actions:
        findings.append("missing-action-alignment")
        decision = WorldRuleApplicationDecision.NEEDS_ACTION_ALIGNMENT
    elif not matched_features:
        findings.append("missing-feature-alignment")
        decision = WorldRuleApplicationDecision.NEEDS_FEATURE_ALIGNMENT
    else:
        decision = WorldRuleApplicationDecision.APPLICATION_READY

    return WorldRuleApplicationPlan(
        plan_id=plan_id,
        rule=rule,
        task=task,
        decision=decision,
        matched_features=matched_features,
        matched_actions=matched_actions,
        findings=tuple(findings),
    )


def _confidence_from_trials(
    trials: tuple[TransferTrialRecord, ...],
) -> WorldRuleConfidence:
    if any(trial.status is TransferTrialStatus.BLOCKED for trial in trials):
        return WorldRuleConfidence.REVOKED
    if any(trial.status is TransferTrialStatus.REPLAYABLE_FAIL for trial in trials):
        return WorldRuleConfidence.CONTRADICTED
    if _has_transfer_support(trials):
        return WorldRuleConfidence.TRANSFER_SUPPORTED
    if any(trial.status is TransferTrialStatus.REPLAYABLE_PASS for trial in trials):
        return WorldRuleConfidence.SUPPORTED
    return WorldRuleConfidence.HYPOTHESIS


def _has_transfer_support(trials: tuple[TransferTrialRecord, ...]) -> bool:
    bands = {trial.band for trial in trials if trial.status is TransferTrialStatus.REPLAYABLE_PASS}
    return bool({TransferBand.NEAR, TransferBand.FAR, TransferBand.HIDDEN} & bands)


def _expected_operation_from_task(task: UnknownTaskInstance) -> str:
    for feature in task.expected_outcome_features:
        if feature.startswith("operation:"):
            return feature.removeprefix("operation:")
    return ""


def _intersection(left: Iterable[str], right: Iterable[str]) -> tuple[str, ...]:
    right_set = set(right)
    return tuple(sorted({value for value in left if value in right_set}))


def _rule_contains_overclaim(rule: WorldModelRule) -> bool:
    try:
        _reject_overclaiming_text(rule.statement, "statement")
    except ValueError:
        return True
    return False


def _reject_overclaiming_text(value: str, label: str) -> None:
    lowered = value.casefold()
    blocked_terms = (
        "agi",
        "artificial general intelligence",
        "general intelligence achieved",
        "universal intelligence",
        "superintelligence",
    )
    if any(term in lowered for term in blocked_terms):
        raise ValueError(f"{label} contains blocked overclaiming language.")


def _require_non_empty(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty.")
    return normalized


def _normalize_unique_text_tuple(
    values: Iterable[str], *, label: str
) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _require_non_empty(value, label)
        if text in seen:
            raise ValueError(f"Duplicate {label}: {text}")
        seen.add(text)
        normalized.append(text)
    return tuple(sorted(normalized))


def _dedupe_text_tuple(values: Iterable[str], *, label: str) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _require_non_empty(value, label)
        if text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return tuple(sorted(normalized))


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
