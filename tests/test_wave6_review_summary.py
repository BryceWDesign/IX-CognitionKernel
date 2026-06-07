import pytest

from ix_cognition_kernel.wave6_review_summary import (
    WAVE_SIX_REQUIRED_REVIEW_SUMMARY_SECTIONS,
    WaveSixReviewSummaryArtifact,
    WaveSixReviewSummaryDecision,
    WaveSixReviewSummaryFinding,
    WaveSixReviewSummarySection,
    WaveSixReviewSummarySectionKind,
    WaveSixReviewSummaryStatus,
    build_wave_six_review_summary_artifact,
    required_wave_six_review_summary_sections,
)


def _boundary_statement() -> str:
    return (
        "This Wave-6 measured system-level cognition package is released for "
        "bounded review under human authority and independent review. It is not "
        "an AGI claim."
    )


def _section(
    kind: WaveSixReviewSummarySectionKind,
    *,
    section_id: str | None = None,
    finding: WaveSixReviewSummaryFinding = WaveSixReviewSummaryFinding.INCLUDED,
    requires_follow_up: bool = False,
    blocks_summary: bool = False,
) -> WaveSixReviewSummarySection:
    return WaveSixReviewSummarySection(
        section_id=section_id or f"section-{kind.value}",
        kind=kind,
        title=kind.value.replace("-", " ").title(),
        body=f"Bounded Wave 6 summary body for {kind.value}.",
        evidence_ids=(f"evidence-{kind.value}",),
        reviewer_questions=(f"Does {kind.value} stay inside the claim boundary?",),
        finding=finding,
        requires_follow_up=requires_follow_up,
        blocks_summary=blocks_summary,
    )


def _complete_sections() -> tuple[WaveSixReviewSummarySection, ...]:
    return tuple(
        _section(kind) for kind in WAVE_SIX_REQUIRED_REVIEW_SUMMARY_SECTIONS
    )


def _summary(
    *,
    sections: tuple[WaveSixReviewSummarySection, ...] | None = None,
    decision: WaveSixReviewSummaryDecision = (
        WaveSixReviewSummaryDecision.READY_FOR_RELEASE_SUMMARY
    ),
    claims_agi: bool = False,
    claim_boundary_statement: str | None = None,
) -> WaveSixReviewSummaryArtifact:
    return WaveSixReviewSummaryArtifact(
        summary_id="summary-1",
        title="IX-CognitionKernel Wave 6 Bounded Review Summary",
        source_release_manifest_fingerprint="release-manifest-fingerprint",
        sections=sections or _complete_sections(),
        decision=decision,
        claim_boundary_statement=claim_boundary_statement or _boundary_statement(),
        generated_by_engine_id="wave6-review-summary-engine",
        human_authority_id="human-authority-1",
        independent_reviewer_id="independent-reviewer-1",
        claims_agi=claims_agi,
        notes=("This artifact supports release review; README update remains separate.",),
    )


def test_required_review_summary_sections_are_locked() -> None:
    assert required_wave_six_review_summary_sections() == (
        WaveSixReviewSummarySectionKind.CLAIM_BOUNDARY,
        WaveSixReviewSummarySectionKind.WHAT_WAS_ASSEMBLED,
        WaveSixReviewSummarySectionKind.WHAT_WAS_TESTED,
        WaveSixReviewSummarySectionKind.WHAT_CAN_BLOCK,
        WaveSixReviewSummarySectionKind.HUMAN_AUTHORITY,
        WaveSixReviewSummarySectionKind.INDEPENDENT_REVIEW,
        WaveSixReviewSummarySectionKind.NON_CLAIMS,
        WaveSixReviewSummarySectionKind.NEXT_REVIEW_ACTIONS,
    )


def test_review_summary_section_is_evidence_bound_and_fingerprinted() -> None:
    section = _section(WaveSixReviewSummarySectionKind.CLAIM_BOUNDARY)

    assert section.included
    assert not section.needs_more_evidence
    assert not section.blocks_bounded_summary
    assert section.markdown_block().startswith("## Claim Boundary")
    assert section.fingerprint() == section.fingerprint()
    assert len(section.fingerprint()) == 64


def test_review_summary_section_enforces_finding_semantics() -> None:
    with pytest.raises(ValueError, match="cannot require follow-up"):
        _section(
            WaveSixReviewSummarySectionKind.WHAT_WAS_TESTED,
            finding=WaveSixReviewSummaryFinding.INCLUDED,
            requires_follow_up=True,
        )

    with pytest.raises(ValueError, match="require follow-up"):
        _section(
            WaveSixReviewSummarySectionKind.WHAT_WAS_TESTED,
            finding=WaveSixReviewSummaryFinding.NEEDS_MORE_EVIDENCE,
        )

    with pytest.raises(ValueError, match="must block summary"):
        _section(
            WaveSixReviewSummarySectionKind.WHAT_CAN_BLOCK,
            finding=WaveSixReviewSummaryFinding.BLOCKS_SUMMARY,
        )


