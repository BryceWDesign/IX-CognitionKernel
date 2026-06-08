import pytest

from ix_cognition_kernel.wave6_closure_checklist import (
    WAVE_SIX_REQUIRED_CLOSURE_ITEMS,
    WaveSixClosureChecklist,
    WaveSixClosureDecision,
    WaveSixClosureFinding,
    WaveSixClosureItem,
    WaveSixClosureItemKind,
    WaveSixClosureStatus,
    build_wave_six_closure_checklist,
    required_wave_six_closure_items,
)


def _boundary_statement() -> str:
    return (
        "This Wave-6 measured system-level cognition package is released for "
        "bounded review under human authority and independent review. It is not "
        "an AGI claim."
    )


def _item(
    kind: WaveSixClosureItemKind,
    *,
    item_id: str | None = None,
    finding: WaveSixClosureFinding = WaveSixClosureFinding.CLOSED,
    requires_follow_up: bool = False,
    blocks_closure: bool = False,
) -> WaveSixClosureItem:
    return WaveSixClosureItem(
        item_id=item_id or f"item-{kind.value}",
        kind=kind,
        artifact_fingerprint=f"fingerprint-{kind.value}",
        summary=f"Closure item for {kind.value}.",
        evidence_ids=(f"evidence-{kind.value}",),
        reviewer_questions=(f"Can {kind.value} be closed without overclaiming?",),
        finding=finding,
        requires_follow_up=requires_follow_up,
        blocks_closure=blocks_closure,
    )


def _complete_items() -> tuple[WaveSixClosureItem, ...]:
    return tuple(_item(kind) for kind in WAVE_SIX_REQUIRED_CLOSURE_ITEMS)


def _checklist(
    *,
    items: tuple[WaveSixClosureItem, ...] | None = None,
    decision: WaveSixClosureDecision = WaveSixClosureDecision.READY_FOR_README_UPDATE,
    claims_agi: bool = False,
    claim_boundary_statement: str | None = None,
) -> WaveSixClosureChecklist:
    return WaveSixClosureChecklist(
        checklist_id="closure-checklist-1",
        items=items or _complete_items(),
        decision=decision,
        claim_boundary_statement=claim_boundary_statement or _boundary_statement(),
        generated_by_engine_id="wave6-closure-checklist-engine",
        human_authority_id="human-authority-1",
        independent_reviewer_id="independent-reviewer-1",
        claims_agi=claims_agi,
        notes=("README closure remains bounded review, not AGI achieved.",),
    )


def test_required_closure_items_are_locked() -> None:
    assert required_wave_six_closure_items() == (
        WaveSixClosureItemKind.FINAL_OUTCOME_DECLARATION,
        WaveSixClosureItemKind.FINAL_DOSSIER,
        WaveSixClosureItemKind.CI_RECEIPT_LEDGER,
        WaveSixClosureItemKind.EVIDENCE_GAP_REGISTER,
        WaveSixClosureItemKind.PUBLIC_CLAIM_REPORT,
        WaveSixClosureItemKind.CONSISTENCY_REPORT,
        WaveSixClosureItemKind.REVIEW_SUMMARY,
        WaveSixClosureItemKind.README_BOUNDARY,
    )


def test_closure_item_is_evidence_bound_and_fingerprinted() -> None:
    item = _item(WaveSixClosureItemKind.FINAL_OUTCOME_DECLARATION)

    assert item.closed
    assert not item.needs_more_evidence
    assert not item.blocks_bounded_closure
    assert item.fingerprint() == item.fingerprint()
    assert len(item.fingerprint()) == 64


def test_closure_item_enforces_finding_semantics() -> None:
    with pytest.raises(ValueError, match="cannot require follow-up"):
        _item(
            WaveSixClosureItemKind.CI_RECEIPT_LEDGER,
            finding=WaveSixClosureFinding.CLOSED,
            requires_follow_up=True,
        )

    with pytest.raises(ValueError, match="require follow-up"):
        _item(
            WaveSixClosureItemKind.CI_RECEIPT_LEDGER,
            finding=WaveSixClosureFinding.NEEDS_MORE_EVIDENCE,
        )

    with pytest.raises(ValueError, match="must block closure"):
        _item(
            WaveSixClosureItemKind.PUBLIC_CLAIM_REPORT,
            finding=WaveSixClosureFinding.BLOCKS_CLOSURE,
        )


def test_closure_checklist_is_ready_when_complete_and_bounded() -> None:
    checklist = build_wave_six_closure_checklist(
        checklist_id="closure-checklist-ready",
        items=_complete_items(),
        decision=WaveSixClosureDecision.READY_FOR_README_UPDATE,
        claim_boundary_statement=_boundary_statement(),
        generated_by_engine_id="wave6-closure-checklist-engine",
        human_authority_id="human-authority-1",
        independent_reviewer_id="independent-reviewer-1",
        notes=("All closure items are ready for final README update.",),
    )

    assert checklist.present_item_kinds == WAVE_SIX_REQUIRED_CLOSURE_ITEMS
    assert checklist.missing_item_kinds == ()
    assert checklist.follow_up_item_ids == ()
    assert checklist.blocking_item_ids == ()
    assert checklist.status is WaveSixClosureStatus.READY
    assert checklist.ready_for_readme_update
    assert checklist.allowed_readme_status_label == "Wave 6 bounded review ready"
    assert checklist.fingerprint() == checklist.fingerprint()
    assert len(checklist.fingerprint()) == 64


