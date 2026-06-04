import pytest

from ix_cognition_kernel.wave5_bounded_declaration import (
    BLOCKING_DECLARATION_INPUT_STATUSES,
    EXTERNAL_DECLARATION_REVIEW_SOURCE_SYSTEMS,
    REQUIRED_DECLARATION_CHECK_KINDS,
    REQUIRED_DECLARATION_INPUT_KINDS,
    SAFE_DECLARATION_INPUT_STATUSES,
    WaveFiveBoundedDeclaration,
    WaveFiveBoundedDeclarationBlocker,
    WaveFiveBoundedDeclarationCheck,
    WaveFiveBoundedDeclarationState,
    WaveFiveDeclarationBlockerKind,
    WaveFiveDeclarationBlockerSeverity,
    WaveFiveDeclarationCheckKind,
    WaveFiveDeclarationCheckResult,
    WaveFiveDeclarationInputKind,
    WaveFiveDeclarationInputRecord,
    WaveFiveDeclarationInputStatus,
    blocking_declaration_input_statuses,
    external_declaration_review_source_systems,
    required_declaration_check_kinds,
    required_declaration_input_kinds,
    safe_declaration_input_statuses,
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

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


def input_record(
    input_id: str = "input-release-manifest",
    *,
    input_kind: WaveFiveDeclarationInputKind = (
        WaveFiveDeclarationInputKind.RELEASE_MANIFEST
    ),
    status: WaveFiveDeclarationInputStatus = WaveFiveDeclarationInputStatus.REVIEWABLE,
    digest: str = DIGEST_A,
    limitations: tuple[str, ...] = (),
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    ),
) -> WaveFiveDeclarationInputRecord:
    return WaveFiveDeclarationInputRecord(
        input_id=input_id,
        input_kind=input_kind,
        status=status,
        digest=digest,
        evidence_ids=(f"evidence-{input_id}",),
        source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
        summary="Declaration input is evidence-bound and reviewable.",
        limitations=limitations,
        reviewer_ids=("reviewer-001",),
        claim_boundaries=claim_boundaries,
    )


def declaration_check(
    check_id: str,
    check_kind: WaveFiveDeclarationCheckKind,
    *,
    result: WaveFiveDeclarationCheckResult = WaveFiveDeclarationCheckResult.PASSED,
    blocking: bool = True,
) -> WaveFiveBoundedDeclarationCheck:
    return WaveFiveBoundedDeclarationCheck(
        check_id=check_id,
        check_kind=check_kind,
        result=result,
        description="Bounded declaration check preserves Wave 5 boundaries.",
        evidence_ids=(f"evidence-{check_id}",),
        blocking=blocking,
    )


def blocker(
    blocker_id: str = "blocker-release-manifest",
    *,
    input_kind: WaveFiveDeclarationInputKind = (
        WaveFiveDeclarationInputKind.RELEASE_MANIFEST
    ),
    blocker_kind: WaveFiveDeclarationBlockerKind = (
        WaveFiveDeclarationBlockerKind.UNRESOLVED_RELEASE_BLOCKER
    ),
    severity: WaveFiveDeclarationBlockerSeverity = (
        WaveFiveDeclarationBlockerSeverity.LIMITATION
    ),
    resolved: bool = False,
) -> WaveFiveBoundedDeclarationBlocker:
    return WaveFiveBoundedDeclarationBlocker(
        blocker_id=blocker_id,
        blocker_kind=blocker_kind,
        severity=severity,
        input_kind=input_kind,
        description="Declaration blocker remains visible to reviewers.",
        mitigation="Resolve blocker or preserve it as a visible limitation.",
        evidence_ids=(f"evidence-{blocker_id}",),
        resolved=resolved,
    )


def required_inputs() -> tuple[WaveFiveDeclarationInputRecord, ...]:
    return tuple(
        input_record(
            f"input-{input_kind.value}",
            input_kind=input_kind,
            status=WaveFiveDeclarationInputStatus.REVIEWABLE_WITH_LIMITS,
            digest=(DIGEST_A if index % 2 == 0 else DIGEST_B),
            limitations=("Bounded Wave 5 declaration only; not Wave 6 proof.",),
        )
        for index, input_kind in enumerate(REQUIRED_DECLARATION_INPUT_KINDS)
    )


def required_checks() -> tuple[WaveFiveBoundedDeclarationCheck, ...]:
    return tuple(
        declaration_check(f"check-{check_kind.value}", check_kind)
        for check_kind in REQUIRED_DECLARATION_CHECK_KINDS
    )