def test_review_summary_artifact_is_ready_when_complete_and_bounded() -> None:
    summary = build_wave_six_review_summary_artifact(
        summary_id="summary-ready",
        title="IX-CognitionKernel Wave 6 Bounded Review Summary",
        source_release_manifest_fingerprint="release-manifest-fingerprint",
        sections=_complete_sections(),
        decision=WaveSixReviewSummaryDecision.READY_FOR_RELEASE_SUMMARY,
        claim_boundary_statement=_boundary_statement(),
        generated_by_engine_id="wave6-review-summary-engine",
        human_authority_id="human-authority-1",
        independent_reviewer_id="independent-reviewer-1",
        notes=("Every summary section is included for bounded release.",),
    )

    assert summary.present_section_kinds == WAVE_SIX_REQUIRED_REVIEW_SUMMARY_SECTIONS
    assert summary.missing_section_kinds == ()
    assert summary.follow_up_section_ids == ()
    assert summary.blocking_section_ids == ()
    assert summary.claim_boundary_statement_valid
    assert summary.status is WaveSixReviewSummaryStatus.READY_FOR_BOUNDED_RELEASE
    assert summary.ready_for_bounded_release
    assert "# IX-CognitionKernel Wave 6 Bounded Review Summary" in (
        summary.render_markdown()
    )
    assert summary.fingerprint() == summary.fingerprint()
    assert len(summary.fingerprint()) == 64


def test_review_summary_artifact_reports_missing_section() -> None:
    summary = _summary(
        sections=_complete_sections()[:-1],
        decision=WaveSixReviewSummaryDecision.HOLD_FOR_MORE_EVIDENCE,
    )

    assert summary.missing_section_kinds == (
        WaveSixReviewSummarySectionKind.NEXT_REVIEW_ACTIONS,
    )
    assert summary.status is WaveSixReviewSummaryStatus.NEEDS_MORE_EVIDENCE
    assert not summary.ready_for_bounded_release


def test_ready_review_summary_rejects_missing_or_follow_up_sections() -> None:
    with pytest.raises(ValueError, match="require every section"):
        _summary(sections=_complete_sections()[:-1])

    sections = list(_complete_sections())
    sections[2] = _section(
        WaveSixReviewSummarySectionKind.WHAT_WAS_TESTED,
        finding=WaveSixReviewSummaryFinding.NEEDS_MORE_EVIDENCE,
        requires_follow_up=True,
    )

    with pytest.raises(ValueError, match="cannot require follow-up"):
        _summary(sections=tuple(sections))


def test_review_summary_blocks_on_blocking_section_or_overclaim() -> None:
    sections = list(_complete_sections())
    sections[3] = _section(
        WaveSixReviewSummarySectionKind.WHAT_CAN_BLOCK,
        finding=WaveSixReviewSummaryFinding.BLOCKS_SUMMARY,
        blocks_summary=True,
    )
    blocked = _summary(
        sections=tuple(sections),
        decision=WaveSixReviewSummaryDecision.BLOCK_SUMMARY,
    )

    assert blocked.blocking_section_ids == ("section-what-can-block",)
    assert blocked.status is WaveSixReviewSummaryStatus.BLOCKED
    assert not blocked.ready_for_bounded_release

    overclaim = _summary(
        decision=WaveSixReviewSummaryDecision.BLOCK_SUMMARY,
        claims_agi=True,
    )

    assert overclaim.overclaim_present
    assert overclaim.status is WaveSixReviewSummaryStatus.BLOCKED


def test_blocked_review_summary_requires_blocker_or_overclaim() -> None:
    with pytest.raises(ValueError, match="require blocker or overclaim"):
        _summary(decision=WaveSixReviewSummaryDecision.BLOCK_SUMMARY)


def test_review_summary_reports_invalid_claim_boundary_statement() -> None:
    summary = _summary(
        decision=WaveSixReviewSummaryDecision.HOLD_FOR_MORE_EVIDENCE,
        claim_boundary_statement="Wave 6 is done.",
    )

    assert not summary.claim_boundary_statement_valid
    assert summary.status is WaveSixReviewSummaryStatus.NEEDS_MORE_EVIDENCE


def test_review_summary_lookup_returns_present_section_only() -> None:
    summary = _summary(
        sections=(_section(WaveSixReviewSummarySectionKind.CLAIM_BOUNDARY),),
        decision=WaveSixReviewSummaryDecision.HOLD_FOR_MORE_EVIDENCE,
    )

    section = summary.section_for_kind(WaveSixReviewSummarySectionKind.CLAIM_BOUNDARY)

    assert section is not None
    assert section.section_id == "section-claim-boundary"
    assert (
        summary.section_for_kind(WaveSixReviewSummarySectionKind.WHAT_WAS_TESTED)
        is None
    )


def test_review_summary_rejects_duplicate_section_ids_or_kinds() -> None:
    section = _section(WaveSixReviewSummarySectionKind.CLAIM_BOUNDARY)

    with pytest.raises(ValueError, match="Duplicate section_id"):
        _summary(
            sections=(section, section),
            decision=WaveSixReviewSummaryDecision.HOLD_FOR_MORE_EVIDENCE,
        )

    with pytest.raises(ValueError, match="Duplicate section kind"):
        _summary(
            sections=(
                section,
                _section(
                    WaveSixReviewSummarySectionKind.CLAIM_BOUNDARY,
                    section_id="different-section-id",
                ),
            ),
            decision=WaveSixReviewSummaryDecision.HOLD_FOR_MORE_EVIDENCE,
        )


def test_review_summary_requires_non_empty_authority_fields() -> None:
    with pytest.raises(ValueError, match="human_authority_id must not be empty"):
        WaveSixReviewSummaryArtifact(
            summary_id="summary-invalid",
            title="Invalid Summary",
            source_release_manifest_fingerprint="release-fingerprint",
            sections=_complete_sections(),
            decision=WaveSixReviewSummaryDecision.HOLD_FOR_MORE_EVIDENCE,
            claim_boundary_statement=_boundary_statement(),
            generated_by_engine_id="wave6-review-summary-engine",
            human_authority_id=" ",
            independent_reviewer_id="independent-reviewer-1",
        )
