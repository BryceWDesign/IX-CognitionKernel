import pytest

from ix_cognition_kernel.wave3_contracts import (
    WaveThreeArtifactKind,
    WaveThreeAuthorityState,
)
from ix_cognition_kernel.wave3_reward_audit import (
    REQUIRED_REWARD_RISK_KINDS,
    RewardAuditFinding,
    RewardAuditRecord,
    RewardAuditStatus,
    RewardFindingSeverity,
    RewardRiskKind,
    clean_reward_audit_record,
)


def clean_record() -> RewardAuditRecord:
    return clean_reward_audit_record(
        audit_id="reward-audit-001",
        objective="Improve plan quality without bypassing human authority.",
        metric="Verified evidence coverage score.",
        mission_boundary="No automatic execution, no hidden uncertainty, no AGI claim.",
        evidence_ids=("evidence:reward-audit",),
    )


def medium_finding() -> RewardAuditFinding:
    return RewardAuditFinding(
        finding_id="finding-metric-narrowness",
        risk_kind=RewardRiskKind.METRIC_OVER_MISSION,
        severity=RewardFindingSeverity.MEDIUM,
        description="Metric can improve while rollback evidence remains weak.",
        affected_metric="Verified evidence coverage score.",
        evidence_ids=("evidence:metric-narrowness",),
        repair_recommendation=(
            "Add rollback evidence coverage as a required component of the metric."
        ),
    )


def blocking_finding() -> RewardAuditFinding:
    return RewardAuditFinding(
        finding_id="finding-spec-gaming",
        risk_kind=RewardRiskKind.SPECIFICATION_GAMING,
        severity=RewardFindingSeverity.HIGH,
        description="The score can be raised by hiding failed checks from the summary.",
        affected_metric="Verified evidence coverage score.",
        evidence_ids=("evidence:spec-gaming",),
        repair_recommendation=(
            "Require failed checks to remain visible in evidence output."
        ),
        blocks_progress=True,
    )


def test_required_reward_risk_kinds_are_locked() -> None:
    assert REQUIRED_REWARD_RISK_KINDS == (
        RewardRiskKind.OBJECTIVE_MISMATCH,
        RewardRiskKind.SPECIFICATION_GAMING,
        RewardRiskKind.REWARD_HACKING,
        RewardRiskKind.METRIC_OVER_MISSION,
        RewardRiskKind.EVALUATION_GAMING,
    )


def test_clean_reward_audit_is_reviewable_not_executable() -> None:
    record = clean_record()

    assert record.status is RewardAuditStatus.READY_FOR_HUMAN_REVIEW
    assert record.ready_for_human_review is True
    assert record.permits_automatic_execution is False
    assert record.human_authority_state is WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
    assert record.missing_required_risk_kinds == ()
    assert record.readiness_gaps == ()
    assert record.blocking_gaps == ()
    assert "automatic execution is not permitted" in record.review_summary


def test_reward_audit_rejects_empty_objective_metric_or_boundary() -> None:
    with pytest.raises(ValueError, match="objective must not be empty"):
        clean_reward_audit_record(
            audit_id="reward-audit-001",
            objective=" ",
            metric="Evidence coverage.",
            mission_boundary="Human review required.",
            evidence_ids=("evidence",),
        )

    with pytest.raises(ValueError, match="metric must not be empty"):
        clean_reward_audit_record(
            audit_id="reward-audit-001",
            objective="Improve plan quality.",
            metric=" ",
            mission_boundary="Human review required.",
            evidence_ids=("evidence",),
        )

    with pytest.raises(ValueError, match="mission_boundary must not be empty"):
        clean_reward_audit_record(
            audit_id="reward-audit-001",
            objective="Improve plan quality.",
            metric="Evidence coverage.",
            mission_boundary=" ",
            evidence_ids=("evidence",),
        )


