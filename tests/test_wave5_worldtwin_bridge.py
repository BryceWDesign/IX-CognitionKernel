import pytest

from ix_cognition_kernel.wave5_contracts import (
    WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES,
    WaveFiveArtifactDecision,
    WaveFiveArtifactKind,
    WaveFiveAuthorityState,
    WaveFiveCapabilityArea,
    WaveFiveClaimBoundary,
    WaveFiveSourceSystem,
    WaveFiveValidationStatus,
)
from ix_cognition_kernel.wave5_worldtwin_bridge import (
    BLOCKING_PREDICTION_DISPOSITIONS,
    EXTERNAL_WORLDTWIN_REVIEW_SOURCE_SYSTEMS,
    REQUIRED_CONSEQUENCE_KINDS,
    REQUIRED_REALITY_DELTA_KINDS,
    REQUIRED_SCENARIO_ASSUMPTION_KINDS,
    REQUIRED_WORLDTWIN_CONTROL_KINDS,
    SAFE_PREDICTION_DISPOSITIONS,
    WaveFiveConsequenceKind,
    WaveFiveConsequencePrediction,
    WaveFivePredictionDisposition,
    WaveFiveRealityDeltaCheck,
    WaveFiveRealityDeltaDisposition,
    WaveFiveRealityDeltaKind,
    WaveFiveScenarioAssumption,
    WaveFiveScenarioAssumptionKind,
    WaveFiveWorldTwinBridgeState,
    WaveFiveWorldTwinControl,
    WaveFiveWorldTwinControlKind,
    WaveFiveWorldTwinControlResult,
    WaveFiveWorldTwinScenarioBridge,
    blocking_prediction_dispositions,
    external_worldtwin_review_source_systems,
    required_consequence_kinds,
    required_reality_delta_kinds,
    required_scenario_assumption_kinds,
    required_worldtwin_control_kinds,
    safe_prediction_dispositions,
)


def assumption(
    assumption_id: str = "assumption-initial-conditions",
    *,
    assumption_kind: WaveFiveScenarioAssumptionKind = (
        WaveFiveScenarioAssumptionKind.INITIAL_CONDITIONS
    ),
    reviewer_visible: bool = True,
) -> WaveFiveScenarioAssumption:
    return WaveFiveScenarioAssumption(
        assumption_id=assumption_id,
        assumption_kind=assumption_kind,
        statement="Scenario assumption is explicit and bounded for review.",
        uncertainty_summary="Uncertainty remains visible and not promoted to truth.",
        falsification_signal="Observed evidence can falsify this scenario assumption.",
        evidence_ids=(f"evidence-{assumption_id}",),
        reviewer_visible=reviewer_visible,
    )


def prediction(
    prediction_id: str = "prediction-safety-consequence",
    *,
    consequence_kind: WaveFiveConsequenceKind = (
        WaveFiveConsequenceKind.SAFETY_CONSEQUENCE
    ),
    disposition: WaveFivePredictionDisposition = (
        WaveFivePredictionDisposition.REVIEWABLE_WITH_BOUNDARIES
    ),
    assumption_ids: tuple[str, ...] = ("assumption-initial-conditions",),
    preserves_human_authority: bool = True,
    grants_execution_authority: bool = False,
    claims_simulation_as_truth: bool = False,
) -> WaveFiveConsequencePrediction:
    return WaveFiveConsequencePrediction(
        prediction_id=prediction_id,
        consequence_kind=consequence_kind,
        disposition=disposition,
        predicted_consequence="Consequence is reviewable only inside boundaries.",
        assumption_ids=assumption_ids,
        uncertainty_summary="Scenario uncertainty remains attached to prediction.",
        falsification_path="Reality-delta evidence can reject this prediction.",
        evidence_ids=(f"evidence-{prediction_id}",),
        preserves_human_authority=preserves_human_authority,
        grants_execution_authority=grants_execution_authority,
        claims_simulation_as_truth=claims_simulation_as_truth,
    )


