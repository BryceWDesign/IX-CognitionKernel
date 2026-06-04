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
from ix_cognition_kernel.wave5_cross_domain_transfer import (
    EXTERNAL_TRANSFER_REVIEW_SOURCE_SYSTEMS,
    REQUIRED_WAVE_FIVE_NEGATIVE_CONTROLS,
    REQUIRED_WAVE_FIVE_TRANSFER_DIMENSIONS,
    SAFE_WAVE_FIVE_TRANSFER_OUTCOMES,
    WaveFiveCrossDomainTransferRecord,
    WaveFiveTransferDimension,
    WaveFiveTransferDomain,
    WaveFiveTransferNegativeControl,
    WaveFiveTransferNegativeControlKind,
    WaveFiveTransferObservation,
    WaveFiveTransferOutcome,
    WaveFiveTransferReviewState,
    WaveFiveTransferSourceCapability,
    WaveFiveTransferTargetDomain,
    external_transfer_review_source_systems,
    required_wave_five_transfer_dimensions,
    required_wave_five_transfer_negative_controls,
    safe_wave_five_transfer_outcomes,
)


def source(
    source_capability_id: str = "source-causal-evidence",
    *,
    source_domain: WaveFiveTransferDomain = WaveFiveTransferDomain.CAUSAL_REASONING,
) -> WaveFiveTransferSourceCapability:
    return WaveFiveTransferSourceCapability(
        source_capability_id=source_capability_id,
        source_domain=source_domain,
        capability_summary=(
            "Uses causal evidence constraints without hiding uncertainty."
        ),
        invariant_claims=(
            "Evidence must remain bound to the reviewed claim.",
            "Human authority cannot be bypassed by transfer success.",
        ),
        prohibited_assumptions=(
            "Do not treat analogy as proof.",
            "Do not claim target-domain mastery from source-domain success.",
        ),
        protocol_ids=("wave5-external-protocol-001",),
        evidence_ids=(f"evidence-{source_capability_id}",),
    )


def target(
    target_id: str = "target-scenario-reasoning",
    *,
    source_capability_id: str = "source-causal-evidence",
    target_domain: WaveFiveTransferDomain = WaveFiveTransferDomain.SCENARIO_REASONING,
) -> WaveFiveTransferTargetDomain:
    return WaveFiveTransferTargetDomain(
        target_id=target_id,
        source_capability_id=source_capability_id,
        target_domain=target_domain,
        novelty_summary="Target requires new scenario reasoning, not source replay.",
        adaptation_constraints=(
            "Keep invariant evidence binding visible.",
            "Expose uncertainty instead of stretching the analogy.",
        ),
        prohibited_shortcuts=(
            "No benchmark memory credit.",
            "No target-domain overfit credit.",
        ),
        scenario_ids=(f"scenario-{target_id}",),
        evidence_ids=(f"evidence-{target_id}",),
    )


def observation(
    observation_id: str = "observation-scenario-reasoning",
    *,
    target_id: str = "target-scenario-reasoning",
    outcome: WaveFiveTransferOutcome = (
        WaveFiveTransferOutcome.BOUNDED_TRANSFER_CONFIRMED
    ),
    dimensions: tuple[WaveFiveTransferDimension, ...] = (
        REQUIRED_WAVE_FIVE_TRANSFER_DIMENSIONS
    ),
    preserved_uncertainty: bool = True,
    preserved_human_authority: bool = True,
    evidence_bound: bool = True,
    violated_invariants: tuple[str, ...] = (),
) -> WaveFiveTransferObservation:
    return WaveFiveTransferObservation(
        observation_id=observation_id,
        target_id=target_id,
        outcome=outcome,
        observed_behavior="Target-domain transfer stayed bounded and reviewable.",
        matched_invariants=("Evidence must remain bound to the reviewed claim.",),
        violated_invariants=violated_invariants,
        covered_dimensions=dimensions,
        preserved_uncertainty=preserved_uncertainty,
        preserved_human_authority=preserved_human_authority,
        evidence_bound=evidence_bound,
        evidence_ids=(f"evidence-{observation_id}",),
    )


