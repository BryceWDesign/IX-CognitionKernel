import pytest

from ix_cognition_kernel.wave6_claim_boundary import (
    WAVE_SIX_REQUIRED_ALLOWED_CLAIMS,
    WAVE_SIX_REQUIRED_CLAIM_PREREQUISITES,
    WAVE_SIX_REQUIRED_PROHIBITED_CLAIMS,
    WaveSixClaimBoundaryAssessment,
    WaveSixClaimBoundaryDecision,
    WaveSixClaimBoundaryDeclaration,
)
from ix_cognition_kernel.wave6_evidence_package import (
    WAVE_SIX_REQUIRED_EVIDENCE_SURFACES,
    WaveSixEvidencePackage,
    WaveSixEvidencePackageBlocker,
    WaveSixEvidencePackageStatus,
    WaveSixEvidenceReference,
    WaveSixEvidenceSurface,
    build_wave_six_evidence_package,
    required_wave_six_evidence_surfaces,
)
from ix_cognition_kernel.wave6_falsification import (
    WaveSixFalsificationDecision,
    WaveSixFalsificationLedger,
    WaveSixFalsificationOutcome,
    WaveSixFalsificationProbe,
    WaveSixFalsificationProbeKind,
    WaveSixFalsificationResult,
)
from ix_cognition_kernel.wave6_future_reasoning import (
    WaveSixFutureReasoningChangeProof,
    WaveSixFutureReasoningProofLedger,
    WaveSixReasoningChangeKind,
    WaveSixReasoningProofDecision,
    WaveSixReasoningSnapshot,
)
from ix_cognition_kernel.wave6_human_review import (
    WAVE_SIX_REQUIRED_REVIEW_ITEM_KINDS,
    WaveSixHumanReviewDecision,
    WaveSixHumanReviewDocket,
    WaveSixHumanReviewFinding,
    WaveSixReviewItem,
    WaveSixReviewItemKind,
)
from ix_cognition_kernel.wave6_independent_review import (
    WAVE_SIX_REQUIRED_INDEPENDENT_REVIEW_ARTIFACT_KINDS,
    WaveSixIndependentReviewArtifact,
    WaveSixIndependentReviewArtifactKind,
    WaveSixIndependentReviewDecision,
    WaveSixIndependentReviewFinding,
    WaveSixIndependentReviewPacket,
)
from ix_cognition_kernel.wave6_transfer_novelty import (
    WaveSixNegativeControlResult,
    WaveSixNoveltyPressureKind,
    WaveSixTransferDecision,
    WaveSixTransferDomain,
    WaveSixTransferNoveltyLedger,
    WaveSixTransferNoveltyRecord,
)


class _ReadyRealityLedger:
    @property
    def blocking_record_ids(self) -> tuple[str, ...]:
        return ()

    @property
    def ready_for_wave_six_memory_update(self) -> bool:
        return True

    def fingerprint(self) -> str:
        return "reality-ledger-fingerprint"


def _reality_ledger() -> _ReadyRealityLedger:
    return _ReadyRealityLedger()


def _snapshot(snapshot_id: str, summary: str) -> WaveSixReasoningSnapshot:
    return WaveSixReasoningSnapshot(
        snapshot_id=snapshot_id,
        task_context="Wave 6 future reasoning proof.",
        reasoning_summary=summary,
        active_assumption_ids=("assumption-1",),
        memory_ids=(f"memory-{snapshot_id}",),
        evidence_ids=(f"evidence-{snapshot_id}",),
        created_by_stage="memory-update",
    )


def _future_reasoning_ledger() -> WaveSixFutureReasoningProofLedger:
    proof = WaveSixFutureReasoningChangeProof(
        proof_id="future-proof-1",
        before_snapshot=_snapshot("before", "Use the original assumption first."),
        after_snapshot=_snapshot("after", "Use the corrected condition first."),
        reality_correction_record_ids=("correction-1",),
        changed_assumption_ids=("assumption-1",),
        changed_memory_ids=("memory-after",),
        change_kind=WaveSixReasoningChangeKind.CAUSAL_ASSUMPTION_REWEIGHTED,
        expected_future_behavior="Future trials check the corrected condition first.",
        counterfactual_old_behavior=(
            "Future trials reuse the original assumption first."
        ),
        evidence_ids=("future-proof-evidence",),
        decision=WaveSixReasoningProofDecision.ACCEPT_FOR_WAVE_SIX_REVIEW,
    )
    return WaveSixFutureReasoningProofLedger(ledger_id="future-ledger", proofs=(proof,))


