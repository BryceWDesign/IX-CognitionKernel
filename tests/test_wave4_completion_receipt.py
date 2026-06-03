from dataclasses import dataclass

import pytest

from ix_cognition_kernel.wave4_completion_receipt import (
    REQUIRED_WAVE_FOUR_RECORD_CHECK_KINDS,
    WaveFourCompletionReceipt,
    WaveFourCompletionReceiptDecision,
    WaveFourCompletionReceiptStatus,
    WaveFourRecordCheck,
    WaveFourRecordCheckKind,
    WaveFourRecordCheckSeverity,
    build_wave_four_completion_receipt,
)
from ix_cognition_kernel.wave4_contracts import (
    WaveFourArtifactKind,
    WaveFourAuthorityState,
    WaveFourCapabilityArea,
)
from ix_cognition_kernel.wave4_review_docket import WaveFourReviewDocketStatus


@dataclass(frozen=True)
class FakeDocket:
    docket_id: str = "review-docket-001"
    status: WaveFourReviewDocketStatus = (
        WaveFourReviewDocketStatus.READY_FOR_HUMAN_REVIEW
    )
    human_authority_state: WaveFourAuthorityState = (
        WaveFourAuthorityState.HUMAN_REVIEW_REQUIRED
    )
    final_digest: str = "a" * 64
    all_evidence_ids: tuple[str, ...] = (
        "evidence:declaration",
        "evidence:docket",
        "evidence:scorecard",
    )
    scenario_ids: tuple[str, ...] = ("worldtwin:completion-receipt",)
    blackfox_receipt_ids: tuple[str, ...] = ("blackfox:completion-receipt",)
    reviewer_assignments: tuple[str, ...] = ("assignment:technical",)
    readiness_gaps: tuple[str, ...] = ()
    blocking_gaps: tuple[str, ...] = ()
    permits_automatic_execution: bool = False
    permits_automatic_promotion: bool = False
    claims_agi: bool = False
    independently_validated: bool = False
    production_ready: bool = False


def ready_docket() -> FakeDocket:
    return FakeDocket()


def ready_receipt() -> WaveFourCompletionReceipt:
    return build_wave_four_completion_receipt(
        receipt_id="completion-receipt-001",
        review_docket=ready_docket(),
    )


def test_required_completion_record_check_kinds_are_locked() -> None:
    assert REQUIRED_WAVE_FOUR_RECORD_CHECK_KINDS == (
        WaveFourRecordCheckKind.DOCKET_READY,
        WaveFourRecordCheckKind.DOCKET_DIGEST_PRESENT,
        WaveFourRecordCheckKind.EVIDENCE_PRESENT,
        WaveFourRecordCheckKind.REVIEWERS_PRESENT,
        WaveFourRecordCheckKind.SCENARIOS_PRESENT,
        WaveFourRecordCheckKind.BLACKFOX_RECEIPTS_PRESENT,
        WaveFourRecordCheckKind.HUMAN_AUTHORITY_REQUIRED,
        WaveFourRecordCheckKind.NO_AUTOMATIC_EXECUTION,
        WaveFourRecordCheckKind.NO_AUTOMATIC_PROMOTION,
        WaveFourRecordCheckKind.NO_AGI_CLAIM,
        WaveFourRecordCheckKind.NO_INDEPENDENT_VALIDATION_CLAIM,
        WaveFourRecordCheckKind.NO_PRODUCTION_CLAIM,
    )


def test_record_check_requires_failure_text_when_failed() -> None:
    with pytest.raises(ValueError, match="require failure text"):
        WaveFourRecordCheck(
            check_id="check:invalid",
            check_kind=WaveFourRecordCheckKind.EVIDENCE_PRESENT,
            severity=WaveFourRecordCheckSeverity.EVIDENCE,
            passed=False,
            summary="Invalid failed check without text.",
        )

    with pytest.raises(ValueError, match="cannot carry failure text"):
        WaveFourRecordCheck(
            check_id="check:invalid",
            check_kind=WaveFourRecordCheckKind.EVIDENCE_PRESENT,
            severity=WaveFourRecordCheckSeverity.EVIDENCE,
            passed=True,
            summary="Invalid passed check with failure text.",
            failure_summary="should not exist",
        )


def test_ready_completion_receipt_records_wave_four_without_overclaim() -> None:
    receipt = ready_receipt()

    assert receipt.status is WaveFourCompletionReceiptStatus.READY_FOR_WAVE_FOUR_RECORD
    assert receipt.decision is (
        WaveFourCompletionReceiptDecision.RECORD_WAVE_FOUR_REVIEW_PACKAGE
    )
    assert receipt.ready_for_wave_four_record is True
    assert receipt.missing_required_check_kinds == ()
    assert receipt.failed_check_ids == ()
    assert receipt.readiness_gaps == ()
    assert receipt.blocking_gaps == ()
    assert receipt.permits_automatic_execution is False
    assert receipt.permits_automatic_promotion is False
    assert receipt.claims_agi is False
    assert receipt.independently_validated is False
    assert receipt.production_ready is False
    assert len(receipt.receipt_digest) == 64
    assert "human review record only; no AGI claim" in receipt.review_summary


def test_receipt_holds_for_evidence_when_digest_is_malformed() -> None:
    receipt = build_wave_four_completion_receipt(
        receipt_id="completion-receipt-bad-digest",
        review_docket=FakeDocket(final_digest="bad-digest"),
    )

    assert receipt.status is WaveFourCompletionReceiptStatus.NEEDS_EVIDENCE
    assert receipt.decision is WaveFourCompletionReceiptDecision.HOLD_FOR_EVIDENCE
    assert "check:docket-digest-present" in receipt.failed_evidence_check_ids
    assert "digest is missing or malformed" in receipt.readiness_gaps[0]


