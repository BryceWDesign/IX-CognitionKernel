from dataclasses import dataclass

import pytest

from ix_cognition_kernel.wave4_contracts import (
    WaveFourArtifactKind,
    WaveFourCapabilityArea,
)
from ix_cognition_kernel.wave4_maturity_declaration import (
    WaveFourMaturityDeclarationDecision,
    WaveFourMaturityDeclarationStatus,
)
from ix_cognition_kernel.wave4_review_docket import (
    DEFAULT_WAVE_FOUR_REVIEW_DECISION_OPTIONS,
    REQUIRED_WAVE_FOUR_DOCKET_ENTRY_KINDS,
    WaveFourHumanReviewDocket,
    WaveFourReviewDecisionOption,
    WaveFourReviewDocketDecision,
    WaveFourReviewDocketEntry,
    WaveFourReviewDocketEntryKind,
    WaveFourReviewDocketStatus,
    WaveFourReviewerAssignment,
    build_wave_four_human_review_docket,
)


@dataclass(frozen=True)
class FakeScorecard:
    scorecard_id: str = "scorecard-001"


@dataclass(frozen=True)
class FakeReviewPacket:
    packet_id: str = "packet-001"
    scorecard: FakeScorecard = FakeScorecard()
    all_evidence_ids: tuple[str, ...] = (
        "evidence:declaration",
        "evidence:packet",
        "evidence:scorecard",
    )
    scenario_ids: tuple[str, ...] = ("worldtwin:review-docket",)
    blackfox_receipt_ids: tuple[str, ...] = ("blackfox:review-docket",)
    required_reviewer_role_ids: tuple[str, ...] = (
        "proto-candidate-technical-reviewer",
        "safety-boundary-reviewer",
    )


@dataclass(frozen=True)
class FakeDeclaration:
    declaration_id: str = "declaration-001"
    artifact_id: str = "artifact:declaration-001"
    status: WaveFourMaturityDeclarationStatus = (
        WaveFourMaturityDeclarationStatus.DECLARABLE_FOR_HUMAN_REVIEW
    )
    decision: WaveFourMaturityDeclarationDecision = (
        WaveFourMaturityDeclarationDecision.DECLARE_WAVE_FOUR_REVIEW_READY
    )
    declarable_for_human_review: bool = True
    review_packet: FakeReviewPacket = FakeReviewPacket()
    all_evidence_ids: tuple[str, ...] = (
        "evidence:declaration",
        "evidence:packet",
        "evidence:scorecard",
    )
    readiness_gaps: tuple[str, ...] = ()
    blocking_gaps: tuple[str, ...] = ()
    permits_automatic_execution: bool = False
    permits_automatic_promotion: bool = False
    claims_agi: bool = False
    independently_validated: bool = False
    production_ready: bool = False


def ready_declaration() -> FakeDeclaration:
    return FakeDeclaration()


def ready_docket() -> WaveFourHumanReviewDocket:
    return build_wave_four_human_review_docket(
        docket_id="review-docket-001",
        maturity_declaration=ready_declaration(),
    )


def entry(
    entry_id: str = "entry:maturity-declaration",
    entry_kind: WaveFourReviewDocketEntryKind = (
        WaveFourReviewDocketEntryKind.MATURITY_DECLARATION
    ),
    evidence_ids: tuple[str, ...] = (
        "evidence:declaration",
        "evidence:packet",
        "evidence:scorecard",
    ),
) -> WaveFourReviewDocketEntry:
    return WaveFourReviewDocketEntry(
        entry_id=entry_id,
        entry_kind=entry_kind,
        source_id="source:entry",
        summary="Review docket entry.",
        payload={"entry": entry_id},
        evidence_ids=evidence_ids,
    )


def assignment(
    assignment_id: str = "assignment:technical",
    role_id: str = "proto-candidate-technical-reviewer",
    required_entry_ids: tuple[str, ...] = ("entry:maturity-declaration",),
) -> WaveFourReviewerAssignment:
    return WaveFourReviewerAssignment(
        assignment_id=assignment_id,
        reviewer_role_id=role_id,
        review_scope="Review the bounded Wave 4 docket evidence.",
        required_entry_ids=required_entry_ids,
        decision_options=DEFAULT_WAVE_FOUR_REVIEW_DECISION_OPTIONS,
        evidence_ids=("evidence:assignment",),
    )


