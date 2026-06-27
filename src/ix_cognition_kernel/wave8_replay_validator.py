"""Wave 8 replay validator.

This module adds deterministic replay validation for the Recursive
Reality-Corrected Learner. It does not certify intelligence. It checks whether
the core Wave 8 evidence chain is replayable enough to support later review.

Replay doctrine:

- a claim without replay is not evidence,
- a passing episode without measured result is not learning,
- transfer, skill, world-model, and baseline records must be bound together,
- blocked artifacts remain visible,
- replay packets must reject AGI overclaim language,
- validation is a review gate, not self-certification.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from ix_cognition_kernel.wave8_baseline_comparison import (
    BaselineComparisonDecision,
    BaselineComparisonReport,
)
from ix_cognition_kernel.wave8_episode_runner import BoundedEpisodeRun, EpisodeRunStatus
from ix_cognition_kernel.wave8_skill_synthesis import (
    SkillPromotionDecision,
    SkillValidationRecord,
)
from ix_cognition_kernel.wave8_transfer_challenge import (
    TransferChallengeReport,
    TransferClaimDecision,
)
from ix_cognition_kernel.wave8_world_model import WorldModelSnapshot

WAVE_EIGHT_REPLAY_ARTIFACT_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-replay-artifact-v1"
)
WAVE_EIGHT_REPLAY_VALIDATION_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-replay-validation-v1"
)


class ReplayArtifactKind(StrEnum):
    """Kinds of artifacts in a Wave 8 replay packet."""

    EPISODE_RUN = "episode-run"
    TRANSFER_REPORT = "transfer-report"
    SKILL_VALIDATION = "skill-validation"
    WORLD_MODEL_SNAPSHOT = "world-model-snapshot"
    BASELINE_COMPARISON = "baseline-comparison"


class ReplayArtifactStatus(StrEnum):
    """Replay status for one artifact."""

    REPLAYABLE = "replayable"
    NEEDS_MEASURED_RESULT = "needs-measured-result"
    BLOCKED = "blocked"
    OVERCLAIM_BLOCKED = "overclaim-blocked"


class ReplayValidationDecision(StrEnum):
    """Replay-packet validation decision."""

    READY_FOR_REVIEW = "ready-for-review"
    NEEDS_MEASURED_RESULT = "needs-measured-result"
    NEEDS_REQUIRED_ARTIFACTS = "needs-required-artifacts"
    BLOCKED = "blocked"
    OVERCLAIM_BLOCKED = "overclaim-blocked"


@dataclass(frozen=True, slots=True)
class ReplayArtifactRecord:
    """One deterministic artifact record in a replay packet."""

    artifact_id: str
    kind: ReplayArtifactKind
    source_fingerprint: str
    status: ReplayArtifactStatus
    evidence_ids: tuple[str, ...]
    summary: str
    schema_version: str = WAVE_EIGHT_REPLAY_ARTIFACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate replay artifact payload."""

        object.__setattr__(
            self,
            "artifact_id",
            _require_non_empty(self.artifact_id, "artifact_id"),
        )
        object.__setattr__(
            self,
            "source_fingerprint",
            _require_sha256(self.source_fingerprint, "source_fingerprint"),
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "summary",
            _require_non_empty(self.summary, "summary"),
        )
        _reject_overclaiming_text(self.summary, "summary")
        object.__setattr__(
            self,
            "schema_version",
            _require_non_empty(self.schema_version, "schema_version"),
        )
        if not self.evidence_ids:
            raise ValueError("Replay artifacts require evidence ids.")

    @property
    def replayable(self) -> bool:
        """Return whether this artifact can support review."""

        return self.status is ReplayArtifactStatus.REPLAYABLE

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic replay-artifact payload."""

        return {
            "artifact_id": self.artifact_id,
            "evidence_ids": list(self.evidence_ids),
            "kind": self.kind.value,
            "schema_version": self.schema_version,
            "source_fingerprint": self.source_fingerprint,
            "status": self.status.value,
            "summary": self.summary,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this artifact."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class ReplayValidationReport:
    """Validation report for a Wave 8 replay packet."""

    report_id: str
    purpose: str
    artifacts: tuple[ReplayArtifactRecord, ...]
    decision: ReplayValidationDecision
    findings: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_REPLAY_VALIDATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate replay report coverage and findings."""

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
            "artifacts",
            tuple(self.artifacts),
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
        if not self.artifacts:
            raise ValueError("Replay validation reports require artifacts.")
        seen: set[str] = set()
        for artifact in self.artifacts:
            if artifact.artifact_id in seen:
                raise ValueError(f"Duplicate artifact_id: {artifact.artifact_id}")
            seen.add(artifact.artifact_id)
        if (
            self.decision is not ReplayValidationDecision.READY_FOR_REVIEW
            and not self.findings
        ):
            raise ValueError("Non-ready replay reports require findings.")

    @property
    def ready(self) -> bool:
        """Return whether the packet is ready for human/external review."""

        return self.decision is ReplayValidationDecision.READY_FOR_REVIEW

    @property
    def replayable_artifact_count(self) -> int:
        """Return count of replayable artifacts."""

        return sum(1 for artifact in self.artifacts if artifact.replayable)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic replay report payload."""

        return {
            "artifact_fingerprints": [
                artifact.fingerprint() for artifact in self.artifacts
            ],
            "decision": self.decision.value,
            "findings": list(self.findings),
            "purpose": self.purpose,
            "report_id": self.report_id,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this report."""

        return _stable_sha256(self.canonical_payload())


