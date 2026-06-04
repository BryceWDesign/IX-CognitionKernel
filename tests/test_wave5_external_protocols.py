import pytest

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
from ix_cognition_kernel.wave5_external_protocols import (
    REQUIRED_WAVE_FIVE_ACCEPTANCE_GATES,
    REQUIRED_WAVE_FIVE_PROTOCOL_DOMAINS,
    WaveFiveAcceptanceGate,
    WaveFiveAcceptanceGateKind,
    WaveFiveExternalProtocolManifest,
    WaveFiveProtocolCriterion,
    WaveFiveProtocolCriterionKind,
    WaveFiveProtocolDomain,
    WaveFiveProtocolRegistrationState,
    required_wave_five_acceptance_gates,
    required_wave_five_protocol_domains,
)


def criterion(
    criterion_id: str = "criterion-001",
    *,
    criterion_kind: WaveFiveProtocolCriterionKind = (
        WaveFiveProtocolCriterionKind.ACCEPTANCE
    ),
    domain: WaveFiveProtocolDomain = WaveFiveProtocolDomain.EXTERNAL_REVIEW,
    evidence_ids: tuple[str, ...] = ("protocol-evidence-001",),
    pass_condition: str = "Independent reviewer evidence is present.",
    fail_condition: str = "Independent reviewer evidence is missing.",
) -> WaveFiveProtocolCriterion:
    return WaveFiveProtocolCriterion(
        criterion_id=criterion_id,
        criterion_kind=criterion_kind,
        domain=domain,
        statement="External validators must be able to falsify this criterion.",
        measurement_method="Inspect review packet and reproducible evidence bundle.",
        pass_condition=pass_condition,
        fail_condition=fail_condition,
        required_evidence_ids=evidence_ids,
    )


def gate(
    gate_id: str = "gate-001",
    *,
    gate_kind: WaveFiveAcceptanceGateKind = (
        WaveFiveAcceptanceGateKind.REQUIRED_EVIDENCE_PRESENT
    ),
    criterion_ids: tuple[str, ...] = ("criterion-001",),
    blocking: bool = True,
) -> WaveFiveAcceptanceGate:
    return WaveFiveAcceptanceGate(
        gate_id=gate_id,
        gate_kind=gate_kind,
        description="Block Wave 5 progress when required protocol evidence is absent.",
        required_criterion_ids=criterion_ids,
        blocking=blocking,
    )


