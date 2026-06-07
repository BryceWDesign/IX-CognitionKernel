import pytest

from ix_cognition_kernel.wave6_public_claims import (
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


def _bounded_text(surface: WaveSixPublicClaimSurface) -> str:
    return (
        f"The {surface.value} describes a Wave-6 measured system-level cognition "
        "package released for bounded review under human authority and "
        "independent review. It is not an AGI claim."
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
        text=text or _bounded_text(surface),
        intended_audience="bounded Wave 6 reviewers",
        evidence_ids=(f"evidence-{surface.value}",),
        reviewer_questions=(
            f"Does the {surface.value} wording avoid AGI and autonomy overclaims?",
        ),
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


def test_required_public_claim_sets_are_locked() -> None:
    assert required_wave_six_public_claim_surfaces() == (
        WaveSixPublicClaimSurface.README,
        WaveSixPublicClaimSurface.GITHUB_ABOUT,
        WaveSixPublicClaimSurface.RELEASE_SUMMARY,
        WaveSixPublicClaimSurface.INDEPENDENT_REVIEW_PACKET,
    )
    assert "not an agi" in required_wave_six_public_claim_fragments()
    assert "agi achieved" in prohibited_wave_six_public_claim_fragments()


def test_public_claim_statement_is_evidence_bound_and_fingerprinted() -> None:
    statement = _statement(WaveSixPublicClaimSurface.README)

    assert statement.accepted
    assert statement.missing_required_fragments == ()
    assert statement.prohibited_matches == ()
    assert not statement.needs_more_evidence
    assert not statement.blocks_bounded_publication
    assert statement.fingerprint() == statement.fingerprint()
    assert len(statement.fingerprint()) == 64


def test_public_claim_statement_detects_missing_required_fragments() -> None:
    statement = _statement(
        WaveSixPublicClaimSurface.README,
        text="This is a careful repository summary.",
        finding=WaveSixPublicClaimFinding.NEEDS_MORE_EVIDENCE,
        requires_follow_up=True,
    )

    assert "measured system-level cognition" in statement.missing_required_fragments
    assert statement.needs_more_evidence
    assert not statement.blocks_bounded_publication


def test_public_claim_statement_detects_prohibited_overclaim() -> None:
    statement = _statement(
        WaveSixPublicClaimSurface.SOCIAL_POST,
        text=(
            "The repo says AGI achieved and production ready, which should never "
            "pass as bounded Wave 6 wording."
        ),
        finding=WaveSixPublicClaimFinding.BLOCKS_PUBLICATION,
        blocks_publication=True,
    )

    assert "agi achieved" in statement.prohibited_matches
    assert "production ready" in statement.prohibited_matches
    assert statement.blocks_bounded_publication


def test_accepted_public_claim_rejects_missing_boundary_or_overclaim() -> None:
    with pytest.raises(ValueError, match="require boundary fragments"):
        _statement(
            WaveSixPublicClaimSurface.README,
            text="Wave 6 is ready.",
        )

    with pytest.raises(ValueError, match="cannot contain overclaims"):
        _statement(
            WaveSixPublicClaimSurface.README,
            text=(
                _bounded_text(WaveSixPublicClaimSurface.README)
                + " AGI achieved."
            ),
        )


def test_public_claim_statement_enforces_finding_semantics() -> None:
    with pytest.raises(ValueError, match="cannot require follow-up"):
        _statement(
            WaveSixPublicClaimSurface.README,
            requires_follow_up=True,
        )

    with pytest.raises(ValueError, match="require follow-up"):
        _statement(
            WaveSixPublicClaimSurface.README,
            text="Needs more evidence.",
            finding=WaveSixPublicClaimFinding.NEEDS_MORE_EVIDENCE,
        )

    with pytest.raises(ValueError, match="require blocker or overclaim"):
        _statement(
            WaveSixPublicClaimSurface.README,
            finding=WaveSixPublicClaimFinding.BLOCKS_PUBLICATION,
        )


def test_public_claim_report_is_ready_when_all_surfaces_are_clean() -> None:
    report = build_wave_six_public_claim_report(
        report_id="public-claim-report-ready",
        statements=_complete_statements(),
        decision=WaveSixPublicClaimDecision.APPROVE_BOUNDED_PUBLICATION,
        generated_by_engine_id="wave6-public-claim-engine",
        human_authority_id="human-authority-1",
        independent_reviewer_id="independent-reviewer-1",
        notes=("All public wording is bounded and review-gated.",),
    )

    assert report.present_surfaces == WAVE_SIX_REQUIRED_PUBLIC_CLAIM_SURFACES
    assert report.missing_surfaces == ()
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


def test_public_claim_report_blocks_on_public_overclaim() -> None:
    statements = list(_complete_statements())
    statements[0] = _statement(
        WaveSixPublicClaimSurface.README,
        text=_bounded_text(WaveSixPublicClaimSurface.README) + " True AGI.",
        finding=WaveSixPublicClaimFinding.BLOCKS_PUBLICATION,
        blocks_publication=True,
    )
    report = _report(
        statements=tuple(statements),
        decision=WaveSixPublicClaimDecision.BLOCK_PUBLICATION,
    )

    assert report.blocking_statement_ids == ("statement-readme",)
    assert report.status is WaveSixPublicClaimStatus.BLOCKED
    assert not report.ready_for_bounded_publication


def test_approved_public_claim_report_rejects_gaps_or_follow_up() -> None:
    with pytest.raises(ValueError, match="require every surface"):
        _report(statements=_complete_statements()[:-1])

    statements = list(_complete_statements())
    statements[1] = _statement(
        WaveSixPublicClaimSurface.GITHUB_ABOUT,
        text="GitHub about needs more evidence.",
        finding=WaveSixPublicClaimFinding.NEEDS_MORE_EVIDENCE,
        requires_follow_up=True,
    )
    with pytest.raises(ValueError, match="cannot need follow-up"):
        _report(statements=tuple(statements))


def test_blocked_public_claim_report_requires_blocking_statement() -> None:
    with pytest.raises(ValueError, match="require a blocker"):
        _report(decision=WaveSixPublicClaimDecision.BLOCK_PUBLICATION)


def test_public_claim_report_lookup_returns_present_surface_only() -> None:
    report = _report(
        statements=(_statement(WaveSixPublicClaimSurface.README),),
        decision=WaveSixPublicClaimDecision.HOLD_FOR_MORE_EVIDENCE,
    )

    statement = report.statement_for_surface(WaveSixPublicClaimSurface.README)

    assert statement is not None
    assert statement.statement_id == "statement-readme"
    assert report.statement_for_surface(WaveSixPublicClaimSurface.SOCIAL_POST) is None


def test_public_claim_report_rejects_duplicate_ids_or_surfaces() -> None:
    statement = _statement(WaveSixPublicClaimSurface.README)

    with pytest.raises(ValueError, match="Duplicate statement_id"):
        _report(
            statements=(statement, statement),
            decision=WaveSixPublicClaimDecision.HOLD_FOR_MORE_EVIDENCE,
        )

    with pytest.raises(ValueError, match="Duplicate surface"):
        _report(
            statements=(
                statement,
                _statement(
                    WaveSixPublicClaimSurface.README,
                    statement_id="different-statement-id",
                ),
            ),
            decision=WaveSixPublicClaimDecision.HOLD_FOR_MORE_EVIDENCE,
        )
