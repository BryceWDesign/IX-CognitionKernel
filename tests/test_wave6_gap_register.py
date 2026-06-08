import pytest

from ix_cognition_kernel.wave6_gap_register import (
    WAVE_SIX_REQUIRED_GAP_KINDS,
    WaveSixEvidenceGap,
    WaveSixEvidenceGapRegister,
    WaveSixGapDisposition,
    WaveSixGapKind,
    WaveSixGapRegisterDecision,
    WaveSixGapRegisterStatus,
    WaveSixGapSeverity,
    WaveSixGapState,
    build_wave_six_gap_register,
    required_wave_six_gap_kinds,
)


def _boundary_statement() -> str:
    return (
        "This Wave-6 measured system-level cognition package is released for "
        "bounded review under human authority and independent review. It is not "
        "an AGI claim."
    )


def _gap(
    kind: WaveSixGapKind,
    *,
    gap_id: str | None = None,
    severity: WaveSixGapSeverity = WaveSixGapSeverity.MINOR,
    state: WaveSixGapState = WaveSixGapState.RESOLVED,
    disposition: WaveSixGapDisposition = WaveSixGapDisposition.TRACK,
    evidence_ids: tuple[str, ...] | None = None,
    requires_follow_up: bool = False,
    blocks_review: bool = False,
    claim_boundary_impact: bool = False,
) -> WaveSixEvidenceGap:
    required_evidence_ids = (f"required-{kind.value}",)
    return WaveSixEvidenceGap(
        gap_id=gap_id or f"gap-{kind.value}",
        kind=kind,
        severity=severity,
        state=state,
        disposition=disposition,
        summary=f"Evidence gap check for {kind.value}.",
        affected_artifact_ids=(f"artifact-{kind.value}",),
        required_evidence_ids=required_evidence_ids,
        mitigation_summary=f"Mitigation for {kind.value}.",
        reviewer_question=f"Is the {kind.value} gap closed or bounded?",
        evidence_ids=evidence_ids
        if evidence_ids is not None
        else required_evidence_ids,
        requires_follow_up=requires_follow_up,
        blocks_review=blocks_review,
        claim_boundary_impact=claim_boundary_impact,
    )


def _complete_gaps() -> tuple[WaveSixEvidenceGap, ...]:
    return tuple(_gap(kind) for kind in WAVE_SIX_REQUIRED_GAP_KINDS)


def _register(
    *,
    gaps: tuple[WaveSixEvidenceGap, ...] | None = None,
    decision: WaveSixGapRegisterDecision = (
        WaveSixGapRegisterDecision.READY_FOR_BOUNDED_REVIEW
    ),
    claims_agi: bool = False,
    claim_boundary_statement: str | None = None,
) -> WaveSixEvidenceGapRegister:
    return WaveSixEvidenceGapRegister(
        register_id="gap-register-1",
        gaps=gaps or _complete_gaps(),
        decision=decision,
        claim_boundary_statement=claim_boundary_statement or _boundary_statement(),
        generated_by_engine_id="wave6-gap-register-engine",
        human_authority_id="human-authority-1",
        independent_reviewer_id="independent-reviewer-1",
        claims_agi=claims_agi,
        notes=("Gaps are explicit bounded-review evidence, not AGI proof.",),
    )


def test_required_gap_kinds_are_locked() -> None:
    assert required_wave_six_gap_kinds() == (
        WaveSixGapKind.CI_VERIFICATION_GAP,
        WaveSixGapKind.REQUIRED_EVIDENCE_GAP,
        WaveSixGapKind.FINGERPRINT_REPRODUCTION_GAP,
        WaveSixGapKind.TRANSFER_EVIDENCE_GAP,
        WaveSixGapKind.FALSIFICATION_EVIDENCE_GAP,
        WaveSixGapKind.HUMAN_REVIEW_GAP,
        WaveSixGapKind.INDEPENDENT_REVIEW_GAP,
        WaveSixGapKind.CLAIM_BOUNDARY_GAP,
        WaveSixGapKind.PUBLIC_WORDING_GAP,
    )


def test_evidence_gap_is_resolved_and_fingerprinted() -> None:
    gap = _gap(WaveSixGapKind.CI_VERIFICATION_GAP)

    assert gap.resolved
    assert gap.evidence_complete
    assert gap.missing_evidence_ids == ()
    assert not gap.needs_more_evidence
    assert not gap.blocks_bounded_review
    assert gap.fingerprint() == gap.fingerprint()
    assert len(gap.fingerprint()) == 64


