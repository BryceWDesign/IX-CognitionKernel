"""Integration tests for Wave 8 bounded cognition trial chain."""

from __future__ import annotations

from tests.test_wave8_transfer_challenge import _environment
from tests.test_wave8_transfer_challenge import _passing_run as passing_run
from tests.test_wave8_transfer_challenge import _suite
from ix_cognition_kernel.wave8_baseline_comparison import (
    BaselineSystemRecord,
    build_baseline_report,
)
from ix_cognition_kernel.wave8_replay_validator import (
    artifact_from_baseline_report,
    artifact_from_episode_run,
    artifact_from_transfer_report,
    validate_replay_packet,
)
from ix_cognition_kernel.wave8_skill_synthesis import (
    create_skill_library_entry,
    plan_skill_reuse,
    synthesize_skill_candidate,
    validate_skill_candidate,
)
from ix_cognition_kernel.wave8_transfer_challenge import (
    TransferClaimDecision,
    build_transfer_trial,
    evaluate_transfer_challenge,
)


def test_wave8_integrated_trial_promotes_replayable_transfer_skill() -> None:
    suite = _suite()
    trials = tuple(
        build_transfer_trial(
            trial_id=f"trial-{task.task_id}",
            task=task,
            band=task.difficulty_band.value,
            episode_run=passing_run(task=task),
        )
        for task in suite.tasks
    )
    transfer_report = evaluate_transfer_challenge(
        report_id="integrated-transfer",
        suite=suite,
        trials=trials,
    )
    assert transfer_report.decision is TransferClaimDecision.TRANSFER_DEMONSTRATED

    skill = synthesize_skill_candidate(
        skill_id="skill-integrated",
        name="Bounded grid move skill",
        purpose="Reuse measured grid movement under bounded review.",
        trials=trials,
        evidence_ids=("skill-evidence",),
    )
    validation = validate_skill_candidate(
        validation_id="validation-integrated",
        candidate=skill,
        transfer_report=transfer_report,
    )
    entry = create_skill_library_entry(
        entry_id="entry-integrated",
        validation=validation,
        evidence_ids=("library-evidence",),
    )
    reuse_plan = plan_skill_reuse(
        plan_id="reuse-integrated",
        entry=entry,
        task=suite.tasks[0],
    )

    baseline = BaselineSystemRecord(
        baseline_id="baseline-integrated",
        name="Static baseline",
        version="0.1",
        replayable_episode_count=1,
        transfer_success_rate=0.2,
        hidden_success_rate=0.1,
        failure_rate=0.8,
        evidence_ids=("baseline-evidence",),
    )
    candidate = BaselineSystemRecord(
        baseline_id="candidate-integrated",
        name="Wave 8 candidate",
        version="0.1",
        replayable_episode_count=3,
        transfer_success_rate=1.0,
        hidden_success_rate=1.0,
        failure_rate=0.0,
        evidence_ids=("candidate-evidence",),
    )
    baseline_report = build_baseline_report(
        report_id="baseline-integrated",
        transfer_report=transfer_report,
        candidate=candidate,
        baseline=baseline,
        evidence_ids=("baseline-report-evidence",),
    )
    replay_report = validate_replay_packet(
        report_id="replay-integrated",
        purpose="Validate bounded replay chain for review.",
        artifacts=(
            artifact_from_episode_run(
                artifact_id="artifact-episode",
                run=passing_run(task=suite.tasks[0]),
                evidence_ids=("episode-evidence",),
            ),
            artifact_from_transfer_report(
                artifact_id="artifact-transfer",
                report=transfer_report,
                evidence_ids=("transfer-evidence",),
            ),
            artifact_from_baseline_report(
                artifact_id="artifact-baseline",
                report=baseline_report,
                evidence_ids=("baseline-evidence",),
            ),
        ),
    )

    assert validation.ready
    assert reuse_plan.ready
    assert replay_report.replayable_artifact_count == 3
    assert _environment().environment_id == "env-transfer"
