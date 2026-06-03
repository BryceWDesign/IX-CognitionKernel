import pytest

from ix_cognition_kernel.wave4_adversarial_robustness import (
    REQUIRED_WAVE_FOUR_ADVERSARIAL_PRESSURE_KINDS,
    WaveFourAdversarialObservation,
    WaveFourAdversarialOutcome,
    WaveFourAdversarialPressureCase,
    WaveFourAdversarialPressureKind,
    WaveFourAdversarialRobustnessProbe,
    WaveFourAdversarialStatus,
    adversarial_pressure_case,
    resisted_adversarial_observation,
)
from ix_cognition_kernel.wave4_contracts import (
    WaveFourArtifactKind,
    WaveFourCapabilityArea,
)
from ix_cognition_kernel.wave4_trials import (
    WaveFourTrialOutcome,
    WaveFourTrialStatus,
    WaveFourTrialTaskKind,
)


def case(
    case_id: str,
    pressure_kind: WaveFourAdversarialPressureKind,
) -> WaveFourAdversarialPressureCase:
    return adversarial_pressure_case(
        case_id=case_id,
        pressure_kind=pressure_kind,
        attack_summary=f"Controlled adversarial pressure for {pressure_kind.value}.",
        target_boundary="human authority and evidence visibility remain mandatory",
        expected_safe_behavior=(
            "Refuse or neutralize unsafe pressure with evidence kept."
        ),
        evidence_id=f"evidence:{case_id}",
        scenario_id=f"worldtwin:{case_id}",
    )


def observation(case_id: str) -> WaveFourAdversarialObservation:
    return resisted_adversarial_observation(
        observation_id=f"observation:{case_id}",
        case_id=case_id,
        observed_behavior="The system preserved evidence and rejected unsafe pressure.",
        evidence_id=f"evidence:observation:{case_id}",
        preserved_evidence_id=f"evidence:{case_id}",
        preserved_uncertainty_id=f"uncertainty:{case_id}",
        blackfox_receipt_id=f"blackfox:{case_id}",
    )


def ready_probe() -> WaveFourAdversarialRobustnessProbe:
    cases = tuple(
        case(f"case:{pressure.value}", pressure)
        for pressure in REQUIRED_WAVE_FOUR_ADVERSARIAL_PRESSURE_KINDS
    )
    return WaveFourAdversarialRobustnessProbe(
        probe_id="adversarial-probe-001",
        cases=cases,
        observations=tuple(observation(item.case_id) for item in cases),
    )


def test_required_adversarial_pressure_kinds_are_locked() -> None:
    assert REQUIRED_WAVE_FOUR_ADVERSARIAL_PRESSURE_KINDS == (
        WaveFourAdversarialPressureKind.PROMPT_INJECTION,
        WaveFourAdversarialPressureKind.ROLE_CONFUSION,
        WaveFourAdversarialPressureKind.AUTHORITY_ESCALATION,
        WaveFourAdversarialPressureKind.EVIDENCE_WITHHOLDING,
        WaveFourAdversarialPressureKind.UNCERTAINTY_ERASURE,
        WaveFourAdversarialPressureKind.REWARD_GAMING_PRESSURE,
        WaveFourAdversarialPressureKind.TOOL_USE_PRESSURE,
        WaveFourAdversarialPressureKind.CONTRADICTION_PRESSURE,
    )


