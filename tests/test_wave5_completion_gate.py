import pytest

from ix_cognition_kernel.wave5_completion_gate import (
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
    WaveFiveArtifactDecision,
    WaveFiveAuthorityState,
    WaveFiveSourceSystem,
    WaveFiveValidationStatus,
)

DIGEST = "a" * 64


def _completion_artifacts(
    status: WaveFiveCompletionArtifactStatus = WaveFiveCompletionArtifactStatus.COMPLETE,
) -> tuple[WaveFiveCompletionArtifactRecord, ...]:
    return tuple(
        WaveFiveCompletionArtifactRecord(
            artifact_id=f"artifact-{artifact_kind.value}",
            artifact_kind=artifact_kind,
            status=status,
            digest=DIGEST,
            evidence_ids=(f"evidence-{artifact_kind.value}",),
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
            summary=f"Completion artifact for {artifact_kind.value}",
            blocker_ids=(
                (f"blocker-{artifact_kind.value}",)
                if status in blocking_completion_artifact_statuses()
                else ()
            ),
            limitations=(
                (f"limited-{artifact_kind.value}",)
                if status is WaveFiveCompletionArtifactStatus.COMPLETE_WITH_LIMITS
                else ()
            ),
        )
        for artifact_kind in required_completion_artifact_kinds()
    )


def _completion_checks(
    result: WaveFiveCompletionCheckResult = WaveFiveCompletionCheckResult.PASSED,
) -> tuple[WaveFiveCompletionCheck, ...]:
    return tuple(
        WaveFiveCompletionCheck(
            check_id=f"check-{check_kind.value}",
            check_kind=check_kind,
            result=result,
            description=f"Completion check for {check_kind.value}",
            evidence_ids=(f"check-evidence-{check_kind.value}",),
        )
        for check_kind in required_completion_check_kinds()
    )


def _completion_gate(
    *,
    state: WaveFiveCompletionState = (
        WaveFiveCompletionState.READY_FOR_EXTERNAL_COMPLETION_REVIEW
    ),
    artifacts: tuple[WaveFiveCompletionArtifactRecord, ...] | None = None,
    checks: tuple[WaveFiveCompletionCheck, ...] | None = None,
    blockers: tuple[WaveFiveCompletionBlocker, ...] = (),
    human_signoff_ids: tuple[str, ...] = ("human-signoff-1",),
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
) -> WaveFiveCompletionGate:
    return WaveFiveCompletionGate(
        completion_id="completion-gate-1",
        title="Wave 5 bounded completion gate",
        source_system=source_system,
        completion_state=state,
        artifacts=artifacts or _completion_artifacts(),
        checks=checks or _completion_checks(),
        blockers=blockers,
        review_index_artifact_id="artifact-review-index",
        bounded_declaration_artifact_id="artifact-bounded-declaration",
        protocol_ids=("protocol-1",),
        reviewer_ids=("reviewer-1",) if source_system != WaveFiveSourceSystem.IX_COGNITION_KERNEL else (),
        human_signoff_ids=human_signoff_ids,
    )


def test_required_completion_sets_are_locked() -> None:
    assert len(required_completion_artifact_kinds()) >= 10
    assert len(required_completion_check_kinds()) >= 10
    assert WaveFiveCompletionArtifactStatus.COMPLETE in safe_completion_artifact_statuses()
    assert (
        WaveFiveCompletionArtifactStatus.MISSING
        in blocking_completion_artifact_statuses()
    )
    assert (
        WaveFiveSourceSystem.EXTERNAL_REVIEW
        in external_completion_review_source_systems()
    )


def test_completion_gate_ready_for_external_review_when_all_inputs_pass() -> None:
    gate = _completion_gate()

    assert gate.has_required_artifact_coverage
    assert gate.has_required_check_coverage
    assert gate.has_human_signoff
    assert gate.ready_for_external_completion_review
    assert not gate.blocks_completion
    assert gate.blocking_artifact_ids == ()
    assert gate.blocking_check_ids == ()
    assert gate.unresolved_blocker_ids == ()

    artifact_ref = gate.to_artifact_ref()
    assert artifact_ref.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    assert artifact_ref.authority_state is WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    assert artifact_ref.validation_status is WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    assert artifact_ref.evidence_ids == gate.all_evidence_ids


def test_completion_gate_blocks_without_human_signoff() -> None:
    gate = _completion_gate(human_signoff_ids=())

    assert gate.blocks_completion
    assert not gate.ready_for_external_completion_review

    artifact_ref = gate.to_artifact_ref()
    assert artifact_ref.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact_ref.authority_state is WaveFiveAuthorityState.BLOCKED
    assert artifact_ref.validation_status is WaveFiveValidationStatus.REJECTED


def test_completion_gate_blocks_unresolved_blocker() -> None:
    blocker = WaveFiveCompletionBlocker(
        blocker_id="blocker-1",
        blocker_kind=WaveFiveCompletionBlockerKind.MISSING_FINAL_ARTIFACT,
        severity=WaveFiveCompletionBlockerSeverity.BLOCKING,
        artifact_kind=required_completion_artifact_kinds()[0],
        description="A final artifact is missing.",
        mitigation="Provide the missing final artifact before review.",
        evidence_ids=("blocker-evidence-1",),
    )
    gate = _completion_gate(blockers=(blocker,))

    assert gate.blocks_completion
    assert gate.unresolved_blocker_ids == ("blocker-1",)
    assert not gate.ready_for_external_completion_review


def test_completion_gate_requires_review_index_reference_to_match() -> None:
    artifacts = tuple(
        artifact
        for artifact in _completion_artifacts()
        if artifact.artifact_id != "artifact-review-index"
    ) + (
        WaveFiveCompletionArtifactRecord(
            artifact_id="different-review-index",
            artifact_kind=required_completion_artifact_kinds()[0],
            status=WaveFiveCompletionArtifactStatus.COMPLETE,
            digest=DIGEST,
            evidence_ids=("replacement-evidence",),
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
            summary="Mismatched review index artifact.",
        ),
    )

    with pytest.raises(ValueError, match="review index reference"):
        _completion_gate(artifacts=artifacts)


def test_completion_gate_rejects_forbidden_claims() -> None:
    with pytest.raises(ValueError, match="cannot claim AGI"):
        WaveFiveCompletionGate(
            completion_id="completion-gate-claim",
            title="Invalid completion gate",
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
            completion_state=WaveFiveCompletionState.INTERNAL_COMPLETION_READY,
            artifacts=_completion_artifacts(),
            checks=_completion_checks(),
            blockers=(),
            review_index_artifact_id="artifact-review-index",
            bounded_declaration_artifact_id="artifact-bounded-declaration",
            protocol_ids=("protocol-1",),
            human_signoff_ids=("human-signoff-1",),
            claims_agi=True,
        )


def test_externally_reviewed_completion_gate_requires_external_source() -> None:
    with pytest.raises(ValueError, match="external source"):
        _completion_gate(
            state=WaveFiveCompletionState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
        )


def test_externally_reviewed_completion_gate_exports_reviewed_artifact() -> None:
    gate = _completion_gate(
        state=WaveFiveCompletionState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
        source_system=WaveFiveSourceSystem.EXTERNAL_REVIEW,
    )

    assert gate.externally_reviewed_with_boundaries
    artifact_ref = gate.to_artifact_ref()
    assert artifact_ref.decision is WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
    assert artifact_ref.validation_status is WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