def delta(
    delta_id: str = "delta-assumption-drift",
    *,
    prediction_id: str = "prediction-safety-consequence",
    delta_kind: WaveFiveRealityDeltaKind = WaveFiveRealityDeltaKind.ASSUMPTION_DRIFT,
    disposition: WaveFiveRealityDeltaDisposition = (
        WaveFiveRealityDeltaDisposition.NO_BLOCKING_DELTA
    ),
    reviewer_visible: bool = True,
) -> WaveFiveRealityDeltaCheck:
    return WaveFiveRealityDeltaCheck(
        delta_id=delta_id,
        prediction_id=prediction_id,
        delta_kind=delta_kind,
        disposition=disposition,
        observation_summary="Reality delta is recorded for reviewer inspection.",
        required_response="Keep limitation visible or block readiness if needed.",
        evidence_ids=(f"evidence-{delta_id}",),
        reviewer_visible=reviewer_visible,
    )


def control(
    control_id: str,
    control_kind: WaveFiveWorldTwinControlKind,
    *,
    result: WaveFiveWorldTwinControlResult = WaveFiveWorldTwinControlResult.PASSED,
    blocking: bool = True,
) -> WaveFiveWorldTwinControl:
    return WaveFiveWorldTwinControl(
        control_id=control_id,
        control_kind=control_kind,
        result=result,
        description="WorldTwin control keeps scenario evidence bounded.",
        evidence_ids=(f"evidence-{control_id}",),
        blocking=blocking,
    )


def required_assumptions() -> tuple[WaveFiveScenarioAssumption, ...]:
    return tuple(
        assumption(f"assumption-{kind.value}", assumption_kind=kind)
        for kind in REQUIRED_SCENARIO_ASSUMPTION_KINDS
    )


def required_predictions() -> tuple[WaveFiveConsequencePrediction, ...]:
    return tuple(
        prediction(
            f"prediction-{kind.value}",
            consequence_kind=kind,
            assumption_ids=("assumption-initial-conditions",),
        )
        for kind in REQUIRED_CONSEQUENCE_KINDS
    )


def required_deltas() -> tuple[WaveFiveRealityDeltaCheck, ...]:
    return tuple(
        delta(
            f"delta-{kind.value}",
            prediction_id="prediction-safety-consequence",
            delta_kind=kind,
        )
        for kind in REQUIRED_REALITY_DELTA_KINDS
    )


def required_controls() -> tuple[WaveFiveWorldTwinControl, ...]:
    return tuple(
        control(f"control-{kind.value}", kind)
        for kind in REQUIRED_WORLDTWIN_CONTROL_KINDS
    )


def bridge(
    *,
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    bridge_state: WaveFiveWorldTwinBridgeState = (
        WaveFiveWorldTwinBridgeState.READY_FOR_EXTERNAL_SCENARIO_REVIEW
    ),
    assumptions: tuple[WaveFiveScenarioAssumption, ...] | None = None,
    predictions: tuple[WaveFiveConsequencePrediction, ...] | None = None,
    deltas: tuple[WaveFiveRealityDeltaCheck, ...] | None = None,
    controls: tuple[WaveFiveWorldTwinControl, ...] | None = None,
    reviewer_ids: tuple[str, ...] = (),
    claims_simulation_as_proof: bool = False,
    grants_execution_authority: bool = False,
    claims_agi: bool = False,
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    ),
) -> WaveFiveWorldTwinScenarioBridge:
    resolved_assumptions = (
        required_assumptions() if assumptions is None else assumptions
    )
    resolved_predictions = (
        required_predictions() if predictions is None else predictions
    )
    resolved_deltas = required_deltas() if deltas is None else deltas
    resolved_controls = required_controls() if controls is None else controls
    return WaveFiveWorldTwinScenarioBridge(
        bridge_id="wave5-worldtwin-bridge-001",
        title="Wave 5 WorldTwin scenario and consequence bridge.",
        source_system=source_system,
        bridge_state=bridge_state,
        assumptions=resolved_assumptions,
        predictions=resolved_predictions,
        reality_delta_checks=resolved_deltas,
        controls=resolved_controls,
        protocol_ids=("wave5-external-protocol-001",),
        reviewer_ids=reviewer_ids,
        claims_simulation_as_proof=claims_simulation_as_proof,
        grants_execution_authority=grants_execution_authority,
        claims_agi=claims_agi,
        claim_boundaries=claim_boundaries,
        notes=("Scenario evidence is review support, not truth or authority.",),
    )


