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
    *,
    step_id: str,
    stage: WaveSixLoopStage,
    prior_step_id: str | None = None,
    evidence_ids: tuple[str, ...] = ("evidence-1",),
    decision: WaveSixDecisionState = WaveSixDecisionState.READY_FOR_WAVE_SIX_LOOP,
    measured_reality_signal: bool = False,
    changes_future_reasoning: bool = False,
) -> WaveSixMasterLoopStep:
    return WaveSixMasterLoopStep(
        step_id=step_id,
        stage=stage,
        summary=f"Wave 6 {stage.value} step.",
        source_system=WaveSixSourceSystem.IX_COGNITION_KERNEL,
        evidence_ids=evidence_ids,
        prior_step_id=prior_step_id,
        decision=decision,
        measured_reality_signal=measured_reality_signal,
        changes_future_reasoning=changes_future_reasoning,
    )


def _complete_steps() -> tuple[WaveSixMasterLoopStep, ...]:
    prior_step_id: str | None = None
    steps: list[WaveSixMasterLoopStep] = []
    for index, stage in enumerate(WAVE_SIX_REQUIRED_LOOP_STAGES, start=1):
        step_id = f"step-{index:02d}-{stage.value}"
        step = _step(
            step_id=step_id,
            stage=stage,
            prior_step_id=prior_step_id,
            evidence_ids=(f"evidence-{stage.value}",),
            measured_reality_signal=stage
            in {
                WaveSixLoopStage.OUTCOME,
                WaveSixLoopStage.DELTA,
                WaveSixLoopStage.MEMORY_UPDATE,
            },
            changes_future_reasoning=stage is WaveSixLoopStage.MEMORY_UPDATE,
        )
        steps.append(step)
        prior_step_id = step_id
    return tuple(steps)


def _trace(
    *,
    steps: tuple[WaveSixMasterLoopStep, ...] | None = None,
    objective: str = (
        "Prove whether measured reality corrected future reasoning under bounded "
        "Wave 6 review."
    ),
) -> WaveSixMasterLoopTrace:
    return WaveSixMasterLoopTrace(
        trace_id="wave6-master-loop-trace",
        objective=objective,
        steps=steps or _complete_steps(),
        notes=("This is a bounded measured-cognition trace, not an AGI claim.",),
    )


def test_master_loop_step_is_evidence_bound_and_fingerprinted() -> None:
    step = _step(
        step_id="step-01-intent",
        stage=WaveSixLoopStage.INTENT,
        evidence_ids=("intent-evidence",),
    )

    assert step.evidence_bound
    assert step.review_ready
    assert not step.blocks_progress
    assert step.fingerprint() == step.fingerprint()
    assert len(step.fingerprint()) == 64


def test_master_loop_step_rejects_empty_identity_and_evidence() -> None:
    with pytest.raises(ValueError, match="step_id must not be empty"):
        _step(step_id=" ", stage=WaveSixLoopStage.INTENT)

    with pytest.raises(ValueError, match="require evidence ids"):
        _step(
            step_id="step-no-evidence",
            stage=WaveSixLoopStage.INTENT,
            evidence_ids=(),
        )


def test_master_loop_step_rejects_future_reasoning_change_without_reality_signal() -> None:
    with pytest.raises(ValueError, match="requires measured reality correction"):
        _step(
            step_id="step-invalid-future-change",
            stage=WaveSixLoopStage.MEMORY_UPDATE,
            measured_reality_signal=False,
            changes_future_reasoning=True,
        )


def test_master_loop_step_blocks_progress_when_decision_is_blocked() -> None:
    step = _step(
        step_id="step-blocked",
        stage=WaveSixLoopStage.FALSIFICATION,
        decision=WaveSixDecisionState.BLOCKED,
    )

    assert step.blocks_progress
    assert not step.review_ready


def test_master_loop_trace_is_ready_when_stage_order_and_evidence_are_complete() -> None:
    trace = build_wave_six_master_loop_trace(
        trace_id="wave6-trace-ready",
        objective=(
            "Show the intent to permission to prediction to trial to outcome to "
            "delta to memory update to transfer check to falsification to human "
            "review loop."
        ),
        steps=_complete_steps(),
        notes=("Ready means human review ready, not AGI achieved.",),
    )

    assert trace.stage_sequence == WAVE_SIX_REQUIRED_LOOP_STAGES
    assert trace.step_ids == tuple(step.step_id for step in _complete_steps())
    assert trace.missing_stages == ()
    assert trace.out_of_order_stage_pairs == ()
    assert trace.invalid_prior_links == ()
    assert trace.evidence_missing_step_ids == ()
    assert trace.blocked_step_ids == ()
    assert trace.reality_corrected_reasoning_step_ids == (
        "step-07-memory-update",
    )
    assert trace.readiness is WaveSixLoopReadiness.READY_FOR_HUMAN_REVIEW
    assert trace.ready_for_human_review
    assert trace.fingerprint() == trace.fingerprint()
    assert len(trace.fingerprint()) == 64


