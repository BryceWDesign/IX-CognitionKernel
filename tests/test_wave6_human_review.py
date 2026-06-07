import pytest

from ix_cognition_kernel.wave6_human_review import (
    WAVE_SIX_REQUIRED_REVIEW_ITEM_KINDS,
    WaveSixHumanReviewDecision,
    WaveSixHumanReviewDocket,
    WaveSixHumanReviewFinding,
    WaveSixReviewItem,
    WaveSixReviewItemKind,
    build_wave_six_human_review_docket,
    required_wave_six_review_item_kinds,
)


def _item(
    kind: WaveSixReviewItemKind,
    *,
    item_id: str | None = None,
    finding: WaveSixHumanReviewFinding = WaveSixHumanReviewFinding.ACCEPTED,
    requires_follow_up: bool = False,
    blocks_wave_six_claim: bool = False,
) -> WaveSixReviewItem:
    return WaveSixReviewItem(
        item_id=item_id or f"item-{kind.value}",
        kind=kind,
        summary=f"Human review item for {kind.value}.",
        artifact_fingerprint=f"fingerprint-{kind.value}",
        evidence_ids=(f"evidence-{kind.value}",),
        finding=finding,
        reviewer_notes=("Reviewed as bounded Wave 6 evidence, not an AGI claim.",),
        requires_follow_up=requires_follow_up,
        blocks_wave_six_claim=blocks_wave_six_claim,
    )


def _complete_items() -> tuple[WaveSixReviewItem, ...]:
    return tuple(_item(kind) for kind in WAVE_SIX_REQUIRED_REVIEW_ITEM_KINDS)


def test_required_human_review_item_kinds_are_locked() -> None:
    assert required_wave_six_review_item_kinds() == (
        WaveSixReviewItemKind.MASTER_LOOP_TRACE,
        WaveSixReviewItemKind.CONTRACT_BUNDLE,
        WaveSixReviewItemKind.DONOR_TRACEABILITY_MAP,
        WaveSixReviewItemKind.REALITY_CORRECTION_LEDGER,
        WaveSixReviewItemKind.FUTURE_REASONING_CHANGE_LEDGER,
        WaveSixReviewItemKind.TRANSFER_NOVELTY_LEDGER,
        WaveSixReviewItemKind.FALSIFICATION_LEDGER,
        WaveSixReviewItemKind.CLAIM_BOUNDARY_DECLARATION,
    )


def test_review_item_is_evidence_bound_and_fingerprinted() -> None:
    item = _item(WaveSixReviewItemKind.MASTER_LOOP_TRACE)

    assert item.accepted
    assert not item.needs_more_evidence
    assert not item.blocks_claim
    assert item.evidence_ids == ("evidence-master-loop-trace",)
    assert item.fingerprint() == item.fingerprint()
    assert len(item.fingerprint()) == 64


def test_review_item_rejects_missing_evidence_and_notes() -> None:
    with pytest.raises(ValueError, match="require evidence ids"):
        WaveSixReviewItem(
            item_id="missing-evidence",
            kind=WaveSixReviewItemKind.MASTER_LOOP_TRACE,
            summary="Invalid review item.",
            artifact_fingerprint="fingerprint",
            evidence_ids=(),
            finding=WaveSixHumanReviewFinding.ACCEPTED,
            reviewer_notes=("Reviewed.",),
        )

    with pytest.raises(ValueError, match="require reviewer notes"):
        WaveSixReviewItem(
            item_id="missing-notes",
            kind=WaveSixReviewItemKind.MASTER_LOOP_TRACE,
            summary="Invalid review item.",
            artifact_fingerprint="fingerprint",
            evidence_ids=("evidence",),
            finding=WaveSixHumanReviewFinding.ACCEPTED,
            reviewer_notes=(),
        )


def test_blocking_review_findings_must_block_the_claim() -> None:
    with pytest.raises(ValueError, match="must block the claim"):
        _item(
            WaveSixReviewItemKind.FALSIFICATION_LEDGER,
            finding=WaveSixHumanReviewFinding.CONTRADICTED,
            blocks_wave_six_claim=False,
        )


