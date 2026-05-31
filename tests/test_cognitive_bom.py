import pytest

from ix_cognition_kernel.cognitive_bom import (
    COGNITIVE_BOM,
    LayerKind,
    layer_by_number,
    layer_names,
    layers_by_kind,
    required_kernel_pressures,
)


def test_cognitive_bom_has_ten_locked_layers() -> None:
    assert [layer.number for layer in COGNITIVE_BOM] == list(range(1, 11))
    assert len(COGNITIVE_BOM) == 10


def test_layer_names_match_locked_stack_order() -> None:
    assert layer_names() == (
        "Self-play / open-ended curriculum",
        "Emergent communication / multi-agent protocol learning",
        "World-model / imagination layer",
        "Evaluator-driven discovery",
        "Memory / reflection / skill accumulation",
        "Scientific-loop automation",
        "Tool-using agents / coding agents",
        "Multi-agent governance / specialist roles",
        "Failure/danger threads",
        "IX governance stack",
    )


def test_emergent_communication_layer_preserves_translation_requirement() -> None:
    layer = layer_by_number(2)

    assert layer.kind is LayerKind.COMMUNICATION_MECHANISM
    assert "Facebook FAIR negotiation agents" in layer.representative_threads
    assert "human-readable evidence" in layer.required_kernel_pressure


def test_world_model_layer_links_imagination_to_observable_predictions() -> None:
    layer = layer_by_number(3)

    assert layer.kind is LayerKind.WORLD_MODELING
    assert "counterfactuals" in layer.role
    assert "observable results" in layer.required_kernel_pressure
    assert "IX-BlackFox-WorldTwin" in layer.representative_threads


def test_evaluator_layer_blocks_fluency_only_discovery() -> None:
    layer = layer_by_number(4)

    assert layer.kind is LayerKind.DISCOVERY_MECHANISM
    assert "FunSearch" in layer.representative_threads
    assert "AlphaEvolve" in layer.representative_threads
    assert "evidence records" in layer.required_kernel_pressure


def test_failure_layer_is_part_of_the_bom_not_a_side_note() -> None:
    failure_layers = layers_by_kind(LayerKind.FAILURE_THREAD)

    assert len(failure_layers) == 1
    layer = failure_layers[0]
    assert layer.number == 9
    assert "specification gaming" in layer.representative_threads
    assert "reward hacking" in layer.representative_threads
    assert "objective mismatch" in layer.required_kernel_pressure


def test_ix_governance_layer_binds_cognition_to_authority_and_handoff() -> None:
    layer = layer_by_number(10)

    assert layer.kind is LayerKind.IX_GOVERNANCE
    assert "IX-BlackFox" in layer.representative_threads
    assert "IX-Agent-Notary" in layer.representative_threads
    assert "No evidence-bound action package" in layer.required_kernel_pressure


def test_unknown_layer_number_is_rejected() -> None:
    with pytest.raises(
        ValueError, match="Unknown IX-CognitionKernel cognitive BOM layer"
    ):
        layer_by_number(11)


def test_every_layer_has_representative_threads_and_kernel_pressure() -> None:
    for layer in COGNITIVE_BOM:
        assert layer.representative_threads
        assert layer.required_kernel_pressure
        assert layer.role


def test_required_kernel_pressures_preserve_all_ten_constraints() -> None:
    pressures = required_kernel_pressures()

    assert len(pressures) == 10
    assert any("stop conditions" in pressure for pressure in pressures)
    assert any("No private protocol" in pressure for pressure in pressures)
    assert any("No evidence-bound action package" in pressure for pressure in pressures)
