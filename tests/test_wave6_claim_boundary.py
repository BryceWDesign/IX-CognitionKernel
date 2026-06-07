import pytest

from ix_cognition_kernel.wave6_claim_boundary import (
    WAVE_SIX_REQUIRED_ALLOWED_CLAIMS,
    WAVE_SIX_REQUIRED_CLAIM_PREREQUISITES,
    WAVE_SIX_REQUIRED_PROHIBITED_CLAIMS,
    WaveSixAllowedClaim,
    WaveSixClaimBoundaryAssessment,
    WaveSixClaimBoundaryDecision,
    WaveSixClaimBoundaryDeclaration,
    WaveSixClaimPrerequisite,
    WaveSixProhibitedClaim,
    build_wave_six_claim_boundary_assessment,
    required_wave_six_allowed_claims,
    required_wave_six_claim_prerequisites,
    required_wave_six_prohibited_claims,
)


def _declaration(
    *,
    declaration_id: str = "boundary-1",
    decision: WaveSixClaimBoundaryDecision = (
        WaveSixClaimBoundaryDecision.READY_FOR_BOUNDED_REVIEW
    ),
    satisfied_prerequisites: tuple[WaveSixClaimPrerequisite, ...] = (
        WAVE_SIX_REQUIRED_CLAIM_PREREQUISITES
    ),
    evidence_ids: tuple[str, ...] = ("evidence-boundary-1",),
) -> WaveSixClaimBoundaryDeclaration:
    return WaveSixClaimBoundaryDeclaration(
        declaration_id=declaration_id,
        boundary_statement=(
            "This is a Wave-6 measured system-level cognition attempt. It is "
            "not an AGI, production, certification, or autonomous-authority claim."
        ),
        allowed_claims=WAVE_SIX_REQUIRED_ALLOWED_CLAIMS,
        prohibited_claims=WAVE_SIX_REQUIRED_PROHIBITED_CLAIMS,
        satisfied_prerequisites=satisfied_prerequisites,
        evidence_ids=evidence_ids,
        reviewer_questions=(
            "Does the evidence survive transfer, novelty, falsification, and "
            "independent review?",
        ),
        decision=decision,
    )


def test_required_claim_boundary_sets_are_locked() -> None:
    assert required_wave_six_allowed_claims() == (
        WaveSixAllowedClaim.MEASURED_SYSTEM_LEVEL_COGNITION_ATTEMPT,
        WaveSixAllowedClaim.BOUNDED_WAVE_SIX_REVIEW_READY,
        WaveSixAllowedClaim.EVIDENCE_PACKAGE_ASSEMBLED,
        WaveSixAllowedClaim.EXTERNAL_REVIEW_CANDIDATE,
    )
    assert required_wave_six_prohibited_claims() == (
        WaveSixProhibitedClaim.AGI_ACHIEVED,
        WaveSixProhibitedClaim.PRODUCTION_READY,
        WaveSixProhibitedClaim.CERTIFIED_SAFE,
        WaveSixProhibitedClaim.AUTONOMOUS_AUTHORITY_GRANTED,
        WaveSixProhibitedClaim.SELF_VALIDATED_INTELLIGENCE,
        WaveSixProhibitedClaim.HUMAN_REVIEW_NOT_REQUIRED,
        WaveSixProhibitedClaim.TRANSFER_PROVEN_UNIVERSALLY,
    )
    assert required_wave_six_claim_prerequisites() == (
        WaveSixClaimPrerequisite.CLEAN_MASTER_LOOP,
        WaveSixClaimPrerequisite.REALITY_CORRECTED_REASONING,
        WaveSixClaimPrerequisite.FUTURE_REASONING_CHANGED,
        WaveSixClaimPrerequisite.CROSS_DOMAIN_TRANSFER_PRESSURE,
        WaveSixClaimPrerequisite.NOVELTY_PRESSURE,
        WaveSixClaimPrerequisite.NEGATIVE_CONTROL_PRESSURE,
        WaveSixClaimPrerequisite.FALSIFICATION_SURVIVAL,
        WaveSixClaimPrerequisite.HUMAN_REVIEW_APPROVAL,
        WaveSixClaimPrerequisite.INDEPENDENT_REVIEW_PACKET,
    )


