import pytest

from ix_cognition_kernel.wave5_completion_gate import (
    BLOCKING_COMPLETION_ARTIFACT_STATUSES,
    EXTERNAL_COMPLETION_REVIEW_SOURCE_SYSTEMS,
    REQUIRED_COMPLETION_ARTIFACT_KINDS,
    REQUIRED_COMPLETION_CHECK_KINDS,
    SAFE_COMPLETION_ARTIFACT_STATUSES,
    WaveFiveCompletionArtifactKind,
    WaveFiveCompletionArtifactRecord,
    WaveFiveCompletionArtifactStatus,
    WaveFiveCompletionBlocker,
    WaveFiveCompletionBlockerKind,
    WaveFiveCompletionBlockerSeverity,
    WaveFiveCompletionCheck,
    WaveFiveCompletionCheckKind,
    WaveFiveCompletionCheckResult,
    WaveFiveCompletionGate,
    WaveFiveCompletionState,
    blocking_completion_artifact_statuses,
    external_completion_review_source_systems,
    required_completion_artifact_kinds,
    required_completion_check_kinds,
    safe_completion_artifact_statuses,
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
REVIEW_INDEX_ARTIFACT_ID = "wave5-review-index-001"
BOUNDED_DECLARATION_ARTIFACT_ID = "wave5-bounded-declaration-001"


def artifact_record(
    artifact_id: str = REVIEW_INDEX_ARTIFACT_ID,
    *,
    artifact_kind: WaveFiveCompletionArtifactKind = (
        WaveFiveCompletionArtifactKind.REVIEW_INDEX
    ),
    status: WaveFiveCompletionArtifactStatus = (
        WaveFiveCompletionArtifactStatus.COMPLETE
    ),
    digest: str = DIGEST_A,
    limitations: tuple[str, ...] = (),
    blocker_ids: tuple[str, ...] = (),
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    ),
) -> WaveFiveCompletionArtifactRecord:
    return WaveFiveCompletionArtifactRecord(
        artifact_id=artifact_id,
        artifact_kind=artifact_kind,
        status=status,
        digest=digest,
        evidence_ids=(f"evidence-{artifact_id}",),
        source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
        summary="Completion artifact is evidence-bound and reviewable.",
        limitations=limitations,
        blocker_ids=blocker_ids,
        claim_boundaries=claim_boundaries,
    )


def completion_check(
    check_id: str,
    check_kind: WaveFiveCompletionCheckKind,
    *,
    result: WaveFiveCompletionCheckResult = WaveFiveCompletionCheckResult.PASSED,
    blocking: bool = True,
) -> WaveFiveCompletionCheck:
    return WaveFiveCompletionCheck(
        check_id=check_id,
        check_kind=check_kind,
        result=result,
        description="Completion check preserves bounded Wave 5 claim limits.",
        evidence_ids=(f"evidence-{check_id}",),
        blocking=blocking,
    )


def blocker(
    blocker_id: str = "blocker-review-index",
    *,
    artifact_kind: WaveFiveCompletionArtifactKind = (
        WaveFiveCompletionArtifactKind.REVIEW_INDEX
    ),
    blocker_kind: WaveFiveCompletionBlockerKind = (
        WaveFiveCompletionBlockerKind.REVIEW_INDEX_GAP
    ),
    severity: WaveFiveCompletionBlockerSeverity = (
        WaveFiveCompletionBlockerSeverity.LIMITATION
    ),
    resolved: bool = False,
) -> WaveFiveCompletionBlocker:
    return WaveFiveCompletionBlocker(
        blocker_id=blocker_id,
        blocker_kind=blocker_kind,
        severity=severity,
        artifact_kind=artifact_kind,
        description="Completion blocker remains visible to reviewers.",
        mitigation="Resolve blocker or preserve it as a visible limitation.",
        evidence_ids=(f"evidence-{blocker_id}",),
        resolved=resolved,
    )


