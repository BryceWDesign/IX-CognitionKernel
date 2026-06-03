import pytest

from ix_cognition_kernel.wave4_contracts import (
    WaveFourArtifactKind,
    WaveFourCapabilityArea,
)
from ix_cognition_kernel.wave4_transfer import (
    WaveFourCrossDomainTransferEvaluation,
    WaveFourTransferObservation,
    WaveFourTransferOutcome,
    WaveFourTransferRule,
    WaveFourTransferStatus,
    WaveFourTransferTarget,
    passing_transfer_observation,
)
from ix_cognition_kernel.wave4_trials import (
    WaveFourTrialOutcome,
    WaveFourTrialStatus,
    WaveFourTrialTaskKind,
)


def transfer_rule() -> WaveFourTransferRule:
    return WaveFourTransferRule(
        rule_id="rule-evidence-visible",
        source_domain="AI-assisted code repair governance",
        rule_summary=(
            "Preserve evidence visibility when moving from proposal to review."
        ),
        invariant_conditions=(
            "model output remains untrusted",
            "human review authority remains explicit",
            "evidence ids remain attached to the decision",
        ),
        supporting_evidence_ids=("evidence:source-rule",),
        prohibited_assumptions=("a passing model answer is an approval",),
    )


def transfer_target(
    target_id: str = "target-world-model-scenario",
    *,
    target_domain: str = "WorldTwin consequence scenario review",
) -> WaveFourTransferTarget:
    return WaveFourTransferTarget(
        target_id=target_id,
        target_domain=target_domain,
        adaptation_summary="Apply evidence-visible review to scenario consequences.",
        expected_behavior="Scenario consequences stay linked to evidence and review.",
        scenario_ids=(f"worldtwin:{target_id}",),
        evidence_ids=(f"evidence:{target_id}",),
        risk_notes=("domain analogy may hide unsupported assumptions",),
    )


def transfer_observation(
    observation_id: str = "observation-world-model-scenario",
    *,
    target_id: str = "target-world-model-scenario",
) -> WaveFourTransferObservation:
    return passing_transfer_observation(
        observation_id=observation_id,
        target_id=target_id,
        observed_behavior="Evidence and human-review state stayed attached.",
        matched_invariant_conditions=(
            "model output remains untrusted",
            "human review authority remains explicit",
            "evidence ids remain attached to the decision",
        ),
        evidence_id=f"evidence:{observation_id}",
    )


def transfer_evaluation() -> WaveFourCrossDomainTransferEvaluation:
    return WaveFourCrossDomainTransferEvaluation(
        evaluation_id="transfer-evaluation-001",
        source_rule=transfer_rule(),
        targets=(
            transfer_target(),
            transfer_target(
                "target-memory-quarantine",
                target_domain="Memory quarantine acceptance review",
            ),
        ),
        observations=(
            transfer_observation(),
            transfer_observation(
                "observation-memory-quarantine",
                target_id="target-memory-quarantine",
            ),
        ),
        blackfox_receipt_ids=("blackfox:receipt-transfer-001",),
    )


def test_transfer_rule_requires_invariants_and_supporting_evidence() -> None:
    with pytest.raises(ValueError, match="require invariant conditions"):
        WaveFourTransferRule(
            rule_id="rule-invalid",
            source_domain="repo governance",
            rule_summary="Invalid rule without invariants.",
            invariant_conditions=(),
            supporting_evidence_ids=("evidence:rule",),
        )

    with pytest.raises(ValueError, match="require supporting evidence ids"):
        WaveFourTransferRule(
            rule_id="rule-invalid",
            source_domain="repo governance",
            rule_summary="Invalid rule without evidence.",
            invariant_conditions=("human review remains explicit",),
            supporting_evidence_ids=(),
        )


def test_transfer_target_requires_scenario_and_evidence_links() -> None:
    with pytest.raises(ValueError, match="transfer targets require scenario ids"):
        WaveFourTransferTarget(
            target_id="target-invalid",
            target_domain="scenario review",
            adaptation_summary="Invalid missing scenario.",
            expected_behavior="Evidence remains linked.",
            scenario_ids=(),
            evidence_ids=("evidence:target",),
        )

    with pytest.raises(ValueError, match="transfer targets require evidence ids"):
        WaveFourTransferTarget(
            target_id="target-invalid",
            target_domain="scenario review",
            adaptation_summary="Invalid missing evidence.",
            expected_behavior="Evidence remains linked.",
            scenario_ids=("worldtwin:target",),
            evidence_ids=(),
        )