def test_evidence_gap_tracks_missing_required_evidence() -> None:
    gap = _gap(
        WaveSixGapKind.REQUIRED_EVIDENCE_GAP,
        state=WaveSixGapState.OPEN,
        disposition=WaveSixGapDisposition.REQUIRE_EVIDENCE,
        evidence_ids=(),
        requires_follow_up=True,
    )

    assert gap.missing_evidence_ids == ("required-required-evidence-gap",)
    assert not gap.evidence_complete
    assert gap.needs_more_evidence
    assert not gap.resolved


def test_evidence_gap_allows_noncritical_bounded_risk_acceptance() -> None:
    gap = _gap(
        WaveSixGapKind.FINGERPRINT_REPRODUCTION_GAP,
        severity=WaveSixGapSeverity.MINOR,
        state=WaveSixGapState.ACCEPTED_FOR_BOUNDED_REVIEW,
        disposition=WaveSixGapDisposition.ACCEPT_BOUNDED_RISK,
        evidence_ids=(),
    )

    assert gap.accepted_for_bounded_review
    assert not gap.needs_more_evidence
    assert not gap.blocks_bounded_review


def test_evidence_gap_enforces_fail_closed_semantics() -> None:
    with pytest.raises(ValueError, match="Resolved evidence gaps require"):
        _gap(
            WaveSixGapKind.TRANSFER_EVIDENCE_GAP,
            state=WaveSixGapState.RESOLVED,
            evidence_ids=(),
        )

    with pytest.raises(ValueError, match="must block review"):
        _gap(
            WaveSixGapKind.FALSIFICATION_EVIDENCE_GAP,
            state=WaveSixGapState.BLOCKING,
            disposition=WaveSixGapDisposition.BLOCK_WAVE_SIX_REVIEW,
        )

    with pytest.raises(ValueError, match="Open evidence gaps require follow-up"):
        _gap(
            WaveSixGapKind.HUMAN_REVIEW_GAP,
            state=WaveSixGapState.OPEN,
            disposition=WaveSixGapDisposition.REQUIRE_EVIDENCE,
        )


def test_critical_gap_cannot_be_accepted_as_bounded_risk() -> None:
    with pytest.raises(ValueError, match="Critical evidence gaps cannot be accepted"):
        _gap(
            WaveSixGapKind.INDEPENDENT_REVIEW_GAP,
            severity=WaveSixGapSeverity.CRITICAL,
            state=WaveSixGapState.ACCEPTED_FOR_BOUNDED_REVIEW,
            disposition=WaveSixGapDisposition.ACCEPT_BOUNDED_RISK,
            evidence_ids=(),
        )


def test_gap_register_is_ready_when_complete_and_bounded() -> None:
    register = build_wave_six_gap_register(
        register_id="gap-register-ready",
        gaps=_complete_gaps(),
        decision=WaveSixGapRegisterDecision.READY_FOR_BOUNDED_REVIEW,
        claim_boundary_statement=_boundary_statement(),
        generated_by_engine_id="wave6-gap-register-engine",
        human_authority_id="human-authority-1",
        independent_reviewer_id="independent-reviewer-1",
        notes=("All required evidence-gap kinds are represented.",),
    )

    assert register.present_gap_kinds == WAVE_SIX_REQUIRED_GAP_KINDS
    assert register.missing_gap_kinds == ()
    assert register.follow_up_gap_ids == ()
    assert register.blocking_gap_ids == ()
    assert register.status is WaveSixGapRegisterStatus.READY
    assert register.ready_for_bounded_review
    assert register.fingerprint() == register.fingerprint()
    assert len(register.fingerprint()) == 64


def test_gap_register_reports_missing_gap_kind() -> None:
    register = _register(
        gaps=_complete_gaps()[:-1],
        decision=WaveSixGapRegisterDecision.HOLD_FOR_MORE_EVIDENCE,
    )

    assert register.missing_gap_kinds == (WaveSixGapKind.PUBLIC_WORDING_GAP,)
    assert register.status is WaveSixGapRegisterStatus.NEEDS_MORE_EVIDENCE
    assert not register.ready_for_bounded_review


