import pytest

from ix_cognition_kernel.wave6_contracts import (
    WAVE_SIX_REQUIRED_LOOP_STAGES,
    WaveSixDecisionState,
    WaveSixLoopStage,
    WaveSixSourceSystem,
)
from ix_cognition_kernel.wave6_master_loop import (
    WaveSixLoopReadiness,
    WaveSixMasterLoopStep,
    WaveSixMasterLoopTrace,
    build_wave_six_master_loop_trace,
)


def _step(
    stage: WaveSixLoopStage,
    *,
    step_id: str | None = None,
    prior_step_id: str | None = None,
    evidence_ids: tuple[str, ...] = ("evidence-1",),
    decision: WaveSixDecisionState = WaveSixDecisionState.READY_FOR_WAVE_SIX_LOOP,
    measured_reality_signal: bool = False,
    changes_future_reasoning: bool = False,
    source_system: WaveSixSourceSystem = WaveSixSourceSystem.IX_COGNITION_KERNEL,
) -> WaveSixMasterLoopStep:
    return WaveSixMasterLoopStep(
        step_id=step_id or f"step-{stage.value}",
        stage=stage,
        summary=f"Wave 6 loop step for {stage.value}.",
        source_system=source_system,
        evidence_ids=evidence_ids,
        prior_step_id=prior_step_id,
        decision=decision,
        measured_reality_signal=measured_reality_signal,
        changes_future_reasoning=changes_future_reasoning,
    )


def _complete_steps() -> tuple[WaveSixMasterLoopStep, ...]:
    steps: list[WaveSixMasterLoopStep] = []
    prior_step_id: str | None = None
    for stage in WAVE_SIX_REQUIRED_LOOP_STAGES:
        step = _step(
            stage,
            step_id=f"step-{len(steps) + 1:02d}-{stage.value}",
            prior_step_id=prior_step_id,
            measured_reality_signal=stage
            in {
                WaveSixLoopStage.OUTCOME,
                WaveSixLoopStage.DELTA,
                WaveSixLoopStage.MEMORY_UPDATE,
            },
            changes_future_reasoning=stage is WaveSixLoopStage.MEMORY_UPDATE,
        )
        steps.append(step)
        prior_step_id = step.step_id
    return tuple(steps)


def test_master_loop_trace_accepts_clean_complete_ordered_loop() -> None:
    trace = build_wave_six_master_loop_trace(
        trace_id="trace-1",
        objective="Measure whether reality correction changes future reasoning.",
        steps=_complete_steps(),
        notes=("No AGI claim is made by this trace.",),
    )

    assert trace.stage_sequence == WAVE_SIX_REQUIRED_LOOP_STAGES
    assert trace.covered_stages == WAVE_SIX_REQUIRED_LOOP_STAGES
    assert trace.missing_stages == ()
    assert trace.out_of_order_stage_pairs == ()
    assert trace.invalid_prior_links == ()
    assert trace.evidence_missing_step_ids == ()
    assert trace.blocked_step_ids == ()
    assert trace.has_complete_required_order
    assert trace.readiness is WaveSixLoopReadiness.READY_FOR_HUMAN_REVIEW
    assert trace.ready_for_human_review
    assert trace.reality_corrected_reasoning_step_ids == (
        "step-07-memory-update",
    )
    assert trace.fingerprint() == trace.fingerprint()
    assert len(trace.fingerprint()) == 64


def test_master_loop_trace_reports_incomplete_loop_without_pretending_ready() -> None:
    trace = WaveSixMasterLoopTrace(
        trace_id="trace-incomplete",
        objective="Partial trace must fail closed until every stage exists.",
        steps=(
            _step(WaveSixLoopStage.INTENT),
            _step(
                WaveSixLoopStage.PERMISSION,
                step_id="step-permission",
                prior_step_id="step-intent",
            ),
        ),
    )

    assert trace.readiness is WaveSixLoopReadiness.INCOMPLETE
    assert WaveSixLoopStage.PREDICTION in trace.missing_stages
    assert not trace.ready_for_human_review


def test_master_loop_trace_reports_out_of_order_stage_pairs() -> None:
    trace = WaveSixMasterLoopTrace(
        trace_id="trace-order-invalid",
        objective="Out-of-order loop stages must fail closed.",
        steps=(
            _step(WaveSixLoopStage.PERMISSION, step_id="permission"),
            _step(
                WaveSixLoopStage.INTENT,
                step_id="intent",
                prior_step_id="permission",
            ),
        ),
    )

    assert trace.out_of_order_stage_pairs == (
        (WaveSixLoopStage.PERMISSION, WaveSixLoopStage.INTENT),
    )
    assert trace.readiness is WaveSixLoopReadiness.INCOMPLETE
    assert not trace.ready_for_human_review


