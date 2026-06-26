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
    PublicClaimDecision,
    PublicClaimScope,
    build_public_claim_draft,
    review_public_claim,
)
from ix_cognition_kernel.wave8_readiness_scorecard import (
    build_wave8_readiness_scorecard,
)


def _ready_chain():
    integrated = build_integrated_wave8_trial(
        trial_id="public-claim-integrated-trial",
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
    return index, scorecard, matrix


def test_public_claim_guard_approves_bounded_review_claim() -> None:
    index, scorecard, matrix = _ready_chain()
    draft = build_public_claim_draft(
        claim_id="claim-review-handoff",
        scope=PublicClaimScope.REVIEW_HANDOFF,
        text=(
            "Wave 8 produced bounded replay, transfer, baseline, negative-control, "
            "and falsification evidence for human review handoff."
        ),
        source_artifact_kinds=(
            EvidenceArtifactKind.READINESS_SCORECARD,
            EvidenceArtifactKind.FALSIFICATION_MATRIX
            if hasattr(EvidenceArtifactKind, "FALSIFICATION_MATRIX")
            else EvidenceArtifactKind.NEGATIVE_CONTROL_REPORT,
        ),
        evidence_ids=("claim-evidence-1",),
    )
    review = review_public_claim(
        review_id="public-claim-review-1",
        draft=draft,
        evidence_index=index,
        readiness_scorecard=scorecard,
        falsification_matrix=matrix,
    )

    assert review.approved
    assert review.decision is PublicClaimDecision.APPROVED_BOUNDED_REVIEW_CLAIM
    assert review.findings == ()
    assert "entry-readiness-scorecard" in review.matched_entry_ids
    assert review.fingerprint() == review.fingerprint()
    assert len(review.fingerprint()) == 64


def test_public_claim_guard_blocks_overclaiming_text() -> None:
    index, scorecard, matrix = _ready_chain()
    draft = build_public_claim_draft(
        claim_id="claim-overclaim",
        scope=PublicClaimScope.REVIEW_HANDOFF,
        text="Wave 8 proves AGI and deployment approved autonomous authority.",
        source_artifact_kinds=(EvidenceArtifactKind.READINESS_SCORECARD,),
        evidence_ids=("claim-evidence-1",),
    )
    review = review_public_claim(
        review_id="public-claim-review-overclaim",
        draft=draft,
        evidence_index=index,
        readiness_scorecard=scorecard,
        falsification_matrix=matrix,
    )

    assert not review.approved
    assert review.decision is PublicClaimDecision.BLOCKED_OVERCLAIM
    assert "public-claim-overclaims-scope" in review.findings


def test_public_claim_guard_blocks_when_evidence_index_not_ready() -> None:
    index, scorecard, matrix = _ready_chain()
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
    draft = build_public_claim_draft(
        claim_id="claim-index-blocked",
        scope=PublicClaimScope.EVIDENCE_INDEX,
        text="Evidence index is available for bounded human review.",
        source_artifact_kinds=(EvidenceArtifactKind.EVIDENCE_INDEX,),
        evidence_ids=("claim-evidence-1",),
    )
    review = review_public_claim(
        review_id="public-claim-review-index-blocked",
        draft=draft,
        evidence_index=blocked_index,
        readiness_scorecard=scorecard,
        falsification_matrix=matrix,
    )

    assert not review.approved
    assert review.decision is PublicClaimDecision.NEEDS_READY_EVIDENCE_INDEX
    assert "evidence-index-not-ready:blocked" in review.findings


def test_public_claim_guard_blocks_when_falsification_does_not_survive() -> None:
    index, scorecard, _matrix = _ready_chain()
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
    review = review_public_claim(
        review_id="public-claim-review-falsification",
        draft=draft,
        evidence_index=index,
        readiness_scorecard=scorecard,
        falsification_matrix=failed_matrix,
    )

    assert not review.approved
    assert review.decision is PublicClaimDecision.NEEDS_FALSIFICATION_SURVIVAL
    assert any(
        finding.startswith("falsification-matrix-not-survived")
        for finding in review.findings
    )


def test_public_claim_guard_requires_source_artifact_matches() -> None:
    index, scorecard, matrix = _ready_chain()
    draft = build_public_claim_draft(
        claim_id="claim-missing-source",
        scope=PublicClaimScope.EVIDENCE_INDEX,
        text="This bounded claim has no matching source artifact.",
        source_artifact_kinds=(EvidenceArtifactKind.EVIDENCE_INDEX,),
        evidence_ids=("claim-evidence-1",),
    )
    review = review_public_claim(
        review_id="public-claim-review-missing-source",
        draft=draft,
        evidence_index=index,
        readiness_scorecard=scorecard,
        falsification_matrix=matrix,
    )

    assert not review.approved
    assert review.decision is PublicClaimDecision.NEEDS_SOURCE_ARTIFACTS
    assert "missing-source-artifact-kinds" in review.findings
