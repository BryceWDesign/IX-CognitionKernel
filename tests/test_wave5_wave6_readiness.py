import pytest

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
from ix_cognition_kernel.wave5_wave6_readiness import (
    BLOCKING_READINESS_STATUSES,
    EXTERNAL_READINESS_REVIEW_SOURCE_SYSTEMS,
    REQUIRED_READINESS_CHECKS,
    REQUIRED_READINESS_FAMILIES,
    SAFE_READINESS_STATUSES,
    WaveFiveReadinessBlockerKind,
    WaveFiveReadinessCheckKind,
    WaveFiveReadinessCheckResult,
    WaveFiveReadinessEvidenceFamilyRecord,
    WaveFiveReadinessFamily,
    WaveFiveReadinessGateCheck,
    WaveFiveReadinessReviewState,
    WaveFiveReadinessStatus,
    WaveFiveWaveSixReadinessBlocker,
    WaveFiveWaveSixReadinessGate,
    blocking_readiness_statuses,
    external_readiness_review_source_systems,
    required_readiness_checks,
    required_readiness_families,
    safe_readiness_statuses,
)


def family_record(
    family_id: str = "family-external-protocols",
    *,
    family: WaveFiveReadinessFamily = WaveFiveReadinessFamily.EXTERNAL_PROTOCOLS,
    status: WaveFiveReadinessStatus = WaveFiveReadinessStatus.SATISFIED,
    limitations: tuple[str, ...] = (),
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    ),
) -> WaveFiveReadinessEvidenceFamilyRecord:
    return WaveFiveReadinessEvidenceFamilyRecord(
        family_id=family_id,
        family=family,
        status=status,
        artifact_ids=(f"artifact-{family_id}",),
        evidence_ids=(f"evidence-{family_id}",),
        source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
        summary="Wave 5 family is reviewable and evidence-bound.",
        limitations=limitations,
        reviewer_ids=("reviewer-001",),
        claim_boundaries=claim_boundaries,
    )


def gate_check(
    check_id: str,
    check_kind: WaveFiveReadinessCheckKind,
    *,
    result: WaveFiveReadinessCheckResult = WaveFiveReadinessCheckResult.PASSED,
    blocking: bool = True,
) -> WaveFiveReadinessGateCheck:
    return WaveFiveReadinessGateCheck(
        check_id=check_id,
        check_kind=check_kind,
        result=result,
        description="Wave 6 readiness check preserves anti-overclaim boundaries.",
        evidence_ids=(f"evidence-{check_id}",),
        blocking=blocking,
    )


def blocker(
    blocker_id: str = "blocker-memory-gap",
    *,
    family: WaveFiveReadinessFamily = WaveFiveReadinessFamily.MEMORY_INTEGRITY,
    blocker_kind: WaveFiveReadinessBlockerKind = (
        WaveFiveReadinessBlockerKind.MEMORY_INTEGRITY_GAP
    ),
    resolved: bool = False,
    blocking: bool = True,
) -> WaveFiveWaveSixReadinessBlocker:
    return WaveFiveWaveSixReadinessBlocker(
        blocker_id=blocker_id,
        blocker_kind=blocker_kind,
        family=family,
        description="Blocker remains visible before Wave 6 design review.",
        mitigation="Resolve evidence gap before allowing Wave 6 design work.",
        evidence_ids=(f"evidence-{blocker_id}",),
        resolved=resolved,
        blocking=blocking,
    )


def required_families() -> tuple[WaveFiveReadinessEvidenceFamilyRecord, ...]:
    return tuple(
        family_record(
            f"family-{family.value}",
            family=family,
            status=WaveFiveReadinessStatus.SATISFIED_WITH_LIMITS,
            limitations=("Reviewable for Wave 6 design only; not Wave 6 proof.",),
        )
        for family in REQUIRED_READINESS_FAMILIES
    )


def required_gate_checks() -> tuple[WaveFiveReadinessGateCheck, ...]:
    return tuple(
        gate_check(f"check-{check_kind.value}", check_kind)
        for check_kind in REQUIRED_READINESS_CHECKS
    )


