"""Wave 8 skill synthesis and reuse.

This module adds the first real skill-synthesis surface for the Recursive
Reality-Corrected Learner. It does not allow a model to declare that it "has a
skill." A skill candidate must be derived from replayable evidence, transfer
pressure, failure history, and bounded reuse constraints.

Skill doctrine:

- a skill is not a prompt,
- a skill is not self-certified,
- original-task success is not enough,
- transfer evidence is required before reuse promotion,
- failure modes must remain attached to the skill,
- skills can become stale, blocked, or revoked,
- no skill may claim AGI or broad competence by name.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from ix_cognition_kernel.wave8_task_suite import UnknownTaskInstance
from ix_cognition_kernel.wave8_transfer_challenge import (
    TransferBand,
    TransferChallengeReport,
    TransferClaimDecision,
    TransferTrialRecord,
    TransferTrialStatus,
)

WAVE_EIGHT_SKILL_CANDIDATE_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-skill-candidate-v1"
)
WAVE_EIGHT_SKILL_VALIDATION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-skill-validation-v1"
)
WAVE_EIGHT_SKILL_LIBRARY_ENTRY_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-skill-library-entry-v1"
)
WAVE_EIGHT_SKILL_REUSE_PLAN_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-skill-reuse-plan-v1"
)


class SkillPromotionDecision(StrEnum):
    """Fail-closed promotion state for a synthesized skill."""

    READY_FOR_REUSE = "ready-for-reuse"
    NEEDS_REPLAYABLE_EVIDENCE = "needs-replayable-evidence"
    NEEDS_TRANSFER_EVIDENCE = "needs-transfer-evidence"
    NEEDS_HIDDEN_VALIDATION = "needs-hidden-validation"
    BLOCKED_BY_FAILURE = "blocked-by-failure"
    BLOCKED_BY_OVERCLAIM = "blocked-by-overclaim"


class SkillReuseDecision(StrEnum):
    """Decision for applying a skill candidate to a new bounded task."""

    REUSE_READY = "reuse-ready"
    NEEDS_HUMAN_REVIEW = "needs-human-review"
    NEEDS_TRANSFER_ALIGNMENT = "needs-transfer-alignment"
    BLOCKED_STALE = "blocked-stale"
    BLOCKED_REVOKED = "blocked-revoked"
    BLOCKED_UNVALIDATED = "blocked-unvalidated"


@dataclass(frozen=True, slots=True)
class SkillCandidate:
    """Evidence-derived bounded skill candidate."""

    skill_id: str
    name: str
    purpose: str
    source_task_ids: tuple[str, ...]
    operation_ids: tuple[str, ...]
    preconditions: tuple[str, ...]
    expected_effects: tuple[str, ...]
    transfer_tags: tuple[str, ...]
    failure_modes: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_SKILL_CANDIDATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate bounded skill identity and evidence."""

        object.__setattr__(
            self,
            "skill_id",
            _require_non_empty(self.skill_id, "skill_id"),
        )
        object.__setattr__(
            self,
            "name",
            _require_non_empty(self.name, "name"),
        )
        object.__setattr__(
            self,
            "purpose",
            _require_non_empty(self.purpose, "purpose"),
        )
        _reject_overclaiming_text(self.name, "name")
        _reject_overclaiming_text(self.purpose, "purpose")
        object.__setattr__(
            self,
            "source_task_ids",
            _normalize_unique_text_tuple(self.source_task_ids, label="source_task_id"),
        )
        object.__setattr__(
            self,
            "operation_ids",
            _normalize_unique_text_tuple(self.operation_ids, label="operation_id"),
        )
        object.__setattr__(
            self,
            "preconditions",
            _normalize_unique_text_tuple(self.preconditions, label="precondition"),
        )
        object.__setattr__(
            self,
            "expected_effects",
            _normalize_unique_text_tuple(
                self.expected_effects, label="expected_effect"
            ),
        )
        object.__setattr__(
            self,
            "transfer_tags",
            _normalize_unique_text_tuple(self.transfer_tags, label="transfer_tag"),
        )
        object.__setattr__(
            self,
            "failure_modes",
            _dedupe_text_tuple(self.failure_modes, label="failure_mode"),
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
        if not self.source_task_ids:
            raise ValueError("Skill candidates require source task ids.")
        if not self.operation_ids:
            raise ValueError("Skill candidates require operation ids.")
        if not self.preconditions:
            raise ValueError("Skill candidates require preconditions.")
        if not self.expected_effects:
            raise ValueError("Skill candidates require expected effects.")
        if not self.transfer_tags:
            raise ValueError("Skill candidates require transfer tags.")
        if not self.evidence_ids:
            raise ValueError("Skill candidates require evidence ids.")

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic skill-candidate payload."""

        return {
            "evidence_ids": list(self.evidence_ids),
            "expected_effects": list(self.expected_effects),
            "failure_modes": list(self.failure_modes),
            "name": self.name,
            "operation_ids": list(self.operation_ids),
            "preconditions": list(self.preconditions),
            "purpose": self.purpose,
            "schema_version": self.schema_version,
            "skill_id": self.skill_id,
            "source_task_ids": list(self.source_task_ids),
            "transfer_tags": list(self.transfer_tags),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this skill candidate."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class SkillValidationRecord:
    """Validation record for promoting a skill candidate."""

    validation_id: str
    candidate: SkillCandidate
    transfer_report: TransferChallengeReport
    decision: SkillPromotionDecision
    findings: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_SKILL_VALIDATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate skill promotion record."""

        object.__setattr__(
            self,
            "validation_id",
            _require_non_empty(self.validation_id, "validation_id"),
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
        report_task_ids = {trial.task.task_id for trial in self.transfer_report.trials}
        for task_id in self.candidate.source_task_ids:
            if task_id not in report_task_ids:
                raise ValueError(
                    f"Skill source task is not in transfer report: {task_id}"
                )
        if (
            self.decision is not SkillPromotionDecision.READY_FOR_REUSE
            and not self.findings
        ):
            raise ValueError("Non-ready skill validations require findings.")

    @property
    def ready(self) -> bool:
        """Return whether the skill can be reused under bounded constraints."""

        return self.decision is SkillPromotionDecision.READY_FOR_REUSE

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic validation payload."""

        return {
            "candidate_fingerprint": self.candidate.fingerprint(),
            "decision": self.decision.value,
            "findings": list(self.findings),
            "schema_version": self.schema_version,
            "transfer_report_fingerprint": self.transfer_report.fingerprint(),
            "validation_id": self.validation_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this validation."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class SkillLibraryEntry:
    """Stored skill library entry with lifecycle controls."""

    entry_id: str
    candidate: SkillCandidate
    validation: SkillValidationRecord
    reuse_count: int
    stale: bool = False
    revoked: bool = False
    review_required: bool = False
    evidence_ids: tuple[str, ...] = ()
    schema_version: str = WAVE_EIGHT_SKILL_LIBRARY_ENTRY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate stored skill lifecycle entry."""

        object.__setattr__(
            self,
            "entry_id",
            _require_non_empty(self.entry_id, "entry_id"),
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
        if self.reuse_count < 0:
            raise ValueError("reuse_count must be greater than or equal to zero.")
        if self.candidate.skill_id != self.validation.candidate.skill_id:
            raise ValueError("Library entry candidate and validation must match.")
        if not self.evidence_ids:
            raise ValueError("Skill library entries require evidence ids.")

    @property
    def reusable(self) -> bool:
        """Return whether the entry may be reused without fail-closed block."""

        return self.validation.ready and not self.stale and not self.revoked

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic library-entry payload."""

        return {
            "candidate_fingerprint": self.candidate.fingerprint(),
            "entry_id": self.entry_id,
            "evidence_ids": list(self.evidence_ids),
            "reuse_count": self.reuse_count,
            "revoked": self.revoked,
            "review_required": self.review_required,
            "schema_version": self.schema_version,
            "stale": self.stale,
            "validation_fingerprint": self.validation.fingerprint(),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this library entry."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class SkillReusePlan:
    """Evidence-bound plan for reusing a skill against a bounded task."""

    plan_id: str
    entry: SkillLibraryEntry
    task: UnknownTaskInstance
    decision: SkillReuseDecision
    matched_transfer_tags: tuple[str, ...]
    matched_expected_operations: tuple[str, ...]
    findings: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_SKILL_REUSE_PLAN_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate reuse plan payload."""

        object.__setattr__(
            self,
            "plan_id",
            _require_non_empty(self.plan_id, "plan_id"),
        )
        object.__setattr__(
            self,
            "matched_transfer_tags",
            _dedupe_text_tuple(
                self.matched_transfer_tags, label="matched_transfer_tag"
            ),
        )
        object.__setattr__(
            self,
            "matched_expected_operations",
            _dedupe_text_tuple(
                self.matched_expected_operations,
                label="matched_expected_operation",
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
        if self.decision is not SkillReuseDecision.REUSE_READY and not self.findings:
            raise ValueError("Non-ready skill reuse plans require findings.")

    @property
    def ready(self) -> bool:
        """Return whether this skill reuse plan is ready."""

        return self.decision is SkillReuseDecision.REUSE_READY

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic reuse-plan payload."""

        return {
            "decision": self.decision.value,
            "entry_fingerprint": self.entry.fingerprint(),
            "findings": list(self.findings),
            "matched_expected_operations": list(self.matched_expected_operations),
            "matched_transfer_tags": list(self.matched_transfer_tags),
            "plan_id": self.plan_id,
            "schema_version": self.schema_version,
            "task_fingerprint": self.task.fingerprint(),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this reuse plan."""

        return _stable_sha256(self.canonical_payload())


def synthesize_skill_candidate(
    *,
    skill_id: str,
    name: str,
    purpose: str,
    trials: Iterable[TransferTrialRecord],
    evidence_ids: Iterable[str],
) -> SkillCandidate:
    """Synthesize a bounded skill candidate from transfer-trial evidence."""

    trial_tuple = tuple(trials)
    if not trial_tuple:
        raise ValueError("Skill synthesis requires transfer trials.")
    source_task_ids = tuple(trial.task.task_id for trial in trial_tuple)
    operation_ids = _dedupe_text_tuple(
        (
            _expected_operation_from_task(trial.task)
            for trial in trial_tuple
            if _expected_operation_from_task(trial.task)
        ),
        label="operation_id",
    )
    preconditions = _dedupe_text_tuple(
        (
            feature
            for trial in trial_tuple
            for feature in trial.task.initial_observation.visible_features
        ),
        label="precondition",
    )
    expected_effects = _dedupe_text_tuple(
        (feature for trial in trial_tuple for feature in trial.expected_feature_ids),
        label="expected_effect",
    )
    transfer_tags = _dedupe_text_tuple(
        (tag for trial in trial_tuple for tag in trial.task.transfer_tags),
        label="transfer_tag",
    )
    failure_modes = tuple(
        f"{trial.trial_id}:{trial.status.value}"
        for trial in trial_tuple
        if trial.status is not TransferTrialStatus.REPLAYABLE_PASS
    )
    combined_evidence = (
        *tuple(evidence_ids),
        *tuple(trial.fingerprint() for trial in trial_tuple),
    )
    return SkillCandidate(
        skill_id=skill_id,
        name=name,
        purpose=purpose,
        source_task_ids=source_task_ids,
        operation_ids=operation_ids,
        preconditions=preconditions,
        expected_effects=expected_effects,
        transfer_tags=transfer_tags,
        failure_modes=failure_modes,
        evidence_ids=combined_evidence,
    )


def validate_skill_candidate(
    *,
    validation_id: str,
    candidate: SkillCandidate,
    transfer_report: TransferChallengeReport,
) -> SkillValidationRecord:
    """Validate whether a skill candidate is ready for bounded reuse."""

    findings: list[str] = []
    if transfer_report.decision is not TransferClaimDecision.TRANSFER_DEMONSTRATED:
        findings.append(f"transfer-report-not-ready:{transfer_report.decision.value}")
    if transfer_report.blocked_count > 0:
        findings.append("blocked-transfer-trials-present")
    if candidate.failure_modes:
        findings.append("candidate-retains-failure-modes")
    if not _candidate_has_band(candidate, transfer_report, TransferBand.FAR):
        findings.append("missing-far-transfer-source")
    if not _candidate_has_band(candidate, transfer_report, TransferBand.HIDDEN):
        findings.append("missing-hidden-validation-source")
    if _candidate_contains_overclaim(candidate):
        findings.append("candidate-overclaims-scope")

    if "candidate-overclaims-scope" in findings:
        decision = SkillPromotionDecision.BLOCKED_BY_OVERCLAIM
    elif "blocked-transfer-trials-present" in findings:
        decision = SkillPromotionDecision.BLOCKED_BY_FAILURE
    elif any(finding.startswith("transfer-report-not-ready") for finding in findings):
        if transfer_report.decision is TransferClaimDecision.NEEDS_HIDDEN_VALIDATION:
            decision = SkillPromotionDecision.NEEDS_HIDDEN_VALIDATION
        elif (
            transfer_report.decision is TransferClaimDecision.NEEDS_REPLAYABLE_EVIDENCE
        ):
            decision = SkillPromotionDecision.NEEDS_REPLAYABLE_EVIDENCE
        else:
            decision = SkillPromotionDecision.NEEDS_TRANSFER_EVIDENCE
    elif "missing-hidden-validation-source" in findings:
        decision = SkillPromotionDecision.NEEDS_HIDDEN_VALIDATION
    elif "missing-far-transfer-source" in findings:
        decision = SkillPromotionDecision.NEEDS_TRANSFER_EVIDENCE
    else:
        decision = SkillPromotionDecision.READY_FOR_REUSE

    return SkillValidationRecord(
        validation_id=validation_id,
        candidate=candidate,
        transfer_report=transfer_report,
        decision=decision,
        findings=tuple(findings),
    )


def create_skill_library_entry(
    *,
    entry_id: str,
    validation: SkillValidationRecord,
    evidence_ids: Iterable[str],
    reuse_count: int = 0,
    stale: bool = False,
    revoked: bool = False,
    review_required: bool = False,
) -> SkillLibraryEntry:
    """Create a stored skill entry after validation."""

    return SkillLibraryEntry(
        entry_id=entry_id,
        candidate=validation.candidate,
        validation=validation,
        reuse_count=reuse_count,
        stale=stale,
        revoked=revoked,
        review_required=review_required,
        evidence_ids=tuple(evidence_ids),
    )


def plan_skill_reuse(
    *,
    plan_id: str,
    entry: SkillLibraryEntry,
    task: UnknownTaskInstance,
) -> SkillReusePlan:
    """Plan bounded skill reuse against a new task."""

    matched_tags = _intersection(entry.candidate.transfer_tags, task.transfer_tags)
    task_operations = tuple(
        feature.removeprefix("operation:")
        for feature in task.expected_outcome_features
        if feature.startswith("operation:")
    )
    matched_operations = _intersection(entry.candidate.operation_ids, task_operations)
    findings: list[str] = []
    if entry.revoked:
        findings.append("skill-entry-revoked")
        decision = SkillReuseDecision.BLOCKED_REVOKED
    elif entry.stale:
        findings.append("skill-entry-stale")
        decision = SkillReuseDecision.BLOCKED_STALE
    elif not entry.validation.ready:
        findings.append("skill-entry-not-validated")
        decision = SkillReuseDecision.BLOCKED_UNVALIDATED
    elif not matched_tags or not matched_operations:
        if not matched_tags:
            findings.append("missing-transfer-tag-alignment")
        if not matched_operations:
            findings.append("missing-operation-alignment")
        decision = SkillReuseDecision.NEEDS_TRANSFER_ALIGNMENT
    elif entry.review_required:
        findings.append("human-review-required-before-reuse")
        decision = SkillReuseDecision.NEEDS_HUMAN_REVIEW
    else:
        decision = SkillReuseDecision.REUSE_READY

    return SkillReusePlan(
        plan_id=plan_id,
        entry=entry,
        task=task,
        decision=decision,
        matched_transfer_tags=matched_tags,
        matched_expected_operations=matched_operations,
        findings=tuple(findings),
    )


def _candidate_has_band(
    candidate: SkillCandidate,
    transfer_report: TransferChallengeReport,
    band: TransferBand,
) -> bool:
    source_ids = set(candidate.source_task_ids)
    return any(
        trial.band is band
        and trial.task.task_id in source_ids
        and trial.status is TransferTrialStatus.REPLAYABLE_PASS
        for trial in transfer_report.trials
    )


def _candidate_contains_overclaim(candidate: SkillCandidate) -> bool:
    try:
        _reject_overclaiming_text(candidate.name, "name")
        _reject_overclaiming_text(candidate.purpose, "purpose")
    except ValueError:
        return True
    return False


def _expected_operation_from_task(task: UnknownTaskInstance) -> str:
    for feature in task.expected_outcome_features:
        if feature.startswith("operation:"):
            return feature.removeprefix("operation:")
    return ""


def _intersection(left: Iterable[str], right: Iterable[str]) -> tuple[str, ...]:
    right_set = set(right)
    return tuple(sorted({value for value in left if value in right_set}))


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
