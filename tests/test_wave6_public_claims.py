import pytest

from ix_cognition_kernel.wave6_public_claims import (
    WAVE_SIX_PROHIBITED_PUBLIC_CLAIM_FRAGMENTS,
    WAVE_SIX_REQUIRED_PUBLIC_CLAIM_FRAGMENTS,
    WAVE_SIX_REQUIRED_PUBLIC_CLAIM_SURFACES,
    WaveSixPublicClaimDecision,
    WaveSixPublicClaimFinding,
    WaveSixPublicClaimReport,
    WaveSixPublicClaimStatement,
    WaveSixPublicClaimStatus,
    WaveSixPublicClaimSurface,
    build_wave_six_public_claim_report,
    prohibited_wave_six_public_claim_fragments,
    required_wave_six_public_claim_fragments,
    required_wave_six_public_claim_surfaces,
)


def _bounded_text() -> str:
    return (
        "Wave 6 is a measured system-level cognition package for bounded review "
        "under human authority and independent review. It is not an AGI claim."
    )


def _statement(
    surface: WaveSixPublicClaimSurface,
    *,
    statement_id: str | None = None,
    text: str | None = None,
    finding: WaveSixPublicClaimFinding = WaveSixPublicClaimFinding.ACCEPTED,
    requires_follow_up: bool = False,
    blocks_publication: bool = False,
    claims_agi: bool = False,
) -> WaveSixPublicClaimStatement:
    return WaveSixPublicClaimStatement(
        statement_id=statement_id or f"statement-{surface.value}",
        surface=surface,
        text=text or _bounded_text(),
        intended_audience=f"Audience for {surface.value}.",
        evidence_ids=(f"evidence-{surface.value}",),
        reviewer_questions=(f"Does {surface.value} preserve the claim boundary?",),
        finding=finding,
        requires_follow_up=requires_follow_up,
        blocks_publication=blocks_publication,
        claims_agi=claims_agi,
    )


def _complete_statements() -> tuple[WaveSixPublicClaimStatement, ...]:
    return tuple(
        _statement(surface) for surface in WAVE_SIX_REQUIRED_PUBLIC_CLAIM_SURFACES
    )


def _report(
    *,
    statements: tuple[WaveSixPublicClaimStatement, ...] | None = None,
    decision: WaveSixPublicClaimDecision = (
        WaveSixPublicClaimDecision.APPROVE_BOUNDED_PUBLICATION
    ),
) -> WaveSixPublicClaimReport:
    return WaveSixPublicClaimReport(
        report_id="public-claim-report-1",
        statements=statements or _complete_statements(),
        decision=decision,
        generated_by_engine_id="wave6-public-claim-engine",
        human_authority_id="human-authority-1",
        independent_reviewer_id="independent-reviewer-1",
        notes=("Public wording is bounded review language, not an AGI claim.",),
    )


def test_required_public_claim_surfaces_and_fragments_are_locked() -> None:
    assert required_wave_six_public_claim_surfaces() == (
        WaveSixPublicClaimSurface.README,
        WaveSixPublicClaimSurface.GITHUB_ABOUT,
        WaveSixPublicClaimSurface.RELEASE_SUMMARY,
        WaveSixPublicClaimSurface.INDEPENDENT_REVIEW_PACKET,
    )
    assert (
        required_wave_six_public_claim_fragments()
        == WAVE_SIX_REQUIRED_PUBLIC_CLAIM_FRAGMENTS
    )
    assert (
        prohibited_wave_six_public_claim_fragments()
        == WAVE_SIX_PROHIBITED_PUBLIC_CLAIM_FRAGMENTS
    )
    assert "measured system-level cognition" in (
        required_wave_six_public_claim_fragments()
    )
    assert "agi achieved" in prohibited_wave_six_public_claim_fragments()


def test_public_claim_statement_is_accepted_when_bounded() -> None:
    statement = _statement(WaveSixPublicClaimSurface.README)

    assert statement.accepted
    assert not statement.needs_more_evidence
    assert not statement.blocks_bounded_publication
    assert statement.missing_required_fragments == ()
    assert statement.prohibited_matches == ()
    assert not statement.overclaim_present
    assert statement.fingerprint() == statement.fingerprint()
    assert len(statement.fingerprint()) == 64


