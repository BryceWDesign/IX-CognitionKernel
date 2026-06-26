import pytest

from ix_cognition_kernel.wave8_evidence_index import (
    EvidenceArtifactKind,
    EvidenceIndexDecision,
    EvidenceIndexEntry,
    EvidenceIndexEntryStatus,
    Wave8EvidenceIndex,
    build_wave8_evidence_index,
)
from ix_cognition_kernel.wave8_integrated_trial import build_integrated_wave8_trial
from ix_cognition_kernel.wave8_negative_controls import (
    build_negative_control_report,
    default_wave8_negative_control_records,
)
from ix_cognition_kernel.wave8_readiness_scorecard import (
    build_wave8_readiness_scorecard,
)


def _integrated_trial():
    return build_integrated_wave8_trial(
        trial_id="evidence-index-integrated-trial",
        human_authority_evidence_ids=("human-authority-evidence-1",),
    )


def _negative_control_report():
    return build_negative_control_report(
        report_id="negative-control-report-1",
        purpose="Validate Wave 8 fail-closed behavior without certification.",
        records=default_wave8_negative_control_records(),
    )


def _scorecard():
    integrated = _integrated_trial()
    negative_report = _negative_control_report()
    return integrated, negative_report, build_wave8_readiness_scorecard(
        scorecard_id="scorecard-1",
        purpose="Score bounded Wave 8 readiness for review handoff.",
        claim_boundary="Readiness score only; no certification.",
        integrated_trial=integrated,
        negative_control_report=negative_report,
    )


def test_wave8_evidence_index_ready_for_review_query() -> None:
    integrated, negative_report, scorecard = _scorecard()
    index = build_wave8_evidence_index(
        index_id="evidence-index-1",
        purpose="Index bounded Wave 8 evidence for review query.",
        claim_boundary="Evidence index only; no certification.",
        integrated_trial=integrated,
        negative_control_report=negative_report,
        readiness_scorecard=scorecard,
    )

    assert index.ready
    assert index.decision is EvidenceIndexDecision.READY_FOR_REVIEW_QUERY
    assert index.blocked_entry_count == 0
    assert index.warning_entry_count == 0
    assert index.findings == ()
    assert len(index.entries_by_kind(EvidenceArtifactKind.EPISODE_RUN)) == 5
    assert index.entry_by_id("entry-readiness-scorecard").ready
    assert index.fingerprint() == index.fingerprint()
    assert len(index.fingerprint()) == 64


def test_wave8_evidence_index_preserves_parent_relationships() -> None:
    integrated, negative_report, scorecard = _scorecard()
    index = build_wave8_evidence_index(
        index_id="evidence-index-parent-links",
        purpose="Index bounded Wave 8 evidence for review query.",
        claim_boundary="Evidence index only; no certification.",
        integrated_trial=integrated,
        negative_control_report=negative_report,
        readiness_scorecard=scorecard,
    )

    replay_entry = index.entry_by_id("entry-replay-report")
    scorecard_entry = index.entry_by_id("entry-readiness-scorecard")

    assert "entry-transfer-report" in replay_entry.parent_entry_ids
    assert "entry-baseline-report" in replay_entry.parent_entry_ids
    assert "entry-release-manifest" in scorecard_entry.parent_entry_ids
    assert "entry-negative-control-report" in scorecard_entry.parent_entry_ids


def test_evidence_index_rejects_unknown_parent_entry_id() -> None:
    integrated, negative_report, scorecard = _scorecard()
    index = build_wave8_evidence_index(
        index_id="evidence-index-good",
        purpose="Index bounded Wave 8 evidence for review query.",
        claim_boundary="Evidence index only; no certification.",
        integrated_trial=integrated,
        negative_control_report=negative_report,
        readiness_scorecard=scorecard,
    )
    bad_entries = list(index.entries)
    bad_entries[-1] = EvidenceIndexEntry(
        entry_id="entry-readiness-scorecard",
        kind=EvidenceArtifactKind.READINESS_SCORECARD,
        title="Readiness scorecard",
        source_fingerprint=scorecard.fingerprint(),
        status=EvidenceIndexEntryStatus.READY,
        claim_boundary="Evidence index only; no certification.",
        evidence_ids=(scorecard.fingerprint(),),
        parent_entry_ids=("missing-parent",),
    )

    with pytest.raises(ValueError, match="Unknown parent evidence entry id"):
        Wave8EvidenceIndex(
            index_id="evidence-index-bad-parent",
            purpose="Index bounded Wave 8 evidence for review query.",
            claim_boundary="Evidence index only; no certification.",
            entries=tuple(bad_entries),
            decision=EvidenceIndexDecision.READY_FOR_REVIEW_QUERY,
            findings=(),
        )


def test_evidence_index_blocks_non_ready_entry() -> None:
    integrated, negative_report, scorecard = _scorecard()
    index = build_wave8_evidence_index(
        index_id="evidence-index-good",
        purpose="Index bounded Wave 8 evidence for review query.",
        claim_boundary="Evidence index only; no certification.",
        integrated_trial=integrated,
        negative_control_report=negative_report,
        readiness_scorecard=scorecard,
    )
    bad_entries = list(index.entries)
    task_suite = bad_entries[0]
    bad_entries[0] = EvidenceIndexEntry(
        entry_id=task_suite.entry_id,
        kind=task_suite.kind,
        title=task_suite.title,
        source_fingerprint=task_suite.source_fingerprint,
        status=EvidenceIndexEntryStatus.BLOCKED,
        claim_boundary=task_suite.claim_boundary,
        evidence_ids=task_suite.evidence_ids,
        findings=("task-suite-blocked",),
    )
    blocked_index = Wave8EvidenceIndex(
        index_id="evidence-index-blocked",
        purpose="Index bounded Wave 8 evidence for review query.",
        claim_boundary="Evidence index only; no certification.",
        entries=tuple(bad_entries),
        decision=EvidenceIndexDecision.BLOCKED,
        findings=("blocked-evidence-index-entries:entry-task-suite",),
    )

    assert not blocked_index.ready
    assert blocked_index.blocked_entry_count == 1


def test_evidence_index_rejects_missing_required_artifact_kind() -> None:
    integrated, negative_report, scorecard = _scorecard()
    index = build_wave8_evidence_index(
        index_id="evidence-index-good",
        purpose="Index bounded Wave 8 evidence for review query.",
        claim_boundary="Evidence index only; no certification.",
        integrated_trial=integrated,
        negative_control_report=negative_report,
        readiness_scorecard=scorecard,
    )
    entries = tuple(
        entry
        for entry in index.entries
        if entry.kind is not EvidenceArtifactKind.READINESS_SCORECARD
    )

    with pytest.raises(ValueError, match="missing artifact kinds"):
        Wave8EvidenceIndex(
            index_id="evidence-index-missing-kind",
            purpose="Index bounded Wave 8 evidence for review query.",
            claim_boundary="Evidence index only; no certification.",
            entries=entries,
            decision=EvidenceIndexDecision.NEEDS_EVIDENCE,
            findings=("missing-readiness-scorecard",),
        )


def test_evidence_index_rejects_overclaiming_claim_boundary() -> None:
    integrated, negative_report, scorecard = _scorecard()

    with pytest.raises(ValueError, match="blocked overclaiming"):
        build_wave8_evidence_index(
            index_id="evidence-index-overclaim",
            purpose="Index bounded Wave 8 evidence for review query.",
            claim_boundary="This certifies artificial general intelligence.",
            integrated_trial=integrated,
            negative_control_report=negative_report,
            readiness_scorecard=scorecard,
        )
