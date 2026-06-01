import pytest

from ix_cognition_kernel.planning import (
    EvidenceRequirement,
    PlanNode,
    PlanNodeStatus,
    RollbackStep,
    SimplePlanGraph,
    StopCondition,
    StopSeverity,
)


def satisfied_requirement() -> EvidenceRequirement:
    return EvidenceRequirement(
        requirement_id="req-001",
        description="The plan needs a verified belief-state evidence record.",
        required_evidence_ids=("ev-belief-001",),
        satisfied_evidence_ids=("ev-belief-001",),
    )


def rollback_step() -> RollbackStep:
    return RollbackStep(
        rollback_id="rollback-001",
        description="Return the proposal to draft state without handoff authority.",
        restores_node_ids=("node-draft",),
        requires_human_confirmation=True,
    )


def quiet_stop_condition() -> StopCondition:
    return StopCondition(
        condition_id="stop-001",
        description="Stop if a required belief becomes disputed.",
        severity=StopSeverity.BLOCKING,
        triggered=False,
        evidence_ids=(),
    )


def draft_node() -> PlanNode:
    return PlanNode(
        node_id="node-draft",
        title="Draft structured cognition record",
        proposed_action="Create a reviewable cognition record without execution.",
        depends_on=(),
        belief_ids=("belief-001",),
        causal_assumption_ids=("assumption-001",),
        evidence_requirement_ids=("req-001",),
        rollback_step_ids=("rollback-001",),
        stop_condition_ids=("stop-001",),
        reversible=True,
        human_authority_required=True,
    )


def review_node() -> PlanNode:
    return PlanNode(
        node_id="node-review",
        title="Review structured cognition record",
        proposed_action="Review the draft record before any downstream handoff.",
        depends_on=("node-draft",),
        belief_ids=("belief-001",),
        causal_assumption_ids=(),
        evidence_requirement_ids=(),
        rollback_step_ids=("rollback-001",),
        stop_condition_ids=("stop-001",),
        reversible=True,
        human_authority_required=True,
        status=PlanNodeStatus.READY,
    )


def simple_graph() -> SimplePlanGraph:
    return SimplePlanGraph(
        graph_id="plan-graph-001",
        objective="Represent a bounded Wave 1 plan graph without execution authority.",
        nodes=(draft_node(), review_node()),
        evidence_requirements=(satisfied_requirement(),),
        rollback_steps=(rollback_step(),),
        stop_conditions=(quiet_stop_condition(),),
    )


def test_evidence_requirement_reports_missing_evidence() -> None:
    requirement = EvidenceRequirement(
        requirement_id="req-missing",
        description="Both evidence records are required before readiness.",
        required_evidence_ids=("ev-001", "ev-002"),
        satisfied_evidence_ids=("ev-001",),
    )

    assert requirement.missing_evidence_ids == ("ev-002",)
    assert requirement.is_satisfied is False


def test_plan_node_rejects_self_dependency() -> None:
    with pytest.raises(ValueError, match="depend on themselves"):
        PlanNode(
            node_id="node-loop",
            title="Invalid loop",
            proposed_action="A node cannot depend on itself.",
            depends_on=("node-loop",),
            belief_ids=(),
            causal_assumption_ids=(),
            evidence_requirement_ids=(),
            rollback_step_ids=(),
            stop_condition_ids=(),
            reversible=False,
            human_authority_required=True,
        )


def test_reversible_plan_node_requires_rollback_step_ids() -> None:
    with pytest.raises(ValueError, match="rollback_step_ids"):
        PlanNode(
            node_id="node-no-rollback",
            title="Missing rollback",
            proposed_action="Reversible proposals need rollback metadata.",
            depends_on=(),
            belief_ids=(),
            causal_assumption_ids=(),
            evidence_requirement_ids=(),
            rollback_step_ids=(),
            stop_condition_ids=(),
            reversible=True,
            human_authority_required=True,
        )


def test_triggered_stop_condition_requires_evidence_ids() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        StopCondition(
            condition_id="stop-triggered-without-evidence",
            description="Triggered stops must explain what triggered them.",
            severity=StopSeverity.BLOCKING,
            triggered=True,
            evidence_ids=(),
        )


def test_triggered_blocking_stop_condition_blocks_node() -> None:
    condition = StopCondition(
        condition_id="stop-triggered",
        description="A triggered blocking stop blocks attached plan nodes.",
        severity=StopSeverity.KILL_SWITCH,
        triggered=True,
        evidence_ids=("ev-stop-001",),
    )

    assert condition.blocks_node is True


def test_simple_plan_graph_reports_roots_terminal_nodes_and_ready_nodes() -> None:
    graph = simple_graph()

    assert graph.root_nodes == (draft_node(),)
    assert graph.terminal_nodes == (review_node(),)
    assert graph.ready_nodes(completed_node_ids=()) == (draft_node(),)
    assert graph.ready_nodes(completed_node_ids=("node-draft",)) == (review_node(),)
    assert graph.blocked_nodes == ()
    assert graph.unmet_evidence_requirements == ()