def test_required_scenario_assumption_kinds_are_locked() -> None:
    assert required_scenario_assumption_kinds() == REQUIRED_SCENARIO_ASSUMPTION_KINDS
    assert len(REQUIRED_SCENARIO_ASSUMPTION_KINDS) == 8
    assert WaveFiveScenarioAssumptionKind.CLAIM_BOUNDARY in (
        REQUIRED_SCENARIO_ASSUMPTION_KINDS
    )


def test_required_consequence_and_delta_kinds_are_locked() -> None:
    assert required_consequence_kinds() == REQUIRED_CONSEQUENCE_KINDS
    assert required_reality_delta_kinds() == REQUIRED_REALITY_DELTA_KINDS
    assert WaveFiveConsequenceKind.WAVE_SIX_READINESS_CONSEQUENCE in (
        REQUIRED_CONSEQUENCE_KINDS
    )
    assert WaveFiveRealityDeltaKind.WAVE_SIX_LIMITATION_DELTA in (
        REQUIRED_REALITY_DELTA_KINDS
    )


def test_required_worldtwin_controls_are_locked() -> None:
    assert required_worldtwin_control_kinds() == REQUIRED_WORLDTWIN_CONTROL_KINDS
    assert len(REQUIRED_WORLDTWIN_CONTROL_KINDS) == 9
    assert WaveFiveWorldTwinControlKind.NO_SIMULATION_AS_PROOF in (
        REQUIRED_WORLDTWIN_CONTROL_KINDS
    )


def test_safe_and_blocking_prediction_dispositions_are_locked() -> None:
    assert safe_prediction_dispositions() == SAFE_PREDICTION_DISPOSITIONS
    assert blocking_prediction_dispositions() == BLOCKING_PREDICTION_DISPOSITIONS
    assert WaveFivePredictionDisposition.UNSAFE_TO_ACT in (
        BLOCKING_PREDICTION_DISPOSITIONS
    )


