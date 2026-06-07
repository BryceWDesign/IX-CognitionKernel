import pytest

from ix_cognition_kernel.wave6_ci_receipts import (
    WAVE_SIX_REQUIRED_CI_COMMAND_KINDS,
    WaveSixCICommandKind,
    WaveSixCICommandReceipt,
    WaveSixCICommandStatus,
    WaveSixCIReceiptDecision,
    WaveSixCIReceiptLedger,
    WaveSixCIReceiptLedgerDecision,
    WaveSixCIReceiptLedgerStatus,
    build_wave_six_ci_receipt_ledger,
    required_wave_six_ci_command_kinds,
)


def _boundary_statement() -> str:
    return (
        "This Wave-6 measured system-level cognition package is released for "
        "bounded review under human authority and independent review. It is not "
        "an AGI claim."
    )


def _receipt(
    command_kind: WaveSixCICommandKind,
    *,
    receipt_id: str | None = None,
    status: WaveSixCICommandStatus = WaveSixCICommandStatus.PASSED,
    decision: WaveSixCIReceiptDecision = WaveSixCIReceiptDecision.ACCEPT_FOR_REVIEW,
    exit_code: int | None = 0,
    requires_follow_up: bool = False,
    blocks_review: bool = False,
) -> WaveSixCICommandReceipt:
    command_by_kind = {
        WaveSixCICommandKind.RUFF_CHECK: "python -m ruff check src tests",
        WaveSixCICommandKind.MYPY: "python -m mypy src tests",
        WaveSixCICommandKind.PYTEST: "PYTHONPATH=src python -m pytest -q",
        WaveSixCICommandKind.PY_COMPILE: "python -m py_compile src tests",
        WaveSixCICommandKind.PACKAGE_IMPORT: (
            "PYTHONPATH=src python -c 'import ix_cognition_kernel'"
        ),
        WaveSixCICommandKind.SECURITY_SCAN: "python -m pip_audit",
    }
    return WaveSixCICommandReceipt(
        receipt_id=receipt_id or f"receipt-{command_kind.value}",
        command_kind=command_kind,
        command=command_by_kind[command_kind],
        status=status,
        decision=decision,
        summary=f"CI receipt for {command_kind.value}.",
        evidence_ids=(f"evidence-{command_kind.value}",),
        output_fingerprint=f"fingerprint-{command_kind.value}",
        exit_code=exit_code,
        requires_follow_up=requires_follow_up,
        blocks_review=blocks_review,
    )


def _complete_receipts() -> tuple[WaveSixCICommandReceipt, ...]:
    return tuple(_receipt(kind) for kind in WAVE_SIX_REQUIRED_CI_COMMAND_KINDS)


def _ledger(
    *,
    receipts: tuple[WaveSixCICommandReceipt, ...] | None = None,
    decision: WaveSixCIReceiptLedgerDecision = (
        WaveSixCIReceiptLedgerDecision.READY_FOR_BOUNDED_REVIEW
    ),
    claims_agi: bool = False,
    claim_boundary_statement: str | None = None,
) -> WaveSixCIReceiptLedger:
    return WaveSixCIReceiptLedger(
        ledger_id="ci-ledger-1",
        receipts=receipts or _complete_receipts(),
        decision=decision,
        claim_boundary_statement=claim_boundary_statement or _boundary_statement(),
        generated_by_engine_id="wave6-ci-receipt-engine",
        human_authority_id="human-authority-1",
        independent_reviewer_id="independent-reviewer-1",
        claims_agi=claims_agi,
        notes=("CI receipts are evidence, not AGI proof.",),
    )


def test_required_ci_command_kinds_are_locked() -> None:
    assert required_wave_six_ci_command_kinds() == (
        WaveSixCICommandKind.RUFF_CHECK,
        WaveSixCICommandKind.MYPY,
        WaveSixCICommandKind.PYTEST,
    )


def test_passed_ci_receipt_is_evidence_bound_and_fingerprinted() -> None:
    receipt = _receipt(WaveSixCICommandKind.PYTEST)

    assert receipt.passed
    assert not receipt.needs_more_evidence
    assert not receipt.blocks_bounded_review
    assert receipt.exit_code == 0
    assert receipt.fingerprint() == receipt.fingerprint()
    assert len(receipt.fingerprint()) == 64


