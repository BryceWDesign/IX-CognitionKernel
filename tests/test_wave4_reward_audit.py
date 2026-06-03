import pytest

from ix_cognition_kernel.wave4_contracts import (
    WaveFourArtifactKind,
    WaveFourCapabilityArea,
)
from ix_cognition_kernel.wave4_reward_audit import (
    REQUIRED_WAVE_FOUR_REWARD_RISK_KINDS,
    WaveFourRewardAuditFinding,
    WaveFourRewardAuditOutcome,
    WaveFourRewardAuditStatus,
    WaveFourRewardFindingSeverity,
    WaveFourRewardHackingAudit,
    WaveFourRewardMetricDefinition,
    WaveFourRewardNegativeControl,
    WaveFourRewardRiskKind,
    detected_reward_control,
    reward_metric,
)
from ix_cognition_kernel.wave4_trials import (
    WaveFourTrialOutcome,
    WaveFourTrialStatus,
    WaveFourTrialTaskKind,
)


def metric(
    metric_id: str = "metric:evidence-coverage",
) -> WaveFourRewardMetricDefinition:
    return reward_metric(
        metric_id=metric_id,
        metric_name="Evidence coverage score",
        objective="Improve review evidence without hiding failed checks.",
        mission_boundary="Human review required; no automatic execution.",
        target_behavior="Higher score means more visible verified evidence.",
        evidence_id=f"evidence:{metric_id}",
    )


def control(
    control_id: str = "control:hidden-failure",
    *,
    metric_id: str = "metric:evidence-coverage",
    detected: bool = True,
    repair_guidance: str = "Keep failed checks visible in the audit output.",
) -> WaveFourRewardNegativeControl:
    return WaveFourRewardNegativeControl(
        control_id=control_id,
        metric_id=metric_id,
        risk_kind=WaveFourRewardRiskKind.HIDDEN_FAILURE_SUPPRESSION,
        injected_behavior="The score was raised by omitting a failed check.",
        expected_detection="Detect hidden failure suppression before review.",
        evidence_ids=(f"evidence:{control_id}",),
        detected=detected,
        repair_guidance=repair_guidance,
    )


def finding(
    finding_id: str = "finding:metric-over-mission",
    *,
    severity: WaveFourRewardFindingSeverity = WaveFourRewardFindingSeverity.MEDIUM,
    blocks_progress: bool = False,
) -> WaveFourRewardAuditFinding:
    return WaveFourRewardAuditFinding(
        finding_id=finding_id,
        metric_id="metric:evidence-coverage",
        risk_kind=WaveFourRewardRiskKind.METRIC_OVER_MISSION,
        severity=severity,
        description="The metric can rise while rollback evidence remains weak.",
        observed_gaming_behavior="Rollback evidence was omitted from scoring.",
        evidence_ids=(f"evidence:{finding_id}",),
        repair_recommendation="Require rollback evidence in the score.",
        blocks_progress=blocks_progress,
    )


def ready_audit() -> WaveFourRewardHackingAudit:
    return WaveFourRewardHackingAudit(
        audit_id="reward-audit-001",
        metrics=(
            metric(),
            metric("metric:authority-preservation"),
        ),
        evaluated_risk_kinds=REQUIRED_WAVE_FOUR_REWARD_RISK_KINDS,
        findings=(),
        negative_controls=(
            control(),
            detected_reward_control(
                control_id="control:authority-bypass",
                metric_id="metric:authority-preservation",
                risk_kind=WaveFourRewardRiskKind.HUMAN_AUTHORITY_BYPASS,
                injected_behavior="The score ignored missing human authority.",
                expected_detection="Detect authority bypass in metric scoring.",
                evidence_id="evidence:control:authority-bypass",
                repair_guidance="Require human-authority state in the metric.",
            ),
        ),
        scenario_ids=("worldtwin:reward-gaming-scenario",),
        blackfox_receipt_ids=("blackfox:reward-audit-receipt",),
    )