def test_needs_more_evidence_finding_requires_follow_up() -> None:
    with pytest.raises(ValueError, match="require follow-up"):
        _item(
            WaveSixReviewItemKind.TRANSFER_NOVELTY_LEDGER,
            finding=WaveSixHumanReviewFinding.NEEDS_MORE_EVIDENCE,
            requires_follow_up=False,
        )


def test_human_review_docket_approves_complete_bounded_review() -> None:
    docket = build_wave_six_human_review_docket(
        docket_id="docket-ready",
        reviewer_id="reviewer-1",
        reviewer_role="human-authority",
        items=_complete_items(),
        decision=WaveSixHumanReviewDecision.APPROVE_BOUNDED_WAVE_SIX_REVIEW,
        decision_rationale=(
            "All required evidence surfaces are accepted for bounded Wave 6 "
            "review without making an AGI claim."
        ),
        notes=("Human authority remains outside the system.",),
    )

    assert docket.item_ids == tuple(sorted(item.item_id for item in _complete_items()))
    assert docket.present_item_kinds == WAVE_SIX_REQUIRED_REVIEW_ITEM_KINDS
    assert docket.missing_item_kinds == ()
    assert docket.follow_up_item_ids == ()
    assert docket.blocking_item_ids == ()
    assert len(docket.accepted_item_ids) == len(WAVE_SIX_REQUIRED_REVIEW_ITEM_KINDS)
    assert docket.approves_bounded_wave_six_review
    assert not docket.blocks_wave_six_claim
    assert docket.fingerprint() == docket.fingerprint()
    assert len(docket.fingerprint()) == 64


def test_human_review_docket_reports_missing_review_item_kinds() -> None:
    docket = WaveSixHumanReviewDocket(
        docket_id="docket-incomplete",
        reviewer_id="reviewer-1",
        reviewer_role="human-authority",
        items=_complete_items()[:-1],
        decision=WaveSixHumanReviewDecision.NEEDS_MORE_EVIDENCE,
        decision_rationale="Claim-boundary declaration still needs review.",
    )

    assert docket.missing_item_kinds == (
        WaveSixReviewItemKind.CLAIM_BOUNDARY_DECLARATION,
    )
    assert not docket.approves_bounded_wave_six_review
    assert not docket.blocks_wave_six_claim


def test_approved_docket_rejects_missing_item_kinds() -> None:
    with pytest.raises(ValueError, match="all review item kinds"):
        WaveSixHumanReviewDocket(
            docket_id="docket-invalid-approval",
            reviewer_id="reviewer-1",
            reviewer_role="human-authority",
            items=_complete_items()[:-1],
            decision=WaveSixHumanReviewDecision.APPROVE_BOUNDED_WAVE_SIX_REVIEW,
            decision_rationale="Invalid approval with incomplete evidence.",
        )


def test_approved_docket_rejects_follow_up_or_blocking_items() -> None:
    follow_up_items = list(_complete_items())
    follow_up_items[0] = _item(
        WaveSixReviewItemKind.MASTER_LOOP_TRACE,
        finding=WaveSixHumanReviewFinding.NEEDS_MORE_EVIDENCE,
        requires_follow_up=True,
    )

    with pytest.raises(ValueError, match="follow-up evidence"):
        WaveSixHumanReviewDocket(
            docket_id="docket-follow-up",
            reviewer_id="reviewer-1",
            reviewer_role="human-authority",
            items=tuple(follow_up_items),
            decision=WaveSixHumanReviewDecision.APPROVE_BOUNDED_WAVE_SIX_REVIEW,
            decision_rationale="Invalid approval with follow-up required.",
        )

    blocking_items = list(_complete_items())
    blocking_items[1] = _item(
        WaveSixReviewItemKind.CONTRACT_BUNDLE,
        finding=WaveSixHumanReviewFinding.BLOCKS_CLAIM,
        blocks_wave_six_claim=True,
    )

    with pytest.raises(ValueError, match="blocking items"):
        WaveSixHumanReviewDocket(
            docket_id="docket-blocking-approval",
            reviewer_id="reviewer-1",
            reviewer_role="human-authority",
            items=tuple(blocking_items),
            decision=WaveSixHumanReviewDecision.APPROVE_BOUNDED_WAVE_SIX_REVIEW,
            decision_rationale="Invalid approval with blocking evidence.",
        )


