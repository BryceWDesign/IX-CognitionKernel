import pytest

from ix_cognition_kernel.wave7_goal_pressure import (
    GoalConflict,
    GoalConflictKind,
    GoalPressureDecision,
    GoalPriority,
    GoalRetirement,
    GoalStatus,
    ResearchGoal,
    Subgoal,
    SubgoalStatus,
    assess_goal_pressure,
    build_goal_pressure_report,
)


def _goal(
    *,
    status: GoalStatus = GoalStatus.READY_FOR_REVIEW,
    priority: GoalPriority = GoalPriority.HIGH,
    blocked_reason: str = "",
    subgoal_ids: tuple[str, ...] = ("subgoal-1",),
) -> ResearchGoal:
    return ResearchGoal(
        goal_id="goal-1",
        title="Improve transfer under novelty.",
        mission_alignment=(
            "Pressure-test durable generalization without granting authority."
        ),
        status=status,
        priority=priority,
        subgoal_ids=subgoal_ids,
        success_criteria=("measured transfer trial survives review",),
        non_goal_ids=("claim-agi-by-declaration",),
        doctrine_ids=("goals-are-not-permission", "human-authority-final"),
        authority_refs=("human-authority-1",),
        evidence_ids=("goal-evidence-1",),
        blocked_reason=blocked_reason,
    )


def _subgoal(
    *,
    subgoal_id: str = "subgoal-1",
    status: SubgoalStatus = SubgoalStatus.READY_FOR_REVIEW,
    blocked_reason: str = "",
) -> Subgoal:
    return Subgoal(
        subgoal_id=subgoal_id,
        parent_goal_id="goal-1",
        title="Run a bounded novelty transfer trial.",
        status=status,
        bounded_trial_recommendations=("trial-transfer-1",),
        evidence_ids=("subgoal-evidence-1",),
        authority_refs=("human-authority-1",),
        completion_criteria=("trial result is measured and replayable",),
        blocked_reason=blocked_reason,
    )


def _conflict(
    *,
    conflict_id: str = "conflict-1",
    kind: GoalConflictKind = GoalConflictKind.EVIDENCE_CONFLICT,
    unresolved: bool = True,
    mitigation: str = "",
) -> GoalConflict:
    return GoalConflict(
        conflict_id=conflict_id,
        goal_id="goal-1",
        kind=kind,
        summary="Evidence is incomplete for one transfer condition.",
        evidence_ids=("conflict-evidence-1",),
        authority_refs=("human-authority-1",),
        unresolved=unresolved,
        mitigation=mitigation,
    )


def _retirement() -> GoalRetirement:
    return GoalRetirement(
        retirement_id="retirement-1",
        goal_id="goal-1",
        reason="Goal was replaced by a narrower measured transfer target.",
        preserved_evidence_ids=("retirement-evidence-1",),
        authority_refs=("human-authority-1",),
        lesson="Future goal pressure must narrow transfer domains earlier.",
    )


def test_research_goal_is_bounded_and_not_authority() -> None:
    goal = _goal()

    assert goal.ready_for_review
    assert goal.requires_elevated_review
    assert not goal.blocked
    assert goal.fingerprint() == goal.fingerprint()
    assert len(goal.fingerprint()) == 64

    with pytest.raises(ValueError, match="must not claim autonomous authority"):
        ResearchGoal(
            goal_id="goal-authority",
            title="Bad authority goal.",
            mission_alignment="Bad mission alignment.",
            status=GoalStatus.ACTIVE,
            priority=GoalPriority.HIGH,
            subgoal_ids=("subgoal-1",),
            success_criteria=("bad criterion",),
            non_goal_ids=("bad-non-goal",),
            doctrine_ids=("human-authority-final",),
            authority_refs=("human-authority-1",),
            evidence_ids=("goal-evidence-1",),
            claims_autonomous_authority=True,
        )


def test_research_goal_rejects_doctrine_override() -> None:
    with pytest.raises(ValueError, match="must not override doctrine"):
        ResearchGoal(
            goal_id="goal-doctrine",
            title="Bad doctrine goal.",
            mission_alignment="Bad mission alignment.",
            status=GoalStatus.ACTIVE,
            priority=GoalPriority.HIGH,
            subgoal_ids=("subgoal-1",),
            success_criteria=("bad criterion",),
            non_goal_ids=("bad-non-goal",),
            doctrine_ids=("human-authority-final",),
            authority_refs=("human-authority-1",),
            evidence_ids=("goal-evidence-1",),
            overrides_doctrine=True,
        )


