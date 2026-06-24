import pytest

from ix_cognition_kernel.wave7_cognitive_identity import (
    CognitiveIdentity,
    ContinuityMarker,
    IdentityContinuityDecision,
    IdentityRevision,
    KnownWeakness,
    WeaknessStatus,
    build_identity_continuity_report,
)


def _marker(marker_id: str = "marker-1") -> ContinuityMarker:
    return ContinuityMarker(
        marker_id=marker_id,
        stage="experience-compilation",
        summary="Measured correction preserved identity continuity.",
        evidence_ids=("marker-evidence-1",),
    )


def _weakness(
    weakness_id: str = "weakness-transfer-1",
    *,
    status: WeaknessStatus = WeaknessStatus.ACTIVE,
    superseded_by_revision_id: str = "",
) -> KnownWeakness:
    return KnownWeakness(
        weakness_id=weakness_id,
        domain="cross-domain transfer",
        description="The system overweights prior causal assumptions in novelty.",
        evidence_ids=("weakness-evidence-1",),
        status=status,
        superseded_by_revision_id=superseded_by_revision_id,
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


def _revision() -> IdentityRevision:
    return IdentityRevision(
        revision_id="revision-1",
        previous_identity_id="identity-wave7-0",
        revised_identity_id="identity-wave7-1",
        reason="Measured transfer failure changed future causal weighting.",
        evidence_ids=("revision-evidence-1",),
        changed_belief_ids=("belief-causal-weight-1",),
        changed_memory_ids=("memory-transfer-rule-1",),
        future_reasoning_change=(
            "Future novelty trials must test the corrected causal condition "
            "before reusing prior assumptions."
        ),
    )


def test_cognitive_identity_is_evidence_bound_and_fingerprinted() -> None:
    identity = _identity()

    assert identity.doctrine_ids == (
        "human-authority-final",
        "memory-is-not-truth",
        "output-is-not-evidence",
    )
    assert identity.continuity_marker_ids == ("marker-1",)
    assert identity.known_weakness_ids == ("weakness-transfer-1",)
    assert identity.evidence_ids == ("identity-evidence-1",)
    assert identity.fingerprint() == identity.fingerprint()
    assert len(identity.fingerprint()) == 64


def test_cognitive_identity_rejects_memory_as_truth() -> None:
    with pytest.raises(ValueError, match="must not treat memory as truth"):
        CognitiveIdentity(
            identity_id="identity-bad-memory",
            mission="Preserve continuity.",
            doctrine_ids=("memory-is-truth",),
            continuity_marker_ids=("marker-1",),
            known_weakness_ids=(),
            evidence_ids=("identity-evidence-1",),
            human_authority_ref="human-review-board-1",
            treats_memory_as_truth=True,
        )


def test_continuity_marker_rejects_memory_truth_and_autonomous_execution() -> None:
    with pytest.raises(ValueError, match="must not treat memory as truth"):
        ContinuityMarker(
            marker_id="marker-memory-truth",
            stage="memory-update",
            summary="Bad marker.",
            evidence_ids=("marker-evidence-1",),
            claims_memory_truth=True,
        )

    with pytest.raises(ValueError, match="must not allow autonomous execution"):
        ContinuityMarker(
            marker_id="marker-exec",
            stage="runtime-handoff",
            summary="Bad marker.",
            evidence_ids=("marker-evidence-1",),
            allows_autonomous_execution=True,
        )


def test_known_weakness_remains_visible_until_superseded() -> None:
    active = _weakness()
    superseded = _weakness(
        weakness_id="weakness-transfer-2",
        status=WeaknessStatus.SUPERSEDED,
        superseded_by_revision_id="revision-1",
    )

    assert active.active
    assert not active.resolved
    assert not superseded.active
    assert superseded.resolved
    assert superseded.superseded_by_revision_id == "revision-1"


def test_known_weakness_rejects_bad_supersession_state() -> None:
    with pytest.raises(ValueError, match="require superseded_by_revision_id"):
        _weakness(status=WeaknessStatus.SUPERSEDED)

    with pytest.raises(ValueError, match="Only superseded weaknesses"):
        _weakness(
            status=WeaknessStatus.ACTIVE,
            superseded_by_revision_id="revision-1",
        )


def test_identity_revision_requires_evidence_and_blocks_self_approval() -> None:
    revision = _revision()

    assert revision.changes_future_reasoning
    assert revision.requires_human_review
    assert revision.fingerprint() == revision.fingerprint()
    assert len(revision.fingerprint()) == 64

    with pytest.raises(ValueError, match="must not self-approve"):
        IdentityRevision(
            revision_id="revision-self-approved",
            previous_identity_id="identity-wave7-0",
            revised_identity_id="identity-wave7-1",
            reason="Bad self approval.",
            evidence_ids=("revision-evidence-1",),
            changed_belief_ids=("belief-1",),
            changed_memory_ids=(),
            future_reasoning_change="Change future reasoning.",
            self_approved=True,
        )


def test_identity_revision_rejects_agi_claim_and_missing_change_ids() -> None:
    with pytest.raises(ValueError, match="must not claim AGI"):
        IdentityRevision(
            revision_id="revision-agi",
            previous_identity_id="identity-wave7-0",
            revised_identity_id="identity-wave7-1",
            reason="Bad AGI claim.",
            evidence_ids=("revision-evidence-1",),
            changed_belief_ids=("belief-1",),
            changed_memory_ids=(),
            future_reasoning_change="Change future reasoning.",
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="changed belief or memory ids"):
        IdentityRevision(
            revision_id="revision-no-change",
            previous_identity_id="identity-wave7-0",
            revised_identity_id="identity-wave7-1",
            reason="No changed ids.",
            evidence_ids=("revision-evidence-1",),
            changed_belief_ids=(),
            changed_memory_ids=(),
            future_reasoning_change="Change future reasoning.",
        )


def test_identity_continuity_report_preserves_active_weaknesses() -> None:
    report = build_identity_continuity_report(
        report_id="identity-report-1",
        identity=_identity(),
        markers=(_marker(),),
        revisions=(_revision(),),
        weaknesses=(_weakness(),),
        notes=("Identity continuity remains under human authority.",),
        decision=IdentityContinuityDecision.READY_FOR_REVIEW,
    )

    assert report.marker_ids == ("marker-1",)
    assert report.revision_ids == ("revision-1",)
    assert report.active_weakness_ids == ("weakness-transfer-1",)
    assert report.resolved_weakness_ids == ()
    assert report.has_future_reasoning_revision
    assert report.ready_for_review
    assert not report.blocks_claim
    assert "identity-evidence-1" in report.evidence_ids
    assert "marker-evidence-1" in report.evidence_ids
    assert "revision-evidence-1" in report.evidence_ids
    assert "weakness-evidence-1" in report.evidence_ids
    assert report.fingerprint() == report.fingerprint()
    assert len(report.fingerprint()) == 64


def test_identity_continuity_report_rejects_missing_marker() -> None:
    with pytest.raises(ValueError, match="missing continuity markers"):
        build_identity_continuity_report(
            report_id="identity-report-missing-marker",
            identity=_identity(),
            markers=(),
            weaknesses=(_weakness(),),
        )


def test_identity_continuity_report_rejects_duplicate_markers() -> None:
    marker = _marker()

    with pytest.raises(ValueError, match="Duplicate marker_id"):
        build_identity_continuity_report(
            report_id="identity-report-duplicate-marker",
            identity=_identity(),
            markers=(marker, marker),
            weaknesses=(_weakness(),),
        )
