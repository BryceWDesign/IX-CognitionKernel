import pytest

from ix_cognition_kernel.wave5_blackfox_bridge import (
    BLACKFOX_ACCEPTANCE_SOURCE_SYSTEMS,
    REQUIRED_BLACKFOX_GATE_KINDS,
    REQUIRED_BLACKFOX_RECEIPT_KINDS,
    SAFE_BLACKFOX_AUTHORITY_MODES,
    WaveFiveBlackFoxAuthorityMode,
    WaveFiveBlackFoxCompatibilityHandoff,
    WaveFiveBlackFoxGate,
    WaveFiveBlackFoxGateKind,
    WaveFiveBlackFoxGateResult,
    WaveFiveBlackFoxHandoffState,
    WaveFiveBlackFoxReceipt,
    WaveFiveBlackFoxReceiptKind,
    blackfox_acceptance_source_systems,
    required_blackfox_gate_kinds,
    required_blackfox_receipt_kinds,
    safe_blackfox_authority_modes,
)
from ix_cognition_kernel.wave5_contracts import (
    WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES,
    WaveFiveArtifactDecision,
    WaveFiveArtifactKind,
    WaveFiveAuthorityState,
    WaveFiveCapabilityArea,
    WaveFiveClaimBoundary,
    WaveFiveSourceSystem,
    WaveFiveValidationStatus,
)

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


def gate(
    gate_id: str = "gate-model-output-untrusted",
    *,
    gate_kind: WaveFiveBlackFoxGateKind = (
        WaveFiveBlackFoxGateKind.MODEL_OUTPUT_UNTRUSTED
    ),
    result: WaveFiveBlackFoxGateResult = WaveFiveBlackFoxGateResult.PASSED,
    blocking: bool = True,
) -> WaveFiveBlackFoxGate:
    return WaveFiveBlackFoxGate(
        gate_id=gate_id,
        gate_kind=gate_kind,
        result=result,
        description="BlackFox governance gate preserves review-only evidence.",
        evidence_ids=(f"evidence-{gate_id}",),
        blocking=blocking,
    )


def receipt(
    receipt_id: str = "receipt-proposed-change",
    *,
    receipt_kind: WaveFiveBlackFoxReceiptKind = (
        WaveFiveBlackFoxReceiptKind.PROPOSED_CHANGE
    ),
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_BLACKFOX,
    digest: str = DIGEST_A,
    human_reviewer_id: str = "",
    authorizes_execution: bool = False,
    self_approved: bool = False,
) -> WaveFiveBlackFoxReceipt:
    return WaveFiveBlackFoxReceipt(
        receipt_id=receipt_id,
        receipt_kind=receipt_kind,
        source_system=source_system,
        artifact_ids=("wave5-artifact-001",),
        digest=digest,
        evidence_ids=(f"evidence-{receipt_id}",),
        human_reviewer_id=human_reviewer_id,
        authorizes_execution=authorizes_execution,
        self_approved=self_approved,
    )


def required_gates() -> tuple[WaveFiveBlackFoxGate, ...]:
    return tuple(
        gate(f"gate-{kind.value}", gate_kind=kind)
        for kind in REQUIRED_BLACKFOX_GATE_KINDS
    )


def required_receipts() -> tuple[WaveFiveBlackFoxReceipt, ...]:
    receipts: list[WaveFiveBlackFoxReceipt] = []
    for index, kind in enumerate(REQUIRED_BLACKFOX_RECEIPT_KINDS):
        reviewer_id = (
            "human-reviewer-001"
            if kind is WaveFiveBlackFoxReceiptKind.HUMAN_REVIEW
            else ""
        )
        receipts.append(
            receipt(
                f"receipt-{kind.value}",
                receipt_kind=kind,
                digest=(DIGEST_A if index % 2 == 0 else DIGEST_B),
                human_reviewer_id=reviewer_id,
            )
        )
    return tuple(receipts)


