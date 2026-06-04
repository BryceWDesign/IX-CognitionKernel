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
from ix_cognition_kernel.wave5_repeatability import (
    BLOCKING_REPEATABILITY_OUTCOMES,
    EXTERNAL_REPEATABILITY_SOURCE_SYSTEMS,
    REQUIRED_DISAGREEMENT_KINDS,
    REQUIRED_REPEATABILITY_ATTEMPT_KINDS,
    REQUIRED_REPEATABILITY_CONTROL_KINDS,
    SAFE_REPEATABILITY_OUTCOMES,
    WaveFiveDisagreementDisposition,
    WaveFiveDisagreementKind,
    WaveFiveRepeatabilityAttempt,
    WaveFiveRepeatabilityAttemptKind,
    WaveFiveRepeatabilityControl,
    WaveFiveRepeatabilityControlKind,
    WaveFiveRepeatabilityControlResult,
    WaveFiveRepeatabilityLedger,
    WaveFiveRepeatabilityLedgerState,
    WaveFiveRepeatabilityOutcome,
    WaveFiveReviewerDisagreement,
    blocking_repeatability_outcomes,
    external_repeatability_source_systems,
    required_disagreement_kinds,
    required_repeatability_attempt_kinds,
    required_repeatability_control_kinds,
    safe_repeatability_outcomes,
)


def attempt(
    attempt_id: str = "attempt-clean-checkout-replay",
    *,
    attempt_kind: WaveFiveRepeatabilityAttemptKind = (
        WaveFiveRepeatabilityAttemptKind.CLEAN_CHECKOUT_REPLAY
    ),
    outcome: WaveFiveRepeatabilityOutcome = WaveFiveRepeatabilityOutcome.REPRODUCED,
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    reviewer_ids: tuple[str, ...] = (),
    retained_failed_output: bool = True,
) -> WaveFiveRepeatabilityAttempt:
    return WaveFiveRepeatabilityAttempt(
        attempt_id=attempt_id,
        attempt_kind=attempt_kind,
        outcome=outcome,
        source_system=source_system,
        artifact_ids=("wave5-artifact-001",),
        protocol_ids=("wave5-external-protocol-001",),
        reviewer_ids=reviewer_ids,
        environment_summary="Clean checkout replay with captured environment notes.",
        result_summary="Repeatability result is preserved without cherry-picking.",
        evidence_ids=(f"evidence-{attempt_id}",),
        retained_failed_output=retained_failed_output,
    )


def disagreement(
    disagreement_id: str = "disagreement-protocol-interpretation",
    *,
    disagreement_kind: WaveFiveDisagreementKind = (
        WaveFiveDisagreementKind.PROTOCOL_INTERPRETATION
    ),
    disposition: WaveFiveDisagreementDisposition = (
        WaveFiveDisagreementDisposition.RESOLVED_WITH_EVIDENCE
    ),
    contradictory_evidence_ids: tuple[str, ...] = (),
) -> WaveFiveReviewerDisagreement:
    return WaveFiveReviewerDisagreement(
        disagreement_id=disagreement_id,
        disagreement_kind=disagreement_kind,
        disposition=disposition,
        reviewer_ids=("reviewer-001",),
        disputed_artifact_ids=("wave5-artifact-001",),
        summary="Reviewer disagreement remains visible in the ledger.",
        resolution_summary="Resolution is evidence-linked and not erased.",
        evidence_ids=(f"evidence-{disagreement_id}",),
        contradictory_evidence_ids=contradictory_evidence_ids,
    )


def control(
    control_id: str,
    control_kind: WaveFiveRepeatabilityControlKind,
    *,
    result: WaveFiveRepeatabilityControlResult = (
        WaveFiveRepeatabilityControlResult.PASSED
    ),
    blocking: bool = True,
) -> WaveFiveRepeatabilityControl:
    return WaveFiveRepeatabilityControl(
        control_id=control_id,
        control_kind=control_kind,
        result=result,
        description="Repeatability control preserves failed attempts and dissent.",
        evidence_ids=(f"evidence-{control_id}",),
        blocking=blocking,
    )