def artifact_from_episode_run(
    *,
    artifact_id: str,
    run: BoundedEpisodeRun,
    evidence_ids: Iterable[str],
) -> ReplayArtifactRecord:
    """Build a replay artifact from an episode run."""

    if run.status is EpisodeRunStatus.REPLAYABLE:
        status = ReplayArtifactStatus.REPLAYABLE
    elif run.status is EpisodeRunStatus.NEEDS_MEASURED_RESULT:
        status = ReplayArtifactStatus.NEEDS_MEASURED_RESULT
    else:
        status = ReplayArtifactStatus.BLOCKED
    return ReplayArtifactRecord(
        artifact_id=artifact_id,
        kind=ReplayArtifactKind.EPISODE_RUN,
        source_fingerprint=run.fingerprint(),
        status=status,
        evidence_ids=tuple(evidence_ids),
        summary=f"Episode run {run.run_id} status {run.status.value}.",
    )


def artifact_from_transfer_report(
    *,
    artifact_id: str,
    report: TransferChallengeReport,
    evidence_ids: Iterable[str],
) -> ReplayArtifactRecord:
    """Build a replay artifact from a transfer challenge report."""

    status = (
        ReplayArtifactStatus.REPLAYABLE
        if report.decision is TransferClaimDecision.TRANSFER_DEMONSTRATED
        else ReplayArtifactStatus.BLOCKED
    )
    return ReplayArtifactRecord(
        artifact_id=artifact_id,
        kind=ReplayArtifactKind.TRANSFER_REPORT,
        source_fingerprint=report.fingerprint(),
        status=status,
        evidence_ids=tuple(evidence_ids),
        summary=(
            f"Transfer report {report.report_id} decision {report.decision.value}."
        ),
    )


def artifact_from_skill_validation(
    *,
    artifact_id: str,
    validation: SkillValidationRecord,
    evidence_ids: Iterable[str],
) -> ReplayArtifactRecord:
    """Build a replay artifact from a skill validation record."""

    status = (
        ReplayArtifactStatus.REPLAYABLE
        if validation.decision is SkillPromotionDecision.READY_FOR_REUSE
        else ReplayArtifactStatus.BLOCKED
    )
    return ReplayArtifactRecord(
        artifact_id=artifact_id,
        kind=ReplayArtifactKind.SKILL_VALIDATION,
        source_fingerprint=validation.fingerprint(),
        status=status,
        evidence_ids=tuple(evidence_ids),
        summary=(
            f"Skill validation {validation.validation_id} decision "
            f"{validation.decision.value}."
        ),
    )


