import pytest

from ix_cognition_kernel.wave6_contracts import (
    WAVE_SIX_REQUIRED_LOOP_STAGES,
    WaveSixLoopStage,
    WaveSixSourceSystem,
)
from ix_cognition_kernel.wave6_loop_blueprints import (
    WAVE_SIX_CANONICAL_OBJECTIVE,
    WAVE_SIX_CANONICAL_TRACE_ID,
    WaveSixLoopStepBlueprint,
    build_canonical_wave_six_master_loop_trace,
    canonical_wave_six_loop_step_blueprints,
)
from ix_cognition_kernel.wave6_master_loop import WaveSixLoopReadiness


def test_canonical_loop_blueprints_match_required_stage_order() -> None:
    blueprints = canonical_wave_six_loop_step_blueprints()

    assert tuple(blueprint.stage for blueprint in blueprints) == (
        WAVE_SIX_REQUIRED_LOOP_STAGES
    )
    assert len({blueprint.blueprint_id for blueprint in blueprints}) == len(blueprints)
    assert len({blueprint.step_id for blueprint in blueprints}) == len(blueprints)
    assert all(blueprint.evidence_ids for blueprint in blueprints)
    assert all(blueprint.summary for blueprint in blueprints)


def test_canonical_loop_blueprints_assign_expected_source_systems() -> None:
    source_by_stage = {
        blueprint.stage: blueprint.source_system
        for blueprint in canonical_wave_six_loop_step_blueprints()
    }

    assert source_by_stage == {
        WaveSixLoopStage.INTENT: WaveSixSourceSystem.IX_MAIN,
        WaveSixLoopStage.PERMISSION: (
            WaveSixSourceSystem.IX_AUTONOMY_ASSURANCE_RUNTIME
        ),
        WaveSixLoopStage.PREDICTION: WaveSixSourceSystem.IX_BLACKFOX_WORLDTWIN,
        WaveSixLoopStage.TRIAL: WaveSixSourceSystem.IX_BLACKFOX,
        WaveSixLoopStage.OUTCOME: WaveSixSourceSystem.IX_INTENT_REALITY_LOOP,
        WaveSixLoopStage.DELTA: WaveSixSourceSystem.IX_BLACKFOX_WORLDTWIN,
        WaveSixLoopStage.MEMORY_UPDATE: WaveSixSourceSystem.IX_COGNITION_KERNEL,
        WaveSixLoopStage.TRANSFER_CHECK: WaveSixSourceSystem.IX_FUNCTION,
        WaveSixLoopStage.FALSIFICATION: WaveSixSourceSystem.IX_FUNCTION,
        WaveSixLoopStage.HUMAN_REVIEW: WaveSixSourceSystem.HUMAN_REVIEW,
    }


def test_canonical_loop_blueprints_mark_only_memory_update_as_future_change() -> None:
    future_change_blueprints = tuple(
        blueprint
        for blueprint in canonical_wave_six_loop_step_blueprints()
        if blueprint.changes_future_reasoning
    )

    assert tuple(blueprint.stage for blueprint in future_change_blueprints) == (
        WaveSixLoopStage.MEMORY_UPDATE,
    )
    assert all(
        blueprint.measured_reality_signal for blueprint in future_change_blueprints
    )


def test_canonical_master_loop_trace_is_ready_for_human_review() -> None:
    trace = build_canonical_wave_six_master_loop_trace()

    assert trace.trace_id == WAVE_SIX_CANONICAL_TRACE_ID
    assert trace.objective == WAVE_SIX_CANONICAL_OBJECTIVE
    assert trace.stage_sequence == WAVE_SIX_REQUIRED_LOOP_STAGES
    assert trace.step_ids == tuple(
        blueprint.step_id for blueprint in canonical_wave_six_loop_step_blueprints()
    )
    assert trace.invalid_prior_links == ()
    assert trace.out_of_order_stage_pairs == ()
    assert trace.missing_stages == ()
    assert trace.evidence_missing_step_ids == ()
    assert trace.readiness is WaveSixLoopReadiness.READY_FOR_HUMAN_REVIEW
    assert trace.ready_for_human_review
    assert trace.reality_corrected_reasoning_step_ids == ("step-07-memory-update",)
    assert len(trace.fingerprint()) == 64
    assert trace.fingerprint() == trace.fingerprint()


def test_blueprint_to_step_preserves_prior_link_and_evidence() -> None:
    blueprint = canonical_wave_six_loop_step_blueprints()[2]
    step = blueprint.to_step(prior_step_id="step-02-permission")

    assert step.step_id == blueprint.step_id
    assert step.stage is WaveSixLoopStage.PREDICTION
    assert step.prior_step_id == "step-02-permission"
    assert step.evidence_ids == blueprint.evidence_ids
    assert step.source_system is blueprint.source_system
    assert step.review_ready


def test_loop_step_blueprint_rejects_future_change_without_reality_signal() -> None:
    with pytest.raises(ValueError, match="requires measured reality correction"):
        WaveSixLoopStepBlueprint(
            blueprint_id="invalid-future-change",
            stage=WaveSixLoopStage.MEMORY_UPDATE,
            source_system=WaveSixSourceSystem.IX_COGNITION_KERNEL,
            summary="Invalid future-reasoning change without measured reality.",
            evidence_ids=("evidence-invalid",),
            changes_future_reasoning=True,
            measured_reality_signal=False,
        )


def test_loop_step_blueprint_rejects_empty_evidence() -> None:
    with pytest.raises(ValueError, match="require evidence ids"):
        WaveSixLoopStepBlueprint(
            blueprint_id="invalid-no-evidence",
            stage=WaveSixLoopStage.INTENT,
            source_system=WaveSixSourceSystem.IX_MAIN,
            summary="Invalid blueprint without evidence.",
            evidence_ids=(),
        )