def test_reward_audit_reports_missing_risk_coverage_and_evidence() -> None:
    record = RewardAuditRecord(
        audit_id="reward-audit-001",
        objective="Improve plan quality.",
        metric="Evidence coverage.",
        mission_boundary="Human review required.",
        evaluated_risk_kinds=(RewardRiskKind.OBJECTIVE_MISMATCH,),
        evidence_ids=(),
    )

    assert record.status is RewardAuditStatus.NEEDS_EVIDENCE
    assert record.ready_for_human_review is False
    assert record.missing_required_risk_kinds == (
        RewardRiskKind.SPECIFICATION_GAMING,
        RewardRiskKind.REWARD_HACKING,
        RewardRiskKind.METRIC_OVER_MISSION,
        RewardRiskKind.EVALUATION_GAMING,
    )
    assert "reward audit has no top-level evidence ids" in record.readiness_gaps


def test_reward_finding_requires_evidence_and_repair_recommendation() -> None:
    with pytest.raises(ValueError, match="finding evidence_id must not be empty"):
        RewardAuditFinding(
            finding_id="finding-001",
            risk_kind=RewardRiskKind.REWARD_HACKING,
            severity=RewardFindingSeverity.LOW,
            description="Finding without evidence should fail closed.",
            affected_metric="Score.",
            evidence_ids=(" ",),
            repair_recommendation="Add evidence.",
        )

    with pytest.raises(ValueError, match="repair_recommendation must not be empty"):
        RewardAuditFinding(
            finding_id="finding-001",
            risk_kind=RewardRiskKind.REWARD_HACKING,
            severity=RewardFindingSeverity.LOW,
            description="Finding without repair should fail closed.",
            affected_metric="Score.",
            evidence_ids=("evidence",),
            repair_recommendation=" ",
        )


def test_high_and_critical_findings_must_block_progress() -> None:
    with pytest.raises(ValueError, match="must block progress"):
        RewardAuditFinding(
            finding_id="finding-high-risk",
            risk_kind=RewardRiskKind.SPECIFICATION_GAMING,
            severity=RewardFindingSeverity.HIGH,
            description="High severity spec-gaming risk must block.",
            affected_metric="Evidence coverage score.",
            evidence_ids=("evidence:spec-gaming",),
            repair_recommendation="Patch the metric before review.",
        )


def test_non_blocking_findings_need_repair_before_readiness() -> None:
    record = RewardAuditRecord(
        audit_id="reward-audit-001",
        objective="Improve plan quality without bypassing human authority.",
        metric="Verified evidence coverage score.",
        mission_boundary="No automatic execution.",
        evaluated_risk_kinds=REQUIRED_REWARD_RISK_KINDS,
        evidence_ids=("evidence:reward-audit",),
        findings=(medium_finding(),),
    )

    assert record.status is RewardAuditStatus.NEEDS_REPAIR
    assert record.ready_for_human_review is False
    assert record.non_blocking_findings == (medium_finding(),)
    assert record.repair_recommendations == (
        "Add rollback evidence coverage as a required component of the metric.",
    )
    assert (
        "reward findings need repair: finding-metric-narrowness"
        in record.readiness_gaps
    )


def test_blocking_findings_block_reward_audit() -> None:
    record = RewardAuditRecord(
        audit_id="reward-audit-001",
        objective="Improve plan quality without bypassing human authority.",
        metric="Verified evidence coverage score.",
        mission_boundary="No automatic execution.",
        evaluated_risk_kinds=REQUIRED_REWARD_RISK_KINDS,
        evidence_ids=("evidence:reward-audit",),
        findings=(blocking_finding(),),
    )

    assert record.status is RewardAuditStatus.BLOCKED
    assert record.ready_for_human_review is False
    assert record.human_authority_state is WaveThreeAuthorityState.BLOCKED
    assert record.blocking_gaps == (
        "reward finding blocks progress: finding-spec-gaming (specification-gaming)",
    )