def test_closure_checklist_reports_missing_item_kind() -> None:
    checklist = _checklist(
        items=_complete_items()[:-1],
        decision=WaveSixClosureDecision.HOLD_FOR_MORE_EVIDENCE,
    )

    assert checklist.missing_item_kinds == (WaveSixClosureItemKind.README_BOUNDARY,)
    assert checklist.status is WaveSixClosureStatus.NEEDS_MORE_EVIDENCE
    assert checklist.allowed_readme_status_label == "Wave 6 needs more evidence"


def test_closure_checklist_tracks_follow_up_item() -> None:
    items = list(_complete_items())
    items[2] = _item(
        WaveSixClosureItemKind.CI_RECEIPT_LEDGER,
        finding=WaveSixClosureFinding.NEEDS_MORE_EVIDENCE,
        requires_follow_up=True,
    )
    checklist = _checklist(
        items=tuple(items),
        decision=WaveSixClosureDecision.HOLD_FOR_MORE_EVIDENCE,
    )

    assert checklist.follow_up_item_ids == ("item-ci-receipt-ledger",)
    assert checklist.status is WaveSixClosureStatus.NEEDS_MORE_EVIDENCE
    assert not checklist.ready_for_readme_update


def test_closure_checklist_blocks_on_blocking_item_or_overclaim() -> None:
    items = list(_complete_items())
    items[4] = _item(
        WaveSixClosureItemKind.PUBLIC_CLAIM_REPORT,
        finding=WaveSixClosureFinding.BLOCKS_CLOSURE,
        blocks_closure=True,
    )
    blocked = _checklist(
        items=tuple(items),
        decision=WaveSixClosureDecision.BLOCK_README_UPDATE,
    )

    assert blocked.blocking_item_ids == ("item-public-claim-report",)
    assert blocked.status is WaveSixClosureStatus.BLOCKED
    assert blocked.allowed_readme_status_label == "Wave 6 interpretation blocked"

    overclaim = _checklist(
        decision=WaveSixClosureDecision.BLOCK_README_UPDATE,
        claims_agi=True,
    )

    assert overclaim.overclaim_present
    assert overclaim.status is WaveSixClosureStatus.BLOCKED


def test_ready_closure_checklist_rejects_missing_or_follow_up_items() -> None:
    with pytest.raises(ValueError, match="require every item kind"):
        _checklist(items=_complete_items()[:-1])

    items = list(_complete_items())
    items[3] = _item(
        WaveSixClosureItemKind.EVIDENCE_GAP_REGISTER,
        finding=WaveSixClosureFinding.NEEDS_MORE_EVIDENCE,
        requires_follow_up=True,
    )

    with pytest.raises(ValueError, match="cannot need follow-up"):
        _checklist(items=tuple(items))


def test_blocked_closure_checklist_requires_blocker_or_overclaim() -> None:
    with pytest.raises(ValueError, match="require blocker or overclaim"):
        _checklist(decision=WaveSixClosureDecision.BLOCK_README_UPDATE)


def test_closure_checklist_reports_invalid_claim_boundary_statement() -> None:
    checklist = _checklist(
        decision=WaveSixClosureDecision.HOLD_FOR_MORE_EVIDENCE,
        claim_boundary_statement="Wave 6 is ready.",
    )

    assert not checklist.claim_boundary_statement_valid
    assert checklist.status is WaveSixClosureStatus.NEEDS_MORE_EVIDENCE


def test_closure_checklist_lookup_and_duplicate_rejection() -> None:
    checklist = _checklist(
        items=(_item(WaveSixClosureItemKind.README_BOUNDARY),),
        decision=WaveSixClosureDecision.HOLD_FOR_MORE_EVIDENCE,
    )

    item = checklist.item_for_kind(WaveSixClosureItemKind.README_BOUNDARY)

    assert item is not None
    assert item.item_id == "item-readme-boundary"
    assert checklist.item_for_kind(WaveSixClosureItemKind.PUBLIC_CLAIM_REPORT) is None

    duplicate = _item(WaveSixClosureItemKind.README_BOUNDARY)
    with pytest.raises(ValueError, match="Duplicate item_id"):
        _checklist(
            items=(duplicate, duplicate),
            decision=WaveSixClosureDecision.HOLD_FOR_MORE_EVIDENCE,
        )

    with pytest.raises(ValueError, match="Duplicate item kind"):
        _checklist(
            items=(
                duplicate,
                _item(
                    WaveSixClosureItemKind.README_BOUNDARY,
                    item_id="different-item-id",
                ),
            ),
            decision=WaveSixClosureDecision.HOLD_FOR_MORE_EVIDENCE,
        )


def test_closure_checklist_requires_non_empty_authority_fields() -> None:
    with pytest.raises(ValueError, match="human_authority_id must not be empty"):
        WaveSixClosureChecklist(
            checklist_id="closure-checklist-invalid",
            items=_complete_items(),
            decision=WaveSixClosureDecision.HOLD_FOR_MORE_EVIDENCE,
            claim_boundary_statement=_boundary_statement(),
            generated_by_engine_id="wave6-closure-checklist-engine",
            human_authority_id=" ",
            independent_reviewer_id="independent-reviewer-1",
        )
