import pytest

from ix_cognition_kernel.engines import engine_ids
from ix_cognition_kernel.wave3_contracts import (
    WaveThreeArtifactBundle,
    WaveThreeArtifactDecision,
    WaveThreeArtifactKind,
    WaveThreeArtifactRef,
    WaveThreeAuthorityState,
    WaveThreeEvidenceLink,
    WaveThreeEvidenceRelation,
    WaveThreeSourceSystem,
)
from ix_cognition_kernel.wave3_coordinator import (
    WaveThreeCoordinationResult,
    WaveThreeCoordinationStatus,
    coordinate_wave_three_engines,
)
from ix_cognition_kernel.wave3_engine_coordination import (
    EngineCoordinationBundle,
    EngineCoordinationRecord,
    EngineCoordinationStatus,
    complete_engine_coordination_record,
)


def complete_record(engine_id: str) -> EngineCoordinationRecord:
    return complete_engine_coordination_record(
        engine_id,
        evidence_ids=(f"evidence:{engine_id}",),
        downstream_artifact_ids=(f"artifact:{engine_id}",),
    )


def complete_bundle(
    *, required_engine_ids: tuple[str, ...] = engine_ids()
) -> EngineCoordinationBundle:
    return EngineCoordinationBundle(
        bundle_id="engine-bundle-001",
        records=tuple(complete_record(engine_id) for engine_id in required_engine_ids),
        required_engine_ids=required_engine_ids,
    )


def test_coordinate_wave_three_engines_creates_reviewable_substrate_result() -> None:
    result = coordinate_wave_three_engines(
        coordination_id="coordination-001",
        engine_bundle=complete_bundle(),
    )

    assert result.status is WaveThreeCoordinationStatus.READY_FOR_HUMAN_REVIEW
    assert result.ready_for_human_review is True
    assert result.permits_automatic_execution is False
    assert result.human_authority_state is WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
    assert result.coordinated_engine_count == len(engine_ids())
    assert result.required_engine_count == len(engine_ids())
    assert result.readiness_gaps == ()
    assert result.blocking_gaps == ()
    assert "automatic execution is not permitted" in result.review_summary


def test_coordinator_keeps_wave_three_scope_to_review_not_execution() -> None:
    result = coordinate_wave_three_engines(
        coordination_id="coordination-001",
        engine_bundle=complete_bundle(),
    )

    payload = result.canonical_payload()

    assert payload["status"] == "ready-for-human-review"
    assert payload["permits_automatic_execution"] is False
    assert payload["human_authority_state"] == "human-review-required"


def test_coordinator_can_scope_to_subset_for_incremental_internal_reviews() -> None:
    required_engine_ids = ("belief", "evaluator", "blackfox-handoff")
    result = coordinate_wave_three_engines(
        coordination_id="coordination-subset",
        engine_bundle=complete_bundle(required_engine_ids=required_engine_ids),
        required_engine_ids=required_engine_ids,
    )

    assert result.status is WaveThreeCoordinationStatus.READY_FOR_HUMAN_REVIEW
    assert result.required_engine_ids == required_engine_ids
    assert result.coordinated_engine_count == 3
    assert result.artifact_by_engine_id("blackfox-handoff").produced_by_engine_id == (
        "blackfox-handoff"
    )


def test_coordinator_rejects_scope_mismatch_between_bundle_and_coordinator() -> None:
    with pytest.raises(ValueError, match="required_engine_ids must match"):
        coordinate_wave_three_engines(
            coordination_id="coordination-001",
            engine_bundle=complete_bundle(required_engine_ids=("belief",)),
            required_engine_ids=("belief", "evaluator"),
        )


def test_coordinator_reports_needs_evidence_when_engine_record_is_incomplete() -> None:
    incomplete = EngineCoordinationRecord(
        engine_id="belief",
        satisfied_input_names=("claim",),
        produced_output_names=("belief-record",),
        covered_failure_modes=("hallucinated-truth",),
        evidence_ids=(),
    )
    engine_bundle = EngineCoordinationBundle(
        bundle_id="engine-bundle-001",
        records=(incomplete,),
        required_engine_ids=("belief",),
    )
    result = coordinate_wave_three_engines(
        coordination_id="coordination-001",
        engine_bundle=engine_bundle,
        required_engine_ids=("belief",),
    )

    assert result.status is WaveThreeCoordinationStatus.NEEDS_EVIDENCE
    assert result.ready_for_human_review is False
    assert any("belief has no evidence ids" in gap for gap in result.readiness_gaps)
    assert result.blocking_gaps == ()