def test_required_reward_risk_kinds_are_locked() -> None:
    assert REQUIRED_WAVE_FOUR_REWARD_RISK_KINDS == (
        WaveFourRewardRiskKind.OBJECTIVE_MISMATCH,
        WaveFourRewardRiskKind.SPECIFICATION_GAMING,
        WaveFourRewardRiskKind.REWARD_HACKING,
        WaveFourRewardRiskKind.METRIC_OVER_MISSION,
        WaveFourRewardRiskKind.EVALUATION_GAMING,
        WaveFourRewardRiskKind.HIDDEN_FAILURE_SUPPRESSION,
        WaveFourRewardRiskKind.HUMAN_AUTHORITY_BYPASS,
    )


def test_reward_metric_requires_prohibited_optimizations_and_evidence() -> None:
    with pytest.raises(ValueError, match="require prohibited optimizations"):
        reward_metric(
            metric_id="metric:invalid",
            metric_name="Invalid metric",
            objective="Invalid objective.",
            mission_boundary="Human review required.",
            target_behavior="Invalid target.",
            prohibited_optimizations=(),
            evidence_id="evidence:metric-invalid",
        )

    with pytest.raises(ValueError, match="reward metrics require evidence ids"):
        WaveFourRewardMetricDefinition(
            metric_id="metric:invalid",
            metric_name="Invalid metric",
            objective="Invalid objective.",
            mission_boundary="Human review required.",
            target_behavior="Invalid target.",
            prohibited_optimizations=("hide failed checks",),
            evidence_ids=(),
        )


def test_reward_finding_requires_evidence_repair_and_high_severity_blocking() -> None:
    with pytest.raises(ValueError, match="reward findings require evidence ids"):
        WaveFourRewardAuditFinding(
            finding_id="finding:invalid",
            metric_id="metric:evidence-coverage",
            risk_kind=WaveFourRewardRiskKind.REWARD_HACKING,
            severity=WaveFourRewardFindingSeverity.LOW,
            description="Finding without evidence.",
            observed_gaming_behavior="Score rose without evidence.",
            evidence_ids=(),
            repair_recommendation="Add evidence.",
        )

    with pytest.raises(ValueError, match="must block"):
        finding(
            "finding:critical",
            severity=WaveFourRewardFindingSeverity.CRITICAL,
            blocks_progress=False,
        )


def test_negative_control_requires_evidence_and_guidance_when_detected() -> None:
    with pytest.raises(ValueError, match="negative controls require evidence ids"):
        WaveFourRewardNegativeControl(
            control_id="control:invalid",
            metric_id="metric:evidence-coverage",
            risk_kind=WaveFourRewardRiskKind.REWARD_HACKING,
            injected_behavior="Invalid missing evidence.",
            expected_detection="Detect invalid control.",
            evidence_ids=(),
            detected=True,
            repair_guidance="Repair invalid control.",
        )

    with pytest.raises(ValueError, match="require repair guidance"):
        control("control:no-guidance", repair_guidance="")


def test_ready_reward_audit_confirms_negative_controls_without_overclaim() -> None:
    audit = ready_audit()

    assert audit.status is WaveFourRewardAuditStatus.READY_FOR_CONTROLLED_REVIEW
    assert audit.outcome is WaveFourRewardAuditOutcome.REWARD_GAMING_NOT_DETECTED
    assert audit.ready_for_controlled_review is True
    assert audit.missing_required_risk_kinds == ()
    assert audit.blocking_gaps == ()
    assert audit.readiness_gaps == ()
    assert audit.permits_automatic_execution is False
    assert audit.claims_agi is False
    assert "no AGI claim" in audit.review_summary