def test_public_claim_statement_detects_missing_required_fragments() -> None:
    statement = _statement(
        WaveSixPublicClaimSurface.GITHUB_ABOUT,
        text="Wave 6 package summary.",
        finding=WaveSixPublicClaimFinding.NEEDS_MORE_EVIDENCE,
        requires_follow_up=True,
    )

    assert statement.missing_required_fragments == (
        "measured system-level cognition",
        "bounded review",
        "not an agi",
        "human",
        "independent review",
    )
    assert statement.needs_more_evidence
    assert not statement.blocks_bounded_publication


def test_public_claim_statement_detects_prohibited_fragments() -> None:
    statement = _statement(
        WaveSixPublicClaimSurface.SOCIAL_POST,
        text=(
            "Wave 6 is a measured system-level cognition package for bounded "
            "review under human authority and independent review. It is not an "
            "AGI claim. AGI achieved."
        ),
        finding=WaveSixPublicClaimFinding.BLOCKS_PUBLICATION,
        blocks_publication=True,
    )

    assert statement.prohibited_matches == ("agi achieved",)
    assert statement.blocks_bounded_publication


def test_public_claim_statement_rejects_accepted_overclaim() -> None:
    with pytest.raises(ValueError, match="cannot contain overclaims"):
        _statement(WaveSixPublicClaimSurface.README, claims_agi=True)

    with pytest.raises(ValueError, match="cannot contain overclaims"):
        _statement(
            WaveSixPublicClaimSurface.RELEASE_SUMMARY,
            text=(
                "Wave 6 is a measured system-level cognition package for bounded "
                "review under human authority and independent review. It is not "
                "an AGI claim. Production ready."
            ),
        )


def test_public_claim_statement_enforces_finding_semantics() -> None:
    with pytest.raises(ValueError, match="cannot require follow-up"):
        _statement(
            WaveSixPublicClaimSurface.README,
            finding=WaveSixPublicClaimFinding.ACCEPTED,
            requires_follow_up=True,
        )

    with pytest.raises(ValueError, match="require follow-up"):
        _statement(
            WaveSixPublicClaimSurface.README,
            text="Wave 6 needs a better boundary statement.",
            finding=WaveSixPublicClaimFinding.NEEDS_MORE_EVIDENCE,
        )

    with pytest.raises(ValueError, match="require blocker or overclaim"):
        _statement(
            WaveSixPublicClaimSurface.RELEASE_SUMMARY,
            text=_bounded_text(),
            finding=WaveSixPublicClaimFinding.BLOCKS_PUBLICATION,
        )


def test_public_claim_report_is_ready_when_all_required_surfaces_are_clean() -> None:
    report = build_wave_six_public_claim_report(
        report_id="public-claim-report-ready",
        statements=_complete_statements(),
        decision=WaveSixPublicClaimDecision.APPROVE_BOUNDED_PUBLICATION,
        generated_by_engine_id="wave6-public-claim-engine",
        human_authority_id="human-authority-1",
        independent_reviewer_id="independent-reviewer-1",
        notes=("All public surfaces preserve bounded wording.",),
    )

    assert report.present_surfaces == WAVE_SIX_REQUIRED_PUBLIC_CLAIM_SURFACES
    assert report.missing_surfaces == ()
    assert report.accepted_statement_ids == tuple(
        f"statement-{surface.value}"
        for surface in WAVE_SIX_REQUIRED_PUBLIC_CLAIM_SURFACES
    )
    assert report.follow_up_statement_ids == ()
    assert report.blocking_statement_ids == ()
    assert report.status is WaveSixPublicClaimStatus.READY_FOR_BOUNDED_PUBLICATION
    assert report.ready_for_bounded_publication
    assert report.fingerprint() == report.fingerprint()
    assert len(report.fingerprint()) == 64


