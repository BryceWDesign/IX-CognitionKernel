import pytest

from ix_cognition_kernel.wave4_contracts import (
    WaveFourArtifactKind,
    WaveFourCapabilityArea,
    WaveFourEvidenceRelation,
)
from ix_cognition_kernel.wave4_transfer import (
    WaveFourCrossDomainTransferEvaluation,
    WaveFourTransferObservation,
    WaveFourTransferRule,
    WaveFourTransferStatus,
    WaveFourTransferTarget,
    passing_transfer_observation,
)
from ix_cognition_kernel.wave4_transfer_bundle import (
    WaveFourCrossDomainTransferBundle,
    WaveFourTransferFailureCase,
    WaveFourTransferFailureMode,
)
from ix_cognition_kernel.wave4_trials import (
    WaveFourTrialStatus,
    WaveFourTrialTaskKind,
)


def transfer_rule(
    source_domain: str = "AI-assisted code repair governance",
) -> WaveFourTransferRule:
    return WaveFourTransferRule(
        rule_id=f"rule:{source_domain}",
        source_domain=source_domain,
        rule_summary="Preserve evidence and review authority during transfer.",
        invariant_conditions=(
            "model output remains untrusted",
            "human review authority remains explicit",
            "evidence ids remain attached",
        ),
        supporting_evidence_ids=(f"evidence:rule:{source_domain}",),
        prohibited_assumptions=("analogy alone is proof",),
    )


def target(target_id: str, target_domain: str) -> WaveFourTransferTarget:
    return WaveFourTransferTarget(
        target_id=target_id,
        target_domain=target_domain,
        adaptation_summary=f"Apply transfer discipline to {target_domain}.",
        expected_behavior="Evidence and review state remain visible.",
        scenario_ids=(f"worldtwin:{target_id}",),
        evidence_ids=(f"evidence:{target_id}",),
        risk_notes=("domain transfer may hide unsupported assumptions",),
    )


def observation(observation_id: str, target_id: str) -> WaveFourTransferObservation:
    return passing_transfer_observation(
        observation_id=observation_id,
        target_id=target_id,
        observed_behavior="The target preserved review authority and evidence ids.",
        matched_invariant_conditions=(
            "model output remains untrusted",
            "human review authority remains explicit",
            "evidence ids remain attached",
        ),
        evidence_id=f"evidence:{observation_id}",
    )


def evaluation(
    evaluation_id: str = "transfer-evaluation-governance",
    *,
    source_domain: str = "AI-assisted code repair governance",
    target_pairs: tuple[tuple[str, str], ...] = (
        ("target-worldtwin-scenario", "WorldTwin consequence scenario review"),
        ("target-memory-quarantine", "Memory quarantine review"),
    ),
    blackfox_receipts: tuple[str, ...] = ("blackfox:receipt-transfer",),
) -> WaveFourCrossDomainTransferEvaluation:
    targets = tuple(
        target(target_id, target_domain)
        for target_id, target_domain in target_pairs
    )
    observations = tuple(
        observation(f"observation:{target_id}", target_id)
        for target_id, _target_domain in target_pairs
    )
    return WaveFourCrossDomainTransferEvaluation(
        evaluation_id=evaluation_id,
        source_rule=transfer_rule(source_domain),
        targets=targets,
        observations=observations,
        blackfox_receipt_ids=blackfox_receipts,
    )


def failure_case(
    failure_case_id: str = "failure-hidden-authority",
    *,
    evaluation_id: str = "transfer-evaluation-governance",
    target_id: str = "target-worldtwin-scenario",
    detected: bool = True,
    repair_recommendation: str = (
        "Require explicit human-review authority before reuse."
    ),
) -> WaveFourTransferFailureCase:
    return WaveFourTransferFailureCase(
        failure_case_id=failure_case_id,
        evaluation_id=evaluation_id,
        target_id=target_id,
        failure_mode=WaveFourTransferFailureMode.HIDDEN_AUTHORITY_ESCALATION,
        violated_invariant="human review authority remains explicit",
        expected_detection_summary="Detect hidden transfer from evidence to authority.",
        evidence_ids=(f"evidence:{failure_case_id}",),
        detected=detected,
        repair_recommendation=repair_recommendation,
    )


