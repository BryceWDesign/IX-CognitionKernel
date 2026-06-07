import pytest

from ix_cognition_kernel.wave6_final_dossier import (
    WAVE_SIX_REQUIRED_DOSSIER_ENTRY_KINDS,
    WaveSixDossierDecision,
    WaveSixDossierEntryKind,
    WaveSixDossierFinding,
    WaveSixDossierStatus,
    WaveSixFinalDossier,
    WaveSixFinalDossierEntry,
    build_dossier_entry_from_artifact,
    build_wave_six_final_dossier,
    required_wave_six_dossier_entry_kinds,
)


class _BoundedArtifact:
    def __init__(
        self, *, ready: bool, fingerprint: str = "artifact-fingerprint"
    ) -> None:
        self._ready = ready
        self._fingerprint = fingerprint

    @property
    def ready_for_bounded_review(self) -> bool:
        return self._ready

    def fingerprint(self) -> str:
        return self._fingerprint


def _boundary_statement() -> str:
    return (
        "This Wave-6 measured system-level cognition package is released for "
        "bounded review under human authority and independent review. It is not "
        "an AGI claim."
    )


def _entry(
    kind: WaveSixDossierEntryKind,
    *,
    entry_id: str | None = None,
    finding: WaveSixDossierFinding = WaveSixDossierFinding.INCLUDED,
    requires_follow_up: bool = False,
    blocks_handoff: bool = False,
) -> WaveSixFinalDossierEntry:
    return WaveSixFinalDossierEntry(
        entry_id=entry_id or f"entry-{kind.value}",
        kind=kind,
        artifact_fingerprint=f"fingerprint-{kind.value}",
        source_label=f"source-{kind.value}",
        summary=f"Final dossier entry for {kind.value}.",
        evidence_ids=(f"evidence-{kind.value}",),
        reviewer_questions=(f"Can {kind.value} be reviewed without overclaiming?",),
        finding=finding,
        requires_follow_up=requires_follow_up,
        blocks_handoff=blocks_handoff,
    )


def _complete_entries() -> tuple[WaveSixFinalDossierEntry, ...]:
    return tuple(_entry(kind) for kind in WAVE_SIX_REQUIRED_DOSSIER_ENTRY_KINDS)


def _dossier(
    *,
    entries: tuple[WaveSixFinalDossierEntry, ...] | None = None,
    decision: WaveSixDossierDecision = WaveSixDossierDecision.READY_FOR_BOUNDED_HANDOFF,
    claims_agi: bool = False,
    claim_boundary_statement: str | None = None,
) -> WaveSixFinalDossier:
    return WaveSixFinalDossier(
        dossier_id="final-dossier-1",
        entries=entries or _complete_entries(),
        decision=decision,
        claim_boundary_statement=claim_boundary_statement or _boundary_statement(),
        generated_by_engine_id="wave6-final-dossier-engine",
        human_authority_id="human-authority-1",
        independent_reviewer_id="independent-reviewer-1",
        claims_agi=claims_agi,
        notes=("Final handoff remains bounded review, not AGI achieved.",),
    )


def test_required_dossier_entry_kinds_are_locked() -> None:
    assert required_wave_six_dossier_entry_kinds() == (
        WaveSixDossierEntryKind.MATURITY_DECISION_RECORD,
        WaveSixDossierEntryKind.AUDIT_MANIFEST,
        WaveSixDossierEntryKind.RELEASE_MANIFEST,
        WaveSixDossierEntryKind.REVIEW_SUMMARY,
        WaveSixDossierEntryKind.CONSISTENCY_REPORT,
        WaveSixDossierEntryKind.PUBLIC_CLAIM_REPORT,
        WaveSixDossierEntryKind.EVIDENCE_GAP_REGISTER,
        WaveSixDossierEntryKind.CI_RECEIPT_LEDGER,
    )


