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
from ix_cognition_kernel.wave5_reviewers import (
    BLOCKING_WAVE_FIVE_REVIEWER_DECISIONS,
    REQUIRED_WAVE_FIVE_REVIEW_SCOPES,
    WaveFiveConflictDisclosure,
    WaveFiveConflictKind,
    WaveFiveConflictSeverity,
    WaveFiveIndependenceStatus,
    WaveFiveReviewPanel,
    WaveFiveReviewScope,
    WaveFiveReviewerAttestation,
    WaveFiveReviewerDecision,
    WaveFiveReviewerRole,
    blocking_wave_five_reviewer_decisions,
    required_wave_five_review_scopes,
)


def no_conflict(disclosure_id: str = "conflict-none") -> WaveFiveConflictDisclosure:
    return WaveFiveConflictDisclosure(
        disclosure_id=disclosure_id,
        conflict_kind=WaveFiveConflictKind.NONE_DECLARED,
        severity=WaveFiveConflictSeverity.NONE,
        description="Reviewer declares no conflict relevant to this validation.",
        mitigation="No mitigation required because no conflict is declared.",
        evidence_ids=(),
    )


def manageable_conflict() -> WaveFiveConflictDisclosure:
    return WaveFiveConflictDisclosure(
        disclosure_id="conflict-managed",
        conflict_kind=WaveFiveConflictKind.COMPETITIVE_INTEREST,
        severity=WaveFiveConflictSeverity.MANAGEABLE,
        description="Reviewer has adjacent research interests but no authorship.",
        mitigation="Panel records limitation and preserves dissent visibility.",
        evidence_ids=("conflict-evidence-001",),
    )


def attestation(
    attestation_id: str = "reviewer-attestation-001",
    *,
    reviewer_id: str = "independent-reviewer-001",
    reviewer_role: WaveFiveReviewerRole = WaveFiveReviewerRole.SAFETY_REVIEWER,
    review_scopes: tuple[WaveFiveReviewScope, ...] = (
        WaveFiveReviewScope.EXTERNAL_PROTOCOLS,
        WaveFiveReviewScope.REPRODUCIBLE_EVIDENCE,
    ),
    independence_status: WaveFiveIndependenceStatus = (
        WaveFiveIndependenceStatus.INDEPENDENT
    ),
    decision: WaveFiveReviewerDecision = (
        WaveFiveReviewerDecision.ACCEPT_WITH_BOUNDARIES
    ),
    conflicts: tuple[WaveFiveConflictDisclosure, ...] | None = None,
    limitations: tuple[str, ...] = (),
    dissent_notes: tuple[str, ...] = (),
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    ),
) -> WaveFiveReviewerAttestation:
    resolved_conflicts = (no_conflict(),) if conflicts is None else conflicts

    return WaveFiveReviewerAttestation(
        attestation_id=attestation_id,
        reviewer_id=reviewer_id,
        reviewer_label="Independent Wave 5 reviewer",
        reviewer_role=reviewer_role,
        independence_status=independence_status,
        decision=decision,
        review_scopes=review_scopes,
        reviewed_artifact_ids=("wave5-artifact-001",),
        protocol_ids=("wave5-external-protocol-001",),
        evidence_ids=("review-evidence-001",),
        conflict_disclosures=resolved_conflicts,
        rationale="Independent reviewer accepts only bounded Wave 5 evidence.",
        limitations=limitations,
        dissent_notes=dissent_notes,
        claim_boundaries=claim_boundaries,
        source_system=source_system,
    )


def full_scope_attestation(
    attestation_id: str,
    reviewer_id: str,
    *,
    role: WaveFiveReviewerRole,
) -> WaveFiveReviewerAttestation:
    return attestation(
        attestation_id=attestation_id,
        reviewer_id=reviewer_id,
        reviewer_role=role,
        review_scopes=REQUIRED_WAVE_FIVE_REVIEW_SCOPES,
        conflicts=(no_conflict(f"conflict-{reviewer_id}"),),
    )


def test_required_review_scopes_are_locked() -> None:
    assert required_wave_five_review_scopes() == REQUIRED_WAVE_FIVE_REVIEW_SCOPES
    assert len(REQUIRED_WAVE_FIVE_REVIEW_SCOPES) == 10
    assert WaveFiveReviewScope.WAVE_SIX_PRECONDITIONS in (
        REQUIRED_WAVE_FIVE_REVIEW_SCOPES
    )