def complete_criteria() -> tuple[WaveFiveProtocolCriterion, ...]:
    return (
        criterion(
            "criterion-adversarial",
            criterion_kind=WaveFiveProtocolCriterionKind.FALSIFICATION,
            domain=WaveFiveProtocolDomain.ADVERSARIAL_SAFETY,
            evidence_ids=("evidence-adversarial",),
            pass_condition="Adversarial pressure does not bypass authority gates.",
            fail_condition="Adversarial pressure bypasses authority gates.",
        ),
        criterion(
            "criterion-cross-domain",
            criterion_kind=WaveFiveProtocolCriterionKind.MEASUREMENT,
            domain=WaveFiveProtocolDomain.CROSS_DOMAIN_TRANSFER,
            evidence_ids=("evidence-cross-domain",),
        ),
        criterion(
            "criterion-ecosystem",
            criterion_kind=WaveFiveProtocolCriterionKind.ACCEPTANCE,
            domain=WaveFiveProtocolDomain.ECOSYSTEM_TRACEABILITY,
            evidence_ids=("evidence-ecosystem",),
        ),
        criterion(
            "criterion-external-review",
            criterion_kind=WaveFiveProtocolCriterionKind.ACCEPTANCE,
            domain=WaveFiveProtocolDomain.EXTERNAL_REVIEW,
            evidence_ids=("evidence-external-review",),
        ),
        criterion(
            "criterion-human-authority",
            criterion_kind=WaveFiveProtocolCriterionKind.ACCEPTANCE,
            domain=WaveFiveProtocolDomain.HUMAN_AUTHORITY,
            evidence_ids=("evidence-human-authority",),
        ),
        criterion(
            "criterion-long-horizon",
            criterion_kind=WaveFiveProtocolCriterionKind.MEASUREMENT,
            domain=WaveFiveProtocolDomain.LONG_HORIZON,
            evidence_ids=("evidence-long-horizon",),
        ),
        criterion(
            "criterion-memory",
            criterion_kind=WaveFiveProtocolCriterionKind.NEGATIVE_CONTROL,
            domain=WaveFiveProtocolDomain.MEMORY_INTEGRITY,
            evidence_ids=("evidence-memory",),
            pass_condition="Quarantined memory is rejected under replay.",
            fail_condition="Quarantined memory is accepted under replay.",
        ),
        criterion(
            "criterion-reproducibility",
            criterion_kind=WaveFiveProtocolCriterionKind.ACCEPTANCE,
            domain=WaveFiveProtocolDomain.REPRODUCIBILITY,
            evidence_ids=("evidence-reproducibility",),
        ),
        criterion(
            "criterion-safe-refusal",
            criterion_kind=WaveFiveProtocolCriterionKind.ACCEPTANCE,
            domain=WaveFiveProtocolDomain.SAFE_REFUSAL,
            evidence_ids=("evidence-safe-refusal",),
        ),
        criterion(
            "criterion-wave-six",
            criterion_kind=WaveFiveProtocolCriterionKind.REJECTION,
            domain=WaveFiveProtocolDomain.WAVE_SIX_PRECONDITIONS,
            evidence_ids=("evidence-wave-six",),
            pass_condition="Wave 6 prerequisites are explicit and externally testable.",
            fail_condition="Wave 6 prerequisites are implicit or self-attested.",
        ),
    )


def complete_gates() -> tuple[WaveFiveAcceptanceGate, ...]:
    return (
        gate(
            "gate-adversarial",
            gate_kind=WaveFiveAcceptanceGateKind.ADVERSARIAL_PRESSURE_PRESENT,
            criterion_ids=("criterion-adversarial",),
        ),
        gate(
            "gate-boundary",
            gate_kind=WaveFiveAcceptanceGateKind.OVERCLAIM_BOUNDARY_PRESERVED,
            criterion_ids=("criterion-wave-six",),
        ),
        gate(
            "gate-evidence",
            gate_kind=WaveFiveAcceptanceGateKind.REQUIRED_EVIDENCE_PRESENT,
            criterion_ids=("criterion-reproducibility",),
        ),
        gate(
            "gate-human-authority",
            gate_kind=WaveFiveAcceptanceGateKind.HUMAN_AUTHORITY_PRESERVED,
            criterion_ids=("criterion-human-authority",),
        ),
        gate(
            "gate-reproduction",
            gate_kind=WaveFiveAcceptanceGateKind.REPRODUCTION_ATTEMPT_PRESENT,
            criterion_ids=("criterion-reproducibility",),
        ),
        gate(
            "gate-reviewer",
            gate_kind=WaveFiveAcceptanceGateKind.INDEPENDENT_REVIEWER_PRESENT,
            criterion_ids=("criterion-external-review",),
        ),
    )


