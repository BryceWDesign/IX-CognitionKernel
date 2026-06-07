import pytest

from ix_cognition_kernel.wave6_outcome_declaration import (
    WAVE_SIX_REQUIRED_OUTCOME_SURFACES,
    WaveSixFinalOutcomeDeclaration,
    WaveSixOutcomeDecision,
    WaveSixOutcomeFinding,
    WaveSixOutcomeStatus,
    WaveSixOutcomeSurface,
    WaveSixOutcomeSurfaceKind,
    build_outcome_surface_from_artifact,
    build_wave_six_final_outcome_declaration,
    required_wave_six_outcome_surfaces,
)


class _Artifact:
    def __init__(self, fingerprint: str = "artifact-fingerprint") -> None:
        self._fingerprint = fingerprint

    def fingerprint(self) -> str:
        return self._fingerprint


def _boundary_statement() -> str:
    return (
        "This Wave-6 measured system-level cognition package is released for "
        "bounded review under human authority and independent review. It is not "
        "an AGI claim."
    )


def _surface(
    kind: WaveSixOutcomeSurfaceKind,
    *,
    surface_id: str | None = None,
    finding: WaveSixOutcomeFinding = WaveSixOutcomeFinding.READY,
    requires_follow_up: bool = False,
    blocks_outcome: bool = False,
) -> WaveSixOutcomeSurface:
    return WaveSixOutcomeSurface(
        surface_id=surface_id or f"surface-{kind.value}",
        kind=kind,
        artifact_fingerprint=f"fingerprint-{kind.value}",
        summary=f"Outcome surface for {kind.value}.",
        evidence_ids=(f"evidence-{kind.value}",),
        reviewer_questions=(f"Can {kind.value} support bounded review?",),
        finding=finding,
        requires_follow_up=requires_follow_up,
        blocks_outcome=blocks_outcome,
    )


def _complete_surfaces() -> tuple[WaveSixOutcomeSurface, ...]:
    return tuple(_surface(kind) for kind in WAVE_SIX_REQUIRED_OUTCOME_SURFACES)


def _declaration(
    *,
    surfaces: tuple[WaveSixOutcomeSurface, ...] | None = None,
    decision: WaveSixOutcomeDecision = (
        WaveSixOutcomeDecision.DECLARE_BOUNDED_REVIEW_READY
    ),
    claims_agi: bool = False,
    claim_boundary_statement: str | None = None,
) -> WaveSixFinalOutcomeDeclaration:
    return WaveSixFinalOutcomeDeclaration(
        declaration_id="outcome-1",
        surfaces=surfaces or _complete_surfaces(),
        decision=decision,
        claim_boundary_statement=claim_boundary_statement or _boundary_statement(),
        generated_by_engine_id="wave6-final-outcome-engine",
        human_authority_id="human-authority-1",
        independent_reviewer_id="independent-reviewer-1",
        claims_agi=claims_agi,
        notes=("Final outcome is bounded review readiness, not AGI achieved.",),
    )


def test_required_outcome_surfaces_are_locked() -> None:
    assert required_wave_six_outcome_surfaces() == (
        WaveSixOutcomeSurfaceKind.FINAL_DOSSIER,
        WaveSixOutcomeSurfaceKind.CI_RECEIPT_LEDGER,
        WaveSixOutcomeSurfaceKind.EVIDENCE_GAP_REGISTER,
        WaveSixOutcomeSurfaceKind.PUBLIC_CLAIM_REPORT,
        WaveSixOutcomeSurfaceKind.CONSISTENCY_REPORT,
    )


def test_outcome_surface_is_evidence_bound_and_fingerprinted() -> None:
    surface = _surface(WaveSixOutcomeSurfaceKind.FINAL_DOSSIER)

    assert surface.ready
    assert not surface.needs_more_evidence
    assert not surface.blocks_bounded_outcome
    assert surface.fingerprint() == surface.fingerprint()
    assert len(surface.fingerprint()) == 64