def test_reward_audit_reports_missing_risk_coverage_controls_and_receipts() -> None:
    audit = WaveFourRewardHackingAudit(
        audit_id="reward-audit-gaps",
        metrics=(metric(),),
        evaluated_risk_kinds=(WaveFourRewardRiskKind.OBJECTIVE_MISMATCH,),
        findings=(),
        negative_controls=(),
        scenario_ids=(),
        blackfox_receipt_ids=(),
    )

    assert audit.status is WaveFourRewardAuditStatus.NEEDS_EVIDENCE
    assert audit.outcome is WaveFourRewardAuditOutcome.NEEDS_EVIDENCE
    assert audit.missing_required_risk_kinds == (
        WaveFourRewardRiskKind.SPECIFICATION_GAMING,
        WaveFourRewardRiskKind.REWARD_HACKING,
        WaveFourRewardRiskKind.METRIC_OVER_MISSION,
        WaveFourRewardRiskKind.EVALUATION_GAMING,
        WaveFourRewardRiskKind.HIDDEN_FAILURE_SUPPRESSION,
        WaveFourRewardRiskKind.HUMAN_AUTHORITY_BYPASS,
    )
    assert "missing reward-risk coverage" in audit.readiness_gaps[0]
    assert "reward-audit-gaps has no reward-gaming negative controls" in (
        audit.readiness_gaps
    )
    assert "reward-audit-gaps has no WorldTwin scenario ids" in audit.readiness_gaps
    assert "reward-audit-gaps has no BlackFox receipt ids" in audit.readiness_gaps


def test_unresolved_negative_control_needs_repair() -> None:
    audit = WaveFourRewardHackingAudit(
        audit_id="reward-audit-unresolved-control",
        metrics=(metric(),),
        evaluated_risk_kinds=REQUIRED_WAVE_FOUR_REWARD_RISK_KINDS,
        findings=(),
        negative_controls=(
            control(
                "control:undetected",
                detected=False,
                repair_guidance="",
            ),
        ),
        scenario_ids=("worldtwin:reward-gaming-scenario",),
        blackfox_receipt_ids=("blackfox:reward-audit-receipt",),
    )

    assert audit.status is WaveFourRewardAuditStatus.NEEDS_REPAIR
    assert audit.outcome is WaveFourRewardAuditOutcome.REWARD_GAMING_DETECTED
    assert audit.unresolved_negative_control_ids == ("control:undetected",)
    assert "control:undetected was not detected" in audit.readiness_gaps[0]


def test_non_blocking_finding_needs_repair() -> None:
    audit = WaveFourRewardHackingAudit(
        audit_id="reward-audit-finding",
        metrics=(metric(),),
        evaluated_risk_kinds=REQUIRED_WAVE_FOUR_REWARD_RISK_KINDS,
        findings=(finding(),),
        negative_controls=(control(),),
        scenario_ids=("worldtwin:reward-gaming-scenario",),
        blackfox_receipt_ids=("blackfox:reward-audit-receipt",),
    )

    assert audit.status is WaveFourRewardAuditStatus.NEEDS_REPAIR
    assert audit.repair_finding_ids == ("finding:metric-over-mission",)
    assert "reward findings need repair" in audit.readiness_gaps[0]


def test_blocking_finding_blocks_reward_audit() -> None:
    audit = WaveFourRewardHackingAudit(
        audit_id="reward-audit-blocked-finding",
        metrics=(metric(),),
        evaluated_risk_kinds=REQUIRED_WAVE_FOUR_REWARD_RISK_KINDS,
        findings=(
            finding(
                "finding:critical",
                severity=WaveFourRewardFindingSeverity.CRITICAL,
                blocks_progress=True,
            ),
        ),
        negative_controls=(control(),),
        scenario_ids=("worldtwin:reward-gaming-scenario",),
        blackfox_receipt_ids=("blackfox:reward-audit-receipt",),
    )

    assert audit.status is WaveFourRewardAuditStatus.BLOCKED
    assert audit.outcome is WaveFourRewardAuditOutcome.BLOCKED
    assert audit.blocking_finding_ids == ("finding:critical",)
    assert "reward finding blocks progress" in audit.blocking_gaps[0]


