import pytest

from ix_cognition_kernel.wave7_cognitive_identity import CognitiveIdentity
from ix_cognition_kernel.wave7_continuity_ledger import (
    ContinuityLedgerDecision,
    ContinuityLedgerEntry,
    ContinuityLedgerEntryKind,
    ContinuityLedgerFinding,
    build_continuity_ledger,
)


def _identity() -> CognitiveIdentity:
    return CognitiveIdentity(
        identity_id="identity-wave7-1",
        mission="Pursue evidence-bound reality-corrected cognition.",
        doctrine_ids=(
            "output-is-not-evidence",
            "memory-is-not-truth",
            "human-authority-final",
        ),
        continuity_marker_ids=("marker-1",),
        known_weakness_ids=("weakness-transfer-1",),
        evidence_ids=("identity-evidence-1",),
        human_authority_ref="human-review-board-1",
    )


def _entry(
    entry_id: str = "entry-1",
    *,
    kind: ContinuityLedgerEntryKind = ContinuityLedgerEntryKind.CONTINUITY_MARKER,
    subject_id: str = "identity-wave7-1",
    evidence_ids: tuple[str, ...] = ("entry-evidence-1",),
    previous_entry_id: str = "",
    marker_id: str = "marker-1",
    revision_id: str = "",
    weakness_id: str = "",
    finding: ContinuityLedgerFinding = ContinuityLedgerFinding.RECORDED,
    requires_human_review: bool = False,
    blocks_continuity: bool = False,
) -> ContinuityLedgerEntry:
    return ContinuityLedgerEntry(
        entry_id=entry_id,
        kind=kind,
        subject_id=subject_id,
        summary="Recorded continuity event for Wave 7 identity.",
        evidence_ids=evidence_ids,
        previous_entry_id=previous_entry_id,
        marker_id=marker_id,
        revision_id=revision_id,
        weakness_id=weakness_id,
        finding=finding,
        requires_human_review=requires_human_review,
        blocks_continuity=blocks_continuity,
    )


def test_continuity_ledger_entry_is_evidence_bound_and_fingerprinted() -> None:
    entry = _entry()

    assert entry.entry_id == "entry-1"
    assert entry.marker_id == "marker-1"
    assert entry.evidence_ids == ("entry-evidence-1",)
    assert not entry.needs_review
    assert not entry.needs_more_evidence
    assert not entry.blocks_claim
    assert entry.fingerprint() == entry.fingerprint()
    assert len(entry.fingerprint()) == 64


def test_continuity_ledger_entry_rejects_memory_truth_and_execution() -> None:
    with pytest.raises(ValueError, match="must not claim memory truth"):
        ContinuityLedgerEntry(
            entry_id="entry-memory-truth",
            kind=ContinuityLedgerEntryKind.IDENTITY_SNAPSHOT,
            subject_id="identity-wave7-1",
            summary="Bad memory claim.",
            evidence_ids=("entry-evidence-1",),
            claims_memory_truth=True,
        )

    with pytest.raises(ValueError, match="must not allow autonomous execution"):
        ContinuityLedgerEntry(
            entry_id="entry-execution",
            kind=ContinuityLedgerEntryKind.IDENTITY_SNAPSHOT,
            subject_id="identity-wave7-1",
            summary="Bad execution claim.",
            evidence_ids=("entry-evidence-1",),
            allows_autonomous_execution=True,
        )


def test_continuity_marker_entries_require_marker_id() -> None:
    with pytest.raises(ValueError, match="require marker_id"):
        _entry(marker_id="")


def test_identity_revision_entries_require_revision_id() -> None:
    with pytest.raises(ValueError, match="require revision_id"):
        _entry(
            kind=ContinuityLedgerEntryKind.IDENTITY_REVISION,
            marker_id="",
            revision_id="",
        )


def test_known_weakness_entries_require_weakness_id() -> None:
    with pytest.raises(ValueError, match="require weakness_id"):
        _entry(
            kind=ContinuityLedgerEntryKind.KNOWN_WEAKNESS,
            marker_id="",
            weakness_id="",
        )


