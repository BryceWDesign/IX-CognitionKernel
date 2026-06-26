"""Wave 8 readiness scorecard.

This module adds a deterministic readiness scorecard for the Recursive
Reality-Corrected Learner. It does not certify intelligence. It turns the
integrated trial, release manifest, replay readiness, transfer proof, baseline
comparison, world-model evidence, skill validation, and negative controls into
one bounded readiness report.

Scorecard doctrine:

- readiness is not AGI,
- scorecards cannot override gates,
- blocked negative controls fail the scorecard,
- transfer and baseline evidence are required,
- replay and external review readiness are required,
- missing human authority cannot be hidden behind a high score,
- public claims remain bounded to evidence reviewed by humans.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from ix_cognition_kernel.wave8_integrated_trial import IntegratedWave8TrialResult
from ix_cognition_kernel.wave8_negative_controls import (
    NegativeControlReport,
    NegativeControlSuiteDecision,
)

WAVE_EIGHT_READINESS_DIMENSION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-readiness-dimension-v1"
)
WAVE_EIGHT_READINESS_SCORECARD_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-readiness-scorecard-v1"
)


class ReadinessDimensionKind(StrEnum):
    """Wave 8 readiness dimensions."""

    EPISODE_REPLAY = "episode-replay"
    TRANSFER_GENERALIZATION = "transfer-generalization"
    SKILL_REUSE = "skill-reuse"
    WORLD_MODEL = "world-model"
    BASELINE_IMPROVEMENT = "baseline-improvement"
    REPLAY_VALIDATION = "replay-validation"
    EXTERNAL_REVIEW = "external-review"
    RELEASE_GATES = "release-gates"
    NEGATIVE_CONTROLS = "negative-controls"
    CLAIM_BOUNDARY = "claim-boundary"


class ReadinessDimensionDecision(StrEnum):
    """Decision for one readiness dimension."""

    PASS = "pass"
    WARN = "warn"
    BLOCK = "block"


class Wave8ReadinessDecision(StrEnum):
    """Overall Wave 8 readiness scorecard decision."""

    READY_FOR_REVIEW_HANDOFF = "ready-for-review-handoff"
    READY_WITH_WARNINGS = "ready-with-warnings"
    NEEDS_EVIDENCE = "needs-evidence"
    BLOCKED = "blocked"
    OVERCLAIM_BLOCKED = "overclaim-blocked"


@dataclass(frozen=True, slots=True)
class ReadinessDimensionRecord:
    """One evidence-bound readiness dimension."""

    dimension_id: str
    kind: ReadinessDimensionKind
    decision: ReadinessDimensionDecision
    score: int
    summary: str
    evidence_ids: tuple[str, ...]
    findings: tuple[str, ...] = ()
    schema_version: str = WAVE_EIGHT_READINESS_DIMENSION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate dimension score and evidence."""

        object.__setattr__(
            self,
            "dimension_id",
            _require_non_empty(self.dimension_id, "dimension_id"),
        )
        object.__setattr__(
            self,
            "summary",
            _require_non_empty(self.summary, "summary"),
        )
        _reject_overclaiming_text(self.summary, "summary")
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
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
        if self.score < 0 or self.score > 100:
            raise ValueError("Readiness dimension score must be between 0 and 100.")
        if not self.evidence_ids:
            raise ValueError("Readiness dimensions require evidence ids.")
        if self.decision is not ReadinessDimensionDecision.PASS and not self.findings:
            raise ValueError("Warned or blocked readiness dimensions require findings.")
        if self.decision is ReadinessDimensionDecision.BLOCK and self.score > 0:
            raise ValueError("Blocked readiness dimensions must have a zero score.")

    @property
    def passed(self) -> bool:
        """Return whether this dimension passed."""

        return self.decision is ReadinessDimensionDecision.PASS

    @property
    def warned(self) -> bool:
        """Return whether this dimension warns."""

        return self.decision is ReadinessDimensionDecision.WARN

    @property
    def blocked(self) -> bool:
        """Return whether this dimension blocks readiness."""

        return self.decision is ReadinessDimensionDecision.BLOCK

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic readiness-dimension payload."""

        return {
            "decision": self.decision.value,
            "dimension_id": self.dimension_id,
            "evidence_ids": list(self.evidence_ids),
            "findings": list(self.findings),
            "kind": self.kind.value,
            "schema_version": self.schema_version,
            "score": self.score,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this dimension."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class Wave8ReadinessScorecard:
    """Evidence-bound Wave 8 readiness scorecard."""

    scorecard_id: str
    purpose: str
    claim_boundary: str
    integrated_trial_fingerprint: str
    negative_control_report_fingerprint: str
    dimensions: tuple[ReadinessDimensionRecord, ...]
    decision: Wave8ReadinessDecision
    findings: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_READINESS_SCORECARD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate scorecard coverage and claim boundary."""

        object.__setattr__(
            self,
            "scorecard_id",
            _require_non_empty(self.scorecard_id, "scorecard_id"),
        )
        object.__setattr__(
            self,
            "purpose",
            _require_non_empty(self.purpose, "purpose"),
        )
        object.__setattr__(
            self,
            "claim_boundary",
            _require_non_empty(self.claim_boundary, "claim_boundary"),
        )
        _reject_overclaiming_text(self.purpose, "purpose")
        _reject_overclaiming_text(self.claim_boundary, "claim_boundary")
        object.__setattr__(
            self,
            "integrated_trial_fingerprint",
            _require_sha256(
                self.integrated_trial_fingerprint,
                "integrated_trial_fingerprint",
            ),
        )
        object.__setattr__(
            self,
            "negative_control_report_fingerprint",
            _require_sha256(
                self.negative_control_report_fingerprint,
                "negative_control_report_fingerprint",
            ),
        )
        object.__setattr__(
            self,
            "dimensions",
            tuple(self.dimensions),
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
        if not self.dimensions:
            raise ValueError("Wave 8 readiness scorecards require dimensions.")
        seen_ids: set[str] = set()
        for dimension in self.dimensions:
            if dimension.dimension_id in seen_ids:
                raise ValueError(f"Duplicate readiness dimension id: {dimension.dimension_id}")
            seen_ids.add(dimension.dimension_id)
        missing = _missing_required_dimensions(self.dimensions)
        if missing:
            raise ValueError(
                "Wave 8 readiness scorecards are missing dimensions: "
                f"{','.join(missing)}"
            )
        if self.decision is not Wave8ReadinessDecision.READY_FOR_REVIEW_HANDOFF:
            if not self.findings:
                raise ValueError("Non-ready scorecards require findings.")

    @property
    def ready(self) -> bool:
        """Return whether the scorecard is ready for review handoff."""

        return self.decision is Wave8ReadinessDecision.READY_FOR_REVIEW_HANDOFF

    @property
    def total_score(self) -> int:
        """Return aggregate readiness score across dimensions."""

        return sum(dimension.score for dimension in self.dimensions)

    @property
    def max_score(self) -> int:
        """Return maximum possible score."""

        return len(self.dimensions) * 100

    @property
    def normalized_score(self) -> float:
        """Return readiness score normalized from zero to one."""

        return self.total_score / self.max_score

    @property
    def blocked_dimension_count(self) -> int:
        """Return count of blocking readiness dimensions."""

        return sum(1 for dimension in self.dimensions if dimension.blocked)

    @property
    def warning_dimension_count(self) -> int:
        """Return count of warning readiness dimensions."""

        return sum(1 for dimension in self.dimensions if dimension.warned)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic scorecard payload."""

        return {
            "claim_boundary": self.claim_boundary,
            "decision": self.decision.value,
            "dimension_fingerprints": [
                dimension.fingerprint() for dimension in self.dimensions
            ],
            "findings": list(self.findings),
            "integrated_trial_fingerprint": self.integrated_trial_fingerprint,
            "negative_control_report_fingerprint": (
                self.negative_control_report_fingerprint
            ),
            "normalized_score": self.normalized_score,
            "purpose": self.purpose,
            "schema_version": self.schema_version,
            "scorecard_id": self.scorecard_id,
            "total_score": self.total_score,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this scorecard."""

        return _stable_sha256(self.canonical_payload())


def build_wave8_readiness_scorecard(
    *,
    scorecard_id: str,
    purpose: str,
    claim_boundary: str,
    integrated_trial: IntegratedWave8TrialResult,
    negative_control_report: NegativeControlReport,
) -> Wave8ReadinessScorecard:
    """Build a deterministic Wave 8 readiness scorecard."""

    dimensions = _dimension_records_from_evidence(
        integrated_trial=integrated_trial,
        negative_control_report=negative_control_report,
    )
    findings = _scorecard_findings(
        dimensions=dimensions,
        negative_control_report=negative_control_report,
    )
    decision = _scorecard_decision(
        dimensions=dimensions,
        negative_control_report=negative_control_report,
        findings=findings,
    )
    return Wave8ReadinessScorecard(
        scorecard_id=scorecard_id,
        purpose=purpose,
        claim_boundary=claim_boundary,
        integrated_trial_fingerprint=integrated_trial.fingerprint(),
        negative_control_report_fingerprint=negative_control_report.fingerprint(),
        dimensions=dimensions,
        decision=decision,
        findings=findings,
    )


def _dimension_records_from_evidence(
    *,
    integrated_trial: IntegratedWave8TrialResult,
    negative_control_report: NegativeControlReport,
) -> tuple[ReadinessDimensionRecord, ...]:
    return (
        _dimension(
            dimension_id="dimension-episode-replay",
            kind=ReadinessDimensionKind.EPISODE_REPLAY,
            passed=all(run.replayable for run in integrated_trial.runs),
            summary="Episode runs are replayable and measured.",
            evidence_ids=tuple(run.fingerprint() for run in integrated_trial.runs),
            failed_finding="episode-run-not-replayable",
        ),
        _dimension(
            dimension_id="dimension-transfer-generalization",
            kind=ReadinessDimensionKind.TRANSFER_GENERALIZATION,
            passed=integrated_trial.transfer_report.ready,
            summary="Transfer report demonstrates seed, near, far, adversarial, and hidden pressure.",
            evidence_ids=(integrated_trial.transfer_report.fingerprint(),),
            failed_finding="transfer-report-not-ready",
        ),
        _dimension(
            dimension_id="dimension-skill-reuse",
            kind=ReadinessDimensionKind.SKILL_REUSE,
            passed=integrated_trial.skill_validation.ready and integrated_trial.skill_entry.reusable,
            summary="Skill validation and reusable library entry are evidence-bound.",
            evidence_ids=(
                integrated_trial.skill_validation.fingerprint(),
                integrated_trial.skill_entry.fingerprint(),
            ),
            failed_finding="skill-reuse-not-ready",
        ),
        _dimension(
            dimension_id="dimension-world-model",
            kind=ReadinessDimensionKind.WORLD_MODEL,
            passed=bool(integrated_trial.world_snapshot.active_rules),
            summary="World-model snapshot contains active bounded rules.",
            evidence_ids=(integrated_trial.world_snapshot.fingerprint(),),
            failed_finding="world-model-not-ready",
        ),
        _dimension(
            dimension_id="dimension-baseline-improvement",
            kind=ReadinessDimensionKind.BASELINE_IMPROVEMENT,
            passed=integrated_trial.baseline_report.ready,
            summary="Candidate improvement is measured against model-alone baseline.",
            evidence_ids=(integrated_trial.baseline_report.fingerprint(),),
            failed_finding="baseline-improvement-not-ready",
        ),
        _dimension(
            dimension_id="dimension-replay-validation",
            kind=ReadinessDimensionKind.REPLAY_VALIDATION,
            passed=integrated_trial.replay_report.ready,
            summary="Replay packet is ready for review.",
            evidence_ids=(integrated_trial.replay_report.fingerprint(),),
            failed_finding="replay-validation-not-ready",
        ),
        _dimension(
            dimension_id="dimension-external-review",
            kind=ReadinessDimensionKind.EXTERNAL_REVIEW,
            passed=integrated_trial.external_review_packet.ready,
            summary="External review packet is ready.",
            evidence_ids=(integrated_trial.external_review_packet.fingerprint(),),
            failed_finding="external-review-not-ready",
        ),
        _dimension(
            dimension_id="dimension-release-gates",
            kind=ReadinessDimensionKind.RELEASE_GATES,
            passed=integrated_trial.release_manifest.ready,
            summary="Release manifest gates are ready for review handoff.",
            evidence_ids=(integrated_trial.release_manifest.fingerprint(),),
            failed_finding="release-gates-not-ready",
        ),
        _dimension(
            dimension_id="dimension-negative-controls",
            kind=ReadinessDimensionKind.NEGATIVE_CONTROLS,
            passed=negative_control_report.passed,
            summary="Required negative controls blocked as designed.",
            evidence_ids=(negative_control_report.fingerprint(),),
            failed_finding="negative-controls-not-ready",
        ),
        _dimension(
            dimension_id="dimension-claim-boundary",
            kind=ReadinessDimensionKind.CLAIM_BOUNDARY,
            passed=True,
            summary="Claim boundary remains review-only and non-certifying.",
            evidence_ids=(
                integrated_trial.release_manifest.fingerprint(),
                negative_control_report.fingerprint(),
            ),
            failed_finding="claim-boundary-not-ready",
        ),
    )


def _dimension(
    *,
    dimension_id: str,
    kind: ReadinessDimensionKind,
    passed: bool,
    summary: str,
    evidence_ids: tuple[str, ...],
    failed_finding: str,
) -> ReadinessDimensionRecord:
    return ReadinessDimensionRecord(
        dimension_id=dimension_id,
        kind=kind,
        decision=(
            ReadinessDimensionDecision.PASS
            if passed
            else ReadinessDimensionDecision.BLOCK
        ),
        score=100 if passed else 0,
        summary=summary,
        evidence_ids=evidence_ids,
        findings=() if passed else (failed_finding,),
    )


def _scorecard_findings(
    *,
    dimensions: tuple[ReadinessDimensionRecord, ...],
    negative_control_report: NegativeControlReport,
) -> tuple[str, ...]:
    findings: list[str] = []
    blocked = tuple(sorted(dimension.dimension_id for dimension in dimensions if dimension.blocked))
    warnings = tuple(sorted(dimension.dimension_id for dimension in dimensions if dimension.warned))
    if blocked:
        findings.append(f"blocked-readiness-dimensions:{','.join(blocked)}")
    if warnings:
        findings.append(f"warning-readiness-dimensions:{','.join(warnings)}")
    if negative_control_report.decision is NegativeControlSuiteDecision.FAILED_OPEN:
        findings.append("negative-controls-failed-open")
    if negative_control_report.decision is NegativeControlSuiteDecision.NEEDS_EVIDENCE:
        findings.append("negative-controls-need-evidence")
    return tuple(findings)


def _scorecard_decision(
    *,
    dimensions: tuple[ReadinessDimensionRecord, ...],
    negative_control_report: NegativeControlReport,
    findings: tuple[str, ...],
) -> Wave8ReadinessDecision:
    if "negative-controls-failed-open" in findings:
        return Wave8ReadinessDecision.BLOCKED
    if any(dimension.blocked for dimension in dimensions):
        return Wave8ReadinessDecision.BLOCKED
    if "negative-controls-need-evidence" in findings:
        return Wave8ReadinessDecision.NEEDS_EVIDENCE
    if any(dimension.warned for dimension in dimensions):
        return Wave8ReadinessDecision.READY_WITH_WARNINGS
    return Wave8ReadinessDecision.READY_FOR_REVIEW_HANDOFF


def _missing_required_dimensions(
    dimensions: Iterable[ReadinessDimensionRecord],
) -> tuple[str, ...]:
    required = {
        ReadinessDimensionKind.EPISODE_REPLAY,
        ReadinessDimensionKind.TRANSFER_GENERALIZATION,
        ReadinessDimensionKind.SKILL_REUSE,
        ReadinessDimensionKind.WORLD_MODEL,
        ReadinessDimensionKind.BASELINE_IMPROVEMENT,
        ReadinessDimensionKind.REPLAY_VALIDATION,
        ReadinessDimensionKind.EXTERNAL_REVIEW,
        ReadinessDimensionKind.RELEASE_GATES,
        ReadinessDimensionKind.NEGATIVE_CONTROLS,
        ReadinessDimensionKind.CLAIM_BOUNDARY,
    }
    present = {dimension.kind for dimension in dimensions}
    return tuple(sorted(kind.value for kind in required - present))


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


def _require_sha256(value: str, label: str) -> str:
    normalized = _require_non_empty(value, label)
    if len(normalized) != 64:
        raise ValueError(f"{label} must be a SHA-256 hex digest.")
    try:
        int(normalized, 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be a SHA-256 hex digest.") from exc
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