def declaration(
    *,
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    declaration_state: WaveFiveBoundedDeclarationState = (
        WaveFiveBoundedDeclarationState.READY_FOR_EXTERNAL_DECLARATION_REVIEW
    ),
    inputs: tuple[WaveFiveDeclarationInputRecord, ...] | None = None,
    checks: tuple[WaveFiveBoundedDeclarationCheck, ...] | None = None,
    blockers: tuple[WaveFiveBoundedDeclarationBlocker, ...] = (),
    reviewer_ids: tuple[str, ...] = (),
    human_signoff_ids: tuple[str, ...] = ("human-signoff-001",),
    attempted_wave_six_promotion: bool = False,
    claims_agi: bool = False,
    grants_execution_authority: bool = False,
    claims_production_ready: bool = False,
    claims_certified: bool = False,
    claims_independent_validation: bool = False,
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    ),
) -> WaveFiveBoundedDeclaration:
    resolved_inputs = required_inputs() if inputs is None else inputs
    resolved_checks = required_checks() if checks is None else checks
    return WaveFiveBoundedDeclaration(
        declaration_id="wave5-bounded-declaration-001",
        title="Bounded Wave 5 declaration for external review readiness.",
        source_system=source_system,
        declaration_state=declaration_state,
        inputs=resolved_inputs,
        checks=resolved_checks,
        blockers=blockers,
        protocol_ids=("wave5-external-protocol-001",),
        reviewer_ids=reviewer_ids,
        human_signoff_ids=human_signoff_ids,
        attempted_wave_six_promotion=attempted_wave_six_promotion,
        claims_agi=claims_agi,
        grants_execution_authority=grants_execution_authority,
        claims_production_ready=claims_production_ready,
        claims_certified=claims_certified,
        claims_independent_validation=claims_independent_validation,
        claim_boundaries=claim_boundaries,
        notes=("Declaration says bounded Wave 5 review package, not Wave 6.",),
    )


def test_required_declaration_inputs_are_locked() -> None:
    assert required_declaration_input_kinds() == REQUIRED_DECLARATION_INPUT_KINDS
    assert len(REQUIRED_DECLARATION_INPUT_KINDS) == 12
    assert WaveFiveDeclarationInputKind.RELEASE_MANIFEST in (
        REQUIRED_DECLARATION_INPUT_KINDS
    )
    assert WaveFiveDeclarationInputKind.ECOSYSTEM_BRIDGE_PROOFS in (
        REQUIRED_DECLARATION_INPUT_KINDS
    )


def test_required_declaration_checks_are_locked() -> None:
    assert required_declaration_check_kinds() == REQUIRED_DECLARATION_CHECK_KINDS
    assert len(REQUIRED_DECLARATION_CHECK_KINDS) == 12
    assert WaveFiveDeclarationCheckKind.NO_WAVE_SIX_PROMOTION in (
        REQUIRED_DECLARATION_CHECK_KINDS
    )
    assert WaveFiveDeclarationCheckKind.NO_EXECUTION_AUTHORITY in (
        REQUIRED_DECLARATION_CHECK_KINDS
    )


def test_safe_and_blocking_input_statuses_are_locked() -> None:
    assert safe_declaration_input_statuses() == SAFE_DECLARATION_INPUT_STATUSES
    assert blocking_declaration_input_statuses() == (
        BLOCKING_DECLARATION_INPUT_STATUSES
    )
    assert WaveFiveDeclarationInputStatus.REVIEWABLE in (
        SAFE_DECLARATION_INPUT_STATUSES
    )
    assert WaveFiveDeclarationInputStatus.DISPUTED in (
        BLOCKING_DECLARATION_INPUT_STATUSES
    )


