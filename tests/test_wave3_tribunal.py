import pytest

from ix_cognition_kernel.agents import ArtifactKind
from ix_cognition_kernel.wave3_agent_artifacts import (
    RoleArtifactAuthority,
    RoleArtifactBundle,
    RoleArtifactRecord,
    RoleArtifactStatus,
    complete_role_artifact_record,
)
from ix_cognition_kernel.wave3_contracts import (
    WaveThreeArtifactKind,
    WaveThreeAuthorityState,
)
from ix_cognition_kernel.wave3_tribunal import (
    REQUIRED_TRIBUNAL_PHASES,
    TribunalDecisionRecord,
    TribunalDecisionStatus,
    TribunalPhase,
    TribunalRoleVote,
    TribunalVotePosition,
    tribunal_vote,
)

REQUIRED_ROLE_IDS = (
    "planner",
    "skeptic-red-team",
    "verifier",
    "tool-safety-officer",
    "translator-interpreter",
    "execution-liaison",
)


def role_bundle() -> RoleArtifactBundle:
    return RoleArtifactBundle(
        bundle_id="role-bundle-tribunal",
        records=tuple(
            complete_role_artifact_record(
                role_id, evidence_ids=(f"evidence:{role_id}",)
            )
            for role_id in REQUIRED_ROLE_IDS
        ),
        required_role_ids=REQUIRED_ROLE_IDS,
    )


def ready_votes() -> tuple[TribunalRoleVote, ...]:
    return (
        tribunal_vote(
            role_id="planner",
            phase=TribunalPhase.PROPOSAL,
            evidence_ids=("vote-evidence:planner",),
            rationale="Planner proposes a bounded plan graph for review.",
        ),
        tribunal_vote(
            role_id="skeptic-red-team",
            phase=TribunalPhase.CRITIQUE,
            position=TribunalVotePosition.CONCERN,
            evidence_ids=("vote-evidence:skeptic",),
            rationale="Red team records non-blocking concerns for review.",
            concerns=("Rollback evidence should stay attached to the handoff.",),
        ),
        tribunal_vote(
            role_id="verifier",
            phase=TribunalPhase.VERIFICATION,
            evidence_ids=("vote-evidence:verifier",),
            rationale="Verifier confirms evidence is sufficient for human review.",
        ),
        tribunal_vote(
            role_id="tool-safety-officer",
            phase=TribunalPhase.SAFETY,
            evidence_ids=("vote-evidence:tool-safety",),
            rationale="Tool safety confirms no execution authority is granted.",
        ),
        tribunal_vote(
            role_id="translator-interpreter",
            phase=TribunalPhase.TRANSLATION,
            evidence_ids=("vote-evidence:translator",),
            rationale="Translator keeps the tribunal decision human-readable.",
        ),
        tribunal_vote(
            role_id="execution-liaison",
            phase=TribunalPhase.HANDOFF,
            evidence_ids=("vote-evidence:execution",),
            rationale="Execution liaison packages only a reviewable handoff boundary.",
        ),
    )


def ready_decision() -> TribunalDecisionRecord:
    return TribunalDecisionRecord(
        tribunal_id="tribunal-001",
        role_artifact_bundle=role_bundle(),
        votes=ready_votes(),
        required_role_ids=REQUIRED_ROLE_IDS,
        decision_summary="Bounded tribunal record is ready for human review only.",
    )


def test_required_tribunal_phases_are_locked() -> None:
    assert REQUIRED_TRIBUNAL_PHASES == (
        TribunalPhase.PROPOSAL,
        TribunalPhase.CRITIQUE,
        TribunalPhase.VERIFICATION,
        TribunalPhase.SAFETY,
        TribunalPhase.TRANSLATION,
        TribunalPhase.HANDOFF,
    )


def test_tribunal_vote_rejects_unknown_role() -> None:
    with pytest.raises(ValueError, match="Unknown IX-CognitionKernel agent role id"):
        tribunal_vote(
            role_id="not-a-real-role",
            phase=TribunalPhase.PROPOSAL,
            evidence_ids=("evidence",),
            rationale="Invalid role should fail closed.",
        )


def test_tribunal_vote_rejects_missing_evidence() -> None:
    with pytest.raises(ValueError, match="vote evidence_id must not be empty"):
        tribunal_vote(
            role_id="planner",
            phase=TribunalPhase.PROPOSAL,
            evidence_ids=(" ",),
            rationale="Missing evidence should fail closed.",
        )