def test_gap_register_tracks_follow_up_gap() -> None:
    gaps = list(_complete_gaps())
    gaps[3] = _gap(
        WaveSixGapKind.TRANSFER_EVIDENCE_GAP,
        state=WaveSixGapState.OPEN,
        disposition=WaveSixGapDisposition.REQUIRE_EVIDENCE,
        evidence_ids=(),
        requires_follow_up=True,
    )
    register = _register(
        gaps=tuple(gaps),
        decision=WaveSixGapRegisterDecision.HOLD_FOR_MORE_EVIDENCE,
    )

    assert register.follow_up_gap_ids == ("gap-transfer-evidence-gap",)
    assert register.status is WaveSixGapRegisterStatus.NEEDS_MORE_EVIDENCE
    assert not register.ready_for_bounded_review


def test_gap_register_blocks_on_blocking_gap_or_overclaim() -> None:
    gaps = list(_complete_gaps())
    gaps[7] = _gap(
        WaveSixGapKind.CLAIM_BOUNDARY_GAP,
        severity=WaveSixGapSeverity.CRITICAL,
        state=WaveSixGapState.BLOCKING,
        disposition=WaveSixGapDisposition.BLOCK_WAVE_SIX_REVIEW,
        blocks_review=True,
        claim_boundary_impact=True,
    )
    blocked = _register(
        gaps=tuple(gaps),
        decision=WaveSixGapRegisterDecision.BLOCK_REVIEW,
    )

    assert blocked.blocking_gap_ids == ("gap-claim-boundary-gap",)
    assert blocked.claim_boundary_gap_ids == ("gap-claim-boundary-gap",)
    assert blocked.status is WaveSixGapRegisterStatus.BLOCKED

    overclaim = _register(
        decision=WaveSixGapRegisterDecision.BLOCK_REVIEW,
        claims_agi=True,
    )

    assert overclaim.overclaim_present
    assert overclaim.status is WaveSixGapRegisterStatus.BLOCKED


def test_ready_gap_register_rejects_missing_or_follow_up_gaps() -> None:
    with pytest.raises(ValueError, match="require every gap kind"):
        _register(gaps=_complete_gaps()[:-1])

    gaps = list(_complete_gaps())
    gaps[5] = _gap(
        WaveSixGapKind.HUMAN_REVIEW_GAP,
        state=WaveSixGapState.OPEN,
        disposition=WaveSixGapDisposition.REQUIRE_EVIDENCE,
        evidence_ids=(),
        requires_follow_up=True,
    )

    with pytest.raises(ValueError, match="cannot need follow-up"):
        _register(gaps=tuple(gaps))


def test_blocked_gap_register_requires_blocker_or_overclaim() -> None:
    with pytest.raises(ValueError, match="require blocker or overclaim"):
        _register(decision=WaveSixGapRegisterDecision.BLOCK_REVIEW)


def test_gap_register_reports_invalid_claim_boundary_statement() -> None:
    register = _register(
        decision=WaveSixGapRegisterDecision.HOLD_FOR_MORE_EVIDENCE,
        claim_boundary_statement="Wave 6 is done.",
    )

    assert not register.claim_boundary_statement_valid
    assert register.status is WaveSixGapRegisterStatus.NEEDS_MORE_EVIDENCE


def test_gap_register_lookup_and_duplicate_rejection() -> None:
    register = _register(
        gaps=(_gap(WaveSixGapKind.PUBLIC_WORDING_GAP),),
        decision=WaveSixGapRegisterDecision.HOLD_FOR_MORE_EVIDENCE,
    )

    gap = register.gap_for_kind(WaveSixGapKind.PUBLIC_WORDING_GAP)

    assert gap is not None
    assert gap.gap_id == "gap-public-wording-gap"
    assert register.gap_for_kind(WaveSixGapKind.CI_VERIFICATION_GAP) is None

    duplicate = _gap(WaveSixGapKind.PUBLIC_WORDING_GAP)
    with pytest.raises(ValueError, match="Duplicate gap_id"):
        _register(
            gaps=(duplicate, duplicate),
            decision=WaveSixGapRegisterDecision.HOLD_FOR_MORE_EVIDENCE,
        )

    with pytest.raises(ValueError, match="Duplicate gap kind"):
        _register(
            gaps=(
                duplicate,
                _gap(WaveSixGapKind.PUBLIC_WORDING_GAP, gap_id="different-gap"),
            ),
            decision=WaveSixGapRegisterDecision.HOLD_FOR_MORE_EVIDENCE,
        )
