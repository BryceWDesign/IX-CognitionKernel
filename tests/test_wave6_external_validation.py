import pytest

from ix_cognition_kernel.wave6_challenge_suite import (
    WAVE_SIX_REQUIRED_CHALLENGE_KINDS,
    WaveSixChallengeCase,
    WaveSixChallengeDecision,
    WaveSixChallengeKind,
    WaveSixChallengeOutcome,
    WaveSixChallengeSuite,
)
from ix_cognition_kernel.wave6_external_validation import (
    WaveSixExternalValidationBlocker,
    WaveSixExternalValidationGate,
    WaveSixExternalValidationStatus,
    WaveSixExternalValidationSummary,
    WaveSixExternalValidationSurface,
    build_wave_six_external_validation_gate,
)
from ix_cognition_kernel.wave6_replication_protocol import (
    WAVE_SIX_REQUIRED_REPLICATION_STEP_KINDS,
    WaveSixReplicationDecision,
    WaveSixReplicationProtocol,
    WaveSixReplicationStep,
    WaveSixReplicationStepKind,
    WaveSixReplicationStepStatus,
)
from ix_cognition_kernel.wave6_trial_replay import (
    WAVE_SIX_REQUIRED_REPLAY_STAGES,
    WaveSixReplayDecision,
    WaveSixReplayOutcome,
    WaveSixReplayStage,
    WaveSixTrialReplayLedger,
    WaveSixTrialReplayRecord,
)


def _case(kind: WaveSixChallengeKind) -> WaveSixChallengeCase:
    return WaveSixChallengeCase(
        case_id=f"case-{kind.value}",
        kind=kind,
        title=f"{kind.value} challenge",
        challenge_prompt="Apply corrected reasoning under independent pressure.",
        hidden_constraint_summary="A hidden constraint prevents prompt replay.",
        measurable_success_criteria=("Prediction precedes outcome evidence.",),
        expected_failure_modes=("The system ignores the hidden constraint.",),
        evidence_ids=(f"evidence-{kind.value}",),
        outcome=WaveSixChallengeOutcome.PASSED,
        decision=WaveSixChallengeDecision.ACCEPT_FOR_REVIEW,
    )


def _challenge_suite() -> WaveSixChallengeSuite:
    return WaveSixChallengeSuite(
        suite_id="challenge-suite-ready",
        cases=tuple(_case(kind) for kind in WAVE_SIX_REQUIRED_CHALLENGE_KINDS),
    )


def _step(kind: WaveSixReplicationStepKind) -> WaveSixReplicationStep:
    return WaveSixReplicationStep(
        step_id=f"step-{kind.value}",
        kind=kind,
        instruction=f"Replay {kind.value}.",
        expected_artifact_ids=(f"artifact-{kind.value}",),
        expected_fingerprints=(f"fingerprint-{kind.value}",),
        pass_criteria=("Fingerprint recomputes exactly.",),
        evidence_ids=(f"evidence-{kind.value}",),
        status=WaveSixReplicationStepStatus.PASSED,
        reviewer_notes=("Replication remains a bounded evidence check.",),
    )


def _replication_protocol() -> WaveSixReplicationProtocol:
    return WaveSixReplicationProtocol(
        protocol_id="replication-ready",
        package_fingerprint="package-fingerprint",
        steps=tuple(_step(kind) for kind in WAVE_SIX_REQUIRED_REPLICATION_STEP_KINDS),
        decision=WaveSixReplicationDecision.REPLICATION_PASSED,
        replication_boundary_statement="Replication is not an AGI claim.",
    )


def _replay_record(stage: WaveSixReplayStage) -> WaveSixTrialReplayRecord:
    return WaveSixTrialReplayRecord(
        replay_id=f"replay-{stage.value}",
        stage=stage,
        original_artifact_id=f"artifact-{stage.value}",
        expected_fingerprint=f"fingerprint-{stage.value}",
        observed_fingerprint=f"fingerprint-{stage.value}",
        expected_evidence_ids=(f"expected-{stage.value}",),
        observed_evidence_ids=(f"observed-{stage.value}",),
        outcome=WaveSixReplayOutcome.MATCHED,
        decision=WaveSixReplayDecision.ACCEPT_FOR_REVIEW,
        reviewer_notes=("Replay remains bounded evidence review.",),
    )


def _trial_replay_ledger() -> WaveSixTrialReplayLedger:
    return WaveSixTrialReplayLedger(
        ledger_id="replay-ledger-ready",
        records=tuple(
            _replay_record(stage) for stage in WAVE_SIX_REQUIRED_REPLAY_STAGES
        ),
    )


def _gate(
    *,
    challenge_suite: WaveSixChallengeSuite | None = None,
    replication_protocol: WaveSixReplicationProtocol | None = None,
    trial_replay_ledger: WaveSixTrialReplayLedger | None = None,
    claims_agi: bool = False,
) -> WaveSixExternalValidationGate:
    return WaveSixExternalValidationGate(
        gate_id="external-validation-gate",
        challenge_suite=challenge_suite or _challenge_suite(),
        replication_protocol=replication_protocol or _replication_protocol(),
        trial_replay_ledger=trial_replay_ledger or _trial_replay_ledger(),
        validation_boundary_statement=(
            "External validation reviews bounded Wave 6 evidence only; it is not "
            "an AGI, production, certification, or authority claim."
        ),
        claims_agi=claims_agi,
        notes=("External reviewers decide whether evidence survives.",),
    )


