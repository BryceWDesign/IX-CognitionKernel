import pytest

from ix_cognition_kernel.wave7_capability_surface import (
    CapabilityRestriction,
    CapabilityRestrictionKind,
    CapabilityRisk,
    CapabilityScope,
    CapabilityStatus,
    CapabilitySurface,
    CapabilityUseDecision,
    CapabilityUseDecisionStatus,
    CapabilityUseRequest,
    build_capability_surface_report,
    decide_capability_use,
)


def _scope(
    *,
    scope_id: str = "scope-sim-1",
    operations: tuple[str, ...] = ("simulate-trial",),
    surface_ids: tuple[str, ...] = ("surface-sim-1",),
) -> CapabilityScope:
    return CapabilityScope(
        scope_id=scope_id,
        domain="bounded simulation",
        operations=operations,
        surface_ids=surface_ids,
        evidence_ids=("scope-evidence-1",),
        authority_refs=("human-authority-1",),
    )


def _restriction(
    *,
    restriction_id: str = "restriction-review-1",
    kind: CapabilityRestrictionKind = (
        CapabilityRestrictionKind.HUMAN_REVIEW_REQUIRED
    ),
    blocks_use: bool = False,
) -> CapabilityRestriction:
    return CapabilityRestriction(
        restriction_id=restriction_id,
        kind=kind,
        summary="Human review is required before this capability is used.",
        affected_operations=("simulate-trial",),
        affected_surface_ids=("surface-sim-1",),
        evidence_ids=("restriction-evidence-1",),
        authority_refs=("human-authority-1",),
        blocks_use=blocks_use,
    )


def _capability(
    *,
    status: CapabilityStatus = CapabilityStatus.ALLOWED,
    risk: CapabilityRisk = CapabilityRisk.LOW,
    restrictions: tuple[CapabilityRestriction, ...] = (),
    confidence: float = 0.8,
    stale_reason: str = "",
    revoked_reason: str = "",
) -> CapabilitySurface:
    return CapabilitySurface(
        capability_id="capability-sim-1",
        name="Bounded simulation capability",
        description="Measured capability for deterministic simulation trials.",
        status=status,
        risk=risk,
        scopes=(_scope(),),
        restrictions=restrictions,
        evidence_ids=("capability-evidence-1",),
        confidence=confidence,
        stale_reason=stale_reason,
        revoked_reason=revoked_reason,
    )


def _request(
    *,
    operation: str = "simulate-trial",
    surface_id: str = "surface-sim-1",
    capability_id: str = "capability-sim-1",
) -> CapabilityUseRequest:
    return CapabilityUseRequest(
        request_id="request-1",
        capability_id=capability_id,
        operation=operation,
        surface_id=surface_id,
        purpose="Use capability only for a bounded Wave 7 simulation trial.",
        evidence_ids=("request-evidence-1",),
    )


def test_capability_scope_requires_evidence_and_authority() -> None:
    scope = _scope()

    assert scope.supports(operation="simulate-trial", surface_id="surface-sim-1")
    assert not scope.supports(operation="deploy", surface_id="surface-sim-1")
    assert scope.fingerprint() == scope.fingerprint()
    assert len(scope.fingerprint()) == 64

    with pytest.raises(ValueError, match="require authority refs"):
        CapabilityScope(
            scope_id="scope-no-authority",
            domain="bounded simulation",
            operations=("simulate-trial",),
            surface_ids=("surface-sim-1",),
            evidence_ids=("scope-evidence-1",),
            authority_refs=(),
        )


def test_capability_restriction_can_block_revoked_operation() -> None:
    restriction = _restriction(
        kind=CapabilityRestrictionKind.REVOKED_OPERATION,
        blocks_use=True,
    )

    assert restriction.applies_to(
        operation="simulate-trial",
        surface_id="surface-sim-1",
    )
    assert restriction.blocks_use
    assert restriction.fingerprint() == restriction.fingerprint()

    with pytest.raises(ValueError, match="must block use"):
        _restriction(kind=CapabilityRestrictionKind.REVOKED_OPERATION)


def test_capability_surface_is_measured_but_not_authorization() -> None:
    capability = _capability()

    assert capability.supports(
        operation="simulate-trial",
        surface_id="surface-sim-1",
    )
    assert capability.status is CapabilityStatus.ALLOWED
    assert not capability.needs_review
    assert not capability.needs_more_evidence
    assert not capability.blocks_use
    assert "capability-evidence-1" in capability.evidence_bundle_ids
    assert "scope-evidence-1" in capability.evidence_bundle_ids
    assert capability.fingerprint() == capability.fingerprint()
    assert len(capability.fingerprint()) == 64

    with pytest.raises(ValueError, match="must not claim authorization"):
        CapabilitySurface(
            capability_id="capability-bad-auth",
            name="Bad authorization claim",
            description="Bad surface.",
            status=CapabilityStatus.ALLOWED,
            risk=CapabilityRisk.LOW,
            scopes=(_scope(),),
            restrictions=(),
            evidence_ids=("capability-evidence-1",),
            confidence=0.8,
            claims_authorization=True,
        )


def test_unproven_and_revoked_capabilities_require_zero_confidence() -> None:
    unproven = _capability(status=CapabilityStatus.UNPROVEN, confidence=0.0)
    revoked = _capability(
        status=CapabilityStatus.REVOKED,
        confidence=0.0,
        revoked_reason="Evidence was invalidated by later review.",
    )

    assert unproven.needs_more_evidence
    assert revoked.blocks_use

    with pytest.raises(ValueError, match="Unproven capabilities"):
        _capability(status=CapabilityStatus.UNPROVEN, confidence=0.1)

    with pytest.raises(ValueError, match="Revoked capabilities"):
        _capability(
            status=CapabilityStatus.REVOKED,
            confidence=0.1,
            revoked_reason="Bad confidence.",
        )