def test_claim_boundary_declaration_accepts_bounded_wave_six_language() -> None:
    declaration = _declaration()

    assert declaration.missing_prerequisites == ()
    assert declaration.ready_for_bounded_review
    assert not declaration.blocks_claim
    assert declaration.preserves_no_agi_boundary
    assert declaration.preserves_human_authority
    assert declaration.fingerprint() == declaration.fingerprint()
    assert len(declaration.fingerprint()) == 64


def test_claim_boundary_declaration_reports_missing_prerequisites() -> None:
    declaration = _declaration(
        decision=WaveSixClaimBoundaryDecision.NEEDS_MORE_EVIDENCE,
        satisfied_prerequisites=(
            WaveSixClaimPrerequisite.CLEAN_MASTER_LOOP,
            WaveSixClaimPrerequisite.REALITY_CORRECTED_REASONING,
        ),
    )

    assert declaration.missing_prerequisites == (
        WaveSixClaimPrerequisite.FUTURE_REASONING_CHANGED,
        WaveSixClaimPrerequisite.CROSS_DOMAIN_TRANSFER_PRESSURE,
        WaveSixClaimPrerequisite.NOVELTY_PRESSURE,
        WaveSixClaimPrerequisite.NEGATIVE_CONTROL_PRESSURE,
        WaveSixClaimPrerequisite.FALSIFICATION_SURVIVAL,
        WaveSixClaimPrerequisite.HUMAN_REVIEW_APPROVAL,
        WaveSixClaimPrerequisite.INDEPENDENT_REVIEW_PACKET,
    )
    assert not declaration.ready_for_bounded_review


def test_ready_claim_boundary_requires_all_prerequisites() -> None:
    with pytest.raises(ValueError, match="require all prerequisites"):
        _declaration(
            satisfied_prerequisites=(WaveSixClaimPrerequisite.CLEAN_MASTER_LOOP,),
        )


def test_claim_boundary_rejects_missing_allowed_or_prohibited_claim() -> None:
    with pytest.raises(ValueError, match="allowed claim"):
        WaveSixClaimBoundaryDeclaration(
            declaration_id="missing-allowed",
            boundary_statement="Invalid boundary.",
            allowed_claims=(WaveSixAllowedClaim.EVIDENCE_PACKAGE_ASSEMBLED,),
            prohibited_claims=WAVE_SIX_REQUIRED_PROHIBITED_CLAIMS,
            satisfied_prerequisites=WAVE_SIX_REQUIRED_CLAIM_PREREQUISITES,
            evidence_ids=("evidence",),
            reviewer_questions=("Question?",),
        )

    with pytest.raises(ValueError, match="prohibited claim"):
        WaveSixClaimBoundaryDeclaration(
            declaration_id="missing-prohibited",
            boundary_statement="Invalid boundary.",
            allowed_claims=WAVE_SIX_REQUIRED_ALLOWED_CLAIMS,
            prohibited_claims=(WaveSixProhibitedClaim.AGI_ACHIEVED,),
            satisfied_prerequisites=WAVE_SIX_REQUIRED_CLAIM_PREREQUISITES,
            evidence_ids=("evidence",),
            reviewer_questions=("Question?",),
        )