def required_attempts() -> tuple[WaveFiveRepeatabilityAttempt, ...]:
    attempts: list[WaveFiveRepeatabilityAttempt] = []
    for kind in REQUIRED_REPEATABILITY_ATTEMPT_KINDS:
        source = WaveFiveSourceSystem.IX_COGNITION_KERNEL
        reviewers: tuple[str, ...] = ()
        if kind in {
            WaveFiveRepeatabilityAttemptKind.INDEPENDENT_LAB_REPLAY,
            WaveFiveRepeatabilityAttemptKind.EXTERNAL_REVIEWER_REPLAY,
        }:
            source = WaveFiveSourceSystem.INDEPENDENT_REPLICATION_LAB
            reviewers = ("reviewer-001",)
        attempts.append(
            attempt(
                f"attempt-{kind.value}",
                attempt_kind=kind,
                source_system=source,
                reviewer_ids=reviewers,
            )
        )
    return tuple(attempts)


def required_disagreements() -> tuple[WaveFiveReviewerDisagreement, ...]:
    return tuple(
        disagreement(
            f"disagreement-{kind.value}",
            disagreement_kind=kind,
        )
        for kind in REQUIRED_DISAGREEMENT_KINDS
    )


def required_controls() -> tuple[WaveFiveRepeatabilityControl, ...]:
    return tuple(
        control(f"control-{kind.value}", kind)
        for kind in REQUIRED_REPEATABILITY_CONTROL_KINDS
    )


def ledger(
    *,
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    ledger_state: WaveFiveRepeatabilityLedgerState = (
        WaveFiveRepeatabilityLedgerState.READY_FOR_EXTERNAL_REPEATABILITY_REVIEW
    ),
    attempts: tuple[WaveFiveRepeatabilityAttempt, ...] | None = None,
    disagreements: tuple[WaveFiveReviewerDisagreement, ...] | None = None,
    controls: tuple[WaveFiveRepeatabilityControl, ...] | None = None,
    reviewer_ids: tuple[str, ...] = (),
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    ),
) -> WaveFiveRepeatabilityLedger:
    resolved_attempts = required_attempts() if attempts is None else attempts
    resolved_disagreements = (
        required_disagreements() if disagreements is None else disagreements
    )
    resolved_controls = required_controls() if controls is None else controls
    return WaveFiveRepeatabilityLedger(
        ledger_id="wave5-repeatability-ledger-001",
        title="Wave 5 independent repeatability and disagreement ledger.",
        source_system=source_system,
        ledger_state=ledger_state,
        attempts=resolved_attempts,
        disagreements=resolved_disagreements,
        controls=resolved_controls,
        protocol_ids=("wave5-external-protocol-001",),
        reviewer_ids=reviewer_ids,
        claim_boundaries=claim_boundaries,
        notes=("Failed reproduction and dissent remain visible for Wave 6.",),
    )


def test_required_repeatability_attempt_kinds_are_locked() -> None:
    assert required_repeatability_attempt_kinds() == (
        REQUIRED_REPEATABILITY_ATTEMPT_KINDS
    )
    assert len(REQUIRED_REPEATABILITY_ATTEMPT_KINDS) == 6
    assert WaveFiveRepeatabilityAttemptKind.FAILED_REPRODUCTION_CAPTURE in (
        REQUIRED_REPEATABILITY_ATTEMPT_KINDS
    )


def test_required_disagreement_kinds_are_locked() -> None:
    assert required_disagreement_kinds() == REQUIRED_DISAGREEMENT_KINDS
    assert len(REQUIRED_DISAGREEMENT_KINDS) == 8
    assert WaveFiveDisagreementKind.WAVE_SIX_READINESS in REQUIRED_DISAGREEMENT_KINDS


def test_required_repeatability_control_kinds_are_locked() -> None:
    assert required_repeatability_control_kinds() == (
        REQUIRED_REPEATABILITY_CONTROL_KINDS
    )
    assert len(REQUIRED_REPEATABILITY_CONTROL_KINDS) == 8
    assert WaveFiveRepeatabilityControlKind.NO_CHERRY_PICKED_REPRODUCTION in (
        REQUIRED_REPEATABILITY_CONTROL_KINDS
    )


def test_safe_and_blocking_repeatability_outcomes_are_locked() -> None:
    assert safe_repeatability_outcomes() == SAFE_REPEATABILITY_OUTCOMES
    assert blocking_repeatability_outcomes() == BLOCKING_REPEATABILITY_OUTCOMES
    assert WaveFiveRepeatabilityOutcome.FAILED_TO_REPRODUCE in (
        BLOCKING_REPEATABILITY_OUTCOMES
    )