def test_required_docket_entry_kinds_and_decision_options_are_locked() -> None:
    assert REQUIRED_WAVE_FOUR_DOCKET_ENTRY_KINDS == (
        WaveFourReviewDocketEntryKind.MATURITY_DECLARATION,
        WaveFourReviewDocketEntryKind.HUMAN_REVIEW_PACKET,
        WaveFourReviewDocketEntryKind.SCORECARD,
        WaveFourReviewDocketEntryKind.PROTO_CANDIDATE_BUNDLE,
        WaveFourReviewDocketEntryKind.EVIDENCE_MANIFEST,
        WaveFourReviewDocketEntryKind.REVIEW_INSTRUCTIONS,
    )
    assert DEFAULT_WAVE_FOUR_REVIEW_DECISION_OPTIONS == (
        WaveFourReviewDecisionOption.ACCEPT_FOR_WAVE_FOUR_RECORD,
        WaveFourReviewDecisionOption.REQUEST_MORE_EVIDENCE,
        WaveFourReviewDecisionOption.REQUEST_REPAIR,
        WaveFourReviewDecisionOption.BLOCK_WAVE_FOUR_RECORD,
    )


def test_docket_entry_requires_payload_and_evidence() -> None:
    with pytest.raises(ValueError, match="require non-empty payloads"):
        WaveFourReviewDocketEntry(
            entry_id="entry:invalid",
            entry_kind=WaveFourReviewDocketEntryKind.EVIDENCE_MANIFEST,
            source_id="source:invalid",
            summary="Invalid empty payload.",
            payload={},
            evidence_ids=("evidence:invalid",),
        )

    with pytest.raises(ValueError, match="docket entries require evidence ids"):
        WaveFourReviewDocketEntry(
            entry_id="entry:invalid",
            entry_kind=WaveFourReviewDocketEntryKind.EVIDENCE_MANIFEST,
            source_id="source:invalid",
            summary="Invalid missing evidence.",
            payload={"ok": True},
            evidence_ids=(),
        )

    with pytest.raises(ValueError, match="must be JSON serializable"):
        WaveFourReviewDocketEntry(
            entry_id="entry:invalid",
            entry_kind=WaveFourReviewDocketEntryKind.EVIDENCE_MANIFEST,
            source_id="source:invalid",
            summary="Invalid non-serializable payload.",
            payload={"bad": {"set-is-not-json"}},
            evidence_ids=("evidence:invalid",),
        )


def test_reviewer_assignment_requires_entries_options_and_evidence() -> None:
    with pytest.raises(ValueError, match="reviewer assignments require entry ids"):
        assignment(required_entry_ids=())

    with pytest.raises(ValueError, match="reviewer assignments require decision"):
        WaveFourReviewerAssignment(
            assignment_id="assignment:invalid",
            reviewer_role_id="reviewer",
            review_scope="Invalid missing decision options.",
            required_entry_ids=("entry:maturity-declaration",),
            decision_options=(),
            evidence_ids=("evidence:assignment",),
        )

    with pytest.raises(ValueError, match="reviewer assignments require evidence"):
        WaveFourReviewerAssignment(
            assignment_id="assignment:invalid",
            reviewer_role_id="reviewer",
            review_scope="Invalid missing evidence.",
            required_entry_ids=("entry:maturity-declaration",),
            decision_options=DEFAULT_WAVE_FOUR_REVIEW_DECISION_OPTIONS,
            evidence_ids=(),
        )


def test_ready_docket_submits_for_human_review_without_overclaim() -> None:
    docket = ready_docket()

    assert docket.status is WaveFourReviewDocketStatus.READY_FOR_HUMAN_REVIEW
    assert docket.decision is (
        WaveFourReviewDocketDecision.SUBMIT_DOCKET_FOR_HUMAN_REVIEW
    )
    assert docket.ready_for_human_review is True
    assert docket.missing_required_entry_kinds == ()
    assert docket.missing_required_reviewer_role_ids == ()
    assert docket.missing_declaration_evidence_ids == ()
    assert docket.readiness_gaps == ()
    assert docket.blocking_gaps == ()
    assert docket.permits_automatic_execution is False
    assert docket.permits_automatic_promotion is False
    assert docket.claims_agi is False
    assert docket.independently_validated is False
    assert docket.production_ready is False
    assert len(docket.final_digest) == 64
    assert "human review only; no AGI claim" in docket.review_summary


