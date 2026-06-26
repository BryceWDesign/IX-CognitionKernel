"""Wave 8 baseline comparison.

This module adds the first model-alone versus kernel-assisted comparison surface
for the Recursive Reality-Corrected Learner. It does not allow the architecture
to claim intelligence merely because a task passed. A candidate must be compared
against a baseline on the same bounded tasks, with replayable evidence and clear
feature-level outcomes.

Baseline doctrine:

- the same task must be used for baseline and candidate comparison,
- model-alone success must not be credited to the kernel,
- kernel-assisted improvement must be measured, not asserted,
- blocked or unmeasured runs cannot support improvement claims,
- regression against baseline must remain visible,
- no comparison may certify AGI.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from ix_cognition_kernel.wave8_episode_runner import BoundedEpisodeRun, EpisodeRunStatus
from ix_cognition_kernel.wave8_task_suite import UnknownTaskInstance

WAVE_EIGHT_BASELINE_OUTCOME_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-baseline-outcome-v1"
)
WAVE_EIGHT_BASELINE_PAIR_SCHEMA_VERSION = "ix-cognition-kernel-wave8-baseline-pair-v1"
WAVE_EIGHT_BASELINE_REPORT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-baseline-report-v1"
)


class BaselineSystemKind(StrEnum):
    """System kind being compared on a bounded task."""

    MODEL_ALONE = "model-alone"
    PROMPT_SCAFFOLD = "prompt-scaffold"
    COGNITION_KERNEL = "cognition-kernel"
    COGNITION_KERNEL_WITH_INTENT_REALITY_LOOP = (
        "cognition-kernel-with-intent-reality-loop"
    )


class BaselineOutcomeStatus(StrEnum):
    """Outcome status for one system on one task."""

    REPLAYABLE_PASS = "replayable-pass"
    REPLAYABLE_FAIL = "replayable-fail"
    NEEDS_MEASURED_RESULT = "needs-measured-result"
    BLOCKED = "blocked"


class BaselineImprovementDecision(StrEnum):
    """Pairwise baseline comparison decision."""

    CANDIDATE_IMPROVED = "candidate-improved"
    CANDIDATE_TIED_BASELINE = "candidate-tied-baseline"
    CANDIDATE_REGRESSED = "candidate-regressed"
    NEEDS_REPLAYABLE_EVIDENCE = "needs-replayable-evidence"
    BLOCKED = "blocked"


class BaselineComparisonDecision(StrEnum):
    """Overall comparison report decision."""

    IMPROVEMENT_DEMONSTRATED = "improvement-demonstrated"
    MIXED_OR_TIED = "mixed-or-tied"
    REGRESSION_DETECTED = "regression-detected"
    NEEDS_MORE_TASKS = "needs-more-tasks"
    NEEDS_REPLAYABLE_EVIDENCE = "needs-replayable-evidence"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class BaselineOutcomeRecord:
    """One system outcome on one bounded task."""

    outcome_id: str
    system_kind: BaselineSystemKind
    task: UnknownTaskInstance
    run: BoundedEpisodeRun
    expected_feature_ids: tuple[str, ...]
    observed_feature_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_BASELINE_OUTCOME_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate baseline outcome identity and evidence."""

        object.__setattr__(
            self,
            "outcome_id",
            _require_non_empty(self.outcome_id, "outcome_id"),
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
            raise ValueError("Baseline outcomes require expected feature ids.")
        if not self.observed_feature_ids:
            raise ValueError("Baseline outcomes require observed feature ids.")
        if not self.evidence_ids:
            raise ValueError("Baseline outcomes require evidence ids.")

    @property
    def matched_expected_features(self) -> tuple[str, ...]:
        """Return expected features observed by this system."""

        observed = set(self.observed_feature_ids)
        return tuple(
            feature for feature in self.expected_feature_ids if feature in observed
        )

    @property
    def matched_feature_count(self) -> int:
        """Return count of matched expected features."""

        return len(self.matched_expected_features)

    @property
    def missed_feature_count(self) -> int:
        """Return count of expected features not observed."""

        return len(self.expected_feature_ids) - self.matched_feature_count

    @property
    def score(self) -> float:
        """Return normalized feature-match score."""

        return self.matched_feature_count / len(self.expected_feature_ids)

    @property
    def status(self) -> BaselineOutcomeStatus:
        """Return fail-closed baseline outcome status."""

        if self.run.status is EpisodeRunStatus.BLOCKED:
            return BaselineOutcomeStatus.BLOCKED
        if self.run.status is EpisodeRunStatus.NEEDS_MEASURED_RESULT:
            return BaselineOutcomeStatus.NEEDS_MEASURED_RESULT
        if self.missed_feature_count == 0:
            return BaselineOutcomeStatus.REPLAYABLE_PASS
        return BaselineOutcomeStatus.REPLAYABLE_FAIL

    @property
    def replayable(self) -> bool:
        """Return whether this outcome can support comparison."""

        return self.status in {
            BaselineOutcomeStatus.REPLAYABLE_PASS,
            BaselineOutcomeStatus.REPLAYABLE_FAIL,
        }

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic outcome payload."""

        return {
            "evidence_ids": list(self.evidence_ids),
            "expected_feature_ids": list(self.expected_feature_ids),
            "matched_expected_features": list(self.matched_expected_features),
            "observed_feature_ids": list(self.observed_feature_ids),
            "outcome_id": self.outcome_id,
            "run_fingerprint": self.run.fingerprint(),
            "schema_version": self.schema_version,
            "score": self.score,
            "status": self.status.value,
            "system_kind": self.system_kind.value,
            "task_fingerprint": self.task.fingerprint(),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this outcome."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class BaselineComparisonPair:
    """Pairwise baseline/candidate comparison for one task."""

    pair_id: str
    task: UnknownTaskInstance
    baseline: BaselineOutcomeRecord
    candidate: BaselineOutcomeRecord
    decision: BaselineImprovementDecision
    findings: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_BASELINE_PAIR_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate comparison pair consistency."""

        object.__setattr__(
            self,
            "pair_id",
            _require_non_empty(self.pair_id, "pair_id"),
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
        _require_same_text(
            self.task.task_id,
            self.baseline.task.task_id,
            "baseline_task_id",
        )
        _require_same_text(
            self.task.task_id,
            self.candidate.task.task_id,
            "candidate_task_id",
        )
        if self.baseline.system_kind is self.candidate.system_kind:
            raise ValueError("Baseline comparison pairs require distinct systems.")
        if (
            self.decision is not BaselineImprovementDecision.CANDIDATE_IMPROVED
            and not self.findings
        ):
            raise ValueError("Non-improved comparison pairs require findings.")

    @property
    def score_delta(self) -> float:
        """Return candidate score minus baseline score."""

        return self.candidate.score - self.baseline.score

    @property
    def improved(self) -> bool:
        """Return whether candidate improved against the baseline."""

        return self.decision is BaselineImprovementDecision.CANDIDATE_IMPROVED

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic pair payload."""

        return {
            "baseline_fingerprint": self.baseline.fingerprint(),
            "candidate_fingerprint": self.candidate.fingerprint(),
            "decision": self.decision.value,
            "findings": list(self.findings),
            "pair_id": self.pair_id,
            "schema_version": self.schema_version,
            "score_delta": self.score_delta,
            "task_fingerprint": self.task.fingerprint(),
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this pair."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class BaselineComparisonReport:
    """Evidence-bound report across multiple baseline/candidate pairs."""

    report_id: str
    purpose: str
    pairs: tuple[BaselineComparisonPair, ...]
    decision: BaselineComparisonDecision
    findings: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_BASELINE_REPORT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate baseline comparison report."""

        object.__setattr__(
            self,
            "report_id",
            _require_non_empty(self.report_id, "report_id"),
        )
        object.__setattr__(
            self,
            "purpose",
            _require_non_empty(self.purpose, "purpose"),
        )
        _reject_overclaiming_text(self.purpose, "purpose")
        object.__setattr__(
            self,
            "pairs",
            tuple(self.pairs),
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
        if not self.pairs:
            raise ValueError("Baseline comparison reports require pairs.")
        seen: set[str] = set()
        for pair in self.pairs:
            if pair.pair_id in seen:
                raise ValueError(f"Duplicate pair_id: {pair.pair_id}")
            seen.add(pair.pair_id)
        if (
            self.decision is not BaselineComparisonDecision.IMPROVEMENT_DEMONSTRATED
            and not self.findings
        ):
            raise ValueError("Non-improved reports require findings.")

    @property
    def improved_pair_count(self) -> int:
        """Return count of improved comparison pairs."""

        return sum(1 for pair in self.pairs if pair.improved)

    @property
    def regression_pair_count(self) -> int:
        """Return count of candidate regressions."""

        return sum(
            1
            for pair in self.pairs
            if pair.decision is BaselineImprovementDecision.CANDIDATE_REGRESSED
        )

    @property
    def ready(self) -> bool:
        """Return whether improvement was demonstrated."""

        return self.decision is BaselineComparisonDecision.IMPROVEMENT_DEMONSTRATED

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic report payload."""

        return {
            "decision": self.decision.value,
            "findings": list(self.findings),
            "pair_fingerprints": [pair.fingerprint() for pair in self.pairs],
            "purpose": self.purpose,
            "report_id": self.report_id,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this report."""

        return _stable_sha256(self.canonical_payload())


def build_baseline_outcome_record(
    *,
    outcome_id: str,
    system_kind: BaselineSystemKind,
    task: UnknownTaskInstance,
    run: BoundedEpisodeRun,
    observed_feature_ids: Iterable[str],
    evidence_ids: Iterable[str],
) -> BaselineOutcomeRecord:
    """Build one system outcome bound to a task and run."""

    return BaselineOutcomeRecord(
        outcome_id=outcome_id,
        system_kind=system_kind,
        task=task,
        run=run,
        expected_feature_ids=task.expected_outcome_features,
        observed_feature_ids=tuple(observed_feature_ids),
        evidence_ids=tuple(evidence_ids),
    )


def compare_baseline_pair(
    *,
    pair_id: str,
    baseline: BaselineOutcomeRecord,
    candidate: BaselineOutcomeRecord,
) -> BaselineComparisonPair:
    """Compare candidate outcome against baseline outcome on one task."""

    _require_same_text(
        baseline.task.task_id,
        candidate.task.task_id,
        "task_id",
    )
    findings: list[str] = []
    if not baseline.replayable or not candidate.replayable:
        if not baseline.replayable:
            findings.append(f"baseline-not-replayable:{baseline.status.value}")
        if not candidate.replayable:
            findings.append(f"candidate-not-replayable:{candidate.status.value}")
        if (
            baseline.status is BaselineOutcomeStatus.BLOCKED
            or candidate.status is BaselineOutcomeStatus.BLOCKED
        ):
            decision = BaselineImprovementDecision.BLOCKED
        else:
            decision = BaselineImprovementDecision.NEEDS_REPLAYABLE_EVIDENCE
    elif candidate.score > baseline.score:
        decision = BaselineImprovementDecision.CANDIDATE_IMPROVED
    elif candidate.score < baseline.score:
        findings.append("candidate-score-below-baseline")
        decision = BaselineImprovementDecision.CANDIDATE_REGRESSED
    else:
        findings.append("candidate-tied-baseline")
        decision = BaselineImprovementDecision.CANDIDATE_TIED_BASELINE

    return BaselineComparisonPair(
        pair_id=pair_id,
        task=baseline.task,
        baseline=baseline,
        candidate=candidate,
        decision=decision,
        findings=tuple(findings),
    )


def evaluate_baseline_comparison(
    *,
    report_id: str,
    purpose: str,
    pairs: Iterable[BaselineComparisonPair],
    minimum_pair_count: int = 2,
) -> BaselineComparisonReport:
    """Evaluate whether candidate improvement is demonstrated across pairs."""

    pair_tuple = tuple(pairs)
    findings: list[str] = []
    if len(pair_tuple) < minimum_pair_count:
        findings.append("insufficient-comparison-pair-count")
    if any(pair.decision is BaselineImprovementDecision.BLOCKED for pair in pair_tuple):
        findings.append("blocked-comparison-pair-present")
    if any(
        pair.decision is BaselineImprovementDecision.NEEDS_REPLAYABLE_EVIDENCE
        for pair in pair_tuple
    ):
        findings.append("unreplayable-comparison-pair-present")
    if any(
        pair.decision is BaselineImprovementDecision.CANDIDATE_REGRESSED
        for pair in pair_tuple
    ):
        findings.append("candidate-regression-present")
    if any(
        pair.decision is BaselineImprovementDecision.CANDIDATE_TIED_BASELINE
        for pair in pair_tuple
    ):
        findings.append("candidate-tie-present")
    if not any(pair.improved for pair in pair_tuple):
        findings.append("no-improved-comparison-pair")

    if "blocked-comparison-pair-present" in findings:
        decision = BaselineComparisonDecision.BLOCKED
    elif "unreplayable-comparison-pair-present" in findings:
        decision = BaselineComparisonDecision.NEEDS_REPLAYABLE_EVIDENCE
    elif "candidate-regression-present" in findings:
        decision = BaselineComparisonDecision.REGRESSION_DETECTED
    elif "insufficient-comparison-pair-count" in findings:
        decision = BaselineComparisonDecision.NEEDS_MORE_TASKS
    elif (
        "candidate-tie-present" in findings or "no-improved-comparison-pair" in findings
    ):
        decision = BaselineComparisonDecision.MIXED_OR_TIED
    else:
        decision = BaselineComparisonDecision.IMPROVEMENT_DEMONSTRATED

    return BaselineComparisonReport(
        report_id=report_id,
        purpose=purpose,
        pairs=pair_tuple,
        decision=decision,
        findings=tuple(findings),
    )


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


def _require_same_text(left: str, right: str, label: str) -> None:
    if left != right:
        raise ValueError(f"Mismatched {label}: {left} != {right}")


def _stable_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
