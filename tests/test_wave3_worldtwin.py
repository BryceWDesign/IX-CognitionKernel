import pytest

from ix_cognition_kernel.wave3_contracts import (
    WaveThreeArtifactKind,
    WaveThreeAuthorityState,
    WaveThreeSourceSystem,
)
from ix_cognition_kernel.wave3_worldtwin import (
    REQUIRED_WORLDTWIN_BOUNDARY_KINDS,
    WorldTwinAssumption,
    WorldTwinAssumptionStatus,
    WorldTwinBoundaryKind,
    WorldTwinCounterfactualBranch,
    WorldTwinExpectedOutcome,
    WorldTwinImpactLevel,
    WorldTwinScenarioBoundary,
    WorldTwinScenarioBundle,
    WorldTwinScenarioRecord,
    WorldTwinScenarioStatus,
)


def boundary(kind: WorldTwinBoundaryKind) -> WorldTwinScenarioBoundary:
    return WorldTwinScenarioBoundary(
        boundary_id=f"boundary:{kind.value}",
        kind=kind,
        description=f"{kind.value} boundary keeps the scenario bounded.",
    )


def required_boundaries() -> tuple[WorldTwinScenarioBoundary, ...]:
    return tuple(boundary(kind) for kind in REQUIRED_WORLDTWIN_BOUNDARY_KINDS)


def assumption(
    assumption_id: str = "assumption-001",
    *,
    status: WorldTwinAssumptionStatus = WorldTwinAssumptionStatus.ACTIVE,
    impact: WorldTwinImpactLevel = WorldTwinImpactLevel.MEDIUM,
    evidence_ids: tuple[str, ...] = ("evidence:assumption-001",),
    required_evidence: tuple[str, ...] = (),
) -> WorldTwinAssumption:
    return WorldTwinAssumption(
        assumption_id=assumption_id,
        statement="The review artifact remains bounded to human-authorized action.",
        status=status,
        confidence=0.76,
        impact_if_wrong=impact,
        evidence_ids=evidence_ids,
        required_evidence=required_evidence,
    )


def expected_outcome(
    outcome_id: str = "outcome-001",
    *,
    evidence_ids: tuple[str, ...] = ("evidence:outcome-001",),
) -> WorldTwinExpectedOutcome:
    return WorldTwinExpectedOutcome(
        outcome_id=outcome_id,
        description="The proposed handoff remains review-only.",
        measurement_name="execution-authority-state",
        expected_result="human-review-required and automatic-execution-false",
        uncertainty_notes=("The scenario does not claim complete reality coverage.",),
        evidence_ids=evidence_ids,
    )


def branch(
    branch_id: str = "branch-001",
    *,
    changed_assumption_ids: tuple[str, ...] = ("assumption-001",),
    expected_outcome_ids: tuple[str, ...] = ("outcome-001",),
    evidence_ids: tuple[str, ...] = ("evidence:branch-001",),
) -> WorldTwinCounterfactualBranch:
    return WorldTwinCounterfactualBranch(
        branch_id=branch_id,
        changed_assumption_ids=changed_assumption_ids,
        expected_outcome_ids=expected_outcome_ids,
        rationale="Flip a fragile assumption and check whether review safety survives.",
        risk_notes=("If the branch hides uncertainty, the scenario must not pass.",),
        evidence_ids=evidence_ids,
    )


def ready_scenario(scenario_id: str = "scenario-001") -> WorldTwinScenarioRecord:
    return WorldTwinScenarioRecord(
        scenario_id=scenario_id,
        title="Review-only BlackFox handoff scenario",
        bounded_question=(
            "Would this cognition package remain review-only if sent toward a "
            "BlackFox-style governance boundary?"
        ),
        system_under_test="IX-CognitionKernel Wave 3 substrate handoff candidate",
        boundaries=required_boundaries(),
        assumptions=(assumption(),),
        expected_outcomes=(expected_outcome(),),
        counterfactual_branches=(branch(),),
        evidence_ids=(f"evidence:{scenario_id}",),
    )


def test_required_worldtwin_boundaries_are_locked() -> None:
    assert REQUIRED_WORLDTWIN_BOUNDARY_KINDS == (
        WorldTwinBoundaryKind.OPERATIONAL,
        WorldTwinBoundaryKind.POLICY,
        WorldTwinBoundaryKind.SAFETY,
        WorldTwinBoundaryKind.DATA,
        WorldTwinBoundaryKind.HUMAN_REVIEW,
    )


def test_ready_worldtwin_scenario_is_reviewable_not_executable() -> None:
    scenario = ready_scenario()

    assert scenario.status is WorldTwinScenarioStatus.READY_FOR_HUMAN_REVIEW
    assert scenario.ready_for_human_review is True
    assert scenario.permits_automatic_execution is False
    assert (
        scenario.human_authority_state is WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
    )
    assert scenario.missing_required_boundary_kinds == ()
    assert scenario.readiness_gaps == ()
    assert scenario.blocking_gaps == ()
    assert "automatic execution is not permitted" in scenario.review_summary


