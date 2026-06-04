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
from ix_cognition_kernel.wave5_human_authority import (
    BLOCKING_AUTHORITY_DECISIONS,
    EXTERNAL_AUTHORITY_REVIEW_SOURCE_SYSTEMS,
    REQUIRED_AUTHORITY_BOUNDARIES,
    REQUIRED_AUTHORITY_BYPASS_KINDS,
    REQUIRED_AUTHORITY_CHECKS,
    SAFE_AUTHORITY_DECISIONS,
    WaveFiveAuthorityBoundary,
    WaveFiveAuthorityBoundaryKind,
    WaveFiveAuthorityBypassAttempt,
    WaveFiveAuthorityBypassKind,
    WaveFiveAuthorityCheckKind,
    WaveFiveAuthorityCheckResult,
    WaveFiveAuthorityDecisionKind,
    WaveFiveAuthorityDecisionRecord,
    WaveFiveAuthorityPreservationCheck,
    WaveFiveAuthorityReviewState,
    WaveFiveHumanAuthorityProof,
    blocking_authority_decisions,
    external_authority_review_source_systems,
    required_authority_boundaries,
    required_authority_bypass_kinds,
    required_authority_checks,
    safe_authority_decisions,
)


def boundary(
    boundary_id: str = "boundary-human-approval-required",
    *,
    boundary_kind: WaveFiveAuthorityBoundaryKind = (
        WaveFiveAuthorityBoundaryKind.HUMAN_APPROVAL_REQUIRED
    ),
    enforced: bool = True,
    revocable: bool = True,
) -> WaveFiveAuthorityBoundary:
    return WaveFiveAuthorityBoundary(
        boundary_id=boundary_id,
        boundary_kind=boundary_kind,
        protected_action="Any Wave 5 evidence-to-execution or maturity claim path.",
        required_human_role="authorized human reviewer",
        enforcement_summary="Human approval remains required and reviewable.",
        evidence_ids=(f"evidence-{boundary_id}",),
        enforced=enforced,
        revocable=revocable,
    )


def decision(
    decision_id: str = "decision-review-only",
    *,
    boundary_id: str = "boundary-human-approval-required",
    decision_kind: WaveFiveAuthorityDecisionKind = (
        WaveFiveAuthorityDecisionKind.APPROVED_FOR_REVIEW_ONLY
    ),
    human_reviewer_id: str = "human-reviewer-001",
    granted_execution_authority: bool = False,
    self_approved: bool = False,
    approved_maturity_claim: bool = False,
    preserved_human_authority: bool = True,
) -> WaveFiveAuthorityDecisionRecord:
    return WaveFiveAuthorityDecisionRecord(
        decision_id=decision_id,
        boundary_id=boundary_id,
        decision_kind=decision_kind,
        requested_action="Treat evidence as reviewable without granting execution.",
        decision_summary="Decision preserves human authority and review scope.",
        human_reviewer_id=human_reviewer_id,
        evidence_ids=(f"evidence-{decision_id}",),
        granted_execution_authority=granted_execution_authority,
        self_approved=self_approved,
        approved_maturity_claim=approved_maturity_claim,
        preserved_human_authority=preserved_human_authority,
    )


def bypass_attempt(
    attempt_id: str = "attempt-self-approval",
    *,
    boundary_id: str = "boundary-human-approval-required",
    bypass_kind: WaveFiveAuthorityBypassKind = (
        WaveFiveAuthorityBypassKind.SELF_APPROVAL
    ),
    detected: bool = True,
    blocked: bool = True,
    reviewer_visible: bool = True,
) -> WaveFiveAuthorityBypassAttempt:
    return WaveFiveAuthorityBypassAttempt(
        attempt_id=attempt_id,
        boundary_id=boundary_id,
        bypass_kind=bypass_kind,
        attempt_summary="Attempt tries to bypass required human authority.",
        detected=detected,
        blocked=blocked,
        reviewer_visible=reviewer_visible,
        mitigation="Block bypass and preserve reviewer-visible evidence.",
        evidence_ids=(f"evidence-{attempt_id}",),
    )


def check(
    check_id: str,
    check_kind: WaveFiveAuthorityCheckKind,
    *,
    result: WaveFiveAuthorityCheckResult = WaveFiveAuthorityCheckResult.PASSED,
    blocking: bool = True,
) -> WaveFiveAuthorityPreservationCheck:
    return WaveFiveAuthorityPreservationCheck(
        check_id=check_id,
        check_kind=check_kind,
        result=result,
        description="Authority check preserves human authorization boundaries.",
        evidence_ids=(f"evidence-{check_id}",),
        blocking=blocking,
    )