def _domain(domain_id: str, family: str) -> WaveSixTransferDomain:
    return WaveSixTransferDomain(
        domain_id=domain_id,
        name=f"{family} domain",
        domain_family=family,
        task_summary="Transfer corrected causal structure.",
        measurable_success_criteria=("Prediction is made before outcome.",),
        evidence_ids=(f"evidence-{domain_id}",),
    )


def _transfer_ledger() -> WaveSixTransferNoveltyLedger:
    record = WaveSixTransferNoveltyRecord(
        record_id="transfer-1",
        source_domain=_domain("source-domain", "software"),
        target_domain=_domain("target-domain", "assurance"),
        transferred_structure_id="corrected-structure-1",
        future_reasoning_proof_ids=("future-proof-1",),
        expected_transfer_behavior="Target checks corrected precondition first.",
        observed_target_behavior="Target checked corrected precondition first.",
        novelty_pressure_kinds=(
            WaveSixNoveltyPressureKind.DOMAIN_SHIFT,
            WaveSixNoveltyPressureKind.NEGATIVE_CONTROL,
        ),
        negative_control_result=WaveSixNegativeControlResult.PASSED,
        negative_control_summary="The decoy target did not get a false pass.",
        evidence_ids=("transfer-evidence",),
        decision=WaveSixTransferDecision.ACCEPT_FOR_WAVE_SIX_REVIEW,
    )
    return WaveSixTransferNoveltyLedger(ledger_id="transfer-ledger", records=(record,))


def _falsification_ledger() -> WaveSixFalsificationLedger:
    probe = WaveSixFalsificationProbe(
        probe_id="probe-1",
        probe_kind=WaveSixFalsificationProbeKind.NEGATIVE_CONTROL,
        claim_under_test="Bounded transfer survived negative-control pressure.",
        falsification_question="Does a decoy target get a false pass?",
        expected_failure_mode="The system withholds the transfer claim.",
        method_summary="Remove the causal precondition from the target.",
        evidence_ids=("probe-evidence",),
    )
    result = WaveSixFalsificationResult(
        result_id="result-1",
        probe=probe,
        observed_result_summary="The decoy target did not get a false pass.",
        outcome=WaveSixFalsificationOutcome.SURVIVED,
        decision=WaveSixFalsificationDecision.ACCEPT_FOR_WAVE_SIX_REVIEW,
        evidence_ids=("result-evidence",),
        affected_claim_ids=("claim-transfer",),
    )
    return WaveSixFalsificationLedger(
        ledger_id="falsification-ledger", results=(result,)
    )


def _human_item(kind: WaveSixReviewItemKind) -> WaveSixReviewItem:
    return WaveSixReviewItem(
        item_id=f"item-{kind.value}",
        kind=kind,
        summary=f"Human review item for {kind.value}.",
        artifact_fingerprint=f"fingerprint-{kind.value}",
        evidence_ids=(f"evidence-{kind.value}",),
        finding=WaveSixHumanReviewFinding.ACCEPTED,
        reviewer_notes=("Accepted as bounded review evidence, not an AGI claim.",),
    )


def _human_review_docket() -> WaveSixHumanReviewDocket:
    return WaveSixHumanReviewDocket(
        docket_id="human-docket",
        reviewer_id="reviewer-1",
        reviewer_role="human-authority",
        items=tuple(_human_item(kind) for kind in WAVE_SIX_REQUIRED_REVIEW_ITEM_KINDS),
        decision=WaveSixHumanReviewDecision.APPROVE_BOUNDED_WAVE_SIX_REVIEW,
        decision_rationale="All bounded Wave 6 evidence surfaces were accepted.",
    )