def test_external_worldtwin_sources_are_locked() -> None:
    assert external_worldtwin_review_source_systems() == (
        EXTERNAL_WORLDTWIN_REVIEW_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.INDEPENDENT_REVIEWER in (
        EXTERNAL_WORLDTWIN_REVIEW_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.IX_COGNITION_KERNEL not in (
        EXTERNAL_WORLDTWIN_REVIEW_SOURCE_SYSTEMS
    )


def test_assumption_requires_evidence_and_visibility() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveScenarioAssumption(
            assumption_id="assumption-invalid",
            assumption_kind=WaveFiveScenarioAssumptionKind.INITIAL_CONDITIONS,
            statement="Invalid assumption.",
            uncertainty_summary="Visible uncertainty.",
            falsification_signal="Falsifiable signal.",
            evidence_ids=(),
        )

    with pytest.raises(ValueError, match="reviewer visible"):
        assumption(reviewer_visible=False)


def test_prediction_rejects_execution_authority_and_simulation_truth() -> None:
    with pytest.raises(ValueError, match="execution authority"):
        prediction(grants_execution_authority=True)

    with pytest.raises(ValueError, match="simulation as truth"):
        prediction(claims_simulation_as_truth=True)


def test_safe_prediction_requires_human_authority_preservation() -> None:
    with pytest.raises(ValueError, match="preserve human authority"):
        prediction(preserves_human_authority=False)


def test_blocking_prediction_disposition_blocks_progress() -> None:
    item = prediction(disposition=WaveFivePredictionDisposition.UNSAFE_TO_ACT)

    assert item.blocks_wave_five_progress is True


def test_reality_delta_requires_evidence_and_visibility() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveRealityDeltaCheck(
            delta_id="delta-invalid",
            prediction_id="prediction-safety-consequence",
            delta_kind=WaveFiveRealityDeltaKind.ASSUMPTION_DRIFT,
            disposition=WaveFiveRealityDeltaDisposition.NO_BLOCKING_DELTA,
            observation_summary="Invalid delta without evidence.",
            required_response="Record limitation.",
            evidence_ids=(),
        )

    with pytest.raises(ValueError, match="reviewer visible"):
        delta(reviewer_visible=False)


def test_blocking_delta_blocks_progress() -> None:
    item = delta(disposition=WaveFiveRealityDeltaDisposition.BLOCKING_DELTA)

    assert item.blocks_wave_five_progress is True


def test_worldtwin_control_requires_evidence() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveWorldTwinControl(
            control_id="control-invalid",
            control_kind=WaveFiveWorldTwinControlKind.NO_SIMULATION_AS_PROOF,
            result=WaveFiveWorldTwinControlResult.PASSED,
            description="Invalid control without evidence.",
            evidence_ids=(),
        )


def test_failed_worldtwin_control_blocks_progress() -> None:
    item = control(
        "control-failed",
        WaveFiveWorldTwinControlKind.NO_EXECUTION_AUTHORITY,
        result=WaveFiveWorldTwinControlResult.FAILED,
    )

    assert item.passed_with_boundaries is False
    assert item.blocks_wave_five_progress is True


def test_bridge_rejects_simulation_proof_execution_or_agi_claims() -> None:
    with pytest.raises(ValueError, match="simulation as proof"):
        bridge(claims_simulation_as_proof=True)

    with pytest.raises(ValueError, match="execution authority"):
        bridge(grants_execution_authority=True)

    with pytest.raises(ValueError, match="claim AGI"):
        bridge(claims_agi=True)


def test_bridge_rejects_prediction_for_unknown_assumption() -> None:
    with pytest.raises(ValueError, match="bundled assumptions"):
        bridge(predictions=(prediction(assumption_ids=("missing-assumption",)),))


def test_bridge_rejects_delta_for_unknown_prediction() -> None:
    with pytest.raises(ValueError, match="bundled predictions"):
        bridge(deltas=(delta(prediction_id="missing-prediction"),))


def test_bridge_rejects_missing_claim_boundary() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        bridge(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_bridge_reports_missing_required_coverage() -> None:
    item = bridge(
        assumptions=(assumption(),),
        predictions=(prediction(),),
        deltas=(delta(),),
        controls=(
            control(
                "control-assumption-ledger-present",
                WaveFiveWorldTwinControlKind.ASSUMPTION_LEDGER_PRESENT,
            ),
        ),
    )

    assert item.has_required_assumption_coverage is False
    assert WaveFiveScenarioAssumptionKind.CLAIM_BOUNDARY in (
        item.missing_required_assumption_kinds
    )
    assert item.has_required_consequence_coverage is False
    assert WaveFiveConsequenceKind.WAVE_SIX_READINESS_CONSEQUENCE in (
        item.missing_required_consequence_kinds
    )
    assert item.has_required_delta_coverage is False
    assert WaveFiveRealityDeltaKind.WAVE_SIX_LIMITATION_DELTA in (
        item.missing_required_delta_kinds
    )
    assert item.has_required_control_coverage is False
    assert WaveFiveWorldTwinControlKind.NO_SIMULATION_AS_PROOF in (
        item.missing_required_control_kinds
    )


def test_bridge_is_ready_for_external_worldtwin_review() -> None:
    item = bridge()

    assert item.has_required_assumption_coverage is True
    assert item.has_required_consequence_coverage is True
    assert item.has_required_delta_coverage is True
    assert item.has_required_control_coverage is True
    assert item.blocking_prediction_ids == ()
    assert item.blocking_delta_ids == ()
    assert item.blocking_control_ids == ()
    assert item.preserves_human_authority is True
    assert item.ready_for_external_worldtwin_review is True


def test_ready_bridge_exports_reviewable_traceability_artifact() -> None:
    artifact = bridge().to_artifact_ref()

    assert artifact.kind is WaveFiveArtifactKind.ECOSYSTEM_TRACEABILITY_MAP
    assert artifact.capability_area is WaveFiveCapabilityArea.ECOSYSTEM_TRACEABILITY
    assert artifact.source_system is WaveFiveSourceSystem.IX_COGNITION_KERNEL
    assert artifact.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    assert artifact.authority_state is WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    )


def test_blocking_prediction_exports_blocked_artifact() -> None:
    predictions = tuple(
        prediction(
            f"prediction-{kind.value}",
            consequence_kind=kind,
            disposition=(
                WaveFivePredictionDisposition.UNSAFE_TO_ACT
                if kind is WaveFiveConsequenceKind.AUTHORITY_CONSEQUENCE
                else WaveFivePredictionDisposition.REVIEWABLE_WITH_BOUNDARIES
            ),
            assumption_ids=("assumption-initial-conditions",),
        )
        for kind in REQUIRED_CONSEQUENCE_KINDS
    )
    artifact = bridge(predictions=predictions).to_artifact_ref()

    assert artifact.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact.authority_state is WaveFiveAuthorityState.BLOCKED
    assert artifact.validation_status is WaveFiveValidationStatus.REJECTED


def test_blocking_control_exports_blocked_artifact() -> None:
    controls = tuple(
        control(
            f"control-{kind.value}",
            kind,
            result=(
                WaveFiveWorldTwinControlResult.FAILED
                if kind is WaveFiveWorldTwinControlKind.NO_SIMULATION_AS_PROOF
                else WaveFiveWorldTwinControlResult.PASSED
            ),
        )
        for kind in REQUIRED_WORLDTWIN_CONTROL_KINDS
    )
    artifact = bridge(controls=controls).to_artifact_ref()

    assert artifact.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact.validation_status is WaveFiveValidationStatus.REJECTED


def test_externally_reviewed_bridge_requires_external_source() -> None:
    with pytest.raises(ValueError, match="external source"):
        bridge(
            bridge_state=(
                WaveFiveWorldTwinBridgeState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
            reviewer_ids=("reviewer-001",),
        )


def test_externally_reviewed_bridge_requires_reviewer_ids() -> None:
    with pytest.raises(ValueError, match="reviewer ids"):
        bridge(
            source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
            bridge_state=(
                WaveFiveWorldTwinBridgeState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
        )


def test_externally_reviewed_bridge_exports_bounded_external_artifact() -> None:
    item = bridge(
        source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
        bridge_state=WaveFiveWorldTwinBridgeState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
        reviewer_ids=("reviewer-001",),
    )
    artifact = item.to_artifact_ref()

    assert item.externally_reviewed_with_boundaries is True
    assert artifact.decision is WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
    )
    assert artifact.externally_validated_with_boundaries is True


def test_bridge_collects_unique_evidence_ids() -> None:
    item = bridge()

    assert item.all_evidence_ids[0] == "evidence-assumption-claim-boundary"
    assert "evidence-prediction-wave-six-readiness-consequence" in item.all_evidence_ids
    assert "evidence-delta-wave-six-limitation-delta" in item.all_evidence_ids
    assert "evidence-control-no-simulation-as-proof" in item.all_evidence_ids
    assert len(item.all_evidence_ids) == 31


def test_bridge_fingerprint_is_deterministic() -> None:
    item = bridge()

    assert item.fingerprint() == item.fingerprint()
    assert len(item.fingerprint()) == 64
