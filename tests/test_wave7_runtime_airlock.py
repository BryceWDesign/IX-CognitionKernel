import pytest

from ix_cognition_kernel.wave7_runtime_airlock import (
    AirlockAuthorityRequirement,
    AirlockDecisionStatus,
    AirlockFinding,
    AirlockFindingSeverity,
    AirlockReport,
    AirlockRequestKind,
    RuntimeAirlockDecision,
    RuntimeAirlockRequest,
    build_airlock_report,
    evaluate_runtime_airlock,
)


def _request(
    *,
    kind: AirlockRequestKind = AirlockRequestKind.SIMULATION,
    upstream_decision_ids: tuple[str, ...] = (),
    required_authority_refs: tuple[str, ...] = (),
    requests_deployment: bool = False,
) -> RuntimeAirlockRequest:
    return RuntimeAirlockRequest(
        request_id="airlock-request-1",
        kind=kind,
        subject_id="candidate-lifecycle-1",
        surface_id="surface-sim-1",
        proposed_operation="simulate-trial",
        intent_summary="Move only a bounded simulation request through airlock.",
        evidence_ids=("request-evidence-1",),
        upstream_decision_ids=upstream_decision_ids,
        required_authority_refs=required_authority_refs,
        requests_deployment=requests_deployment,
    )


def test_runtime_airlock_request_rejects_self_authorization() -> None:
    with pytest.raises(ValueError, match="must not self-authorize"):
        RuntimeAirlockRequest(
            request_id="request-self-authorized",
            kind=AirlockRequestKind.SIMULATION,
            subject_id="candidate-lifecycle-1",
            surface_id="surface-sim-1",
            proposed_operation="simulate-trial",
            intent_summary="Bad self authorization.",
            evidence_ids=("request-evidence-1",),
            upstream_decision_ids=(),
            required_authority_refs=(),
            self_authorized=True,
        )


def test_runtime_airlock_request_rejects_permission_claim() -> None:
    with pytest.raises(ValueError, match="must not claim permission"):
        RuntimeAirlockRequest(
            request_id="request-permission",
            kind=AirlockRequestKind.SIMULATION,
            subject_id="candidate-lifecycle-1",
            surface_id="surface-sim-1",
            proposed_operation="simulate-trial",
            intent_summary="Bad permission claim.",
            evidence_ids=("request-evidence-1",),
            upstream_decision_ids=(),
            required_authority_refs=(),
            claims_permission=True,
        )


def test_non_simulation_request_requires_upstream_decision() -> None:
    with pytest.raises(ValueError, match="need upstream decisions"):
        _request(kind=AirlockRequestKind.BODY_HANDOFF)


def test_deployment_request_requires_authority_refs() -> None:
    with pytest.raises(ValueError, match="require authority refs"):
        _request(requests_deployment=True)


def test_airlock_finding_fail_closed_rules() -> None:
    info = AirlockFinding(
        finding_id="info-1",
        severity=AirlockFindingSeverity.INFO,
        summary="Informational finding.",
        evidence_ids=("finding-evidence-1",),
    )

    assert not info.blocks_handoff
    assert not info.requires_human_review
    assert info.fingerprint() == info.fingerprint()
    assert len(info.fingerprint()) == 64

    with pytest.raises(ValueError, match="must block handoff"):
        AirlockFinding(
            finding_id="blocking-bad",
            severity=AirlockFindingSeverity.BLOCKING,
            summary="Bad blocking finding.",
            evidence_ids=("finding-evidence-1",),
            blocks_handoff=False,
        )

    with pytest.raises(ValueError, match="must require human review"):
        AirlockFinding(
            finding_id="review-bad",
            severity=AirlockFindingSeverity.REVIEW_REQUIRED,
            summary="Bad review finding.",
            evidence_ids=("finding-evidence-1",),
            requires_human_review=False,
        )


def test_authority_requirement_tracks_review_satisfaction() -> None:
    requirement = AirlockAuthorityRequirement(
        requirement_id="authority-1",
        authority_ref="human-authority-1",
        reason="Human review required.",
        evidence_ids=("authority-evidence-1",),
    )
    satisfied = AirlockAuthorityRequirement(
        requirement_id="authority-2",
        authority_ref="human-authority-1",
        reason="Human review required.",
        evidence_ids=("authority-evidence-1",),
        satisfied_by_review_ref="human-authority-1",
    )

    assert not requirement.satisfied
    assert satisfied.satisfied
    assert requirement.fingerprint() == requirement.fingerprint()
    assert len(requirement.fingerprint()) == 64


def test_evaluate_airlock_allows_simulation_only_when_evidence_is_present() -> None:
    decision = evaluate_runtime_airlock(
        decision_id="airlock-decision-1",
        request=_request(),
        supplied_evidence_ids=("request-evidence-1",),
        notes=("Simulation-only request remains bounded.",),
    )

    assert decision.allowed_for_simulation
    assert not decision.ready_for_review
    assert not decision.needs_more_evidence
    assert not decision.blocks_handoff
    assert decision.finding_ids == ("simulation-only-boundary",)
    assert decision.unsatisfied_authority_refs == ()
    assert "request-evidence-1" in decision.evidence_bundle_ids
    assert decision.fingerprint() == decision.fingerprint()
    assert len(decision.fingerprint()) == 64


