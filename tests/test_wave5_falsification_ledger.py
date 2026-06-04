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
from ix_cognition_kernel.wave5_falsification_ledger import (
    BLOCKING_FALSIFICATION_VERDICTS,
    EXTERNAL_FALSIFICATION_REVIEW_SOURCE_SYSTEMS,
    REQUIRED_FALSIFICATION_TARGETS,
    REQUIRED_KILL_CRITERIA,
    SAFE_FALSIFICATION_VERDICTS,
    WaveFiveFalsificationChallenge,
    WaveFiveFalsificationChallengeStatus,
    WaveFiveFalsificationLedger,
    WaveFiveFalsificationLedgerState,
    WaveFiveFalsificationResult,
    WaveFiveFalsificationTargetKind,
    WaveFiveFalsificationVerdict,
    WaveFiveKillCriterion,
    WaveFiveKillCriterionDisposition,
    WaveFiveKillCriterionKind,
    blocking_falsification_verdicts,
    external_falsification_review_source_systems,
    required_falsification_targets,
    required_kill_criteria,
    safe_falsification_verdicts,
)


def challenge(
    challenge_id: str = "challenge-evidence-chain",
    *,
    target_kind: WaveFiveFalsificationTargetKind = (
        WaveFiveFalsificationTargetKind.EVIDENCE_CHAIN
    ),
    status: WaveFiveFalsificationChallengeStatus = (
        WaveFiveFalsificationChallengeStatus.READY
    ),
    reviewer_visible: bool = True,
) -> WaveFiveFalsificationChallenge:
    return WaveFiveFalsificationChallenge(
        challenge_id=challenge_id,
        target_kind=target_kind,
        status=status,
        challenge_question="Can this evidence target be falsified by replay?",
        expected_failure_signal="A broken trace, unsafe response, or disputed replay.",
        artifact_ids=(f"artifact-{challenge_id}",),
        evidence_ids=(f"evidence-{challenge_id}",),
        reviewer_visible=reviewer_visible,
    )


def kill_criterion(
    criterion_id: str = "criterion-evidence-chain-break",
    *,
    criterion_kind: WaveFiveKillCriterionKind = (
        WaveFiveKillCriterionKind.EVIDENCE_CHAIN_BREAK
    ),
    disposition: WaveFiveKillCriterionDisposition = (
        WaveFiveKillCriterionDisposition.NOT_TRIGGERED
    ),
    resolved_by_evidence_ids: tuple[str, ...] = (),
    reviewer_visible: bool = True,
) -> WaveFiveKillCriterion:
    return WaveFiveKillCriterion(
        criterion_id=criterion_id,
        criterion_kind=criterion_kind,
        disposition=disposition,
        description="Criterion blocks Wave 6 if the evidence target fails.",
        blocking_response="Stop Wave 6 design review until evidence is repaired.",
        evidence_ids=(f"evidence-{criterion_id}",),
        resolved_by_evidence_ids=resolved_by_evidence_ids,
        reviewer_visible=reviewer_visible,
    )


def result(
    result_id: str = "result-evidence-chain",
    *,
    challenge_id: str = "challenge-evidence-chain",
    verdict: WaveFiveFalsificationVerdict = (
        WaveFiveFalsificationVerdict.SURVIVED_CHALLENGE
    ),
    triggered_criterion_ids: tuple[str, ...] = (),
    reviewer_ids: tuple[str, ...] = (),
    retained_failure_output: bool = True,
) -> WaveFiveFalsificationResult:
    return WaveFiveFalsificationResult(
        result_id=result_id,
        challenge_id=challenge_id,
        verdict=verdict,
        observed_result="Falsification output is retained for review.",
        evidence_ids=(f"evidence-{result_id}",),
        triggered_criterion_ids=triggered_criterion_ids,
        reviewer_ids=reviewer_ids,
        retained_failure_output=retained_failure_output,
    )


def required_challenges() -> tuple[WaveFiveFalsificationChallenge, ...]:
    return tuple(
        challenge(
            f"challenge-{target.value}",
            target_kind=target,
        )
        for target in REQUIRED_FALSIFICATION_TARGETS
    )


def required_criteria() -> tuple[WaveFiveKillCriterion, ...]:
    return tuple(
        kill_criterion(
            f"criterion-{criterion.value}",
            criterion_kind=criterion,
        )
        for criterion in REQUIRED_KILL_CRITERIA
    )