def handoff(
    *,
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    handoff_state: WaveFiveBlackFoxHandoffState = (
        WaveFiveBlackFoxHandoffState.READY_FOR_BLACKFOX_REVIEW
    ),
    authority_mode: WaveFiveBlackFoxAuthorityMode = (
        WaveFiveBlackFoxAuthorityMode.HUMAN_APPROVAL_REQUIRED
    ),
    gates: tuple[WaveFiveBlackFoxGate, ...] | None = None,
    receipts: tuple[WaveFiveBlackFoxReceipt, ...] | None = None,
    reviewer_ids: tuple[str, ...] = (),
    granted_execution_authority: bool = False,
    claims_agi: bool = False,
    claims_production_ready: bool = False,
    claims_certified: bool = False,
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    ),
) -> WaveFiveBlackFoxCompatibilityHandoff:
    resolved_gates = required_gates() if gates is None else gates
    resolved_receipts = required_receipts() if receipts is None else receipts
    return WaveFiveBlackFoxCompatibilityHandoff(
        handoff_id="wave5-blackfox-handoff-001",
        title="Wave 5 Kernel-to-BlackFox Wave 10 compatibility handoff.",
        source_system=source_system,
        handoff_state=handoff_state,
        authority_mode=authority_mode,
        kernel_artifact_ids=("wave5-dossier-001", "wave5-scorecard-001"),
        blackfox_control_refs=(
            "untrusted-model-output",
            "policy-gates",
            "isolated-workspaces",
            "ci-bound-verification",
            "human-authorization",
        ),
        gates=resolved_gates,
        receipts=resolved_receipts,
        protocol_ids=("wave5-external-protocol-001",),
        reviewer_ids=reviewer_ids,
        granted_execution_authority=granted_execution_authority,
        claims_agi=claims_agi,
        claims_production_ready=claims_production_ready,
        claims_certified=claims_certified,
        claim_boundaries=claim_boundaries,
        notes=("BlackFox compatibility is review evidence, not execution authority.",),
    )


def test_required_blackfox_gates_are_locked() -> None:
    assert required_blackfox_gate_kinds() == REQUIRED_BLACKFOX_GATE_KINDS
    assert len(REQUIRED_BLACKFOX_GATE_KINDS) == 10
    assert WaveFiveBlackFoxGateKind.NO_AUTONOMOUS_EXECUTION in (
        REQUIRED_BLACKFOX_GATE_KINDS
    )


def test_required_blackfox_receipts_are_locked() -> None:
    assert required_blackfox_receipt_kinds() == REQUIRED_BLACKFOX_RECEIPT_KINDS
    assert len(REQUIRED_BLACKFOX_RECEIPT_KINDS) == 9
    assert WaveFiveBlackFoxReceiptKind.HUMAN_REVIEW in REQUIRED_BLACKFOX_RECEIPT_KINDS


def test_safe_blackfox_authority_modes_are_locked() -> None:
    assert safe_blackfox_authority_modes() == SAFE_BLACKFOX_AUTHORITY_MODES
    assert WaveFiveBlackFoxAuthorityMode.BLOCKED not in SAFE_BLACKFOX_AUTHORITY_MODES


def test_blackfox_acceptance_sources_are_locked() -> None:
    assert blackfox_acceptance_source_systems() == BLACKFOX_ACCEPTANCE_SOURCE_SYSTEMS
    assert WaveFiveSourceSystem.IX_BLACKFOX in BLACKFOX_ACCEPTANCE_SOURCE_SYSTEMS
    assert WaveFiveSourceSystem.IX_COGNITION_KERNEL not in (
        BLACKFOX_ACCEPTANCE_SOURCE_SYSTEMS
    )


def test_gate_requires_evidence_ids() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        WaveFiveBlackFoxGate(
            gate_id="gate-invalid",
            gate_kind=WaveFiveBlackFoxGateKind.POLICY_GATE,
            result=WaveFiveBlackFoxGateResult.PASSED,
            description="Invalid gate without evidence.",
            evidence_ids=(),
        )