def required_boundaries() -> tuple[WaveFiveAuthorityBoundary, ...]:
    return tuple(
        boundary(f"boundary-{kind.value}", boundary_kind=kind)
        for kind in REQUIRED_AUTHORITY_BOUNDARIES
    )


def required_decisions() -> tuple[WaveFiveAuthorityDecisionRecord, ...]:
    return tuple(
        decision(
            f"decision-{item.boundary_kind.value}",
            boundary_id=item.boundary_id,
        )
        for item in required_boundaries()
    )


def required_bypass_attempts() -> tuple[WaveFiveAuthorityBypassAttempt, ...]:
    return tuple(
        bypass_attempt(
            f"attempt-{kind.value}",
            boundary_id="boundary-human-approval-required",
            bypass_kind=kind,
        )
        for kind in REQUIRED_AUTHORITY_BYPASS_KINDS
    )


def required_checks() -> tuple[WaveFiveAuthorityPreservationCheck, ...]:
    return tuple(
        check(f"check-{check_kind.value}", check_kind)
        for check_kind in REQUIRED_AUTHORITY_CHECKS
    )


def proof(
    *,
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    review_state: WaveFiveAuthorityReviewState = (
        WaveFiveAuthorityReviewState.READY_FOR_EXTERNAL_AUTHORITY_REVIEW
    ),
    boundaries: tuple[WaveFiveAuthorityBoundary, ...] | None = None,
    decisions: tuple[WaveFiveAuthorityDecisionRecord, ...] | None = None,
    attempts: tuple[WaveFiveAuthorityBypassAttempt, ...] | None = None,
    checks: tuple[WaveFiveAuthorityPreservationCheck, ...] | None = None,
    reviewer_ids: tuple[str, ...] = (),
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    ),
) -> WaveFiveHumanAuthorityProof:
    resolved_boundaries = required_boundaries() if boundaries is None else boundaries
    resolved_decisions = required_decisions() if decisions is None else decisions
    resolved_attempts = required_bypass_attempts() if attempts is None else attempts
    resolved_checks = required_checks() if checks is None else checks

    return WaveFiveHumanAuthorityProof(
        proof_id="wave5-human-authority-proof-001",
        title="Wave 5 human-authority preservation proof for Wave 6 readiness.",
        source_system=source_system,
        review_state=review_state,
        boundaries=resolved_boundaries,
        decisions=resolved_decisions,
        bypass_attempts=resolved_attempts,
        checks=resolved_checks,
        protocol_ids=("wave5-external-protocol-001",),
        reviewer_ids=reviewer_ids,
        claim_boundaries=claim_boundaries,
        notes=("Human authority remains mandatory for action and maturity claims.",),
    )


def test_required_authority_boundaries_are_locked() -> None:
    assert required_authority_boundaries() == REQUIRED_AUTHORITY_BOUNDARIES
    assert len(REQUIRED_AUTHORITY_BOUNDARIES) == 8
    assert WaveFiveAuthorityBoundaryKind.NO_AUTONOMOUS_EXECUTION in (
        REQUIRED_AUTHORITY_BOUNDARIES
    )
    assert WaveFiveAuthorityBoundaryKind.MATURITY_CLAIM_REVIEW_REQUIRED in (
        REQUIRED_AUTHORITY_BOUNDARIES
    )


def test_required_bypass_kinds_are_locked() -> None:
    assert required_authority_bypass_kinds() == REQUIRED_AUTHORITY_BYPASS_KINDS
    assert len(REQUIRED_AUTHORITY_BYPASS_KINDS) == 7
    assert WaveFiveAuthorityBypassKind.DONOR_REPO_AUTHORITY_LEAK in (
        REQUIRED_AUTHORITY_BYPASS_KINDS
    )


def test_required_authority_checks_are_locked() -> None:
    assert required_authority_checks() == REQUIRED_AUTHORITY_CHECKS
    assert len(REQUIRED_AUTHORITY_CHECKS) == 9
    assert WaveFiveAuthorityCheckKind.NO_AUTONOMOUS_EXECUTION_GRANTED in (
        REQUIRED_AUTHORITY_CHECKS
    )