def artifact_from_world_snapshot(
    *,
    artifact_id: str,
    snapshot: WorldModelSnapshot,
    evidence_ids: Iterable[str],
) -> ReplayArtifactRecord:
    """Build a replay artifact from a world-model snapshot."""

    status = (
        ReplayArtifactStatus.REPLAYABLE
        if snapshot.active_rules
        else ReplayArtifactStatus.BLOCKED
    )
    return ReplayArtifactRecord(
        artifact_id=artifact_id,
        kind=ReplayArtifactKind.WORLD_MODEL_SNAPSHOT,
        source_fingerprint=snapshot.fingerprint(),
        status=status,
        evidence_ids=tuple(evidence_ids),
        summary=(
            f"World snapshot {snapshot.snapshot_id} active rules "
            f"{len(snapshot.active_rules)}."
        ),
    )


def artifact_from_baseline_report(
    *,
    artifact_id: str,
    report: BaselineComparisonReport,
    evidence_ids: Iterable[str],
) -> ReplayArtifactRecord:
    """Build a replay artifact from a baseline comparison report."""

    status = (
        ReplayArtifactStatus.REPLAYABLE
        if report.decision is BaselineComparisonDecision.IMPROVEMENT_DEMONSTRATED
        else ReplayArtifactStatus.BLOCKED
    )
    return ReplayArtifactRecord(
        artifact_id=artifact_id,
        kind=ReplayArtifactKind.BASELINE_COMPARISON,
        source_fingerprint=report.fingerprint(),
        status=status,
        evidence_ids=tuple(evidence_ids),
        summary=f"Baseline report {report.report_id} decision {report.decision.value}.",
    )


def validate_replay_packet(
    *,
    report_id: str,
    purpose: str,
    artifacts: Iterable[ReplayArtifactRecord],
) -> ReplayValidationReport:
    """Validate a Wave 8 replay packet across required artifact kinds."""

    artifact_tuple = tuple(artifacts)
    findings: list[str] = []
    kinds = {artifact.kind for artifact in artifact_tuple}
    required = {
        ReplayArtifactKind.EPISODE_RUN,
        ReplayArtifactKind.TRANSFER_REPORT,
        ReplayArtifactKind.SKILL_VALIDATION,
        ReplayArtifactKind.WORLD_MODEL_SNAPSHOT,
        ReplayArtifactKind.BASELINE_COMPARISON,
    }
    missing = tuple(sorted(kind.value for kind in required - kinds))
    if missing:
        findings.append(f"missing-required-artifacts:{','.join(missing)}")
    if any(
        artifact.status is ReplayArtifactStatus.OVERCLAIM_BLOCKED
        for artifact in artifact_tuple
    ):
        findings.append("overclaim-artifact-present")
    if any(
        artifact.status is ReplayArtifactStatus.BLOCKED for artifact in artifact_tuple
    ):
        findings.append("blocked-artifact-present")
    if any(
        artifact.status is ReplayArtifactStatus.NEEDS_MEASURED_RESULT
        for artifact in artifact_tuple
    ):
        findings.append("unmeasured-artifact-present")

    if "overclaim-artifact-present" in findings:
        decision = ReplayValidationDecision.OVERCLAIM_BLOCKED
    elif "blocked-artifact-present" in findings:
        decision = ReplayValidationDecision.BLOCKED
    elif "unmeasured-artifact-present" in findings:
        decision = ReplayValidationDecision.NEEDS_MEASURED_RESULT
    elif missing:
        decision = ReplayValidationDecision.NEEDS_REQUIRED_ARTIFACTS
    else:
        decision = ReplayValidationDecision.READY_FOR_REVIEW

    return ReplayValidationReport(
        report_id=report_id,
        purpose=purpose,
        artifacts=artifact_tuple,
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