def readiness_gate(
    *,
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    review_state: WaveFiveReadinessReviewState = (
        WaveFiveReadinessReviewState.READY_FOR_WAVE_SIX_DESIGN_REVIEW
    ),
    families: tuple[WaveFiveReadinessEvidenceFamilyRecord, ...] | None = None,
    checks: tuple[WaveFiveReadinessGateCheck, ...] | None = None,
    blockers: tuple[WaveFiveWaveSixReadinessBlocker, ...] = (),
    reviewer_ids: tuple[str, ...] = (),
    attempted_wave_six_promotion: bool = False,
    claims_agi: bool = False,
    grants_execution_authority: bool = False,
    claims_production_ready: bool = False,
    claims_certified: bool = False,
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    ),
) -> WaveFiveWaveSixReadinessGate:
    resolved_families = required_families() if families is None else families
    resolved_checks = required_gate_checks() if checks is None else checks
    return WaveFiveWaveSixReadinessGate(
        gate_id="wave5-wave6-readiness-gate-001",
        title="Wave 5 to Wave 6 readiness gate.",
        source_system=source_system,
        review_state=review_state,
        evidence_families=resolved_families,
        checks=resolved_checks,
        blockers=blockers,
        protocol_ids=("wave5-external-protocol-001",),
        reviewer_ids=reviewer_ids,
        attempted_wave_six_promotion=attempted_wave_six_promotion,
        claims_agi=claims_agi,
        grants_execution_authority=grants_execution_authority,
        claims_production_ready=claims_production_ready,
        claims_certified=claims_certified,
        claim_boundaries=claim_boundaries,
        notes=("Ready means Wave 6 design review may begin, not Wave 6 success.",),
    )


def test_required_readiness_families_are_locked() -> None:
    assert required_readiness_families() == REQUIRED_READINESS_FAMILIES
    assert len(REQUIRED_READINESS_FAMILIES) == 13
    assert WaveFiveReadinessFamily.BLACKFOX_COMPATIBILITY in (
        REQUIRED_READINESS_FAMILIES
    )
    assert WaveFiveReadinessFamily.WORLDTWIN_SCENARIOS in (
        REQUIRED_READINESS_FAMILIES
    )


def test_required_readiness_checks_are_locked() -> None:
    assert required_readiness_checks() == REQUIRED_READINESS_CHECKS
    assert len(REQUIRED_READINESS_CHECKS) == 10
    assert WaveFiveReadinessCheckKind.NO_AGI_CLAIM in REQUIRED_READINESS_CHECKS
    assert WaveFiveReadinessCheckKind.WAVE_SIX_SCOPE_BOUND in (
        REQUIRED_READINESS_CHECKS
    )


def test_safe_and_blocking_readiness_statuses_are_locked() -> None:
    assert safe_readiness_statuses() == SAFE_READINESS_STATUSES
    assert blocking_readiness_statuses() == BLOCKING_READINESS_STATUSES
    assert WaveFiveReadinessStatus.SATISFIED in SAFE_READINESS_STATUSES
    assert WaveFiveReadinessStatus.DISPUTED in BLOCKING_READINESS_STATUSES


