import pytest

from ix_cognition_kernel.wave8_environment_protocol import (
    BoundedEnvironmentSpec,
    EnvironmentKind,
    EnvironmentObservation,
)
from ix_cognition_kernel.wave8_model_adapter import (
    BoundedModelOutput,
    DeterministicModelAdapter,
    DeterministicModelPolicy,
    ModelActionDraftDecision,
    build_model_action_draft,
    evaluate_model_output,
)


def _environment() -> BoundedEnvironmentSpec:
    return BoundedEnvironmentSpec(
        environment_id="env-grid-1",
        kind=EnvironmentKind.GRID_ABSTRACTION,
        objective="Infer a bounded grid transition.",
        observation_channels=("grid-visible-state",),
        action_space_ids=("move-east", "inspect-cell"),
        scoring_rules=("score-correct-transition",),
        reset_evidence_ids=("reset-evidence-1",),
    )


def _observation(*, measured: bool = True) -> EnvironmentObservation:
    return EnvironmentObservation(
        observation_id="obs-1",
        environment_id="env-grid-1",
        episode_id="episode-1",
        state_id="state-1",
        channel_id="grid-visible-state",
        summary="The east cell is visibly empty.",
        visible_features=("agent-at-0-0", "east-cell-empty"),
        evidence_ids=("obs-evidence-1",),
        measured=measured,
    )


def _policy(
    *, operation_preferences: tuple[str, ...] = ("move-east",)
) -> DeterministicModelPolicy:
    return DeterministicModelPolicy(
        policy_id="policy-1",
        supported_environment_ids=("env-grid-1",),
        operation_preferences=operation_preferences,
        rationale_template="Use {operation_id} in {environment_id} from {state_id}.",
        expected_effect_template="{operation_id} should produce a bounded transition.",
        evidence_ids=("policy-evidence-1",),
        assumptions=("visible-state-is-current",),
        uncertainty_ids=("uncertainty-grid-transition",),
    )


def _adapter(
    *, operation_preferences: tuple[str, ...] = ("move-east",)
) -> DeterministicModelAdapter:
    return DeterministicModelAdapter(
        adapter_id="deterministic-adapter-1",
        policy=_policy(operation_preferences=operation_preferences),
    )


def test_deterministic_model_adapter_generates_stable_bounded_output() -> None:
    adapter = _adapter()
    environment = _environment()
    observation = _observation()

    first = adapter.generate_output(
        output_id="model-output-1",
        environment=environment,
        observation=observation,
    )
    second = adapter.generate_output(
        output_id="model-output-1",
        environment=environment,
        observation=observation,
    )

    assert first == second
    assert first.selected_operation_id == "move-east"
    assert first.fingerprint() == second.fingerprint()
    assert len(first.fingerprint()) == 64


def test_bounded_model_output_rejects_truth_authority_and_completion_claims() -> None:
    kwargs = {
        "output_id": "bad-output",
        "adapter_id": "adapter-1",
        "environment_id": "env-grid-1",
        "episode_id": "episode-1",
        "observation_id": "obs-1",
        "selected_operation_id": "move-east",
        "rationale": "Bad model claim.",
        "expected_effect": "Bad expected effect.",
        "assumptions": ("assumption-1",),
        "uncertainty_ids": ("uncertainty-1",),
        "evidence_ids": ("evidence-1",),
    }

    with pytest.raises(ValueError, match="must not claim truth"):
        BoundedModelOutput(**kwargs, claims_truth=True)
    with pytest.raises(ValueError, match="must not claim authority"):
        BoundedModelOutput(**kwargs, claims_authority=True)
    with pytest.raises(ValueError, match="must not claim completion"):
        BoundedModelOutput(**kwargs, claims_completion=True)


def test_model_output_evaluation_requires_measured_observation() -> None:
    environment = _environment()
    output = _adapter().generate_output(
        output_id="model-output-1",
        environment=environment,
        observation=_observation(measured=False),
    )

    assert (
        evaluate_model_output(
            environment=environment,
            observation=_observation(measured=False),
            model_output=output,
        )
        is ModelActionDraftDecision.NEEDS_OBSERVATION_EVIDENCE
    )


def test_model_output_evaluation_blocks_unsupported_operation() -> None:
    environment = _environment()
    observation = _observation()
    output = _adapter(operation_preferences=("delete-host-file",)).generate_output(
        output_id="model-output-1",
        environment=environment,
        observation=observation,
    )

    assert output.selected_operation_id == "delete-host-file"
    assert (
        evaluate_model_output(
            environment=environment,
            observation=observation,
            model_output=output,
        )
        is ModelActionDraftDecision.UNSUPPORTED_OPERATION
    )


def test_build_model_action_draft_creates_bounded_action_when_ready() -> None:
    environment = _environment()
    observation = _observation()
    output = _adapter().generate_output(
        output_id="model-output-1",
        environment=environment,
        observation=observation,
    )

    draft = build_model_action_draft(
        draft_id="draft-1",
        action_id="action-1",
        environment=environment,
        observation=observation,
        model_output=output,
        notes=("model output converted to bounded action proposal",),
    )

    assert draft.ready
    assert draft.action_proposal is not None
    assert draft.action_proposal.actor_id == "deterministic-adapter-1"
    assert draft.action_proposal.operation_id == "move-east"
    assert not draft.action_proposal.self_authorized
    assert not draft.action_proposal.claims_completion
    assert draft.fingerprint() == draft.fingerprint()


def test_build_model_action_draft_fails_closed_without_proposal() -> None:
    environment = _environment()
    observation = _observation()
    output = _adapter(
        operation_preferences=("write-outside-boundary",)
    ).generate_output(
        output_id="model-output-1",
        environment=environment,
        observation=observation,
    )

    draft = build_model_action_draft(
        draft_id="draft-blocked",
        action_id="action-blocked",
        environment=environment,
        observation=observation,
        model_output=output,
    )

    assert not draft.ready
    assert draft.action_proposal is None
    assert draft.decision is ModelActionDraftDecision.UNSUPPORTED_OPERATION