def negative_control(
    control_id: str = "control-benchmark-memorization",
    *,
    target_id: str = "target-scenario-reasoning",
    control_kind: WaveFiveTransferNegativeControlKind = (
        WaveFiveTransferNegativeControlKind.BENCHMARK_MEMORIZATION
    ),
    detected: bool = True,
    blocking: bool = True,
) -> WaveFiveTransferNegativeControl:
    mitigation = (
        "Reject shortcut and preserve failed-transfer evidence." if detected else ""
    )
    return WaveFiveTransferNegativeControl(
        control_id=control_id,
        target_id=target_id,
        control_kind=control_kind,
        invalid_shortcut="Invalid shortcut attempts to pass as real transfer.",
        expected_detection="Kernel must detect the invalid transfer shortcut.",
        detected=detected,
        blocking=blocking,
        evidence_ids=(f"evidence-{control_id}",),
        mitigation=mitigation,
    )


def required_targets() -> tuple[WaveFiveTransferTargetDomain, ...]:
    return (
        target(
            "target-scenario-reasoning",
            target_domain=WaveFiveTransferDomain.SCENARIO_REASONING,
        ),
        target(
            "target-memory-governance",
            target_domain=WaveFiveTransferDomain.MEMORY_GOVERNANCE,
        ),
        target(
            "target-human-authority",
            target_domain=WaveFiveTransferDomain.HUMAN_AUTHORITY_GOVERNANCE,
        ),
    )


def required_observations() -> tuple[WaveFiveTransferObservation, ...]:
    return tuple(
        observation(
            f"observation-{item.target_domain.value}",
            target_id=item.target_id,
        )
        for item in required_targets()
    )


def required_negative_controls() -> tuple[WaveFiveTransferNegativeControl, ...]:
    return tuple(
        negative_control(
            f"control-{kind.value}",
            control_kind=kind,
        )
        for kind in REQUIRED_WAVE_FIVE_NEGATIVE_CONTROLS
    )


def record(
    *,
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    review_state: WaveFiveTransferReviewState = (
        WaveFiveTransferReviewState.READY_FOR_EXTERNAL_TRANSFER_REVIEW
    ),
    sources: tuple[WaveFiveTransferSourceCapability, ...] | None = None,
    targets: tuple[WaveFiveTransferTargetDomain, ...] | None = None,
    observations: tuple[WaveFiveTransferObservation, ...] | None = None,
    controls: tuple[WaveFiveTransferNegativeControl, ...] | None = None,
    reviewer_ids: tuple[str, ...] = (),
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    ),
) -> WaveFiveCrossDomainTransferRecord:
    resolved_sources = (source(),) if sources is None else sources
    resolved_targets = required_targets() if targets is None else targets
    resolved_observations = (
        required_observations() if observations is None else observations
    )
    resolved_controls = required_negative_controls() if controls is None else controls

    return WaveFiveCrossDomainTransferRecord(
        record_id="wave5-cross-domain-transfer-record-001",
        title="Wave 5 cross-domain transfer validation record.",
        source_system=source_system,
        review_state=review_state,
        sources=resolved_sources,
        targets=resolved_targets,
        observations=resolved_observations,
        negative_controls=resolved_controls,
        protocol_ids=("wave5-external-protocol-001",),
        reviewer_ids=reviewer_ids,
        claim_boundaries=claim_boundaries,
        notes=("Transfer success is evidence only, never an AGI claim.",),
    )


def test_required_transfer_dimensions_are_locked() -> None:
    assert required_wave_five_transfer_dimensions() == (
        REQUIRED_WAVE_FIVE_TRANSFER_DIMENSIONS
    )
    assert len(REQUIRED_WAVE_FIVE_TRANSFER_DIMENSIONS) == 8
    assert WaveFiveTransferDimension.NO_CUSTOM_RETRAINING in (
        REQUIRED_WAVE_FIVE_TRANSFER_DIMENSIONS
    )


def test_required_negative_controls_are_locked() -> None:
    assert required_wave_five_transfer_negative_controls() == (
        REQUIRED_WAVE_FIVE_NEGATIVE_CONTROLS
    )
    assert len(REQUIRED_WAVE_FIVE_NEGATIVE_CONTROLS) == 7
    assert WaveFiveTransferNegativeControlKind.AUTHORITY_ESCALATION in (
        REQUIRED_WAVE_FIVE_NEGATIVE_CONTROLS
    )


def test_safe_transfer_outcomes_are_locked() -> None:
    assert safe_wave_five_transfer_outcomes() == SAFE_WAVE_FIVE_TRANSFER_OUTCOMES
    assert WaveFiveTransferOutcome.AUTHORITY_BYPASS not in (
        SAFE_WAVE_FIVE_TRANSFER_OUTCOMES
    )