def test_active_worldtwin_assumptions_require_evidence() -> None:
    with pytest.raises(ValueError, match="Active WorldTwin assumptions require"):
        assumption(evidence_ids=())


def test_unsupported_assumptions_require_required_evidence_notes() -> None:
    with pytest.raises(ValueError, match="Unsupported assumptions require"):
        assumption(
            status=WorldTwinAssumptionStatus.UNSUPPORTED,
            evidence_ids=(),
            required_evidence=(),
        )


def test_assumption_confidence_must_be_in_range() -> None:
    with pytest.raises(ValueError, match="confidence must be between"):
        WorldTwinAssumption(
            assumption_id="assumption-001",
            statement="Invalid confidence should fail closed.",
            status=WorldTwinAssumptionStatus.ACTIVE,
            confidence=1.2,
            impact_if_wrong=WorldTwinImpactLevel.MEDIUM,
            evidence_ids=("evidence",),
            required_evidence=(),
        )


def test_expected_outcomes_require_uncertainty_notes() -> None:
    with pytest.raises(ValueError, match="require uncertainty notes"):
        WorldTwinExpectedOutcome(
            outcome_id="outcome-001",
            description="Invalid outcome.",
            measurement_name="authority-state",
            expected_result="human-review-required",
            uncertainty_notes=(),
            evidence_ids=("evidence",),
        )


def test_counterfactual_branches_require_assumptions_outcomes_and_risks() -> None:
    with pytest.raises(ValueError, match="require changed assumptions"):
        branch(changed_assumption_ids=())
    with pytest.raises(ValueError, match="require expected outcomes"):
        branch(expected_outcome_ids=())
    with pytest.raises(ValueError, match="require risk notes"):
        WorldTwinCounterfactualBranch(
            branch_id="branch-001",
            changed_assumption_ids=("assumption-001",),
            expected_outcome_ids=("outcome-001",),
            rationale="Invalid branch without risk notes.",
            risk_notes=(),
            evidence_ids=("evidence",),
        )


def test_scenario_rejects_missing_counterfactual_references() -> None:
    with pytest.raises(ValueError, match="missing assumption"):
        WorldTwinScenarioRecord(
            scenario_id="scenario-001",
            title="Invalid scenario",
            bounded_question="Does the branch reference a real assumption?",
            system_under_test="IX-CognitionKernel",
            boundaries=required_boundaries(),
            assumptions=(assumption(),),
            expected_outcomes=(expected_outcome(),),
            counterfactual_branches=(
                branch(changed_assumption_ids=("missing-assumption",)),
            ),
            evidence_ids=("evidence:scenario",),
        )
    with pytest.raises(ValueError, match="missing expected outcome"):
        WorldTwinScenarioRecord(
            scenario_id="scenario-001",
            title="Invalid scenario",
            bounded_question="Does the branch reference a real outcome?",
            system_under_test="IX-CognitionKernel",
            boundaries=required_boundaries(),
            assumptions=(assumption(),),
            expected_outcomes=(expected_outcome(),),
            counterfactual_branches=(
                branch(expected_outcome_ids=("missing-outcome",)),
            ),
            evidence_ids=("evidence:scenario",),
        )


def test_scenario_reports_missing_boundary_and_counterfactual_evidence() -> None:
    scenario = WorldTwinScenarioRecord(
        scenario_id="scenario-001",
        title="Incomplete scenario",
        bounded_question="Can incomplete scenario evidence pass review?",
        system_under_test="IX-CognitionKernel",
        boundaries=tuple(
            boundary(kind)
            for kind in REQUIRED_WORLDTWIN_BOUNDARY_KINDS
            if kind is not WorldTwinBoundaryKind.HUMAN_REVIEW
        ),
        assumptions=(assumption(),),
        expected_outcomes=(expected_outcome(),),
        counterfactual_branches=(branch(evidence_ids=()),),
        evidence_ids=("evidence:scenario",),
    )

    assert scenario.status is WorldTwinScenarioStatus.NEEDS_REPAIR
    assert scenario.ready_for_human_review is False
    assert scenario.missing_required_boundary_kinds == (
        WorldTwinBoundaryKind.HUMAN_REVIEW,
    )
    assert "missing WorldTwin boundary kinds: human-review" in scenario.readiness_gaps
    assert "WorldTwin counterfactual branches need evidence: branch-001" in (
        scenario.readiness_gaps
    )


def test_unsupported_assumption_and_missing_outcome_evidence_need_evidence() -> None:
    scenario = WorldTwinScenarioRecord(
        scenario_id="scenario-001",
        title="Unsupported assumption scenario",
        bounded_question="Does unsupported evidence block readiness?",
        system_under_test="IX-CognitionKernel",
        boundaries=required_boundaries(),
        assumptions=(
            assumption(
                status=WorldTwinAssumptionStatus.UNSUPPORTED,
                evidence_ids=(),
                required_evidence=("Need replay evidence before review.",),
            ),
        ),
        expected_outcomes=(expected_outcome(evidence_ids=()),),
        counterfactual_branches=(branch(),),
        evidence_ids=("evidence:scenario",),
    )

    assert scenario.status is WorldTwinScenarioStatus.NEEDS_EVIDENCE
    assert scenario.unsupported_assumption_ids == ("assumption-001",)
    assert scenario.outcomes_needing_evidence_ids == ("outcome-001",)
    assert (
        "WorldTwin assumptions need evidence: assumption-001" in scenario.readiness_gaps
    )
    assert "WorldTwin expected outcomes need evidence: outcome-001" in (
        scenario.readiness_gaps
    )


