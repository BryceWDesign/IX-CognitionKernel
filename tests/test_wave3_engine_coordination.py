import pytest

from ix_cognition_kernel.engines import engine_by_id, engine_ids
from ix_cognition_kernel.wave3_contracts import WaveThreeArtifactKind
from ix_cognition_kernel.wave3_engine_coordination import (
    EngineCoordinationBundle,
    EngineCoordinationRecord,
    EngineCoordinationStatus,
    EngineDependency,
    EngineDependencyRelation,
    complete_engine_coordination_record,
)


def complete_record(
    engine_id: str = "belief", *, evidence_ids: tuple[str, ...] | None = None
) -> EngineCoordinationRecord:
    return complete_engine_coordination_record(
        engine_id,
        evidence_ids=evidence_ids or (f"evidence-{engine_id}",),
        downstream_artifact_ids=(f"artifact:{engine_id}",),
    )


def test_complete_record_uses_locked_engine_registry_contract() -> None:
    engine = engine_by_id("belief")
    record = complete_record("belief")

    assert record.engine_id == "belief"
    assert record.satisfied_input_names == engine.required_inputs
    assert record.produced_output_names == engine.required_outputs
    assert record.covered_failure_modes == engine.blocked_failure_modes
    assert record.has_coordination_coverage is True
    assert record.readiness_gaps == ()


def test_record_rejects_unknown_engine_id() -> None:
    with pytest.raises(ValueError, match="Unknown IX-CognitionKernel engine id"):
        complete_record("not-an-engine")


def test_record_rejects_values_outside_engine_registry_contract() -> None:
    with pytest.raises(ValueError, match="Unknown satisfied_input_name"):
        EngineCoordinationRecord(
            engine_id="belief",
            satisfied_input_names=("claim", "not-a-real-input"),
            produced_output_names=engine_by_id("belief").required_outputs,
            covered_failure_modes=engine_by_id("belief").blocked_failure_modes,
            evidence_ids=("evidence-belief",),
        )


def test_evidence_complete_record_requires_full_coverage() -> None:
    with pytest.raises(ValueError, match="Evidence-complete engine records require"):
        EngineCoordinationRecord(
            engine_id="belief",
            satisfied_input_names=("claim",),
            produced_output_names=engine_by_id("belief").required_outputs,
            covered_failure_modes=engine_by_id("belief").blocked_failure_modes,
            evidence_ids=("evidence-belief",),
            status=EngineCoordinationStatus.EVIDENCE_COMPLETE,
        )


def test_incomplete_record_reports_precise_readiness_gaps() -> None:
    record = EngineCoordinationRecord(
        engine_id="belief",
        satisfied_input_names=("claim",),
        produced_output_names=("belief-record",),
        covered_failure_modes=("hallucinated-truth",),
        evidence_ids=(),
    )

    assert record.has_required_input_coverage is False
    assert record.has_required_output_coverage is False
    assert record.has_failure_mode_coverage is False
    assert record.has_coordination_coverage is False
    assert "belief missing required inputs: evidence, source, confidence" in (
        record.readiness_gaps
    )
    assert "belief missing required outputs: confidence-state, contradiction-state" in (
        record.readiness_gaps
    )
    assert (
        "belief missing failure-mode coverage: uncited-belief-persistence, "
        "contradiction-blindness"
    ) in record.readiness_gaps
    assert "belief has no evidence ids" in record.readiness_gaps


def test_blocked_records_require_reasons_and_report_gaps() -> None:
    with pytest.raises(ValueError, match="require blocking reasons"):
        EngineCoordinationRecord(
            engine_id="belief",
            satisfied_input_names=engine_by_id("belief").required_inputs,
            produced_output_names=engine_by_id("belief").required_outputs,
            covered_failure_modes=engine_by_id("belief").blocked_failure_modes,
            evidence_ids=("evidence-belief",),
            status=EngineCoordinationStatus.BLOCKED,
        )

    blocked = EngineCoordinationRecord(
        engine_id="belief",
        satisfied_input_names=engine_by_id("belief").required_inputs,
        produced_output_names=engine_by_id("belief").required_outputs,
        covered_failure_modes=engine_by_id("belief").blocked_failure_modes,
        evidence_ids=("evidence-belief",),
        status=EngineCoordinationStatus.BLOCKED,
        blocking_reasons=("contradictory evidence requires human review",),
    )

    assert blocked.blocks_progress is True
    assert "belief blocked: contradictory evidence requires human review" in (
        blocked.readiness_gaps
    )


def test_non_blocked_records_cannot_carry_blocking_reasons() -> None:
    with pytest.raises(ValueError, match="Only blocked engine records"):
        EngineCoordinationRecord(
            engine_id="belief",
            satisfied_input_names=engine_by_id("belief").required_inputs,
            produced_output_names=engine_by_id("belief").required_outputs,
            covered_failure_modes=engine_by_id("belief").blocked_failure_modes,
            evidence_ids=("evidence-belief",),
            blocking_reasons=("not allowed",),
        )


def test_record_converts_to_non_executable_artifact_ref() -> None:
    artifact = complete_record("blackfox-handoff").to_artifact_ref()

    assert artifact.kind is WaveThreeArtifactKind.ENGINE_COORDINATION
    assert artifact.artifact_id == "engine-coordination:blackfox-handoff"
    assert artifact.produced_by_engine_id == "blackfox-handoff"
    assert artifact.allowed_for_automatic_execution is False
    assert artifact.ready_for_human_review is True


