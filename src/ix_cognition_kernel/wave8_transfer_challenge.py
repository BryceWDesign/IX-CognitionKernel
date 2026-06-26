"""Wave 8 transfer challenge evaluation.

This module adds the first transfer/generalization proof surface for the
Recursive Reality-Corrected Learner. It does not treat original-task success as
general intelligence. It requires replayable evidence across seed, transfer,
adversarial, and hidden-validation task pressure before a transfer claim can be
promoted.

Transfer doctrine:

- original-task success is not generalization,
- near transfer is weaker than far transfer,
- hidden validation must be separated from seed replay,
- blocked and unmeasured runs must remain visible evidence,
- a transfer claim requires replayable runs bound to task fingerprints,
- no report may certify AGI.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from ix_cognition_kernel.wave8_episode_runner import BoundedEpisodeRun, EpisodeRunStatus
from ix_cognition_kernel.wave8_task_suite import (
    TaskDifficulty,
    UnknownTaskInstance,
    UnknownTaskSuite,
)

WAVE_EIGHT_TRANSFER_TRIAL_SCHEMA_VERSION = "ix-cognition-kernel-wave8-transfer-trial-v1"
WAVE_EIGHT_TRANSFER_REPORT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-transfer-report-v1"
)


class TransferBand(StrEnum):
    """Transfer band assigned to a task trial."""

    SEED = "seed"
    NEAR = "near"
    FAR = "far"
    ADVERSARIAL = "adversarial"
    HIDDEN = "hidden"


class TransferTrialStatus(StrEnum):
    """Outcome status for a transfer trial."""

    REPLAYABLE_PASS = "replayable-pass"
    REPLAYABLE_FAIL = "replayable-fail"
    NEEDS_MEASURED_RESULT = "needs-measured-result"
    BLOCKED = "blocked"


class TransferClaimDecision(StrEnum):
    """Fail-closed decision for a transfer challenge report."""

    TRANSFER_DEMONSTRATED = "transfer-demonstrated"
    ORIGINAL_TASK_ONLY = "original-task-only"
    NEEDS_HIDDEN_VALIDATION = "needs-hidden-validation"
    NEEDS_FAR_TRANSFER = "needs-far-transfer"
    NEEDS_REPLAYABLE_EVIDENCE = "needs-replayable-evidence"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class TransferTrialRecord:
    """One task/run binding inside a transfer challenge."""

    trial_id: str
    task: UnknownTaskInstance
    run: BoundedEpisodeRun
    expected_feature_ids: tuple[str, ...]
    observed_feature_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_TRANSFER_TRIAL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate task/run identity and evidence."""

        object.__setattr__(
            self,
            "trial_id",
            _require_non_empty(self.trial_id, "trial_id"),
        )
        object.__setattr__(
            self,
            "expected_feature_ids",
            _normalize_unique_text_tuple(
                self.expected_feature_ids,
                label="expected_feature_id",
            ),
        )
        object.__setattr__(
            self,
            "observed_feature_ids",
            _normalize_unique_text_tuple(
                self.observed_feature_ids,
                label="observed_feature_id",
            ),
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
        _require_same_text(
            self.task.environment.environment_id,
            self.run.environment.environment_id,
            "environment_id",
        )
        _require_same_text(
            self.task.initial_observation.episode_id,
            self.run.episode_id,
            "episode_id",
        )
        if not self.expected_feature_ids:
            raise ValueError("Transfer trials require expected feature ids.")
        if not self.observed_feature_ids:
            raise ValueError("Transfer trials require observed feature ids.")
        if not self.evidence_ids:
            raise ValueError("Transfer trials require evidence ids.")

    @property
    def band(self) -> TransferBand:
        """Return transfer band for this trial."""

        if self.task.difficulty is TaskDifficulty.SEED:
            return TransferBand.SEED
        if self.task.difficulty is TaskDifficulty.NEAR_TRANSFER:
            return TransferBand.NEAR
        if self.task.difficulty is TaskDifficulty.FAR_TRANSFER:
            return TransferBand.FAR
        if self.task.difficulty is TaskDifficulty.ADVERSARIAL:
            return TransferBand.ADVERSARIAL
        return TransferBand.HIDDEN

    @property
    def matched_expected_features(self) -> tuple[str, ...]:
        """Return expected features observed in the measured outcome."""

        observed = set(self.observed_feature_ids)
        return tuple(
            feature_id
            for feature_id in self.expected_feature_ids
            if feature_id in observed
        )

    @property
    def passed(self) -> bool:
        """Return whether expected features were observed."""

        return len(self.matched_expected_features) == len(self.expected_feature_ids)

    @property
    def status(self) -> TransferTrialStatus:
        """Return fail-closed transfer-trial status."""

        if self.run.status is EpisodeRunStatus.BLOCKED:
            return TransferTrialStatus.BLOCKED
        if self.run.status is EpisodeRunStatus.NEEDS_MEASURED_RESULT:
            return TransferTrialStatus.NEEDS_MEASURED_RESULT
        if self.passed:
            return TransferTrialStatus.REPLAYABLE_PASS
        return TransferTrialStatus.REPLAYABLE_FAIL

    @property
    def replayable_pass(self) -> bool:
        """Return whether the trial can support transfer promotion."""

        return self.status is TransferTrialStatus.REPLAYABLE_PASS

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic transfer-trial payload."""

        return {
            "band": self.band.value,
            "evidence_ids": list(self.evidence_ids),
            "expected_feature_ids": list(self.expected_feature_ids),
            "matched_expected_features": list(self.matched_expected_features),
            "observed_feature_ids": list(self.observed_feature_ids),
            "run_fingerprint": self.run.fingerprint(),
            "schema_version": self.schema_version,
            "status": self.status.value,
            "task_fingerprint": self.task.fingerprint(),
            "trial_id": self.trial_id,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this trial."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class TransferChallengeReport:
    """Evidence-bound report for transfer/generalization pressure."""

    report_id: str
    suite: UnknownTaskSuite
    trials: tuple[TransferTrialRecord, ...]
    decision: TransferClaimDecision
    findings: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_TRANSFER_REPORT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate report shape and task coverage."""

        object.__setattr__(
            self,
            "report_id",
            _require_non_empty(self.report_id, "report_id"),
        )
        object.__setattr__(
            self,
            "trials",
            tuple(self.trials),
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
        if not self.trials:
            raise ValueError("Transfer challenge reports require trials.")
        suite_task_ids = {task.task_id for task in self.suite.tasks}
        seen_trial_ids: set[str] = set()
        for trial in self.trials:
            if trial.trial_id in seen_trial_ids:
                raise ValueError(f"Duplicate trial_id: {trial.trial_id}")
            seen_trial_ids.add(trial.trial_id)
            if trial.task.task_id not in suite_task_ids:
                raise ValueError(f"Trial task is not in suite: {trial.task.task_id}")
        if (
            self.decision is not TransferClaimDecision.TRANSFER_DEMONSTRATED
            and not self.findings
        ):
            raise ValueError("Non-demonstrated transfer reports require findings.")

    @property
    def ready(self) -> bool:
        """Return whether transfer was demonstrated under Wave 8 rules."""

        return self.decision is TransferClaimDecision.TRANSFER_DEMONSTRATED

    @property
    def replayable_pass_count(self) -> int:
        """Return replayable passing trial count."""

        return sum(1 for trial in self.trials if trial.replayable_pass)

    @property
    def blocked_count(self) -> int:
        """Return blocked trial count."""

        return sum(
            1 for trial in self.trials if trial.status is TransferTrialStatus.BLOCKED
        )

    def pass_count_for_band(self, band: TransferBand) -> int:
        """Return replayable passing count for a transfer band."""

        return sum(
            1 for trial in self.trials if trial.band is band and trial.replayable_pass
        )

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic transfer report payload."""

        return {
            "decision": self.decision.value,
            "findings": list(self.findings),
            "report_id": self.report_id,
            "schema_version": self.schema_version,
            "suite_fingerprint": self.suite.fingerprint(),
            "trial_fingerprints": [trial.fingerprint() for trial in self.trials],
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this report."""

        return _stable_sha256(self.canonical_payload())


def build_transfer_trial_record(
    *,
    trial_id: str,
    task: UnknownTaskInstance,
    run: BoundedEpisodeRun,
    observed_feature_ids: Iterable[str],
    evidence_ids: Iterable[str],
) -> TransferTrialRecord:
    """Build a task/run transfer-trial record."""

    return TransferTrialRecord(
        trial_id=trial_id,
        task=task,
        run=run,
        expected_feature_ids=task.expected_outcome_features,
        observed_feature_ids=tuple(observed_feature_ids),
        evidence_ids=tuple(evidence_ids),
    )


def evaluate_transfer_challenge(
    *,
    report_id: str,
    suite: UnknownTaskSuite,
    trials: Iterable[TransferTrialRecord],
) -> TransferChallengeReport:
    """Evaluate transfer/generalization without promoting weak claims."""

    trial_tuple = tuple(trials)
    findings: list[str] = []
    trial_task_ids = {trial.task.task_id for trial in trial_tuple}
    suite_task_ids = {task.task_id for task in suite.tasks}

    if trial_task_ids != suite_task_ids:
        missing = tuple(sorted(suite_task_ids - trial_task_ids))
        extra = tuple(sorted(trial_task_ids - suite_task_ids))
        if missing:
            findings.append(f"missing-suite-task-trials:{','.join(missing)}")
        if extra:
            findings.append(f"trials-outside-suite:{','.join(extra)}")

    if any(trial.status is TransferTrialStatus.BLOCKED for trial in trial_tuple):
        findings.append("blocked-transfer-trial-present")
    if any(
        trial.status is TransferTrialStatus.NEEDS_MEASURED_RESULT
        for trial in trial_tuple
    ):
        findings.append("unmeasured-transfer-trial-present")

    seed_passes = _pass_count_for_band(trial_tuple, TransferBand.SEED)
    near_passes = _pass_count_for_band(trial_tuple, TransferBand.NEAR)
    far_passes = _pass_count_for_band(trial_tuple, TransferBand.FAR)
    adversarial_passes = _pass_count_for_band(trial_tuple, TransferBand.ADVERSARIAL)
    hidden_passes = _pass_count_for_band(trial_tuple, TransferBand.HIDDEN)

    if seed_passes == 0:
        findings.append("missing-seed-replayable-pass")
    if near_passes == 0:
        findings.append("missing-near-transfer-pass")
    if far_passes == 0:
        findings.append("missing-far-transfer-pass")
    if adversarial_passes == 0:
        findings.append("missing-adversarial-transfer-pass")
    if hidden_passes == 0:
        findings.append("missing-hidden-validation-pass")

    decision = _decision_from_findings(findings=findings)

    return TransferChallengeReport(
        report_id=report_id,
        suite=suite,
        trials=trial_tuple,
        decision=decision,
        findings=tuple(findings),
    )


def _decision_from_findings(*, findings: list[str]) -> TransferClaimDecision:
    if any(
        finding.startswith("missing-suite-task-trials")
        or finding.startswith("trials-outside-suite")
        or finding == "blocked-transfer-trial-present"
        for finding in findings
    ):
        return TransferClaimDecision.BLOCKED
    if "unmeasured-transfer-trial-present" in findings:
        return TransferClaimDecision.NEEDS_REPLAYABLE_EVIDENCE
    if "missing-hidden-validation-pass" in findings:
        return TransferClaimDecision.NEEDS_HIDDEN_VALIDATION
    if "missing-far-transfer-pass" in findings:
        return TransferClaimDecision.NEEDS_FAR_TRANSFER
    if (
        "missing-near-transfer-pass" in findings
        or "missing-adversarial-transfer-pass" in findings
    ):
        return TransferClaimDecision.ORIGINAL_TASK_ONLY
    if "missing-seed-replayable-pass" in findings:
        return TransferClaimDecision.NEEDS_REPLAYABLE_EVIDENCE
    return TransferClaimDecision.TRANSFER_DEMONSTRATED


def _pass_count_for_band(
    trials: Iterable[TransferTrialRecord], band: TransferBand
) -> int:
    return sum(1 for trial in trials if trial.band is band and trial.replayable_pass)


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


def _require_same_text(left: str, right: str, label: str) -> None:
    if left != right:
        raise ValueError(f"Mismatched {label}: {left} != {right}")


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