def test_docket_holds_for_missing_entry_coverage() -> None:
    docket = WaveFourHumanReviewDocket(
        docket_id="review-docket-missing-entry",
        maturity_declaration=ready_declaration(),
        entries=(entry(),),
        reviewer_assignments=(assignment(),),
        scenario_ids=("worldtwin:review-docket",),
        blackfox_receipt_ids=("blackfox:review-docket",),
    )

    assert docket.status is WaveFourReviewDocketStatus.NEEDS_EVIDENCE
    assert WaveFourReviewDocketEntryKind.EVIDENCE_MANIFEST in (
        docket.missing_required_entry_kinds
    )
    assert "missing docket entry coverage" in docket.readiness_gaps[0]


def test_docket_holds_for_missing_reviewer_role_coverage() -> None:
    docket = WaveFourHumanReviewDocket(
        docket_id="review-docket-missing-role",
        maturity_declaration=ready_declaration(),
        entries=ready_docket().entries,
        reviewer_assignments=(
            assignment(role_id="proto-candidate-technical-reviewer"),
        ),
        scenario_ids=("worldtwin:review-docket",),
        blackfox_receipt_ids=("blackfox:review-docket",),
    )

    assert docket.status is WaveFourReviewDocketStatus.NEEDS_EVIDENCE
    assert docket.missing_required_reviewer_role_ids == (
        "safety-boundary-reviewer",
    )
    assert "missing reviewer role coverage" in docket.readiness_gaps[0]


def test_docket_rejects_assignment_referencing_unknown_entry() -> None:
    with pytest.raises(ValueError, match="must reference docket entries"):
        WaveFourHumanReviewDocket(
            docket_id="review-docket-bad-assignment",
            maturity_declaration=ready_declaration(),
            entries=(entry(),),
            reviewer_assignments=(
                assignment(required_entry_ids=("entry:missing",)),
            ),
            scenario_ids=("worldtwin:review-docket",),
            blackfox_receipt_ids=("blackfox:review-docket",),
        )


def test_docket_holds_for_missing_declaration_evidence() -> None:
    docket = WaveFourHumanReviewDocket(
        docket_id="review-docket-missing-evidence",
        maturity_declaration=ready_declaration(),
        entries=(
            entry(evidence_ids=("evidence:declaration",)),
            entry(
                "entry:human-review-packet",
                WaveFourReviewDocketEntryKind.HUMAN_REVIEW_PACKET,
                ("evidence:declaration",),
            ),
            entry(
                "entry:scorecard",
                WaveFourReviewDocketEntryKind.SCORECARD,
                ("evidence:declaration",),
            ),
            entry(
                "entry:proto-candidate-bundle",
                WaveFourReviewDocketEntryKind.PROTO_CANDIDATE_BUNDLE,
                ("evidence:declaration",),
            ),
            entry(
                "entry:evidence-manifest",
                WaveFourReviewDocketEntryKind.EVIDENCE_MANIFEST,
                ("evidence:declaration",),
            ),
            entry(
                "entry:review-instructions",
                WaveFourReviewDocketEntryKind.REVIEW_INSTRUCTIONS,
                ("evidence:declaration",),
            ),
        ),
        reviewer_assignments=(
            assignment(role_id="proto-candidate-technical-reviewer"),
            assignment(
                "assignment:safety",
                "safety-boundary-reviewer",
            ),
        ),
        scenario_ids=("worldtwin:review-docket",),
        blackfox_receipt_ids=("blackfox:review-docket",),
    )

    assert docket.status is WaveFourReviewDocketStatus.NEEDS_EVIDENCE
    assert docket.missing_declaration_evidence_ids == (
        "evidence:packet",
        "evidence:scorecard",
    )
    assert "missing declaration evidence in docket" in docket.readiness_gaps[0]


def test_docket_needs_repair_when_declaration_needs_repair() -> None:
    declaration = FakeDeclaration(
        status=WaveFourMaturityDeclarationStatus.NEEDS_REPAIR,
        decision=WaveFourMaturityDeclarationDecision.HOLD_FOR_REPAIR,
        declarable_for_human_review=False,
        readiness_gaps=("boundary failed",),
    )
    docket = WaveFourHumanReviewDocket(
        docket_id="review-docket-declaration-repair",
        maturity_declaration=declaration,
        entries=ready_docket().entries,
        reviewer_assignments=ready_docket().reviewer_assignments,
        scenario_ids=("worldtwin:review-docket",),
        blackfox_receipt_ids=("blackfox:review-docket",),
    )

    assert docket.status is WaveFourReviewDocketStatus.NEEDS_REPAIR
    assert docket.decision is WaveFourReviewDocketDecision.HOLD_FOR_REPAIR
    assert "boundary failed" in docket.readiness_gaps