def required_results() -> tuple[WaveFiveFalsificationResult, ...]:
    return tuple(
        result(
            f"result-{target.value}",
            challenge_id=f"challenge-{target.value}",
        )
        for target in REQUIRED_FALSIFICATION_TARGETS
    )


def ledger(
    *,
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    ledger_state: WaveFiveFalsificationLedgerState = (
        WaveFiveFalsificationLedgerState.READY_FOR_EXTERNAL_FALSIFICATION_REVIEW
    ),
    challenges: tuple[WaveFiveFalsificationChallenge, ...] | None = None,
    criteria: tuple[WaveFiveKillCriterion, ...] | None = None,
    results: tuple[WaveFiveFalsificationResult, ...] | None = None,
    reviewer_ids: tuple[str, ...] = (),
    attempted_wave_six_promotion: bool = False,
    claims_agi: bool = False,
    grants_execution_authority: bool = False,
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    ),
) -> WaveFiveFalsificationLedger:
    resolved_challenges = required_challenges() if challenges is None else challenges
    resolved_criteria = required_criteria() if criteria is None else criteria
    resolved_results = required_results() if results is None else results
    return WaveFiveFalsificationLedger(
        ledger_id="wave5-falsification-ledger-001",
        title="Wave 5 falsification and kill-criteria ledger.",
        source_system=source_system,
        ledger_state=ledger_state,
        challenges=resolved_challenges,
        kill_criteria=resolved_criteria,
        results=resolved_results,
        protocol_ids=("wave5-external-protocol-001",),
        reviewer_ids=reviewer_ids,
        attempted_wave_six_promotion=attempted_wave_six_promotion,
        claims_agi=claims_agi,
        grants_execution_authority=grants_execution_authority,
        claim_boundaries=claim_boundaries,
        notes=("Surviving falsification is review evidence, not Wave 6 proof.",),
    )


def test_required_falsification_targets_are_locked() -> None:
    assert required_falsification_targets() == REQUIRED_FALSIFICATION_TARGETS
    assert len(REQUIRED_FALSIFICATION_TARGETS) == 11
    assert WaveFiveFalsificationTargetKind.WAVE_SIX_READINESS in (
        REQUIRED_FALSIFICATION_TARGETS
    )


def test_required_kill_criteria_are_locked() -> None:
    assert required_kill_criteria() == REQUIRED_KILL_CRITERIA
    assert len(REQUIRED_KILL_CRITERIA) == 11
    assert WaveFiveKillCriterionKind.WAVE_SIX_OVERCLAIM in REQUIRED_KILL_CRITERIA


def test_safe_and_blocking_verdicts_are_locked() -> None:
    assert safe_falsification_verdicts() == SAFE_FALSIFICATION_VERDICTS
    assert blocking_falsification_verdicts() == BLOCKING_FALSIFICATION_VERDICTS
    assert WaveFiveFalsificationVerdict.FALSIFIED in BLOCKING_FALSIFICATION_VERDICTS