def test_validation_summary_requires_evidence_and_clean_ready_state() -> None:
    summary = WaveSixExternalValidationSummary(
        summary_id="summary-1",
        surface=WaveSixExternalValidationSurface.TRIAL_REPLAY_LEDGER,
        artifact_fingerprint="fingerprint",
        ready=True,
        blocking_ids=(),
        needs_more_evidence_ids=(),
        evidence_ids=("evidence-1",),
        reviewer_question="Can replay be reproduced?",
    )

    assert summary.ready
    assert not summary.blocked
    assert not summary.needs_more_evidence
    assert summary.fingerprint() == summary.fingerprint()
    assert len(summary.fingerprint()) == 64


def test_ready_validation_summary_rejects_blockers_or_missing_evidence() -> None:
    with pytest.raises(ValueError, match="cannot include blockers"):
        WaveSixExternalValidationSummary(
            summary_id="summary-blocked-ready",
            surface=WaveSixExternalValidationSurface.TRIAL_REPLAY_LEDGER,
            artifact_fingerprint="fingerprint",
            ready=True,
            blocking_ids=("blocker-1",),
            needs_more_evidence_ids=(),
            evidence_ids=("evidence-1",),
            reviewer_question="Can replay be reproduced?",
        )

    with pytest.raises(ValueError, match="require evidence ids"):
        WaveSixExternalValidationSummary(
            summary_id="summary-no-evidence",
            surface=WaveSixExternalValidationSurface.TRIAL_REPLAY_LEDGER,
            artifact_fingerprint="fingerprint",
            ready=False,
            blocking_ids=(),
            needs_more_evidence_ids=("missing-1",),
            evidence_ids=(),
            reviewer_question="Can replay be reproduced?",
        )


def test_external_validation_gate_is_ready_when_all_surfaces_pass() -> None:
    gate = build_wave_six_external_validation_gate(
        gate_id="gate-ready",
        challenge_suite=_challenge_suite(),
        replication_protocol=_replication_protocol(),
        trial_replay_ledger=_trial_replay_ledger(),
        validation_boundary_statement="Bounded external validation only.",
        notes=("No AGI claim is made.",),
    )

    assert gate.blockers == ()
    assert gate.blocking_summary_ids == ()
    assert gate.needs_more_evidence_summary_ids == ()
    assert gate.status is (
        WaveSixExternalValidationStatus.READY_FOR_EXTERNAL_VALIDATION_REVIEW
    )
    assert gate.ready_for_external_validation_review
    assert not gate.overclaim_present
    assert len(gate.summaries) == 3
    assert gate.fingerprint() == gate.fingerprint()
    assert len(gate.fingerprint()) == 64


def test_external_validation_gate_reports_challenge_suite_gap() -> None:
    challenge_suite = WaveSixChallengeSuite(
        suite_id="challenge-suite-gap",
        cases=tuple(_case(kind) for kind in WAVE_SIX_REQUIRED_CHALLENGE_KINDS[:-1]),
    )
    gate = _gate(challenge_suite=challenge_suite)

    assert WaveSixExternalValidationBlocker.CHALLENGE_SUITE_NOT_READY in gate.blockers
    assert gate.status is WaveSixExternalValidationStatus.NEEDS_MORE_EVIDENCE
    assert "summary-independent-challenge-suite" in gate.needs_more_evidence_summary_ids
    assert not gate.ready_for_external_validation_review


def test_external_validation_gate_blocks_on_failed_challenge_case() -> None:
    cases = list(_challenge_suite().cases)
    cases[4] = WaveSixChallengeCase(
        case_id="case-negative-control",
        kind=WaveSixChallengeKind.NEGATIVE_CONTROL,
        title="Failed negative control",
        challenge_prompt="Run the negative control.",
        hidden_constraint_summary="The decoy lacks the causal condition.",
        measurable_success_criteria=("The system withholds the claim.",),
        expected_failure_modes=("The system falsely transfers.",),
        evidence_ids=("evidence-negative-control",),
        outcome=WaveSixChallengeOutcome.FAILED,
        decision=WaveSixChallengeDecision.BLOCK_CLAIM,
    )
    gate = _gate(
        challenge_suite=WaveSixChallengeSuite("challenge-blocked", tuple(cases))
    )

    assert WaveSixExternalValidationBlocker.CHALLENGE_CASE_BLOCKED in gate.blockers
    assert gate.status is WaveSixExternalValidationStatus.BLOCKED
    assert gate.blocking_summary_ids == ("summary-independent-challenge-suite",)