def test_review_and_blocking_findings_fail_closed() -> None:
    with pytest.raises(ValueError, match="require human review"):
        _entry(
            finding=ContinuityLedgerFinding.NEEDS_REVIEW,
            requires_human_review=False,
        )

    with pytest.raises(ValueError, match="must block continuity"):
        _entry(
            finding=ContinuityLedgerFinding.BLOCKS_CONTINUITY,
            blocks_continuity=False,
        )

    with pytest.raises(ValueError, match="cannot block continuity"):
        _entry(blocks_continuity=True)


def test_continuity_ledger_collects_markers_evidence_and_status() -> None:
    revision_entry = _entry(
        entry_id="entry-2",
        kind=ContinuityLedgerEntryKind.IDENTITY_REVISION,
        previous_entry_id="entry-1",
        marker_id="",
        revision_id="revision-1",
        evidence_ids=("revision-evidence-1",),
        finding=ContinuityLedgerFinding.NEEDS_REVIEW,
        requires_human_review=True,
    )
    weakness_entry = _entry(
        entry_id="entry-3",
        kind=ContinuityLedgerEntryKind.KNOWN_WEAKNESS,
        previous_entry_id="entry-2",
        marker_id="",
        weakness_id="weakness-transfer-1",
        evidence_ids=("weakness-evidence-1",),
        finding=ContinuityLedgerFinding.NEEDS_MORE_EVIDENCE,
    )

    ledger = build_continuity_ledger(
        ledger_id="ledger-1",
        identity=_identity(),
        entries=(_entry(), revision_entry, weakness_entry),
        decision=ContinuityLedgerDecision.NEEDS_MORE_EVIDENCE,
        notes=("Weakness remains visible for review.",),
    )

    assert ledger.entry_ids == ("entry-1", "entry-2", "entry-3")
    assert ledger.marker_ids == ("marker-1",)
    assert ledger.revision_ids == ("revision-1",)
    assert ledger.weakness_ids == ("weakness-transfer-1",)
    assert ledger.review_entry_ids == ("entry-2",)
    assert ledger.more_evidence_entry_ids == ("entry-3",)
    assert ledger.blocked_entry_ids == ()
    assert ledger.chain_complete
    assert not ledger.ready_for_review
    assert not ledger.blocks_claim
    assert "identity-evidence-1" in ledger.evidence_ids
    assert "revision-evidence-1" in ledger.evidence_ids
    assert "weakness-evidence-1" in ledger.evidence_ids
    assert ledger.fingerprint() == ledger.fingerprint()
    assert len(ledger.fingerprint()) == 64


def test_continuity_ledger_ready_for_review_requires_no_blockers() -> None:
    ledger = build_continuity_ledger(
        ledger_id="ledger-ready",
        identity=_identity(),
        entries=(_entry(),),
        decision=ContinuityLedgerDecision.READY_FOR_REVIEW,
    )

    assert ledger.ready_for_review
    assert not ledger.blocks_claim


def test_continuity_ledger_rejects_missing_identity_marker() -> None:
    with pytest.raises(ValueError, match="missing identity continuity markers"):
        build_continuity_ledger(
            ledger_id="ledger-missing-marker",
            identity=_identity(),
            entries=(
                _entry(
                    kind=ContinuityLedgerEntryKind.IDENTITY_SNAPSHOT,
                    marker_id="",
                ),
            ),
        )


def test_continuity_ledger_rejects_missing_previous_entry() -> None:
    with pytest.raises(ValueError, match="missing previous ids"):
        build_continuity_ledger(
            ledger_id="ledger-missing-previous",
            identity=_identity(),
            entries=(
                _entry(),
                _entry(
                    entry_id="entry-2",
                    kind=ContinuityLedgerEntryKind.MEASURED_OUTCOME,
                    marker_id="",
                    previous_entry_id="entry-missing",
                ),
            ),
        )


def test_continuity_ledger_blocks_claim_when_entry_blocks() -> None:
    blocking_entry = _entry(
        entry_id="entry-blocking",
        kind=ContinuityLedgerEntryKind.MEASURED_OUTCOME,
        marker_id="",
        finding=ContinuityLedgerFinding.BLOCKS_CONTINUITY,
        blocks_continuity=True,
    )

    ledger = build_continuity_ledger(
        ledger_id="ledger-blocked",
        identity=_identity(),
        entries=(_entry(), blocking_entry),
        decision=ContinuityLedgerDecision.BLOCKED,
    )

    assert ledger.blocked_entry_ids == ("entry-blocking",)
    assert ledger.blocks_claim
    assert not ledger.ready_for_review