def test_claim_boundary_rejects_overclaims() -> None:
    with pytest.raises(ValueError, match="must not claim AGI"):
        WaveSixClaimBoundaryDeclaration(
            declaration_id="agi-boundary",
            boundary_statement="Invalid AGI claim.",
            allowed_claims=WAVE_SIX_REQUIRED_ALLOWED_CLAIMS,
            prohibited_claims=WAVE_SIX_REQUIRED_PROHIBITED_CLAIMS,
            satisfied_prerequisites=WAVE_SIX_REQUIRED_CLAIM_PREREQUISITES,
            evidence_ids=("evidence",),
            reviewer_questions=("Question?",),
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="autonomous authority"):
        WaveSixClaimBoundaryDeclaration(
            declaration_id="authority-boundary",
            boundary_statement="Invalid autonomous authority claim.",
            allowed_claims=WAVE_SIX_REQUIRED_ALLOWED_CLAIMS,
            prohibited_claims=WAVE_SIX_REQUIRED_PROHIBITED_CLAIMS,
            satisfied_prerequisites=WAVE_SIX_REQUIRED_CLAIM_PREREQUISITES,
            evidence_ids=("evidence",),
            reviewer_questions=("Question?",),
            allows_autonomous_authority=True,
        )

    with pytest.raises(ValueError, match="self-validation"):
        WaveSixClaimBoundaryDeclaration(
            declaration_id="self-validating-boundary",
            boundary_statement="Invalid self-validation claim.",
            allowed_claims=WAVE_SIX_REQUIRED_ALLOWED_CLAIMS,
            prohibited_claims=WAVE_SIX_REQUIRED_PROHIBITED_CLAIMS,
            satisfied_prerequisites=WAVE_SIX_REQUIRED_CLAIM_PREREQUISITES,
            evidence_ids=("evidence",),
            reviewer_questions=("Question?",),
            self_validated=True,
        )


def test_blocked_claim_boundary_requires_blocking_evidence() -> None:
    with pytest.raises(ValueError, match="blocking evidence"):
        _declaration(
            decision=WaveSixClaimBoundaryDecision.BLOCKED,
            evidence_ids=("evidence-nonblocking",),
        )

    declaration = _declaration(
        decision=WaveSixClaimBoundaryDecision.BLOCKED,
        evidence_ids=("block-evidence-1",),
    )

    assert declaration.blocks_claim
    assert not declaration.ready_for_bounded_review


def test_claim_boundary_assessment_accepts_ready_declaration() -> None:
    assessment = build_wave_six_claim_boundary_assessment(
        assessment_id="assessment-1",
        declarations=(_declaration(declaration_id="boundary-b"), _declaration()),
        notes=("Claim boundary remains bounded and review-gated.",),
    )

    assert assessment.declaration_ids == ("boundary-1", "boundary-b")
    assert assessment.ready_declaration_ids == ("boundary-1", "boundary-b")
    assert assessment.blocked_declaration_ids == ()
    assert assessment.declarations_missing_prerequisites == ()
    assert assessment.has_required_ready_declarations
    assert assessment.ready_for_wave_six_review
    assert assessment.fingerprint() == assessment.fingerprint()
    assert len(assessment.fingerprint()) == 64


def test_claim_boundary_assessment_fails_when_declaration_needs_evidence() -> None:
    assessment = WaveSixClaimBoundaryAssessment(
        assessment_id="assessment-needs-evidence",
        declarations=(
            _declaration(
                decision=WaveSixClaimBoundaryDecision.NEEDS_MORE_EVIDENCE,
                satisfied_prerequisites=(WaveSixClaimPrerequisite.CLEAN_MASTER_LOOP,),
            ),
        ),
    )

    assert assessment.ready_declaration_ids == ()
    assert assessment.declarations_missing_prerequisites == ("boundary-1",)
    assert not assessment.has_required_ready_declarations
    assert not assessment.ready_for_wave_six_review


def test_claim_boundary_assessment_blocks_on_blocked_declaration() -> None:
    assessment = WaveSixClaimBoundaryAssessment(
        assessment_id="assessment-blocked",
        declarations=(
            _declaration(
                decision=WaveSixClaimBoundaryDecision.BLOCKED,
                evidence_ids=("block-evidence-1",),
            ),
        ),
    )

    assert assessment.blocked_declaration_ids == ("boundary-1",)
    assert not assessment.ready_for_wave_six_review


def test_claim_boundary_assessment_rejects_duplicate_declaration_ids() -> None:
    declaration = _declaration()

    with pytest.raises(ValueError, match="Duplicate declaration_id"):
        WaveSixClaimBoundaryAssessment(
            assessment_id="assessment-duplicate",
            declarations=(declaration, declaration),
        )