def test_final_dossier_entry_is_evidence_bound_and_fingerprinted() -> None:
    entry = _entry(WaveSixDossierEntryKind.MATURITY_DECISION_RECORD)

    assert entry.included
    assert not entry.needs_more_evidence
    assert not entry.blocks_bounded_handoff
    assert entry.fingerprint() == entry.fingerprint()
    assert len(entry.fingerprint()) == 64


def test_final_dossier_entry_enforces_finding_semantics() -> None:
    with pytest.raises(ValueError, match="cannot require follow-up"):
        _entry(
            WaveSixDossierEntryKind.CONSISTENCY_REPORT,
            finding=WaveSixDossierFinding.INCLUDED,
            requires_follow_up=True,
        )

    with pytest.raises(ValueError, match="require follow-up"):
        _entry(
            WaveSixDossierEntryKind.CONSISTENCY_REPORT,
            finding=WaveSixDossierFinding.NEEDS_MORE_EVIDENCE,
        )

    with pytest.raises(ValueError, match="must block handoff"):
        _entry(
            WaveSixDossierEntryKind.PUBLIC_CLAIM_REPORT,
            finding=WaveSixDossierFinding.BLOCKS_DOSSIER,
        )


def test_final_dossier_is_ready_when_complete_and_bounded() -> None:
    dossier = build_wave_six_final_dossier(
        dossier_id="final-dossier-ready",
        entries=_complete_entries(),
        decision=WaveSixDossierDecision.READY_FOR_BOUNDED_HANDOFF,
        claim_boundary_statement=_boundary_statement(),
        generated_by_engine_id="wave6-final-dossier-engine",
        human_authority_id="human-authority-1",
        independent_reviewer_id="independent-reviewer-1",
        notes=("Every final dossier entry is included and bounded.",),
    )

    assert dossier.present_entry_kinds == WAVE_SIX_REQUIRED_DOSSIER_ENTRY_KINDS
    assert dossier.missing_entry_kinds == ()
    assert dossier.follow_up_entry_ids == ()
    assert dossier.blocking_entry_ids == ()
    assert dossier.status is WaveSixDossierStatus.READY
    assert dossier.ready_for_bounded_handoff
    assert dossier.claim_boundary_statement_valid
    assert dossier.fingerprint() == dossier.fingerprint()
    assert len(dossier.fingerprint()) == 64


def test_final_dossier_reports_missing_entry_kind() -> None:
    dossier = _dossier(
        entries=_complete_entries()[:-1],
        decision=WaveSixDossierDecision.HOLD_FOR_MORE_EVIDENCE,
    )

    assert dossier.missing_entry_kinds == (WaveSixDossierEntryKind.CI_RECEIPT_LEDGER,)
    assert dossier.status is WaveSixDossierStatus.NEEDS_MORE_EVIDENCE
    assert not dossier.ready_for_bounded_handoff


def test_final_dossier_tracks_follow_up_entry() -> None:
    entries = list(_complete_entries())
    entries[4] = _entry(
        WaveSixDossierEntryKind.CONSISTENCY_REPORT,
        finding=WaveSixDossierFinding.NEEDS_MORE_EVIDENCE,
        requires_follow_up=True,
    )
    dossier = _dossier(
        entries=tuple(entries),
        decision=WaveSixDossierDecision.HOLD_FOR_MORE_EVIDENCE,
    )

    assert dossier.follow_up_entry_ids == ("entry-consistency-report",)
    assert dossier.status is WaveSixDossierStatus.NEEDS_MORE_EVIDENCE


def test_final_dossier_blocks_on_blocking_entry_or_overclaim() -> None:
    entries = list(_complete_entries())
    entries[5] = _entry(
        WaveSixDossierEntryKind.PUBLIC_CLAIM_REPORT,
        finding=WaveSixDossierFinding.BLOCKS_DOSSIER,
        blocks_handoff=True,
    )
    blocked = _dossier(
        entries=tuple(entries),
        decision=WaveSixDossierDecision.BLOCK_HANDOFF,
    )

    assert blocked.blocking_entry_ids == ("entry-public-claim-report",)
    assert blocked.status is WaveSixDossierStatus.BLOCKED

    overclaim = _dossier(
        decision=WaveSixDossierDecision.BLOCK_HANDOFF,
        claims_agi=True,
    )

    assert overclaim.overclaim_present
    assert overclaim.status is WaveSixDossierStatus.BLOCKED


