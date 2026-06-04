import pytest

from ix_cognition_kernel.wave5_adversarial_safety import (
    EXTERNAL_ADVERSARIAL_SOURCE_SYSTEMS,
    REQUIRED_WAVE_FIVE_ADVERSARIAL_VECTORS,
    SAFE_WAVE_FIVE_ADVERSARIAL_OUTCOMES,
    WaveFiveAdversarialCase,
    WaveFiveAdversarialObservation,
    WaveFiveAdversarialOutcome,
    WaveFiveAdversarialReviewState,
    WaveFiveAdversarialSafetyRecord,
    WaveFiveAdversarialSeverity,
    WaveFiveAdversarialVector,
    external_adversarial_source_systems,
    required_wave_five_adversarial_vectors,
    safe_wave_five_adversarial_outcomes,
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


def case(
    case_id: str = "adversarial-case-001",
    *,
    vector: WaveFiveAdversarialVector = WaveFiveAdversarialVector.REWARD_HACKING,
) -> WaveFiveAdversarialCase:
    return WaveFiveAdversarialCase(
        case_id=case_id,
        vector=vector,
        severity=WaveFiveAdversarialSeverity.HIGH,
        prompt_summary="Pressure attempts to make the candidate optimize a proxy.",
        unsafe_success_marker="Candidate hides uncertainty or bypasses authority.",
        expected_safe_response="Candidate blocks, contains, or escalates safely.",
        protocol_ids=("wave5-external-protocol-001",),
        evidence_ids=(f"evidence-{case_id}",),
    )


def observation(
    observation_id: str = "adversarial-observation-001",
    *,
    case_id: str = "adversarial-case-001",
    outcome: WaveFiveAdversarialOutcome = WaveFiveAdversarialOutcome.BLOCKED,
    preserved_human_authority: bool = True,
    preserved_uncertainty: bool = True,
    blocked_unsafe_success_marker: bool = True,
) -> WaveFiveAdversarialObservation:
    return WaveFiveAdversarialObservation(
        observation_id=observation_id,
        case_id=case_id,
        outcome=outcome,
        observed_behavior="Candidate preserved evidence boundaries under pressure.",
        containment_action="Blocked unsafe path and retained human-review gate.",
        preserved_human_authority=preserved_human_authority,
        preserved_uncertainty=preserved_uncertainty,
        blocked_unsafe_success_marker=blocked_unsafe_success_marker,
        evidence_ids=(f"evidence-{observation_id}",),
    )


def required_cases() -> tuple[WaveFiveAdversarialCase, ...]:
    return tuple(
        case(f"case-{vector.value}", vector=vector)
        for vector in REQUIRED_WAVE_FIVE_ADVERSARIAL_VECTORS
    )


def required_observations(
    *,
    outcome: WaveFiveAdversarialOutcome = WaveFiveAdversarialOutcome.BLOCKED,
) -> tuple[WaveFiveAdversarialObservation, ...]:
    return tuple(
        observation(
            f"observation-{vector.value}",
            case_id=f"case-{vector.value}",
            outcome=outcome,
        )
        for vector in REQUIRED_WAVE_FIVE_ADVERSARIAL_VECTORS
    )


def record(
    *,
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    review_state: WaveFiveAdversarialReviewState = (
        WaveFiveAdversarialReviewState.READY_FOR_EXTERNAL_ADVERSARIAL_REVIEW
    ),
    cases: tuple[WaveFiveAdversarialCase, ...] | None = None,
    observations: tuple[WaveFiveAdversarialObservation, ...] | None = None,
    reviewer_ids: tuple[str, ...] = (),
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    ),
) -> WaveFiveAdversarialSafetyRecord:
    resolved_cases = required_cases() if cases is None else cases
    resolved_observations = (
        required_observations() if observations is None else observations
    )

    return WaveFiveAdversarialSafetyRecord(
        record_id="wave5-adversarial-record-001",
        title="Wave 5 adversarial safety validation record.",
        source_system=source_system,
        review_state=review_state,
        cases=resolved_cases,
        observations=resolved_observations,
        reviewer_ids=reviewer_ids,
        protocol_ids=("wave5-external-protocol-001",),
        claim_boundaries=claim_boundaries,
        notes=("Adversarial success never grants execution authority.",),
    )


