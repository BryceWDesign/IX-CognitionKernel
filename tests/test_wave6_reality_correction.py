import pytest

from ix_cognition_kernel.wave6_contracts import (
    WaveSixClaimBoundary,
    WaveSixDecisionState,
    WaveSixLoopStage,
)
from ix_cognition_kernel.wave6_reality_correction import (
    WaveSixCorrectionDecision,
    WaveSixRealityCorrectionLedger,
    WaveSixRealityCorrectionRecord,
    WaveSixRealitySignalKind,
    build_wave_six_reality_correction_ledger,
)


def _record(
    *,
    record_id: str = "correction-1",
    changes_future_reasoning: bool = True,
    correction_decision: WaveSixCorrectionDecision = (
        WaveSixCorrectionDecision.UPDATE_FUTURE_REASONING
    ),
    affected_memory_ids: tuple[str, ...] = ("memory-causal-assumption-1",),
    decision: WaveSixDecisionState = WaveSixDecisionState.READY_FOR_WAVE_SIX_LOOP,
) -> WaveSixRealityCorrectionRecord:
    return WaveSixRealityCorrectionRecord(
        record_id=record_id,
        prediction_summary="The prior causal assumption predicted outcome A.",
        measured_outcome_summary="Measured reality produced outcome B instead.",
        reality_signal_kind=WaveSixRealitySignalKind.FAILED_PREDICTION,
        prediction_evidence_ids=("prediction-evidence-1",),
        outcome_evidence_ids=("outcome-evidence-1",),
        prior_reasoning_fingerprint="prior-reasoning-fingerprint-1",
        corrected_reasoning_summary=(
            "Future reasoning must reduce confidence in the original causal "
            "assumption and test the corrected condition first."
        ),
        affected_memory_ids=affected_memory_ids,
        correction_decision=correction_decision,
        decision=decision,
        changes_future_reasoning=changes_future_reasoning,
    )


def test_reality_correction_record_proves_future_reasoning_change() -> None:
    record = _record()

    assert record.evidence_bound
    assert record.review_ready
    assert not record.blocks_claim
    assert record.proves_reality_corrected_future_reasoning
    assert record.combined_evidence_ids == (
        "prediction-evidence-1",
        "outcome-evidence-1",
    )
    assert record.fingerprint() == record.fingerprint()
    assert len(record.fingerprint()) == 64


def test_reality_correction_converts_to_memory_update_step() -> None:
    record = _record()
    step = record.to_memory_update_step()

    assert step.step_id == "memory-update-correction-1"
    assert step.stage is WaveSixLoopStage.MEMORY_UPDATE
    assert step.measured_reality_signal
    assert step.changes_future_reasoning
    assert step.evidence_ids == record.combined_evidence_ids
    assert step.review_ready


def test_reality_correction_record_rejects_agi_claim() -> None:
    with pytest.raises(ValueError, match="must not claim AGI"):
        WaveSixRealityCorrectionRecord(
            record_id="agi-claim",
            prediction_summary="Prediction.",
            measured_outcome_summary="Outcome.",
            reality_signal_kind=WaveSixRealitySignalKind.OBSERVED_OUTCOME,
            prediction_evidence_ids=("prediction-evidence",),
            outcome_evidence_ids=("outcome-evidence",),
            prior_reasoning_fingerprint="prior",
            corrected_reasoning_summary="Correction.",
            affected_memory_ids=("memory-1",),
            correction_decision=WaveSixCorrectionDecision.UPDATE_FUTURE_REASONING,
            claims_agi=True,
            changes_future_reasoning=True,
        )


def test_reality_correction_record_rejects_autonomous_execution() -> None:
    with pytest.raises(ValueError, match="must not allow autonomous execution"):
        WaveSixRealityCorrectionRecord(
            record_id="autonomous-correction",
            prediction_summary="Prediction.",
            measured_outcome_summary="Outcome.",
            reality_signal_kind=WaveSixRealitySignalKind.OBSERVED_OUTCOME,
            prediction_evidence_ids=("prediction-evidence",),
            outcome_evidence_ids=("outcome-evidence",),
            prior_reasoning_fingerprint="prior",
            corrected_reasoning_summary="Correction.",
            affected_memory_ids=("memory-1",),
            correction_decision=WaveSixCorrectionDecision.UPDATE_FUTURE_REASONING,
            allows_autonomous_execution=True,
            changes_future_reasoning=True,
        )


def test_future_reasoning_change_requires_affected_memory_ids() -> None:
    with pytest.raises(ValueError, match="affected memory identifiers"):
        _record(affected_memory_ids=())


def test_future_reasoning_change_rejects_record_only_decision() -> None:
    with pytest.raises(ValueError, match="record-only correction decision"):
        _record(correction_decision=WaveSixCorrectionDecision.RECORD_ONLY)


def test_reality_correction_record_requires_all_claim_boundaries() -> None:
    with pytest.raises(ValueError, match="required claim boundary"):
        WaveSixRealityCorrectionRecord(
            record_id="missing-boundaries",
            prediction_summary="Prediction.",
            measured_outcome_summary="Outcome.",
            reality_signal_kind=WaveSixRealitySignalKind.OBSERVED_OUTCOME,
            prediction_evidence_ids=("prediction-evidence",),
            outcome_evidence_ids=("outcome-evidence",),
            prior_reasoning_fingerprint="prior",
            corrected_reasoning_summary="Correction.",
            affected_memory_ids=("memory-1",),
            correction_decision=WaveSixCorrectionDecision.UPDATE_FUTURE_REASONING,
            claim_boundaries=(WaveSixClaimBoundary.NO_AGI_CLAIM,),
            changes_future_reasoning=True,
        )


def test_reality_correction_ledger_accepts_required_proof_record() -> None:
    ledger = build_wave_six_reality_correction_ledger(
        ledger_id="ledger-1",
        records=(_record(record_id="correction-b"), _record(record_id="correction-a")),
        notes=("Reality correction changed future reasoning.",),
    )

    assert ledger.record_ids == ("correction-a", "correction-b")
    assert ledger.proof_record_ids == ("correction-a", "correction-b")
    assert ledger.blocking_record_ids == ()
    assert ledger.has_required_reality_correction_proof
    assert ledger.ready_for_wave_six_memory_update
    assert ledger.fingerprint() == ledger.fingerprint()
    assert len(ledger.fingerprint()) == 64


def test_reality_correction_ledger_fails_without_required_proof() -> None:
    ledger = WaveSixRealityCorrectionLedger(
        ledger_id="ledger-no-proof",
        records=(
            _record(
                changes_future_reasoning=False,
                correction_decision=WaveSixCorrectionDecision.RECORD_ONLY,
                affected_memory_ids=(),
            ),
        ),
    )

    assert ledger.proof_record_ids == ()
    assert not ledger.has_required_reality_correction_proof
    assert not ledger.ready_for_wave_six_memory_update


def test_reality_correction_ledger_blocks_on_blocking_record() -> None:
    ledger = WaveSixRealityCorrectionLedger(
        ledger_id="ledger-blocked",
        records=(
            _record(
                correction_decision=WaveSixCorrectionDecision.BLOCK_CLAIM,
                decision=WaveSixDecisionState.BLOCKED,
            ),
        ),
    )

    assert ledger.blocking_record_ids == ("correction-1",)
    assert not ledger.ready_for_wave_six_memory_update


def test_reality_correction_ledger_rejects_duplicate_record_ids() -> None:
    record = _record()

    with pytest.raises(ValueError, match="Duplicate record_id"):
        WaveSixRealityCorrectionLedger(
            ledger_id="ledger-duplicate",
            records=(record, record),
        )