def test_external_declaration_review_sources_are_locked() -> None:
    assert external_declaration_review_source_systems() == (
        EXTERNAL_DECLARATION_REVIEW_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.INDEPENDENT_REVIEWER in (
        EXTERNAL_DECLARATION_REVIEW_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.IX_COGNITION_KERNEL not in (
        EXTERNAL_DECLARATION_REVIEW_SOURCE_SYSTEMS
    )


def test_input_record_requires_valid_digest_and_evidence() -> None:
    with pytest.raises(ValueError, match="64-character"):
        input_record(digest="not-a-digest")

    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveDeclarationInputRecord(
            input_id="input-invalid",
            input_kind=WaveFiveDeclarationInputKind.RELEASE_MANIFEST,
            status=WaveFiveDeclarationInputStatus.REVIEWABLE,
            digest=DIGEST_A,
            evidence_ids=(),
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
            summary="Invalid input.",
        )


def test_limited_input_record_requires_limitations() -> None:
    with pytest.raises(ValueError, match="require limitations"):
        input_record(status=WaveFiveDeclarationInputStatus.REVIEWABLE_WITH_LIMITS)


def test_input_record_rejects_missing_claim_boundary() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        input_record(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_blocking_input_status_blocks_declaration_readiness() -> None:
    item = input_record(status=WaveFiveDeclarationInputStatus.DISPUTED)

    assert item.blocks_declaration_readiness is True
    assert item.reviewable_with_boundaries is False


def test_declaration_check_requires_evidence() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveBoundedDeclarationCheck(
            check_id="check-invalid",
            check_kind=WaveFiveDeclarationCheckKind.NO_WAVE_SIX_PROMOTION,
            result=WaveFiveDeclarationCheckResult.PASSED,
            description="Invalid check without evidence.",
            evidence_ids=(),
        )


def test_failed_declaration_check_blocks_readiness() -> None:
    item = declaration_check(
        "check-failed",
        WaveFiveDeclarationCheckKind.NO_AGI_OR_CERTIFICATION_CLAIM,
        result=WaveFiveDeclarationCheckResult.FAILED,
    )

    assert item.passed_with_boundaries is False
    assert item.blocks_declaration_readiness is True


def test_non_blocking_declaration_check_does_not_block_readiness() -> None:
    item = declaration_check(
        "check-warning",
        WaveFiveDeclarationCheckKind.INPUT_DIGESTS_PRESENT,
        result=WaveFiveDeclarationCheckResult.NEEDS_MORE_EVIDENCE,
        blocking=False,
    )

    assert item.blocks_declaration_readiness is False


def test_declaration_blocker_requires_evidence() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveBoundedDeclarationBlocker(
            blocker_id="blocker-invalid",
            blocker_kind=WaveFiveDeclarationBlockerKind.MISSING_INPUT,
            severity=WaveFiveDeclarationBlockerSeverity.BLOCKING,
            input_kind=WaveFiveDeclarationInputKind.RELEASE_MANIFEST,
            description="Invalid blocker.",
            mitigation="Resolve blocker.",
            evidence_ids=(),
        )


def test_unresolved_blocking_declaration_blocker_blocks_readiness() -> None:
    item = blocker(severity=WaveFiveDeclarationBlockerSeverity.BLOCKING)

    assert item.blocks_declaration_readiness is True


def test_resolved_blocking_declaration_blocker_does_not_block_readiness() -> None:
    item = blocker(
        severity=WaveFiveDeclarationBlockerSeverity.BLOCKING,
        resolved=True,
    )

    assert item.blocks_declaration_readiness is False


def test_declaration_rejects_forbidden_claim_flags() -> None:
    with pytest.raises(ValueError, match="cannot promote to Wave 6"):
        declaration(attempted_wave_six_promotion=True)

    with pytest.raises(ValueError, match="cannot claim AGI"):
        declaration(claims_agi=True)

    with pytest.raises(ValueError, match="cannot grant execution authority"):
        declaration(grants_execution_authority=True)


def test_declaration_rejects_production_certification_and_independent_claims() -> None:
    with pytest.raises(ValueError, match="production readiness"):
        declaration(claims_production_ready=True)

    with pytest.raises(ValueError, match="certification"):
        declaration(claims_certified=True)

    with pytest.raises(ValueError, match="independent validation"):
        declaration(claims_independent_validation=True)


def test_declaration_rejects_missing_claim_boundary() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        declaration(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_declaration_reports_missing_required_inputs_and_checks() -> None:
    item = declaration(
        inputs=(input_record(),),
        checks=(
            declaration_check(
                "check-required-inputs-present",
                WaveFiveDeclarationCheckKind.REQUIRED_INPUTS_PRESENT,
            ),
        ),
    )

    assert item.has_required_input_coverage is False
    assert WaveFiveDeclarationInputKind.ECOSYSTEM_BRIDGE_PROOFS in (
        item.missing_required_input_kinds
    )
    assert item.has_required_check_coverage is False
    assert WaveFiveDeclarationCheckKind.NO_WAVE_SIX_PROMOTION in (
        item.missing_required_check_kinds
    )
    assert item.ready_for_external_declaration_review is False


def test_declaration_blocks_when_input_status_is_blocking() -> None:
    inputs = tuple(
        input_record(
            f"input-{input_kind.value}",
            input_kind=input_kind,
            status=(
                WaveFiveDeclarationInputStatus.DISPUTED
                if input_kind is WaveFiveDeclarationInputKind.REPEATABILITY_LEDGER
                else WaveFiveDeclarationInputStatus.REVIEWABLE
            ),
            digest=(DIGEST_A if index % 2 == 0 else DIGEST_B),
        )
        for index, input_kind in enumerate(REQUIRED_DECLARATION_INPUT_KINDS)
    )
    item = declaration(inputs=inputs)

    assert item.blocking_input_ids == ("input-repeatability-ledger",)
    assert item.blocks_declaration_readiness is True


def test_declaration_blocks_when_check_fails() -> None:
    checks = tuple(
        declaration_check(
            f"check-{check_kind.value}",
            check_kind,
            result=(
                WaveFiveDeclarationCheckResult.FAILED
                if check_kind is WaveFiveDeclarationCheckKind.NO_WAVE_SIX_PROMOTION
                else WaveFiveDeclarationCheckResult.PASSED
            ),
        )
        for check_kind in REQUIRED_DECLARATION_CHECK_KINDS
    )
    item = declaration(checks=checks)

    assert item.blocking_check_ids == ("check-no-wave-six-promotion",)
    assert item.blocks_declaration_readiness is True


def test_declaration_blocks_when_unresolved_blocker_exists() -> None:
    item = declaration(
        blockers=(blocker(severity=WaveFiveDeclarationBlockerSeverity.BLOCKING),)
    )

    assert item.unresolved_blocker_ids == ("blocker-release-manifest",)
    assert item.blocks_declaration_readiness is True


def test_declaration_blocks_without_human_signoff() -> None:
    item = declaration(human_signoff_ids=())

    assert item.has_human_signoff is False
    assert item.blocks_declaration_readiness is True
    assert item.ready_for_external_declaration_review is False


def test_declaration_is_ready_for_external_review() -> None:
    item = declaration(blockers=(blocker(),))

    assert item.has_required_input_coverage is True
    assert item.has_required_check_coverage is True
    assert item.blocking_input_ids == ()
    assert item.blocking_check_ids == ()
    assert item.unresolved_blocker_ids == ()
    assert item.has_human_signoff is True
    assert item.makes_no_forbidden_claims is True
    assert item.blocks_declaration_readiness is False
    assert item.ready_for_external_declaration_review is True


def test_declaration_bundle_digest_is_deterministic() -> None:
    item = declaration()

    assert item.declaration_bundle_digest == item.declaration_bundle_digest
    assert len(item.declaration_bundle_digest) == 64


def test_ready_declaration_exports_reviewable_traceability_artifact() -> None:
    artifact = declaration().to_artifact_ref()

    assert artifact.kind is WaveFiveArtifactKind.ECOSYSTEM_TRACEABILITY_MAP
    assert artifact.capability_area is WaveFiveCapabilityArea.ECOSYSTEM_TRACEABILITY
    assert artifact.source_system is WaveFiveSourceSystem.IX_COGNITION_KERNEL
    assert artifact.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    assert artifact.authority_state is WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    )


def test_blocked_declaration_exports_blocked_artifact() -> None:
    artifact = declaration(
        blockers=(blocker(severity=WaveFiveDeclarationBlockerSeverity.BLOCKING),)
    ).to_artifact_ref()

    assert artifact.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact.authority_state is WaveFiveAuthorityState.BLOCKED
    assert artifact.validation_status is WaveFiveValidationStatus.REJECTED


def test_externally_reviewed_declaration_requires_external_source() -> None:
    with pytest.raises(ValueError, match="external source"):
        declaration(
            declaration_state=(
                WaveFiveBoundedDeclarationState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
            reviewer_ids=("reviewer-001",),
        )


def test_externally_reviewed_declaration_requires_reviewer_ids() -> None:
    with pytest.raises(ValueError, match="reviewer ids"):
        declaration(
            source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
            declaration_state=(
                WaveFiveBoundedDeclarationState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
        )


def test_externally_reviewed_declaration_exports_bounded_external_artifact() -> None:
    item = declaration(
        source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
        declaration_state=(
            WaveFiveBoundedDeclarationState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
        ),
        reviewer_ids=("reviewer-001",),
    )
    artifact = item.to_artifact_ref()

    assert item.externally_reviewed_with_boundaries is True
    assert artifact.decision is WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
    )
    assert artifact.externally_validated_with_boundaries is True


def test_declaration_collects_unique_evidence_ids() -> None:
    item = declaration(blockers=(blocker(),))

    assert "evidence-input-release-manifest" in item.all_evidence_ids
    assert "evidence-input-ecosystem-bridge-proofs" in item.all_evidence_ids
    assert "evidence-check-no-wave-six-promotion" in item.all_evidence_ids
    assert "evidence-blocker-release-manifest" in item.all_evidence_ids
    assert len(item.all_evidence_ids) == 25


def test_declaration_fingerprint_is_deterministic() -> None:
    item = declaration()

    assert item.fingerprint() == item.fingerprint()
    assert len(item.fingerprint()) == 64
