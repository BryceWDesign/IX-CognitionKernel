import pytest

from ix_cognition_kernel.wave7_body_contract import (
    ActionProposal,
    ActionProposalKind,
    BodyContractDecision,
    BodyContractDecisionStatus,
    BodySurface,
    BodySurfaceKind,
    BodySurfaceRisk,
    CapabilityGrant,
    CapabilityGrantStatus,
    ExecutionBoundary,
    ObservationChannel,
    decide_body_contract,
)


def _surface(
    *,
    risk: BodySurfaceRisk = BodySurfaceRisk.LOW,
    requires_human_review: bool = False,
    operations: tuple[str, ...] = ("simulate-trial",),
) -> BodySurface:
    return BodySurface(
        surface_id="surface-sim-1",
        kind=BodySurfaceKind.SIMULATION,
        name="Bounded simulation surface",
        description="Deterministic simulated body surface for Wave 7 trials.",
        allowed_operations=operations,
        risk=risk,
        requires_human_review=requires_human_review,
    )


def _grant(
    *,
    status: CapabilityGrantStatus = CapabilityGrantStatus.ALLOWED,
    operation: str = "simulate-trial",
    surface_id: str = "surface-sim-1",
    grant_id: str = "grant-sim-1",
    restrictions: tuple[str, ...] = (),
) -> CapabilityGrant:
    return CapabilityGrant(
        grant_id=grant_id,
        surface_id=surface_id,
        operation=operation,
        status=status,
        evidence_ids=("grant-evidence-1",),
        authority_ref="human-authority-1",
        restrictions=restrictions,
    )


def _proposal(
    *,
    operation: str = "simulate-trial",
    grant_ids: tuple[str, ...] = ("grant-sim-1",),
    surface_id: str = "surface-sim-1",
) -> ActionProposal:
    return ActionProposal(
        proposal_id="proposal-1",
        kind=ActionProposalKind.SIMULATE,
        surface_id=surface_id,
        requested_operation=operation,
        intent_summary="Run a bounded simulation trial before any real handoff.",
        predicted_outcome="Simulation will expose whether the policy holds.",
        evidence_ids=("proposal-evidence-1",),
        required_grant_ids=grant_ids,
        risk_notes=("simulation-only",),
    )


def _boundary(
    *,
    allowed: tuple[BodyContractDecisionStatus, ...] = (
        BodyContractDecisionStatus.ALLOWED_FOR_SIMULATION,
        BodyContractDecisionStatus.READY_FOR_HUMAN_REVIEW,
        BodyContractDecisionStatus.NEEDS_MORE_EVIDENCE,
    ),
    prohibited_operations: tuple[str, ...] = (),
) -> ExecutionBoundary:
    return ExecutionBoundary(
        boundary_id="boundary-1",
        surface_id="surface-sim-1",
        allowed_decision_statuses=allowed,
        prohibited_operations=prohibited_operations,
        required_authority_refs=("human-authority-1",),
        evidence_ids=("boundary-evidence-1",),
        description="Simulation boundary blocks deployment authority.",
    )


def test_body_surface_is_bounded_and_fingerprinted() -> None:
    surface = _surface()

    assert surface.supports("simulate-trial")
    assert not surface.prohibited
    assert surface.fingerprint() == surface.fingerprint()
    assert len(surface.fingerprint()) == 64


def test_body_surface_rejects_direct_live_execution() -> None:
    with pytest.raises(ValueError, match="must not allow live execution"):
        BodySurface(
            surface_id="surface-live",
            kind=BodySurfaceKind.TOOL_STAGING,
            name="Live tool",
            description="Bad live execution surface.",
            allowed_operations=("execute",),
            allows_live_execution=True,
        )


def test_prohibited_surface_requires_human_review() -> None:
    with pytest.raises(ValueError, match="Prohibited body surfaces"):
        _surface(risk=BodySurfaceRisk.PROHIBITED, requires_human_review=False)


def test_observation_channel_requires_evidence_without_ground_truth_claim() -> None:
    channel = ObservationChannel(
        channel_id="channel-1",
        surface_id="surface-sim-1",
        observable_state_ids=("state-1",),
        evidence_ids=("observation-evidence-1",),
        description="Observed simulated state only.",
    )

    assert channel.observable_state_ids == ("state-1",)
    assert channel.fingerprint() == channel.fingerprint()
    assert len(channel.fingerprint()) == 64

    with pytest.raises(ValueError, match="must not claim ground truth"):
        ObservationChannel(
            channel_id="channel-bad",
            surface_id="surface-sim-1",
            observable_state_ids=("state-1",),
            evidence_ids=("observation-evidence-1",),
            description="Bad ground truth claim.",
            claims_ground_truth=True,
        )


def test_capability_grant_status_controls_use() -> None:
    allowed = _grant()
    review = _grant(
        grant_id="grant-review-1",
        status=CapabilityGrantStatus.REVIEW_REQUIRED,
        restrictions=("human review before use",),
    )
    revoked = _grant(grant_id="grant-revoked-1", status=CapabilityGrantStatus.REVOKED)

    assert allowed.usable_without_review
    assert review.needs_review
    assert revoked.blocks_use


