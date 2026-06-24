import pytest

from ix_cognition_kernel.wave7_observation_action_schema import (
    ActionIntent,
    ActionIntentKind,
    ActionProposalEnvelope,
    EvidenceRequirementStatus,
    ObservationActionTrace,
    ObservationFrame,
    ObservationReliability,
    ObservedOutcome,
    OutcomeAlignment,
    ProposalEvidenceRequirement,
    ProposalReadiness,
    ProposalRisk,
    assess_proposal_readiness,
    build_observation_action_trace,
)


def _observation(
    *,
    reliability: ObservationReliability = ObservationReliability.MEASURED,
    frame_id: str = "frame-1",
    captured_after_action_id: str = "prior-action-1",
) -> ObservationFrame:
    return ObservationFrame(
        frame_id=frame_id,
        surface_id="surface-sim-1",
        channel_id="channel-sim-1",
        observed_state_ids=("state-policy-1",),
        observation_summary="The bounded simulation state was observed.",
        evidence_ids=("observation-evidence-1",),
        reliability=reliability,
        captured_after_action_id=captured_after_action_id,
    )


def _intent() -> ActionIntent:
    return ActionIntent(
        intent_id="intent-1",
        kind=ActionIntentKind.SIMULATE,
        surface_id="surface-sim-1",
        requested_operation="simulate-trial",
        purpose="Run a bounded simulation before any runtime handoff.",
        expected_state_change="The simulation will expose whether the rule holds.",
        evidence_ids=("intent-evidence-1",),
        originating_observation_ids=("frame-1",),
    )


def _requirement(
    *,
    status: EvidenceRequirementStatus = EvidenceRequirementStatus.SATISFIED,
    requirement_id: str = "requirement-1",
    satisfied_evidence_ids: tuple[str, ...] = ("requirement-evidence-1",),
    authority_refs: tuple[str, ...] = (),
) -> ProposalEvidenceRequirement:
    return ProposalEvidenceRequirement(
        requirement_id=requirement_id,
        description="Prediction and bounded-surface evidence must be present.",
        required_evidence_kinds=("prediction", "bounded-surface"),
        satisfied_evidence_ids=satisfied_evidence_ids,
        status=status,
        authority_refs=authority_refs,
    )


def _envelope(
    *,
    observations: tuple[ObservationFrame, ...] | None = None,
    requirements: tuple[ProposalEvidenceRequirement, ...] | None = None,
    readiness: ProposalReadiness = ProposalReadiness.READY_FOR_REVIEW,
    risk: ProposalRisk = ProposalRisk.MODERATE,
) -> ActionProposalEnvelope:
    return ActionProposalEnvelope(
        envelope_id="envelope-1",
        intent=_intent(),
        observations=observations or (_observation(),),
        evidence_requirements=requirements
        or (
            _requirement(),
            _requirement(
                status=EvidenceRequirementStatus.REQUIRES_REVIEW,
                requirement_id="requirement-review-1",
                satisfied_evidence_ids=(),
                authority_refs=("human-authority-1",),
            ),
        ),
        risk=risk,
        predicted_outcome="The simulation should preserve the safety boundary.",
        readiness=readiness,
        reviewer_notes=("Review before any runtime airlock escalation.",),
    )


def _outcome(
    *,
    alignment: OutcomeAlignment = OutcomeAlignment.MATCHED,
    lesson: str = "",
    measured_state_ids: tuple[str, ...] = ("state-policy-1",),
) -> ObservedOutcome:
    return ObservedOutcome(
        outcome_id="outcome-1",
        envelope_id="envelope-1",
        outcome_summary="The bounded simulation preserved the expected boundary.",
        evidence_ids=("outcome-evidence-1",),
        alignment=alignment,
        measured_state_ids=measured_state_ids,
        lesson=lesson,
    )


def test_observation_frame_is_evidence_bound_and_not_ground_truth() -> None:
    frame = _observation()

    assert frame.measured
    assert not frame.blocks_claim
    assert frame.fingerprint() == frame.fingerprint()
    assert len(frame.fingerprint()) == 64

    with pytest.raises(ValueError, match="must not claim ground truth"):
        ObservationFrame(
            frame_id="frame-ground-truth",
            surface_id="surface-sim-1",
            channel_id="channel-sim-1",
            observed_state_ids=("state-policy-1",),
            observation_summary="Bad ground truth claim.",
            evidence_ids=("observation-evidence-1",),
            claims_ground_truth=True,
        )