def test_blocking_reviewer_decisions_are_locked() -> None:
    assert blocking_wave_five_reviewer_decisions() == (
        BLOCKING_WAVE_FIVE_REVIEWER_DECISIONS
    )
    assert WaveFiveReviewerDecision.REQUEST_MORE_EVIDENCE in (
        BLOCKING_WAVE_FIVE_REVIEWER_DECISIONS
    )
    assert WaveFiveReviewerDecision.DISPUTE in BLOCKING_WAVE_FIVE_REVIEWER_DECISIONS
    assert WaveFiveReviewerDecision.REJECT in BLOCKING_WAVE_FIVE_REVIEWER_DECISIONS


def test_no_conflict_disclosure_must_use_none_severity() -> None:
    with pytest.raises(ValueError, match="severity none"):
        WaveFiveConflictDisclosure(
            disclosure_id="conflict-invalid",
            conflict_kind=WaveFiveConflictKind.NONE_DECLARED,
            severity=WaveFiveConflictSeverity.LOW,
            description="Invalid no-conflict declaration.",
            mitigation="No mitigation.",
            evidence_ids=(),
        )


def test_declared_conflict_cannot_use_none_severity() -> None:
    with pytest.raises(ValueError, match="Declared conflicts"):
        WaveFiveConflictDisclosure(
            disclosure_id="conflict-invalid",
            conflict_kind=WaveFiveConflictKind.FUNDING,
            severity=WaveFiveConflictSeverity.NONE,
            description="Funding conflict is declared.",
            mitigation="Mitigation is recorded.",
            evidence_ids=("conflict-evidence",),
        )


def test_authorship_conflict_is_blocking() -> None:
    disclosure = WaveFiveConflictDisclosure(
        disclosure_id="conflict-author",
        conflict_kind=WaveFiveConflictKind.AUTHORSHIP,
        severity=WaveFiveConflictSeverity.LOW,
        description="Reviewer is also an author of the reviewed repo.",
        mitigation="Authorship cannot be mitigated for independence.",
        evidence_ids=("conflict-evidence",),
    )

    assert disclosure.is_blocking is True


def test_reviewer_attestation_rejects_missing_conflict_disclosure() -> None:
    with pytest.raises(ValueError, match="conflict disclosures"):
        attestation(conflicts=())


def test_reviewer_attestation_rejects_blocking_conflict() -> None:
    blocking = WaveFiveConflictDisclosure(
        disclosure_id="conflict-blocking",
        conflict_kind=WaveFiveConflictKind.CONTRACTING,
        severity=WaveFiveConflictSeverity.BLOCKING,
        description="Reviewer has a blocking contractor relationship.",
        mitigation="Reviewer cannot count as independent evidence.",
        evidence_ids=("conflict-evidence",),
    )

    with pytest.raises(ValueError, match="blocking conflicts"):
        attestation(conflicts=(blocking,))


def test_reviewer_attestation_rejects_non_independent_statuses() -> None:
    with pytest.raises(ValueError, match="not independently usable"):
        attestation(independence_status=WaveFiveIndependenceStatus.NOT_INDEPENDENT)

    with pytest.raises(ValueError, match="not independently usable"):
        attestation(independence_status=WaveFiveIndependenceStatus.UNKNOWN)


def test_limited_independence_requires_limitations() -> None:
    with pytest.raises(ValueError, match="requires stated limitations"):
        attestation(
            independence_status=(
                WaveFiveIndependenceStatus.INDEPENDENT_WITH_DISCLOSED_LIMITS
            ),
            conflicts=(manageable_conflict(),),
        )


def test_limited_independence_with_manageable_conflict_is_usable() -> None:
    limited = attestation(
        independence_status=(
            WaveFiveIndependenceStatus.INDEPENDENT_WITH_DISCLOSED_LIMITS
        ),
        conflicts=(manageable_conflict(),),
        limitations=("Reviewer has adjacent research interests.",),
    )

    assert limited.usable_for_independent_review is True
    assert limited.all_conflict_evidence_ids == ("conflict-evidence-001",)
    assert limited.all_evidence_ids == (
        "review-evidence-001",
        "conflict-evidence-001",
    )


def test_dissenting_attestation_requires_dissent_notes() -> None:
    with pytest.raises(ValueError, match="Dissenting reviewer decisions"):
        attestation(decision=WaveFiveReviewerDecision.DISPUTE)


def test_dissenting_attestation_blocks_progress_but_preserves_dissent() -> None:
    dissent = attestation(
        decision=WaveFiveReviewerDecision.DISPUTE,
        dissent_notes=("Reviewer disputes cross-domain transfer evidence.",),
    )

    assert dissent.is_dissenting is True
    assert dissent.blocks_wave_five_progress is True
    artifact = dissent.to_artifact_ref()
    assert artifact.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact.authority_state is WaveFiveAuthorityState.BLOCKED
    assert artifact.validation_status is WaveFiveValidationStatus.DISPUTED