def test_record_fingerprint_is_deterministic() -> None:
    first = complete_record("belief").fingerprint()
    second = complete_record("belief").fingerprint()

    assert first == second
    assert len(first) == 64


def test_dependency_rejects_self_dependency() -> None:
    with pytest.raises(ValueError, match="distinct engines"):
        EngineDependency(
            upstream_engine_id="belief",
            downstream_engine_id="belief",
            relation=EngineDependencyRelation.REQUIRES,
            required_artifact_ids=("artifact:belief",),
            reason="Self-dependencies hide missing coordination.",
        )


def test_dependency_rejects_duplicate_required_artifacts() -> None:
    with pytest.raises(ValueError, match="Duplicate dependency required_artifact_id"):
        EngineDependency(
            upstream_engine_id="belief",
            downstream_engine_id="evaluator",
            relation=EngineDependencyRelation.SUPPORTS,
            required_artifact_ids=("artifact:belief", "artifact:belief"),
            reason="Evaluator needs belief evidence.",
        )


def test_bundle_reports_missing_required_engines_without_faking_readiness() -> None:
    bundle = EngineCoordinationBundle(
        bundle_id="bundle-001",
        records=(complete_record("belief"),),
        required_engine_ids=("belief", "evaluator"),
    )

    assert bundle.missing_required_engine_ids == ("evaluator",)
    assert bundle.is_complete_for_required_engines is False
    assert "missing required engine records: evaluator" in bundle.readiness_gaps


def test_bundle_rejects_duplicate_engine_records() -> None:
    with pytest.raises(ValueError, match="Duplicate engine_id"):
        EngineCoordinationBundle(
            bundle_id="bundle-001",
            records=(complete_record("belief"), complete_record("belief")),
        )


def test_bundle_rejects_dependency_without_bundled_upstream_record() -> None:
    with pytest.raises(ValueError, match="requires a bundled upstream record"):
        EngineCoordinationBundle(
            bundle_id="bundle-001",
            records=(complete_record("evaluator"),),
            dependencies=(
                EngineDependency(
                    upstream_engine_id="belief",
                    downstream_engine_id="evaluator",
                    relation=EngineDependencyRelation.SUPPORTS,
                    required_artifact_ids=("artifact:belief",),
                    reason="Evaluator needs belief-state evidence.",
                ),
            ),
            required_engine_ids=("belief", "evaluator"),
        )


def test_bundle_dependency_map_is_deterministic() -> None:
    bundle = EngineCoordinationBundle(
        bundle_id="bundle-001",
        records=(complete_record("belief"), complete_record("evaluator")),
        dependencies=(
            EngineDependency(
                upstream_engine_id="belief",
                downstream_engine_id="evaluator",
                relation=EngineDependencyRelation.SUPPORTS,
                required_artifact_ids=("artifact:belief",),
                reason="Evaluator needs belief-state evidence.",
            ),
        ),
        required_engine_ids=("belief", "evaluator"),
    )

    assert bundle.dependency_map == {"evaluator": ("belief",)}


def test_complete_bundle_for_all_required_engines_has_no_readiness_gaps() -> None:
    records = tuple(
        complete_record(engine_id, evidence_ids=(f"evidence:{engine_id}",))
        for engine_id in engine_ids()
    )
    bundle = EngineCoordinationBundle(bundle_id="bundle-001", records=records)

    assert bundle.record_engine_ids == tuple(sorted(engine_ids()))
    assert set(bundle.complete_engine_ids) == set(engine_ids())
    assert bundle.missing_required_engine_ids == ()
    assert bundle.incomplete_engine_ids == ()
    assert bundle.blocked_engine_ids == ()
    assert bundle.readiness_gaps == ()
    assert bundle.is_complete_for_required_engines is True


def test_bundle_converts_to_shared_artifact_bundle() -> None:
    bundle = EngineCoordinationBundle(
        bundle_id="bundle-001",
        records=(complete_record("belief"), complete_record("evaluator")),
        required_engine_ids=("belief", "evaluator"),
    )
    artifact_bundle = bundle.to_artifact_bundle(
        artifact_bundle_id="artifact-bundle-engine-coordination"
    )

    assert artifact_bundle.has_required_kind_coverage is True
    assert artifact_bundle.artifact_ids == (
        "engine-coordination:belief",
        "engine-coordination:evaluator",
    )
    assert artifact_bundle.ready_for_human_review_artifact_ids == (
        "engine-coordination:belief",
        "engine-coordination:evaluator",
    )
    assert artifact_bundle.evidence_link_table == {
        "engine-coordination:belief": ("evidence-belief",),
        "engine-coordination:evaluator": ("evidence-evaluator",),
    }


def test_bundle_fingerprint_is_deterministic_despite_input_order() -> None:
    first = EngineCoordinationBundle(
        bundle_id="bundle-001",
        records=(complete_record("evaluator"), complete_record("belief")),
        required_engine_ids=("belief", "evaluator"),
    )
    second = EngineCoordinationBundle(
        bundle_id="bundle-001",
        records=(complete_record("belief"), complete_record("evaluator")),
        required_engine_ids=("belief", "evaluator"),
    )

    assert first.fingerprint() == second.fingerprint()
    assert len(first.fingerprint()) == 64