def test_failed_blocking_gate_blocks_progress() -> None:
    item = gate(result=WaveFiveBlackFoxGateResult.FAILED)

    assert item.passed_with_boundaries is False
    assert item.blocks_wave_five_progress is True


def test_non_blocking_gate_does_not_block_progress() -> None:
    item = gate(
        result=WaveFiveBlackFoxGateResult.NEEDS_MORE_EVIDENCE,
        blocking=False,
    )

    assert item.blocks_wave_five_progress is False


def test_receipt_requires_valid_sha256_digest() -> None:
    with pytest.raises(ValueError, match="64-character"):
        receipt(digest="not-a-digest")


def test_receipt_rejects_execution_authority_and_self_approval() -> None:
    with pytest.raises(ValueError, match="cannot authorize execution"):
        receipt(authorizes_execution=True)

    with pytest.raises(ValueError, match="cannot be self-approved"):
        receipt(self_approved=True)


def test_human_review_receipt_requires_human_reviewer() -> None:
    with pytest.raises(ValueError, match="human reviewer id"):
        receipt(receipt_kind=WaveFiveBlackFoxReceiptKind.HUMAN_REVIEW)


def test_human_review_receipt_reports_human_review() -> None:
    item = receipt(
        receipt_kind=WaveFiveBlackFoxReceiptKind.HUMAN_REVIEW,
        human_reviewer_id="human-reviewer-001",
    )

    assert item.has_human_review is True


def test_handoff_rejects_execution_or_overclaim_flags() -> None:
    with pytest.raises(ValueError, match="cannot grant execution"):
        handoff(granted_execution_authority=True)

    with pytest.raises(ValueError, match="cannot claim AGI"):
        handoff(claims_agi=True)

    with pytest.raises(ValueError, match="production readiness"):
        handoff(claims_production_ready=True)

    with pytest.raises(ValueError, match="certification"):
        handoff(claims_certified=True)


def test_handoff_requires_kernel_artifacts_and_blackfox_refs() -> None:
    with pytest.raises(ValueError, match="Kernel artifact ids"):
        WaveFiveBlackFoxCompatibilityHandoff(
            handoff_id="handoff-invalid",
            title="Invalid handoff without Kernel artifacts.",
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
            handoff_state=WaveFiveBlackFoxHandoffState.READY_FOR_BLACKFOX_REVIEW,
            authority_mode=WaveFiveBlackFoxAuthorityMode.HUMAN_APPROVAL_REQUIRED,
            kernel_artifact_ids=(),
            blackfox_control_refs=("policy-gates",),
            gates=required_gates(),
            receipts=required_receipts(),
            protocol_ids=("protocol",),
        )


def test_handoff_rejects_missing_claim_boundary() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        handoff(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_handoff_reports_missing_gate_and_receipt_coverage() -> None:
    item = handoff(
        gates=(
            gate(
                "gate-policy-gate",
                gate_kind=WaveFiveBlackFoxGateKind.POLICY_GATE,
            ),
        ),
        receipts=(
            receipt(
                "receipt-policy-decision",
                receipt_kind=WaveFiveBlackFoxReceiptKind.POLICY_DECISION,
            ),
        ),
    )

    assert item.has_required_gate_coverage is False
    assert WaveFiveBlackFoxGateKind.NO_AUTONOMOUS_EXECUTION in (
        item.missing_required_gate_kinds
    )
    assert item.has_required_receipt_coverage is False
    assert WaveFiveBlackFoxReceiptKind.HUMAN_REVIEW in (
        item.missing_required_receipt_kinds
    )
    assert item.ready_for_blackfox_review is False


def test_handoff_requires_human_review_receipt_for_authority_boundary() -> None:
    receipts = tuple(
        item
        for item in required_receipts()
        if item.receipt_kind is not WaveFiveBlackFoxReceiptKind.HUMAN_REVIEW
    )
    item = handoff(receipts=receipts)

    assert item.has_human_review_receipt is False
    assert item.preserves_blackfox_authority_boundary is False
    assert item.ready_for_blackfox_review is False


def test_handoff_is_ready_for_blackfox_review() -> None:
    item = handoff()

    assert item.has_required_gate_coverage is True
    assert item.has_required_receipt_coverage is True
    assert item.blocking_gate_ids == ()
    assert item.has_human_review_receipt is True
    assert item.preserves_blackfox_authority_boundary is True
    assert item.blocks_blackfox_compatibility is False
    assert item.ready_for_blackfox_review is True


def test_ready_handoff_exports_reviewable_traceability_artifact() -> None:
    artifact = handoff().to_artifact_ref()

    assert artifact.kind is WaveFiveArtifactKind.ECOSYSTEM_TRACEABILITY_MAP
    assert artifact.capability_area is WaveFiveCapabilityArea.ECOSYSTEM_TRACEABILITY
    assert artifact.source_system is WaveFiveSourceSystem.IX_COGNITION_KERNEL
    assert artifact.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    assert artifact.authority_state is WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    )