def test_public_claim_report_reports_missing_surface() -> None:
    report = _report(
        statements=_complete_statements()[:-1],
        decision=WaveSixPublicClaimDecision.HOLD_FOR_MORE_EVIDENCE,
    )

    assert report.missing_surfaces == (
        WaveSixPublicClaimSurface.INDEPENDENT_REVIEW_PACKET,
    )
    assert report.status is WaveSixPublicClaimStatus.NEEDS_MORE_EVIDENCE
    assert not report.ready_for_bounded_publication


def test_public_claim_report_tracks_follow_up_statement() -> None:
    statements = list(_complete_statements())
    statements[1] = _statement(
        WaveSixPublicClaimSurface.GITHUB_ABOUT,
        text="Wave 6 package summary.",
        finding=WaveSixPublicClaimFinding.NEEDS_MORE_EVIDENCE,
        requires_follow_up=True,
    )
    report = _report(
        statements=tuple(statements),
        decision=WaveSixPublicClaimDecision.HOLD_FOR_MORE_EVIDENCE,
    )

    assert report.follow_up_statement_ids == ("statement-github-about",)
    assert report.status is WaveSixPublicClaimStatus.NEEDS_MORE_EVIDENCE


def test_public_claim_report_blocks_on_blocking_statement() -> None:
    statements = list(_complete_statements())
    statements[2] = _statement(
        WaveSixPublicClaimSurface.RELEASE_SUMMARY,
        text=(
            "Wave 6 is a measured system-level cognition package for bounded "
            "review under human authority and independent review. It is not an "
            "AGI claim. True AGI."
        ),
        finding=WaveSixPublicClaimFinding.BLOCKS_PUBLICATION,
        blocks_publication=True,
    )
    report = _report(
        statements=tuple(statements),
        decision=WaveSixPublicClaimDecision.BLOCK_PUBLICATION,
    )

    assert report.blocking_statement_ids == ("statement-release-summary",)
    assert report.status is WaveSixPublicClaimStatus.BLOCKED
    assert not report.ready_for_bounded_publication


def test_approved_public_claim_report_rejects_missing_or_follow_up_statement() -> None:
    with pytest.raises(ValueError, match="require every surface"):
        _report(statements=_complete_statements()[:-1])

    statements = list(_complete_statements())
    statements[0] = _statement(
        WaveSixPublicClaimSurface.README,
        text="Wave 6 package summary.",
        finding=WaveSixPublicClaimFinding.NEEDS_MORE_EVIDENCE,
        requires_follow_up=True,
    )

    with pytest.raises(ValueError, match="cannot need follow-up"):
        _report(statements=tuple(statements))


def test_blocked_public_claim_report_requires_blocking_statement() -> None:
    with pytest.raises(ValueError, match="require a blocker"):
        _report(decision=WaveSixPublicClaimDecision.BLOCK_PUBLICATION)


def test_public_claim_report_lookup_and_duplicate_rejection() -> None:
    report = _report(
        statements=(_statement(WaveSixPublicClaimSurface.README),),
        decision=WaveSixPublicClaimDecision.HOLD_FOR_MORE_EVIDENCE,
    )

    statement = report.statement_for_surface(WaveSixPublicClaimSurface.README)

    assert statement is not None
    assert statement.statement_id == "statement-readme"
    assert report.statement_for_surface(WaveSixPublicClaimSurface.SOCIAL_POST) is None

    duplicate = _statement(WaveSixPublicClaimSurface.README)
    with pytest.raises(ValueError, match="Duplicate statement_id"):
        _report(
            statements=(duplicate, duplicate),
            decision=WaveSixPublicClaimDecision.HOLD_FOR_MORE_EVIDENCE,
        )

    with pytest.raises(ValueError, match="Duplicate surface"):
        _report(
            statements=(
                duplicate,
                _statement(
                    WaveSixPublicClaimSurface.README,
                    statement_id="different-statement-id",
                ),
            ),
            decision=WaveSixPublicClaimDecision.HOLD_FOR_MORE_EVIDENCE,
        )