def ready_bundle() -> WaveFourCrossDomainTransferBundle:
    return WaveFourCrossDomainTransferBundle(
        bundle_id="transfer-bundle-001",
        evaluations=(
            evaluation(),
            evaluation(
                "transfer-evaluation-assurance",
                source_domain="Assurance-case review governance",
                target_pairs=(
                    ("target-safe-refusal", "Safe-refusal review"),
                    ("target-reward-audit", "Reward-audit review"),
                ),
                blackfox_receipts=("blackfox:receipt-assurance",),
            ),
        ),
        failure_cases=(
            failure_case(),
            failure_case(
                "failure-missing-evidence",
                target_id="target-memory-quarantine",
                repair_recommendation=(
                    "Reject transfer until evidence ids are restored."
                ),
            ),
        ),
        required_source_domains=(
            "AI-assisted code repair governance",
            "Assurance-case review governance",
        ),
        required_target_domains=(
            "WorldTwin consequence scenario review",
            "Memory quarantine review",
            "Safe-refusal review",
            "Reward-audit review",
        ),
        min_ready_evaluations=2,
        notes=("Transfer bundle requires human review and no AGI claim.",),
    )


def test_transfer_failure_case_requires_evidence_and_repair_when_detected() -> None:
    with pytest.raises(ValueError, match="failure cases require evidence ids"):
        WaveFourTransferFailureCase(
            failure_case_id="failure-invalid",
            evaluation_id="transfer-evaluation-governance",
            target_id="target-worldtwin-scenario",
            failure_mode=WaveFourTransferFailureMode.MISSING_EVIDENCE_BINDING,
            violated_invariant="evidence ids remain attached",
            expected_detection_summary="Detect missing evidence binding.",
            evidence_ids=(),
            detected=True,
            repair_recommendation="Restore evidence binding.",
        )

    with pytest.raises(ValueError, match="require repair guidance"):
        failure_case(repair_recommendation="")


def test_detected_transfer_failure_case_is_resolved_negative_control() -> None:
    item = failure_case()

    assert item.resolved is True
    assert item.readiness_gap == ""
    assert len(item.fingerprint()) == 64


def test_undetected_failure_case_reports_repair_gap() -> None:
    item = failure_case(
        "failure-undetected-authority",
        detected=False,
        repair_recommendation="",
    )

    assert item.resolved is False
    assert item.readiness_gap == (
        "failure-undetected-authority was not detected by transfer review"
    )


def test_transfer_bundle_requires_evaluations_and_positive_ready_count() -> None:
    with pytest.raises(ValueError, match="require evaluations"):
        WaveFourCrossDomainTransferBundle(
            bundle_id="invalid-bundle",
            evaluations=(),
            failure_cases=(),
            required_source_domains=(),
            required_target_domains=(),
        )

    with pytest.raises(ValueError, match="positive ready count"):
        WaveFourCrossDomainTransferBundle(
            bundle_id="invalid-bundle",
            evaluations=(evaluation(),),
            failure_cases=(),
            required_source_domains=(),
            required_target_domains=(),
            min_ready_evaluations=0,
        )


def test_transfer_bundle_rejects_duplicate_evaluation_ids() -> None:
    item = evaluation()

    with pytest.raises(ValueError, match="Duplicate evaluation_id"):
        WaveFourCrossDomainTransferBundle(
            bundle_id="invalid-bundle",
            evaluations=(item, item),
            failure_cases=(),
            required_source_domains=(),
            required_target_domains=(),
        )


def test_transfer_bundle_rejects_failure_case_for_unknown_evaluation() -> None:
    with pytest.raises(ValueError, match="reference bundled evaluations"):
        WaveFourCrossDomainTransferBundle(
            bundle_id="invalid-bundle",
            evaluations=(evaluation(),),
            failure_cases=(failure_case(evaluation_id="missing-evaluation"),),
            required_source_domains=(),
            required_target_domains=(),
        )


