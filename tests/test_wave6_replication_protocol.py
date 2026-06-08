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
        instruction=f"Replay the {kind.value} artifact and compare fingerprints.",
        expected_artifact_ids=(f"artifact-{kind.value}",),
        expected_fingerprints=(f"fingerprint-{kind.value}",),
        pass_criteria=(f"{kind.value} fingerprint recomputes exactly.",),
        evidence_ids=(f"evidence-{kind.value}",),
        status=status,
        reviewer_notes=("Replication remains bounded review evidence.",),
        blocks_claim=blocks_claim,
    )


def _complete_steps() -> tuple[WaveSixReplicationStep, ...]:
    return tuple(_step(kind) for kind in WAVE_SIX_REQUIRED_REPLICATION_STEP_KINDS)


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
            "Replication checks bounded Wave 6 evidence only. It is not an AGI, "
            "production, certification, or autonomous authority claim."
        ),
        claims_agi=claims_agi,
        notes=("Independent reviewers must be able to recompute evidence.",),
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


def test_replication_step_is_passed_and_fingerprinted() -> None:
    step = _step(WaveSixReplicationStepKind.MASTER_LOOP_REPLAY)

    assert step.passed
    assert not step.needs_evidence
    assert not step.blocks_replication
    assert step.fingerprint() == step.fingerprint()
    assert len(step.fingerprint()) == 64


def test_replication_step_reports_not_run_as_needing_evidence() -> None:
    step = _step(
        WaveSixReplicationStepKind.REALITY_CORRECTION_REPLAY,
        status=WaveSixReplicationStepStatus.NOT_RUN,
    )

    assert not step.passed
    assert step.needs_evidence
    assert not step.blocks_replication


def test_replication_step_enforces_failed_and_blocked_semantics() -> None:
    with pytest.raises(ValueError, match="must block the claim"):
        _step(
            WaveSixReplicationStepKind.FALSIFICATION_REPLAY,
            status=WaveSixReplicationStepStatus.FAILED,
        )

    with pytest.raises(ValueError, match="must block the claim"):
        _step(
            WaveSixReplicationStepKind.HUMAN_REVIEW_REPLAY,
            status=WaveSixReplicationStepStatus.BLOCKED,
        )

    with pytest.raises(ValueError, match="cannot block the claim"):
        _step(
            WaveSixReplicationStepKind.CLAIM_BOUNDARY_REPLAY,
            status=WaveSixReplicationStepStatus.PASSED,
            blocks_claim=True,
        )


def test_replication_step_rejects_overclaims_and_autonomous_execution() -> None:
    with pytest.raises(ValueError, match="must not claim AGI"):
        WaveSixReplicationStep(
            step_id="step-agi",
            kind=WaveSixReplicationStepKind.CLAIM_BOUNDARY_REPLAY,
            instruction="Invalid AGI replication step.",
            expected_artifact_ids=("artifact-agi",),
            expected_fingerprints=("fingerprint-agi",),
            pass_criteria=("No AGI claim is allowed.",),
            evidence_ids=("evidence-agi",),
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="must not allow autonomous execution"):
        WaveSixReplicationStep(
            step_id="step-autonomous",
            kind=WaveSixReplicationStepKind.HUMAN_REVIEW_REPLAY,
            instruction="Invalid autonomous replication step.",
            expected_artifact_ids=("artifact-autonomous",),
            expected_fingerprints=("fingerprint-autonomous",),
            pass_criteria=("Human review remains required.",),
            evidence_ids=("evidence-autonomous",),
            allows_autonomous_execution=True,
        )


def test_replication_step_requires_artifacts_fingerprints_and_evidence() -> None:
    with pytest.raises(ValueError, match="require expected artifact ids"):
        WaveSixReplicationStep(
            step_id="step-no-artifacts",
            kind=WaveSixReplicationStepKind.ENVIRONMENT_CHECK,
            instruction="Invalid step without expected artifacts.",
            expected_artifact_ids=(),
            expected_fingerprints=("fingerprint",),
            pass_criteria=("Pass criterion.",),
            evidence_ids=("evidence",),
        )

    with pytest.raises(ValueError, match="require expected fingerprints"):
        WaveSixReplicationStep(
            step_id="step-no-fingerprints",
            kind=WaveSixReplicationStepKind.ENVIRONMENT_CHECK,
            instruction="Invalid step without expected fingerprints.",
            expected_artifact_ids=("artifact",),
            expected_fingerprints=(),
            pass_criteria=("Pass criterion.",),
            evidence_ids=("evidence",),
        )

    with pytest.raises(ValueError, match="require evidence ids"):
        WaveSixReplicationStep(
            step_id="step-no-evidence",
            kind=WaveSixReplicationStepKind.ENVIRONMENT_CHECK,
            instruction="Invalid step without evidence.",
            expected_artifact_ids=("artifact",),
            expected_fingerprints=("fingerprint",),
            pass_criteria=("Pass criterion.",),
            evidence_ids=(),
        )


