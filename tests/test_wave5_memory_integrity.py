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
from ix_cognition_kernel.wave5_memory_integrity import (
    BLOCKING_MEMORY_INTEGRITY_STATES,
    EXTERNAL_MEMORY_REVIEW_SOURCE_SYSTEMS,
    REQUIRED_WAVE_FIVE_MEMORY_CHECKS,
    SAFE_MEMORY_INTEGRITY_STATES,
    WaveFiveMemoryCheckKind,
    WaveFiveMemoryCheckResult,
    WaveFiveMemoryClaim,
    WaveFiveMemoryIntegrityCheck,
    WaveFiveMemoryIntegrityProof,
    WaveFiveMemoryIntegrityState,
    WaveFiveMemoryProofReviewState,
    WaveFiveMemoryProvenance,
    WaveFiveMemoryQuarantineFinding,
    WaveFiveMemoryQuarantineReason,
    blocking_memory_integrity_states,
    external_memory_review_source_systems,
    required_wave_five_memory_checks,
    safe_memory_integrity_states,
)


def claim(
    memory_id: str = "memory-validated",
    *,
    provenance: WaveFiveMemoryProvenance = WaveFiveMemoryProvenance.OUTCOME_LEARNED,
    state: WaveFiveMemoryIntegrityState = WaveFiveMemoryIntegrityState.VALIDATED,
    evidence_ids: tuple[str, ...] = ("evidence-memory-validated",),
    contradiction_ids: tuple[str, ...] = (),
    staleness_evidence_ids: tuple[str, ...] = (),
    allowed_for_planning: bool = True,
    allowed_for_action: bool = False,
) -> WaveFiveMemoryClaim:
    return WaveFiveMemoryClaim(
        memory_id=memory_id,
        summary="Memory claim remains evidence-bound and reviewer visible.",
        provenance=provenance,
        integrity_state=state,
        source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
        evidence_ids=evidence_ids,
        contradiction_ids=contradiction_ids,
        staleness_evidence_ids=staleness_evidence_ids,
        allowed_for_planning=allowed_for_planning,
        allowed_for_action=allowed_for_action,
    )


def check(
    check_id: str,
    check_kind: WaveFiveMemoryCheckKind,
    *,
    result: WaveFiveMemoryCheckResult = WaveFiveMemoryCheckResult.PASSED,
    blocking: bool = True,
) -> WaveFiveMemoryIntegrityCheck:
    return WaveFiveMemoryIntegrityCheck(
        check_id=check_id,
        check_kind=check_kind,
        result=result,
        description="Memory-integrity check preserves Wave 5 evidence boundaries.",
        evidence_ids=(f"evidence-{check_id}",),
        blocking=blocking,
    )


def quarantine(
    finding_id: str = "quarantine-memory-quarantined",
    *,
    memory_id: str = "memory-quarantined",
    reason: WaveFiveMemoryQuarantineReason = (
        WaveFiveMemoryQuarantineReason.UNKNOWN_PROVENANCE
    ),
    rejected: bool = True,
    reviewer_visible: bool = True,
) -> WaveFiveMemoryQuarantineFinding:
    return WaveFiveMemoryQuarantineFinding(
        finding_id=finding_id,
        memory_id=memory_id,
        reason=reason,
        rejected_from_trusted_memory=rejected,
        reviewer_visible=reviewer_visible,
        mitigation="Reject from trusted memory and preserve review-visible trace.",
        evidence_ids=(f"evidence-{finding_id}",),
    )


def required_checks() -> tuple[WaveFiveMemoryIntegrityCheck, ...]:
    return tuple(
        check(f"check-{check_kind.value}", check_kind)
        for check_kind in REQUIRED_WAVE_FIVE_MEMORY_CHECKS
    )


def proof(
    *,
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    review_state: WaveFiveMemoryProofReviewState = (
        WaveFiveMemoryProofReviewState.READY_FOR_EXTERNAL_MEMORY_REVIEW
    ),
    claims: tuple[WaveFiveMemoryClaim, ...] | None = None,
    checks: tuple[WaveFiveMemoryIntegrityCheck, ...] | None = None,
    quarantines: tuple[WaveFiveMemoryQuarantineFinding, ...] | None = None,
    reviewer_ids: tuple[str, ...] = (),
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    ),
) -> WaveFiveMemoryIntegrityProof:
    resolved_claims = (claim(),) if claims is None else claims
    resolved_checks = required_checks() if checks is None else checks
    resolved_quarantines = () if quarantines is None else quarantines

    return WaveFiveMemoryIntegrityProof(
        proof_id="wave5-memory-integrity-proof-001",
        title="Wave 5 memory-integrity proof for Wave 6 readiness.",
        source_system=source_system,
        review_state=review_state,
        memory_claims=resolved_claims,
        integrity_checks=resolved_checks,
        quarantine_findings=resolved_quarantines,
        protocol_ids=("wave5-external-protocol-001",),
        reviewer_ids=reviewer_ids,
        claim_boundaries=claim_boundaries,
        notes=("Memory supports planning only after evidence-bound validation.",),
    )