def test_blocked_docket_blocks_review() -> None:
    docket = WaveFourHumanReviewDocket(
        docket_id="review-docket-blocked",
        maturity_declaration=ready_declaration(),
        entries=ready_docket().entries,
        reviewer_assignments=ready_docket().reviewer_assignments,
        scenario_ids=("worldtwin:review-docket",),
        blackfox_receipt_ids=("blackfox:review-docket",),
        blocked_reasons=("review docket source evidence was contradicted",),
    )

    assert docket.status is WaveFourReviewDocketStatus.BLOCKED
    assert docket.decision is WaveFourReviewDocketDecision.BLOCK_DOCKET
    assert docket.blocking_gaps == (
        "review-docket-blocked blocked: review docket source evidence was contradicted",
    )


def test_docket_rejects_execution_promotion_agi_validation_and_production() -> None:
    base = ready_docket()

    with pytest.raises(ValueError, match="cannot permit execution"):
        WaveFourHumanReviewDocket(
            docket_id="invalid-execution",
            maturity_declaration=ready_declaration(),
            entries=base.entries,
            reviewer_assignments=base.reviewer_assignments,
            scenario_ids=base.scenario_ids,
            blackfox_receipt_ids=base.blackfox_receipt_ids,
            permits_automatic_execution=True,
        )

    with pytest.raises(ValueError, match="cannot permit promotion"):
        WaveFourHumanReviewDocket(
            docket_id="invalid-promotion",
            maturity_declaration=ready_declaration(),
            entries=base.entries,
            reviewer_assignments=base.reviewer_assignments,
            scenario_ids=base.scenario_ids,
            blackfox_receipt_ids=base.blackfox_receipt_ids,
            permits_automatic_promotion=True,
        )

    with pytest.raises(ValueError, match="cannot claim AGI"):
        WaveFourHumanReviewDocket(
            docket_id="invalid-agi",
            maturity_declaration=ready_declaration(),
            entries=base.entries,
            reviewer_assignments=base.reviewer_assignments,
            scenario_ids=base.scenario_ids,
            blackfox_receipt_ids=base.blackfox_receipt_ids,
            claims_agi=True,
        )

    with pytest.raises(ValueError, match="cannot claim independent validation"):
        WaveFourHumanReviewDocket(
            docket_id="invalid-validation",
            maturity_declaration=ready_declaration(),
            entries=base.entries,
            reviewer_assignments=base.reviewer_assignments,
            scenario_ids=base.scenario_ids,
            blackfox_receipt_ids=base.blackfox_receipt_ids,
            independently_validated=True,
        )

    with pytest.raises(ValueError, match="cannot claim production readiness"):
        WaveFourHumanReviewDocket(
            docket_id="invalid-production",
            maturity_declaration=ready_declaration(),
            entries=base.entries,
            reviewer_assignments=base.reviewer_assignments,
            scenario_ids=base.scenario_ids,
            blackfox_receipt_ids=base.blackfox_receipt_ids,
            production_ready=True,
        )


def test_docket_converts_to_readiness_artifact_and_bundle() -> None:
    docket = ready_docket()
    artifact = docket.to_artifact_ref()
    bundle = docket.to_artifact_bundle()

    assert artifact.kind is WaveFourArtifactKind.READINESS_SNAPSHOT
    assert artifact.capability_area is WaveFourCapabilityArea.AUDIT_TRAIL
    assert artifact.ready_for_controlled_review is True
    assert artifact.allowed_for_automatic_execution is False
    assert artifact.claims_agi is False
    assert bundle.has_required_kind_coverage is True
    assert bundle.has_required_capability_coverage is True
    assert bundle.ready_for_controlled_review_artifact_ids == (artifact.artifact_id,)


def test_docket_fingerprint_is_deterministic_despite_input_order() -> None:
    first = ready_docket()
    second = WaveFourHumanReviewDocket(
        docket_id="review-docket-001",
        maturity_declaration=ready_declaration(),
        entries=tuple(reversed(first.entries)),
        reviewer_assignments=tuple(reversed(first.reviewer_assignments)),
        scenario_ids=("worldtwin:review-docket",),
        blackfox_receipt_ids=("blackfox:review-docket",),
    )

    assert first.fingerprint() == second.fingerprint()
    assert len(first.fingerprint()) == 64
