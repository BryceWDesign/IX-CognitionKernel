import pytest

from ix_cognition_kernel.wave5_contracts import (
    WaveFiveArtifactDecision,
    WaveFiveAuthorityState,
    WaveFiveSourceSystem,
    WaveFiveValidationStatus,
)
from ix_cognition_kernel.wave5_reviewers import (
    WaveFiveConflictDisclosure,
    WaveFiveConflictKind,
    WaveFiveConflictSeverity,
    WaveFiveIndependenceStatus,
    WaveFiveReviewerAttestation,
    WaveFiveReviewerDecision,
    WaveFiveReviewerRole,
    WaveFiveReviewPanel,
    WaveFiveReviewScope,
    blocking_wave_five_reviewer_decisions,
    required_wave_five_review_scopes,
)


def _no_conflict(disclosure_id: str = "disclosure-none") -> WaveFiveConflictDisclosure:
    return WaveFiveConflictDisclosure(
        disclosure_id=disclosure_id,
        conflict_kind=WaveFiveConflictKind.NONE_DECLARED,
        severity=WaveFiveConflictSeverity.NONE,
        description="No conflicts declared.",
        mitigation="No mitigation required.",
        evidence_ids=(),
    )


def _reviewer_attestation(
    *,
    attestation_id: str = "attestation-1",
    reviewer_id: str = "reviewer-1",
    decision: WaveFiveReviewerDecision = (
        WaveFiveReviewerDecision.ACCEPT_WITH_BOUNDARIES
    ),
    independence_status: WaveFiveIndependenceStatus = (
        WaveFiveIndependenceStatus.INDEPENDENT
    ),
    review_scopes: tuple[WaveFiveReviewScope, ...] | None = None,
    disclosures: tuple[WaveFiveConflictDisclosure, ...] | None = None,
    limitations: tuple[str, ...] = (),
    dissent_notes: tuple[str, ...] = (),
) -> WaveFiveReviewerAttestation:
    return WaveFiveReviewerAttestation(
        attestation_id=attestation_id,
        reviewer_id=reviewer_id,
        reviewer_label=f"Reviewer {reviewer_id}",
        reviewer_role=WaveFiveReviewerRole.INDEPENDENT_REPRODUCER,
        independence_status=independence_status,
        decision=decision,
        review_scopes=review_scopes or required_wave_five_review_scopes(),
        reviewed_artifact_ids=("artifact-1", "artifact-2"),
        protocol_ids=("protocol-1",),
        evidence_ids=(f"evidence-{attestation_id}",),
        conflict_disclosures=disclosures or (_no_conflict(),),
        rationale="Reviewer accepts the evidence with explicit boundaries.",
        limitations=limitations,
        dissent_notes=dissent_notes,
    )


def test_required_review_scope_and_blocking_decisions_are_locked() -> None:
    assert len(required_wave_five_review_scopes()) >= 8
    assert (
        WaveFiveReviewScope.WAVE_SIX_PRECONDITIONS in required_wave_five_review_scopes()
    )
    assert WaveFiveReviewerDecision.REJECT in blocking_wave_five_reviewer_decisions()


def test_reviewer_attestation_is_usable_when_independent_and_evidence_bound() -> None:
    attestation = _reviewer_attestation()

    assert attestation.usable_for_independent_review
    assert not attestation.blocks_wave_five_progress
    assert not attestation.has_blocking_conflict
    assert attestation.all_evidence_ids == ("evidence-attestation-1",)
    assert attestation.fingerprint() == attestation.fingerprint()

    artifact_ref = attestation.to_artifact_ref()
    assert artifact_ref.decision is WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
    assert artifact_ref.authority_state is WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    assert (
        artifact_ref.validation_status
        is WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
    )
    assert artifact_ref.source_system is WaveFiveSourceSystem.INDEPENDENT_REVIEWER


def test_limited_independence_requires_limitations() -> None:
    with pytest.raises(ValueError, match="Limited independence"):
        _reviewer_attestation(
            independence_status=(
                WaveFiveIndependenceStatus.INDEPENDENT_WITH_DISCLOSED_LIMITS
            )
        )