def test_reward_audit_rejects_duplicate_findings_and_duplicate_risk_coverage() -> None:
    finding = medium_finding()

    with pytest.raises(ValueError, match="Duplicate finding_id"):
        RewardAuditRecord(
            audit_id="reward-audit-001",
            objective="Improve plan quality.",
            metric="Evidence coverage.",
            mission_boundary="Human review required.",
            evaluated_risk_kinds=REQUIRED_REWARD_RISK_KINDS,
            evidence_ids=("evidence:reward-audit",),
            findings=(finding, finding),
        )

    with pytest.raises(ValueError, match="Duplicate evaluated risk kind"):
        RewardAuditRecord(
            audit_id="reward-audit-001",
            objective="Improve plan quality.",
            metric="Evidence coverage.",
            mission_boundary="Human review required.",
            evaluated_risk_kinds=(
                RewardRiskKind.OBJECTIVE_MISMATCH,
                RewardRiskKind.OBJECTIVE_MISMATCH,
            ),
            evidence_ids=("evidence:reward-audit",),
        )


def test_reward_audit_must_be_produced_by_reward_auditor_role() -> None:
    with pytest.raises(ValueError, match="must be produced by reward-auditor"):
        RewardAuditRecord(
            audit_id="reward-audit-001",
            objective="Improve plan quality.",
            metric="Evidence coverage.",
            mission_boundary="Human review required.",
            evaluated_risk_kinds=REQUIRED_REWARD_RISK_KINDS,
            evidence_ids=("evidence:reward-audit",),
            auditor_role_id="planner",
        )


def test_reward_audit_converts_to_shared_artifact_ref() -> None:
    artifact = clean_record().to_artifact_ref()

    assert artifact.artifact_id == "reward-audit:reward-audit-001"
    assert artifact.kind is WaveThreeArtifactKind.REWARD_AUDIT
    assert artifact.produced_by_engine_id == "reward-auditor"
    assert artifact.produced_by_agent_role_id == "reward-auditor"
    assert artifact.allowed_for_automatic_execution is False
    assert artifact.ready_for_human_review is True


def test_reward_audit_artifact_includes_finding_evidence() -> None:
    record = RewardAuditRecord(
        audit_id="reward-audit-001",
        objective="Improve plan quality without bypassing human authority.",
        metric="Verified evidence coverage score.",
        mission_boundary="No automatic execution.",
        evaluated_risk_kinds=REQUIRED_REWARD_RISK_KINDS,
        evidence_ids=("evidence:reward-audit",),
        findings=(blocking_finding(),),
    )
    artifact = record.to_artifact_ref()

    assert artifact.evidence_ids == (
        "evidence:reward-audit",
        "evidence:spec-gaming",
    )
    assert artifact.blocks_progress is True


def test_reward_audit_converts_to_shared_artifact_bundle() -> None:
    bundle = clean_record().to_artifact_bundle(
        artifact_bundle_id="reward-audit-artifacts"
    )

    assert bundle.has_required_kind_coverage is True
    assert bundle.artifact_ids == ("reward-audit:reward-audit-001",)
    assert bundle.ready_for_human_review_artifact_ids == (
        "reward-audit:reward-audit-001",
    )
    assert tuple(link.evidence_id for link in bundle.evidence_links) == (
        "evidence:reward-audit",
    )
    assert tuple(link.artifact_id for link in bundle.evidence_links) == (
        "reward-audit:reward-audit-001",
    )


def test_reward_audit_fingerprint_is_deterministic_despite_finding_order() -> None:
    first = RewardAuditRecord(
        audit_id="reward-audit-001",
        objective="Improve plan quality without bypassing human authority.",
        metric="Verified evidence coverage score.",
        mission_boundary="No automatic execution.",
        evaluated_risk_kinds=REQUIRED_REWARD_RISK_KINDS,
        evidence_ids=("evidence:reward-audit",),
        findings=(
            medium_finding(),
            blocking_finding(),
        ),
    )
    second = RewardAuditRecord(
        audit_id="reward-audit-001",
        objective="Improve plan quality without bypassing human authority.",
        metric="Verified evidence coverage score.",
        mission_boundary="No automatic execution.",
        evaluated_risk_kinds=REQUIRED_REWARD_RISK_KINDS,
        evidence_ids=("evidence:reward-audit",),
        findings=(
            blocking_finding(),
            medium_finding(),
        ),
    )

    assert first.fingerprint() == second.fingerprint()
    assert len(first.fingerprint()) == 64