def test_blocked_goal_requires_reason() -> None:
    blocked = _goal(
        status=GoalStatus.BLOCKED,
        blocked_reason="Authority boundary conflict.",
    )

    assert blocked.blocked
    assert not blocked.ready_for_review

    with pytest.raises(ValueError, match="require blocked_reason"):
        _goal(status=GoalStatus.BLOCKED)


def test_subgoal_recommends_trials_without_granting_permission() -> None:
    subgoal = _subgoal()

    assert subgoal.ready_for_review
    assert subgoal.recommends_trials
    assert not subgoal.complete
    assert subgoal.fingerprint() == subgoal.fingerprint()
    assert len(subgoal.fingerprint()) == 64

    with pytest.raises(ValueError, match="must not grant permission"):
        Subgoal(
            subgoal_id="subgoal-permission",
            parent_goal_id="goal-1",
            title="Bad permission subgoal.",
            status=SubgoalStatus.IN_PROGRESS,
            bounded_trial_recommendations=("trial-1",),
            evidence_ids=("subgoal-evidence-1",),
            authority_refs=("human-authority-1",),
            completion_criteria=("criterion",),
            grants_permission=True,
        )


def test_blocked_subgoal_requires_reason() -> None:
    blocked = _subgoal(
        status=SubgoalStatus.BLOCKED,
        blocked_reason="Missing body contract.",
    )

    assert blocked.blocked

    with pytest.raises(ValueError, match="require blocked_reason"):
        _subgoal(status=SubgoalStatus.BLOCKED)


def test_goal_conflict_blocks_only_material_unresolved_conflicts() -> None:
    evidence_conflict = _conflict()
    authority_conflict = _conflict(
        conflict_id="conflict-authority",
        kind=GoalConflictKind.AUTHORITY_CONFLICT,
    )
    resolved_authority = _conflict(
        conflict_id="conflict-resolved",
        kind=GoalConflictKind.AUTHORITY_CONFLICT,
        unresolved=False,
        mitigation="Human review boundary was added.",
    )

    assert not evidence_conflict.blocks_goal
    assert authority_conflict.blocks_goal
    assert not resolved_authority.blocks_goal
    assert authority_conflict.fingerprint() == authority_conflict.fingerprint()

    with pytest.raises(ValueError, match="require mitigation"):
        _conflict(
            kind=GoalConflictKind.AUTHORITY_CONFLICT,
            unresolved=False,
        )


def test_goal_retirement_preserves_evidence_and_lesson() -> None:
    retirement = _retirement()

    assert retirement.preserved_evidence_ids == ("retirement-evidence-1",)
    assert retirement.lesson == (
        "Future goal pressure must narrow transfer domains earlier."
    )
    assert retirement.fingerprint() == retirement.fingerprint()
    assert len(retirement.fingerprint()) == 64


def test_assess_goal_pressure_ready_for_review() -> None:
    pressure = assess_goal_pressure(
        pressure_id="pressure-1",
        goal=_goal(),
        subgoals=(_subgoal(),),
        recommended_next_trial_ids=("trial-transfer-1",),
        notes=("Goal pressure recommends bounded trial only.",),
    )

    assert pressure.ready_for_review
    assert not pressure.blocks_claim
    assert pressure.recommends_trials
    assert pressure.complete_subgoal_ids == ()
    assert pressure.blocked_subgoal_ids == ()
    assert pressure.blocking_reason_ids == ()
    assert pressure.evidence_ids == ("goal-evidence-1", "subgoal-evidence-1")
    assert pressure.fingerprint() == pressure.fingerprint()
    assert len(pressure.fingerprint()) == 64


def test_assess_goal_pressure_blocks_on_material_conflict() -> None:
    pressure = assess_goal_pressure(
        pressure_id="pressure-blocked",
        goal=_goal(status=GoalStatus.ACTIVE),
        subgoals=(_subgoal(status=SubgoalStatus.IN_PROGRESS),),
        conflicts=(
            _conflict(
                kind=GoalConflictKind.AUTHORITY_CONFLICT,
            ),
        ),
        recommended_next_trial_ids=("trial-transfer-1",),
    )

    assert pressure.decision is GoalPressureDecision.BLOCKED
    assert pressure.blocks_claim
    assert pressure.blocking_conflict_ids == ("conflict-1",)
    assert "conflict-blocks-goal" in pressure.blocking_reason_ids