def test_external_validation_gate_reports_replication_not_passed() -> None:
    protocol = WaveSixReplicationProtocol(
        protocol_id="replication-not-run",
        package_fingerprint="package-fingerprint",
        steps=tuple(
            WaveSixReplicationStep(
                step_id=f"step-{kind.value}",
                kind=kind,
                instruction=f"Replay {kind.value}.",
                expected_artifact_ids=(f"artifact-{kind.value}",),
                expected_fingerprints=(f"fingerprint-{kind.value}",),
                pass_criteria=("Fingerprint recomputes exactly.",),
                evidence_ids=(f"evidence-{kind.value}",),
                status=WaveSixReplicationStepStatus.NOT_RUN,
            )
            for kind in WAVE_SIX_REQUIRED_REPLICATION_STEP_KINDS
        ),
        decision=WaveSixReplicationDecision.READY_FOR_REPLICATION,
        replication_boundary_statement="Ready to run replication.",
    )
    gate = _gate(replication_protocol=protocol)

    assert WaveSixExternalValidationBlocker.REPLICATION_NOT_PASSED in gate.blockers
    assert gate.status is WaveSixExternalValidationStatus.NEEDS_MORE_EVIDENCE
    assert "summary-independent-replication-protocol" in (
        gate.needs_more_evidence_summary_ids
    )


def test_external_validation_gate_blocks_on_failed_replication_step() -> None:
    steps = tuple(
        WaveSixReplicationStep(
            step_id="step-falsification-replay",
            kind=kind,
            instruction="Replay falsification.",
            expected_artifact_ids=("artifact-falsification",),
            expected_fingerprints=("fingerprint-falsification",),
            pass_criteria=("Falsification replay passes.",),
            evidence_ids=("evidence-falsification",),
            status=WaveSixReplicationStepStatus.FAILED,
            blocks_claim=True,
        )
        if kind is WaveSixReplicationStepKind.FALSIFICATION_REPLAY
        else _step(kind)
        for kind in WAVE_SIX_REQUIRED_REPLICATION_STEP_KINDS
    )
    protocol = WaveSixReplicationProtocol(
        protocol_id="replication-blocked",
        package_fingerprint="package-fingerprint",
        steps=steps,
        decision=WaveSixReplicationDecision.BLOCK_CLAIM,
        replication_boundary_statement="Failed replication blocks claim.",
    )
    gate = _gate(replication_protocol=protocol)

    assert WaveSixExternalValidationBlocker.REPLICATION_STEP_BLOCKED in gate.blockers
    assert gate.status is WaveSixExternalValidationStatus.BLOCKED
    assert gate.blocking_summary_ids == ("summary-independent-replication-protocol",)


def test_external_validation_gate_reports_replay_not_ready() -> None:
    ledger = WaveSixTrialReplayLedger(
        ledger_id="replay-ledger-gap",
        records=_trial_replay_ledger().records[:-1],
    )
    gate = _gate(trial_replay_ledger=ledger)

    assert WaveSixExternalValidationBlocker.TRIAL_REPLAY_NOT_READY in gate.blockers
    assert gate.status is WaveSixExternalValidationStatus.NEEDS_MORE_EVIDENCE
    assert "summary-trial-replay-ledger" in gate.needs_more_evidence_summary_ids


def test_external_validation_gate_blocks_on_diverged_replay() -> None:
    records = tuple(
        WaveSixTrialReplayRecord(
            replay_id="replay-transfer-replay",
            stage=stage,
            original_artifact_id="artifact-transfer",
            expected_fingerprint="expected-transfer",
            observed_fingerprint="observed-transfer",
            expected_evidence_ids=("expected-transfer",),
            observed_evidence_ids=("observed-transfer",),
            outcome=WaveSixReplayOutcome.DIVERGED,
            decision=WaveSixReplayDecision.BLOCK_CLAIM,
            reviewer_notes=("Transfer replay diverged.",),
        )
        if stage is WaveSixReplayStage.TRANSFER_REPLAY
        else _replay_record(stage)
        for stage in WAVE_SIX_REQUIRED_REPLAY_STAGES
    )
    ledger = WaveSixTrialReplayLedger("replay-ledger-blocked", records)
    gate = _gate(trial_replay_ledger=ledger)

    assert WaveSixExternalValidationBlocker.TRIAL_REPLAY_BLOCKED in gate.blockers
    assert gate.status is WaveSixExternalValidationStatus.BLOCKED
    assert gate.blocking_summary_ids == ("summary-trial-replay-ledger",)


def test_external_validation_gate_blocks_on_overclaim() -> None:
    gate = _gate(claims_agi=True)

    assert gate.overclaim_present
    assert WaveSixExternalValidationBlocker.OVERCLAIM_PRESENT in gate.blockers
    assert gate.status is WaveSixExternalValidationStatus.BLOCKED
    assert not gate.ready_for_external_validation_review


def test_external_validation_gate_rejects_empty_identity() -> None:
    with pytest.raises(ValueError, match="gate_id must not be empty"):
        WaveSixExternalValidationGate(
            gate_id=" ",
            challenge_suite=_challenge_suite(),
            replication_protocol=_replication_protocol(),
            trial_replay_ledger=_trial_replay_ledger(),
            validation_boundary_statement="Bounded validation only.",
        )
