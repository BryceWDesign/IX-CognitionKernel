import pytest

from ix_cognition_kernel.causal import (
    CausalAssumption,
    CausalConstraint,
    CausalRelation,
    ConstraintSeverity,
    CounterfactualNote,
    ExpectedObservation,
    SimpleCausalModel,
)
from ix_cognition_kernel.doctrine import wave_by_number
from ix_cognition_kernel.evaluation import (
    AcceptanceCriterion,
    EvaluationLedger,
    EvaluationRecord,
    EvaluationStatus,
)
from ix_cognition_kernel.planning import (
    EvidenceRequirement,
    PlanNode,
    RollbackStep,
    SimplePlanGraph,
    StopCondition,
    StopSeverity,
)
from ix_cognition_kernel.prototype import (
    WAVE_ONE_REQUIRED_ARTIFACT_IDS,
    WAVE_ONE_REQUIRED_ROLE_IDS,
    ResearchPrototypeSnapshot,
    wave_one_research_prototype_snapshot,
)
from ix_cognition_kernel.purpose import (
    NonAttachedPurposeAssessment,
    PurposeAssessmentInput,
    assess_non_attached_purpose,
)
from ix_cognition_kernel.state import (
    BeliefDisposition,
    BeliefRecord,
    BeliefState,
    ClaimRecord,
    EvidenceRecord,
    EvidenceStatus,
    HumanAuthority,
    UncertaintyStatus,
)


def evidence() -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id="ev-wave1-001",
        summary="A passing integration test supports the Wave 1 snapshot structure.",
        status=EvidenceStatus.VERIFIED,
        sources=("tests/test_research_prototype_snapshot.py",),
        supports_claim_ids=("claim-wave1-001",),
    )


def belief_state() -> BeliefState:
    claim = ClaimRecord(
        claim_id="claim-wave1-001",
        statement="IX-CognitionKernel can represent an integrated Wave 1 snapshot.",
        confidence=0.9,
        uncertainty=UncertaintyStatus.KNOWN,
        evidence_ids=("ev-wave1-001",),
    )
    belief = BeliefRecord(
        belief_id="belief-wave1-001",
        claim=claim,
        provenance=("commit-6-integration-test",),
        rationale="The snapshot binds Wave 1 cognition records without execution.",
        disposition=BeliefDisposition.ACTIVE,
    )
    return BeliefState(beliefs=(belief,), evidence=(evidence(),))


def causal_model() -> SimpleCausalModel:
    constraint = CausalConstraint(
        constraint_id="constraint-wave1-scope",
        description="The causal assumption only describes structured representation.",
        severity=ConstraintSeverity.CONTEXT,
        source_belief_ids=("belief-wave1-001",),
    )
    observation = ExpectedObservation(
        observation_id="observation-wave1-001",
        description="The integrated snapshot exposes all required Wave 1 components.",
        linked_evidence_ids=("ev-wave1-001",),
        required_for_validation=True,
    )
    counterfactual = CounterfactualNote(
        note_id="counterfactual-wave1-001",
        scenario="If evidence coverage is removed, the snapshot reports a gap.",
        expected_difference="The snapshot is no longer Wave 1 ready.",
        uncertainty=UncertaintyStatus.KNOWN,
    )
    assumption = CausalAssumption(
        assumption_id="assumption-wave1-001",
        cause_belief_id="belief-wave1-001",
        effect_belief_id="belief-wave1-effect",
        relation=CausalRelation.ENABLES,
        rationale="A validated belief enables a bounded plan graph representation.",
        confidence=0.82,
        uncertainty=UncertaintyStatus.KNOWN,
        evidence_ids=("ev-wave1-001",),
        constraint_ids=("constraint-wave1-scope",),
        expected_observation_ids=("observation-wave1-001",),
        counterfactual_note_ids=("counterfactual-wave1-001",),
    )
    return SimpleCausalModel(
        model_id="causal-model-wave1",
        assumptions=(assumption,),
        constraints=(constraint,),
        expected_observations=(observation,),
        counterfactuals=(counterfactual,),
    )