def test_master_loop_trace_reports_missing_stage() -> None:
    trace = _trace(steps=_complete_steps()[:-1])

    assert trace.missing_stages == (WaveSixLoopStage.HUMAN_REVIEW,)
    assert trace.readiness is WaveSixLoopReadiness.INCOMPLETE
    assert not trace.ready_for_human_review


def test_master_loop_trace_reports_out_of_order_stage_pair() -> None:
    steps = list(_complete_steps())
    steps[2], steps[3] = steps[3], steps[2]
    trace = _trace(steps=tuple(steps))

    assert trace.out_of_order_stage_pairs == (
        (WaveSixLoopStage.TRIAL, WaveSixLoopStage.PREDICTION),
    )
    assert trace.readiness is WaveSixLoopReadiness.INCOMPLETE
    assert not trace.ready_for_human_review


def test_master_loop_trace_reports_invalid_prior_links() -> None:
    steps = list(_complete_steps())
    steps[4] = _step(
        step_id="step-05-outcome",
        stage=WaveSixLoopStage.OUTCOME,
        prior_step_id="not-the-trial-step",
        evidence_ids=("evidence-outcome",),
        measured_reality_signal=True,
    )
    trace = _trace(steps=tuple(steps))

    assert trace.invalid_prior_links == ("step-05-outcome",)
    assert trace.readiness is WaveSixLoopReadiness.INCOMPLETE


def test_master_loop_trace_reports_steps_missing_evidence() -> None:
    steps = list(_complete_steps())
    steps[0] = WaveSixMasterLoopStep(
        step_id="step-01-intent",
        stage=WaveSixLoopStage.INTENT,
        summary="Intent step is present but not review-ready.",
        source_system=WaveSixSourceSystem.IX_COGNITION_KERNEL,
        evidence_ids=(),
        decision=WaveSixDecisionState.RECORD_ONLY,
    )
    trace = _trace(steps=tuple(steps))

    assert trace.evidence_missing_step_ids == ("step-01-intent",)
    assert trace.readiness is WaveSixLoopReadiness.INCOMPLETE
    assert not trace.ready_for_human_review


def test_master_loop_trace_blocks_when_any_step_blocks_progress() -> None:
    steps = list(_complete_steps())
    steps[8] = _step(
        step_id="step-09-falsification",
        stage=WaveSixLoopStage.FALSIFICATION,
        prior_step_id="step-08-transfer-check",
        evidence_ids=("evidence-falsification",),
        decision=WaveSixDecisionState.BLOCKED,
    )
    trace = _trace(steps=tuple(steps))

    assert trace.blocked_step_ids == ("step-09-falsification",)
    assert trace.readiness is WaveSixLoopReadiness.BLOCKED
    assert not trace.ready_for_human_review


def test_master_loop_trace_requires_reality_corrected_future_reasoning_step() -> None:
    steps = tuple(
        _step(
            step_id=step.step_id,
            stage=step.stage,
            prior_step_id=step.prior_step_id,
            evidence_ids=step.evidence_ids,
            decision=step.decision,
            measured_reality_signal=step.measured_reality_signal,
            changes_future_reasoning=False,
        )
        for step in _complete_steps()
    )
    trace = _trace(steps=steps)

    assert trace.reality_corrected_reasoning_step_ids == ()
    assert trace.readiness is WaveSixLoopReadiness.INCOMPLETE
    assert not trace.ready_for_human_review


def test_master_loop_trace_rejects_duplicate_step_ids() -> None:
    step = _step(step_id="duplicate-step", stage=WaveSixLoopStage.INTENT)

    with pytest.raises(ValueError, match="Duplicate step_id"):
        _trace(steps=(step, step))


def test_master_loop_trace_lookup_returns_step_for_stage() -> None:
    trace = _trace()
    step = trace.step_for_stage(WaveSixLoopStage.MEMORY_UPDATE)

    assert step is not None
    assert step.step_id == "step-07-memory-update"
    assert trace.step_for_stage(WaveSixLoopStage.HUMAN_REVIEW) is not None