def test_external_readiness_review_sources_are_locked() -> None:
    assert external_readiness_review_source_systems() == (
        EXTERNAL_READINESS_REVIEW_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.INDEPENDENT_REVIEWER in (
        EXTERNAL_READINESS_REVIEW_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.IX_COGNITION_KERNEL not in (
        EXTERNAL_READINESS_REVIEW_SOURCE_SYSTEMS
    )


def test_family_record_requires_artifacts_and_evidence() -> None:
    with pytest.raises(ValueError, match="artifact ids"):
        WaveFiveReadinessEvidenceFamilyRecord(
            family_id="family-invalid",
            family=WaveFiveReadinessFamily.EXTERNAL_PROTOCOLS,
            status=WaveFiveReadinessStatus.SATISFIED,
            artifact_ids=(),
            evidence_ids=("evidence",),
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
            summary="Invalid family.",
        )

    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveReadinessEvidenceFamilyRecord(
            family_id="family-invalid",
            family=WaveFiveReadinessFamily.EXTERNAL_PROTOCOLS,
            status=WaveFiveReadinessStatus.SATISFIED,
            artifact_ids=("artifact",),
            evidence_ids=(),
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
            summary="Invalid family.",
        )


def test_limited_family_requires_limitations() -> None:
    with pytest.raises(ValueError, match="require limitations"):
        family_record(status=WaveFiveReadinessStatus.SATISFIED_WITH_LIMITS)


def test_family_rejects_missing_claim_boundary() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        family_record(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_blocking_family_status_blocks_wave_six_entry() -> None:
    item = family_record(status=WaveFiveReadinessStatus.DISPUTED)

    assert item.blocks_wave_six_entry is True
    assert item.reviewable_with_boundaries is False


def test_satisfied_family_is_reviewable_with_boundaries() -> None:
    item = family_record()

    assert item.blocks_wave_six_entry is False
    assert item.reviewable_with_boundaries is True


def test_readiness_check_requires_evidence() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveReadinessGateCheck(
            check_id="check-invalid",
            check_kind=WaveFiveReadinessCheckKind.NO_AGI_CLAIM,
            result=WaveFiveReadinessCheckResult.PASSED,
            description="Invalid check.",
            evidence_ids=(),
        )


def test_failed_readiness_check_blocks_wave_six_entry() -> None:
    item = gate_check(
        "check-failed",
        WaveFiveReadinessCheckKind.NO_EXECUTION_AUTHORITY,
        result=WaveFiveReadinessCheckResult.FAILED,
    )

    assert item.passed_with_boundaries is False
    assert item.blocks_wave_six_entry is True


def test_non_blocking_check_does_not_block_wave_six_entry() -> None:
    item = gate_check(
        "check-warning",
        WaveFiveReadinessCheckKind.EXTERNAL_REVIEW_PATH_PRESENT,
        result=WaveFiveReadinessCheckResult.NEEDS_MORE_EVIDENCE,
        blocking=False,
    )

    assert item.blocks_wave_six_entry is False


def test_readiness_blocker_requires_evidence() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveWaveSixReadinessBlocker(
            blocker_id="blocker-invalid",
            blocker_kind=WaveFiveReadinessBlockerKind.CLAIM_BOUNDARY_GAP,
            family=WaveFiveReadinessFamily.EXTERNAL_PROTOCOLS,
            description="Invalid blocker.",
            mitigation="Resolve blocker.",
            evidence_ids=(),
        )


def test_unresolved_blocker_blocks_wave_six_entry() -> None:
    item = blocker()

    assert item.blocks_wave_six_entry is True


def test_resolved_blocker_does_not_block_wave_six_entry() -> None:
    item = blocker(resolved=True)

    assert item.blocks_wave_six_entry is False


def test_gate_rejects_forbidden_claim_flags() -> None:
    with pytest.raises(ValueError, match="cannot promote to Wave 6"):
        readiness_gate(attempted_wave_six_promotion=True)

    with pytest.raises(ValueError, match="cannot claim AGI"):
        readiness_gate(claims_agi=True)

    with pytest.raises(ValueError, match="cannot grant execution"):
        readiness_gate(grants_execution_authority=True)


def test_gate_rejects_production_and_certification_claims() -> None:
    with pytest.raises(ValueError, match="production readiness"):
        readiness_gate(claims_production_ready=True)

    with pytest.raises(ValueError, match="certification"):
        readiness_gate(claims_certified=True)


def test_gate_rejects_missing_claim_boundary() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        readiness_gate(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_gate_reports_missing_required_family_and_check_coverage() -> None:
    item = readiness_gate(
        families=(family_record(),),
        checks=(
            gate_check(
                "check-artifacts-present",
                WaveFiveReadinessCheckKind.ARTIFACTS_PRESENT,
            ),
        ),
    )

    assert item.has_required_family_coverage is False
    assert WaveFiveReadinessFamily.WORLDTWIN_SCENARIOS in (
        item.missing_required_families
    )
    assert item.has_required_check_coverage is False
    assert WaveFiveReadinessCheckKind.WAVE_SIX_SCOPE_BOUND in (
        item.missing_required_check_kinds
    )
    assert item.ready_for_wave_six_design_review is False


def test_gate_blocks_when_family_status_is_blocking() -> None:
    families = tuple(
        family_record(
            f"family-{family.value}",
            family=family,
            status=(
                WaveFiveReadinessStatus.DISPUTED
                if family is WaveFiveReadinessFamily.REPEATABILITY_LEDGER
                else WaveFiveReadinessStatus.SATISFIED
            ),
        )
        for family in REQUIRED_READINESS_FAMILIES
    )
    item = readiness_gate(families=families)

    assert item.blocking_family_ids == ("family-repeatability-ledger",)
    assert item.blocks_wave_six_design_review is True


def test_gate_blocks_when_check_fails() -> None:
    checks = tuple(
        gate_check(
            f"check-{check_kind.value}",
            check_kind,
            result=(
                WaveFiveReadinessCheckResult.FAILED
                if check_kind is WaveFiveReadinessCheckKind.NO_AGI_CLAIM
                else WaveFiveReadinessCheckResult.PASSED
            ),
        )
        for check_kind in REQUIRED_READINESS_CHECKS
    )
    item = readiness_gate(checks=checks)

    assert item.blocking_check_ids == ("check-no-agi-claim",)
    assert item.blocks_wave_six_design_review is True


def test_gate_blocks_when_unresolved_blocker_exists() -> None:
    item = readiness_gate(blockers=(blocker(),))

    assert item.unresolved_blocker_ids == ("blocker-memory-gap",)
    assert item.blocks_wave_six_design_review is True


def test_gate_is_ready_for_wave_six_design_review_only() -> None:
    item = readiness_gate()

    assert item.has_required_family_coverage is True
    assert item.has_required_check_coverage is True
    assert item.blocking_family_ids == ()
    assert item.blocking_check_ids == ()
    assert item.unresolved_blocker_ids == ()
    assert item.makes_no_forbidden_claims is True
    assert item.blocks_wave_six_design_review is False
    assert item.ready_for_wave_six_design_review is True


def test_ready_gate_exports_reviewable_traceability_artifact() -> None:
    artifact = readiness_gate().to_artifact_ref()

    assert artifact.kind is WaveFiveArtifactKind.ECOSYSTEM_TRACEABILITY_MAP
    assert artifact.capability_area is WaveFiveCapabilityArea.ECOSYSTEM_TRACEABILITY
    assert artifact.source_system is WaveFiveSourceSystem.IX_COGNITION_KERNEL
    assert artifact.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    assert artifact.authority_state is WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    )


def test_blocked_gate_exports_blocked_artifact() -> None:
    artifact = readiness_gate(blockers=(blocker(),)).to_artifact_ref()

    assert artifact.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact.authority_state is WaveFiveAuthorityState.BLOCKED
    assert artifact.validation_status is WaveFiveValidationStatus.REJECTED


def test_externally_reviewed_gate_requires_external_source() -> None:
    with pytest.raises(ValueError, match="external source"):
        readiness_gate(
            review_state=(
                WaveFiveReadinessReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
            reviewer_ids=("reviewer-001",),
        )


def test_externally_reviewed_gate_requires_reviewer_ids() -> None:
    with pytest.raises(ValueError, match="reviewer ids"):
        readiness_gate(
            source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
            review_state=(
                WaveFiveReadinessReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
        )


def test_externally_reviewed_gate_exports_bounded_external_artifact() -> None:
    item = readiness_gate(
        source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
        review_state=WaveFiveReadinessReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
        reviewer_ids=("reviewer-001",),
    )
    artifact = item.to_artifact_ref()

    assert item.externally_reviewed_with_boundaries is True
    assert artifact.decision is WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
    )
    assert artifact.externally_validated_with_boundaries is True


def test_gate_collects_unique_evidence_ids() -> None:
    item = readiness_gate()

    assert item.all_evidence_ids[0] == "evidence-family-adversarial-safety"
    assert "evidence-family-worldtwin-scenarios" in item.all_evidence_ids
    assert "evidence-check-wave-six-scope-bound" in item.all_evidence_ids
    assert len(item.all_evidence_ids) == 23


def test_gate_fingerprint_is_deterministic() -> None:
    item = readiness_gate()

    assert item.fingerprint() == item.fingerprint()
    assert len(item.fingerprint()) == 64
