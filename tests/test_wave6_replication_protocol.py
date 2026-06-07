import pytest

from ix_cognition_kernel.wave6_replication_protocol import (
    WAVE_SIX_REQUIRED_REPLICATION_STEP_KINDS,
    WaveSixReplicationDecision,
    WaveSixReplicationProtocol,
    WaveSixReplicationStep,
    WaveSixReplicationStepKind,
    WaveSixReplicationStepStatus,
    build_wave_six_replication_protocol,
    required_wave_six_replication_step_kinds,
)


def _step(
    kind: WaveSixReplicationStepKind,
    *,
    step_id: str | None = None,
    status: WaveSixReplicationStepStatus = WaveSixReplicationStepStatus.PASSED,
    blocks_claim: bool = False,
) -> WaveSixReplicationStep:
    return WaveSixReplicationStep(
        step_id=step_id or f"step-{kind.value}",
        kind=kind,
        instruction=f"Replay and verify the {kind.value} artifact.",
        expected_artifact_ids=(f"artifact-{kind.value}",),
        expected_fingerprints=(f"fingerprint-{kind.value}",),
        pass_criteria=(f"The {kind.value} fingerprint recomputes exactly.",),
        evidence_ids=(f"evidence-{kind.value}",),
        status=status,
        reviewer_notes=("Replication is bounded review, not an AGI claim.",),
        blocks_claim=blocks_claim,
    )


def _complete_steps(
    *,
    status: WaveSixReplicationStepStatus = WaveSixReplicationStepStatus.PASSED,
) -> tuple[WaveSixReplicationStep, ...]:
    return tuple(
        _step(kind, status=status)
        for kind in WAVE_SIX_REQUIRED_REPLICATION_STEP_KINDS
    )


def _protocol(
    *,
    steps: tuple[WaveSixReplicationStep, ...] | None = None,
    decision: WaveSixReplicationDecision = (
        WaveSixReplicationDecision.REPLICATION_PASSED
    ),
    claims_agi: bool = False,
) -> WaveSixReplicationProtocol:
    return WaveSixReplicationProtocol(
        protocol_id="replication-protocol-1",
        package_fingerprint="package-fingerprint-1",
        steps=steps or _complete_steps(),
        decision=decision,
        replication_boundary_statement=(
            "Replication checks reproducibility of bounded Wave 6 evidence; it "
            "does not claim AGI, production readiness, certification, or autonomy."
        ),
        claims_agi=claims_agi,
        notes=("External reviewers decide whether replication survives.",),
    )


def test_required_replication_step_kinds_are_locked() -> None:
    assert required_wave_six_replication_step_kinds() == (
        WaveSixReplicationStepKind.ENVIRONMENT_CHECK,
        WaveSixReplicationStepKind.ARTIFACT_FINGERPRINT_REPLAY,
        WaveSixReplicationStepKind.MASTER_LOOP_REPLAY,
        WaveSixReplicationStepKind.REALITY_CORRECTION_REPLAY,
        WaveSixReplicationStepKind.FUTURE_REASONING_REPLAY,
        WaveSixReplicationStepKind.TRANSFER_NOVELTY_REPLAY,
        WaveSixReplicationStepKind.FALSIFICATION_REPLAY,
        WaveSixReplicationStepKind.HUMAN_REVIEW_REPLAY,
        WaveSixReplicationStepKind.CLAIM_BOUNDARY_REPLAY,
    )


def test_replication_step_is_evidence_bound_and_fingerprinted() -> None:
    step = _step(WaveSixReplicationStepKind.MASTER_LOOP_REPLAY)

    assert step.passed
    assert not step.needs_evidence
    assert not step.blocks_replication
    assert step.expected_artifact_ids == ("artifact-master-loop-replay",)
    assert step.fingerprint() == step.fingerprint()
    assert len(step.fingerprint()) == 64


def test_replication_step_rejects_overclaim_and_autonomous_execution() -> None:
    with pytest.raises(ValueError, match="must not claim AGI"):
        WaveSixReplicationStep(
            step_id="agi-step",
            kind=WaveSixReplicationStepKind.CLAIM_BOUNDARY_REPLAY,
            instruction="Invalid AGI step.",
            expected_artifact_ids=("artifact",),
            expected_fingerprints=("fingerprint",),
            pass_criteria=("Criterion.",),
            evidence_ids=("evidence",),
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="must not allow autonomous execution"):
        WaveSixReplicationStep(
            step_id="auto-step",
            kind=WaveSixReplicationStepKind.CLAIM_BOUNDARY_REPLAY,
            instruction="Invalid autonomous step.",
            expected_artifact_ids=("artifact",),
            expected_fingerprints=("fingerprint",),
            pass_criteria=("Criterion.",),
            evidence_ids=("evidence",),
            allows_autonomous_execution=True,
        )


def test_failed_or_blocked_replication_step_must_block_claim() -> None:
    with pytest.raises(ValueError, match="must block the claim"):
        _step(
            WaveSixReplicationStepKind.FALSIFICATION_REPLAY,
            status=WaveSixReplicationStepStatus.FAILED,
            blocks_claim=False,
        )

    with pytest.raises(ValueError, match="must block the claim"):
        _step(
            WaveSixReplicationStepKind.HUMAN_REVIEW_REPLAY,
            status=WaveSixReplicationStepStatus.BLOCKED,
            blocks_claim=False,
        )