def test_receipt_holds_for_evidence_when_context_is_missing() -> None:
    receipt = build_wave_four_completion_receipt(
        receipt_id="completion-receipt-gaps",
        review_docket=FakeDocket(
            all_evidence_ids=(),
            scenario_ids=(),
            blackfox_receipt_ids=(),
            reviewer_assignments=(),
        ),
    )

    assert receipt.status is WaveFourCompletionReceiptStatus.NEEDS_EVIDENCE
    assert "check:evidence-present" in receipt.failed_evidence_check_ids
    assert "check:reviewers-present" in receipt.failed_evidence_check_ids
    assert "check:scenarios-present" in receipt.failed_evidence_check_ids
    assert "check:blackfox-receipts-present" in receipt.failed_evidence_check_ids


def test_receipt_needs_repair_when_docket_needs_repair() -> None:
    receipt = build_wave_four_completion_receipt(
        receipt_id="completion-receipt-repair",
        review_docket=FakeDocket(
            status=WaveFourReviewDocketStatus.NEEDS_REPAIR,
            readiness_gaps=("docket repair required",),
        ),
    )

    assert receipt.status is WaveFourCompletionReceiptStatus.NEEDS_REPAIR
    assert receipt.decision is WaveFourCompletionReceiptDecision.HOLD_FOR_REPAIR
    assert "check:docket-ready" in receipt.failed_repair_check_ids
    assert "docket repair required" in receipt.readiness_gaps[0]


def test_receipt_blocks_when_human_authority_is_not_required() -> None:
    receipt = build_wave_four_completion_receipt(
        receipt_id="completion-receipt-blocked-authority",
        review_docket=FakeDocket(
            human_authority_state=WaveFourAuthorityState.BLOCKED,
        ),
    )

    assert receipt.status is WaveFourCompletionReceiptStatus.BLOCKED
    assert receipt.decision is WaveFourCompletionReceiptDecision.BLOCK_RECORD
    assert "check:human-authority-required" in receipt.failed_blocking_check_ids
    assert receipt.blocking_gaps == (
        "blocking completion receipt check failed: check:human-authority-required",
    )


def test_receipt_reports_missing_check_coverage() -> None:
    check = WaveFourRecordCheck(
        check_id="check:evidence-present",
        check_kind=WaveFourRecordCheckKind.EVIDENCE_PRESENT,
        severity=WaveFourRecordCheckSeverity.EVIDENCE,
        passed=True,
        summary="Evidence ids are present.",
    )
    receipt = WaveFourCompletionReceipt(
        receipt_id="completion-receipt-incomplete",
        review_docket=ready_docket(),
        record_checks=(check,),
    )

    assert receipt.status is WaveFourCompletionReceiptStatus.NEEDS_EVIDENCE
    assert WaveFourRecordCheckKind.DOCKET_READY in receipt.missing_required_check_kinds
    assert "missing completion receipt check coverage" in receipt.readiness_gaps[0]


def test_receipt_rejects_execution_promotion_agi_validation_and_production() -> None:
    checks = ready_receipt().record_checks
    docket = ready_docket()

    with pytest.raises(ValueError, match="cannot permit execution"):
        WaveFourCompletionReceipt(
            receipt_id="invalid-execution",
            review_docket=docket,
            record_checks=checks,
            permits_automatic_execution=True,
        )

    with pytest.raises(ValueError, match="cannot permit promotion"):
        WaveFourCompletionReceipt(
            receipt_id="invalid-promotion",
            review_docket=docket,
            record_checks=checks,
            permits_automatic_promotion=True,
        )

    with pytest.raises(ValueError, match="cannot claim AGI"):
        WaveFourCompletionReceipt(
            receipt_id="invalid-agi",
            review_docket=docket,
            record_checks=checks,
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="cannot claim independent validation"):
        WaveFourCompletionReceipt(
            receipt_id="invalid-validation",
            review_docket=docket,
            record_checks=checks,
            independently_validated=True,
        )

    with pytest.raises(ValueError, match="cannot claim production readiness"):
        WaveFourCompletionReceipt(
            receipt_id="invalid-production",
            review_docket=docket,
            record_checks=checks,
            production_ready=True,
        )


def test_receipt_converts_to_readiness_artifact_and_bundle() -> None:
    receipt = ready_receipt()
    artifact = receipt.to_artifact_ref()
    bundle = receipt.to_artifact_bundle()

    assert artifact.kind is WaveFourArtifactKind.READINESS_SNAPSHOT
    assert artifact.capability_area is WaveFourCapabilityArea.AUDIT_TRAIL
    assert artifact.ready_for_controlled_review is True
    assert artifact.allowed_for_automatic_execution is False
    assert artifact.claims_agi is False
    assert bundle.has_required_kind_coverage is True
    assert bundle.has_required_capability_coverage is True
    assert bundle.ready_for_controlled_review_artifact_ids == (artifact.artifact_id,)


def test_receipt_fingerprint_is_deterministic_despite_check_order() -> None:
    first = ready_receipt()
    second = WaveFourCompletionReceipt(
        receipt_id="completion-receipt-001",
        review_docket=ready_docket(),
        record_checks=tuple(reversed(first.record_checks)),
    )

    assert first.fingerprint() == second.fingerprint()
    assert len(first.fingerprint()) == 64