def test_measured_observation_requires_captured_action() -> None:
    with pytest.raises(ValueError, match="captured_after_action_id"):
        _observation(
            reliability=ObservationReliability.MEASURED,
            captured_after_action_id="",
        )


def test_unverified_or_contradicted_observations_block_claims() -> None:
    unverified = _observation(
        reliability=ObservationReliability.UNVERIFIED,
        captured_after_action_id="",
    )
    contradicted = _observation(
        reliability=ObservationReliability.CONTRADICTED,
        captured_after_action_id="",
    )

    assert unverified.blocks_claim
    assert contradicted.blocks_claim


def test_action_intent_rejects_self_authorization_and_permission_claims() -> None:
    with pytest.raises(ValueError, match="must not self-authorize"):
        ActionIntent(
            intent_id="intent-self-authorized",
            kind=ActionIntentKind.SIMULATE,
            surface_id="surface-sim-1",
            requested_operation="simulate-trial",
            purpose="Bad self authorization.",
            expected_state_change="Bad state change.",
            evidence_ids=("intent-evidence-1",),
            originating_observation_ids=("frame-1",),
            self_authorized=True,
        )

    with pytest.raises(ValueError, match="must not claim permission"):
        ActionIntent(
            intent_id="intent-permission",
            kind=ActionIntentKind.SIMULATE,
            surface_id="surface-sim-1",
            requested_operation="simulate-trial",
            purpose="Bad permission claim.",
            expected_state_change="Bad state change.",
            evidence_ids=("intent-evidence-1",),
            originating_observation_ids=("frame-1",),
            claims_permission=True,
        )


def test_non_noop_intent_requires_observation_ids() -> None:
    with pytest.raises(ValueError, match="require observation ids"):
        ActionIntent(
            intent_id="intent-no-observations",
            kind=ActionIntentKind.SIMULATE,
            surface_id="surface-sim-1",
            requested_operation="simulate-trial",
            purpose="Missing observations.",
            expected_state_change="Bad state change.",
            evidence_ids=("intent-evidence-1",),
            originating_observation_ids=(),
        )


def test_evidence_requirement_states_are_fail_closed() -> None:
    satisfied = _requirement()
    review = _requirement(
        status=EvidenceRequirementStatus.REQUIRES_REVIEW,
        requirement_id="requirement-review",
        satisfied_evidence_ids=(),
        authority_refs=("human-authority-1",),
    )
    missing = _requirement(
        status=EvidenceRequirementStatus.MISSING,
        requirement_id="requirement-missing",
        satisfied_evidence_ids=(),
    )

    assert satisfied.satisfied
    assert review.needs_review
    assert missing.blocks_readiness

    with pytest.raises(ValueError, match="Satisfied requirements"):
        _requirement(
            status=EvidenceRequirementStatus.SATISFIED,
            satisfied_evidence_ids=(),
        )

    with pytest.raises(ValueError, match="authority refs"):
        _requirement(
            status=EvidenceRequirementStatus.REQUIRES_REVIEW,
            requirement_id="requirement-review-bad",
            satisfied_evidence_ids=(),
            authority_refs=(),
        )


def test_ready_envelope_requires_no_blockers_and_authority_refs() -> None:
    envelope = _envelope()

    assert envelope.ready_for_review
    assert not envelope.blocks_claim
    assert envelope.observation_ids == ("frame-1",)
    assert envelope.requirement_ids == ("requirement-1", "requirement-review-1")
    assert envelope.review_requirement_ids == ("requirement-review-1",)
    assert envelope.required_authority_refs == ("human-authority-1",)
    assert "intent-evidence-1" in envelope.evidence_ids
    assert "observation-evidence-1" in envelope.evidence_ids
    assert "requirement-evidence-1" in envelope.evidence_ids
    assert envelope.fingerprint() == envelope.fingerprint()
    assert len(envelope.fingerprint()) == 64


def test_envelope_rejects_missing_intent_observation() -> None:
    with pytest.raises(ValueError, match="missing intent observations"):
        _envelope(
            observations=(_observation(frame_id="frame-other"),),
        )


def test_ready_envelope_rejects_blocking_requirements() -> None:
    with pytest.raises(ValueError, match="blocking requirements"):
        _envelope(
            requirements=(
                _requirement(
                    status=EvidenceRequirementStatus.MISSING,
                    satisfied_evidence_ids=(),
                ),
            ),
        )


