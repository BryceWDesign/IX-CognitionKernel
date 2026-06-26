import pytest

from ix_cognition_kernel.wave8_evidence_index import (
    EvidenceArtifactKind,
    EvidenceIndexDecision,
    EvidenceIndexEntry,
    EvidenceIndexEntryStatus,
    Wave8EvidenceIndex,
    build_wave8_evidence_index,
)
from ix_cognition_kernel.wave8_falsification_matrix import (
    build_wave8_falsification_matrix,
)
from ix_cognition_kernel.wave8_integrated_trial import build_integrated_wave8_trial
from ix_cognition_kernel.wave8_negative_controls import (
    NegativeControlKind,
    build_negative_control_record,
    build_negative_control_report,
    default_wave8_negative_control_records,
)
from ix_cognition_kernel.wave8_public_claim_guard import (
    PublicClaimScope,
    build_public_claim_draft,
    review_public_claim,
)
from ix_cognition_kernel.wave8_readiness_scorecard import (
    build_wave8_readiness_scorecard,
)
from ix_cognition_kernel.wave8_review_handoff import (
    ReviewHandoffDecision,
    build_wave8_review_handoff,
)
from ix_cognition_kernel.wave8_review_query import (
    ReviewQueryMode,
    build_review_query_request,
    execute_review_query,
)


def _ready_chain():
    integrated = build_integrated_wave8_trial(
        trial_id="review-handoff-integrated-trial",
        human_authority_evidence_ids=("human-authority-evidence-1",),
    )
    negative_report = build_negative_control_report(
        report_id="negative-control-report-1",
        purpose="Validate Wave 8 fail-closed behavior without certification.",
        records=default_wave8_negative_control_records(),
    )
    scorecard = build_wave8_readiness_scorecard(
        scorecard_id="scorecard-1",
        purpose="Score bounded Wave 8 readiness for review handoff.",
        claim_boundary="Readiness score only; no certification.",
        integrated_trial=integrated,
        negative_control_report=negative_report,
    )
    index = build_wave8_evidence_index(
        index_id="evidence-index-1",
        purpose="Index bounded Wave 8 evidence for review query.",
        claim_boundary="Evidence index only; no certification.",
        integrated_trial=integrated,
        negative_control_report=negative_report,
        readiness_scorecard=scorecard,
    )
    matrix = build_wave8_falsification_matrix(
        matrix_id="falsification-matrix-1",
        purpose="Bind bounded falsification checks for Wave 8 review.",
        claim_boundary="Falsification matrix only; no certification.",
        evidence_index=index,
        readiness_scorecard=scorecard,
        negative_control_report=negative_report,
    )
    query_request = build_review_query_request(
        query_id="query-scorecard",
        mode=ReviewQueryMode.BY_KIND,
        artifact_kinds=(EvidenceArtifactKind.READINESS_SCORECARD,),
        evidence_ids=("query-evidence-1",),
    )
    query_result = execute_review_query(
        result_id="query-result-scorecard",
        index=index,
        request=query_request,
    )
    draft = build_public_claim_draft(
        claim_id="claim-review-handoff",
        scope=PublicClaimScope.REVIEW_HANDOFF,
        text=(
            "Wave 8 produced bounded replay, transfer, baseline, negative-control, "
            "and falsification evidence for human review handoff."
        ),
        source_artifact_kinds=(
            EvidenceArtifactKind.READINESS_SCORECARD,
            EvidenceArtifactKind.NEGATIVE_CONTROL_REPORT,
        ),
        evidence_ids=("claim-evidence-1",),
    )
    public_review = review_public_claim(
        review_id="public-claim-review-1",
        draft=draft,
        evidence_index=index,
        readiness_scorecard=scorecard,
        falsification_matrix=matrix,
    )
    return scorecard, index, matrix, query_result, public_review


def test_wave8_review_handoff_ready_for_human_review() -> None:
    scorecard, index, matrix, query_result, public_review = _ready_chain()
    handoff = build_wave8_review_handoff(
        handoff_id="handoff-1",
        purpose="Bind bounded Wave 8 evidence for human review handoff.",
        claim_boundary="Human review handoff only; no certification.",
        readiness_scorecard=scorecard,
        evidence_index=index,
        falsification_matrix=matrix,
        review_query_result=query_result,
        public_claim_review=public_review,
        reviewer_evidence_ids=("human-review-evidence-1",),
    )

    assert handoff.ready
    assert handoff.decision is ReviewHandoffDecision.READY_FOR_HUMAN_REVIEW
    assert handoff.findings == ()
    assert handoff.fingerprint() == handoff.fingerprint()
    assert len(handoff.fingerprint()) == 64