def manifest(
    *,
    registration_state: WaveFiveProtocolRegistrationState = (
        WaveFiveProtocolRegistrationState.PREREGISTERED_EXTERNAL
    ),
    domains: tuple[WaveFiveProtocolDomain, ...] = REQUIRED_WAVE_FIVE_PROTOCOL_DOMAINS,
    criteria: tuple[WaveFiveProtocolCriterion, ...] | None = None,
    gates: tuple[WaveFiveAcceptanceGate, ...] | None = None,
    source_system: WaveFiveSourceSystem = (
        WaveFiveSourceSystem.EXTERNAL_VALIDATION_PROTOCOL
    ),
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    ),
) -> WaveFiveExternalProtocolManifest:
    resolved_criteria = complete_criteria() if criteria is None else criteria
    resolved_gates = complete_gates() if gates is None else gates

    return WaveFiveExternalProtocolManifest(
        protocol_id="wave5-external-protocol-001",
        title="Wave 5 independent-validation protocol for Wave 6 readiness.",
        owner="External validation registrar",
        registration_state=registration_state,
        domains=domains,
        criteria=resolved_criteria,
        acceptance_gates=resolved_gates,
        required_artifact_kinds=(
            WaveFiveArtifactKind.EXTERNAL_PROTOCOL_MANIFEST,
            WaveFiveArtifactKind.REPRODUCIBLE_EVIDENCE_BUNDLE,
            WaveFiveArtifactKind.WAVE_SIX_PRECONDITION_LEDGER,
        ),
        required_capability_areas=(
            WaveFiveCapabilityArea.EXTERNAL_PROTOCOLS,
            WaveFiveCapabilityArea.REPRODUCIBILITY,
            WaveFiveCapabilityArea.WAVE_SIX_READINESS_BOUNDARY,
        ),
        forbidden_shortcuts=(
            "Do not treat internal tests as independent validation.",
            "Do not claim AGI from a self-authored protocol.",
            "Do not omit failed reproduction attempts.",
        ),
        external_reviewer_requirements=(
            "Reviewer must be independent of the repo author.",
            "Reviewer must disclose conflicts of interest.",
        ),
        reproduction_requirements=(
            "Replay evidence bundle from a clean checkout.",
            "Record failed reproduction attempts as blocking evidence.",
        ),
        claim_boundaries=claim_boundaries,
        source_system=source_system,
        notes=("Protocol gates Wave 5 as a bridge into Wave 6 without overclaiming.",),
    )


def test_required_protocol_domains_are_locked() -> None:
    assert required_wave_five_protocol_domains() == REQUIRED_WAVE_FIVE_PROTOCOL_DOMAINS
    assert len(REQUIRED_WAVE_FIVE_PROTOCOL_DOMAINS) == 10
    assert WaveFiveProtocolDomain.WAVE_SIX_PRECONDITIONS in (
        REQUIRED_WAVE_FIVE_PROTOCOL_DOMAINS
    )


def test_required_acceptance_gates_are_locked() -> None:
    assert required_wave_five_acceptance_gates() == REQUIRED_WAVE_FIVE_ACCEPTANCE_GATES
    assert len(REQUIRED_WAVE_FIVE_ACCEPTANCE_GATES) == 6
    assert WaveFiveAcceptanceGateKind.OVERCLAIM_BOUNDARY_PRESERVED in (
        REQUIRED_WAVE_FIVE_ACCEPTANCE_GATES
    )


def test_criterion_rejects_empty_evidence() -> None:
    with pytest.raises(ValueError, match="evidence ids"):
        criterion(evidence_ids=())


def test_criterion_rejects_identical_pass_and_fail_conditions() -> None:
    with pytest.raises(ValueError, match="must differ"):
        criterion(
            pass_condition="same condition",
            fail_condition="same condition",
        )


def test_acceptance_gate_rejects_empty_criterion_links() -> None:
    with pytest.raises(ValueError, match="criterion ids"):
        gate(criterion_ids=())


def test_manifest_rejects_gate_referencing_unknown_criterion() -> None:
    with pytest.raises(ValueError, match="reference manifest criteria"):
        manifest(gates=(gate(criterion_ids=("missing-criterion",)),))