def test_ready_final_dossier_rejects_missing_or_follow_up_entries() -> None:
    with pytest.raises(ValueError, match="require every entry kind"):
        _dossier(entries=_complete_entries()[:-1])

    entries = list(_complete_entries())
    entries[6] = _entry(
        WaveSixDossierEntryKind.EVIDENCE_GAP_REGISTER,
        finding=WaveSixDossierFinding.NEEDS_MORE_EVIDENCE,
        requires_follow_up=True,
    )

    with pytest.raises(ValueError, match="cannot require follow-up"):
        _dossier(entries=tuple(entries))


def test_blocked_final_dossier_requires_blocker_or_overclaim() -> None:
    with pytest.raises(ValueError, match="require blocker or overclaim"):
        _dossier(decision=WaveSixDossierDecision.BLOCK_HANDOFF)


def test_final_dossier_reports_invalid_claim_boundary_statement() -> None:
    dossier = _dossier(
        decision=WaveSixDossierDecision.HOLD_FOR_MORE_EVIDENCE,
        claim_boundary_statement="Wave 6 is ready.",
    )

    assert not dossier.claim_boundary_statement_valid
    assert dossier.status is WaveSixDossierStatus.NEEDS_MORE_EVIDENCE


def test_final_dossier_lookup_and_duplicate_rejection() -> None:
    dossier = _dossier(
        entries=(_entry(WaveSixDossierEntryKind.RELEASE_MANIFEST),),
        decision=WaveSixDossierDecision.HOLD_FOR_MORE_EVIDENCE,
    )

    entry = dossier.entry_for_kind(WaveSixDossierEntryKind.RELEASE_MANIFEST)

    assert entry is not None
    assert entry.entry_id == "entry-release-manifest"
    assert dossier.entry_for_kind(WaveSixDossierEntryKind.CI_RECEIPT_LEDGER) is None

    duplicate = _entry(WaveSixDossierEntryKind.RELEASE_MANIFEST)
    with pytest.raises(ValueError, match="Duplicate entry_id"):
        _dossier(
            entries=(duplicate, duplicate),
            decision=WaveSixDossierDecision.HOLD_FOR_MORE_EVIDENCE,
        )

    with pytest.raises(ValueError, match="Duplicate entry kind"):
        _dossier(
            entries=(
                duplicate,
                _entry(
                    WaveSixDossierEntryKind.RELEASE_MANIFEST,
                    entry_id="different-entry-id",
                ),
            ),
            decision=WaveSixDossierDecision.HOLD_FOR_MORE_EVIDENCE,
        )


def test_dossier_entry_builder_uses_bounded_artifact_protocol() -> None:
    entry = build_dossier_entry_from_artifact(
        entry_id="entry-from-artifact",
        kind=WaveSixDossierEntryKind.CI_RECEIPT_LEDGER,
        artifact=_BoundedArtifact(ready=True, fingerprint="ci-ledger-fingerprint"),
        source_label="ci-ledger",
        summary="CI receipt ledger is included.",
        evidence_ids=("ci-evidence",),
        reviewer_questions=("Can CI receipts be recomputed?",),
    )

    assert entry.included
    assert entry.artifact_fingerprint == "ci-ledger-fingerprint"

    follow_up = build_dossier_entry_from_artifact(
        entry_id="entry-from-not-ready-artifact",
        kind=WaveSixDossierEntryKind.EVIDENCE_GAP_REGISTER,
        artifact=_BoundedArtifact(ready=False),
        source_label="gap-register",
        summary="Gap register still needs evidence.",
        evidence_ids=("gap-evidence",),
        reviewer_questions=("Are all gaps closed?",),
    )

    assert follow_up.needs_more_evidence
    assert follow_up.requires_follow_up