def test_assess_goal_pressure_blocks_on_blocked_subgoal() -> None:
    pressure = assess_goal_pressure(
        pressure_id="pressure-blocked-subgoal",
        goal=_goal(status=GoalStatus.ACTIVE),
        subgoals=(
            _subgoal(
                status=SubgoalStatus.BLOCKED,
                blocked_reason="Missing measured outcome.",
            ),
        ),
    )

    assert pressure.blocks_claim
    assert pressure.blocked_subgoal_ids == ("subgoal-1",)
    assert "subgoal-blocked" in pressure.blocking_reason_ids


def test_goal_pressure_rejects_missing_subgoal_link() -> None:
    with pytest.raises(ValueError, match="missing subgoals"):
        assess_goal_pressure(
            pressure_id="pressure-missing-subgoal",
            goal=_goal(subgoal_ids=("subgoal-missing",)),
            subgoals=(_subgoal(),),
        )


def test_retired_goal_requires_retirement_record_for_non_blocking_pressure() -> None:
    pressure = assess_goal_pressure(
        pressure_id="pressure-retired",
        goal=_goal(
            status=GoalStatus.RETIRED,
            subgoal_ids=(),
            priority=GoalPriority.LOW,
        ),
        subgoals=(),
        retirements=(_retirement(),),
    )

    assert not pressure.blocks_claim
    assert pressure.retirement_ids == ("retirement-1",)
    assert "retirement-evidence-1" in pressure.evidence_ids


def test_retired_goal_without_retirement_record_blocks_claim() -> None:
    pressure = assess_goal_pressure(
        pressure_id="pressure-retired-missing-record",
        goal=_goal(
            status=GoalStatus.RETIRED,
            subgoal_ids=(),
            priority=GoalPriority.LOW,
        ),
        subgoals=(),
    )

    assert pressure.blocks_claim
    assert "retired-goal-missing-retirement-record" in pressure.blocking_reason_ids


def test_goal_pressure_report_ready_for_review() -> None:
    pressure = assess_goal_pressure(
        pressure_id="pressure-ready",
        goal=_goal(),
        subgoals=(_subgoal(),),
        recommended_next_trial_ids=("trial-transfer-1",),
    )
    report = build_goal_pressure_report(
        report_id="goal-pressure-report-1",
        pressures=(pressure,),
        decision=GoalPressureDecision.READY_FOR_REVIEW,
        notes=("Goal pressure is ready for review.",),
    )

    assert report.ready_for_review
    assert not report.blocks_claim
    assert report.pressure_ids == ("pressure-ready",)
    assert report.review_ready_pressure_ids == ("pressure-ready",)
    assert report.trial_recommending_pressure_ids == ("pressure-ready",)
    assert "goal-evidence-1" in report.evidence_ids
    assert report.fingerprint() == report.fingerprint()
    assert len(report.fingerprint()) == 64


def test_goal_pressure_report_rejects_ready_state_with_blockers() -> None:
    pressure = assess_goal_pressure(
        pressure_id="pressure-blocked",
        goal=_goal(status=GoalStatus.ACTIVE),
        subgoals=(
            _subgoal(
                status=SubgoalStatus.BLOCKED,
                blocked_reason="Missing measured outcome.",
            ),
        ),
    )

    with pytest.raises(ValueError, match="cannot block"):
        build_goal_pressure_report(
            report_id="goal-pressure-report-bad",
            pressures=(pressure,),
            decision=GoalPressureDecision.READY_FOR_REVIEW,
        )


def test_blocked_goal_pressure_report_preserves_blockers() -> None:
    pressure = assess_goal_pressure(
        pressure_id="pressure-blocked",
        goal=_goal(status=GoalStatus.ACTIVE),
        subgoals=(
            _subgoal(
                status=SubgoalStatus.BLOCKED,
                blocked_reason="Missing measured outcome.",
            ),
        ),
    )
    report = build_goal_pressure_report(
        report_id="goal-pressure-report-blocked",
        pressures=(pressure,),
        decision=GoalPressureDecision.BLOCKED,
        notes=("Blocked subgoal remains visible.",),
    )

    assert report.blocks_claim
    assert not report.ready_for_review
    assert report.blocking_pressure_ids == ("pressure-blocked",)