def test_restricted_grants_require_restrictions() -> None:
    with pytest.raises(ValueError, match="need restrictions"):
        _grant(status=CapabilityGrantStatus.RESTRICTED)


def test_action_proposal_rejects_permission_and_self_authorization() -> None:
    with pytest.raises(ValueError, match="must not self-authorize"):
        ActionProposal(
            proposal_id="proposal-self-authorized",
            kind=ActionProposalKind.STAGE_TOOL_CALL,
            surface_id="surface-sim-1",
            requested_operation="simulate-trial",
            intent_summary="Bad self authorization.",
            predicted_outcome="Bad outcome.",
            evidence_ids=("proposal-evidence-1",),
            required_grant_ids=("grant-sim-1",),
            self_authorized=True,
        )

    with pytest.raises(ValueError, match="must not claim permission"):
        ActionProposal(
            proposal_id="proposal-permission",
            kind=ActionProposalKind.STAGE_TOOL_CALL,
            surface_id="surface-sim-1",
            requested_operation="simulate-trial",
            intent_summary="Bad permission claim.",
            predicted_outcome="Bad outcome.",
            evidence_ids=("proposal-evidence-1",),
            required_grant_ids=("grant-sim-1",),
            claims_permission=True,
        )


def test_execution_boundary_blocks_blocked_decision_as_allowed_status() -> None:
    with pytest.raises(ValueError, match="must not allow blocked decisions"):
        _boundary(allowed=(BodyContractDecisionStatus.BLOCKED,))


def test_decide_body_contract_allows_simulation_only_with_allowed_grant() -> None:
    decision = decide_body_contract(
        decision_id="decision-sim-1",
        proposal=_proposal(),
        surface=_surface(),
        grants=(_grant(),),
        boundary=_boundary(),
        evidence_ids=("decision-evidence-1",),
    )

    assert decision.allowed_for_simulation
    assert not decision.ready_for_review
    assert not decision.blocked
    assert decision.required_human_authority_refs == ()
    assert "allowed-for-simulation-only" in decision.reasons
    assert "proposal-evidence-1" in decision.evidence_bundle_ids
    assert "grant-evidence-1" in decision.evidence_bundle_ids
    assert "boundary-evidence-1" in decision.evidence_bundle_ids
    assert decision.fingerprint() == decision.fingerprint()
    assert len(decision.fingerprint()) == 64


def test_decide_body_contract_routes_restricted_grant_to_review() -> None:
    decision = decide_body_contract(
        decision_id="decision-review-1",
        proposal=_proposal(),
        surface=_surface(),
        grants=(
            _grant(
                status=CapabilityGrantStatus.RESTRICTED,
                restrictions=("human review before simulation",),
            ),
        ),
        boundary=_boundary(),
        evidence_ids=("decision-evidence-1",),
    )

    assert decision.ready_for_review
    assert not decision.allowed_for_simulation
    assert "human-authority-1" in decision.required_human_authority_refs
    assert "grant-restricted:grant-sim-1" in decision.reasons


def test_decide_body_contract_blocks_unsupported_operation() -> None:
    decision = decide_body_contract(
        decision_id="decision-blocked-1",
        proposal=_proposal(operation="stage-live-message"),
        surface=_surface(),
        grants=(_grant(operation="stage-live-message"),),
        boundary=_boundary(),
        evidence_ids=("decision-evidence-1",),
    )

    assert decision.blocked
    assert decision.denied_operations == ("stage-live-message",)
    assert "surface-does-not-support-operation" in decision.reasons
    assert "blocked-fail-closed" in decision.reasons


def test_decide_body_contract_blocks_missing_required_grant() -> None:
    decision = decide_body_contract(
        decision_id="decision-missing-grant",
        proposal=_proposal(grant_ids=("grant-missing",)),
        surface=_surface(),
        grants=(_grant(),),
        boundary=_boundary(),
        evidence_ids=("decision-evidence-1",),
    )

    assert decision.blocked
    assert decision.denied_operations == ("simulate-trial",)
    assert "missing-grant:grant-missing" in decision.reasons


def test_body_contract_decision_rejects_denial_without_blocked_status() -> None:
    with pytest.raises(ValueError, match="Only blocked body decisions"):
        BodyContractDecision(
            decision_id="decision-bad-denial",
            proposal=_proposal(),
            surface=_surface(),
            grants=(_grant(),),
            boundary=_boundary(),
            status=BodyContractDecisionStatus.ALLOWED_FOR_SIMULATION,
            reasons=("bad denial",),
            required_human_authority_refs=(),
            denied_operations=("simulate-trial",),
            evidence_ids=("decision-evidence-1",),
        )


def test_body_contract_decision_requires_all_required_grants() -> None:
    with pytest.raises(ValueError, match="missing required grants"):
        BodyContractDecision(
            decision_id="decision-missing-grant",
            proposal=_proposal(grant_ids=("grant-missing",)),
            surface=_surface(),
            grants=(_grant(),),
            boundary=_boundary(),
            status=BodyContractDecisionStatus.ALLOWED_FOR_SIMULATION,
            reasons=("bad missing grant",),
            required_human_authority_refs=(),
            evidence_ids=("decision-evidence-1",),
        )
