import pytest

from ix_cognition_kernel.wave6_trial_replay import (
    WAVE_SIX_REQUIRED_REPLAY_STAGES,
    WaveSixReplayDecision,
    WaveSixReplayOutcome,
    WaveSixReplayStage,
    WaveSixTrialReplayLedger,
    WaveSixTrialReplayRecord,
    build_wave_six_trial_replay_ledger,
    required_wave_six_replay_stages,
)


def _record(
    stage: WaveSixReplayStage,
    *,
    replay_id: str | None = None,
    outcome: WaveSixReplayOutcome = WaveSixReplayOutcome.MATCHED,
    decision: WaveSixReplayDecision = WaveSixReplayDecision.ACCEPT_FOR_REVIEW,
    expected_fingerprint: str | None = None,
    observed_fingerprint: str | None = None,
) -> WaveSixTrialReplayRecord:
    fingerprint = expected_fingerprint or f"fingerprint-{stage.value}"
    return WaveSixTrialReplayRecord(
        replay_id=replay_id or f"replay-{stage.value}",
        stage=stage,
        original_artifact_id=f"artifact-{stage.value}",
        expected_fingerprint=fingerprint,
        observed_fingerprint=observed_fingerprint or fingerprint,
        expected_evidence_ids=(f"expected-evidence-{stage.value}",),
        observed_evidence_ids=(f"observed-evidence-{stage.value}",),
        outcome=outcome,
        decision=decision,
        reviewer_notes=("Replay is bounded evidence review, not an AGI claim.",),
    )


def _complete_records() -> tuple[WaveSixTrialReplayRecord, ...]:
    return tuple(_record(stage) for stage in WAVE_SIX_REQUIRED_REPLAY_STAGES)


def test_required_replay_stages_are_locked() -> None:
    assert required_wave_six_replay_stages() == (
        WaveSixReplayStage.PREDICTION_REPLAY,
        WaveSixReplayStage.TRIAL_REPLAY,
        WaveSixReplayStage.OUTCOME_REPLAY,
        WaveSixReplayStage.DELTA_REPLAY,
        WaveSixReplayStage.MEMORY_UPDATE_REPLAY,
        WaveSixReplayStage.TRANSFER_REPLAY,
        WaveSixReplayStage.FALSIFICATION_REPLAY,
        WaveSixReplayStage.HUMAN_REVIEW_REPLAY,
    )


def test_trial_replay_record_matches_expected_fingerprint() -> None:
    record = _record(WaveSixReplayStage.MEMORY_UPDATE_REPLAY)

    assert record.replay_matched
    assert not record.needs_more_evidence
    assert not record.blocks_claim
    assert record.combined_evidence_ids == (
        "expected-evidence-memory-update-replay",
        "observed-evidence-memory-update-replay",
    )
    assert record.fingerprint() == record.fingerprint()
    assert len(record.fingerprint()) == 64


def test_trial_replay_record_rejects_agi_claim_and_autonomy() -> None:
    with pytest.raises(ValueError, match="must not claim AGI"):
        WaveSixTrialReplayRecord(
            replay_id="agi-replay",
            stage=WaveSixReplayStage.HUMAN_REVIEW_REPLAY,
            original_artifact_id="artifact",
            expected_fingerprint="fingerprint",
            observed_fingerprint="fingerprint",
            expected_evidence_ids=("expected",),
            observed_evidence_ids=("observed",),
            outcome=WaveSixReplayOutcome.NOT_RUN,
            decision=WaveSixReplayDecision.NEEDS_MORE_EVIDENCE,
            reviewer_notes=("Invalid.",),
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="must not allow autonomous execution"):
        WaveSixTrialReplayRecord(
            replay_id="auto-replay",
            stage=WaveSixReplayStage.HUMAN_REVIEW_REPLAY,
            original_artifact_id="artifact",
            expected_fingerprint="fingerprint",
            observed_fingerprint="fingerprint",
            expected_evidence_ids=("expected",),
            observed_evidence_ids=("observed",),
            outcome=WaveSixReplayOutcome.NOT_RUN,
            decision=WaveSixReplayDecision.NEEDS_MORE_EVIDENCE,
            reviewer_notes=("Invalid.",),
            allows_autonomous_execution=True,
        )


def test_matched_replay_requires_identical_fingerprints_and_acceptance() -> None:
    with pytest.raises(ValueError, match="identical fingerprints"):
        _record(
            WaveSixReplayStage.PREDICTION_REPLAY,
            expected_fingerprint="expected",
            observed_fingerprint="observed",
        )

    with pytest.raises(ValueError, match="must be accepted for review"):
        _record(
            WaveSixReplayStage.PREDICTION_REPLAY,
            decision=WaveSixReplayDecision.RECORD_ONLY,
        )


