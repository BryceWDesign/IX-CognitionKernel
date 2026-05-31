import pytest

from ix_cognition_kernel.agents import (
    AGENT_ROLES,
    AgentTier,
    ArtifactKind,
    agent_by_id,
    agent_ids,
    agent_names,
    agents_by_tier,
    required_output_artifacts,
    roles_paired_with_engine,
)


def test_agent_registry_has_locked_count_and_order() -> None:
    assert len(AGENT_ROLES) == 25
    assert agent_ids() == (
        "mission-governor",
        "belief-curator",
        "unknowns-hunter",
        "world-modeler",
        "planner",
        "skeptic-red-team",
        "verifier",
        "execution-liaison",
        "learning-archivist",
        "translator-interpreter",
        "reward-auditor",
        "tool-safety-officer",
        "domain-specialist-router",
        "software-engineering-specialist",
        "security-threat-specialist",
        "science-physics-specialist",
        "math-formal-methods-specialist",
        "data-provenance-specialist",
        "memory-integrity-specialist",
        "simulation-worldtwin-critic",
        "human-factors-ux-specialist",
        "legal-licensing-compliance-specialist",
        "cost-budget-resource-controller",
        "recovery-rollback-planner",
        "adversarial-prompt-deception-monitor",
    )


def test_agent_names_preserve_the_bounded_council() -> None:
    assert agent_names()[:9] == (
        "Mission Governor",
        "Belief Curator",
        "Unknowns Hunter",
        "World Modeler",
        "Planner",
        "Skeptic / Red Team",
        "Verifier",
        "Execution Liaison",
        "Learning Archivist",
    )
    assert "Adversarial Prompt / Deception Monitor" in agent_names()


def test_agent_tiers_are_locked_to_nine_four_twelve() -> None:
    assert len(agents_by_tier(AgentTier.CORE)) == 9
    assert len(agents_by_tier(AgentTier.GOVERNANCE)) == 4
    assert len(agents_by_tier(AgentTier.SPECIALIST)) == 12


def test_mission_governor_preserves_no_agi_overclaim_and_authority() -> None:
    role = agent_by_id("mission-governor")

    assert role.tier is AgentTier.CORE
    assert "no-AGI-overclaim" in role.mission
    assert ArtifactKind.MISSION_BOUNDARY in role.required_outputs
    assert "non-attached-purpose" in role.paired_engines
    assert any("may not execute tools" in limit for limit in role.authority_limits)


def test_belief_and_unknowns_roles_produce_epistemic_artifacts() -> None:
    belief = agent_by_id("belief-curator")
    unknowns = agent_by_id("unknowns-hunter")

    assert belief.required_outputs == (ArtifactKind.BELIEF_RECORD,)
    assert unknowns.required_outputs == (ArtifactKind.UNCERTAINTY_LEDGER,)
    assert "belief" in belief.paired_engines
    assert "uncertainty" in unknowns.paired_engines


def test_execution_liaison_cannot_execute_or_self_approve() -> None:
    role = agent_by_id("execution-liaison")

    assert role.required_outputs == (ArtifactKind.HANDOFF_PACKAGE,)
    assert "blackfox-handoff" in role.paired_engines
    assert any("may not execute" in limit for limit in role.authority_limits)
    assert any("approve model output" in limit for limit in role.authority_limits)


def test_reward_auditor_blocks_specification_gaming() -> None:
    role = agent_by_id("reward-auditor")

    assert role.tier is AgentTier.GOVERNANCE
    assert "specification gaming" in role.mission
    assert ArtifactKind.REWARD_AUDIT in role.required_outputs
    assert "reward-auditor" in role.paired_engines


def test_specialist_router_does_not_allow_bypass_of_core_review() -> None:
    role = agent_by_id("domain-specialist-router")

    assert role.tier is AgentTier.GOVERNANCE
    assert ArtifactKind.SPECIALIST_ROUTING_DECISION in role.required_outputs
    assert any("bypass core review" in limit for limit in role.authority_limits)


def test_security_specialist_is_safety_bounded_not_offensive() -> None:
    role = agent_by_id("security-threat-specialist")

    assert role.tier is AgentTier.SPECIALIST
    assert ArtifactKind.THREAT_MODEL in role.required_outputs
    assert any("may not provide offensive" in limit for limit in role.authority_limits)


def test_memory_integrity_specialist_binds_learning_to_quarantine() -> None:
    role = agent_by_id("memory-integrity-specialist")

    assert ArtifactKind.MEMORY_INTEGRITY_DECISION in role.required_outputs
    assert "memory-quarantine" in role.paired_engines
    assert "skill-genome" in role.paired_engines
    assert any("unvalidated memory" in limit for limit in role.authority_limits)


def test_adversarial_monitor_requires_evidence_before_deception_claims() -> None:
    role = agent_by_id("adversarial-prompt-deception-monitor")

    assert ArtifactKind.DECEPTION_MONITOR_REPORT in role.required_outputs
    assert "alignment-faking risk" in role.mission
    assert any("without evidence" in limit for limit in role.authority_limits)


def test_roles_paired_with_engine_returns_expected_agents() -> None:
    blackfox_roles = roles_paired_with_engine("blackfox-handoff")
    tribunal_roles = roles_paired_with_engine("multi-agent-tribunal")

    assert "execution-liaison" in tuple(role.role_id for role in blackfox_roles)
    assert "recovery-rollback-planner" in tuple(role.role_id for role in blackfox_roles)
    assert "translator-interpreter" in tuple(role.role_id for role in tribunal_roles)
    assert "adversarial-prompt-deception-monitor" in tuple(
        role.role_id for role in tribunal_roles
    )


def test_unknown_agent_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown IX-CognitionKernel agent role id"):
        agent_by_id("unbounded-agent-swarm")


def test_every_agent_has_artifacts_limits_and_engine_pairing() -> None:
    for role in AGENT_ROLES:
        assert role.required_outputs
        assert role.authority_limits
        assert role.paired_engines
        assert "may not" in " ".join(role.authority_limits).lower()


def test_required_output_artifacts_cover_all_twenty_five_roles() -> None:
    artifacts = required_output_artifacts()

    assert len(artifacts) == 25
    assert ArtifactKind.MISSION_BOUNDARY in artifacts
    assert ArtifactKind.HANDOFF_PACKAGE in artifacts
    assert ArtifactKind.DECEPTION_MONITOR_REPORT in artifacts