def test_reviewer_attestation_rejects_internal_source_system() -> None:
    with pytest.raises(ValueError, match="independent reviewers"):
        attestation(source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL)


def test_reviewer_attestation_requires_claim_boundaries() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        attestation(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_accepted_attestation_exports_as_external_reviewer_artifact() -> None:
    item = attestation()
    artifact = item.to_artifact_ref()

    assert artifact.kind is WaveFiveArtifactKind.REVIEWER_ATTESTATION
    assert artifact.capability_area is WaveFiveCapabilityArea.INDEPENDENT_REVIEW
    assert artifact.source_system is WaveFiveSourceSystem.INDEPENDENT_REVIEWER
    assert artifact.decision is WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
    )
    assert artifact.ready_for_independent_review is False
    assert artifact.externally_validated_with_boundaries is True


def test_attestation_fingerprint_is_deterministic() -> None:
    item = attestation()

    assert item.fingerprint() == item.fingerprint()
    assert len(item.fingerprint()) == 64


def test_review_panel_rejects_duplicate_reviewers() -> None:
    first = attestation("attestation-a", reviewer_id="reviewer-001")
    second = attestation("attestation-b", reviewer_id="reviewer-001")

    with pytest.raises(ValueError, match="Duplicate reviewer_id"):
        WaveFiveReviewPanel(panel_id="panel-001", attestations=(first, second))


def test_review_panel_reports_missing_scope_coverage() -> None:
    panel = WaveFiveReviewPanel(
        panel_id="panel-001",
        attestations=(attestation(),),
        minimum_usable_reviewers=1,
    )

    assert panel.ready_for_independent_review_record is False
    assert WaveFiveReviewScope.WAVE_SIX_PRECONDITIONS in (
        panel.missing_required_review_scopes
    )


def test_review_panel_requires_minimum_usable_reviewers() -> None:
    panel = WaveFiveReviewPanel(
        panel_id="panel-001",
        attestations=(
            full_scope_attestation(
                "attestation-a",
                "reviewer-a",
                role=WaveFiveReviewerRole.SAFETY_REVIEWER,
            ),
        ),
        minimum_usable_reviewers=2,
    )

    assert panel.ready_for_independent_review_record is False
    assert len(panel.usable_attestations) == 1


def test_review_panel_is_ready_when_scope_and_reviewer_count_are_satisfied() -> None:
    panel = WaveFiveReviewPanel(
        panel_id="panel-001",
        attestations=(
            full_scope_attestation(
                "attestation-a",
                "reviewer-a",
                role=WaveFiveReviewerRole.SAFETY_REVIEWER,
            ),
            full_scope_attestation(
                "attestation-b",
                "reviewer-b",
                role=WaveFiveReviewerRole.GOVERNANCE_REVIEWER,
            ),
        ),
        notes=("Panel preserves Wave 6 readiness boundaries.",),
    )

    assert panel.ready_for_independent_review_record is True
    assert panel.blocking_attestation_ids == ()
    assert panel.missing_required_review_scopes == ()
    assert panel.all_evidence_ids == ("review-evidence-001",)


def test_review_panel_blocks_when_dissent_is_present() -> None:
    dissent = attestation(
        "attestation-dissent",
        reviewer_id="reviewer-dissent",
        decision=WaveFiveReviewerDecision.DISPUTE,
        dissent_notes=("Reviewer disputes reproducibility evidence.",),
    )
    panel = WaveFiveReviewPanel(
        panel_id="panel-001",
        attestations=(
            full_scope_attestation(
                "attestation-a",
                "reviewer-a",
                role=WaveFiveReviewerRole.SAFETY_REVIEWER,
            ),
            full_scope_attestation(
                "attestation-b",
                "reviewer-b",
                role=WaveFiveReviewerRole.GOVERNANCE_REVIEWER,
            ),
            dissent,
        ),
    )

    assert panel.ready_for_independent_review_record is False
    assert panel.blocking_attestation_ids == ("attestation-dissent",)
    assert panel.dissenting_attestation_ids == ("attestation-dissent",)


def test_review_panel_fingerprint_is_deterministic() -> None:
    panel = WaveFiveReviewPanel(
        panel_id="panel-001",
        attestations=(
            full_scope_attestation(
                "attestation-a",
                "reviewer-a",
                role=WaveFiveReviewerRole.SAFETY_REVIEWER,
            ),
            full_scope_attestation(
                "attestation-b",
                "reviewer-b",
                role=WaveFiveReviewerRole.GOVERNANCE_REVIEWER,
            ),
        ),
    )

    assert panel.fingerprint() == panel.fingerprint()
    assert len(panel.fingerprint()) == 64
