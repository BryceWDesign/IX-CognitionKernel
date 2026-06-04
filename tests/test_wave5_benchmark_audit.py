import pytest

from ix_cognition_kernel.wave5_benchmark_audit import (
    EXTERNAL_BENCHMARK_AUDIT_SOURCE_SYSTEMS,
    REQUIRED_WAVE_FIVE_BENCHMARK_CONTROLS,
    REQUIRED_WAVE_FIVE_BENCHMARK_RISKS,
    SAFE_WAVE_FIVE_BENCHMARK_RISK_DISPOSITIONS,
    WaveFiveBenchmarkAuditState,
    WaveFiveBenchmarkContaminationAudit,
    WaveFiveBenchmarkControl,
    WaveFiveBenchmarkControlKind,
    WaveFiveBenchmarkControlResult,
    WaveFiveBenchmarkProvenanceStatus,
    WaveFiveBenchmarkRiskDisposition,
    WaveFiveBenchmarkRiskFinding,
    WaveFiveBenchmarkRiskKind,
    WaveFiveBenchmarkSource,
    WaveFiveBenchmarkUse,
    external_benchmark_audit_source_systems,
    required_wave_five_benchmark_controls,
    required_wave_five_benchmark_risks,
    safe_wave_five_benchmark_risk_dispositions,
)
from ix_cognition_kernel.wave5_contracts import (
    WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES,
    WaveFiveArtifactDecision,
    WaveFiveArtifactKind,
    WaveFiveAuthorityState,
    WaveFiveCapabilityArea,
    WaveFiveClaimBoundary,
    WaveFiveSourceSystem,
    WaveFiveValidationStatus,
)


def source(
    benchmark_id: str = "benchmark-held-out-transfer",
    *,
    allowed_use: WaveFiveBenchmarkUse = WaveFiveBenchmarkUse.EXTERNAL_COMPARISON,
    provenance_status: WaveFiveBenchmarkProvenanceStatus = (
        WaveFiveBenchmarkProvenanceStatus.EXTERNAL_HELD_OUT
    ),
) -> WaveFiveBenchmarkSource:
    return WaveFiveBenchmarkSource(
        benchmark_id=benchmark_id,
        name="Held-out Wave 5 transfer comparison",
        allowed_use=allowed_use,
        provenance_status=provenance_status,
        scope_summary="Bounded evaluation source; not proof of general intelligence.",
        known_limitations=(
            "Benchmark coverage is narrower than Wave 6 generality.",
            "Scores cannot replace causal, safety, and authority evidence.",
        ),
        prohibited_claims=(
            "Do not claim AGI from benchmark performance.",
            "Do not claim independent validation from internal scoring.",
        ),
        evidence_ids=(f"evidence-{benchmark_id}",),
    )


def risk(
    finding_id: str = "risk-benchmark-memorization",
    *,
    benchmark_id: str = "benchmark-held-out-transfer",
    risk_kind: WaveFiveBenchmarkRiskKind = (
        WaveFiveBenchmarkRiskKind.BENCHMARK_MEMORIZATION
    ),
    disposition: WaveFiveBenchmarkRiskDisposition = (
        WaveFiveBenchmarkRiskDisposition.MITIGATED_WITH_EVIDENCE
    ),
    reviewer_ids: tuple[str, ...] = (),
) -> WaveFiveBenchmarkRiskFinding:
    return WaveFiveBenchmarkRiskFinding(
        finding_id=finding_id,
        benchmark_id=benchmark_id,
        risk_kind=risk_kind,
        disposition=disposition,
        risk_summary="Benchmark risk is explicitly checked before evidence use.",
        mitigation="Bound benchmark evidence and keep failure cases visible.",
        evidence_ids=(f"evidence-{finding_id}",),
        reviewer_ids=reviewer_ids,
    )


def control(
    control_id: str = "control-provenance-review",
    *,
    control_kind: WaveFiveBenchmarkControlKind = (
        WaveFiveBenchmarkControlKind.PROVENANCE_REVIEW
    ),
    result: WaveFiveBenchmarkControlResult = WaveFiveBenchmarkControlResult.PASSED,
    blocking: bool = True,
) -> WaveFiveBenchmarkControl:
    return WaveFiveBenchmarkControl(
        control_id=control_id,
        control_kind=control_kind,
        result=result,
        description="Anti-gaming control keeps benchmark evidence bounded.",
        evidence_ids=(f"evidence-{control_id}",),
        blocking=blocking,
    )


