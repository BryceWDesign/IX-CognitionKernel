"""Tests for Wave 8 evidence index."""

from __future__ import annotations

import pytest

from ix_cognition_kernel.wave8_evidence_index import (
    EvidenceArtifactKind,
    EvidenceIndexDecision,
    EvidenceIndexEntry,
    EvidenceIndexEntryStatus,
    Wave8EvidenceIndex,
    build_evidence_index,
    build_evidence_index_entry,
)


def _entry(
    *,
    entry_id: str,
    kind: EvidenceArtifactKind,
    status: EvidenceIndexEntryStatus = EvidenceIndexEntryStatus.READY,
) -> EvidenceIndexEntry:
    return build_evidence_index_entry(
        entry_id=entry_id,
        kind=kind,
        title=f"{kind.value} artifact",
        source_fingerprint="a" * 64,
        status=status,
        claim_boundary="Review evidence only; no certification.",
        evidence_ids=(f"evidence-{entry_id}",),
        findings=(() if status is EvidenceIndexEntryStatus.READY else ("blocked",)),
    )


def _ready_entries() -> tuple[EvidenceIndexEntry, ...]:
    return (
        _entry(
            entry_id="entry-task-suite",
            kind=EvidenceArtifactKind.TASK_SUITE,
        ),
        _entry(
            entry_id="entry-transfer-report",
            kind=EvidenceArtifactKind.TRANSFER_REPORT,
            status=EvidenceIndexEntryStatus.REVIEW_REQUIRED,
        ),
        _entry(
            entry_id="entry-baseline-report",
            kind=EvidenceArtifactKind.BASELINE_REPORT,
        ),
        _entry(
            entry_id="entry-replay-report",
            kind=EvidenceArtifactKind.REPLAY_REPORT,
        ),
        _entry(
            entry_id="entry-readiness-scorecard",
            kind=EvidenceArtifactKind.READINESS_SCORECARD,
        ),
        _entry(
            entry_id="entry-public-claim-assessment",
            kind=EvidenceArtifactKind.PUBLIC_CLAIM_ASSESSMENT,
        ),
        _entry(
            entry_id="entry-external-review-packet",
            kind=EvidenceArtifactKind.EXTERNAL_REVIEW_PACKET,
        ),
        _entry(
            entry_id="entry-falsification-matrix",
            kind=EvidenceArtifactKind.FALSIFICATION_MATRIX,
        ),
    )


def test_evidence_index_entry_ready_and_deterministic() -> None:
    entry = _entry(
        entry_id="entry-transfer-report",
        kind=EvidenceArtifactKind.TRANSFER_REPORT,
    )

    assert entry.ready
    assert not entry.blocked
    assert len(entry.fingerprint()) == 64


def test_evidence_index_entry_rejects_bad_fingerprint() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        build_evidence_index_entry(
            entry_id="entry-bad",
            kind=EvidenceArtifactKind.REPLAY_REPORT,
            title="Replay report",
            source_fingerprint="not-a-digest",
            status=EvidenceIndexEntryStatus.READY,
            claim_boundary="Review evidence only.",
            evidence_ids=("evidence-1",),
        )


def test_evidence_index_entry_requires_findings_when_blocked() -> None:
    with pytest.raises(ValueError, match="Non-ready evidence index entries"):
        build_evidence_index_entry(
            entry_id="entry-blocked",
            kind=EvidenceArtifactKind.REPLAY_REPORT,
            title="Replay report",
            source_fingerprint="a" * 64,
            status=EvidenceIndexEntryStatus.BLOCKED,
            claim_boundary="Review evidence only.",
            evidence_ids=("evidence-1",),
        )


def test_build_evidence_index_is_ready_with_required_artifacts() -> None:
    index = build_evidence_index(
        index_id="index-ready",
        purpose="Index bounded Wave 8 evidence for review.",
        claim_boundary="Review evidence only; no certification.",
        entries=_ready_entries(),
        evidence_ids=("index-evidence-1",),
    )

    assert index.decision is EvidenceIndexDecision.READY_FOR_REVIEW_QUERY
    assert index.ready_entry_count == 7
    assert index.blocked_entry_count == 0
    assert not index.findings


def test_evidence_index_detects_missing_required_artifacts() -> None:
    entries = _ready_entries()[:-1]
    index = build_evidence_index(
        index_id="index-missing",
        purpose="Index bounded Wave 8 evidence for review.",
        claim_boundary="Review evidence only; no certification.",
        entries=entries,
        evidence_ids=("index-evidence-1",),
    )

    assert index.decision is EvidenceIndexDecision.NEEDS_REQUIRED_ARTIFACTS
    assert any(
        finding.startswith("missing-required-artifacts")
        for finding in index.findings
    )


def test_evidence_index_blocks_blocked_entries() -> None:
    entries = (
        *_ready_entries(),
        _entry(
            entry_id="entry-blocked",
            kind=EvidenceArtifactKind.REPLAY_REPORT,
            status=EvidenceIndexEntryStatus.BLOCKED,
        ),
    )
    index = build_evidence_index(
        index_id="index-blocked",
        purpose="Index bounded Wave 8 evidence for review.",
        claim_boundary="Review evidence only; no certification.",
        entries=entries,
        evidence_ids=("index-evidence-1",),
    )

    assert index.decision is EvidenceIndexDecision.BLOCKED
    assert "blocked-evidence-index-entries:entry-blocked" in index.findings


def test_evidence_index_rejects_overclaiming_claim_boundary() -> None:
    with pytest.raises(ValueError, match="blocked overclaiming"):
        Wave8EvidenceIndex(
            index_id="index-overclaim",
            purpose="Index bounded evidence.",
            claim_boundary="Certifies AGI.",
            entries=_ready_entries(),
            decision=EvidenceIndexDecision.READY_FOR_REVIEW_QUERY,
            evidence_ids=("index-evidence-1",),
        )