def test_blocked_docket_requires_blocking_item() -> None:
    with pytest.raises(ValueError, match="at least one blocking item"):
        WaveSixHumanReviewDocket(
            docket_id="docket-invalid-block",
            reviewer_id="reviewer-1",
            reviewer_role="human-authority",
            items=_complete_items(),
            decision=WaveSixHumanReviewDecision.BLOCK_CLAIM,
            decision_rationale="Invalid block without blocking evidence.",
        )


def test_human_review_docket_blocks_wave_six_claim() -> None:
    items = list(_complete_items())
    items[6] = _item(
        WaveSixReviewItemKind.FALSIFICATION_LEDGER,
        finding=WaveSixHumanReviewFinding.CONTRADICTED,
        blocks_wave_six_claim=True,
    )
    docket = WaveSixHumanReviewDocket(
        docket_id="docket-blocked",
        reviewer_id="reviewer-1",
        reviewer_role="human-authority",
        items=tuple(items),
        decision=WaveSixHumanReviewDecision.BLOCK_CLAIM,
        decision_rationale="Falsification contradiction blocks Wave 6 interpretation.",
    )

    assert docket.blocking_item_ids == ("item-falsification-ledger",)
    assert docket.blocks_wave_six_claim
    assert not docket.approves_bounded_wave_six_review


def test_human_review_docket_rejects_overclaims() -> None:
    with pytest.raises(ValueError, match="must not claim AGI"):
        WaveSixHumanReviewDocket(
            docket_id="docket-agi",
            reviewer_id="reviewer-1",
            reviewer_role="human-authority",
            items=_complete_items(),
            decision=WaveSixHumanReviewDecision.NEEDS_MORE_EVIDENCE,
            decision_rationale="Invalid overclaim.",
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="must not allow autonomous authority"):
        WaveSixHumanReviewDocket(
            docket_id="docket-autonomous",
            reviewer_id="reviewer-1",
            reviewer_role="human-authority",
            items=_complete_items(),
            decision=WaveSixHumanReviewDecision.NEEDS_MORE_EVIDENCE,
            decision_rationale="Invalid autonomous authority claim.",
            allows_autonomous_authority=True,
        )


def test_human_review_docket_rejects_duplicate_item_ids() -> None:
    item = _item(WaveSixReviewItemKind.MASTER_LOOP_TRACE)

    with pytest.raises(ValueError, match="Duplicate item_id"):
        WaveSixHumanReviewDocket(
            docket_id="docket-duplicate",
            reviewer_id="reviewer-1",
            reviewer_role="human-authority",
            items=(item, item),
            decision=WaveSixHumanReviewDecision.NEEDS_MORE_EVIDENCE,
            decision_rationale="Duplicate items break reviewability.",
        )


def test_item_for_kind_returns_present_item_only() -> None:
    docket = WaveSixHumanReviewDocket(
        docket_id="docket-lookup",
        reviewer_id="reviewer-1",
        reviewer_role="human-authority",
        items=(_item(WaveSixReviewItemKind.MASTER_LOOP_TRACE),),
        decision=WaveSixHumanReviewDecision.NEEDS_MORE_EVIDENCE,
        decision_rationale="Partial docket for lookup testing.",
    )

    item = docket.item_for_kind(WaveSixReviewItemKind.MASTER_LOOP_TRACE)

    assert item is not None
    assert item.item_id == "item-master-loop-trace"
    assert docket.item_for_kind(WaveSixReviewItemKind.CONTRACT_BUNDLE) is None