def test_high_impact_disputed_assumption_blocks_scenario() -> None:
    scenario = WorldTwinScenarioRecord(
        scenario_id="scenario-001",
        title="Blocked scenario",
        bounded_question="Does a disputed high-impact assumption block progress?",
        system_under_test="IX-CognitionKernel",
        boundaries=required_boundaries(),
        assumptions=(
            assumption(
                status=WorldTwinAssumptionStatus.DISPUTED,
                impact=WorldTwinImpactLevel.HIGH,
                evidence_ids=("evidence:dispute",),
            ),
        ),
        expected_outcomes=(expected_outcome(),),
        counterfactual_branches=(branch(),),
        evidence_ids=("evidence:scenario",),
    )

    assert scenario.status is WorldTwinScenarioStatus.BLOCKED
    assert scenario.ready_for_human_review is False
    assert scenario.human_authority_state is WaveThreeAuthorityState.BLOCKED
    assert scenario.blocking_gaps == (
        "WorldTwin assumptions block progress: assumption-001",
    )


def test_worldtwin_scenario_converts_to_shared_artifact_ref() -> None:
    artifact = ready_scenario().to_artifact_ref()

    assert artifact.artifact_id == "worldtwin-scenario:scenario-001"
    assert artifact.kind is WaveThreeArtifactKind.WORLDTWIN_SCENARIO
    assert artifact.source_system is WaveThreeSourceSystem.IX_BLACKFOX_WORLDTWIN
    assert artifact.produced_by_engine_id == "causal-world-model"
    assert artifact.produced_by_agent_role_id == "world-modeler"
    assert artifact.allowed_for_automatic_execution is False
    assert artifact.ready_for_human_review is True


def test_worldtwin_scenario_artifact_bundle_links_all_evidence() -> None:
    bundle = ready_scenario().to_artifact_bundle(
        artifact_bundle_id="worldtwin-artifacts"
    )

    assert bundle.has_required_kind_coverage is True
    assert bundle.artifact_ids == ("worldtwin-scenario:scenario-001",)
    assert bundle.ready_for_human_review_artifact_ids == (
        "worldtwin-scenario:scenario-001",
    )
    assert bundle.evidence_link_table == {
        "worldtwin-scenario:scenario-001": (
            "evidence:assumption-001",
            "evidence:branch-001",
            "evidence:outcome-001",
            "evidence:scenario-001",
        )
    }


def test_worldtwin_bundle_reports_ready_and_blocked_scenarios() -> None:
    ready = ready_scenario("scenario-ready")
    blocked = WorldTwinScenarioRecord(
        scenario_id="scenario-blocked",
        title="Blocked scenario",
        bounded_question="Does blocked scenario report correctly?",
        system_under_test="IX-CognitionKernel",
        boundaries=required_boundaries(),
        assumptions=(
            assumption(
                status=WorldTwinAssumptionStatus.EXPIRED,
                impact=WorldTwinImpactLevel.CRITICAL,
                evidence_ids=("evidence:expired",),
            ),
        ),
        expected_outcomes=(expected_outcome(),),
        counterfactual_branches=(branch(),),
        evidence_ids=("evidence:blocked",),
    )
    bundle = WorldTwinScenarioBundle(
        bundle_id="worldtwin-bundle-001",
        scenarios=(blocked, ready),
    )

    assert bundle.scenario_ids == ("scenario-blocked", "scenario-ready")
    assert bundle.ready_scenario_ids == ("scenario-ready",)
    assert bundle.blocked_scenario_ids == ("scenario-blocked",)
    assert bundle.is_complete_for_human_review is False


def test_worldtwin_bundle_rejects_duplicate_scenarios() -> None:
    scenario = ready_scenario()

    with pytest.raises(ValueError, match="Duplicate scenario_id"):
        WorldTwinScenarioBundle(
            bundle_id="worldtwin-bundle-001",
            scenarios=(scenario, scenario),
        )


def test_worldtwin_fingerprints_are_deterministic() -> None:
    first = ready_scenario().fingerprint()
    second = ready_scenario().fingerprint()
    bundle_first = WorldTwinScenarioBundle(
        bundle_id="worldtwin-bundle-001",
        scenarios=(ready_scenario(),),
    ).fingerprint()
    bundle_second = WorldTwinScenarioBundle(
        bundle_id="worldtwin-bundle-001",
        scenarios=(ready_scenario(),),
    ).fingerprint()

    assert first == second
    assert len(first) == 64
    assert bundle_first == bundle_second
    assert len(bundle_first) == 64