def test_safe_and_blocking_authority_decisions_are_locked() -> None:
    assert safe_authority_decisions() == SAFE_AUTHORITY_DECISIONS
    assert blocking_authority_decisions() == BLOCKING_AUTHORITY_DECISIONS
    assert WaveFiveAuthorityDecisionKind.UNAUTHORIZED_ACTION_ATTEMPTED in (
        BLOCKING_AUTHORITY_DECISIONS
    )


def test_external_authority_review_sources_are_locked() -> None:
    assert external_authority_review_source_systems() == (
        EXTERNAL_AUTHORITY_REVIEW_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.INDEPENDENT_REVIEWER in (
        EXTERNAL_AUTHORITY_REVIEW_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.IX_COGNITION_KERNEL not in (
        EXTERNAL_AUTHORITY_REVIEW_SOURCE_SYSTEMS
    )


def test_authority_boundary_requires_evidence() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveAuthorityBoundary(
            boundary_id="boundary-invalid",
            boundary_kind=WaveFiveAuthorityBoundaryKind.HUMAN_APPROVAL_REQUIRED,
            protected_action="Invalid boundary without evidence.",
            required_human_role="authorized reviewer",
            enforcement_summary="Missing evidence.",
            evidence_ids=(),
        )


def test_revocation_boundary_must_be_revocable() -> None:
    with pytest.raises(ValueError, match="must be revocable"):
        boundary(
            boundary_kind=WaveFiveAuthorityBoundaryKind.REVOCATION_AVAILABLE,
            revocable=False,
        )


def test_unenforced_boundary_blocks_progress() -> None:
    item = boundary(enforced=False)

    assert item.blocks_wave_five_progress is True


def test_authority_decision_rejects_bad_authority_flags() -> None:
    with pytest.raises(ValueError, match="cannot grant execution"):
        decision(granted_execution_authority=True)

    with pytest.raises(ValueError, match="self-approved"):
        decision(self_approved=True)

    with pytest.raises(ValueError, match="maturity claims"):
        decision(approved_maturity_claim=True)


def test_safe_decision_requires_human_reviewer_and_preserved_authority() -> None:
    with pytest.raises(ValueError, match="human reviewer"):
        decision(human_reviewer_id="")

    with pytest.raises(ValueError, match="preserve authority"):
        decision(preserved_human_authority=False)


def test_unauthorized_action_decision_blocks_progress() -> None:
    item = decision(
        decision_kind=WaveFiveAuthorityDecisionKind.UNAUTHORIZED_ACTION_ATTEMPTED,
        human_reviewer_id="",
        preserved_human_authority=False,
    )

    assert item.is_safe_decision is False
    assert item.blocks_wave_five_progress is True


def test_bypass_attempt_requires_reviewer_visibility() -> None:
    with pytest.raises(ValueError, match="reviewer visible"):
        bypass_attempt(reviewer_visible=False)


def test_unresolved_bypass_attempt_blocks_progress() -> None:
    item = bypass_attempt(blocked=False)

    assert item.resolved is False
    assert item.blocks_wave_five_progress is True


def test_authority_check_requires_evidence() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveAuthorityPreservationCheck(
            check_id="check-invalid",
            check_kind=WaveFiveAuthorityCheckKind.HUMAN_APPROVAL_GATE_PRESENT,
            result=WaveFiveAuthorityCheckResult.PASSED,
            description="Invalid check without evidence.",
            evidence_ids=(),
        )


def test_failed_authority_check_blocks_progress() -> None:
    item = check(
        "check-failed",
        WaveFiveAuthorityCheckKind.NO_AUTONOMOUS_EXECUTION_GRANTED,
        result=WaveFiveAuthorityCheckResult.FAILED,
    )

    assert item.passed_with_boundaries is False
    assert item.blocks_wave_five_progress is True


def test_proof_rejects_decision_for_unknown_boundary() -> None:
    with pytest.raises(ValueError, match="reference bundled boundaries"):
        proof(
            boundaries=(boundary("boundary-known"),),
            decisions=(decision(boundary_id="boundary-missing"),),
        )


def test_proof_rejects_bypass_attempt_for_unknown_boundary() -> None:
    with pytest.raises(ValueError, match="reference bundled boundaries"):
        proof(
            boundaries=(boundary("boundary-known"),),
            decisions=(decision(boundary_id="boundary-known"),),
            attempts=(bypass_attempt(boundary_id="boundary-missing"),),
        )


def test_proof_rejects_missing_claim_boundary() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        proof(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_proof_reports_missing_required_coverage() -> None:
    item = proof(
        boundaries=(boundary(),),
        decisions=(decision(),),
        attempts=(bypass_attempt(),),
        checks=(
            check(
                "check-human-approval-gate-present",
                WaveFiveAuthorityCheckKind.HUMAN_APPROVAL_GATE_PRESENT,
            ),
        ),
    )

    assert item.has_required_boundary_coverage is False
    assert WaveFiveAuthorityBoundaryKind.NO_SELF_APPROVAL in (
        item.missing_required_boundary_kinds
    )
    assert item.has_required_bypass_coverage is False
    assert WaveFiveAuthorityBypassKind.AUTONOMOUS_EXECUTION in (
        item.missing_required_bypass_kinds
    )
    assert item.has_required_check_coverage is False
    assert WaveFiveAuthorityCheckKind.AUDIT_TRACE_VISIBLE in (
        item.missing_required_check_kinds
    )
    assert item.ready_for_external_authority_review is False


def test_proof_is_ready_for_external_authority_review() -> None:
    item = proof()

    assert item.has_required_boundary_coverage is True
    assert item.has_required_bypass_coverage is True
    assert item.has_required_check_coverage is True
    assert item.blocking_boundary_ids == ()
    assert item.blocking_decision_ids == ()
    assert item.blocking_bypass_attempt_ids == ()
    assert item.blocking_check_ids == ()
    assert item.grants_no_execution_authority is True
    assert item.blocks_self_approval is True
    assert item.blocks_maturity_self_promotion is True
    assert item.preserves_human_authority is True
    assert item.ready_for_external_authority_review is True


def test_ready_proof_exports_reviewable_artifact() -> None:
    artifact = proof().to_artifact_ref()

    assert artifact.kind is WaveFiveArtifactKind.HUMAN_AUTHORITY_PROOF
    assert artifact.capability_area is (
        WaveFiveCapabilityArea.HUMAN_AUTHORITY_PRESERVATION
    )
    assert artifact.source_system is WaveFiveSourceSystem.IX_COGNITION_KERNEL
    assert artifact.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    assert artifact.authority_state is WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    )


def test_blocking_bypass_attempt_exports_blocked_artifact() -> None:
    attempts = tuple(
        bypass_attempt(
            f"attempt-{kind.value}",
            boundary_id="boundary-human-approval-required",
            bypass_kind=kind,
            blocked=(kind is not WaveFiveAuthorityBypassKind.AUTONOMOUS_EXECUTION),
        )
        for kind in REQUIRED_AUTHORITY_BYPASS_KINDS
    )
    artifact = proof(attempts=attempts).to_artifact_ref()

    assert artifact.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact.authority_state is WaveFiveAuthorityState.BLOCKED
    assert artifact.validation_status is WaveFiveValidationStatus.REJECTED


def test_blocking_check_exports_blocked_artifact() -> None:
    checks = tuple(
        check(
            f"check-{check_kind.value}",
            check_kind,
            result=(
                WaveFiveAuthorityCheckResult.FAILED
                if check_kind
                is WaveFiveAuthorityCheckKind.NO_AUTONOMOUS_EXECUTION_GRANTED
                else WaveFiveAuthorityCheckResult.PASSED
            ),
        )
        for check_kind in REQUIRED_AUTHORITY_CHECKS
    )
    artifact = proof(checks=checks).to_artifact_ref()

    assert artifact.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact.validation_status is WaveFiveValidationStatus.REJECTED


def test_externally_reviewed_proof_requires_external_source() -> None:
    with pytest.raises(ValueError, match="external source"):
        proof(
            review_state=(
                WaveFiveAuthorityReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
            reviewer_ids=("reviewer-001",),
        )


def test_externally_reviewed_proof_requires_reviewer_ids() -> None:
    with pytest.raises(ValueError, match="reviewer ids"):
        proof(
            source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
            review_state=(
                WaveFiveAuthorityReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
        )


def test_externally_reviewed_proof_exports_bounded_external_artifact() -> None:
    item = proof(
        source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
        review_state=WaveFiveAuthorityReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
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
    item = proof()

    assert item.all_evidence_ids[0] == "evidence-boundary-donor-repo-authority-isolated"
    assert "evidence-attempt-maturity-self-promotion" in item.all_evidence_ids
    assert "evidence-check-audit-trace-visible" in item.all_evidence_ids
    assert len(item.all_evidence_ids) == 32


def test_proof_fingerprint_is_deterministic() -> None:
    item = proof()

    assert item.fingerprint() == item.fingerprint()
    assert len(item.fingerprint()) == 64