def test_blocking_and_concern_votes_require_explicit_concerns() -> None:
    with pytest.raises(ValueError, match="Blocking tribunal votes require"):
        tribunal_vote(
            role_id="skeptic-red-team",
            phase=TribunalPhase.CRITIQUE,
            position=TribunalVotePosition.BLOCK,
            evidence_ids=("vote-evidence:skeptic",),
            rationale="A block without concerns is not reviewable.",
        )

    with pytest.raises(ValueError, match="Concern tribunal votes require"):
        tribunal_vote(
            role_id="skeptic-red-team",
            phase=TribunalPhase.CRITIQUE,
            position=TribunalVotePosition.CONCERN,
            evidence_ids=("vote-evidence:skeptic",),
            rationale="A concern without details is not reviewable.",
        )


def test_tribunal_vote_links_to_role_artifact_id() -> None:
    vote = tribunal_vote(
        role_id="planner",
        phase=TribunalPhase.PROPOSAL,
        evidence_ids=("vote-evidence:planner",),
        rationale="Planner vote is linked to its role artifact.",
    )

    assert vote.artifact_ids == ("role-artifact:planner",)
    assert vote.vote_key == ("planner", "proposal", "support")
    assert vote.blocks_progress is False
    assert vote.raises_dissent is False


def test_ready_tribunal_decision_is_reviewable_not_executable() -> None:
    decision = ready_decision()

    assert decision.status is TribunalDecisionStatus.READY_FOR_HUMAN_REVIEW
    assert decision.ready_for_human_review is True
    assert decision.permits_automatic_execution is False
    assert (
        decision.human_authority_state is WaveThreeAuthorityState.HUMAN_REVIEW_REQUIRED
    )
    assert decision.missing_required_phases == ()
    assert decision.missing_required_vote_role_ids == ()
    assert decision.readiness_gaps == ()
    assert decision.blocking_gaps == ()
    assert "automatic execution is not permitted" in decision.review_summary


def test_tribunal_records_dissent_without_treating_it_as_authority() -> None:
    decision = ready_decision()

    assert decision.dissenting_role_ids == ("skeptic-red-team",)
    assert decision.blocking_role_ids == ()
    assert decision.support_role_ids == (
        "execution-liaison",
        "planner",
        "tool-safety-officer",
        "translator-interpreter",
        "verifier",
    )


def test_tribunal_blocks_when_evidence_bound_role_vote_blocks() -> None:
    votes = tuple(
        tribunal_vote(
            role_id=vote.role_id,
            phase=vote.phase,
            position=(
                TribunalVotePosition.BLOCK
                if vote.role_id == "skeptic-red-team"
                else vote.position
            ),
            evidence_ids=vote.evidence_ids,
            rationale=vote.rationale,
            concerns=(
                ("Plan graph omits a rollback condition.",)
                if vote.role_id == "skeptic-red-team"
                else vote.concerns
            ),
        )
        for vote in ready_votes()
    )
    decision = TribunalDecisionRecord(
        tribunal_id="tribunal-001",
        role_artifact_bundle=role_bundle(),
        votes=votes,
        required_role_ids=REQUIRED_ROLE_IDS,
    )

    assert decision.status is TribunalDecisionStatus.BLOCKED
    assert decision.ready_for_human_review is False
    assert decision.human_authority_state is WaveThreeAuthorityState.BLOCKED
    assert decision.blocking_role_ids == ("skeptic-red-team",)
    assert "blocking role votes: skeptic-red-team" in decision.blocking_gaps


def test_tribunal_needs_evidence_when_required_phase_is_missing() -> None:
    votes = tuple(
        vote for vote in ready_votes() if vote.phase is not TribunalPhase.HANDOFF
    )
    decision = TribunalDecisionRecord(
        tribunal_id="tribunal-001",
        role_artifact_bundle=role_bundle(),
        votes=votes,
        required_role_ids=REQUIRED_ROLE_IDS,
    )

    assert decision.status is TribunalDecisionStatus.NEEDS_EVIDENCE
    assert decision.ready_for_human_review is False
    assert decision.missing_required_phases == (TribunalPhase.HANDOFF,)
    assert "missing required tribunal phases: handoff" in decision.readiness_gaps


def test_tribunal_needs_evidence_when_required_role_vote_is_missing() -> None:
    votes = tuple(vote for vote in ready_votes() if vote.role_id != "execution-liaison")
    decision = TribunalDecisionRecord(
        tribunal_id="tribunal-001",
        role_artifact_bundle=role_bundle(),
        votes=votes,
        required_role_ids=REQUIRED_ROLE_IDS,
    )

    assert decision.status is TribunalDecisionStatus.NEEDS_EVIDENCE
    assert decision.missing_required_vote_role_ids == ("execution-liaison",)
    assert "missing required role votes: execution-liaison" in decision.readiness_gaps