def test_external_transfer_review_sources_are_locked() -> None:
    assert external_transfer_review_source_systems() == (
        EXTERNAL_TRANSFER_REVIEW_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.INDEPENDENT_REVIEWER in (
        EXTERNAL_TRANSFER_REVIEW_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.IX_COGNITION_KERNEL not in (
        EXTERNAL_TRANSFER_REVIEW_SOURCE_SYSTEMS
    )


def test_source_capability_requires_invariants() -> None:
    with pytest.raises(ValueError, match="require invariants"):
        WaveFiveTransferSourceCapability(
            source_capability_id="source-invalid",
            source_domain=WaveFiveTransferDomain.CAUSAL_REASONING,
            capability_summary="Invalid source without invariants.",
            invariant_claims=(),
            prohibited_assumptions=("No analogy-as-proof.",),
            protocol_ids=("protocol",),
            evidence_ids=("evidence",),
        )


def test_source_capability_requires_prohibited_assumptions() -> None:
    with pytest.raises(ValueError, match="prohibited assumptions"):
        WaveFiveTransferSourceCapability(
            source_capability_id="source-invalid",
            source_domain=WaveFiveTransferDomain.CAUSAL_REASONING,
            capability_summary="Invalid source without prohibited assumptions.",
            invariant_claims=("Evidence binding remains visible.",),
            prohibited_assumptions=(),
            protocol_ids=("protocol",),
            evidence_ids=("evidence",),
        )


def test_target_rejects_custom_retraining() -> None:
    with pytest.raises(ValueError, match="custom retraining"):
        WaveFiveTransferTargetDomain(
            target_id="target-invalid",
            source_capability_id="source-causal-evidence",
            target_domain=WaveFiveTransferDomain.SCENARIO_REASONING,
            novelty_summary="Invalid target uses custom retraining.",
            adaptation_constraints=("Keep evidence visible.",),
            prohibited_shortcuts=("No overfit credit.",),
            scenario_ids=("scenario",),
            evidence_ids=("evidence",),
            used_custom_retraining=True,
        )


def test_observation_rejects_safe_outcome_without_evidence_binding() -> None:
    with pytest.raises(ValueError, match="evidence bound"):
        observation(evidence_bound=False)


def test_observation_rejects_safe_outcome_without_uncertainty() -> None:
    with pytest.raises(ValueError, match="preserve uncertainty"):
        observation(preserved_uncertainty=False)


def test_observation_rejects_safe_outcome_without_authority() -> None:
    with pytest.raises(ValueError, match="preserve authority"):
        observation(preserved_human_authority=False)


def test_confirmed_transfer_rejects_violated_invariants() -> None:
    with pytest.raises(ValueError, match="cannot violate invariants"):
        observation(violated_invariants=("Evidence binding was lost.",))


def test_authority_bypass_observation_blocks_progress() -> None:
    item = observation(
        outcome=WaveFiveTransferOutcome.AUTHORITY_BYPASS,
        preserved_human_authority=False,
    )

    assert item.is_safe_outcome is False
    assert item.blocks_wave_five_progress is True


def test_negative_control_requires_mitigation_when_detected() -> None:
    with pytest.raises(ValueError, match="require mitigation"):
        WaveFiveTransferNegativeControl(
            control_id="control-invalid",
            target_id="target-scenario-reasoning",
            control_kind=WaveFiveTransferNegativeControlKind.UNSUPPORTED_ANALOGY,
            invalid_shortcut="Unsupported analogy is presented as proof.",
            expected_detection="Kernel must reject unsupported analogy.",
            detected=True,
            blocking=True,
            evidence_ids=("evidence",),
        )


def test_unresolved_negative_control_blocks_progress() -> None:
    item = negative_control(detected=False)

    assert item.resolved is False
    assert item.blocks_wave_five_progress is True


def test_record_rejects_target_for_unknown_source() -> None:
    with pytest.raises(ValueError, match="source capabilities"):
        record(targets=(target(source_capability_id="missing-source"),))


def test_record_rejects_observation_for_unknown_target() -> None:
    with pytest.raises(ValueError, match="reference bundled targets"):
        record(observations=(observation(target_id="missing-target"),))


def test_record_rejects_target_without_observation() -> None:
    with pytest.raises(ValueError, match="require observations"):
        record(
            targets=(target("target-one"), target("target-two")),
            observations=(observation(target_id="target-one"),),
        )


def test_record_rejects_missing_claim_boundary() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        record(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_record_reports_missing_dimension_and_negative_control_coverage() -> None:
    item = record(
        observations=(
            observation(
                target_id="target-scenario-reasoning",
                dimensions=(WaveFiveTransferDimension.NOVEL_TARGET_DOMAIN,),
            ),
            observation(
                "observation-memory-governance",
                target_id="target-memory-governance",
                dimensions=(WaveFiveTransferDimension.NOVEL_TARGET_DOMAIN,),
            ),
            observation(
                "observation-human-authority",
                target_id="target-human-authority",
                dimensions=(WaveFiveTransferDimension.NOVEL_TARGET_DOMAIN,),
            ),
        ),
        controls=(
            negative_control(
                control_kind=WaveFiveTransferNegativeControlKind.BENCHMARK_MEMORIZATION
            ),
        ),
    )

    assert item.has_required_dimension_coverage is False
    assert WaveFiveTransferDimension.EVIDENCE_BINDING in (
        item.missing_required_dimensions
    )
    assert item.has_required_negative_control_coverage is False
    assert WaveFiveTransferNegativeControlKind.AUTHORITY_ESCALATION in (
        item.missing_required_negative_controls
    )
    assert item.ready_for_external_transfer_review is False


def test_record_is_ready_for_external_transfer_review() -> None:
    item = record()

    assert item.has_required_target_domain_coverage is True
    assert item.has_required_dimension_coverage is True
    assert item.has_required_negative_control_coverage is True
    assert item.blocking_observation_ids == ()
    assert item.blocking_negative_control_ids == ()
    assert item.preserves_uncertainty is True
    assert item.preserves_human_authority is True
    assert item.evidence_bound is True
    assert item.ready_for_external_transfer_review is True


def test_ready_record_exports_reviewable_artifact() -> None:
    artifact = record().to_artifact_ref()

    assert artifact.kind is WaveFiveArtifactKind.CROSS_DOMAIN_TRANSFER_RECORD
    assert artifact.capability_area is WaveFiveCapabilityArea.CROSS_DOMAIN_TRANSFER
    assert artifact.source_system is WaveFiveSourceSystem.IX_COGNITION_KERNEL
    assert artifact.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    assert artifact.authority_state is WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    )


def test_blocking_observation_exports_blocked_artifact() -> None:
    observations = (
        observation(
            target_id="target-scenario-reasoning",
            outcome=WaveFiveTransferOutcome.AUTHORITY_BYPASS,
            preserved_human_authority=False,
        ),
        observation(
            "observation-memory-governance",
            target_id="target-memory-governance",
        ),
        observation(
            "observation-human-authority",
            target_id="target-human-authority",
        ),
    )
    artifact = record(observations=observations).to_artifact_ref()

    assert artifact.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact.authority_state is WaveFiveAuthorityState.BLOCKED
    assert artifact.validation_status is WaveFiveValidationStatus.REJECTED


def test_externally_reviewed_record_requires_external_source() -> None:
    with pytest.raises(ValueError, match="external source"):
        record(
            review_state=(
                WaveFiveTransferReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
            reviewer_ids=("reviewer-001",),
        )


def test_externally_reviewed_record_requires_reviewer_ids() -> None:
    with pytest.raises(ValueError, match="reviewer ids"):
        record(
            source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
            review_state=(
                WaveFiveTransferReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
        )


def test_externally_reviewed_record_exports_bounded_external_artifact() -> None:
    item = record(
        source_system=WaveFiveSourceSystem.INDEPENDENT_REVIEWER,
        review_state=WaveFiveTransferReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES,
        reviewer_ids=("reviewer-001",),
    )
    artifact = item.to_artifact_ref()

    assert item.externally_reviewed_with_boundaries is True
    assert artifact.decision is WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.ACCEPTED_WITH_BOUNDARIES
    )
    assert artifact.externally_validated_with_boundaries is True


def test_record_collects_unique_evidence_ids() -> None:
    item = record()

    assert item.all_evidence_ids[0] == "evidence-source-causal-evidence"
    assert "evidence-control-evidence-chain-break" in item.all_evidence_ids
    assert len(item.all_evidence_ids) == 14


def test_record_fingerprint_is_deterministic() -> None:
    item = record()

    assert item.fingerprint() == item.fingerprint()
    assert len(item.fingerprint()) == 64