def plan_graph() -> SimplePlanGraph:
    requirement = EvidenceRequirement(
        requirement_id="req-wave1-001",
        description="The plan graph must link to verified snapshot evidence.",
        required_evidence_ids=("ev-wave1-001",),
        satisfied_evidence_ids=("ev-wave1-001",),
    )
    rollback = RollbackStep(
        rollback_id="rollback-wave1-001",
        description="Return the proposal to review-only state.",
        restores_node_ids=("node-wave1-001",),
        requires_human_confirmation=True,
    )
    stop = StopCondition(
        condition_id="stop-wave1-001",
        description="Stop if the Wave 1 snapshot tries to authorize execution.",
        severity=StopSeverity.BLOCKING,
        triggered=False,
        evidence_ids=(),
    )
    node = PlanNode(
        node_id="node-wave1-001",
        title="Represent Wave 1 cognition state",
        proposed_action="Create a reviewable snapshot without execution authority.",
        depends_on=(),
        belief_ids=("belief-wave1-001",),
        causal_assumption_ids=("assumption-wave1-001",),
        evidence_requirement_ids=("req-wave1-001",),
        rollback_step_ids=("rollback-wave1-001",),
        stop_condition_ids=("stop-wave1-001",),
        reversible=True,
        human_authority_required=True,
    )
    return SimplePlanGraph(
        graph_id="plan-graph-wave1",
        objective="Represent Wave 1 cognition state as bounded structure.",
        nodes=(node,),
        evidence_requirements=(requirement,),
        rollback_steps=(rollback,),
        stop_conditions=(stop,),
    )


def evaluation_ledger(
    artifact_ids: tuple[str, ...] = WAVE_ONE_REQUIRED_ARTIFACT_IDS,
) -> EvaluationLedger:
    criterion = AcceptanceCriterion(
        criterion_id="criterion-wave1-coverage",
        description="Required Wave 1 artifacts have passing evaluation coverage.",
        required=True,
        satisfied=True,
        evidence_ids=("ev-wave1-001",),
    )
    record = EvaluationRecord(
        evaluation_id="eval-wave1-001",
        title="Wave 1 integrated artifact coverage review",
        evaluated_artifact_ids=artifact_ids,
        criteria=(criterion,),
        status=EvaluationStatus.PASSED,
        evidence_ids=("ev-wave1-001",),
        reasons=("All represented Wave 1 artifacts are covered by this review.",),
        evaluator_role_id="verifier",
    )
    return EvaluationLedger(records=(record,))


def purpose_assessment() -> NonAttachedPurposeAssessment:
    return assess_non_attached_purpose(
        PurposeAssessmentInput(
            statement="IX-CognitionKernel is a bounded Wave 1 research prototype.",
            wave_number=1,
            confidence=0.9,
            evidence_ids=("ev-wave1-001",),
            uncertainty=UncertaintyStatus.KNOWN,
            uncertainty_disclosed=True,
            human_authority=HumanAuthority.REQUIRED,
        )
    )


def ready_snapshot() -> ResearchPrototypeSnapshot:
    return wave_one_research_prototype_snapshot(
        belief_state=belief_state(),
        causal_model=causal_model(),
        plan_graph=plan_graph(),
        evaluation_ledger=evaluation_ledger(),
        purpose_assessment=purpose_assessment(),
    )


def test_research_prototype_snapshot_integrates_wave_one_components() -> None:
    snapshot = ready_snapshot()

    assert snapshot.project_name == "IX-CognitionKernel"
    assert snapshot.maturity_wave.number == 1
    assert snapshot.wave_label == "Wave 1 — Research Prototype"
    assert snapshot.evidence_ids == ("ev-wave1-001",)
    assert tuple(role.role_id for role in snapshot.bounded_agent_roles) == (
        WAVE_ONE_REQUIRED_ROLE_IDS
    )
    assert snapshot.permits_agi_claim is False


def test_research_prototype_snapshot_reports_wave_one_ready_state() -> None:
    snapshot = ready_snapshot()

    assert snapshot.readiness_gaps == ()
    assert snapshot.is_wave_one_ready is True
    assert snapshot.missing_required_artifact_evaluations == ()
    assert snapshot.missing_required_role_ids == ()


