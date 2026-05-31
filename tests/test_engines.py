import pytest

from ix_cognition_kernel.engines import (
    REQUIRED_ENGINES,
    EngineCategory,
    blocked_failure_modes,
    engine_by_id,
    engine_ids,
    engine_names,
    engines_by_category,
    engines_introduced_by_wave,
)


def test_required_engine_registry_has_locked_count_and_order() -> None:
    assert engine_ids() == (
        "belief",
        "uncertainty",
        "causal-world-model",
        "plan-graph",
        "evaluator",
        "self-play-curriculum",
        "skill-genome",
        "outcome-learning",
        "memory-quarantine",
        "multi-agent-tribunal",
        "reward-auditor",
        "blackfox-handoff",
        "non-attached-purpose",
    )
    assert len(REQUIRED_ENGINES) == 13


def test_engine_names_preserve_locked_required_engines() -> None:
    assert engine_names() == (
        "Belief Engine",
        "Uncertainty Engine",
        "Causal World Model Engine",
        "Plan Graph Engine",
        "Evaluator Engine",
        "Self-Play / Curriculum Engine",
        "Skill Genome Engine",
        "Outcome Learning Engine",
        "Memory Quarantine Engine",
        "Multi-Agent Tribunal Engine",
        "Reward Auditor Engine",
        "BlackFox Handoff Engine",
        "Nirvana / Non-Attached Purpose Layer",
    )


def test_belief_engine_blocks_raw_output_becoming_truth() -> None:
    engine = engine_by_id("belief")

    assert engine.category is EngineCategory.EPISTEMIC
    assert "raw model output cannot become truth" in engine.purpose
    assert "belief-record" in engine.required_outputs
    assert "hallucinated-truth" in engine.blocked_failure_modes


def test_uncertainty_engine_tracks_unsafe_to_act_state() -> None:
    engine = engine_by_id("uncertainty")

    assert "unsafe to act on" in engine.purpose
    assert "actionability-limit" in engine.required_outputs
    assert "unknown-hidden-as-known" in engine.blocked_failure_modes


def test_causal_world_model_requires_predictions_before_action() -> None:
    engine = engine_by_id("causal-world-model")

    assert engine.category is EngineCategory.MODELING
    assert "counterfactuals" in engine.purpose
    assert "prediction" in engine.required_outputs
    assert "action-without-prediction" in engine.blocked_failure_modes


def test_evaluator_engine_rejects_vibes_validation() -> None:
    engine = engine_by_id("evaluator")

    assert engine.category is EngineCategory.EVALUATION
    assert "pass-fail-result" in engine.required_outputs
    assert "no-vibes-validation" in engine.blocked_failure_modes


def test_reward_auditor_blocks_metric_over_mission() -> None:
    engine = engine_by_id("reward-auditor")

    assert engine.category is EngineCategory.GOVERNANCE
    assert "objective mismatch" in engine.purpose
    assert "reward-audit" in engine.required_outputs
    assert "metric-over-mission" in engine.blocked_failure_modes


def test_blackfox_handoff_blocks_ungoverned_execution() -> None:
    engine = engine_by_id("blackfox-handoff")

    assert engine.category is EngineCategory.HANDOFF
    assert "evidence-bound" in engine.purpose
    assert "handoff-package" in engine.required_outputs
    assert "execution-without-evidence" in engine.blocked_failure_modes


def test_non_attached_purpose_layer_is_truth_and_authority_bound() -> None:
    engine = engine_by_id("non-attached-purpose")

    assert engine.category is EngineCategory.PURPOSE
    assert "truth over winning" in engine.purpose
    assert "human authority" in engine.purpose
    assert "runtime-reward-chasing" in engine.blocked_failure_modes


def test_engine_category_queries_return_expected_sets() -> None:
    epistemic = engines_by_category(EngineCategory.EPISTEMIC)
    learning = engines_by_category(EngineCategory.LEARNING)

    assert tuple(engine.engine_id for engine in epistemic) == ("belief", "uncertainty")
    assert tuple(engine.engine_id for engine in learning) == (
        "self-play-curriculum",
        "skill-genome",
        "outcome-learning",
    )


def test_wave_introduction_queries_are_locked() -> None:
    wave_one = engines_introduced_by_wave(1)
    wave_two = engines_introduced_by_wave(2)
    wave_three = engines_introduced_by_wave(3)

    assert tuple(engine.engine_id for engine in wave_one) == (
        "belief",
        "uncertainty",
        "plan-graph",
        "evaluator",
        "non-attached-purpose",
    )
    assert tuple(engine.engine_id for engine in wave_two) == (
        "causal-world-model",
        "skill-genome",
        "outcome-learning",
        "memory-quarantine",
    )
    assert tuple(engine.engine_id for engine in wave_three) == (
        "self-play-curriculum",
        "multi-agent-tribunal",
        "reward-auditor",
        "blackfox-handoff",
    )


def test_unknown_engine_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown IX-CognitionKernel engine id"):
        engine_by_id("agi-magic")


def test_every_engine_declares_inputs_outputs_and_blocked_failures() -> None:
    for engine in REQUIRED_ENGINES:
        assert engine.required_inputs
        assert engine.required_outputs
        assert engine.blocked_failure_modes
        assert 1 <= engine.introduced_by_wave <= 3


def test_blocked_failure_modes_include_core_danger_threads() -> None:
    failures = blocked_failure_modes()

    assert "specification-gaming" in failures
    assert "reward-hacking" in failures
    assert "agent-theater" in failures
    assert "memory-poisoning" in failures
    assert "model-self-approval" in failures