def test_outcome_surface_enforces_finding_semantics() -> None:
    with pytest.raises(ValueError, match="cannot require follow-up"):
        _surface(
            WaveSixOutcomeSurfaceKind.CI_RECEIPT_LEDGER,
            finding=WaveSixOutcomeFinding.READY,
            requires_follow_up=True,
        )

    with pytest.raises(ValueError, match="require follow-up"):
        _surface(
            WaveSixOutcomeSurfaceKind.CI_RECEIPT_LEDGER,
            finding=WaveSixOutcomeFinding.NEEDS_MORE_EVIDENCE,
        )

    with pytest.raises(ValueError, match="must block outcome"):
        _surface(
            WaveSixOutcomeSurfaceKind.PUBLIC_CLAIM_REPORT,
            finding=WaveSixOutcomeFinding.BLOCKED,
        )


def test_final_outcome_declaration_is_ready_when_all_surfaces_are_ready() -> None:
    declaration = build_wave_six_final_outcome_declaration(
        declaration_id="outcome-ready",
        surfaces=_complete_surfaces(),
        decision=WaveSixOutcomeDecision.DECLARE_BOUNDED_REVIEW_READY,
        claim_boundary_statement=_boundary_statement(),
        generated_by_engine_id="wave6-final-outcome-engine",
        human_authority_id="human-authority-1",
        independent_reviewer_id="independent-reviewer-1",
        notes=("All late-stage surfaces are ready for bounded review.",),
    )

    assert declaration.present_surface_kinds == WAVE_SIX_REQUIRED_OUTCOME_SURFACES
    assert declaration.missing_surface_kinds == ()
    assert declaration.follow_up_surface_ids == ()
    assert declaration.blocking_surface_ids == ()
    assert declaration.status is WaveSixOutcomeStatus.BOUNDED_REVIEW_READY
    assert declaration.ready_for_bounded_review
    assert not declaration.agi_claim_allowed
    assert "not an AGI claim" in declaration.public_outcome_statement
    assert declaration.fingerprint() == declaration.fingerprint()
    assert len(declaration.fingerprint()) == 64


def test_final_outcome_reports_missing_surface_kind() -> None:
    declaration = _declaration(
        surfaces=_complete_surfaces()[:-1],
        decision=WaveSixOutcomeDecision.CONTINUE_EVIDENCE_COLLECTION,
    )

    assert declaration.missing_surface_kinds == (
        WaveSixOutcomeSurfaceKind.CONSISTENCY_REPORT,
    )
    assert declaration.status is WaveSixOutcomeStatus.NEEDS_MORE_EVIDENCE
    assert not declaration.ready_for_bounded_review


def test_final_outcome_tracks_follow_up_surface() -> None:
    surfaces = list(_complete_surfaces())
    surfaces[1] = _surface(
        WaveSixOutcomeSurfaceKind.CI_RECEIPT_LEDGER,
        finding=WaveSixOutcomeFinding.NEEDS_MORE_EVIDENCE,
        requires_follow_up=True,
    )
    declaration = _declaration(
        surfaces=tuple(surfaces),
        decision=WaveSixOutcomeDecision.CONTINUE_EVIDENCE_COLLECTION,
    )

    assert declaration.follow_up_surface_ids == ("surface-ci-receipt-ledger",)
    assert declaration.status is WaveSixOutcomeStatus.NEEDS_MORE_EVIDENCE


def test_final_outcome_blocks_on_blocking_surface_or_overclaim() -> None:
    surfaces = list(_complete_surfaces())
    surfaces[3] = _surface(
        WaveSixOutcomeSurfaceKind.PUBLIC_CLAIM_REPORT,
        finding=WaveSixOutcomeFinding.BLOCKED,
        blocks_outcome=True,
    )
    blocked = _declaration(
        surfaces=tuple(surfaces),
        decision=WaveSixOutcomeDecision.BLOCK_WAVE_SIX_INTERPRETATION,
    )

    assert blocked.blocking_surface_ids == ("surface-public-claim-report",)
    assert blocked.status is WaveSixOutcomeStatus.BLOCKED
    assert "blocked" in blocked.public_outcome_statement

    overclaim = _declaration(
        decision=WaveSixOutcomeDecision.BLOCK_WAVE_SIX_INTERPRETATION,
        claims_agi=True,
    )

    assert overclaim.overclaim_present
    assert overclaim.status is WaveSixOutcomeStatus.BLOCKED