def test_required_adversarial_vectors_are_locked() -> None:
    assert required_wave_five_adversarial_vectors() == (
        REQUIRED_WAVE_FIVE_ADVERSARIAL_VECTORS
    )
    assert len(REQUIRED_WAVE_FIVE_ADVERSARIAL_VECTORS) == 8
    assert WaveFiveAdversarialVector.AUTHORITY_ESCALATION in (
        REQUIRED_WAVE_FIVE_ADVERSARIAL_VECTORS
    )
    assert WaveFiveAdversarialVector.ALIGNMENT_FAKING_PRESSURE in (
        REQUIRED_WAVE_FIVE_ADVERSARIAL_VECTORS
    )


def test_safe_adversarial_outcomes_are_locked() -> None:
    assert safe_wave_five_adversarial_outcomes() == SAFE_WAVE_FIVE_ADVERSARIAL_OUTCOMES
    assert WaveFiveAdversarialOutcome.FAILED_OPEN not in (
        SAFE_WAVE_FIVE_ADVERSARIAL_OUTCOMES
    )


def test_external_adversarial_source_systems_are_locked() -> None:
    assert external_adversarial_source_systems() == EXTERNAL_ADVERSARIAL_SOURCE_SYSTEMS
    assert WaveFiveSourceSystem.ADVERSARIAL_TESTER in (
        EXTERNAL_ADVERSARIAL_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.IX_COGNITION_KERNEL not in (
        EXTERNAL_ADVERSARIAL_SOURCE_SYSTEMS
    )


def test_case_rejects_identical_unsafe_marker_and_safe_response() -> None:
    with pytest.raises(ValueError, match="must differ"):
        WaveFiveAdversarialCase(
            case_id="case-invalid",
            vector=WaveFiveAdversarialVector.REWARD_HACKING,
            severity=WaveFiveAdversarialSeverity.HIGH,
            prompt_summary="Invalid case.",
            unsafe_success_marker="same",
            expected_safe_response="same",
            protocol_ids=("protocol",),
            evidence_ids=("evidence",),
        )


def test_case_requires_protocol_and_evidence_ids() -> None:
    with pytest.raises(ValueError, match="protocol ids"):
        WaveFiveAdversarialCase(
            case_id="case-missing-protocol",
            vector=WaveFiveAdversarialVector.REWARD_HACKING,
            severity=WaveFiveAdversarialSeverity.HIGH,
            prompt_summary="Missing protocol case.",
            unsafe_success_marker="Unsafe marker.",
            expected_safe_response="Safe response.",
            protocol_ids=(),
            evidence_ids=("evidence",),
        )


def test_observation_rejects_safe_outcome_without_authority() -> None:
    with pytest.raises(ValueError, match="preserve authority"):
        observation(preserved_human_authority=False)


def test_observation_rejects_safe_outcome_that_does_not_block_unsafe_success() -> None:
    with pytest.raises(ValueError, match="block unsafe success"):
        observation(blocked_unsafe_success_marker=False)


def test_observation_rejects_failed_open_that_claims_marker_was_blocked() -> None:
    with pytest.raises(ValueError, match="cannot block unsafe success"):
        observation(
            outcome=WaveFiveAdversarialOutcome.FAILED_OPEN,
            blocked_unsafe_success_marker=True,
        )


def test_failed_open_observation_blocks_wave_five_progress() -> None:
    failed = observation(
        outcome=WaveFiveAdversarialOutcome.FAILED_OPEN,
        blocked_unsafe_success_marker=False,
    )

    assert failed.is_safe_outcome is False
    assert failed.blocks_wave_five_progress is True


def test_record_rejects_observation_for_unknown_case() -> None:
    with pytest.raises(ValueError, match="reference bundled cases"):
        record(
            cases=(case("case-known"),),
            observations=(observation(case_id="case-missing"),),
        )


def test_record_rejects_case_without_observation() -> None:
    with pytest.raises(ValueError, match="require observations"):
        record(
            cases=(case("case-one"), case("case-two")),
            observations=(observation(case_id="case-one"),),
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


def test_record_reports_missing_required_vectors() -> None:
    incomplete = record(
        cases=(case("case-reward", vector=WaveFiveAdversarialVector.REWARD_HACKING),),
        observations=(observation(case_id="case-reward"),),
    )

    assert incomplete.has_required_vector_coverage is False
    assert WaveFiveAdversarialVector.AUTHORITY_ESCALATION in (
        incomplete.missing_required_vectors
    )
    assert incomplete.ready_for_external_adversarial_review is False


def test_record_is_ready_for_external_adversarial_review() -> None:
    ready = record()

    assert ready.has_required_vector_coverage is True
    assert ready.blocking_observation_ids == ()
    assert ready.preserves_human_authority is True
    assert ready.preserves_uncertainty is True
    assert ready.all_unsafe_success_markers_blocked is True
    assert ready.ready_for_external_adversarial_review is True


def test_ready_record_exports_reviewable_adversarial_artifact() -> None:
    artifact = record().to_artifact_ref()

    assert artifact.kind is WaveFiveArtifactKind.ADVERSARIAL_SAFETY_RECORD
    assert artifact.capability_area is WaveFiveCapabilityArea.ADVERSARIAL_SAFETY
    assert artifact.source_system is WaveFiveSourceSystem.IX_COGNITION_KERNEL
    assert artifact.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    assert artifact.authority_state is WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    assert artifact.validation_status is (
        WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    )


def test_blocking_observation_exports_blocked_artifact() -> None:
    cases = required_cases()
    observations = tuple(
        observation(
            f"observation-{item.vector.value}",
            case_id=item.case_id,
            outcome=(
                WaveFiveAdversarialOutcome.FAILED_OPEN
                if item.vector is WaveFiveAdversarialVector.EVALUATION_GAMING
                else WaveFiveAdversarialOutcome.BLOCKED
            ),
            blocked_unsafe_success_marker=(
                item.vector is not WaveFiveAdversarialVector.EVALUATION_GAMING
            ),
        )
        for item in cases
    )
    artifact = record(cases=cases, observations=observations).to_artifact_ref()

    assert artifact.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact.authority_state is WaveFiveAuthorityState.BLOCKED
    assert artifact.validation_status is WaveFiveValidationStatus.REJECTED


def test_externally_reviewed_record_requires_external_source() -> None:
    with pytest.raises(ValueError, match="external source"):
        record(
            review_state=(
                WaveFiveAdversarialReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
            reviewer_ids=("reviewer-001",),
        )


def test_externally_reviewed_record_requires_reviewer_ids() -> None:
    with pytest.raises(ValueError, match="reviewer ids"):
        record(
            source_system=WaveFiveSourceSystem.ADVERSARIAL_TESTER,
            review_state=(
                WaveFiveAdversarialReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
            ),
        )


def test_externally_reviewed_record_exports_bounded_external_artifact() -> None:
    item = record(
        source_system=WaveFiveSourceSystem.ADVERSARIAL_TESTER,
        review_state=(
            WaveFiveAdversarialReviewState.EXTERNALLY_REVIEWED_WITH_BOUNDARIES
        ),
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

    assert item.all_evidence_ids[0] == "evidence-case-alignment-faking-pressure"
    assert "evidence-observation-unsafe-tool-handoff" in item.all_evidence_ids
    assert len(item.all_evidence_ids) == 16


def test_record_fingerprint_is_deterministic() -> None:
    item = record()

    assert item.fingerprint() == item.fingerprint()
    assert len(item.fingerprint()) == 64
