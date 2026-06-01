import pytest
from test_learning_cycle import cycle_input, memory_candidate, skill_candidate

from ix_cognition_kernel import PROJECT_NAME, WAVE, __version__
from ix_cognition_kernel.cycle import (
    LearnableCognitionCycleResult,
    run_learnable_cognition_cycle,
)
from ix_cognition_kernel.doctrine import ClaimBoundary, current_wave
from ix_cognition_kernel.wave2 import (
    WAVE_TWO_REQUIRED_VALIDATION_ARTIFACT_IDS,
    WaveTwoReadinessSnapshot,
    wave_two_readiness_snapshot,
)


def ready_cycle() -> LearnableCognitionCycleResult:
    return run_learnable_cognition_cycle(cycle_input())


def test_package_identity_is_wave_two() -> None:
    assert PROJECT_NAME == "IX-CognitionKernel"
    assert WAVE == "Wave 2"
    assert __version__ == "0.2.0"


def test_current_wave_is_learnable_causal_cognition_core() -> None:
    wave = current_wave()

    assert wave.number == 2
    assert wave.claim_boundary is ClaimBoundary.CORE
    assert "updates beliefs" in wave.final_form
    assert "stores validated skills" in wave.final_form


def test_wave_two_readiness_snapshot_accepts_complete_learning_cycle() -> None:
    cycle = ready_cycle()
    snapshot = wave_two_readiness_snapshot(learning_cycles=(cycle,))

    assert snapshot.project_name == "IX-CognitionKernel"
    assert snapshot.wave_label == "Wave 2 — Learnable Causal Cognition Core"
    assert snapshot.belief_revision_count == 1
    assert snapshot.causal_revision_count == 1
    assert snapshot.prediction_comparison_count == 1
    assert snapshot.accepted_outcome_count == 1
    assert snapshot.accepted_memory_count == 1
    assert snapshot.validated_skill_count == 1
    assert snapshot.permits_agi_claim is False
    assert snapshot.readiness_gaps == ()
    assert snapshot.is_wave_two_ready is True


def test_wave_two_readiness_snapshot_requires_learning_cycles() -> None:
    with pytest.raises(ValueError, match="learning cycles"):
        wave_two_readiness_snapshot(learning_cycles=())


def test_wave_two_readiness_snapshot_rejects_missing_validation_artifacts() -> None:
    with pytest.raises(ValueError, match="validation artifact coverage"):
        wave_two_readiness_snapshot(
            learning_cycles=(ready_cycle(),),
            validation_artifact_ids=("belief-update-engine",),
        )


def test_wave_two_readiness_snapshot_rejects_duplicate_validation_artifacts() -> None:
    with pytest.raises(ValueError, match="Duplicate validation_artifact_id"):
        wave_two_readiness_snapshot(
            learning_cycles=(ready_cycle(),),
            validation_artifact_ids=(
                *WAVE_TWO_REQUIRED_VALIDATION_ARTIFACT_IDS,
                WAVE_TWO_REQUIRED_VALIDATION_ARTIFACT_IDS[0],
            ),
        )


def test_wave_two_readiness_snapshot_reports_incomplete_cycle_gaps() -> None:
    incomplete = run_learnable_cognition_cycle(
        cycle_input(
            outcome_evidence_ids=(),
            memory_candidates=(),
            skill_candidates=(),
            skill_reuse_records=(),
        )
    )
    snapshot = wave_two_readiness_snapshot(learning_cycles=(incomplete,))

    assert snapshot.is_wave_two_ready is False
    assert "learning-cycles contain incomplete readiness results" in (
        snapshot.readiness_gaps
    )
    assert "outcome-learning has no accepted records" in snapshot.readiness_gaps
    assert "memory-quarantine has no accepted candidates" in snapshot.readiness_gaps
    assert "skill-validation has no validated skills" in snapshot.readiness_gaps


def test_wave_two_readiness_snapshot_reports_memory_and_skill_gaps() -> None:
    no_memory_or_skill = run_learnable_cognition_cycle(
        cycle_input(
            memory_candidates=(),
            skill_candidates=(),
            skill_reuse_records=(),
        )
    )
    snapshot = wave_two_readiness_snapshot(learning_cycles=(no_memory_or_skill,))

    assert snapshot.is_wave_two_ready is False
    assert snapshot.belief_revision_count == 1
    assert snapshot.causal_revision_count == 1
    assert snapshot.accepted_outcome_count == 1
    assert snapshot.accepted_memory_count == 0
    assert snapshot.validated_skill_count == 0
    assert "memory-quarantine has no accepted candidates" in snapshot.readiness_gaps
    assert "skill-validation has no validated skills" in snapshot.readiness_gaps


def test_wave_two_snapshot_rejects_wrong_project_or_wave() -> None:
    cycle = ready_cycle()
    wave = current_wave()

    with pytest.raises(ValueError, match="IX-CognitionKernel"):
        WaveTwoReadinessSnapshot(
            project_name="WrongProject",
            maturity_wave=wave,
            learning_cycles=(cycle,),
            validation_artifact_ids=WAVE_TWO_REQUIRED_VALIDATION_ARTIFACT_IDS,
        )

    with pytest.raises(ValueError, match="target Wave 2"):
        WaveTwoReadinessSnapshot(
            project_name="IX-CognitionKernel",
            maturity_wave=wave.__class__(
                number=1,
                name="Research Prototype",
                final_form="Wrong maturity state.",
                permitted_claim="Wrong claim.",
                claim_boundary=ClaimBoundary.PROTOTYPE,
            ),
            learning_cycles=(cycle,),
            validation_artifact_ids=WAVE_TWO_REQUIRED_VALIDATION_ARTIFACT_IDS,
        )


def test_wave_two_readiness_is_stricter_than_cycle_completeness() -> None:
    cycle = run_learnable_cognition_cycle(
        cycle_input(
            memory_candidates=(memory_candidate(),),
            skill_candidates=(skill_candidate(),),
            skill_reuse_records=(),
        )
    )
    snapshot = wave_two_readiness_snapshot(learning_cycles=(cycle,))

    assert cycle.is_complete_learning_cycle is False
    assert snapshot.is_wave_two_ready is False
    assert "learning-cycles contain incomplete readiness results" in (
        snapshot.readiness_gaps
    )
    assert "skill-validation has no validated skills" in snapshot.readiness_gaps