def test_passed_replication_step_cannot_block_claim() -> None:
    with pytest.raises(ValueError, match="cannot block the claim"):
        _step(
            WaveSixReplicationStepKind.MASTER_LOOP_REPLAY,
            status=WaveSixReplicationStepStatus.PASSED,
            blocks_claim=True,
        )


def test_replication_protocol_passes_when_all_steps_pass() -> None:
    protocol = build_wave_six_replication_protocol(
        protocol_id="replication-protocol-ready",
        package_fingerprint="package-fingerprint-1",
        steps=_complete_steps(),
        decision=WaveSixReplicationDecision.REPLICATION_PASSED,
        replication_boundary_statement="Replicates bounded evidence only.",
        notes=("No AGI claim is made by replication.",),
    )

    assert protocol.present_step_kinds == WAVE_SIX_REQUIRED_REPLICATION_STEP_KINDS
    assert protocol.missing_step_kinds == ()
    assert protocol.needs_evidence_step_ids == ()
    assert protocol.blocking_step_ids == ()
    assert protocol.replication_passed
    assert not protocol.blocks_claim
    assert protocol.fingerprint() == protocol.fingerprint()
    assert len(protocol.fingerprint()) == 64


def test_replication_protocol_can_be_ready_to_run_before_steps_pass() -> None:
    protocol = _protocol(
        steps=_complete_steps(status=WaveSixReplicationStepStatus.NOT_RUN),
        decision=WaveSixReplicationDecision.READY_FOR_REPLICATION,
    )

    assert protocol.ready_to_run
    assert not protocol.replication_passed
    assert protocol.needs_evidence_step_ids == tuple(
        step.step_id for step in protocol.steps
    )


def test_replication_protocol_reports_missing_step_kind() -> None:
    protocol = WaveSixReplicationProtocol(
        protocol_id="replication-protocol-missing",
        package_fingerprint="package-fingerprint-1",
        steps=_complete_steps()[:-1],
        decision=WaveSixReplicationDecision.NEEDS_MORE_EVIDENCE,
        replication_boundary_statement="Incomplete replication protocol.",
    )

    assert protocol.missing_step_kinds == (
        WaveSixReplicationStepKind.CLAIM_BOUNDARY_REPLAY,
    )
    assert not protocol.replication_passed


def test_passed_replication_protocol_rejects_missing_or_unrun_steps() -> None:
    with pytest.raises(ValueError, match="requires every step kind"):
        WaveSixReplicationProtocol(
            protocol_id="replication-protocol-invalid-missing",
            package_fingerprint="package-fingerprint-1",
            steps=_complete_steps()[:-1],
            decision=WaveSixReplicationDecision.REPLICATION_PASSED,
            replication_boundary_statement="Invalid passed protocol.",
        )

    with pytest.raises(ValueError, match="cannot need more evidence"):
        _protocol(
            steps=_complete_steps(status=WaveSixReplicationStepStatus.NOT_RUN),
            decision=WaveSixReplicationDecision.REPLICATION_PASSED,
        )


def test_replication_protocol_blocks_on_blocking_step() -> None:
    steps = list(_complete_steps())
    steps[6] = _step(
        WaveSixReplicationStepKind.FALSIFICATION_REPLAY,
        status=WaveSixReplicationStepStatus.FAILED,
        blocks_claim=True,
    )
    protocol = WaveSixReplicationProtocol(
        protocol_id="replication-protocol-blocked",
        package_fingerprint="package-fingerprint-1",
        steps=tuple(steps),
        decision=WaveSixReplicationDecision.BLOCK_CLAIM,
        replication_boundary_statement="Failed falsification replay blocks the claim.",
    )

    assert protocol.blocking_step_ids == ("step-falsification-replay",)
    assert protocol.blocks_claim
    assert not protocol.replication_passed


def test_blocked_replication_protocol_requires_blocking_step() -> None:
    with pytest.raises(ValueError, match="requires a blocking step"):
        _protocol(decision=WaveSixReplicationDecision.BLOCK_CLAIM)


def test_replication_protocol_rejects_overclaim_and_duplicate_steps() -> None:
    with pytest.raises(ValueError, match="must not claim AGI"):
        _protocol(
            decision=WaveSixReplicationDecision.NEEDS_MORE_EVIDENCE,
            claims_agi=True,
        )

    step = _step(WaveSixReplicationStepKind.MASTER_LOOP_REPLAY)
    with pytest.raises(ValueError, match="Duplicate step_id"):
        _protocol(
            steps=(step, step),
            decision=WaveSixReplicationDecision.NEEDS_MORE_EVIDENCE,
        )


def test_replication_protocol_step_lookup_returns_present_kind_only() -> None:
    protocol = WaveSixReplicationProtocol(
        protocol_id="replication-protocol-lookup",
        package_fingerprint="package-fingerprint-1",
        steps=(_step(WaveSixReplicationStepKind.MASTER_LOOP_REPLAY),),
        decision=WaveSixReplicationDecision.NEEDS_MORE_EVIDENCE,
        replication_boundary_statement="Partial lookup protocol.",
    )

    step = protocol.step_for_kind(WaveSixReplicationStepKind.MASTER_LOOP_REPLAY)

    assert step is not None
    assert step.step_id == "step-master-loop-replay"
    assert (
        protocol.step_for_kind(WaveSixReplicationStepKind.FALSIFICATION_REPLAY)
        is None
    )