def test_wave8_review_handoff_blocks_non_ready_evidence_index() -> None:
    scorecard, index, matrix, _query_result, public_review = _ready_chain()
    entries = list(index.entries)
    first = entries[0]
    entries[0] = EvidenceIndexEntry(
        entry_id=first.entry_id,
        kind=first.kind,
        title=first.title,
        source_fingerprint=first.source_fingerprint,
        status=EvidenceIndexEntryStatus.BLOCKED,
        claim_boundary=first.claim_boundary,
        evidence_ids=first.evidence_ids,
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
    query_request = build_review_query_request(
        query_id="query-ready-only",
        mode=ReviewQueryMode.READY_ONLY,
        evidence_ids=("query-evidence-1",),
    )
    blocked_query = execute_review_query(
        result_id="query-result-blocked",
        index=blocked_index,
        request=query_request,
    )

    with pytest.raises(ValueError, match="public_claim_index_fingerprint"):
        build_wave8_review_handoff(
            handoff_id="handoff-bad-binding",
            purpose="Bind bounded Wave 8 evidence for human review handoff.",
            claim_boundary="Human review handoff only; no certification.",
            readiness_scorecard=scorecard,
            evidence_index=blocked_index,
            falsification_matrix=matrix,
            review_query_result=blocked_query,
            public_claim_review=public_review,
            reviewer_evidence_ids=("human-review-evidence-1",),
        )


def test_wave8_review_handoff_blocks_failed_falsification_matrix() -> None:
    scorecard, index, _matrix, query_result, _public_review = _ready_chain()
    records = list(default_wave8_negative_control_records())
    records[0] = build_negative_control_record(
        control_id="negative-control-overclaim-failed-open",
        kind=NegativeControlKind.OVERCLAIM_BLOCK,
        expected_block_reason="Overclaiming must be blocked.",
        observed_decision="overclaim-allowed",
        blocked=False,
        evidence_ids=("negative-control-overclaim-evidence",),
        findings=("overclaim-failed-open",),
    )
    failed_negative_report = build_negative_control_report(
        report_id="negative-control-report-failed-open",
        purpose="Validate Wave 8 fail-closed behavior without certification.",
        records=tuple(records),
    )
    failed_matrix = build_wave8_falsification_matrix(
        matrix_id="falsification-matrix-failed-open",
        purpose="Bind bounded falsification checks for Wave 8 review.",
        claim_boundary="Falsification matrix only; no certification.",
        evidence_index=index,
        readiness_scorecard=scorecard,
        negative_control_report=failed_negative_report,
    )
    draft = build_public_claim_draft(
        claim_id="claim-falsification",
        scope=PublicClaimScope.FALSIFICATION_MATRIX,
        text="Falsification checks are available for bounded human review.",
        source_artifact_kinds=(EvidenceArtifactKind.NEGATIVE_CONTROL_REPORT,),
        evidence_ids=("claim-evidence-1",),
    )
    public_review = review_public_claim(
        review_id="public-claim-review-falsification",
        draft=draft,
        evidence_index=index,
        readiness_scorecard=scorecard,
        falsification_matrix=failed_matrix,
    )
    handoff = build_wave8_review_handoff(
        handoff_id="handoff-falsification-failed",
        purpose="Bind bounded Wave 8 evidence for human review handoff.",
        claim_boundary="Human review handoff only; no certification.",
        readiness_scorecard=scorecard,
        evidence_index=index,
        falsification_matrix=failed_matrix,
        review_query_result=query_result,
        public_claim_review=public_review,
        reviewer_evidence_ids=("human-review-evidence-1",),
    )

    assert not handoff.ready
    assert handoff.decision is ReviewHandoffDecision.NEEDS_FALSIFICATION_SURVIVAL
    assert any(
        finding.startswith("falsification-matrix-not-survived")
        for finding in handoff.findings
    )


def test_wave8_review_handoff_blocks_public_claim_overclaim() -> None:
    scorecard, index, matrix, query_result, _public_review = _ready_chain()
    draft = build_public_claim_draft(
        claim_id="claim-overclaim",
        scope=PublicClaimScope.REVIEW_HANDOFF,
        text="Wave 8 proves AGI and deployment approved autonomous authority.",
        source_artifact_kinds=(EvidenceArtifactKind.READINESS_SCORECARD,),
        evidence_ids=("claim-evidence-1",),
    )
    overclaim_review = review_public_claim(
        review_id="public-claim-review-overclaim",
        draft=draft,
        evidence_index=index,
        readiness_scorecard=scorecard,
        falsification_matrix=matrix,
    )
    handoff = build_wave8_review_handoff(
        handoff_id="handoff-overclaim",
        purpose="Bind bounded Wave 8 evidence for human review handoff.",
        claim_boundary="Human review handoff only; no certification.",
        readiness_scorecard=scorecard,
        evidence_index=index,
        falsification_matrix=matrix,
        review_query_result=query_result,
        public_claim_review=overclaim_review,
        reviewer_evidence_ids=("human-review-evidence-1",),
    )

    assert not handoff.ready
    assert handoff.decision is ReviewHandoffDecision.BLOCKED_OVERCLAIM
    assert "public-claim-overclaim-blocked" in handoff.findings


def test_wave8_review_handoff_rejects_overclaiming_boundary() -> None:
    scorecard, index, matrix, query_result, public_review = _ready_chain()

    with pytest.raises(ValueError, match="blocked overclaiming"):
        build_wave8_review_handoff(
            handoff_id="handoff-overclaim-boundary",
            purpose="Bind bounded Wave 8 evidence for human review handoff.",
            claim_boundary="This certifies artificial general intelligence.",
            readiness_scorecard=scorecard,
            evidence_index=index,
            falsification_matrix=matrix,
            review_query_result=query_result,
            public_claim_review=public_review,
            reviewer_evidence_ids=("human-review-evidence-1",),
        )
