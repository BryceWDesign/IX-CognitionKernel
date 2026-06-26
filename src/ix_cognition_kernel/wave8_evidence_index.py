"""Wave 8 evidence index.

This module adds a deterministic evidence index for the Recursive
Reality-Corrected Learner. It does not certify intelligence. It makes the Wave 8
evidence chain searchable by artifact kind, fingerprint, source relationship,
claim boundary, and readiness status.

Evidence-index doctrine:

- an index is not proof by itself,
- fingerprints must bind every referenced artifact,
- missing or duplicate evidence fails closed,
- readiness must remain review-bound,
- negative controls must remain visible,
- scorecards cannot hide blocked artifacts,
- no indexed claim may certify AGI or broad competence.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from ix_cognition_kernel.wave8_integrated_trial import (
    IntegratedWave8TrialResult,
    is_replayable_run,
)
from ix_cognition_kernel.wave8_negative_controls import NegativeControlReport
from ix_cognition_kernel.wave8_readiness_scorecard import Wave8ReadinessScorecard

WAVE_EIGHT_EVIDENCE_INDEX_ENTRY_SCHEMA_VERSION = (
    "ix-cognition-kernel-wave8-evidence-index-entry-v1"
)
WAVE_EIGHT_EVIDENCE_INDEX_SCHEMA_VERSION = "ix-cognition-kernel-wave8-evidence-index-v1"


class EvidenceArtifactKind(StrEnum):
    """Kinds of indexed Wave 8 evidence artifacts."""

    TASK_SUITE = "task-suite"
    EPISODE_RUN = "episode-run"
    TRANSFER_REPORT = "transfer-report"
    SKILL_VALIDATION = "skill-validation"
    SKILL_LIBRARY_ENTRY = "skill-library-entry"
    WORLD_MODEL_SNAPSHOT = "world-model-snapshot"
    BASELINE_REPORT = "baseline-report"
    REPLAY_REPORT = "replay-report"
    EXTERNAL_REVIEW_PACKET = "external-review-packet"
    RELEASE_MANIFEST = "release-manifest"
    NEGATIVE_CONTROL_REPORT = "negative-control-report"
    READINESS_SCORECARD = "readiness-scorecard"
    EVIDENCE_INDEX = "evidence-index"


class EvidenceIndexEntryStatus(StrEnum):
    """Status for one indexed evidence artifact."""

    READY = "ready"
    REVIEW_BOUND = "review-bound"
    WARNING = "warning"
    BLOCKED = "blocked"


class EvidenceIndexDecision(StrEnum):
    """Overall evidence-index decision."""

    READY_FOR_REVIEW_QUERY = "ready-for-review-query"
    READY_WITH_WARNINGS = "ready-with-warnings"
    NEEDS_EVIDENCE = "needs-evidence"
    BLOCKED = "blocked"
    OVERCLAIM_BLOCKED = "overclaim-blocked"


@dataclass(frozen=True, slots=True)
class EvidenceIndexEntry:
    """One indexed Wave 8 evidence artifact."""

    entry_id: str
    kind: EvidenceArtifactKind
    title: str
    source_fingerprint: str
    status: EvidenceIndexEntryStatus
    claim_boundary: str
    evidence_ids: tuple[str, ...]
    parent_entry_ids: tuple[str, ...] = ()
    findings: tuple[str, ...] = ()
    schema_version: str = WAVE_EIGHT_EVIDENCE_INDEX_ENTRY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate indexed artifact payload."""

        object.__setattr__(
            self,
            "entry_id",
            _require_non_empty(self.entry_id, "entry_id"),
        )
        object.__setattr__(
            self,
            "title",
            _require_non_empty(self.title, "title"),
        )
        object.__setattr__(
            self,
            "source_fingerprint",
            _require_sha256(self.source_fingerprint, "source_fingerprint"),
        )
        object.__setattr__(
            self,
            "claim_boundary",
            _require_non_empty(self.claim_boundary, "claim_boundary"),
        )
        _reject_overclaiming_text(self.title, "title")
        _reject_overclaiming_text(self.claim_boundary, "claim_boundary")
        object.__setattr__(
            self,
            "evidence_ids",
            _normalize_unique_text_tuple(self.evidence_ids, label="evidence_id"),
        )
        object.__setattr__(
            self,
            "parent_entry_ids",
            _dedupe_text_tuple(self.parent_entry_ids, label="parent_entry_id"),
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
        if not self.evidence_ids:
            raise ValueError("Evidence index entries require evidence ids.")
        if self.status is not EvidenceIndexEntryStatus.READY and not self.findings:
            raise ValueError("Non-ready evidence index entries require findings.")

    @property
    def ready(self) -> bool:
        """Return whether the entry is ready for review query."""

        return self.status in {
            EvidenceIndexEntryStatus.READY,
            EvidenceIndexEntryStatus.REVIEW_BOUND,
        }

    @property
    def blocked(self) -> bool:
        """Return whether the entry blocks the index."""

        return self.status is EvidenceIndexEntryStatus.BLOCKED

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic index-entry payload."""

        return {
            "claim_boundary": self.claim_boundary,
            "entry_id": self.entry_id,
            "evidence_ids": list(self.evidence_ids),
            "findings": list(self.findings),
            "kind": self.kind.value,
            "parent_entry_ids": list(self.parent_entry_ids),
            "schema_version": self.schema_version,
            "source_fingerprint": self.source_fingerprint,
            "status": self.status.value,
            "title": self.title,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this index entry."""

        return _stable_sha256(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class Wave8EvidenceIndex:
    """Deterministic searchable index for Wave 8 review evidence."""

    index_id: str
    purpose: str
    claim_boundary: str
    entries: tuple[EvidenceIndexEntry, ...]
    decision: EvidenceIndexDecision
    findings: tuple[str, ...]
    schema_version: str = WAVE_EIGHT_EVIDENCE_INDEX_SCHEMA_VERSION

    def __post_init__(self) -> None:
        """Validate index coverage, relationships, and findings."""

        object.__setattr__(
            self,
            "index_id",
            _require_non_empty(self.index_id, "index_id"),
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
            "entries",
            tuple(self.entries),
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
        if not self.entries:
            raise ValueError("Wave 8 evidence indexes require entries.")
        seen_ids: set[str] = set()
        for entry in self.entries:
            if entry.entry_id in seen_ids:
                raise ValueError(f"Duplicate evidence index entry id: {entry.entry_id}")
            seen_ids.add(entry.entry_id)
        for entry in self.entries:
            for parent_id in entry.parent_entry_ids:
                if parent_id not in seen_ids:
                    raise ValueError(f"Unknown parent evidence entry id: {parent_id}")
        missing = _missing_required_kinds(self.entries)
        if missing:
            raise ValueError(
                "Wave 8 evidence indexes are missing artifact kinds: "
                f"{','.join(missing)}"
            )
        if (
            self.decision is not EvidenceIndexDecision.READY_FOR_REVIEW_QUERY
            and not self.findings
        ):
            raise ValueError("Non-ready evidence indexes require findings.")

    @property
    def ready(self) -> bool:
        """Return whether the index is ready for review query."""

        return self.decision is EvidenceIndexDecision.READY_FOR_REVIEW_QUERY

    @property
    def blocked_entry_count(self) -> int:
        """Return count of blocking entries."""

        return sum(1 for entry in self.entries if entry.blocked)

    @property
    def warning_entry_count(self) -> int:
        """Return count of warning entries."""

        return sum(
            1
            for entry in self.entries
            if entry.status is EvidenceIndexEntryStatus.WARNING
        )

    def entries_by_kind(
        self,
        kind: EvidenceArtifactKind,
    ) -> tuple[EvidenceIndexEntry, ...]:
        """Return all entries matching an artifact kind."""

        return tuple(entry for entry in self.entries if entry.kind is kind)

    def entry_by_id(self, entry_id: str) -> EvidenceIndexEntry:
        """Return one entry by id."""

        normalized = _require_non_empty(entry_id, "entry_id")
        for entry in self.entries:
            if entry.entry_id == normalized:
                return entry
        raise KeyError(normalized)

    def canonical_payload(self) -> dict[str, Any]:
        """Return deterministic evidence-index payload."""

        return {
            "claim_boundary": self.claim_boundary,
            "decision": self.decision.value,
            "entry_fingerprints": [entry.fingerprint() for entry in self.entries],
            "findings": list(self.findings),
            "index_id": self.index_id,
            "purpose": self.purpose,
            "schema_version": self.schema_version,
        }

    def fingerprint(self) -> str:
        """Return deterministic SHA-256 fingerprint for this index."""

        return _stable_sha256(self.canonical_payload())


def build_wave8_evidence_index(
    *,
    index_id: str,
    purpose: str,
    claim_boundary: str,
    integrated_trial: IntegratedWave8TrialResult,
    negative_control_report: NegativeControlReport,
    readiness_scorecard: Wave8ReadinessScorecard,
) -> Wave8EvidenceIndex:
    """Build a deterministic Wave 8 evidence index."""

    entries = _entries_from_wave8_evidence(
        integrated_trial=integrated_trial,
        negative_control_report=negative_control_report,
        readiness_scorecard=readiness_scorecard,
        claim_boundary=claim_boundary,
    )
    findings = _index_findings(entries=entries)
    decision = _index_decision(entries=entries, findings=findings)
    return Wave8EvidenceIndex(
        index_id=index_id,
        purpose=purpose,
        claim_boundary=claim_boundary,
        entries=entries,
        decision=decision,
        findings=findings,
    )


def _entries_from_wave8_evidence(
    *,
    integrated_trial: IntegratedWave8TrialResult,
    negative_control_report: NegativeControlReport,
    readiness_scorecard: Wave8ReadinessScorecard,
    claim_boundary: str,
) -> tuple[EvidenceIndexEntry, ...]:
    run_entries = tuple(
        EvidenceIndexEntry(
            entry_id=f"entry-run-{index}",
            kind=EvidenceArtifactKind.EPISODE_RUN,
            title=f"Replayable episode run {index}",
            source_fingerprint=run.fingerprint(),
            status=(
                EvidenceIndexEntryStatus.READY
                if is_replayable_run(run)
                else EvidenceIndexEntryStatus.BLOCKED
            ),
            claim_boundary=claim_boundary,
            evidence_ids=(run.fingerprint(),),
            parent_entry_ids=("entry-task-suite",),
            findings=() if is_replayable_run(run) else ("episode-run-not-replayable",),
        )
        for index, run in enumerate(integrated_trial.runs, start=1)
    )
    return (
        EvidenceIndexEntry(
            entry_id="entry-task-suite",
            kind=EvidenceArtifactKind.TASK_SUITE,
            title="Unknown task suite",
            source_fingerprint=integrated_trial.suite.fingerprint(),
            status=EvidenceIndexEntryStatus.READY,
            claim_boundary=claim_boundary,
            evidence_ids=(integrated_trial.task_validation_fingerprint,),
        ),
        *run_entries,
        EvidenceIndexEntry(
            entry_id="entry-transfer-report",
            kind=EvidenceArtifactKind.TRANSFER_REPORT,
            title="Transfer challenge report",
            source_fingerprint=integrated_trial.transfer_report.fingerprint(),
            status=_status_from_bool(integrated_trial.transfer_report.ready),
            claim_boundary=claim_boundary,
            evidence_ids=(integrated_trial.transfer_report.fingerprint(),),
            parent_entry_ids=tuple(entry.entry_id for entry in run_entries),
            findings=(
                ()
                if integrated_trial.transfer_report.ready
                else ("transfer-report-not-ready",)
            ),
        ),
        EvidenceIndexEntry(
            entry_id="entry-skill-validation",
            kind=EvidenceArtifactKind.SKILL_VALIDATION,
            title="Skill validation record",
            source_fingerprint=integrated_trial.skill_validation.fingerprint(),
            status=_status_from_bool(integrated_trial.skill_validation.ready),
            claim_boundary=claim_boundary,
            evidence_ids=(integrated_trial.skill_validation.fingerprint(),),
            parent_entry_ids=("entry-transfer-report",),
            findings=(
                ()
                if integrated_trial.skill_validation.ready
                else ("skill-validation-not-ready",)
            ),
        ),
        EvidenceIndexEntry(
            entry_id="entry-skill-library-entry",
            kind=EvidenceArtifactKind.SKILL_LIBRARY_ENTRY,
            title="Skill library entry",
            source_fingerprint=integrated_trial.skill_entry.fingerprint(),
            status=_status_from_bool(integrated_trial.skill_entry.reusable),
            claim_boundary=claim_boundary,
            evidence_ids=(integrated_trial.skill_entry.fingerprint(),),
            parent_entry_ids=("entry-skill-validation",),
            findings=(
                ()
                if integrated_trial.skill_entry.reusable
                else ("skill-entry-not-reusable",)
            ),
        ),
        EvidenceIndexEntry(
            entry_id="entry-world-model-snapshot",
            kind=EvidenceArtifactKind.WORLD_MODEL_SNAPSHOT,
            title="World-model snapshot",
            source_fingerprint=integrated_trial.world_snapshot.fingerprint(),
            status=_status_from_bool(
                bool(integrated_trial.world_snapshot.active_rules)
            ),
            claim_boundary=claim_boundary,
            evidence_ids=(integrated_trial.world_snapshot.fingerprint(),),
            parent_entry_ids=("entry-transfer-report",),
            findings=(
                ()
                if integrated_trial.world_snapshot.active_rules
                else ("world-model-not-ready",)
            ),
        ),
        EvidenceIndexEntry(
            entry_id="entry-baseline-report",
            kind=EvidenceArtifactKind.BASELINE_REPORT,
            title="Baseline comparison report",
            source_fingerprint=integrated_trial.baseline_report.fingerprint(),
            status=_status_from_bool(integrated_trial.baseline_report.ready),
            claim_boundary=claim_boundary,
            evidence_ids=(integrated_trial.baseline_report.fingerprint(),),
            parent_entry_ids=("entry-task-suite",),
            findings=(
                ()
                if integrated_trial.baseline_report.ready
                else ("baseline-report-not-ready",)
            ),
        ),
        EvidenceIndexEntry(
            entry_id="entry-replay-report",
            kind=EvidenceArtifactKind.REPLAY_REPORT,
            title="Replay validation report",
            source_fingerprint=integrated_trial.replay_report.fingerprint(),
            status=_status_from_bool(integrated_trial.replay_report.ready),
            claim_boundary=claim_boundary,
            evidence_ids=(integrated_trial.replay_report.fingerprint(),),
            parent_entry_ids=(
                "entry-transfer-report",
                "entry-skill-validation",
                "entry-world-model-snapshot",
                "entry-baseline-report",
            ),
            findings=(
                ()
                if integrated_trial.replay_report.ready
                else ("replay-report-not-ready",)
            ),
        ),
        EvidenceIndexEntry(
            entry_id="entry-external-review-packet",
            kind=EvidenceArtifactKind.EXTERNAL_REVIEW_PACKET,
            title="External review packet",
            source_fingerprint=integrated_trial.external_review_packet.fingerprint(),
            status=_status_from_bool(integrated_trial.external_review_packet.ready),
            claim_boundary=claim_boundary,
            evidence_ids=(integrated_trial.external_review_packet.fingerprint(),),
            parent_entry_ids=("entry-replay-report",),
            findings=(
                ()
                if integrated_trial.external_review_packet.ready
                else ("external-review-packet-not-ready",)
            ),
        ),
        EvidenceIndexEntry(
            entry_id="entry-release-manifest",
            kind=EvidenceArtifactKind.RELEASE_MANIFEST,
            title="Release manifest",
            source_fingerprint=integrated_trial.release_manifest.fingerprint(),
            status=_status_from_bool(integrated_trial.release_manifest.ready),
            claim_boundary=claim_boundary,
            evidence_ids=(integrated_trial.release_manifest.fingerprint(),),
            parent_entry_ids=("entry-external-review-packet",),
            findings=(
                ()
                if integrated_trial.release_manifest.ready
                else ("release-manifest-not-ready",)
            ),
        ),
        EvidenceIndexEntry(
            entry_id="entry-negative-control-report",
            kind=EvidenceArtifactKind.NEGATIVE_CONTROL_REPORT,
            title="Negative-control report",
            source_fingerprint=negative_control_report.fingerprint(),
            status=_status_from_bool(negative_control_report.passed),
            claim_boundary=claim_boundary,
            evidence_ids=(negative_control_report.fingerprint(),),
            findings=(
                ()
                if negative_control_report.passed
                else ("negative-control-report-not-ready",)
            ),
        ),
        EvidenceIndexEntry(
            entry_id="entry-readiness-scorecard",
            kind=EvidenceArtifactKind.READINESS_SCORECARD,
            title="Readiness scorecard",
            source_fingerprint=readiness_scorecard.fingerprint(),
            status=_status_from_bool(readiness_scorecard.ready),
            claim_boundary=claim_boundary,
            evidence_ids=(readiness_scorecard.fingerprint(),),
            parent_entry_ids=(
                "entry-release-manifest",
                "entry-negative-control-report",
            ),
            findings=(
                () if readiness_scorecard.ready else ("readiness-scorecard-not-ready",)
            ),
        ),
    )


def _status_from_bool(ready: bool) -> EvidenceIndexEntryStatus:
    return EvidenceIndexEntryStatus.READY if ready else EvidenceIndexEntryStatus.BLOCKED


def _index_findings(entries: tuple[EvidenceIndexEntry, ...]) -> tuple[str, ...]:
    findings: list[str] = []
    blocked_ids = tuple(sorted(entry.entry_id for entry in entries if entry.blocked))
    warning_ids = tuple(
        sorted(
            entry.entry_id
            for entry in entries
            if entry.status is EvidenceIndexEntryStatus.WARNING
        )
    )
    if blocked_ids:
        findings.append(f"blocked-evidence-index-entries:{','.join(blocked_ids)}")
    if warning_ids:
        findings.append(f"warning-evidence-index-entries:{','.join(warning_ids)}")
    return tuple(findings)


def _index_decision(
    *,
    entries: tuple[EvidenceIndexEntry, ...],
    findings: tuple[str, ...],
) -> EvidenceIndexDecision:
    if any(entry.blocked for entry in entries):
        return EvidenceIndexDecision.BLOCKED
    if any(entry.status is EvidenceIndexEntryStatus.WARNING for entry in entries):
        return EvidenceIndexDecision.READY_WITH_WARNINGS
    if findings:
        return EvidenceIndexDecision.NEEDS_EVIDENCE
    return EvidenceIndexDecision.READY_FOR_REVIEW_QUERY


def _missing_required_kinds(entries: Iterable[EvidenceIndexEntry]) -> tuple[str, ...]:
    required = {
        EvidenceArtifactKind.TASK_SUITE,
        EvidenceArtifactKind.EPISODE_RUN,
        EvidenceArtifactKind.TRANSFER_REPORT,
        EvidenceArtifactKind.SKILL_VALIDATION,
        EvidenceArtifactKind.SKILL_LIBRARY_ENTRY,
        EvidenceArtifactKind.WORLD_MODEL_SNAPSHOT,
        EvidenceArtifactKind.BASELINE_REPORT,
        EvidenceArtifactKind.REPLAY_REPORT,
        EvidenceArtifactKind.EXTERNAL_REVIEW_PACKET,
        EvidenceArtifactKind.RELEASE_MANIFEST,
        EvidenceArtifactKind.NEGATIVE_CONTROL_REPORT,
        EvidenceArtifactKind.READINESS_SCORECARD,
    }
    present = {entry.kind for entry in entries}
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