def test_stale_capabilities_require_reason() -> None:
    stale = _capability(
        status=CapabilityStatus.STALE,
        confidence=0.4,
        stale_reason="Evidence is older than the current trial boundary.",
    )

    assert stale.needs_more_evidence
    assert not stale.blocks_use

    with pytest.raises(ValueError, match="Stale capabilities"):
        _capability(status=CapabilityStatus.STALE, confidence=0.4)


def test_capability_use_request_rejects_permission_claim() -> None:
    with pytest.raises(ValueError, match="must not claim permission"):
        CapabilityUseRequest(
            request_id="request-permission",
            capability_id="capability-sim-1",
            operation="simulate-trial",
            surface_id="surface-sim-1",
            purpose="Bad permission claim.",
            evidence_ids=("request-evidence-1",),
            claims_permission=True,
        )


def test_decide_capability_use_allows_simulation_only() -> None:
    decision = decide_capability_use(
        decision_id="decision-1",
        request=_request(),
        capability=_capability(),
        evidence_ids=("decision-evidence-1",),
    )

    assert decision.allowed_for_simulation
    assert not decision.ready_for_review
    assert not decision.needs_more_evidence
    assert not decision.blocked
    assert decision.required_authority_refs == ()
    assert decision.matched_restriction_ids == ()
    assert "capability-allowed-for-simulation-only" in decision.reasons
    assert "request-evidence-1" in decision.evidence_bundle_ids
    assert "capability-evidence-1" in decision.evidence_bundle_ids
    assert "scope-evidence-1" in decision.evidence_bundle_ids
    assert decision.fingerprint() == decision.fingerprint()
    assert len(decision.fingerprint()) == 64


def test_decide_capability_use_routes_restricted_capability_to_review() -> None:
    decision = decide_capability_use(
        decision_id="decision-review",
        request=_request(),
        capability=_capability(
            status=CapabilityStatus.RESTRICTED,
            risk=CapabilityRisk.HIGH,
            restrictions=(_restriction(),),
        ),
        evidence_ids=("decision-evidence-1",),
    )

    assert decision.ready_for_review
    assert not decision.allowed_for_simulation
    assert "human-authority-1" in decision.required_authority_refs
    assert decision.matched_restriction_ids == ("restriction-review-1",)
    assert "capability-human-review-required" in decision.reasons


def test_decide_capability_use_needs_more_evidence_for_stale() -> None:
    decision = decide_capability_use(
        decision_id="decision-stale",
        request=_request(),
        capability=_capability(
            status=CapabilityStatus.STALE,
            confidence=0.4,
            stale_reason="Evidence needs refresh before reuse.",
        ),
        evidence_ids=("decision-evidence-1",),
    )

    assert decision.needs_more_evidence
    assert not decision.allowed_for_simulation
    assert "human-authority-1" in decision.required_authority_refs
    assert "capability-needs-more-evidence" in decision.reasons


def test_decide_capability_use_blocks_unsupported_scope() -> None:
    decision = decide_capability_use(
        decision_id="decision-blocked",
        request=_request(operation="deploy-live-tool"),
        capability=_capability(),
        evidence_ids=("decision-evidence-1",),
    )

    assert decision.blocked
    assert "capability-scope-does-not-support-use" in decision.reasons
    assert "human-authority-1" in decision.required_authority_refs


def test_decide_capability_use_blocks_revoked_restriction() -> None:
    decision = decide_capability_use(
        decision_id="decision-revoked-restriction",
        request=_request(),
        capability=_capability(
            restrictions=(
                _restriction(
                    kind=CapabilityRestrictionKind.REVOKED_OPERATION,
                    blocks_use=True,
                ),
            ),
        ),
        evidence_ids=("decision-evidence-1",),
    )

    assert decision.blocked
    assert decision.matched_restriction_ids == ("restriction-review-1",)
    assert "capability-use-blocked" in decision.reasons


def test_capability_use_decision_rejects_authority_on_simulation_status() -> None:
    with pytest.raises(ValueError, match="cannot require authority"):
        CapabilityUseDecision(
            decision_id="decision-bad-authority",
            request=_request(),
            capability=_capability(),
            status=CapabilityUseDecisionStatus.ALLOWED_FOR_SIMULATION,
            reasons=("bad authority",),
            required_authority_refs=("human-authority-1",),
            evidence_ids=("decision-evidence-1",),
        )


def test_capability_surface_report_preserves_blockers() -> None:
    blocked_capability = _capability(
        status=CapabilityStatus.REVOKED,
        confidence=0.0,
        revoked_reason="Capability failed later validation.",
    )
    blocked_decision = decide_capability_use(
        decision_id="decision-blocked",
        request=_request(),
        capability=blocked_capability,
        evidence_ids=("decision-evidence-1",),
    )
    report = build_capability_surface_report(
        report_id="capability-report-1",
        capabilities=(blocked_capability,),
        decisions=(blocked_decision,),
        notes=("Revoked capability remains visible.",),
    )

    assert report.capability_ids == ("capability-sim-1",)
    assert report.blocked_capability_ids == ("capability-sim-1",)
    assert report.blocked_decision_ids == ("decision-blocked",)
    assert report.blocks_claim
    assert "capability-evidence-1" in report.evidence_ids
    assert "decision-evidence-1" in report.evidence_ids
    assert report.fingerprint() == report.fingerprint()
    assert len(report.fingerprint()) == 64
