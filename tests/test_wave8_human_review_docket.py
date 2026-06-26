import pytest

from ix_cognition_kernel.wave8_evidence_index import (
    EvidenceArtifactKind,
    build_wave8_evidence_index,
)
from ix_cognition_kernel.wave8_falsification_matrix import (
    build_wave8_falsification_matrix,
)
from ix_cognition_kernel.wave8_human_review_docket import (
    HumanReviewDocketDecision,
    HumanReviewItem,
    HumanReviewItemDecision,
    HumanReviewRole,
    Wave8HumanReviewDocket,
    build_wave8_human_review_docket,
    default_human_review_items,
)
from ix_cognition_kernel.wave8_integrated_trial import build_integrated_wave8_trial
from ix_cognition_kernel.wave8_negative_controls import (
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
    build_wave8_review_handoff,
)
from ix_cognition_kernel.wave8_review_query import (
    ReviewQueryMode,
    build_review_query_request,
    execute_review_query,
)


def _ready_handoff():
    integrated = build_integrated_wave8_trial(
        trial_id="human-review-docket-integrated-trial",
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
    return build_wave8_review_handoff(
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


def test_wave8_human_review_docket_ready_from_ready_handoff() -> None:
    handoff = _ready_handoff()
    items = default_human_review_items(handoff=handoff)
    docket = build_wave8_human_review_docket(
        docket_id="human-review-docket-1",
        purpose="Prepare bounded Wave 8 evidence for human review.",
        claim_boundary="Human review docket only; no certification.",
        handoff=handoff,
        items=items,
    )

    assert docket.ready
    assert docket.decision is HumanReviewDocketDecision.READY_FOR_HUMAN_REVIEW
    assert docket.ready_item_count == 6
    assert docket.blocked_item_count == 0
    assert docket.findings == ()
    assert docket.fingerprint() == docket.fingerprint()
    assert len(docket.fingerprint()) == 64


def test_wave8_human_review_items_bind_required_roles() -> None:
    handoff = _ready_handoff()
    items = default_human_review_items(handoff=handoff)
    roles = {item.role for item in items}

    assert roles == {
        HumanReviewRole.HUMAN_AUTHORITY,
        HumanReviewRole.INDEPENDENT_REPLAYER,
        HumanReviewRole.SAFETY_REVIEWER,
        HumanReviewRole.TRANSFER_REVIEWER,
        HumanReviewRole.BASELINE_REVIEWER,
        HumanReviewRole.CLAIM_BOUNDARY_REVIEWER,
    }
    assert all(item.ready for item in items)
    assert all(item.source_entry_ids for item in items)


def test_human_review_item_requires_findings_when_blocked() -> None:
    with pytest.raises(ValueError, match="require findings"):
        HumanReviewItem(
            item_id="blocked-item",
            role=HumanReviewRole.SAFETY_REVIEWER,
            question="Does this item block safely?",
            decision=HumanReviewItemDecision.BLOCKED_BY_HANDOFF,
            source_entry_ids=("entry-negative-control-report",),
            evidence_ids=("item-evidence-1",),
        )


def test_human_review_docket_rejects_missing_required_roles() -> None:
    handoff = _ready_handoff()
    items = default_human_review_items(handoff=handoff)[:-1]

    with pytest.raises(ValueError, match="missing roles"):
        build_wave8_human_review_docket(
            docket_id="human-review-docket-missing-role",
            purpose="Prepare bounded Wave 8 evidence for human review.",
            claim_boundary="Human review docket only; no certification.",
            handoff=handoff,
            items=items,
        )


def test_human_review_docket_rejects_duplicate_item_ids() -> None:
    handoff = _ready_handoff()
    items = default_human_review_items(handoff=handoff)

    with pytest.raises(ValueError, match="Duplicate human review item id"):
        Wave8HumanReviewDocket(
            docket_id="human-review-docket-duplicate",
            purpose="Prepare bounded Wave 8 evidence for human review.",
            claim_boundary="Human review docket only; no certification.",
            handoff_fingerprint=handoff.fingerprint(),
            items=(items[0], items[0], *items[1:]),
            decision=HumanReviewDocketDecision.NEEDS_EVIDENCE,
            findings=("duplicate-review-item",),
        )


def test_human_review_docket_rejects_overclaiming_boundary() -> None:
    handoff = _ready_handoff()

    with pytest.raises(ValueError, match="blocked overclaiming"):
        build_wave8_human_review_docket(
            docket_id="human-review-docket-overclaim",
            purpose="Prepare bounded Wave 8 evidence for human review.",
            claim_boundary="This certifies artificial general intelligence.",
            handoff=handoff,
            items=default_human_review_items(handoff=handoff),
        )