def test_reward_audit_rejects_duplicate_metrics_and_unknown_references() -> None:
    item = metric()
    with pytest.raises(ValueError, match="Duplicate metric_id"):
        WaveFourRewardHackingAudit(
            audit_id="invalid-duplicates",
            metrics=(item, item),
            evaluated_risk_kinds=REQUIRED_WAVE_FOUR_REWARD_RISK_KINDS,
            findings=(),
            negative_controls=(),
            scenario_ids=(),
            blackfox_receipt_ids=(),
        )

    bad_finding = WaveFourRewardAuditFinding(
        finding_id="finding:unknown-metric",
        metric_id="metric:missing",
        risk_kind=WaveFourRewardRiskKind.REWARD_HACKING,
        severity=WaveFourRewardFindingSeverity.LOW,
        description="Finding references missing metric.",
        observed_gaming_behavior="Metric reference is invalid.",
        evidence_ids=("evidence:finding:unknown-metric",),
        repair_recommendation="Use a real metric id.",
    )
    with pytest.raises(ValueError, match="findings must reference audited metrics"):
        WaveFourRewardHackingAudit(
            audit_id="invalid-finding-reference",
            metrics=(metric(),),
            evaluated_risk_kinds=REQUIRED_WAVE_FOUR_REWARD_RISK_KINDS,
            findings=(bad_finding,),
            negative_controls=(),
            scenario_ids=(),
            blackfox_receipt_ids=(),
        )

    bad_control = control("control:bad-reference", metric_id="metric:missing")
    with pytest.raises(ValueError, match="controls must reference audited metrics"):
        WaveFourRewardHackingAudit(
            audit_id="invalid-control-reference",
            metrics=(metric(),),
            evaluated_risk_kinds=REQUIRED_WAVE_FOUR_REWARD_RISK_KINDS,
            findings=(),
            negative_controls=(bad_control,),
            scenario_ids=(),
            blackfox_receipt_ids=(),
        )


def test_blocked_reward_audit_cannot_carry_results() -> None:
    with pytest.raises(ValueError, match="cannot carry results"):
        WaveFourRewardHackingAudit(
            audit_id="blocked-invalid",
            metrics=(metric(),),
            evaluated_risk_kinds=REQUIRED_WAVE_FOUR_REWARD_RISK_KINDS,
            findings=(),
            negative_controls=(control(),),
            scenario_ids=("worldtwin:reward-gaming-scenario",),
            blackfox_receipt_ids=("blackfox:reward-audit-receipt",),
            blocked_reasons=("metric source evidence was contradicted",),
        )

    audit = WaveFourRewardHackingAudit(
        audit_id="blocked-audit",
        metrics=(metric(),),
        evaluated_risk_kinds=REQUIRED_WAVE_FOUR_REWARD_RISK_KINDS,
        findings=(),
        negative_controls=(),
        scenario_ids=("worldtwin:reward-gaming-scenario",),
        blackfox_receipt_ids=("blackfox:reward-audit-receipt",),
        blocked_reasons=("metric source evidence was contradicted",),
    )

    assert audit.status is WaveFourRewardAuditStatus.BLOCKED
    assert audit.blocking_gaps == (
        "blocked-audit blocked: metric source evidence was contradicted",
    )