def required_artifacts() -> tuple[WaveFiveCompletionArtifactRecord, ...]:
    records: list[WaveFiveCompletionArtifactRecord] = []
    for index, artifact_kind in enumerate(REQUIRED_COMPLETION_ARTIFACT_KINDS):
        artifact_id = f"wave5-{artifact_kind.value}-001"
        if artifact_kind is WaveFiveCompletionArtifactKind.REVIEW_INDEX:
            artifact_id = REVIEW_INDEX_ARTIFACT_ID
        elif artifact_kind is WaveFiveCompletionArtifactKind.BOUNDED_DECLARATION:
            artifact_id = BOUNDED_DECLARATION_ARTIFACT_ID
        records.append(
            artifact_record(
                artifact_id,
                artifact_kind=artifact_kind,
                status=WaveFiveCompletionArtifactStatus.COMPLETE_WITH_LIMITS,
                digest=(DIGEST_A if index % 2 == 0 else DIGEST_B),
                limitations=("Bounded Wave 5 completion only; not Wave 6 proof.",),
            )
        )
    return tuple(records)


def required_checks() -> tuple[WaveFiveCompletionCheck, ...]:
    return tuple(
        completion_check(f"check-{check_kind.value}", check_kind)
        for check_kind in REQUIRED_COMPLETION_CHECK_KINDS
    )


def completion_gate(
    *,
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    completion_state: WaveFiveCompletionState = (
        WaveFiveCompletionState.READY_FOR_EXTERNAL_COMPLETION_REVIEW
    ),
    artifacts: tuple[WaveFiveCompletionArtifactRecord, ...] | None = None,
    checks: tuple[WaveFiveCompletionCheck, ...] | None = None,
    blockers: tuple[WaveFiveCompletionBlocker, ...] = (),
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
) -> WaveFiveCompletionGate:
    resolved_artifacts = required_artifacts() if artifacts is None else artifacts
    resolved_checks = required_checks() if checks is None else checks
    return WaveFiveCompletionGate(
        completion_id="wave5-completion-gate-001",
        title="Bounded Wave 5 completion gate for external review readiness.",
        source_system=source_system,
        completion_state=completion_state,
        artifacts=resolved_artifacts,
        checks=resolved_checks,
        blockers=blockers,
        review_index_artifact_id=REVIEW_INDEX_ARTIFACT_ID,
        bounded_declaration_artifact_id=BOUNDED_DECLARATION_ARTIFACT_ID,
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
        notes=("Completion means bounded Wave 5 package, not Wave 6.",),
    )


def test_required_completion_artifacts_are_locked() -> None:
    assert required_completion_artifact_kinds() == REQUIRED_COMPLETION_ARTIFACT_KINDS
    assert len(REQUIRED_COMPLETION_ARTIFACT_KINDS) == 15
    assert WaveFiveCompletionArtifactKind.REVIEW_INDEX in (
        REQUIRED_COMPLETION_ARTIFACT_KINDS
    )
    assert WaveFiveCompletionArtifactKind.BENCHMARK_GAMING_AUDIT in (
        REQUIRED_COMPLETION_ARTIFACT_KINDS
    )


def test_required_completion_checks_are_locked() -> None:
    assert required_completion_check_kinds() == REQUIRED_COMPLETION_CHECK_KINDS
    assert len(REQUIRED_COMPLETION_CHECK_KINDS) == 14
    assert WaveFiveCompletionCheckKind.NO_WAVE_SIX_PROMOTION in (
        REQUIRED_COMPLETION_CHECK_KINDS
    )
    assert WaveFiveCompletionCheckKind.NO_EXECUTION_AUTHORITY in (
        REQUIRED_COMPLETION_CHECK_KINDS
    )


def test_safe_and_blocking_completion_statuses_are_locked() -> None:
    assert safe_completion_artifact_statuses() == SAFE_COMPLETION_ARTIFACT_STATUSES
    assert blocking_completion_artifact_statuses() == (
        BLOCKING_COMPLETION_ARTIFACT_STATUSES
    )
    assert WaveFiveCompletionArtifactStatus.COMPLETE in (
        SAFE_COMPLETION_ARTIFACT_STATUSES
    )
    assert WaveFiveCompletionArtifactStatus.DISPUTED in (
        BLOCKING_COMPLETION_ARTIFACT_STATUSES
    )