def test_tribunal_rejects_required_role_not_in_role_artifact_bundle() -> None:
    with pytest.raises(ValueError, match="must be represented by role artifacts"):
        TribunalDecisionRecord(
            tribunal_id="tribunal-001",
            role_artifact_bundle=role_bundle(),
            votes=ready_votes(),
            required_role_ids=REQUIRED_ROLE_IDS + ("reward-auditor",),
        )


def test_tribunal_rejects_vote_from_non_required_role() -> None:
    with pytest.raises(ValueError, match="non-required role"):
        TribunalDecisionRecord(
            tribunal_id="tribunal-001",
            role_artifact_bundle=role_bundle(),
            votes=ready_votes()
            + (
                tribunal_vote(
                    role_id="reward-auditor",
                    phase=TribunalPhase.CRITIQUE,
                    evidence_ids=("vote-evidence:reward",),
                    rationale="This role is outside the required tribunal scope.",
                ),
            ),
            required_role_ids=REQUIRED_ROLE_IDS,
        )


def test_tribunal_rejects_vote_that_references_missing_role_artifact() -> None:
    bad_vote = TribunalRoleVote(
        role_id="planner",
        phase=TribunalPhase.PROPOSAL,
        position=TribunalVotePosition.SUPPORT,
        artifact_ids=("role-artifact:not-in-bundle",),
        evidence_ids=("vote-evidence:planner",),
        rationale="Vote points at a missing artifact.",
    )

    with pytest.raises(ValueError, match="references missing role artifact"):
        TribunalDecisionRecord(
            tribunal_id="tribunal-001",
            role_artifact_bundle=role_bundle(),
            votes=(bad_vote,),
            required_role_ids=("planner",),
            required_phases=(TribunalPhase.PROPOSAL,),
        )


def test_tribunal_rejects_duplicate_role_phase_position_votes() -> None:
    duplicate = ready_votes()[0]

    with pytest.raises(ValueError, match="Duplicate tribunal vote"):
        TribunalDecisionRecord(
            tribunal_id="tribunal-001",
            role_artifact_bundle=role_bundle(),
            votes=ready_votes() + (duplicate,),
            required_role_ids=REQUIRED_ROLE_IDS,
        )


def test_blocked_role_artifact_blocks_tribunal_even_without_block_vote() -> None:
    blocked_record = RoleArtifactRecord(
        role_id="planner",
        produced_output_artifacts=(ArtifactKind.PLAN_GRAPH,),
        consumed_input_artifacts=(
            ArtifactKind.MISSION_BOUNDARY,
            ArtifactKind.WORLD_MODEL,
        ),
        evidence_ids=("evidence:planner",),
        rationale="Planner artifact is blocked by missing rollback proof.",
        status=RoleArtifactStatus.BLOCKED,
        authority=RoleArtifactAuthority.BLOCKED,
        paired_engine_ids=("plan-graph",),
        blocking_reasons=("Missing rollback proof.",),
    )
    records = (blocked_record,) + tuple(
        complete_role_artifact_record(role_id, evidence_ids=(f"evidence:{role_id}",))
        for role_id in REQUIRED_ROLE_IDS
        if role_id != "planner"
    )
    decision = TribunalDecisionRecord(
        tribunal_id="tribunal-001",
        role_artifact_bundle=RoleArtifactBundle(
            bundle_id="role-bundle-blocked",
            records=records,
            required_role_ids=REQUIRED_ROLE_IDS,
        ),
        votes=ready_votes(),
        required_role_ids=REQUIRED_ROLE_IDS,
    )

    assert decision.status is TribunalDecisionStatus.BLOCKED
    assert "blocked role artifacts: planner" in decision.blocking_gaps


def test_tribunal_converts_to_shared_artifact_bundle() -> None:
    decision = ready_decision()
    artifact_bundle = decision.to_artifact_bundle(
        artifact_bundle_id="tribunal-artifacts"
    )

    assert artifact_bundle.has_required_kind_coverage is True
    assert artifact_bundle.artifact_ids == ("tribunal-record:tribunal-001",)
    assert artifact_bundle.ready_for_human_review_artifact_ids == (
        "tribunal-record:tribunal-001",
    )
    assert artifact_bundle.artifact_by_id("tribunal-record:tribunal-001").kind is (
        WaveThreeArtifactKind.TRIBUNAL_RECORD
    )


def test_tribunal_fingerprint_is_deterministic() -> None:
    first = ready_decision().fingerprint()
    second = ready_decision().fingerprint()

    assert first == second
    assert len(first) == 64