def test_pressure_case_requires_markers_evidence_and_scenario() -> None:
    with pytest.raises(ValueError, match="require unsafe success markers"):
        adversarial_pressure_case(
            case_id="case-invalid",
            pressure_kind=WaveFourAdversarialPressureKind.PROMPT_INJECTION,
            attack_summary="Invalid missing markers.",
            target_boundary="human authority required",
            expected_safe_behavior="refuse unsafe pressure",
            evidence_id="evidence:case-invalid",
            scenario_id="worldtwin:case-invalid",
            unsafe_success_markers=(),
        )

    with pytest.raises(ValueError, match="adversarial cases require evidence ids"):
        WaveFourAdversarialPressureCase(
            case_id="case-invalid",
            pressure_kind=WaveFourAdversarialPressureKind.PROMPT_INJECTION,
            attack_summary="Invalid missing evidence.",
            target_boundary="human authority required",
            expected_safe_behavior="refuse unsafe pressure",
            unsafe_success_markers=("unsafe success",),
            evidence_ids=(),
            scenario_ids=("worldtwin:case-invalid",),
        )

    with pytest.raises(ValueError, match="adversarial cases require scenario ids"):
        WaveFourAdversarialPressureCase(
            case_id="case-invalid",
            pressure_kind=WaveFourAdversarialPressureKind.PROMPT_INJECTION,
            attack_summary="Invalid missing scenario.",
            target_boundary="human authority required",
            expected_safe_behavior="refuse unsafe pressure",
            unsafe_success_markers=("unsafe success",),
            evidence_ids=("evidence:case-invalid",),
            scenario_ids=(),
        )


def test_adversarial_observation_requires_failure_text_when_not_resisted() -> None:
    with pytest.raises(ValueError, match="require failure text"):
        WaveFourAdversarialObservation(
            observation_id="observation-invalid",
            case_id="case:prompt-injection",
            observed_behavior="Unsafe pressure succeeded without failure text.",
            resisted=False,
            triggered_safe_refusal=False,
            preserved_evidence_ids=(),
            preserved_uncertainty_ids=(),
            evidence_ids=("evidence:observation-invalid",),
            blackfox_receipt_ids=(),
        )


def test_passing_observation_requires_preserved_state_and_receipt() -> None:
    with pytest.raises(ValueError, match="must preserve evidence ids"):
        WaveFourAdversarialObservation(
            observation_id="observation-invalid",
            case_id="case:prompt-injection",
            observed_behavior="Claimed pass without preserved evidence.",
            resisted=True,
            triggered_safe_refusal=True,
            preserved_evidence_ids=(),
            preserved_uncertainty_ids=("uncertainty:one",),
            evidence_ids=("evidence:observation-invalid",),
            blackfox_receipt_ids=("blackfox:receipt",),
        )

    with pytest.raises(ValueError, match="must preserve uncertainty"):
        WaveFourAdversarialObservation(
            observation_id="observation-invalid",
            case_id="case:prompt-injection",
            observed_behavior="Claimed pass without preserved uncertainty.",
            resisted=True,
            triggered_safe_refusal=True,
            preserved_evidence_ids=("evidence:case",),
            preserved_uncertainty_ids=(),
            evidence_ids=("evidence:observation-invalid",),
            blackfox_receipt_ids=("blackfox:receipt",),
        )

    with pytest.raises(ValueError, match="require BlackFox receipts"):
        WaveFourAdversarialObservation(
            observation_id="observation-invalid",
            case_id="case:prompt-injection",
            observed_behavior="Claimed pass without receipt.",
            resisted=True,
            triggered_safe_refusal=True,
            preserved_evidence_ids=("evidence:case",),
            preserved_uncertainty_ids=("uncertainty:one",),
            evidence_ids=("evidence:observation-invalid",),
            blackfox_receipt_ids=(),
        )


def test_ready_adversarial_probe_confirms_robustness_without_overclaim() -> None:
    probe = ready_probe()

    assert probe.status is WaveFourAdversarialStatus.READY_FOR_CONTROLLED_REVIEW
    assert probe.outcome is WaveFourAdversarialOutcome.ROBUSTNESS_CONFIRMED
    assert probe.ready_for_controlled_review is True
    assert probe.missing_required_pressure_kinds == ()
    assert probe.missing_observation_case_ids == ()
    assert probe.failed_observation_ids == ()
    assert probe.readiness_gaps == ()
    assert probe.permits_automatic_execution is False
    assert probe.claims_agi is False
    assert "no AGI claim" in probe.review_summary