def test_reward_audit_rejects_execution_agi_and_independent_validation() -> None:
    with pytest.raises(ValueError, match="cannot permit execution"):
        WaveFourRewardHackingAudit(
            audit_id="invalid-execution",
            metrics=(metric(),),
            evaluated_risk_kinds=REQUIRED_WAVE_FOUR_REWARD_RISK_KINDS,
            findings=(),
            negative_controls=(),
            scenario_ids=(),
            blackfox_receipt_ids=(),
            permits_automatic_execution=True,
        )

    with pytest.raises(ValueError, match="cannot claim AGI"):
        WaveFourRewardHackingAudit(
            audit_id="invalid-agi",
            metrics=(metric(),),
            evaluated_risk_kinds=REQUIRED_WAVE_FOUR_REWARD_RISK_KINDS,
            findings=(),
            negative_controls=(),
            scenario_ids=(),
            blackfox_receipt_ids=(),
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="cannot claim independent validation"):
        WaveFourRewardHackingAudit(
            audit_id="invalid-independent-validation",
            metrics=(metric(),),
            evaluated_risk_kinds=REQUIRED_WAVE_FOUR_REWARD_RISK_KINDS,
            findings=(),
            negative_controls=(),
            scenario_ids=(),
            blackfox_receipt_ids=(),
            independently_validated=True,
        )


def test_reward_audit_converts_to_shared_artifact_and_bundle() -> None:
    audit = ready_audit()
    artifact = audit.to_artifact_ref()
    bundle = audit.to_artifact_bundle()

    assert artifact.kind is WaveFourArtifactKind.REWARD_HACKING_AUDIT
    assert artifact.capability_area is WaveFourCapabilityArea.REWARD_HACKING_DETECTION
    assert artifact.ready_for_controlled_review is True
    assert artifact.allowed_for_automatic_execution is False
    assert artifact.claims_agi is False
    assert len(audit.evidence_links()) == 4
    assert bundle.has_required_kind_coverage is True
    assert bundle.has_required_capability_coverage is True
    assert bundle.ready_for_controlled_review_artifact_ids == (artifact.artifact_id,)


def test_reward_audit_converts_to_controlled_trial_task() -> None:
    task = ready_audit().to_controlled_task()

    assert task.task_kind is WaveFourTrialTaskKind.REWARD_HACKING_PROBE
    assert task.outcome is WaveFourTrialOutcome.PASSED
    assert task.status is WaveFourTrialStatus.READY_FOR_CONTROLLED_REVIEW
    assert task.ready_for_controlled_review is True
    assert task.scenario_ids == ("worldtwin:reward-gaming-scenario",)
    assert task.blackfox_receipt_ids == ("blackfox:reward-audit-receipt",)
    assert len(task.measurements) == 2


def test_failed_reward_audit_converts_to_failed_trial_task() -> None:
    audit = WaveFourRewardHackingAudit(
        audit_id="reward-audit-unresolved-control",
        metrics=(metric(),),
        evaluated_risk_kinds=REQUIRED_WAVE_FOUR_REWARD_RISK_KINDS,
        findings=(),
        negative_controls=(
            control(
                "control:undetected",
                detected=False,
                repair_guidance="",
            ),
        ),
        scenario_ids=("worldtwin:reward-gaming-scenario",),
        blackfox_receipt_ids=("blackfox:reward-audit-receipt",),
    )
    task = audit.to_controlled_task()

    assert task.outcome is WaveFourTrialOutcome.FAILED
    assert task.status is WaveFourTrialStatus.NEEDS_REPAIR
    assert task.failed_measurement_ids == ("reward-control:control:undetected",)


def test_reward_audit_fingerprint_is_deterministic_despite_input_order() -> None:
    first = ready_audit()
    second = WaveFourRewardHackingAudit(
        audit_id="reward-audit-001",
        metrics=tuple(reversed(first.metrics)),
        evaluated_risk_kinds=REQUIRED_WAVE_FOUR_REWARD_RISK_KINDS,
        findings=(),
        negative_controls=tuple(reversed(first.negative_controls)),
        scenario_ids=("worldtwin:reward-gaming-scenario",),
        blackfox_receipt_ids=("blackfox:reward-audit-receipt",),
    )

    assert first.metric_ids == second.metric_ids
    assert first.fingerprint() == second.fingerprint()
    assert len(first.fingerprint()) == 64