def test_evaluate_airlock_needs_more_evidence_when_request_evidence_missing() -> None:
    decision = evaluate_runtime_airlock(
        decision_id="airlock-decision-missing",
        request=_request(),
        supplied_evidence_ids=("other-evidence",),
    )

    assert decision.needs_more_evidence
    assert not decision.allowed_for_simulation
    assert decision.missing_evidence_finding_ids == ("missing-request-evidence",)
    assert "missing-request-evidence" in decision.finding_ids


def test_evaluate_airlock_routes_body_handoff_to_human_review() -> None:
    decision = evaluate_runtime_airlock(
        decision_id="airlock-decision-review",
        request=_request(
            kind=AirlockRequestKind.BODY_HANDOFF,
            upstream_decision_ids=("body-decision-1",),
            required_authority_refs=("human-authority-1",),
        ),
        supplied_evidence_ids=("request-evidence-1",),
    )

    assert decision.ready_for_review
    assert not decision.allowed_for_simulation
    assert decision.review_finding_ids == ("human-review-required",)
    assert decision.unsatisfied_authority_refs == ("human-authority-1",)
    assert decision.authority_requirement_ids == ("authority-1",)


def test_evaluate_airlock_blocks_deployment_requests() -> None:
    decision = evaluate_runtime_airlock(
        decision_id="airlock-decision-deploy",
        request=_request(
            kind=AirlockRequestKind.TOOL_STAGING,
            upstream_decision_ids=("tool-decision-1",),
            required_authority_refs=("human-authority-1",),
            requests_deployment=True,
        ),
        supplied_evidence_ids=("request-evidence-1",),
        satisfied_authority_refs=("human-authority-1",),
    )

    assert decision.blocks_handoff
    assert not decision.ready_for_review
    assert "deployment-requested" in decision.blocking_finding_ids
    assert decision.unsatisfied_authority_refs == ()


def test_runtime_airlock_decision_rejects_simulation_with_authority_requirement() -> None:
    request = _request()
    requirement = AirlockAuthorityRequirement(
        requirement_id="authority-1",
        authority_ref="human-authority-1",
        reason="Authority should not be required for simulation-allowed state.",
        evidence_ids=("authority-evidence-1",),
    )

    with pytest.raises(ValueError, match="cannot require authority"):
        RuntimeAirlockDecision(
            decision_id="airlock-decision-bad-authority",
            request=request,
            status=AirlockDecisionStatus.ALLOWED_FOR_SIMULATION,
            findings=(
                AirlockFinding(
                    finding_id="info-1",
                    severity=AirlockFindingSeverity.INFO,
                    summary="Info only.",
                    evidence_ids=("finding-evidence-1",),
                ),
            ),
            authority_requirements=(requirement,),
            evidence_ids=("request-evidence-1",),
        )


def test_runtime_airlock_decision_rejects_blocked_without_blocker() -> None:
    with pytest.raises(ValueError, match="require blockers"):
        RuntimeAirlockDecision(
            decision_id="airlock-decision-bad-blocked",
            request=_request(),
            status=AirlockDecisionStatus.BLOCKED,
            findings=(
                AirlockFinding(
                    finding_id="info-1",
                    severity=AirlockFindingSeverity.INFO,
                    summary="Info only.",
                    evidence_ids=("finding-evidence-1",),
                ),
            ),
            authority_requirements=(),
            evidence_ids=("request-evidence-1",),
        )


def test_airlock_report_preserves_all_decision_classes() -> None:
    simulation = evaluate_runtime_airlock(
        decision_id="decision-simulation",
        request=_request(),
        supplied_evidence_ids=("request-evidence-1",),
    )
    review = evaluate_runtime_airlock(
        decision_id="decision-review",
        request=_request(
            kind=AirlockRequestKind.BODY_HANDOFF,
            upstream_decision_ids=("body-decision-1",),
            required_authority_refs=("human-authority-1",),
        ),
        supplied_evidence_ids=("request-evidence-1",),
    )
    missing = evaluate_runtime_airlock(
        decision_id="decision-missing",
        request=_request(),
        supplied_evidence_ids=("other-evidence",),
    )
    blocked = evaluate_runtime_airlock(
        decision_id="decision-blocked",
        request=_request(
            kind=AirlockRequestKind.TOOL_STAGING,
            upstream_decision_ids=("tool-decision-1",),
            required_authority_refs=("human-authority-1",),
            requests_deployment=True,
        ),
        supplied_evidence_ids=("request-evidence-1",),
    )
    report = build_airlock_report(
        report_id="airlock-report-1",
        decisions=(simulation, review, missing, blocked),
        notes=("Runtime airlock decisions remain replayable.",),
    )

    assert report.decision_ids == (
        "decision-blocked",
        "decision-missing",
        "decision-review",
        "decision-simulation",
    )
    assert report.simulation_allowed_decision_ids == ("decision-simulation",)
    assert report.review_ready_decision_ids == ("decision-review",)
    assert report.more_evidence_decision_ids == ("decision-missing",)
    assert report.blocked_decision_ids == ("decision-blocked",)
    assert report.blocks_claim
    assert "request-evidence-1" in report.evidence_ids
    assert report.fingerprint() == report.fingerprint()
    assert len(report.fingerprint()) == 64


def test_airlock_report_requires_decisions() -> None:
    with pytest.raises(ValueError, match="require decisions"):
        AirlockReport(report_id="airlock-report-empty", decisions=())