def test_coordinator_reports_blocked_when_engine_record_is_blocked() -> None:
    blocked = EngineCoordinationRecord(
        engine_id="belief",
        satisfied_input_names=("claim", "evidence", "source", "confidence"),
        produced_output_names=(
            "belief-record",
            "confidence-state",
            "contradiction-state",
        ),
        covered_failure_modes=(
            "hallucinated-truth",
            "uncited-belief-persistence",
            "contradiction-blindness",
        ),
        evidence_ids=("evidence:belief",),
        status=EngineCoordinationStatus.BLOCKED,
        blocking_reasons=("contradictory evidence must be reviewed",),
    )
    engine_bundle = EngineCoordinationBundle(
        bundle_id="engine-bundle-001",
        records=(blocked,),
        required_engine_ids=("belief",),
    )
    result = coordinate_wave_three_engines(
        coordination_id="coordination-001",
        engine_bundle=engine_bundle,
        required_engine_ids=("belief",),
    )

    assert result.status is WaveThreeCoordinationStatus.BLOCKED
    assert result.ready_for_human_review is False
    assert result.human_authority_state is WaveThreeAuthorityState.BLOCKED
    assert "blocked engine records: belief" in result.blocking_gaps


def test_coordinator_rejects_artifact_bundle_without_required_kind_scope() -> None:
    engine_bundle = complete_bundle(required_engine_ids=("belief",))
    artifact_bundle = engine_bundle.to_artifact_bundle(
        artifact_bundle_id="artifact-bundle-001"
    )
    artifact_bundle_without_required_kind = WaveThreeArtifactBundle(
        bundle_id="artifact-bundle-002",
        artifacts=artifact_bundle.artifacts,
        evidence_links=artifact_bundle.evidence_links,
        required_kinds=(),
    )

    with pytest.raises(ValueError, match="required_kinds must include"):
        coordinate_wave_three_engines(
            coordination_id="coordination-001",
            engine_bundle=engine_bundle,
            artifact_bundle=artifact_bundle_without_required_kind,
            required_engine_ids=("belief",),
        )


def test_coordinator_rejects_artifact_bundle_that_does_not_match_engine_records() -> (
    None
):
    engine_bundle = complete_bundle(required_engine_ids=("belief",))
    wrong_artifact = WaveThreeArtifactRef(
        artifact_id="engine-coordination:evaluator",
        kind=WaveThreeArtifactKind.ENGINE_COORDINATION,
        source_system=WaveThreeSourceSystem.IX_COGNITION_KERNEL,
        summary="Wrong engine artifact for the bundled engine records.",
        produced_by_engine_id="evaluator",
        evidence_ids=("evidence:evaluator",),
        decision=WaveThreeArtifactDecision.READY_FOR_HUMAN_REVIEW,
        authority_state=WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED,
    )
    wrong_bundle = WaveThreeArtifactBundle(
        bundle_id="artifact-bundle-001",
        artifacts=(wrong_artifact,),
        evidence_links=(
            WaveThreeEvidenceLink(
                evidence_id="evidence:evaluator",
                artifact_id="engine-coordination:evaluator",
                relation=WaveThreeEvidenceRelation.TESTS,
                summary="Mismatched evidence link.",
                source_system=WaveThreeSourceSystem.LOCAL_TEST_SUITE,
            ),
        ),
        required_kinds=(WaveThreeArtifactKind.ENGINE_COORDINATION,),
    )

    with pytest.raises(ValueError, match="must exactly match"):
        coordinate_wave_three_engines(
            coordination_id="coordination-001",
            engine_bundle=engine_bundle,
            artifact_bundle=wrong_bundle,
            required_engine_ids=("belief",),
        )


def test_coordinator_result_rejects_empty_coordination_id() -> None:
    with pytest.raises(ValueError, match="coordination_id must not be empty"):
        coordinate_wave_three_engines(
            coordination_id=" ",
            engine_bundle=complete_bundle(required_engine_ids=("belief",)),
            required_engine_ids=("belief",),
        )


def test_coordinator_rejects_duplicate_required_engine_ids() -> None:
    engine_bundle = complete_bundle(required_engine_ids=("belief",))

    with pytest.raises(ValueError, match="Duplicate required_engine_id"):
        WaveThreeCoordinationResult(
            coordination_id="coordination-001",
            engine_bundle=engine_bundle,
            artifact_bundle=engine_bundle.to_artifact_bundle(
                artifact_bundle_id="artifact-bundle-001"
            ),
            required_engine_ids=("belief", "belief"),
        )


def test_coordinator_fingerprint_is_deterministic() -> None:
    engine_bundle = complete_bundle(required_engine_ids=("belief", "evaluator"))
    first = coordinate_wave_three_engines(
        coordination_id="coordination-001",
        engine_bundle=engine_bundle,
        required_engine_ids=("belief", "evaluator"),
    )
    second = coordinate_wave_three_engines(
        coordination_id="coordination-001",
        engine_bundle=engine_bundle,
        required_engine_ids=("belief", "evaluator"),
    )

    assert first.fingerprint() == second.fingerprint()
    assert len(first.fingerprint()) == 64