def test_replication_protocol_passes_when_all_required_steps_pass() -> None:
    protocol = build_wave_six_replication_protocol(
        protocol_id="replication-protocol-ready",
        package_fingerprint="package-fingerprint-1",
        steps=_complete_steps(),
        decision=WaveSixReplicationDecision.REPLICATION_PASSED,
        replication_boundary_statement="Replication passed for bounded review only.",
        notes=("This remains independent review evidence, not AGI proof.",),
    )

    assert protocol.present_step_kinds == WAVE_SIX_REQUIRED_REPLICATION_STEP_KINDS
    assert protocol.missing_step_kinds == ()
    assert protocol.needs_evidence_step_ids == ()
    assert protocol.blocking_step_ids == ()
    assert protocol.passed_step_ids == tuple(
        f"step-{kind.value}" for kind in WAVE_SIX_REQUIRED_REPLICATION_STEP_KINDS
    )
    assert protocol.replication_passed
    assert not protocol.blocks_claim
    assert protocol.fingerprint() == protocol.fingerprint()
    assert len(protocol.fingerprint()) == 64


def test_replication_protocol_reports_ready_to_run_before_steps_pass() -> None:
    steps = tuple(
        _step(kind, status=WaveSixReplicationStepStatus.NOT_RUN)
        for kind in WAVE_SIX_REQUIRED_REPLICATION_STEP_KINDS
    )
    protocol = _protocol(
        steps=steps,
        decision=WaveSixReplicationDecision.READY_FOR_REPLICATION,
    )

    assert protocol.ready_to_run
    assert not protocol.replication_passed
    assert protocol.needs_evidence_step_ids == tuple(
        f"step-{kind.value}" for kind in WAVE_SIX_REQUIRED_REPLICATION_STEP_KINDS
    )


def test_replication_protocol_reports_missing_step_kind() -> None:
    protocol = _protocol(
        steps=_complete_steps()[:-1],
        decision=WaveSixReplicationDecision.NEEDS_MORE_EVIDENCE,
    )

    assert protocol.missing_step_kinds == (
        WaveSixReplicationStepKind.CLAIM_BOUNDARY_REPLAY,
    )
    assert not protocol.replication_passed


def test_replication_protocol_tracks_inconclusive_step() -> None:
    steps = list(_complete_steps())
    steps[4] = _step(
        WaveSixReplicationStepKind.FUTURE_REASONING_REPLAY,
        status=WaveSixReplicationStepStatus.INCONCLUSIVE,
    )
    protocol = _protocol(
        steps=tuple(steps),
        decision=WaveSixReplicationDecision.NEEDS_MORE_EVIDENCE,
    )

    assert protocol.needs_evidence_step_ids == ("step-future-reasoning-replay",)
    assert not protocol.replication_passed
    assert not protocol.blocks_claim


def test_replication_protocol_blocks_on_failed_step_or_overclaim() -> None:
    steps = list(_complete_steps())
    steps[6] = _step(
        WaveSixReplicationStepKind.FALSIFICATION_REPLAY,
        status=WaveSixReplicationStepStatus.FAILED,
        blocks_claim=True,
    )
    blocked = _protocol(
        steps=tuple(steps),
        decision=WaveSixReplicationDecision.BLOCK_CLAIM,
    )

    assert blocked.blocking_step_ids == ("step-falsification-replay",)
    assert blocked.blocks_claim
    assert not blocked.replication_passed

    with pytest.raises(ValueError, match="must not claim AGI"):
        _protocol(
            decision=WaveSixReplicationDecision.BLOCK_CLAIM,
            claims_agi=True,
        )


def test_passed_replication_protocol_rejects_missing_or_unrun_steps() -> None:
    with pytest.raises(ValueError, match="requires every step kind"):
        _protocol(steps=_complete_steps()[:-1])

    steps = list(_complete_steps())
    steps[1] = _step(
        WaveSixReplicationStepKind.ARTIFACT_FINGERPRINT_REPLAY,
        status=WaveSixReplicationStepStatus.NOT_RUN,
    )

    with pytest.raises(ValueError, match="cannot need more evidence"):
        _protocol(steps=tuple(steps))


def test_blocked_replication_protocol_requires_blocking_step() -> None:
    with pytest.raises(ValueError, match="requires a blocking step"):
        _protocol(decision=WaveSixReplicationDecision.BLOCK_CLAIM)


def test_replication_protocol_lookup_and_duplicate_rejection() -> None:
    protocol = _protocol(
        steps=(_step(WaveSixReplicationStepKind.ENVIRONMENT_CHECK),),
        decision=WaveSixReplicationDecision.NEEDS_MORE_EVIDENCE,
    )

    step = protocol.step_for_kind(WaveSixReplicationStepKind.ENVIRONMENT_CHECK)

    assert step is not None
    assert step.step_id == "step-environment-check"
    assert (
        protocol.step_for_kind(WaveSixReplicationStepKind.CLAIM_BOUNDARY_REPLAY) is None
    )

    duplicate = _step(WaveSixReplicationStepKind.ENVIRONMENT_CHECK)
    with pytest.raises(ValueError, match="Duplicate step_id"):
        _protocol(
            steps=(duplicate, duplicate),
            decision=WaveSixReplicationDecision.NEEDS_MORE_EVIDENCE,
        )

    with pytest.raises(ValueError, match="Duplicate step kind"):
        _protocol(
            steps=(
                duplicate,
                _step(
                    WaveSixReplicationStepKind.ENVIRONMENT_CHECK,
                    step_id="different-step-id",
                ),
            ),
            decision=WaveSixReplicationDecision.NEEDS_MORE_EVIDENCE,
        )