def test_complete_loop_with_invalid_prior_link_fails_order_validation() -> None:
    steps = list(_complete_steps())
    steps[2] = _step(
        WaveSixLoopStage.PREDICTION,
        step_id="step-03-prediction",
        prior_step_id="wrong-prior",
    )
    trace = WaveSixMasterLoopTrace(
        trace_id="trace-bad-prior",
        objective="Complete traces still need clean predecessor links.",
        steps=tuple(steps),
    )

    assert trace.missing_stages == ()
    assert trace.invalid_prior_links == ("step-03-prediction",)
    assert trace.readiness is WaveSixLoopReadiness.ORDER_INVALID


def test_master_loop_trace_reports_evidence_missing_after_complete_order() -> None:
    steps = list(_complete_steps())
    steps[3] = _step(
        WaveSixLoopStage.TRIAL,
        step_id="step-04-trial",
        prior_step_id="step-03-prediction",
        evidence_ids=(),
        decision=WaveSixDecisionState.NEEDS_MORE_EVIDENCE,
    )
    trace = WaveSixMasterLoopTrace(
        trace_id="trace-missing-evidence",
        objective="Complete traces without evidence must fail closed.",
        steps=tuple(steps),
    )

    assert trace.missing_stages == ()
    assert trace.evidence_missing_step_ids == ("step-04-trial",)
    assert trace.readiness is WaveSixLoopReadiness.EVIDENCE_MISSING


def test_master_loop_trace_reports_blocked_step_first() -> None:
    steps = list(_complete_steps())
    steps[8] = _step(
        WaveSixLoopStage.FALSIFICATION,
        step_id="step-09-falsification",
        prior_step_id="step-08-transfer-check",
        decision=WaveSixDecisionState.BLOCKED,
    )
    trace = WaveSixMasterLoopTrace(
        trace_id="trace-blocked",
        objective="Blocked falsification must block Wave 6 review.",
        steps=tuple(steps),
    )

    assert trace.blocked_step_ids == ("step-09-falsification",)
    assert trace.readiness is WaveSixLoopReadiness.BLOCKED
    assert not trace.ready_for_human_review


def test_loop_step_rejects_future_reasoning_change_without_reality_signal() -> None:
    with pytest.raises(ValueError, match="requires a measured reality signal"):
        _step(
            WaveSixLoopStage.MEMORY_UPDATE,
            changes_future_reasoning=True,
            measured_reality_signal=False,
        )


def test_loop_step_rejects_autonomous_execution() -> None:
    with pytest.raises(ValueError, match="must not allow autonomous execution"):
        WaveSixMasterLoopStep(
            step_id="autonomous-step",
            stage=WaveSixLoopStage.TRIAL,
            summary="Invalid autonomous Wave 6 trial step.",
            source_system=WaveSixSourceSystem.IX_COGNITION_KERNEL,
            evidence_ids=("evidence-autonomous",),
            allows_autonomous_execution=True,
        )


def test_master_loop_trace_rejects_duplicate_stage() -> None:
    with pytest.raises(ValueError, match="Duplicate loop stage"):
        WaveSixMasterLoopTrace(
            trace_id="trace-duplicate-stage",
            objective="Duplicate stages would make the loop ambiguous.",
            steps=(
                _step(WaveSixLoopStage.INTENT, step_id="intent-1"),
                _step(WaveSixLoopStage.INTENT, step_id="intent-2"),
            ),
        )


def test_master_loop_trace_rejects_duplicate_step_ids() -> None:
    with pytest.raises(ValueError, match="Duplicate step_id"):
        WaveSixMasterLoopTrace(
            trace_id="trace-duplicate-step",
            objective="Duplicate step identifiers would break reviewability.",
            steps=(
                _step(WaveSixLoopStage.INTENT, step_id="duplicate"),
                _step(WaveSixLoopStage.PERMISSION, step_id="duplicate"),
            ),
        )


def test_step_for_stage_returns_present_stage_only() -> None:
    trace = WaveSixMasterLoopTrace(
        trace_id="trace-stage-lookup",
        objective="Look up present loop steps by stage.",
        steps=(
            _step(WaveSixLoopStage.INTENT),
            _step(
                WaveSixLoopStage.PERMISSION,
                step_id="step-permission",
                prior_step_id="step-intent",
            ),
        ),
    )

    intent_step = trace.step_for_stage(WaveSixLoopStage.INTENT)

    assert intent_step is not None
    assert intent_step.step_id == "step-intent"
    assert trace.step_for_stage(WaveSixLoopStage.PREDICTION) is None
