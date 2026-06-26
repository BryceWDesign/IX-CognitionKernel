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
from ix_cognition_kernel.wave8_review_query import (
    ReviewQueryDecision,
    ReviewQueryMode,
    build_review_query_request,
    execute_review_query,
)


def _integrated_trial():
    return build_integrated_wave8_trial(
        trial_id="review-query-integrated-trial",
        human_authority_evidence_ids=("human-authority-evidence-1",),
    )


def _negative_control_report():
    return build_negative_control_report(
        report_id="negative-control-report-1",
        purpose="Validate Wave 8 fail-closed behavior without certification.",
        records=default_wave8_negative_control_records(),
    )


def _index():
    integrated = _integrated_trial()
    negative_report = _negative_control_report()
    scorecard = build_wave8_readiness_scorecard(
        scorecard_id="scorecard-1",
        purpose="Score bounded Wave 8 readiness for review handoff.",
        claim_boundary="Readiness score only; no certification.",
        integrated_trial=integrated,
        negative_control_report=negative_report,
    )
    return build_wave8_evidence_index(
        index_id="evidence-index-1",
        purpose="Index bounded Wave 8 evidence for review query.",
        claim_boundary="Evidence index only; no certification.",
        integrated_trial=integrated,
        negative_control_report=negative_report,
        readiness_scorecard=scorecard,
    )


def test_review_query_returns_entries_by_artifact_kind() -> None:
    index = _index()
    request = build_review_query_request(
        query_id="query-episode-runs",
        mode=ReviewQueryMode.BY_KIND,
        artifact_kinds=(EvidenceArtifactKind.EPISODE_RUN,),
        evidence_ids=("query-evidence-1",),
    )
    result = execute_review_query(
        result_id="query-result-episode-runs",
        index=index,
        request=request,
    )

    assert result.ready
    assert result.decision is ReviewQueryDecision.MATCHES_READY
    assert result.match_count == 5
    assert all(
        entry.kind is EvidenceArtifactKind.EPISODE_RUN
        for entry in result.matched_entries
    )
    assert result.fingerprint() == result.fingerprint()
    assert len(result.fingerprint()) == 64


def test_review_query_returns_entries_by_parent_relationship() -> None:
    index = _index()
    request = build_review_query_request(
        query_id="query-children-of-release",
        mode=ReviewQueryMode.BY_PARENT,
        parent_entry_ids=("entry-release-manifest",),
        evidence_ids=("query-evidence-1",),
    )
    result = execute_review_query(
        result_id="query-result-children-of-release",
        index=index,
        request=request,
    )

    assert result.ready
    assert result.matched_entry_ids == ("entry-readiness-scorecard",)


def test_review_query_returns_entries_by_text_terms() -> None:
    index = _index()
    request = build_review_query_request(
        query_id="query-baseline-text",
        mode=ReviewQueryMode.BY_TEXT,
        search_terms=("baseline", "comparison"),
        evidence_ids=("query-evidence-1",),
    )
    result = execute_review_query(
        result_id="query-result-baseline-text",
        index=index,
        request=request,
    )

    assert result.ready
    assert "entry-baseline-report" in result.matched_entry_ids


def test_review_query_returns_no_matches_with_finding() -> None:
    index = _index()
    request = build_review_query_request(
        query_id="query-no-matches",
        mode=ReviewQueryMode.BY_TEXT,
        search_terms=("not-present-in-index",),
        evidence_ids=("query-evidence-1",),
    )
    result = execute_review_query(
        result_id="query-result-no-matches",
        index=index,
        request=request,
    )

    assert not result.ready
    assert result.decision is ReviewQueryDecision.NO_MATCHES
    assert result.match_count == 0
    assert "query-produced-no-matches" in result.findings


def test_review_query_blocks_when_index_is_not_ready() -> None:
    index = _index()
    entries = list(index.entries)
    task_suite = entries[0]
    entries[0] = EvidenceIndexEntry(
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
        index_id="blocked-index",
        purpose="Index bounded Wave 8 evidence for review query.",
        claim_boundary="Evidence index only; no certification.",
        entries=tuple(entries),
        decision=EvidenceIndexDecision.BLOCKED,
        findings=("blocked-evidence-index-entries:entry-task-suite",),
    )
    request = build_review_query_request(
        query_id="query-ready-only",
        mode=ReviewQueryMode.READY_ONLY,
        evidence_ids=("query-evidence-1",),
    )
    result = execute_review_query(
        result_id="query-result-blocked-index",
        index=blocked_index,
        request=request,
    )

    assert not result.ready
    assert result.decision is ReviewQueryDecision.BLOCKED_INDEX
    assert result.matched_entries == ()
    assert "index-not-ready:blocked" in result.findings


def test_review_query_can_query_blocked_entries_when_index_gate_is_disabled() -> None:
    index = _index()
    entries = list(index.entries)
    task_suite = entries[0]
    entries[0] = EvidenceIndexEntry(
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
        index_id="blocked-index",
        purpose="Index bounded Wave 8 evidence for review query.",
        claim_boundary="Evidence index only; no certification.",
        entries=tuple(entries),
        decision=EvidenceIndexDecision.BLOCKED,
        findings=("blocked-evidence-index-entries:entry-task-suite",),
    )
    request = build_review_query_request(
        query_id="query-blocked-only",
        mode=ReviewQueryMode.BLOCKED_ONLY,
        require_ready_index=False,
        evidence_ids=("query-evidence-1",),
    )
    result = execute_review_query(
        result_id="query-result-blocked-only",
        index=blocked_index,
        request=request,
    )

    assert result.ready
    assert result.match_count == 1
    assert result.matched_entry_ids == ("entry-task-suite",)


def test_review_query_rejects_overclaiming_search_terms() -> None:
    with pytest.raises(ValueError, match="blocked overclaiming"):
        build_review_query_request(
            query_id="query-overclaim",
            mode=ReviewQueryMode.BY_TEXT,
            search_terms=("certifies AGI",),
            evidence_ids=("query-evidence-1",),
        )


def test_review_query_requires_mode_specific_fields() -> None:
    with pytest.raises(ValueError, match="BY_KIND queries require artifact kinds"):
        build_review_query_request(
            query_id="query-missing-kind",
            mode=ReviewQueryMode.BY_KIND,
            evidence_ids=("query-evidence-1",),
        )

    with pytest.raises(ValueError, match="BY_PARENT queries require parent entry ids"):
        build_review_query_request(
            query_id="query-missing-parent",
            mode=ReviewQueryMode.BY_PARENT,
            evidence_ids=("query-evidence-1",),
        )