def test_transfer_observation_enforces_pass_fail_invariant_accounting() -> None:
    with pytest.raises(ValueError, match="cannot violate invariants"):
        WaveFourTransferObservation(
            observation_id="observation-invalid-pass",
            target_id="target-world-model-scenario",
            observed_behavior="A violation was hidden.",
            matched_invariant_conditions=("human review remains explicit",),
            violated_invariant_conditions=("evidence ids remain attached",),
            evidence_ids=("evidence:observation",),
            passed=True,
        )

    with pytest.raises(ValueError, match="require violated invariants"):
        WaveFourTransferObservation(
            observation_id="observation-invalid-fail",
            target_id="target-world-model-scenario",
            observed_behavior="Failure was declared without a violation.",
            matched_invariant_conditions=("human review remains explicit",),
            violated_invariant_conditions=(),
            evidence_ids=("evidence:observation",),
            passed=False,
        )


def test_transfer_evaluation_is_ready_when_all_targets_are_observed() -> None:
    evaluation = transfer_evaluation()

    assert evaluation.status is WaveFourTransferStatus.READY_FOR_CONTROLLED_REVIEW
    assert evaluation.outcome is WaveFourTransferOutcome.TRANSFER_CONFIRMED
    assert evaluation.ready_for_controlled_review is True
    assert evaluation.missing_observation_target_ids == ()
    assert evaluation.failed_observation_ids == ()
    assert evaluation.readiness_gaps == ()
    assert evaluation.claims_agi is False
    assert evaluation.permits_automatic_execution is False
    assert "no AGI claim" in evaluation.review_summary


def test_transfer_evaluation_sorts_targets_and_observations_deterministically() -> None:
    first = transfer_evaluation()
    second = WaveFourCrossDomainTransferEvaluation(
        evaluation_id="transfer-evaluation-001",
        source_rule=transfer_rule(),
        targets=tuple(reversed(first.targets)),
        observations=tuple(reversed(first.observations)),
        blackfox_receipt_ids=("blackfox:receipt-transfer-001",),
    )

    assert first.target_ids == second.target_ids
    assert first.observed_target_ids == second.observed_target_ids
    assert first.fingerprint() == second.fingerprint()


def test_transfer_evaluation_reports_missing_observations_as_evidence_gap() -> None:
    evaluation = WaveFourCrossDomainTransferEvaluation(
        evaluation_id="transfer-missing-observation",
        source_rule=transfer_rule(),
        targets=(transfer_target(), transfer_target("target-not-observed")),
        observations=(transfer_observation(),),
        blackfox_receipt_ids=("blackfox:receipt-transfer-001",),
    )

    assert evaluation.status is WaveFourTransferStatus.NEEDS_EVIDENCE
    assert evaluation.outcome is WaveFourTransferOutcome.TRANSFER_FAILED
    assert evaluation.ready_for_controlled_review is False
    assert evaluation.missing_observation_target_ids == ("target-not-observed",)
    assert "missing transfer observations" in evaluation.readiness_gaps[0]


def test_transfer_evaluation_requires_blackfox_review_receipts() -> None:
    evaluation = WaveFourCrossDomainTransferEvaluation(
        evaluation_id="transfer-missing-blackfox-receipt",
        source_rule=transfer_rule(),
        targets=(transfer_target(),),
        observations=(transfer_observation(),),
        blackfox_receipt_ids=(),
    )

    assert evaluation.status is WaveFourTransferStatus.NEEDS_EVIDENCE
    assert "missing BlackFox receipt ids" in evaluation.readiness_gaps[0]


def test_transfer_evaluation_marks_failed_observations_as_repair_needed() -> None:
    failed = WaveFourTransferObservation(
        observation_id="observation-failed-transfer",
        target_id="target-world-model-scenario",
        observed_behavior="The target accepted a proposal without review evidence.",
        matched_invariant_conditions=("model output remains untrusted",),
        violated_invariant_conditions=("human review authority remains explicit",),
        evidence_ids=("evidence:observation-failed-transfer",),
        passed=False,
    )
    evaluation = WaveFourCrossDomainTransferEvaluation(
        evaluation_id="transfer-failed-observation",
        source_rule=transfer_rule(),
        targets=(transfer_target(),),
        observations=(failed,),
        blackfox_receipt_ids=("blackfox:receipt-transfer-001",),
    )

    assert evaluation.status is WaveFourTransferStatus.NEEDS_REPAIR
    assert evaluation.outcome is WaveFourTransferOutcome.PARTIAL_TRANSFER
    assert evaluation.failed_observation_ids == ("observation-failed-transfer",)