def test_transfer_bundle_rejects_failure_case_for_unknown_target() -> None:
    with pytest.raises(ValueError, match="reference target ids from their evaluation"):
        WaveFourCrossDomainTransferBundle(
            bundle_id="invalid-bundle",
            evaluations=(evaluation(),),
            failure_cases=(failure_case(target_id="missing-target"),),
            required_source_domains=(),
            required_target_domains=(),
        )


def test_ready_transfer_bundle_has_required_coverage_and_negative_controls() -> None:
    bundle = ready_bundle()

    assert bundle.status is WaveFourTransferStatus.READY_FOR_CONTROLLED_REVIEW
    assert bundle.ready_for_controlled_review is True
    assert bundle.ready_evaluation_ids == (
        "transfer-evaluation-assurance",
        "transfer-evaluation-governance",
    )
    assert bundle.detected_failure_case_ids == (
        "failure-hidden-authority",
        "failure-missing-evidence",
    )
    assert bundle.unresolved_failure_case_ids == ()
    assert bundle.missing_required_source_domains == ()
    assert bundle.missing_required_target_domains == ()
    assert bundle.readiness_gaps == ()
    assert bundle.claims_agi is False
    assert bundle.permits_automatic_execution is False
    assert "no AGI claim" in bundle.review_summary


def test_transfer_bundle_reports_missing_required_domains() -> None:
    bundle = WaveFourCrossDomainTransferBundle(
        bundle_id="bundle-missing-domain",
        evaluations=(evaluation(),),
        failure_cases=(),
        required_source_domains=(
            "AI-assisted code repair governance",
            "Scientific-loop review governance",
        ),
        required_target_domains=(
            "WorldTwin consequence scenario review",
            "Safe-refusal review",
        ),
    )

    assert bundle.status is WaveFourTransferStatus.NEEDS_EVIDENCE
    assert bundle.missing_required_source_domains == (
        "Scientific-loop review governance",
    )
    assert bundle.missing_required_target_domains == ("Safe-refusal review",)
    assert "missing required source domains" in bundle.readiness_gaps[0]


def test_transfer_bundle_needs_repair_for_unresolved_negative_control() -> None:
    bundle = WaveFourCrossDomainTransferBundle(
        bundle_id="bundle-unresolved-failure",
        evaluations=(evaluation(),),
        failure_cases=(
            failure_case(
                "failure-undetected-authority",
                detected=False,
                repair_recommendation="",
            ),
        ),
        required_source_domains=("AI-assisted code repair governance",),
        required_target_domains=("WorldTwin consequence scenario review",),
    )

    assert bundle.status is WaveFourTransferStatus.NEEDS_REPAIR
    assert bundle.unresolved_failure_case_ids == ("failure-undetected-authority",)
    assert (
        "failure-undetected-authority was not detected by transfer review"
        in bundle.readiness_gaps
    )


def test_transfer_bundle_needs_repair_when_evaluation_has_failed_observation() -> None:
    failed_observation = WaveFourTransferObservation(
        observation_id="observation-failed",
        target_id="target-worldtwin-scenario",
        observed_behavior="The transfer treated analogy as approval.",
        matched_invariant_conditions=("model output remains untrusted",),
        violated_invariant_conditions=("human review authority remains explicit",),
        evidence_ids=("evidence:observation-failed",),
        passed=False,
    )
    failed_evaluation = WaveFourCrossDomainTransferEvaluation(
        evaluation_id="transfer-evaluation-governance",
        source_rule=transfer_rule(),
        targets=(
            target(
                "target-worldtwin-scenario",
                "WorldTwin consequence scenario review",
            ),
        ),
        observations=(failed_observation,),
        blackfox_receipt_ids=("blackfox:receipt-transfer",),
    )
    bundle = WaveFourCrossDomainTransferBundle(
        bundle_id="bundle-failed-observation",
        evaluations=(failed_evaluation,),
        failure_cases=(),
        required_source_domains=("AI-assisted code repair governance",),
        required_target_domains=("WorldTwin consequence scenario review",),
    )

    assert bundle.status is WaveFourTransferStatus.NEEDS_REPAIR
    assert bundle.repair_evaluation_ids == ("transfer-evaluation-governance",)
    assert "failed observations: observation-failed" in bundle.readiness_gaps[-1]