def test_external_falsification_sources_are_locked() -> None:
    assert external_falsification_review_source_systems() == (
        EXTERNAL_FALSIFICATION_REVIEW_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.ADVERSARIAL_TESTER in (
        EXTERNAL_FALSIFICATION_REVIEW_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.IX_COGNITION_KERNEL not in (
        EXTERNAL_FALSIFICATION_REVIEW_SOURCE_SYSTEMS
    )


def test_challenge_requires_artifacts_evidence_and_visibility() -> None:
    with pytest.raises(ValueError, match="artifact ids"):
        WaveFiveFalsificationChallenge(
            challenge_id="challenge-invalid",
            target_kind=WaveFiveFalsificationTargetKind.EVIDENCE_CHAIN,
            status=WaveFiveFalsificationChallengeStatus.READY,
            challenge_question="Question.",
            expected_failure_signal="Failure signal.",
            artifact_ids=(),
            evidence_ids=("evidence",),
        )

    with pytest.raises(ValueError, match="reviewer visible"):
        challenge(reviewer_visible=False)


def test_blocked_challenge_blocks_ledger_readiness() -> None:
    item = challenge(status=WaveFiveFalsificationChallengeStatus.BLOCKED)

    assert item.ready_for_review is False
    assert item.blocks_ledger_readiness is True


def test_kill_criterion_requires_evidence_and_visibility() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveKillCriterion(
            criterion_id="criterion-invalid",
            criterion_kind=WaveFiveKillCriterionKind.EVIDENCE_CHAIN_BREAK,
            disposition=WaveFiveKillCriterionDisposition.NOT_TRIGGERED,
            description="Invalid criterion.",
            blocking_response="Block.",
            evidence_ids=(),
        )

    with pytest.raises(ValueError, match="reviewer visible"):
        kill_criterion(reviewer_visible=False)


def test_resolved_kill_criterion_requires_resolution_evidence() -> None:
    with pytest.raises(ValueError, match="resolution evidence"):
        kill_criterion(
            disposition=WaveFiveKillCriterionDisposition.TRIGGERED_BUT_RESOLVED
        )


def test_triggered_kill_criterion_blocks_wave_six_entry() -> None:
    item = kill_criterion(
        disposition=WaveFiveKillCriterionDisposition.TRIGGERED_AND_BLOCKING
    )

    assert item.blocks_wave_six_entry is True
    assert item.all_evidence_ids == ("evidence-criterion-evidence-chain-break",)


def test_resolved_kill_criterion_does_not_block() -> None:
    item = kill_criterion(
        disposition=WaveFiveKillCriterionDisposition.TRIGGERED_BUT_RESOLVED,
        resolved_by_evidence_ids=("evidence-resolution",),
    )

    assert item.blocks_wave_six_entry is False
    assert item.all_evidence_ids == (
        "evidence-criterion-evidence-chain-break",
        "evidence-resolution",
    )


def test_result_requires_evidence() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveFalsificationResult(
            result_id="result-invalid",
            challenge_id="challenge-evidence-chain",
            verdict=WaveFiveFalsificationVerdict.SURVIVED_CHALLENGE,
            observed_result="Invalid result.",
            evidence_ids=(),
        )


def test_blocking_result_must_retain_failure_output() -> None:
    with pytest.raises(ValueError, match="must be retained"):
        result(
            verdict=WaveFiveFalsificationVerdict.FALSIFIED,
            retained_failure_output=False,
        )


def test_kill_criterion_verdict_requires_triggered_criteria() -> None:
    with pytest.raises(ValueError, match="require criterion ids"):
        result(verdict=WaveFiveFalsificationVerdict.BLOCKED_BY_KILL_CRITERION)


def test_blocking_result_blocks_wave_six_entry() -> None:
    item = result(verdict=WaveFiveFalsificationVerdict.FALSIFIED)

    assert item.blocks_wave_six_entry is True


def test_ledger_rejects_unknown_result_challenge_reference() -> None:
    with pytest.raises(ValueError, match="bundled challenges"):
        ledger(results=(result(challenge_id="missing-challenge"),))


def test_ledger_rejects_unknown_result_criterion_reference() -> None:
    with pytest.raises(ValueError, match="bundled criteria"):
        ledger(
            results=(
                result(
                    verdict=WaveFiveFalsificationVerdict.BLOCKED_BY_KILL_CRITERION,
                    triggered_criterion_ids=("missing-criterion",),
                ),
            )
        )


def test_ledger_rejects_forbidden_claim_flags() -> None:
    with pytest.raises(ValueError, match="cannot promote to Wave 6"):
        ledger(attempted_wave_six_promotion=True)

    with pytest.raises(ValueError, match="cannot claim AGI"):
        ledger(claims_agi=True)

    with pytest.raises(ValueError, match="cannot grant execution authority"):
        ledger(grants_execution_authority=True)


def test_ledger_rejects_missing_claim_boundary() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        ledger(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_ledger_reports_missing_target_and_criterion_coverage() -> None:
    item = ledger(
        challenges=(challenge(),),
        criteria=(kill_criterion(),),
        results=(result(),),
    )

    assert item.has_required_target_coverage is False
    assert WaveFiveFalsificationTargetKind.WAVE_SIX_READINESS in (
        item.missing_required_targets
    )
    assert item.has_required_criterion_coverage is False
    assert WaveFiveKillCriterionKind.WAVE_SIX_OVERCLAIM in (
        item.missing_required_criteria
    )
    assert item.ready_for_external_falsification_review is False


def test_ledger_blocks_when_challenge_not_ready() -> None:
    challenges = tuple(
        challenge(
            f"challenge-{target.value}",
            target_kind=target,
            status=(
                WaveFiveFalsificationChallengeStatus.BLOCKED
                if target is WaveFiveFalsificationTargetKind.SAFE_REFUSAL
                else WaveFiveFalsificationChallengeStatus.READY
            ),
        )
        for target in REQUIRED_FALSIFICATION_TARGETS
    )
    item = ledger(challenges=challenges)

    assert item.blocking_challenge_ids == ("challenge-safe-refusal",)
    assert item.blocks_falsification_readiness is True


def test_ledger_blocks_when_criterion_is_triggered() -> None:
    criteria = tuple(
        kill_criterion(
            f"criterion-{criterion.value}",
            criterion_kind=criterion,
            disposition=(
                WaveFiveKillCriterionDisposition.TRIGGERED_AND_BLOCKING
                if criterion is WaveFiveKillCriterionKind.AUTHORITY_BYPASS
                else WaveFiveKillCriterionDisposition.NOT_TRIGGERED
            ),
        )
        for criterion in REQUIRED_KILL_CRITERIA
    )
    item = ledger(criteria=criteria)

    assert item.blocking_criterion_ids == ("criterion-authority-bypass",)
    assert item.blocks_falsification_readiness is True


def test_ledger_blocks_when_result_is_falsified() -> None:
    results = tuple(
        result(
            f"result-{target.value}",
            challenge_id=f"challenge-{target.value}",
            verdict=(
                WaveFiveFalsificationVerdict.FALSIFIED
                if target is WaveFiveFalsificationTargetKind.REPEATABILITY
                else WaveFiveFalsificationVerdict.SURVIVED_CHALLENGE
            ),
        )
        for target in REQUIRED_FALSIFICATION_TARGETS
    )
    item = ledger(results=results)

    assert item.blocking_result_ids == ("result-repeatability",)
    assert item.blocks_falsification_readiness is True


def test_ledger_is_ready_for_external_falsification_review() -> None:
    item = ledger()

    assert item.has_required_target_coverage is True
    assert item.has_required_criterion_coverage is True
    assert item.blocking_challenge_ids == ()
    assert item.blocking_criterion_ids == ()
    assert item.blocking_result_ids == ()
    assert item.makes_no_forbidden_claims is True
    assert item.ready_for_external_falsification_review is True


def test_ready_ledger_exports_reviewable_traceability_artifact() -> None:
    artifact = ledger().to_artifact_ref()

    assert artifact.kind is WaveFiveArtifactKind.ECOSYSTEM_TRACEABILITY_MAP
    assert artifact.capability_area is WaveFiveCapabilityArea.ECOSYSTEM_TRACEABILITY
    assert artifact.source_system is WaveFiveSourceSystem.IX_COGNITION_KERNEL
    assert artifact.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    assert artifact.authority_state is WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    )


def test_blocked_ledger_exports_blocked_artifact() -> None:
    results = tuple(
        result(
            f"result-{target.value}",
            challenge_id=f"challenge-{target.value}",
            verdict=(
                WaveFiveFalsificationVerdict.FALSIFIED
                if target is WaveFiveFalsificationTargetKind.REPEATABILITY
                else WaveFiveFalsificationVerdict.SURVIVED_CHALLENGE
            ),
        )
        for target in REQUIRED_FALSIFICATION_TARGETS
    )
    artifact = ledger(results=results).to_artifact_ref()

    assert artifact.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact.authority_state is WaveFiveAuthorityState.BLOCKED
    assert artifact.validation_status is WaveFiveValidationStatus.REJECTED


def test_externally_reviewed_ledger_requires_external_source() -> None:
    with pytest.raises(ValueError, match="external source"):
        ledger(
            ledger_state=(
                WaveFiveFalsificationLedgerState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
            reviewer_ids=("reviewer-001",),
        )


def test_externally_reviewed_ledger_requires_reviewer_ids() -> None:
    with pytest.raises(ValueError, match="require reviewers"):
        ledger(
            source_system=WaveFiveSourceSystem.ADVERSARIAL_TESTER,
            ledger_state=(
                WaveFiveFalsificationLedgerState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
        )


def test_externally_reviewed_ledger_exports_bounded_external_artifact() -> None:
    item = ledger(
        source_system=WaveFiveSourceSystem.ADVERSARIAL_TESTER,
        ledger_state=(
            WaveFiveFalsificationLedgerState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
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

    assert "evidence-challenge-wave-six-readiness" in item.all_evidence_ids
    assert "evidence-criterion-wave-six-overclaim" in item.all_evidence_ids
    assert "evidence-result-wave-six-readiness" in item.all_evidence_ids
    assert len(item.all_evidence_ids) == 33


def test_ledger_fingerprint_is_deterministic() -> None:
    item = ledger()

    assert item.fingerprint() == item.fingerprint()
    assert len(item.fingerprint()) == 64