def test_probe_reports_missing_pressure_coverage_and_observations() -> None:
    probe = WaveFourAdversarialRobustnessProbe(
        probe_id="probe-missing-coverage",
        cases=(
            case(
                "case:prompt-injection",
                WaveFourAdversarialPressureKind.PROMPT_INJECTION,
            ),
        ),
        observations=(),
    )

    assert probe.status is WaveFourAdversarialStatus.NEEDS_EVIDENCE
    assert probe.outcome is WaveFourAdversarialOutcome.NEEDS_EVIDENCE
    assert probe.missing_observation_case_ids == ("case:prompt-injection",)
    assert "missing adversarial pressure coverage" in probe.readiness_gaps[0]
    assert "missing adversarial observations" in probe.readiness_gaps[1]


def test_probe_detects_adversarial_failure_as_repair_needed() -> None:
    pressure_case = case(
        "case:authority-escalation",
        WaveFourAdversarialPressureKind.AUTHORITY_ESCALATION,
    )
    failed = WaveFourAdversarialObservation(
        observation_id="observation:authority-failed",
        case_id="case:authority-escalation",
        observed_behavior="The response accepted authority that was not granted.",
        resisted=False,
        triggered_safe_refusal=False,
        preserved_evidence_ids=(),
        preserved_uncertainty_ids=(),
        evidence_ids=("evidence:authority-failed",),
        blackfox_receipt_ids=(),
        failure_summary="authority escalation succeeded",
    )
    probe = WaveFourAdversarialRobustnessProbe(
        probe_id="probe-failed-pressure",
        cases=(pressure_case,),
        observations=(failed,),
        required_pressure_kinds=(WaveFourAdversarialPressureKind.AUTHORITY_ESCALATION,),
    )

    assert probe.status is WaveFourAdversarialStatus.NEEDS_REPAIR
    assert probe.outcome is WaveFourAdversarialOutcome.ADVERSARIAL_FAILURE_DETECTED
    assert probe.failed_observation_ids == ("observation:authority-failed",)
    assert "failed adversarial pressure" in probe.readiness_gaps[0]


def test_probe_rejects_duplicate_cases_and_unknown_observations() -> None:
    pressure_case = case(
        "case:prompt-injection",
        WaveFourAdversarialPressureKind.PROMPT_INJECTION,
    )

    with pytest.raises(ValueError, match="Duplicate case_id"):
        WaveFourAdversarialRobustnessProbe(
            probe_id="probe-duplicate-case",
            cases=(pressure_case, pressure_case),
            observations=(),
        )

    with pytest.raises(ValueError, match="observations must reference pressure cases"):
        WaveFourAdversarialRobustnessProbe(
            probe_id="probe-unknown-observation",
            cases=(pressure_case,),
            observations=(observation("case:missing"),),
        )


def test_blocked_probe_cannot_carry_observations() -> None:
    pressure_case = case(
        "case:prompt-injection",
        WaveFourAdversarialPressureKind.PROMPT_INJECTION,
    )
    with pytest.raises(ValueError, match="cannot carry observations"):
        WaveFourAdversarialRobustnessProbe(
            probe_id="probe-blocked-invalid",
            cases=(pressure_case,),
            observations=(observation(pressure_case.case_id),),
            blocked_reasons=("adversarial case evidence was contradicted",),
        )

    probe = WaveFourAdversarialRobustnessProbe(
        probe_id="probe-blocked",
        cases=(pressure_case,),
        observations=(),
        blocked_reasons=("adversarial case evidence was contradicted",),
    )

    assert probe.status is WaveFourAdversarialStatus.BLOCKED
    assert probe.outcome is WaveFourAdversarialOutcome.BLOCKED
    assert probe.blocking_gaps == (
        "probe-blocked blocked: adversarial case evidence was contradicted",
    )


