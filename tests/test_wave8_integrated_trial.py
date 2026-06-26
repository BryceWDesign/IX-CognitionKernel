import pytest

from ix_cognition_kernel.wave8_integrated_trial import (
    IntegratedWave8TrialResult,
    build_integrated_wave8_trial,
)
from ix_cognition_kernel.wave8_release_manifest import Wave8ReleaseDecision


def test_integrated_wave8_trial_builds_ready_review_handoff_chain() -> None:
    result = build_integrated_wave8_trial(
        trial_id="integrated-trial-1",
        human_authority_evidence_ids=("human-authority-evidence-1",),
    )

    assert result.ready
    assert result.transfer_report.ready
    assert result.skill_validation.ready
    assert result.skill_entry.reusable
    assert result.world_snapshot.active_rules
    assert result.baseline_report.ready
    assert result.replay_report.ready
    assert result.external_review_packet.ready
    assert result.release_manifest.ready
    assert result.release_manifest.decision is Wave8ReleaseDecision.READY_FOR_REVIEW_HANDOFF
    assert len(result.runs) == result.suite.task_count
    assert result.fingerprint() == result.fingerprint()
    assert len(result.fingerprint()) == 64


def test_integrated_wave8_trial_requires_human_authority_evidence() -> None:
    with pytest.raises(ValueError, match="ready release manifest"):
        build_integrated_wave8_trial(
            trial_id="integrated-trial-no-human-authority",
            human_authority_evidence_ids=(),
        )


def test_integrated_wave8_trial_result_rejects_missing_run_coverage() -> None:
    result = build_integrated_wave8_trial(
        trial_id="integrated-trial-coverage",
        human_authority_evidence_ids=("human-authority-evidence-1",),
    )

    with pytest.raises(ValueError, match="must cover every suite task"):
        IntegratedWave8TrialResult(
            trial_id="integrated-trial-bad-coverage",
            suite=result.suite,
            task_validation_fingerprint=result.task_validation_fingerprint,
            runs=result.runs[:-1],
            transfer_report=result.transfer_report,
            skill_validation=result.skill_validation,
            skill_entry=result.skill_entry,
            world_snapshot=result.world_snapshot,
            baseline_report=result.baseline_report,
            replay_report=result.replay_report,
            external_review_packet=result.external_review_packet,
            release_manifest=result.release_manifest,
        )


def test_integrated_wave8_trial_result_has_stable_payload_references() -> None:
    first = build_integrated_wave8_trial(
        trial_id="integrated-trial-stable",
        human_authority_evidence_ids=("human-authority-evidence-1",),
    )
    second = build_integrated_wave8_trial(
        trial_id="integrated-trial-stable",
        human_authority_evidence_ids=("human-authority-evidence-1",),
    )

    assert first.fingerprint() == second.fingerprint()
    assert first.canonical_payload() == second.canonical_payload()