def test_passed_ci_receipt_enforces_acceptance_semantics() -> None:
    with pytest.raises(ValueError, match="require exit code 0"):
        _receipt(
            WaveSixCICommandKind.RUFF_CHECK,
            exit_code=1,
        )

    with pytest.raises(ValueError, match="must be accepted for review"):
        _receipt(
            WaveSixCICommandKind.RUFF_CHECK,
            decision=WaveSixCIReceiptDecision.NEEDS_MORE_EVIDENCE,
        )

    with pytest.raises(ValueError, match="cannot require follow-up"):
        _receipt(
            WaveSixCICommandKind.RUFF_CHECK,
            requires_follow_up=True,
        )


def test_failed_or_blocked_ci_receipt_must_block_review() -> None:
    with pytest.raises(ValueError, match="must block review"):
        _receipt(
            WaveSixCICommandKind.MYPY,
            status=WaveSixCICommandStatus.FAILED,
            decision=WaveSixCIReceiptDecision.NEEDS_MORE_EVIDENCE,
            exit_code=1,
        )

    with pytest.raises(ValueError, match="must set blocker"):
        _receipt(
            WaveSixCICommandKind.MYPY,
            status=WaveSixCICommandStatus.FAILED,
            decision=WaveSixCIReceiptDecision.BLOCK_REVIEW,
            exit_code=1,
            blocks_review=False,
        )


def test_not_run_ci_receipt_requires_follow_up() -> None:
    receipt = _receipt(
        WaveSixCICommandKind.MYPY,
        status=WaveSixCICommandStatus.NOT_RUN,
        decision=WaveSixCIReceiptDecision.NEEDS_MORE_EVIDENCE,
        exit_code=None,
        requires_follow_up=True,
    )

    assert not receipt.passed
    assert receipt.needs_more_evidence
    assert not receipt.blocks_bounded_review

    with pytest.raises(ValueError, match="require follow-up"):
        _receipt(
            WaveSixCICommandKind.MYPY,
            status=WaveSixCICommandStatus.NOT_RUN,
            decision=WaveSixCIReceiptDecision.NEEDS_MORE_EVIDENCE,
            exit_code=None,
        )


def test_ci_receipt_ledger_is_ready_when_required_commands_pass() -> None:
    ledger = build_wave_six_ci_receipt_ledger(
        ledger_id="ci-ledger-ready",
        receipts=_complete_receipts(),
        decision=WaveSixCIReceiptLedgerDecision.READY_FOR_BOUNDED_REVIEW,
        claim_boundary_statement=_boundary_statement(),
        generated_by_engine_id="wave6-ci-receipt-engine",
        human_authority_id="human-authority-1",
        independent_reviewer_id="independent-reviewer-1",
        notes=("ruff, mypy, and pytest receipts passed.",),
    )

    assert ledger.present_command_kinds == WAVE_SIX_REQUIRED_CI_COMMAND_KINDS
    assert ledger.missing_command_kinds == ()
    assert ledger.follow_up_receipt_ids == ()
    assert ledger.blocking_receipt_ids == ()
    assert ledger.status is WaveSixCIReceiptLedgerStatus.READY
    assert ledger.ready_for_bounded_review
    assert ledger.fingerprint() == ledger.fingerprint()
    assert len(ledger.fingerprint()) == 64


def test_ci_receipt_ledger_reports_missing_required_command() -> None:
    ledger = _ledger(
        receipts=_complete_receipts()[:-1],
        decision=WaveSixCIReceiptLedgerDecision.HOLD_FOR_MORE_EVIDENCE,
    )

    assert ledger.missing_command_kinds == (WaveSixCICommandKind.PYTEST,)
    assert ledger.status is WaveSixCIReceiptLedgerStatus.NEEDS_MORE_EVIDENCE
    assert not ledger.ready_for_bounded_review