def test_probe_rejects_execution_agi_and_independent_validation() -> None:
    pressure_case = case(
        "case:prompt-injection",
        WaveFourAdversarialPressureKind.PROMPT_INJECTION,
    )

    with pytest.raises(ValueError, match="cannot permit execution"):
        WaveFourAdversarialRobustnessProbe(
            probe_id="probe-invalid-execution",
            cases=(pressure_case,),
            observations=(),
            permits_automatic_execution=True,
        )

    with pytest.raises(ValueError, match="cannot claim AGI"):
        WaveFourAdversarialRobustnessProbe(
            probe_id="probe-invalid-agi",
            cases=(pressure_case,),
            observations=(),
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="cannot claim independent validation"):
        WaveFourAdversarialRobustnessProbe(
            probe_id="probe-invalid-independent-validation",
            cases=(pressure_case,),
            observations=(),
            independently_validated=True,
        )


def test_probe_converts_to_shared_artifact_and_bundle() -> None:
    probe = ready_probe()
    artifact = probe.to_artifact_ref()
    bundle = probe.to_artifact_bundle()

    assert artifact.kind is WaveFourArtifactKind.ADVERSARIAL_ROBUSTNESS_RECORD
    assert artifact.capability_area is WaveFourCapabilityArea.ADVERSARIAL_ROBUSTNESS
    assert artifact.ready_for_controlled_review is True
    assert artifact.allowed_for_automatic_execution is False
    assert artifact.claims_agi is False
    assert bundle.has_required_kind_coverage is True
    assert bundle.has_required_capability_coverage is True
    assert bundle.ready_for_controlled_review_artifact_ids == (artifact.artifact_id,)


def test_probe_converts_to_controlled_trial_task() -> None:
    task = ready_probe().to_controlled_task()

    assert task.task_kind is WaveFourTrialTaskKind.ADVERSARIAL_ROBUSTNESS_PROBE
    assert task.outcome is WaveFourTrialOutcome.PASSED
    assert task.status is WaveFourTrialStatus.READY_FOR_CONTROLLED_REVIEW
    assert task.ready_for_controlled_review is True
    assert len(task.measurements) == 8
    assert len(task.scenario_ids) == 8
    assert len(task.blackfox_receipt_ids) == 8


def test_failed_probe_converts_to_failed_trial_task() -> None:
    pressure_case = case(
        "case:authority-escalation",
        WaveFourAdversarialPressureKind.AUTHORITY_ESCALATION,
    )
    failed = WaveFourAdversarialObservation(
        observation_id="observation:authority-failed",
        case_id="case:authority-escalation",
        observed_behavior="The response accepted authority that was not granted.",
        resisted=False,
        triggered_safe_refusal=False,
        preserved_evidence_ids=(),
        preserved_uncertainty_ids=(),
        evidence_ids=("evidence:authority-failed",),
        blackfox_receipt_ids=(),
        failure_summary="authority escalation succeeded",
    )
    probe = WaveFourAdversarialRobustnessProbe(
        probe_id="probe-failed-pressure",
        cases=(pressure_case,),
        observations=(failed,),
        required_pressure_kinds=(WaveFourAdversarialPressureKind.AUTHORITY_ESCALATION,),
    )
    task = probe.to_controlled_task()

    assert task.outcome is WaveFourTrialOutcome.FAILED
    assert task.status is WaveFourTrialStatus.NEEDS_REPAIR
    assert task.failed_measurement_ids == (
        "adversarial-observation:observation:authority-failed",
    )


def test_probe_fingerprint_is_deterministic_despite_input_order() -> None:
    first = ready_probe()
    second = WaveFourAdversarialRobustnessProbe(
        probe_id="adversarial-probe-001",
        cases=tuple(reversed(first.cases)),
        observations=tuple(reversed(first.observations)),
    )

    assert first.case_ids == second.case_ids
    assert first.fingerprint() == second.fingerprint()
    assert len(first.fingerprint()) == 64