def test_blocking_gate_exports_blocked_artifact() -> None:
    gates = tuple(
        gate(
            f"gate-{kind.value}",
            gate_kind=kind,
            result=(
                WaveFiveBlackFoxGateResult.FAILED
                if kind is WaveFiveBlackFoxGateKind.CI_VERIFICATION
                else WaveFiveBlackFoxGateResult.PASSED
            ),
        )
        for kind in REQUIRED_BLACKFOX_GATE_KINDS
    )
    artifact = handoff(gates=gates).to_artifact_ref()

    assert artifact.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact.authority_state is WaveFiveAuthorityState.BLOCKED
    assert artifact.validation_status is WaveFiveValidationStatus.REJECTED


def test_blocked_authority_mode_requires_blocking_gap() -> None:
    with pytest.raises(ValueError, match="requires a blocking gap"):
        handoff(authority_mode=WaveFiveBlackFoxAuthorityMode.BLOCKED)


def test_blackfox_accepted_handoff_requires_blackfox_or_human_source() -> None:
    with pytest.raises(ValueError, match="BlackFox or human review source"):
        handoff(
            handoff_state=(
                WaveFiveBlackFoxHandoffState.BLACKFOX_ACCEPTED_WITH_BOUNDARIES
            ),
            reviewer_ids=("reviewer-001",),
        )


def test_blackfox_accepted_handoff_requires_reviewer_ids() -> None:
    with pytest.raises(ValueError, match="reviewer ids"):
        handoff(
            source_system=WaveFiveSourceSystem.IX_BLACKFOX,
            handoff_state=(
                WaveFiveBlackFoxHandoffState.BLACKFOX_ACCEPTED_WITH_BOUNDARIES
            ),
        )


def test_blackfox_accepted_handoff_exports_bounded_external_artifact() -> None:
    item = handoff(
        source_system=WaveFiveSourceSystem.IX_BLACKFOX,
        handoff_state=WaveFiveBlackFoxHandoffState.BLACKFOX_ACCEPTED_WITH_BOUNDARIES,
        reviewer_ids=("blackfox-reviewer-001",),
    )
    artifact = item.to_artifact_ref()

    assert item.blackfox_accepted_with_boundaries is True
    assert artifact.decision is WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
    )
    assert artifact.externally_validated_with_boundaries is True


def test_handoff_collects_unique_evidence_ids() -> None:
    item = handoff()

    assert item.all_evidence_ids[0] == "evidence-gate-ci-verification"
    assert "evidence-receipt-human-review" in item.all_evidence_ids
    assert len(item.all_evidence_ids) == 19


def test_handoff_fingerprint_is_deterministic() -> None:
    item = handoff()

    assert item.fingerprint() == item.fingerprint()
    assert len(item.fingerprint()) == 64