def test_ci_receipt_ledger_tracks_not_run_command_as_follow_up() -> None:
    receipts = list(_complete_receipts())
    receipts[1] = _receipt(
        WaveSixCICommandKind.MYPY,
        status=WaveSixCICommandStatus.NOT_RUN,
        decision=WaveSixCIReceiptDecision.NEEDS_MORE_EVIDENCE,
        exit_code=None,
        requires_follow_up=True,
    )
    ledger = _ledger(
        receipts=tuple(receipts),
        decision=WaveSixCIReceiptLedgerDecision.HOLD_FOR_MORE_EVIDENCE,
    )

    assert ledger.follow_up_receipt_ids == ("receipt-mypy",)
    assert ledger.status is WaveSixCIReceiptLedgerStatus.NEEDS_MORE_EVIDENCE


def test_ci_receipt_ledger_blocks_on_failed_receipt_or_overclaim() -> None:
    receipts = list(_complete_receipts())
    receipts[2] = _receipt(
        WaveSixCICommandKind.PYTEST,
        status=WaveSixCICommandStatus.FAILED,
        decision=WaveSixCIReceiptDecision.BLOCK_REVIEW,
        exit_code=1,
        blocks_review=True,
    )
    blocked = _ledger(
        receipts=tuple(receipts),
        decision=WaveSixCIReceiptLedgerDecision.BLOCK_REVIEW,
    )

    assert blocked.blocking_receipt_ids == ("receipt-pytest",)
    assert blocked.status is WaveSixCIReceiptLedgerStatus.BLOCKED

    overclaim = _ledger(
        decision=WaveSixCIReceiptLedgerDecision.BLOCK_REVIEW,
        claims_agi=True,
    )

    assert overclaim.overclaim_present
    assert overclaim.status is WaveSixCIReceiptLedgerStatus.BLOCKED


def test_ready_ci_ledger_rejects_missing_or_follow_up_receipts() -> None:
    with pytest.raises(ValueError, match="require every command kind"):
        _ledger(receipts=_complete_receipts()[:-1])

    receipts = list(_complete_receipts())
    receipts[0] = _receipt(
        WaveSixCICommandKind.RUFF_CHECK,
        status=WaveSixCICommandStatus.NOT_RUN,
        decision=WaveSixCIReceiptDecision.NEEDS_MORE_EVIDENCE,
        exit_code=None,
        requires_follow_up=True,
    )

    with pytest.raises(ValueError, match="cannot require follow-up"):
        _ledger(receipts=tuple(receipts))


def test_blocked_ci_ledger_requires_blocker_or_overclaim() -> None:
    with pytest.raises(ValueError, match="require blocker or overclaim"):
        _ledger(decision=WaveSixCIReceiptLedgerDecision.BLOCK_REVIEW)


def test_ci_ledger_reports_invalid_claim_boundary_statement() -> None:
    ledger = _ledger(
        decision=WaveSixCIReceiptLedgerDecision.HOLD_FOR_MORE_EVIDENCE,
        claim_boundary_statement="Wave 6 is done.",
    )

    assert not ledger.claim_boundary_statement_valid
    assert ledger.status is WaveSixCIReceiptLedgerStatus.NEEDS_MORE_EVIDENCE


def test_ci_ledger_lookup_and_duplicate_rejection() -> None:
    ledger = _ledger(
        receipts=(_receipt(WaveSixCICommandKind.RUFF_CHECK),),
        decision=WaveSixCIReceiptLedgerDecision.HOLD_FOR_MORE_EVIDENCE,
    )

    receipt = ledger.receipt_for_command_kind(WaveSixCICommandKind.RUFF_CHECK)

    assert receipt is not None
    assert receipt.receipt_id == "receipt-ruff-check"
    assert ledger.receipt_for_command_kind(WaveSixCICommandKind.PYTEST) is None

    duplicate = _receipt(WaveSixCICommandKind.RUFF_CHECK)

    with pytest.raises(ValueError, match="Duplicate receipt_id"):
        _ledger(
            receipts=(duplicate, duplicate),
            decision=WaveSixCIReceiptLedgerDecision.HOLD_FOR_MORE_EVIDENCE,
        )

    with pytest.raises(ValueError, match="Duplicate command kind"):
        _ledger(
            receipts=(
                duplicate,
                _receipt(
                    WaveSixCICommandKind.RUFF_CHECK,
                    receipt_id="different-receipt-id",
                ),
            ),
            decision=WaveSixCIReceiptLedgerDecision.HOLD_FOR_MORE_EVIDENCE,
        )