def test_manifest_rejects_missing_claim_boundary() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        manifest(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_manifest_rejects_external_registration_from_internal_source() -> None:
    with pytest.raises(ValueError, match="external source system"):
        manifest(source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL)


def test_manifest_rejects_internal_draft_from_external_source() -> None:
    with pytest.raises(ValueError, match="Draft internal protocols"):
        manifest(registration_state=WaveFiveProtocolRegistrationState.DRAFT_INTERNAL)


def test_internal_draft_from_kernel_is_not_ready_for_execution() -> None:
    draft = manifest(
        registration_state=WaveFiveProtocolRegistrationState.DRAFT_INTERNAL,
        source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    )

    assert draft.is_externally_preregistered is False
    assert draft.ready_for_independent_execution is False
    assert draft.to_artifact_ref().decision is (
        WaveFiveArtifactDecision.NEEDS_EXTERNAL_EVIDENCE
    )


def test_manifest_reports_missing_domain_and_gate_coverage() -> None:
    incomplete = manifest(
        domains=(WaveFiveProtocolDomain.EXTERNAL_REVIEW,),
        gates=(
            gate(
                gate_kind=WaveFiveAcceptanceGateKind.REQUIRED_EVIDENCE_PRESENT,
                criterion_ids=("criterion-external-review",),
            ),
        ),
    )

    assert incomplete.has_required_domain_coverage is False
    assert WaveFiveProtocolDomain.REPRODUCIBILITY in incomplete.missing_required_domains
    assert incomplete.has_required_gate_coverage is False
    assert WaveFiveAcceptanceGateKind.INDEPENDENT_REVIEWER_PRESENT in (
        incomplete.missing_required_acceptance_gates
    )
    assert incomplete.ready_for_independent_execution is False


def test_complete_manifest_is_ready_for_independent_execution() -> None:
    ready = manifest()

    assert ready.is_externally_preregistered is True
    assert ready.has_required_domain_coverage is True
    assert ready.has_required_gate_coverage is True
    assert ready.has_falsification_criteria is True
    assert ready.has_negative_controls is True
    assert ready.ready_for_independent_execution is True
    assert ready.blocking_gates == (
        "gate-adversarial",
        "gate-boundary",
        "gate-evidence",
        "gate-human-authority",
        "gate-reproduction",
        "gate-reviewer",
    )


def test_manifest_collects_unique_evidence_ids_in_criterion_order() -> None:
    ready = manifest()

    assert ready.evidence_ids == (
        "evidence-adversarial",
        "evidence-cross-domain",
        "evidence-ecosystem",
        "evidence-external-review",
        "evidence-human-authority",
        "evidence-long-horizon",
        "evidence-memory",
        "evidence-reproducibility",
        "evidence-safe-refusal",
        "evidence-wave-six",
    )


def test_ready_manifest_exports_as_reviewable_artifact_ref() -> None:
    artifact = manifest().to_artifact_ref()

    assert artifact.kind is WaveFiveArtifactKind.EXTERNAL_PROTOCOL_MANIFEST
    assert artifact.capability_area is WaveFiveCapabilityArea.EXTERNAL_PROTOCOLS
    assert artifact.source_system is WaveFiveSourceSystem.EXTERNAL_VALIDATION_PROTOCOL
    assert artifact.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    assert artifact.authority_state is WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    )
    assert artifact.ready_for_independent_review is True


def test_rejected_manifest_exports_blocking_artifact_ref() -> None:
    rejected = manifest(
        registration_state=WaveFiveProtocolRegistrationState.REJECTED,
        source_system=WaveFiveSourceSystem.EXTERNAL_VALIDATION_PROTOCOL,
    ).to_artifact_ref()

    assert rejected.decision is WaveFiveArtifactDecision.BLOCKED
    assert rejected.authority_state is WaveFiveAuthorityState.BLOCKED
    assert rejected.validation_status is WaveFiveValidationStatus.REJECTED
    assert rejected.blocks_progress is True


def test_manifest_fingerprint_is_deterministic() -> None:
    ready = manifest()

    assert ready.fingerprint() == ready.fingerprint()
    assert len(ready.fingerprint()) == 64


def test_manifest_payload_preserves_wave_six_and_no_overclaim_controls() -> None:
    payload = manifest().canonical_payload()

    assert "wave-six-preconditions" in payload["domains"]
    assert "no-agi-claim" in payload["claim_boundaries"]
    assert "no-self-validation" in payload["claim_boundaries"]
    assert payload["source_system"] == "external-validation-protocol"