def test_ready_final_outcome_rejects_missing_or_follow_up_surfaces() -> None:
    with pytest.raises(ValueError, match="require every surface"):
        _declaration(surfaces=_complete_surfaces()[:-1])

    surfaces = list(_complete_surfaces())
    surfaces[2] = _surface(
        WaveSixOutcomeSurfaceKind.EVIDENCE_GAP_REGISTER,
        finding=WaveSixOutcomeFinding.NEEDS_MORE_EVIDENCE,
        requires_follow_up=True,
    )

    with pytest.raises(ValueError, match="cannot require follow-up"):
        _declaration(surfaces=tuple(surfaces))


def test_blocked_final_outcome_requires_blocker_or_overclaim() -> None:
    with pytest.raises(ValueError, match="require blocker or overclaim"):
        _declaration(decision=WaveSixOutcomeDecision.BLOCK_WAVE_SIX_INTERPRETATION)


def test_final_outcome_reports_invalid_claim_boundary_statement() -> None:
    declaration = _declaration(
        decision=WaveSixOutcomeDecision.CONTINUE_EVIDENCE_COLLECTION,
        claim_boundary_statement="Wave 6 is ready.",
    )

    assert not declaration.claim_boundary_statement_valid
    assert declaration.status is WaveSixOutcomeStatus.NEEDS_MORE_EVIDENCE


def test_final_outcome_lookup_and_duplicate_rejection() -> None:
    declaration = _declaration(
        surfaces=(_surface(WaveSixOutcomeSurfaceKind.FINAL_DOSSIER),),
        decision=WaveSixOutcomeDecision.CONTINUE_EVIDENCE_COLLECTION,
    )

    surface = declaration.surface_for_kind(WaveSixOutcomeSurfaceKind.FINAL_DOSSIER)

    assert surface is not None
    assert surface.surface_id == "surface-final-dossier"
    assert (
        declaration.surface_for_kind(WaveSixOutcomeSurfaceKind.CI_RECEIPT_LEDGER)
        is None
    )

    duplicate = _surface(WaveSixOutcomeSurfaceKind.FINAL_DOSSIER)
    with pytest.raises(ValueError, match="Duplicate surface_id"):
        _declaration(
            surfaces=(duplicate, duplicate),
            decision=WaveSixOutcomeDecision.CONTINUE_EVIDENCE_COLLECTION,
        )

    with pytest.raises(ValueError, match="Duplicate surface kind"):
        _declaration(
            surfaces=(
                duplicate,
                _surface(
                    WaveSixOutcomeSurfaceKind.FINAL_DOSSIER,
                    surface_id="different-surface-id",
                ),
            ),
            decision=WaveSixOutcomeDecision.CONTINUE_EVIDENCE_COLLECTION,
        )


def test_outcome_surface_builder_uses_fingerprinted_artifact_protocol() -> None:
    surface = build_outcome_surface_from_artifact(
        surface_id="surface-from-ready-artifact",
        kind=WaveSixOutcomeSurfaceKind.FINAL_DOSSIER,
        artifact=_Artifact("ready-fingerprint"),
        ready=True,
        summary="Final dossier is ready.",
        evidence_ids=("dossier-evidence",),
        reviewer_questions=("Can the final dossier be recomputed?",),
    )

    assert surface.ready
    assert surface.artifact_fingerprint == "ready-fingerprint"

    follow_up = build_outcome_surface_from_artifact(
        surface_id="surface-from-not-ready-artifact",
        kind=WaveSixOutcomeSurfaceKind.CI_RECEIPT_LEDGER,
        artifact=_Artifact("ci-fingerprint"),
        ready=False,
        summary="CI receipt ledger still needs evidence.",
        evidence_ids=("ci-evidence",),
        reviewer_questions=("Are CI receipts complete?",),
    )

    assert follow_up.needs_more_evidence
    assert follow_up.requires_follow_up