def test_external_completion_review_sources_are_locked() -> None:
    assert external_completion_review_source_systems() == (
        EXTERNAL_COMPLETION_REVIEW_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.INDEPENDENT_REVIEWER in (
        EXTERNAL_COMPLETION_REVIEW_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.IX_COGNITION_KERNEL not in (
        EXTERNAL_COMPLETION_REVIEW_SOURCE_SYSTEMS
    )


def test_artifact_record_requires_valid_digest_and_evidence() -> None:
    with pytest.raises(ValueError, match="64-character"):
        artifact_record(digest="not-a-digest")

    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveCompletionArtifactRecord(
            artifact_id="artifact-invalid",
            artifact_kind=WaveFiveCompletionArtifactKind.REVIEW_INDEX,
            status=WaveFiveCompletionArtifactStatus.COMPLETE,
            digest=DIGEST_A,
            evidence_ids=(),
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
            summary="Invalid artifact.",
        )


def test_limited_artifact_requires_limitations() -> None:
    with pytest.raises(ValueError, match="require limitations"):
        artifact_record(status=WaveFiveCompletionArtifactStatus.COMPLETE_WITH_LIMITS)


def test_blocking_artifact_requires_blocker_ids() -> None:
    with pytest.raises(ValueError, match="require blocker ids"):
        artifact_record(status=WaveFiveCompletionArtifactStatus.DISPUTED)


def test_artifact_record_rejects_missing_claim_boundary() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        artifact_record(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_blocking_artifact_status_blocks_completion() -> None:
    item = artifact_record(
        status=WaveFiveCompletionArtifactStatus.DISPUTED,
        blocker_ids=("blocker-001",),
    )

    assert item.blocks_completion is True
    assert item.complete_with_boundaries is False


def test_completion_check_requires_evidence() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveCompletionCheck(
            check_id="check-invalid",
            check_kind=WaveFiveCompletionCheckKind.NO_WAVE_SIX_PROMOTION,
            result=WaveFiveCompletionCheckResult.PASSED,
            description="Invalid check without evidence.",
            evidence_ids=(),
        )


def test_failed_completion_check_blocks_completion() -> None:
    item = completion_check(
        "check-failed",
        WaveFiveCompletionCheckKind.NO_AGI_OR_CERTIFICATION_CLAIM,
        result=WaveFiveCompletionCheckResult.FAILED,
    )

    assert item.passed_with_boundaries is False
    assert item.blocks_completion is True


def test_non_blocking_completion_check_does_not_block_completion() -> None:
    item = completion_check(
        "check-warning",
        WaveFiveCompletionCheckKind.FINAL_DIGESTS_PRESENT,
        result=WaveFiveCompletionCheckResult.NEEDS_MORE_EVIDENCE,
        blocking=False,
    )

    assert item.blocks_completion is False


def test_completion_blocker_requires_evidence() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveCompletionBlocker(
            blocker_id="blocker-invalid",
            blocker_kind=WaveFiveCompletionBlockerKind.MISSING_FINAL_ARTIFACT,
            severity=WaveFiveCompletionBlockerSeverity.BLOCKING,
            artifact_kind=WaveFiveCompletionArtifactKind.REVIEW_INDEX,
            description="Invalid blocker.",
            mitigation="Resolve blocker.",
            evidence_ids=(),
        )


def test_unresolved_blocking_completion_blocker_blocks_completion() -> None:
    item = blocker(severity=WaveFiveCompletionBlockerSeverity.BLOCKING)

    assert item.blocks_completion is True


def test_resolved_blocking_completion_blocker_does_not_block_completion() -> None:
    item = blocker(severity=WaveFiveCompletionBlockerSeverity.BLOCKING, resolved=True)

    assert item.blocks_completion is False


def test_gate_rejects_review_index_reference_mismatch() -> None:
    artifacts = tuple(
        artifact_record(
            item.artifact_id,
            artifact_kind=item.artifact_kind,
            status=item.status,
            digest=item.digest,
            limitations=item.limitations,
        )
        for item in required_artifacts()
        if item.artifact_kind is not WaveFiveCompletionArtifactKind.REVIEW_INDEX
    ) + (
        artifact_record(
            "wrong-review-index-id",
            artifact_kind=WaveFiveCompletionArtifactKind.REVIEW_INDEX,
            status=WaveFiveCompletionArtifactStatus.COMPLETE,
        ),
    )

    with pytest.raises(ValueError, match="review index reference"):
        completion_gate(artifacts=artifacts)


def test_gate_rejects_bounded_declaration_reference_mismatch() -> None:
    artifacts = tuple(
        artifact_record(
            item.artifact_id,
            artifact_kind=item.artifact_kind,
            status=item.status,
            digest=item.digest,
            limitations=item.limitations,
        )
        for item in required_artifacts()
        if item.artifact_kind
        is not WaveFiveCompletionArtifactKind.BOUNDED_DECLARATION
    ) + (
        artifact_record(
            "wrong-declaration-id",
            artifact_kind=WaveFiveCompletionArtifactKind.BOUNDED_DECLARATION,
            status=WaveFiveCompletionArtifactStatus.COMPLETE,
        ),
    )

    with pytest.raises(ValueError, match="bounded declaration reference"):
        completion_gate(artifacts=artifacts)


def test_gate_rejects_forbidden_claim_flags() -> None:
    with pytest.raises(ValueError, match="cannot promote to Wave 6"):
        completion_gate(attempted_wave_six_promotion=True)

    with pytest.raises(ValueError, match="cannot claim AGI"):
        completion_gate(claims_agi=True)

    with pytest.raises(ValueError, match="cannot grant execution authority"):
        completion_gate(grants_execution_authority=True)


def test_gate_rejects_production_certification_and_independent_claims() -> None:
    with pytest.raises(ValueError, match="production readiness"):
        completion_gate(claims_production_ready=True)

    with pytest.raises(ValueError, match="certification"):
        completion_gate(claims_certified=True)

    with pytest.raises(ValueError, match="independent validation"):
        completion_gate(claims_independent_validation=True)


def test_gate_rejects_missing_claim_boundary() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        completion_gate(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_gate_reports_missing_required_artifacts_and_checks() -> None:
    item = completion_gate(
        artifacts=(artifact_record(),),
        checks=(
            completion_check(
                "check-required-artifacts-present",
                WaveFiveCompletionCheckKind.REQUIRED_ARTIFACTS_PRESENT,
            ),
        ),
    )

    assert item.has_required_artifact_coverage is False
    assert WaveFiveCompletionArtifactKind.BENCHMARK_GAMING_AUDIT in (
        item.missing_required_artifact_kinds
    )
    assert item.has_required_check_coverage is False
    assert WaveFiveCompletionCheckKind.NO_WAVE_SIX_PROMOTION in (
        item.missing_required_check_kinds
    )
    assert item.ready_for_external_completion_review is False


def test_gate_blocks_when_artifact_status_is_blocking() -> None:
    artifacts = tuple(
        artifact_record(
            f"wave5-{artifact_kind.value}-001"
            if artifact_kind not in {
                WaveFiveCompletionArtifactKind.REVIEW_INDEX,
                WaveFiveCompletionArtifactKind.BOUNDED_DECLARATION,
            }
            else REVIEW_INDEX_ARTIFACT_ID
            if artifact_kind is WaveFiveCompletionArtifactKind.REVIEW_INDEX
            else BOUNDED_DECLARATION_ARTIFACT_ID,
            artifact_kind=artifact_kind,
            status=(
                WaveFiveCompletionArtifactStatus.DISPUTED
                if artifact_kind is WaveFiveCompletionArtifactKind.FALSIFICATION_LEDGER
                else WaveFiveCompletionArtifactStatus.COMPLETE
            ),
            digest=(DIGEST_A if index % 2 == 0 else DIGEST_B),
            blocker_ids=(
                ("blocker-falsification",)
                if artifact_kind is WaveFiveCompletionArtifactKind.FALSIFICATION_LEDGER
                else ()
            ),
        )
        for index, artifact_kind in enumerate(REQUIRED_COMPLETION_ARTIFACT_KINDS)
    )
    item = completion_gate(artifacts=artifacts)

    assert item.blocking_artifact_ids == ("wave5-falsification-ledger-001",)
    assert item.blocks_completion is True


def test_gate_blocks_when_check_fails() -> None:
    checks = tuple(
        completion_check(
            f"check-{check_kind.value}",
            check_kind,
            result=(
                WaveFiveCompletionCheckResult.FAILED
                if check_kind is WaveFiveCompletionCheckKind.NO_WAVE_SIX_PROMOTION
                else WaveFiveCompletionCheckResult.PASSED
            ),
        )
        for check_kind in REQUIRED_COMPLETION_CHECK_KINDS
    )
    item = completion_gate(checks=checks)

    assert item.blocking_check_ids == ("check-no-wave-six-promotion",)
    assert item.blocks_completion is True


def test_gate_blocks_when_unresolved_blocker_exists() -> None:
    item = completion_gate(
        blockers=(blocker(severity=WaveFiveCompletionBlockerSeverity.BLOCKING),)
    )

    assert item.unresolved_blocker_ids == ("blocker-review-index",)
    assert item.blocks_completion is True


def test_gate_blocks_without_human_signoff() -> None:
    item = completion_gate(human_signoff_ids=())

    assert item.has_human_signoff is False
    assert item.blocks_completion is True
    assert item.ready_for_external_completion_review is False


def test_gate_is_ready_for_external_completion_review() -> None:
    item = completion_gate(blockers=(blocker(),))

    assert item.has_required_artifact_coverage is True
    assert item.has_required_check_coverage is True
    assert item.blocking_artifact_ids == ()
    assert item.blocking_check_ids == ()
    assert item.unresolved_blocker_ids == ()
    assert item.has_human_signoff is True
    assert item.makes_no_forbidden_claims is True
    assert item.blocks_completion is False
    assert item.ready_for_external_completion_review is True


def test_completion_bundle_digest_is_deterministic() -> None:
    item = completion_gate()

    assert item.completion_bundle_digest == item.completion_bundle_digest
    assert len(item.completion_bundle_digest) == 64


def test_ready_gate_exports_reviewable_traceability_artifact() -> None:
    artifact = completion_gate().to_artifact_ref()

    assert artifact.kind is WaveFiveArtifactKind.ECOSYSTEM_TRACEABILITY_MAP
    assert artifact.capability_area is WaveFiveCapabilityArea.ECOSYSTEM_TRACEABILITY
    assert artifact.source_system is WaveFiveSourceSystem.IX_COGNITION_KERNEL
    assert artifact.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    assert artifact.authority_state is WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    )


def test_blocked_gate_exports_blocked_artifact() -> None:
    artifact = completion_gate(
        blockers=(blocker(severity=WaveFiveCompletionBlockerSeverity.BLOCKING),)
    ).to_artifact_ref()

    assert artifact.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact.authority_state is WaveFiveAuthorityState.BLOCKED
    assert artifact.validation_status is WaveFiveValidationStatus.REJECTED


def test_externally_reviewed_gate_requires_external_source() -> None:
    with pytest.raises(ValueError, match="external source"):
        completion_gate(
            completion_state=(
                WaveFiveCompletionState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
            reviewer_ids=("reviewer-001",),
        )


def test_externally_reviewed_gate_requires_reviewer_ids() -> None:
    with pytest.raises(ValueError, match="reviewer ids"):
        completion_gate(
            source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
            completion_state=(
                WaveFiveCompletionState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
        )


def test_externally_reviewed_gate_exports_bounded_external_artifact() -> None:
    item = completion_gate(
        source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
        completion_state=WaveFiveCompletionState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
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
    item = completion_gate(blockers=(blocker(),))

    assert "evidence-wave5-review-index-001" in item.all_evidence_ids
    assert "evidence-wave5-benchmark-gaming-audit-001" in item.all_evidence_ids
    assert "evidence-check-no-wave-six-promotion" in item.all_evidence_ids
    assert "evidence-blocker-review-index" in item.all_evidence_ids
    assert len(item.all_evidence_ids) == 30


def test_gate_fingerprint_is_deterministic() -> None:
    item = completion_gate()

    assert item.fingerprint() == item.fingerprint()
    assert len(item.fingerprint()) == 64