def test_blocked_transfer_evaluation_cannot_carry_results() -> None:
    with pytest.raises(ValueError, match="cannot carry results"):
        WaveFourCrossDomainTransferEvaluation(
            evaluation_id="transfer-blocked-invalid",
            source_rule=transfer_rule(),
            targets=(transfer_target(),),
            observations=(transfer_observation(),),
            blackfox_receipt_ids=("blackfox:receipt-transfer-001",),
            blocked_reasons=("source rule evidence was contradicted",),
        )

    evaluation = WaveFourCrossDomainTransferEvaluation(
        evaluation_id="transfer-blocked",
        source_rule=transfer_rule(),
        targets=(transfer_target(),),
        observations=(),
        blackfox_receipt_ids=("blackfox:receipt-transfer-001",),
        blocked_reasons=("source rule evidence was contradicted",),
    )

    assert evaluation.status is WaveFourTransferStatus.BLOCKED
    assert evaluation.outcome is WaveFourTransferOutcome.BLOCKED
    assert evaluation.blocking_gaps == (
        "transfer-blocked blocked: source rule evidence was contradicted",
    )


def test_transfer_evaluation_rejects_execution_agi_and_independent_validation() -> None:
    with pytest.raises(ValueError, match="cannot permit execution"):
        WaveFourCrossDomainTransferEvaluation(
            evaluation_id="transfer-invalid-execution",
            source_rule=transfer_rule(),
            targets=(transfer_target(),),
            observations=(),
            blackfox_receipt_ids=("blackfox:receipt-transfer-001",),
            permits_automatic_execution=True,
        )

    with pytest.raises(ValueError, match="cannot claim AGI"):
        WaveFourCrossDomainTransferEvaluation(
            evaluation_id="transfer-invalid-agi",
            source_rule=transfer_rule(),
            targets=(transfer_target(),),
            observations=(),
            blackfox_receipt_ids=("blackfox:receipt-transfer-001",),
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="cannot claim independent validation"):
        WaveFourCrossDomainTransferEvaluation(
            evaluation_id="transfer-invalid-independent-validation",
            source_rule=transfer_rule(),
            targets=(transfer_target(),),
            observations=(),
            blackfox_receipt_ids=("blackfox:receipt-transfer-001",),
            independently_validated=True,
        )


def test_transfer_evaluation_converts_to_shared_artifact_and_bundle() -> None:
    evaluation = transfer_evaluation()
    artifact = evaluation.to_artifact_ref()
    links = evaluation.evidence_links()
    bundle = evaluation.to_artifact_bundle()

    assert artifact.kind is WaveFourArtifactKind.TRANSFER_EVALUATION
    assert artifact.capability_area is WaveFourCapabilityArea.CROSS_DOMAIN_TRANSFER
    assert artifact.ready_for_controlled_review is True
    assert artifact.allowed_for_automatic_execution is False
    assert artifact.claims_agi is False
    assert tuple(link.artifact_id for link in links) == (artifact.artifact_id,) * 5
    assert bundle.has_required_kind_coverage is True
    assert bundle.has_required_capability_coverage is True
    assert bundle.ready_for_controlled_review_artifact_ids == (artifact.artifact_id,)


def test_transfer_evaluation_converts_to_controlled_trial_task() -> None:
    task = transfer_evaluation().to_controlled_task()

    assert task.task_kind is WaveFourTrialTaskKind.CROSS_DOMAIN_TRANSFER_PROBE
    assert task.outcome is WaveFourTrialOutcome.PASSED
    assert task.status is WaveFourTrialStatus.READY_FOR_CONTROLLED_REVIEW
    assert task.ready_for_controlled_review is True
    assert len(task.measurements) == 2
    assert len(task.scenario_ids) == 2
    assert task.blackfox_receipt_ids == ("blackfox:receipt-transfer-001",)


def test_failed_transfer_evaluation_converts_to_repair_trial_task() -> None:
    failed = WaveFourTransferObservation(
        observation_id="observation-failed-transfer",
        target_id="target-world-model-scenario",
        observed_behavior="The target accepted a proposal without review evidence.",
        matched_invariant_conditions=("model output remains untrusted",),
        violated_invariant_conditions=("human review authority remains explicit",),
        evidence_ids=("evidence:observation-failed-transfer",),
        passed=False,
    )
    evaluation = WaveFourCrossDomainTransferEvaluation(
        evaluation_id="transfer-failed-observation",
        source_rule=transfer_rule(),
        targets=(transfer_target(),),
        observations=(failed,),
        blackfox_receipt_ids=("blackfox:receipt-transfer-001",),
    )
    task = evaluation.to_controlled_task()

    assert task.outcome is WaveFourTrialOutcome.FAILED
    assert task.status is WaveFourTrialStatus.NEEDS_REPAIR
    assert task.failed_measurement_ids == (
        "transfer-observation:observation-failed-transfer",
    )


def test_transfer_fingerprint_is_sixty_four_hex_characters() -> None:
    fingerprint = transfer_evaluation().fingerprint()

    assert len(fingerprint) == 64
    assert fingerprint == transfer_evaluation().fingerprint()