def test_diverged_or_safety_blocked_replay_must_block_claim() -> None:
    with pytest.raises(ValueError, match="must block claim"):
        _record(
            WaveSixReplayStage.TRANSFER_REPLAY,
            outcome=WaveSixReplayOutcome.DIVERGED,
            decision=WaveSixReplayDecision.NEEDS_MORE_EVIDENCE,
        )

    with pytest.raises(ValueError, match="must block claim"):
        _record(
            WaveSixReplayStage.FALSIFICATION_REPLAY,
            outcome=WaveSixReplayOutcome.BLOCKED_BY_SAFETY_GATE,
            decision=WaveSixReplayDecision.NEEDS_MORE_EVIDENCE,
        )


def test_trial_replay_ledger_is_ready_when_all_stages_match() -> None:
    ledger = build_wave_six_trial_replay_ledger(
        ledger_id="replay-ledger-ready",
        records=_complete_records(),
        notes=("Replay matched every required Wave 6 review stage.",),
    )

    assert ledger.present_stages == WAVE_SIX_REQUIRED_REPLAY_STAGES
    assert ledger.missing_stages == ()
    assert ledger.matched_required_stages == WAVE_SIX_REQUIRED_REPLAY_STAGES
    assert ledger.missing_matched_required_stages == ()
    assert ledger.blocking_replay_ids == ()
    assert ledger.needs_more_evidence_replay_ids == ()
    assert ledger.ready_for_replay_review
    assert ledger.fingerprint() == ledger.fingerprint()
    assert len(ledger.fingerprint()) == 64


def test_trial_replay_ledger_reports_missing_stage() -> None:
    ledger = WaveSixTrialReplayLedger(
        ledger_id="replay-ledger-missing",
        records=_complete_records()[:-1],
    )

    assert ledger.missing_stages == (WaveSixReplayStage.HUMAN_REVIEW_REPLAY,)
    assert not ledger.ready_for_replay_review


def test_trial_replay_ledger_reports_unmatched_stage() -> None:
    records = list(_complete_records())
    records[2] = _record(
        WaveSixReplayStage.OUTCOME_REPLAY,
        outcome=WaveSixReplayOutcome.INCONCLUSIVE,
        decision=WaveSixReplayDecision.NEEDS_MORE_EVIDENCE,
    )
    ledger = WaveSixTrialReplayLedger(
        ledger_id="replay-ledger-unmatched",
        records=tuple(records),
    )

    assert ledger.needs_more_evidence_replay_ids == ("replay-outcome-replay",)
    assert WaveSixReplayStage.OUTCOME_REPLAY in ledger.missing_matched_required_stages
    assert not ledger.ready_for_replay_review


def test_trial_replay_ledger_blocks_on_diverged_record() -> None:
    records = list(_complete_records())
    records[5] = _record(
        WaveSixReplayStage.TRANSFER_REPLAY,
        outcome=WaveSixReplayOutcome.DIVERGED,
        decision=WaveSixReplayDecision.BLOCK_CLAIM,
        expected_fingerprint="expected-transfer",
        observed_fingerprint="observed-transfer",
    )
    ledger = WaveSixTrialReplayLedger(
        ledger_id="replay-ledger-blocked",
        records=tuple(records),
    )

    assert ledger.blocking_replay_ids == ("replay-transfer-replay",)
    assert not ledger.ready_for_replay_review


def test_trial_replay_ledger_can_relax_all_matched_requirement() -> None:
    records = list(_complete_records())
    records[0] = _record(
        WaveSixReplayStage.PREDICTION_REPLAY,
        outcome=WaveSixReplayOutcome.INCONCLUSIVE,
        decision=WaveSixReplayDecision.RECORD_ONLY,
    )
    ledger = WaveSixTrialReplayLedger(
        ledger_id="replay-ledger-relaxed",
        records=tuple(records),
        require_all_stages_matched=False,
    )

    assert not ledger.missing_stages
    assert not ledger.needs_more_evidence_replay_ids
    assert ledger.ready_for_replay_review


def test_trial_replay_ledger_lookup_returns_present_stage_only() -> None:
    ledger = WaveSixTrialReplayLedger(
        ledger_id="replay-ledger-lookup",
        records=(_record(WaveSixReplayStage.PREDICTION_REPLAY),),
    )

    record = ledger.record_for_stage(WaveSixReplayStage.PREDICTION_REPLAY)

    assert record is not None
    assert record.replay_id == "replay-prediction-replay"
    assert ledger.record_for_stage(WaveSixReplayStage.TRANSFER_REPLAY) is None


def test_trial_replay_ledger_rejects_duplicates_and_overclaim() -> None:
    record = _record(WaveSixReplayStage.PREDICTION_REPLAY)

    with pytest.raises(ValueError, match="Duplicate replay_id"):
        WaveSixTrialReplayLedger(
            ledger_id="replay-ledger-duplicate-id",
            records=(record, record),
        )

    with pytest.raises(ValueError, match="must not claim AGI"):
        WaveSixTrialReplayLedger(
            ledger_id="replay-ledger-agi",
            records=_complete_records(),
            claims_agi=True,
        )