def test_limited_independence_accepts_stated_limitations() -> None:
    attestation = _reviewer_attestation(
        independence_status=(
            WaveFiveIndependenceStatus.INDEPENDENT_WITH_DISCLOSED_LIMITS
        ),
        limitations=("Reviewer only covered reproducibility and safety evidence.",),
    )

    assert attestation.usable_for_independent_review
    assert attestation.limitations == (
        "Reviewer only covered reproducibility and safety evidence.",
    )


def test_reviewer_attestation_rejects_unknown_independence() -> None:
    with pytest.raises(ValueError, match="not independently usable"):
        _reviewer_attestation(independence_status=WaveFiveIndependenceStatus.UNKNOWN)


def test_reviewer_attestation_rejects_authorship_conflict() -> None:
    authorship_conflict = WaveFiveConflictDisclosure(
        disclosure_id="disclosure-authorship",
        conflict_kind=WaveFiveConflictKind.AUTHORSHIP,
        severity=WaveFiveConflictSeverity.BLOCKING,
        description="Reviewer authored the artifact.",
        mitigation="Use a different independent reviewer.",
        evidence_ids=("conflict-evidence-1",),
    )

    with pytest.raises(ValueError, match="blocking conflicts"):
        _reviewer_attestation(disclosures=(authorship_conflict,))


def test_conflict_disclosure_rejects_mismatched_none_state() -> None:
    with pytest.raises(ValueError, match="severity none"):
        WaveFiveConflictDisclosure(
            disclosure_id="disclosure-invalid",
            conflict_kind=WaveFiveConflictKind.NONE_DECLARED,
            severity=WaveFiveConflictSeverity.LOW,
            description="Invalid no-conflict state.",
            mitigation="Correct the disclosure.",
            evidence_ids=(),
        )


def test_dissenting_reviewer_decision_requires_dissent_notes() -> None:
    with pytest.raises(ValueError, match="dissent notes"):
        _reviewer_attestation(decision=WaveFiveReviewerDecision.DISPUTE)


def test_dissenting_reviewer_exports_blocked_artifact_ref() -> None:
    attestation = _reviewer_attestation(
        decision=WaveFiveReviewerDecision.DISPUTE,
        dissent_notes=("Reviewer disputes evidence sufficiency.",),
    )

    assert attestation.blocks_wave_five_progress
    assert attestation.is_dissenting

    artifact_ref = attestation.to_artifact_ref()
    assert artifact_ref.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact_ref.authority_state is WaveFiveAuthorityState.BLOCKED
    assert artifact_ref.validation_status is WaveFiveValidationStatus.DISPUTED


def test_review_panel_ready_when_required_scopes_are_covered() -> None:
    panel = WaveFiveReviewPanel(
        panel_id="panel-1",
        attestations=(
            _reviewer_attestation(
                attestation_id="attestation-1",
                reviewer_id="reviewer-1",
            ),
            _reviewer_attestation(
                attestation_id="attestation-2",
                reviewer_id="reviewer-2",
            ),
        ),
        minimum_usable_reviewers=2,
    )

    assert panel.ready_for_independent_review_record
    assert len(panel.usable_attestations) == 2
    assert panel.blocking_attestation_ids == ()
    assert panel.missing_required_review_scopes == ()
    assert panel.fingerprint() == panel.fingerprint()


def test_review_panel_reports_missing_scope_coverage() -> None:
    limited_scope = (WaveFiveReviewScope.EXTERNAL_PROTOCOLS,)
    panel = WaveFiveReviewPanel(
        panel_id="panel-missing-scope",
        attestations=(
            _reviewer_attestation(
                attestation_id="attestation-1",
                reviewer_id="reviewer-1",
                review_scopes=limited_scope,
            ),
            _reviewer_attestation(
                attestation_id="attestation-2",
                reviewer_id="reviewer-2",
                review_scopes=limited_scope,
            ),
        ),
        minimum_usable_reviewers=2,
    )

    assert WaveFiveReviewScope.REPRODUCIBLE_EVIDENCE in (
        panel.missing_required_review_scopes
    )
    assert not panel.ready_for_independent_review_record


def test_review_panel_blocks_when_reviewer_count_is_too_low() -> None:
    panel = WaveFiveReviewPanel(
        panel_id="panel-too-small",
        attestations=(
            _reviewer_attestation(
                attestation_id="attestation-1",
                reviewer_id="reviewer-1",
            ),
        ),
        minimum_usable_reviewers=2,
    )

    assert len(panel.usable_attestations) == 1
    assert not panel.ready_for_independent_review_record