def _external_artifact(
    kind: WaveSixIndependentReviewArtifactKind,
) -> WaveSixIndependentReviewArtifact:
    return WaveSixIndependentReviewArtifact(
        artifact_id=f"artifact-{kind.value}",
        kind=kind,
        summary=f"External review artifact for {kind.value}.",
        artifact_fingerprint=f"fingerprint-{kind.value}",
        evidence_ids=(f"evidence-{kind.value}",),
        reviewer_questions=("Can this artifact be reproduced from evidence?",),
        finding=WaveSixIndependentReviewFinding.ACCEPTED_FOR_EXTERNAL_REVIEW,
    )


def _independent_review_packet() -> WaveSixIndependentReviewPacket:
    return WaveSixIndependentReviewPacket(
        packet_id="external-packet",
        title="Wave 6 measured system-level cognition review packet",
        artifacts=tuple(
            _external_artifact(kind)
            for kind in WAVE_SIX_REQUIRED_INDEPENDENT_REVIEW_ARTIFACT_KINDS
        ),
        claim_boundary_statement="This is not an AGI claim.",
        replication_instructions=("Recompute every artifact fingerprint.",),
        generated_by_engine_id="wave6-evidence-package-engine",
        decision=WaveSixIndependentReviewDecision.READY_FOR_EXTERNAL_REVIEW,
    )


def _claim_boundary_assessment() -> WaveSixClaimBoundaryAssessment:
    declaration = WaveSixClaimBoundaryDeclaration(
        declaration_id="boundary-1",
        boundary_statement="Wave 6 is not an AGI claim.",
        allowed_claims=WAVE_SIX_REQUIRED_ALLOWED_CLAIMS,
        prohibited_claims=WAVE_SIX_REQUIRED_PROHIBITED_CLAIMS,
        satisfied_prerequisites=WAVE_SIX_REQUIRED_CLAIM_PREREQUISITES,
        evidence_ids=("boundary-evidence",),
        reviewer_questions=("Does evidence survive independent review?",),
        decision=WaveSixClaimBoundaryDecision.READY_FOR_BOUNDED_REVIEW,
    )
    return WaveSixClaimBoundaryAssessment(
        assessment_id="claim-boundary-assessment", declarations=(declaration,)
    )


def _references() -> tuple[WaveSixEvidenceReference, ...]:
    return tuple(
        WaveSixEvidenceReference(
            reference_id=f"reference-{surface.value}",
            surface=surface,
            artifact_fingerprint=f"fingerprint-{surface.value}",
            evidence_ids=(f"evidence-{surface.value}",),
            summary=f"Reference for {surface.value}.",
        )
        for surface in WAVE_SIX_REQUIRED_EVIDENCE_SURFACES
    )


def _package(
    *,
    references: tuple[WaveSixEvidenceReference, ...] | None = None,
    transfer_ledger: WaveSixTransferNoveltyLedger | None = None,
    claims_agi: bool = False,
) -> WaveSixEvidencePackage:
    return WaveSixEvidencePackage(
        package_id="package-1",
        references=references or _references(),
        reality_correction_ledger=_reality_ledger(),
        future_reasoning_ledger=_future_reasoning_ledger(),
        transfer_novelty_ledger=transfer_ledger or _transfer_ledger(),
        falsification_ledger=_falsification_ledger(),
        human_review_docket=_human_review_docket(),
        independent_review_packet=_independent_review_packet(),
        claim_boundary_assessment=_claim_boundary_assessment(),
        claims_agi=claims_agi,
        notes=("Ready means external review candidate, not AGI achieved.",),
    )


def test_required_wave_six_evidence_surfaces_are_locked() -> None:
    assert required_wave_six_evidence_surfaces() == (
        WaveSixEvidenceSurface.MASTER_LOOP_TRACE,
        WaveSixEvidenceSurface.CONTRACT_BUNDLE,
        WaveSixEvidenceSurface.DONOR_TRACEABILITY_MAP,
        WaveSixEvidenceSurface.REALITY_CORRECTION_LEDGER,
        WaveSixEvidenceSurface.FUTURE_REASONING_CHANGE_LEDGER,
        WaveSixEvidenceSurface.TRANSFER_NOVELTY_LEDGER,
        WaveSixEvidenceSurface.FALSIFICATION_LEDGER,
        WaveSixEvidenceSurface.HUMAN_REVIEW_DOCKET,
        WaveSixEvidenceSurface.INDEPENDENT_REVIEW_PACKET,
        WaveSixEvidenceSurface.CLAIM_BOUNDARY_ASSESSMENT,
    )