def test_required_memory_checks_are_locked() -> None:
    assert required_wave_five_memory_checks() == REQUIRED_WAVE_FIVE_MEMORY_CHECKS
    assert len(REQUIRED_WAVE_FIVE_MEMORY_CHECKS) == 8
    assert WaveFiveMemoryCheckKind.QUARANTINE_ENFORCED in (
        REQUIRED_WAVE_FIVE_MEMORY_CHECKS
    )


def test_safe_and_blocking_memory_states_are_locked() -> None:
    assert safe_memory_integrity_states() == SAFE_MEMORY_INTEGRITY_STATES
    assert blocking_memory_integrity_states() == BLOCKING_MEMORY_INTEGRITY_STATES
    assert WaveFiveMemoryIntegrityState.VALIDATED in SAFE_MEMORY_INTEGRITY_STATES
    assert WaveFiveMemoryIntegrityState.CONTRADICTED in (
        BLOCKING_MEMORY_INTEGRITY_STATES
    )


def test_external_memory_review_sources_are_locked() -> None:
    assert external_memory_review_source_systems() == (
        EXTERNAL_MEMORY_REVIEW_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.INDEPENDENT_REVIEWER in (
        EXTERNAL_MEMORY_REVIEW_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.IX_COGNITION_KERNEL not in (
        EXTERNAL_MEMORY_REVIEW_SOURCE_SYSTEMS
    )


def test_unknown_provenance_memory_must_be_quarantined() -> None:
    with pytest.raises(ValueError, match="Unknown-provenance"):
        claim(provenance=WaveFiveMemoryProvenance.UNKNOWN)


def test_validated_memory_requires_evidence() -> None:
    with pytest.raises(ValueError, match="Validated memory"):
        claim(evidence_ids=())


def test_contradicted_memory_requires_contradiction_ids() -> None:
    with pytest.raises(ValueError, match="Contradicted memory"):
        claim(
            state=WaveFiveMemoryIntegrityState.CONTRADICTED,
            allowed_for_planning=False,
        )


def test_stale_memory_requires_staleness_evidence() -> None:
    with pytest.raises(ValueError, match="Stale memory"):
        claim(
            state=WaveFiveMemoryIntegrityState.STALE,
            allowed_for_planning=False,
        )


def test_unsafe_memory_cannot_be_allowed_for_planning() -> None:
    with pytest.raises(ValueError, match="planning/action"):
        claim(
            state=WaveFiveMemoryIntegrityState.QUARANTINED,
            evidence_ids=(),
            allowed_for_planning=True,
        )


def test_memory_claims_cannot_authorize_action() -> None:
    with pytest.raises(ValueError, match="cannot authorize action"):
        claim(allowed_for_action=True)


def test_validated_memory_can_support_bounded_planning_only() -> None:
    item = claim()

    assert item.is_safe_for_bounded_planning is True
    assert item.blocks_wave_five_progress is False
    assert item.needs_visibility_not_trust is False


def test_quarantined_memory_remains_visible_not_trusted() -> None:
    item = claim(
        "memory-quarantined",
        provenance=WaveFiveMemoryProvenance.UNKNOWN,
        state=WaveFiveMemoryIntegrityState.QUARANTINED,
        evidence_ids=(),
        allowed_for_planning=False,
    )

    assert item.blocks_wave_five_progress is True
    assert item.needs_visibility_not_trust is True


def test_memory_integrity_check_requires_evidence() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveMemoryIntegrityCheck(
            check_id="check-invalid",
            check_kind=WaveFiveMemoryCheckKind.EVIDENCE_BOUND,
            result=WaveFiveMemoryCheckResult.PASSED,
            description="Invalid check without evidence.",
            evidence_ids=(),
        )


def test_failed_memory_integrity_check_blocks_progress() -> None:
    item = check(
        "check-failed",
        WaveFiveMemoryCheckKind.EVIDENCE_BOUND,
        result=WaveFiveMemoryCheckResult.FAILED,
    )

    assert item.passed_with_boundaries is False
    assert item.blocks_wave_five_progress is True


def test_non_blocking_check_does_not_block_progress() -> None:
    item = check(
        "check-warning",
        WaveFiveMemoryCheckKind.REPLAY_TRACE_VISIBLE,
        result=WaveFiveMemoryCheckResult.NEEDS_MORE_EVIDENCE,
        blocking=False,
    )

    assert item.blocks_wave_five_progress is False


def test_quarantine_finding_requires_reviewer_visibility() -> None:
    with pytest.raises(ValueError, match="reviewer visible"):
        quarantine(reviewer_visible=False)


def test_quarantine_finding_reports_unresolved_state() -> None:
    item = quarantine(rejected=False)

    assert item.resolved is False
    assert item.blocks_wave_five_progress is True


def test_proof_rejects_quarantine_for_unknown_memory() -> None:
    with pytest.raises(ValueError, match="reference bundled memory"):
        proof(quarantines=(quarantine(memory_id="missing-memory"),))


def test_proof_rejects_missing_claim_boundary() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        proof(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_proof_reports_missing_required_check_coverage() -> None:
    item = proof(
        checks=(
            check(
                "check-provenance-bound",
                WaveFiveMemoryCheckKind.PROVENANCE_BOUND,
            ),
        )
    )

    assert item.has_required_check_coverage is False
    assert WaveFiveMemoryCheckKind.HUMAN_AUTHORITY_PRESERVED in (
        item.missing_required_check_kinds
    )
    assert item.ready_for_external_memory_review is False


def test_proof_rejects_untrusted_memory_when_quarantine_missing() -> None:
    untrusted = claim(
        "memory-quarantined",
        provenance=WaveFiveMemoryProvenance.UNKNOWN,
        state=WaveFiveMemoryIntegrityState.QUARANTINED,
        evidence_ids=(),
        allowed_for_planning=False,
    )
    item = proof(claims=(claim(), untrusted))

    assert item.rejects_untrusted_memory is False
    assert item.visible_untrusted_memory_ids == ("memory-quarantined",)
    assert item.ready_for_external_memory_review is False


def test_proof_is_ready_when_untrusted_memory_is_quarantined() -> None:
    untrusted = claim(
        "memory-quarantined",
        provenance=WaveFiveMemoryProvenance.UNKNOWN,
        state=WaveFiveMemoryIntegrityState.QUARANTINED,
        evidence_ids=(),
        allowed_for_planning=False,
    )
    item = proof(
        claims=(claim(), untrusted),
        quarantines=(quarantine(),),
    )

    assert item.has_required_check_coverage is True
    assert item.rejects_untrusted_memory is True
    assert item.blocking_check_ids == ()
    assert item.blocking_quarantine_finding_ids == ()
    assert item.ready_for_external_memory_review is True


def test_ready_proof_exports_reviewable_artifact() -> None:
    artifact = proof().to_artifact_ref()

    assert artifact.kind is WaveFiveArtifactKind.MEMORY_INTEGRITY_PROOF
    assert artifact.capability_area is WaveFiveCapabilityArea.MEMORY_INTEGRITY
    assert artifact.source_system is WaveFiveSourceSystem.IX_COGNITION_KERNEL
    assert artifact.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    assert artifact.authority_state is WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    )


def test_blocking_check_exports_blocked_artifact() -> None:
    checks = tuple(
        check(
            f"check-{check_kind.value}",
            check_kind,
            result=(
                WaveFiveMemoryCheckResult.FAILED
                if check_kind is WaveFiveMemoryCheckKind.EVIDENCE_BOUND
                else WaveFiveMemoryCheckResult.PASSED
            ),
        )
        for check_kind in REQUIRED_WAVE_FIVE_MEMORY_CHECKS
    )
    artifact = proof(checks=checks).to_artifact_ref()

    assert artifact.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact.authority_state is WaveFiveAuthorityState.BLOCKED
    assert artifact.validation_status is WaveFiveValidationStatus.REJECTED


def test_externally_reviewed_proof_requires_external_source() -> None:
    with pytest.raises(ValueError, match="external source"):
        proof(
            review_state=(
                WaveFiveMemoryProofReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
            reviewer_ids=("reviewer-001",),
        )


def test_externally_reviewed_proof_requires_reviewer_ids() -> None:
    with pytest.raises(ValueError, match="reviewer ids"):
        proof(
            source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
            review_state=(
                WaveFiveMemoryProofReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
        )


def test_externally_reviewed_proof_exports_bounded_external_artifact() -> None:
    item = proof(
        source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
        review_state=WaveFiveMemoryProofReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
        reviewer_ids=("reviewer-001",),
    )
    artifact = item.to_artifact_ref()

    assert item.externally_reviewed_with_boundaries is True
    assert artifact.decision is WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
    )
    assert artifact.externally_validated_with_boundaries is True


def test_proof_collects_unique_evidence_ids() -> None:
    stale = claim(
        "memory-stale",
        state=WaveFiveMemoryIntegrityState.STALE,
        evidence_ids=("evidence-memory-stale",),
        staleness_evidence_ids=("evidence-stale-context",),
        allowed_for_planning=False,
    )
    item = proof(
        claims=(claim(), stale),
        quarantines=(
            quarantine(
                "quarantine-memory-stale",
                memory_id="memory-stale",
                reason=WaveFiveMemoryQuarantineReason.STALE_CONTEXT,
            ),
        ),
    )

    assert item.all_evidence_ids[0] == "evidence-memory-stale"
    assert "evidence-stale-context" in item.all_evidence_ids
    assert "evidence-check-human-authority-preserved" in item.all_evidence_ids


def test_proof_fingerprint_is_deterministic() -> None:
    item = proof()

    assert item.fingerprint() == item.fingerprint()
    assert len(item.fingerprint()) == 64