def test_external_repeatability_sources_are_locked() -> None:
    assert external_repeatability_source_systems() == (
        EXTERNAL_REPEATABILITY_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.INDEPENDENT_REPLICATION_LAB in (
        EXTERNAL_REPEATABILITY_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.IX_COGNITION_KERNEL not in (
        EXTERNAL_REPEATABILITY_SOURCE_SYSTEMS
    )


def test_external_attempt_requires_reviewer_ids() -> None:
    with pytest.raises(ValueError, match="require reviewers"):
        attempt(
            source_system=WaveFiveSourceSystem.INDEPENDENT_REPLICATION_LAB,
        )


def test_failed_attempt_must_retain_failed_output() -> None:
    with pytest.raises(ValueError, match="must be retained"):
        attempt(
            outcome=WaveFiveRepeatabilityOutcome.FAILED_TO_REPRODUCE,
            retained_failed_output=False,
        )


def test_failed_attempt_blocks_progress_but_is_preserved() -> None:
    item = attempt(outcome=WaveFiveRepeatabilityOutcome.FAILED_TO_REPRODUCE)

    assert item.blocks_wave_five_progress is True
    assert item.retained_failed_output is True


def test_disagreement_requires_reviewer_artifact_and_evidence() -> None:
    with pytest.raises(ValueError, match="reviewer ids"):
        WaveFiveReviewerDisagreement(
            disagreement_id="disagreement-invalid",
            disagreement_kind=WaveFiveDisagreementKind.CLAIM_SCOPE,
            disposition=WaveFiveDisagreementDisposition.RECORDED_FOR_REVIEW,
            reviewer_ids=(),
            disputed_artifact_ids=("artifact",),
            summary="Invalid disagreement.",
            resolution_summary="Missing reviewer.",
            evidence_ids=("evidence",),
        )


def test_unresolved_disagreement_requires_contradictory_evidence() -> None:
    with pytest.raises(ValueError, match="contradictory evidence"):
        disagreement(disposition=WaveFiveDisagreementDisposition.UNRESOLVED)


def test_unresolved_disagreement_blocks_progress_and_preserves_dissent() -> None:
    item = disagreement(
        disposition=WaveFiveDisagreementDisposition.UNRESOLVED,
        contradictory_evidence_ids=("evidence-contradiction",),
    )

    assert item.blocks_wave_five_progress is True
    assert item.preserves_dissent is True
    assert item.all_evidence_ids == (
        "evidence-disagreement-protocol-interpretation",
        "evidence-contradiction",
    )


def test_control_requires_evidence() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveRepeatabilityControl(
            control_id="control-invalid",
            control_kind=WaveFiveRepeatabilityControlKind.FAILED_ATTEMPTS_RETAINED,
            result=WaveFiveRepeatabilityControlResult.PASSED,
            description="Invalid control without evidence.",
            evidence_ids=(),
        )


def test_failed_control_blocks_progress() -> None:
    item = control(
        "control-failed",
        WaveFiveRepeatabilityControlKind.DISAGREEMENTS_RETAINED,
        result=WaveFiveRepeatabilityControlResult.FAILED,
    )

    assert item.passed_with_boundaries is False
    assert item.blocks_wave_five_progress is True


def test_non_blocking_control_does_not_block_progress() -> None:
    item = control(
        "control-warning",
        WaveFiveRepeatabilityControlKind.PROTOCOL_VARIANCE_RECORDED,
        result=WaveFiveRepeatabilityControlResult.NEEDS_MORE_EVIDENCE,
        blocking=False,
    )

    assert item.blocks_wave_five_progress is False


def test_ledger_rejects_missing_sections() -> None:
    with pytest.raises(ValueError, match="require attempts"):
        ledger(attempts=())

    with pytest.raises(ValueError, match="disagreement entries"):
        ledger(disagreements=())

    with pytest.raises(ValueError, match="require controls"):
        ledger(controls=())


def test_ledger_rejects_missing_claim_boundary() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        ledger(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_ledger_reports_missing_required_coverage() -> None:
    item = ledger(
        attempts=(attempt(),),
        disagreements=(disagreement(),),
        controls=(
            control(
                "control-failed-attempts-retained",
                WaveFiveRepeatabilityControlKind.FAILED_ATTEMPTS_RETAINED,
            ),
        ),
    )

    assert item.has_required_attempt_coverage is False
    assert WaveFiveRepeatabilityAttemptKind.INDEPENDENT_LAB_REPLAY in (
        item.missing_required_attempt_kinds
    )
    assert item.has_required_disagreement_coverage is False
    assert WaveFiveDisagreementKind.WAVE_SIX_READINESS in (
        item.missing_required_disagreement_kinds
    )
    assert item.has_required_control_coverage is False
    assert WaveFiveRepeatabilityControlKind.DISAGREEMENTS_RETAINED in (
        item.missing_required_control_kinds
    )


def test_ledger_is_ready_for_external_repeatability_review() -> None:
    item = ledger()

    assert item.has_external_attempt is True
    assert item.has_required_attempt_coverage is True
    assert item.has_required_disagreement_coverage is True
    assert item.has_required_control_coverage is True
    assert item.blocks_repeatability_readiness is False
    assert item.ready_for_external_repeatability_review is True


def test_ready_ledger_exports_reviewable_artifact() -> None:
    artifact = ledger().to_artifact_ref()

    assert artifact.kind is WaveFiveArtifactKind.REPEATABILITY_LEDGER
    assert artifact.capability_area is WaveFiveCapabilityArea.REPRODUCIBILITY
    assert artifact.source_system is WaveFiveSourceSystem.IX_COGNITION_KERNEL
    assert artifact.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    assert artifact.authority_state is WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    )


def test_blocking_attempt_exports_blocked_artifact() -> None:
    attempts = tuple(
        attempt(
            f"attempt-{kind.value}",
            attempt_kind=kind,
            outcome=(
                WaveFiveRepeatabilityOutcome.FAILED_TO_REPRODUCE
                if kind is WaveFiveRepeatabilityAttemptKind.CROSS_ENVIRONMENT_REPLAY
                else WaveFiveRepeatabilityOutcome.REPRODUCED
            ),
            source_system=(
                WaveFiveSourceSystem.INDEPENDENT_REPLICATION_LAB
                if kind is WaveFiveRepeatabilityAttemptKind.INDEPENDENT_LAB_REPLAY
                else WaveFiveSourceSystem.IX_COGNITION_KERNEL
            ),
            reviewer_ids=(
                ("reviewer-001",)
                if kind is WaveFiveRepeatabilityAttemptKind.INDEPENDENT_LAB_REPLAY
                else ()
            ),
        )
        for kind in REQUIRED_REPEATABILITY_ATTEMPT_KINDS
    )
    artifact = ledger(attempts=attempts).to_artifact_ref()

    assert artifact.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact.authority_state is WaveFiveAuthorityState.BLOCKED
    assert artifact.validation_status is WaveFiveValidationStatus.REJECTED


def test_blocking_disagreement_exports_blocked_artifact() -> None:
    disagreements = tuple(
        disagreement(
            f"disagreement-{kind.value}",
            disagreement_kind=kind,
            disposition=(
                WaveFiveDisagreementDisposition.BLOCKING
                if kind is WaveFiveDisagreementKind.WAVE_SIX_READINESS
                else WaveFiveDisagreementDisposition.RESOLVED_WITH_EVIDENCE
            ),
            contradictory_evidence_ids=(
                ("evidence-wave-six-dispute",)
                if kind is WaveFiveDisagreementKind.WAVE_SIX_READINESS
                else ()
            ),
        )
        for kind in REQUIRED_DISAGREEMENT_KINDS
    )
    artifact = ledger(disagreements=disagreements).to_artifact_ref()

    assert artifact.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact.validation_status is WaveFiveValidationStatus.REJECTED


def test_externally_reviewed_ledger_requires_external_source() -> None:
    with pytest.raises(ValueError, match="external source"):
        ledger(
            ledger_state=(
                WaveFiveRepeatabilityLedgerState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
            reviewer_ids=("reviewer-001",),
        )


def test_externally_reviewed_ledger_requires_reviewer_ids() -> None:
    with pytest.raises(ValueError, match="reviewer ids"):
        ledger(
            source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
            ledger_state=(
                WaveFiveRepeatabilityLedgerState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
        )


def test_externally_reviewed_ledger_exports_bounded_external_artifact() -> None:
    item = ledger(
        source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
        ledger_state=(
            WaveFiveRepeatabilityLedgerState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
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


def test_ledger_collects_unique_evidence_ids() -> None:
    item = ledger()

    assert item.all_evidence_ids[0] == "evidence-attempt-clean-checkout-replay"
    assert "evidence-disagreement-wave-six-readiness" in item.all_evidence_ids
    assert "evidence-control-wave-six-limitation-visible" in item.all_evidence_ids
    assert len(item.all_evidence_ids) == 22


def test_ledger_fingerprint_is_deterministic() -> None:
    item = ledger()

    assert item.fingerprint() == item.fingerprint()
    assert len(item.fingerprint()) == 64