def test_simple_plan_graph_rejects_duplicate_node_ids() -> None:
    node = draft_node()

    with pytest.raises(ValueError, match="Duplicate node_id"):
        SimplePlanGraph(
            graph_id="plan-graph-duplicates",
            objective="Duplicate node ids are not valid.",
            nodes=(node, node),
            evidence_requirements=(satisfied_requirement(),),
            rollback_steps=(rollback_step(),),
            stop_conditions=(quiet_stop_condition(),),
        )


def test_simple_plan_graph_rejects_unknown_dependency_reference() -> None:
    bad_node = PlanNode(
        node_id="node-bad-reference",
        title="Bad dependency",
        proposed_action="Reference a missing dependency.",
        depends_on=("node-missing",),
        belief_ids=(),
        causal_assumption_ids=(),
        evidence_requirement_ids=(),
        rollback_step_ids=("rollback-001",),
        stop_condition_ids=(),
        reversible=True,
        human_authority_required=True,
    )

    with pytest.raises(ValueError, match="unknown dependency node_id"):
        SimplePlanGraph(
            graph_id="plan-graph-bad-dependency",
            objective="Unknown dependencies must fail closed.",
            nodes=(bad_node,),
            evidence_requirements=(),
            rollback_steps=(rollback_step(),),
            stop_conditions=(),
        )


def test_simple_plan_graph_rejects_dependency_cycle() -> None:
    first = PlanNode(
        node_id="node-a",
        title="Node A",
        proposed_action="Depends on B.",
        depends_on=("node-b",),
        belief_ids=(),
        causal_assumption_ids=(),
        evidence_requirement_ids=(),
        rollback_step_ids=(),
        stop_condition_ids=(),
        reversible=False,
        human_authority_required=True,
    )
    second = PlanNode(
        node_id="node-b",
        title="Node B",
        proposed_action="Depends on A.",
        depends_on=("node-a",),
        belief_ids=(),
        causal_assumption_ids=(),
        evidence_requirement_ids=(),
        rollback_step_ids=(),
        stop_condition_ids=(),
        reversible=False,
        human_authority_required=True,
    )

    with pytest.raises(ValueError, match="dependency cycle"):
        SimplePlanGraph(
            graph_id="plan-graph-cycle",
            objective="Cycles must be rejected.",
            nodes=(first, second),
            evidence_requirements=(),
            rollback_steps=(),
            stop_conditions=(),
        )


def test_simple_plan_graph_blocks_nodes_with_triggered_blocking_stops() -> None:
    stop = StopCondition(
        condition_id="stop-blocking",
        description="A contradiction was found before review.",
        severity=StopSeverity.BLOCKING,
        triggered=True,
        evidence_ids=("ev-contradiction",),
    )
    node = PlanNode(
        node_id="node-blocked-by-stop",
        title="Blocked by stop condition",
        proposed_action="This node should not be ready.",
        depends_on=(),
        belief_ids=(),
        causal_assumption_ids=(),
        evidence_requirement_ids=(),
        rollback_step_ids=("rollback-001",),
        stop_condition_ids=("stop-blocking",),
        reversible=True,
        human_authority_required=True,
    )
    graph = SimplePlanGraph(
        graph_id="plan-graph-blocked",
        objective="Triggered stop conditions block readiness.",
        nodes=(node,),
        evidence_requirements=(),
        rollback_steps=(rollback_step(),),
        stop_conditions=(stop,),
    )

    assert graph.blocking_stop_conditions == (stop,)
    assert graph.blocked_nodes == (node,)
    assert graph.ready_nodes(completed_node_ids=()) == ()


def test_simple_plan_graph_keeps_nodes_with_unmet_evidence_out_of_ready_set() -> None:
    requirement = EvidenceRequirement(
        requirement_id="req-unmet",
        description="Required evidence has not been satisfied.",
        required_evidence_ids=("ev-required",),
        satisfied_evidence_ids=(),
    )
    node = PlanNode(
        node_id="node-needs-evidence",
        title="Needs evidence",
        proposed_action="Remain proposed until evidence is satisfied.",
        depends_on=(),
        belief_ids=(),
        causal_assumption_ids=(),
        evidence_requirement_ids=("req-unmet",),
        rollback_step_ids=("rollback-001",),
        stop_condition_ids=(),
        reversible=True,
        human_authority_required=True,
    )
    graph = SimplePlanGraph(
        graph_id="plan-graph-needs-evidence",
        objective="Unmet evidence blocks readiness.",
        nodes=(node,),
        evidence_requirements=(requirement,),
        rollback_steps=(rollback_step(),),
        stop_conditions=(),
    )

    assert graph.unmet_evidence_requirements == (requirement,)
    assert graph.ready_nodes(completed_node_ids=()) == ()


def test_ready_nodes_rejects_unknown_completed_node_ids() -> None:
    with pytest.raises(ValueError, match="not in plan graph"):
        simple_graph().ready_nodes(completed_node_ids=("node-missing",))