def test_blocked_envelope_requires_blocking_evidence() -> None:
    with pytest.raises(ValueError, match="Blocked envelopes"):
        _envelope(
            readiness=ProposalReadiness.BLOCKED,
        )


def test_observed_outcome_requires_measurement_for_measured_alignment() -> None:
    outcome = _outcome()

    assert outcome.measured
    assert not outcome.changes_future_reasoning
    assert outcome.fingerprint() == outcome.fingerprint()
    assert len(outcome.fingerprint()) == 64

    with pytest.raises(ValueError, match="Measured outcomes"):
        _outcome(measured_state_ids=())

    with pytest.raises(ValueError, match="cannot have measured states"):
        _outcome(
            alignment=OutcomeAlignment.NOT_MEASURED,
            measured_state_ids=("state-policy-1",),
        )


def test_partial_or_mismatched_outcomes_require_lesson() -> None:
    partial = _outcome(
        alignment=OutcomeAlignment.PARTIAL,
        lesson="Future reasoning must check the missing condition first.",
    )

    assert partial.measured
    assert partial.changes_future_reasoning

    with pytest.raises(ValueError, match="require a lesson"):
        _outcome(alignment=OutcomeAlignment.MISMATCHED)


def test_observation_action_trace_preserves_chain_and_evidence() -> None:
    trace = build_observation_action_trace(
        trace_id="trace-1",
        envelope=_envelope(),
        outcome=_outcome(
            alignment=OutcomeAlignment.PARTIAL,
            lesson="Future proposals must test the boundary before reuse.",
        ),
        notes=("Trace is replayable for Wave 7 review.",),
    )

    assert trace.complete
    assert trace.measured
    assert not trace.blocks_claim
    assert trace.changes_future_reasoning
    assert "intent-evidence-1" in trace.evidence_ids
    assert "outcome-evidence-1" in trace.evidence_ids
    assert trace.fingerprint() == trace.fingerprint()
    assert len(trace.fingerprint()) == 64


def test_trace_blocks_claim_when_outcome_is_missing_or_unmeasured() -> None:
    missing_trace = ObservationActionTrace(
        trace_id="trace-missing-outcome",
        envelope=_envelope(),
    )
    unmeasured_trace = ObservationActionTrace(
        trace_id="trace-unmeasured-outcome",
        envelope=_envelope(),
        outcome=_outcome(
            alignment=OutcomeAlignment.NOT_MEASURED,
            measured_state_ids=(),
        ),
    )

    assert missing_trace.blocks_claim
    assert unmeasured_trace.blocks_claim


def test_trace_rejects_outcome_for_wrong_envelope() -> None:
    with pytest.raises(ValueError, match="must reference the envelope id"):
        ObservationActionTrace(
            trace_id="trace-bad-link",
            envelope=_envelope(),
            outcome=ObservedOutcome(
                outcome_id="outcome-wrong",
                envelope_id="envelope-other",
                outcome_summary="Wrong envelope.",
                evidence_ids=("outcome-evidence-1",),
                alignment=OutcomeAlignment.MATCHED,
                measured_state_ids=("state-policy-1",),
            ),
        )


def test_assess_proposal_readiness_fails_closed() -> None:
    assert (
        assess_proposal_readiness(
            observations=(),
            requirements=(),
            risk=ProposalRisk.LOW,
        )
        is ProposalReadiness.NEEDS_MORE_EVIDENCE
    )

    assert (
        assess_proposal_readiness(
            observations=(
                _observation(
                    reliability=ObservationReliability.CONTRADICTED,
                    captured_after_action_id="",
                ),
            ),
            requirements=(_requirement(),),
            risk=ProposalRisk.LOW,
        )
        is ProposalReadiness.BLOCKED
    )

    assert (
        assess_proposal_readiness(
            observations=(_observation(),),
            requirements=(
                _requirement(
                    status=EvidenceRequirementStatus.MISSING,
                    satisfied_evidence_ids=(),
                ),
            ),
            risk=ProposalRisk.LOW,
        )
        is ProposalReadiness.NEEDS_MORE_EVIDENCE
    )

    assert (
        assess_proposal_readiness(
            observations=(_observation(),),
            requirements=(_requirement(),),
            risk=ProposalRisk.HIGH,
        )
        is ProposalReadiness.READY_FOR_REVIEW
    )