def test_transfer_bundle_blocks_when_evaluation_is_blocked() -> None:
    blocked = WaveFourCrossDomainTransferEvaluation(
        evaluation_id="transfer-evaluation-governance",
        source_rule=transfer_rule(),
        targets=(
            target(
                "target-worldtwin-scenario",
                "WorldTwin consequence scenario review",
            ),
        ),
        observations=(),
        blackfox_receipt_ids=("blackfox:receipt-transfer",),
        blocked_reasons=("source rule evidence contradicted",),
    )
    bundle = WaveFourCrossDomainTransferBundle(
        bundle_id="bundle-blocked",
        evaluations=(blocked,),
        failure_cases=(),
        required_source_domains=("AI-assisted code repair governance",),
        required_target_domains=("WorldTwin consequence scenario review",),
    )

    assert bundle.status is WaveFourTransferStatus.BLOCKED
    assert bundle.blocked_evaluation_ids == ("transfer-evaluation-governance",)
    assert "source rule evidence contradicted" in bundle.readiness_gaps[-1]


def test_transfer_bundle_rejects_execution_agi_and_independent_validation() -> None:
    with pytest.raises(ValueError, match="cannot permit execution"):
        WaveFourCrossDomainTransferBundle(
            bundle_id="invalid-execution",
            evaluations=(evaluation(),),
            failure_cases=(),
            required_source_domains=(),
            required_target_domains=(),
            permits_automatic_execution=True,
        )

    with pytest.raises(ValueError, match="cannot claim AGI"):
        WaveFourCrossDomainTransferBundle(
            bundle_id="invalid-agi",
            evaluations=(evaluation(),),
            failure_cases=(),
            required_source_domains=(),
            required_target_domains=(),
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="cannot claim independent validation"):
        WaveFourCrossDomainTransferBundle(
            bundle_id="invalid-independent-validation",
            evaluations=(evaluation(),),
            failure_cases=(),
            required_source_domains=(),
            required_target_domains=(),
            independently_validated=True,
        )


def test_transfer_bundle_converts_to_trial_protocol() -> None:
    protocol = ready_bundle().to_trial_protocol()

    assert protocol.status is WaveFourTrialStatus.READY_FOR_CONTROLLED_REVIEW
    assert protocol.ready_for_controlled_review is True
    assert protocol.task_ids == (
        "transfer:transfer-evaluation-assurance",
        "transfer:transfer-evaluation-governance",
    )
    assert protocol.required_task_kinds == (
        WaveFourTrialTaskKind.CROSS_DOMAIN_TRANSFER_PROBE,
    )


def test_transfer_bundle_converts_to_shared_artifact_bundle() -> None:
    bundle = ready_bundle().to_artifact_bundle()

    assert bundle.has_required_kind_coverage is True
    assert bundle.has_required_capability_coverage is True
    assert len(bundle.artifacts) == 2
    assert {artifact.kind for artifact in bundle.artifacts} == {
        WaveFourArtifactKind.TRANSFER_EVALUATION
    }
    assert {artifact.capability_area for artifact in bundle.artifacts} == {
        WaveFourCapabilityArea.CROSS_DOMAIN_TRANSFER
    }
    assert len(bundle.ready_for_controlled_review_artifact_ids) == 2
    failure_links = tuple(
        link
        for link in bundle.evidence_links
        if link.evidence_id.startswith("evidence:failure")
    )
    assert len(failure_links) == 2
    assert {link.relation for link in failure_links} == {WaveFourEvidenceRelation.TESTS}


def test_transfer_bundle_fingerprint_is_deterministic_despite_input_order() -> None:
    first = ready_bundle()
    second = WaveFourCrossDomainTransferBundle(
        bundle_id="transfer-bundle-001",
        evaluations=tuple(reversed(first.evaluations)),
        failure_cases=tuple(reversed(first.failure_cases)),
        required_source_domains=first.required_source_domains,
        required_target_domains=first.required_target_domains,
        min_ready_evaluations=2,
        notes=("Transfer bundle requires human review and no AGI claim.",),
    )

    assert first.evaluation_ids == second.evaluation_ids
    assert first.fingerprint() == second.fingerprint()
    assert len(first.fingerprint()) == 64