def test_evidence_reference_is_fingerprinted_and_evidence_bound() -> None:
    reference = _references()[0]

    assert reference.surface is WaveSixEvidenceSurface.MASTER_LOOP_TRACE
    assert reference.evidence_ids == ("evidence-master-loop-trace",)
    assert reference.fingerprint() == reference.fingerprint()
    assert len(reference.fingerprint()) == 64


def test_evidence_reference_requires_evidence_ids() -> None:
    with pytest.raises(ValueError, match="require evidence ids"):
        WaveSixEvidenceReference(
            reference_id="reference-no-evidence",
            surface=WaveSixEvidenceSurface.MASTER_LOOP_TRACE,
            artifact_fingerprint="fingerprint",
            evidence_ids=(),
            summary="Invalid empty evidence reference.",
        )


def test_evidence_package_is_ready_when_all_surfaces_and_ledgers_are_ready() -> None:
    package = build_wave_six_evidence_package(
        package_id="package-1",
        references=_references(),
        reality_correction_ledger=_reality_ledger(),
        future_reasoning_ledger=_future_reasoning_ledger(),
        transfer_novelty_ledger=_transfer_ledger(),
        falsification_ledger=_falsification_ledger(),
        human_review_docket=_human_review_docket(),
        independent_review_packet=_independent_review_packet(),
        claim_boundary_assessment=_claim_boundary_assessment(),
        notes=("External reviewers still decide whether evidence survives.",),
    )

    assert package.present_surfaces == WAVE_SIX_REQUIRED_EVIDENCE_SURFACES
    assert package.missing_surfaces == ()
    assert package.blockers == ()
    assert package.status is WaveSixEvidencePackageStatus.READY_FOR_EXTERNAL_REVIEW
    assert package.ready_for_external_review
    assert not package.blocked_by_ledgers
    assert not package.overclaim_present
    assert package.fingerprint() == package.fingerprint()
    assert len(package.fingerprint()) == 64


def test_evidence_package_reports_missing_surfaces() -> None:
    package = _package(references=_references()[:-1])

    assert package.missing_surfaces == (
        WaveSixEvidenceSurface.CLAIM_BOUNDARY_ASSESSMENT,
    )
    assert WaveSixEvidencePackageBlocker.MISSING_REQUIRED_SURFACE in package.blockers
    assert package.status is WaveSixEvidencePackageStatus.NEEDS_MORE_EVIDENCE
    assert not package.ready_for_external_review


def test_evidence_package_blocks_on_overclaim() -> None:
    package = _package(claims_agi=True)

    assert package.overclaim_present
    assert WaveSixEvidencePackageBlocker.OVERCLAIM_PRESENT in package.blockers
    assert package.status is WaveSixEvidencePackageStatus.BLOCKED
    assert not package.ready_for_external_review


def test_evidence_package_reports_transfer_not_ready() -> None:
    transfer_ledger = WaveSixTransferNoveltyLedger(
        ledger_id="transfer-ledger-not-ready",
        records=(_transfer_ledger().records[0],),
        required_supported_records=2,
    )
    package = _package(transfer_ledger=transfer_ledger)

    assert WaveSixEvidencePackageBlocker.TRANSFER_NOVELTY_NOT_READY in package.blockers
    assert package.status is WaveSixEvidencePackageStatus.NEEDS_MORE_EVIDENCE
    assert not package.ready_for_external_review


def test_evidence_package_reference_lookup_returns_present_surface_only() -> None:
    package = _package(references=(_references()[0],))

    reference = package.reference_for_surface(WaveSixEvidenceSurface.MASTER_LOOP_TRACE)

    assert reference is not None
    assert reference.reference_id == "reference-master-loop-trace"
    assert package.reference_for_surface(WaveSixEvidenceSurface.CONTRACT_BUNDLE) is None


def test_evidence_package_rejects_duplicate_reference_ids() -> None:
    reference = _references()[0]

    with pytest.raises(ValueError, match="Duplicate reference_id"):
        _package(references=(reference, reference))