def required_risks() -> tuple[WaveFiveBenchmarkRiskFinding, ...]:
    return tuple(
        risk(
            f"risk-{risk_kind.value}",
            risk_kind=risk_kind,
        )
        for risk_kind in REQUIRED_WAVE_FIVE_BENCHMARK_RISKS
    )


def required_controls() -> tuple[WaveFiveBenchmarkControl, ...]:
    return tuple(
        control(
            f"control-{control_kind.value}",
            control_kind=control_kind,
        )
        for control_kind in REQUIRED_WAVE_FIVE_BENCHMARK_CONTROLS
    )


def audit(
    *,
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    audit_state: WaveFiveBenchmarkAuditState = (
        WaveFiveBenchmarkAuditState.READY_FOR_EXTERNAL_AUDIT
    ),
    sources: tuple[WaveFiveBenchmarkSource, ...] | None = None,
    risks: tuple[WaveFiveBenchmarkRiskFinding, ...] | None = None,
    controls: tuple[WaveFiveBenchmarkControl, ...] | None = None,
    reviewer_ids: tuple[str, ...] = (),
    benchmark_score_used_as_agi_evidence: bool = False,
    retained_failed_cases: bool = True,
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    ),
) -> WaveFiveBenchmarkContaminationAudit:
    resolved_sources = (source(),) if sources is None else sources
    resolved_risks = required_risks() if risks is None else risks
    resolved_controls = required_controls() if controls is None else controls

    return WaveFiveBenchmarkContaminationAudit(
        audit_id="wave5-benchmark-audit-001",
        title="Wave 5 benchmark-gaming and contamination audit.",
        source_system=source_system,
        audit_state=audit_state,
        benchmark_sources=resolved_sources,
        risk_findings=resolved_risks,
        controls=resolved_controls,
        protocol_ids=("wave5-external-protocol-001",),
        reviewer_ids=reviewer_ids,
        benchmark_score_used_as_agi_evidence=benchmark_score_used_as_agi_evidence,
        retained_failed_cases=retained_failed_cases,
        claim_boundaries=claim_boundaries,
        notes=("Benchmark evidence is bounded and never treated as AGI proof.",),
    )


def test_required_benchmark_risks_are_locked() -> None:
    assert required_wave_five_benchmark_risks() == REQUIRED_WAVE_FIVE_BENCHMARK_RISKS
    assert len(REQUIRED_WAVE_FIVE_BENCHMARK_RISKS) == 8
    assert WaveFiveBenchmarkRiskKind.CLAIM_INFLATION in (
        REQUIRED_WAVE_FIVE_BENCHMARK_RISKS
    )


def test_required_benchmark_controls_are_locked() -> None:
    assert required_wave_five_benchmark_controls() == (
        REQUIRED_WAVE_FIVE_BENCHMARK_CONTROLS
    )
    assert len(REQUIRED_WAVE_FIVE_BENCHMARK_CONTROLS) == 7
    assert WaveFiveBenchmarkControlKind.FAILED_CASE_RETENTION in (
        REQUIRED_WAVE_FIVE_BENCHMARK_CONTROLS
    )


def test_safe_risk_dispositions_are_locked() -> None:
    assert safe_wave_five_benchmark_risk_dispositions() == (
        SAFE_WAVE_FIVE_BENCHMARK_RISK_DISPOSITIONS
    )
    assert WaveFiveBenchmarkRiskDisposition.BLOCKING not in (
        SAFE_WAVE_FIVE_BENCHMARK_RISK_DISPOSITIONS
    )