def test_research_prototype_snapshot_rejects_wave_zero_maturity_state() -> None:
    with pytest.raises(ValueError, match="target Wave 1"):
        ResearchPrototypeSnapshot(
            project_name="IX-CognitionKernel",
            maturity_wave=wave_by_number(0),
            belief_state=belief_state(),
            causal_model=causal_model(),
            plan_graph=plan_graph(),
            evaluation_ledger=evaluation_ledger(),
            purpose_assessment=purpose_assessment(),
            agent_role_ids=WAVE_ONE_REQUIRED_ROLE_IDS,
        )


def test_research_prototype_snapshot_rejects_unknown_agent_role() -> None:
    with pytest.raises(ValueError, match="Unknown IX-CognitionKernel agent role id"):
        wave_one_research_prototype_snapshot(
            belief_state=belief_state(),
            causal_model=causal_model(),
            plan_graph=plan_graph(),
            evaluation_ledger=evaluation_ledger(),
            purpose_assessment=purpose_assessment(),
            agent_role_ids=("mission-governor", "unknown-role"),
        )


def test_research_prototype_snapshot_rejects_duplicate_agent_role_ids() -> None:
    with pytest.raises(ValueError, match="Duplicate agent role id"):
        wave_one_research_prototype_snapshot(
            belief_state=belief_state(),
            causal_model=causal_model(),
            plan_graph=plan_graph(),
            evaluation_ledger=evaluation_ledger(),
            purpose_assessment=purpose_assessment(),
            agent_role_ids=("mission-governor", "mission-governor"),
        )


def test_missing_required_agent_roles_are_readiness_gaps() -> None:
    snapshot = wave_one_research_prototype_snapshot(
        belief_state=belief_state(),
        causal_model=causal_model(),
        plan_graph=plan_graph(),
        evaluation_ledger=evaluation_ledger(),
        purpose_assessment=purpose_assessment(),
        agent_role_ids=("mission-governor",),
    )

    assert snapshot.missing_required_role_ids == (
        "belief-curator",
        "unknowns-hunter",
        "world-modeler",
        "planner",
        "verifier",
    )
    assert "bounded-agent-roles missing required Wave 1 roles" in (
        snapshot.readiness_gaps
    )
    assert snapshot.is_wave_one_ready is False


def test_missing_required_artifact_coverage_is_a_readiness_gap() -> None:
    snapshot = wave_one_research_prototype_snapshot(
        belief_state=belief_state(),
        causal_model=causal_model(),
        plan_graph=plan_graph(),
        evaluation_ledger=evaluation_ledger(artifact_ids=("belief-state",)),
        purpose_assessment=purpose_assessment(),
    )

    assert snapshot.missing_required_artifact_evaluations == (
        "causal-model",
        "plan-graph",
        "evaluation-ledger",
        "purpose-assessment",
        "bounded-agent-roles",
        "maturity-state",
    )
    assert "evaluation-ledger missing required artifact coverage" in (
        snapshot.readiness_gaps
    )


def test_purpose_violation_is_a_readiness_gap() -> None:
    violating_purpose = assess_non_attached_purpose(
        PurposeAssessmentInput(
            statement="IX-CognitionKernel is a bounded Wave 1 research prototype.",
            wave_number=1,
            confidence=0.9,
            evidence_ids=("ev-wave1-001",),
            uncertainty=UncertaintyStatus.KNOWN,
            uncertainty_disclosed=True,
            human_authority=HumanAuthority.REQUIRED,
            reward_chasing_detected=True,
        )
    )

    snapshot = wave_one_research_prototype_snapshot(
        belief_state=belief_state(),
        causal_model=causal_model(),
        plan_graph=plan_graph(),
        evaluation_ledger=evaluation_ledger(),
        purpose_assessment=violating_purpose,
    )

    assert "purpose-assessment has doctrine violations" in snapshot.readiness_gaps
    assert snapshot.is_wave_one_ready is False