def test_external_benchmark_audit_sources_are_locked() -> None:
    assert external_benchmark_audit_source_systems() == (
        EXTERNAL_BENCHMARK_AUDIT_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.INDEPENDENT_REVIEWER in (
        EXTERNAL_BENCHMARK_AUDIT_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.IX_COGNITION_KERNEL not in (
        EXTERNAL_BENCHMARK_AUDIT_SOURCE_SYSTEMS
    )


def test_source_requires_known_limitations() -> None:
    with pytest.raises(ValueError, match="known limitations"):
        WaveFiveBenchmarkSource(
            benchmark_id="benchmark-invalid",
            name="Invalid benchmark",
            allowed_use=WaveFiveBenchmarkUse.STRESS_TEST,
            provenance_status=WaveFiveBenchmarkProvenanceStatus.FULLY_DOCUMENTED,
            scope_summary="Invalid source without limitations.",
            known_limitations=(),
            prohibited_claims=("No AGI claim.",),
            evidence_ids=("evidence",),
        )


def test_source_requires_prohibited_claims() -> None:
    with pytest.raises(ValueError, match="prohibited claims"):
        WaveFiveBenchmarkSource(
            benchmark_id="benchmark-invalid",
            name="Invalid benchmark",
            allowed_use=WaveFiveBenchmarkUse.STRESS_TEST,
            provenance_status=WaveFiveBenchmarkProvenanceStatus.FULLY_DOCUMENTED,
            scope_summary="Invalid source without claim boundaries.",
            known_limitations=("Limited benchmark scope.",),
            prohibited_claims=(),
            evidence_ids=("evidence",),
        )


def test_unknown_or_contaminated_source_can_only_be_negative_control() -> None:
    with pytest.raises(ValueError, match="negative controls"):
        source(provenance_status=WaveFiveBenchmarkProvenanceStatus.UNKNOWN)

    negative = source(
        allowed_use=WaveFiveBenchmarkUse.NEGATIVE_CONTROL,
        provenance_status=WaveFiveBenchmarkProvenanceStatus.CONTAMINATED,
    )
    assert negative.reviewable_as_positive_evidence is False


def test_source_positive_reviewability_requires_strong_provenance() -> None:
    positive = source()
    partial = source(
        benchmark_id="benchmark-partial",
        provenance_status=WaveFiveBenchmarkProvenanceStatus.PARTIALLY_DOCUMENTED,
    )

    assert positive.reviewable_as_positive_evidence is True
    assert partial.reviewable_as_positive_evidence is False


def test_risk_finding_requires_evidence() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveBenchmarkRiskFinding(
            finding_id="risk-invalid",
            benchmark_id="benchmark-held-out-transfer",
            risk_kind=WaveFiveBenchmarkRiskKind.DATA_CONTAMINATION,
            disposition=WaveFiveBenchmarkRiskDisposition.NOT_OBSERVED,
            risk_summary="Missing evidence risk finding.",
            mitigation="Evidence is required.",
            evidence_ids=(),
        )


def test_disputed_risk_requires_reviewer_ids() -> None:
    with pytest.raises(ValueError, match="reviewer ids"):
        risk(disposition=WaveFiveBenchmarkRiskDisposition.EXTERNALLY_DISPUTED)


def test_blocking_risk_disposition_blocks_progress() -> None:
    item = risk(disposition=WaveFiveBenchmarkRiskDisposition.BLOCKING)

    assert item.blocks_wave_five_progress is True


def test_control_requires_evidence() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveBenchmarkControl(
            control_id="control-invalid",
            control_kind=WaveFiveBenchmarkControlKind.PROVENANCE_REVIEW,
            result=WaveFiveBenchmarkControlResult.PASSED,
            description="Missing evidence control.",
            evidence_ids=(),
        )


def test_failed_control_blocks_progress() -> None:
    item = control(result=WaveFiveBenchmarkControlResult.FAILED)

    assert item.passed_with_boundaries is False
    assert item.blocks_wave_five_progress is True


def test_non_blocking_failed_control_does_not_block_progress() -> None:
    item = control(
        result=WaveFiveBenchmarkControlResult.NEEDS_MORE_EVIDENCE,
        blocking=False,
    )

    assert item.blocks_wave_five_progress is False


def test_audit_rejects_benchmark_score_as_agi_evidence() -> None:
    with pytest.raises(ValueError, match="AGI evidence"):
        audit(benchmark_score_used_as_agi_evidence=True)


def test_audit_requires_failed_case_retention() -> None:
    with pytest.raises(ValueError, match="retain failed cases"):
        audit(retained_failed_cases=False)


def test_audit_rejects_risk_for_unknown_source() -> None:
    with pytest.raises(ValueError, match="reference bundled sources"):
        audit(risks=(risk(benchmark_id="missing-benchmark"),))


def test_audit_rejects_missing_claim_boundary() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        audit(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_audit_reports_missing_required_coverage() -> None:
    item = audit(
        risks=(
            risk(
                risk_kind=WaveFiveBenchmarkRiskKind.BENCHMARK_MEMORIZATION,
            ),
        ),
        controls=(
            control(
                control_kind=WaveFiveBenchmarkControlKind.PROVENANCE_REVIEW,
            ),
        ),
    )

    assert item.has_required_risk_coverage is False
    assert WaveFiveBenchmarkRiskKind.CLAIM_INFLATION in (
        item.missing_required_risk_kinds
    )
    assert item.has_required_control_coverage is False
    assert WaveFiveBenchmarkControlKind.EXTERNAL_AUDIT_READY in (
        item.missing_required_control_kinds
    )
    assert item.ready_for_external_benchmark_audit is False


def test_audit_is_ready_for_external_benchmark_review() -> None:
    item = audit()

    assert item.has_required_risk_coverage is True
    assert item.has_required_control_coverage is True
    assert item.has_reviewable_positive_source is True
    assert item.blocking_finding_ids == ()
    assert item.blocking_control_ids == ()
    assert item.ready_for_external_benchmark_audit is True


def test_ready_audit_exports_reviewable_artifact() -> None:
    artifact = audit().to_artifact_ref()

    assert artifact.kind is WaveFiveArtifactKind.BENCHMARK_CONTAMINATION_AUDIT
    assert artifact.capability_area is (
        WaveFiveCapabilityArea.BENCHMARK_GAMING_RESISTANCE
    )
    assert artifact.source_system is WaveFiveSourceSystem.IX_COGNITION_KERNEL
    assert artifact.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    assert artifact.authority_state is WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    )


def test_blocking_finding_exports_blocked_artifact() -> None:
    risks = tuple(
        risk(
            f"risk-{risk_kind.value}",
            risk_kind=risk_kind,
            disposition=(
                WaveFiveBenchmarkRiskDisposition.BLOCKING
                if risk_kind is WaveFiveBenchmarkRiskKind.METRIC_GAMING
                else WaveFiveBenchmarkRiskDisposition.MITIGATED_WITH_EVIDENCE
            ),
        )
        for risk_kind in REQUIRED_WAVE_FIVE_BENCHMARK_RISKS
    )
    artifact = audit(risks=risks).to_artifact_ref()

    assert artifact.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact.authority_state is WaveFiveAuthorityState.BLOCKED
    assert artifact.validation_status is WaveFiveValidationStatus.REJECTED


def test_externally_reviewed_audit_requires_external_source() -> None:
    with pytest.raises(ValueError, match="external source"):
        audit(
            audit_state=WaveFiveBenchmarkAuditState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
            reviewer_ids=("reviewer-001",),
        )


def test_externally_reviewed_audit_requires_reviewer_ids() -> None:
    with pytest.raises(ValueError, match="reviewer ids"):
        audit(
            source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
            audit_state=WaveFiveBenchmarkAuditState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
        )


def test_externally_reviewed_audit_exports_bounded_external_artifact() -> None:
    item = audit(
        source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
        audit_state=WaveFiveBenchmarkAuditState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
        reviewer_ids=("reviewer-001",),
    )
    artifact = item.to_artifact_ref()

    assert item.externally_reviewed_with_boundaries is True
    assert artifact.decision is WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
    )
    assert artifact.externally_validated_with_boundaries is True


def test_audit_collects_unique_evidence_ids() -> None:
    item = audit()

    assert item.all_evidence_ids[0] == "evidence-benchmark-held-out-transfer"
    assert "evidence-control-external-audit-ready" in item.all_evidence_ids
    assert len(item.all_evidence_ids) == 16


def test_audit_fingerprint_is_deterministic() -> None:
    item = audit()

    assert item.fingerprint() == item.fingerprint()
    assert len(item.fingerprint()) == 64
