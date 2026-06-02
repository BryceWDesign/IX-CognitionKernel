from ix_cognition_kernel.evaluation import (
    AcceptanceCriterion,
    EvaluationLedger,
    EvaluationRecord,
    EvaluationStatus,
)
from ix_cognition_kernel.memory import (
    MemoryCandidate,
    MemoryCandidateKind,
    MemoryQuarantineLedger,
    MemoryValidationRecord,
    MemoryValidationStatus,
)
from ix_cognition_kernel.outcome import (
    OutcomeLearningLedger,
    OutcomeLearningRecord,
    OutcomeLearningStatus,
    OutcomePressure,
)
from ix_cognition_kernel.skills import (
    SkillCandidate,
    SkillCandidateKind,
    SkillReuseEvidenceRecord,
    evaluate_skill_candidates,
)
from ix_cognition_kernel.wave3_agent_artifacts import (
    RoleArtifactBundle,
    complete_role_artifact_record,
)
from ix_cognition_kernel.wave3_assurance import (
    REQUIRED_ASSURANCE_CLAIM_KINDS,
    AssuranceRecord,
    AssuranceRecordBundle,
    supported_assurance_claim,
)
from ix_cognition_kernel.wave3_blackfox_handoff import (
    REQUIRED_BLACKFOX_BOUNDARY_KINDS,
    REQUIRED_BLACKFOX_REVIEW_REQUIREMENT_KINDS,
    BlackFoxExecutionBoundary,
    BlackFoxHandoffBundle,
    BlackFoxHandoffPackage,
    BlackFoxReviewRequirement,
    BlackFoxRollbackReference,
)
from ix_cognition_kernel.wave3_contracts import WaveThreeArtifactKind
from ix_cognition_kernel.wave3_coordinator import (
    WaveThreeCoordinationResult,
    coordinate_wave_three_engines,
)
from ix_cognition_kernel.wave3_curriculum import (
    CurriculumTaskBundle,
    CurriculumTaskKind,
    measured_curriculum_task,
    passing_curriculum_measurement,
)
from ix_cognition_kernel.wave3_discovery import (
    DiscoveryCandidate,
    DiscoveryCandidateKind,
    DiscoveryRecord,
    DiscoveryRecordBundle,
    DiscoveryUpdateTarget,
)
from ix_cognition_kernel.wave3_engine_coordination import (
    EngineCoordinationBundle,
    complete_engine_coordination_record,
)
from ix_cognition_kernel.wave3_memory_integration import (
    DEFAULT_MEMORY_ROLE_REVIEW_SCOPE,
    MemoryRoleDecisionBundle,
    MemoryRoleDecisionRecord,
)
from ix_cognition_kernel.wave3_reward_audit import (
    RewardAuditRecord,
    clean_reward_audit_record,
)
from ix_cognition_kernel.wave3_skill_governance import (
    DEFAULT_SKILL_GENOME_REVIEW_SCOPE,
    SkillGenomeUpdateBundle,
    SkillGenomeUpdateRecord,
)
from ix_cognition_kernel.wave3_substrate import (
    CORE_WAVE_THREE_ARTIFACT_KINDS,
    WaveThreeSubstrateResult,
    WaveThreeSubstrateStatus,
)
from ix_cognition_kernel.wave3_tribunal import (
    TribunalDecisionRecord,
    TribunalPhase,
    TribunalVotePosition,
    tribunal_vote,
)
from ix_cognition_kernel.wave3_worldtwin import (
    REQUIRED_WORLDTWIN_BOUNDARY_KINDS,
    WorldTwinAssumption,
    WorldTwinAssumptionStatus,
    WorldTwinCounterfactualBranch,
    WorldTwinExpectedOutcome,
    WorldTwinImpactLevel,
    WorldTwinScenarioBoundary,
    WorldTwinScenarioBundle,
    WorldTwinScenarioRecord,
)

TRIBUNAL_ROLE_IDS = (
    "planner",
    "skeptic-red-team",
    "verifier",
    "tool-safety-officer",
    "translator-interpreter",
    "execution-liaison",
)


ROLE_IDS = tuple(
    dict.fromkeys(
        TRIBUNAL_ROLE_IDS
        + DEFAULT_MEMORY_ROLE_REVIEW_SCOPE
        + DEFAULT_SKILL_GENOME_REVIEW_SCOPE
        + (
            "reward-auditor",
            "world-modeler",
        )
    )
)


def role_bundle() -> RoleArtifactBundle:
    return RoleArtifactBundle(
        bundle_id="role-bundle-substrate",
        records=tuple(
            complete_role_artifact_record(
                role_id, evidence_ids=(f"role-evidence:{role_id}",)
            )
            for role_id in ROLE_IDS
        ),
        required_role_ids=ROLE_IDS,
    )


def coordination_result() -> WaveThreeCoordinationResult:
    required_engine_ids = (
        "belief",
        "uncertainty",
        "causal-world-model",
        "plan-graph",
        "evaluator",
        "self-play-curriculum",
        "skill-genome",
        "outcome-learning",
        "memory-quarantine",
        "multi-agent-tribunal",
        "reward-auditor",
        "blackfox-handoff",
        "non-attached-purpose",
    )
    engine_bundle = EngineCoordinationBundle(
        bundle_id="engine-bundle-substrate",
        records=tuple(
            complete_engine_coordination_record(
                engine_id,
                evidence_ids=(f"engine-evidence:{engine_id}",),
            )
            for engine_id in required_engine_ids
        ),
        required_engine_ids=required_engine_ids,
    )
    return coordinate_wave_three_engines(
        coordination_id="coordination-substrate",
        engine_bundle=engine_bundle,
        required_engine_ids=required_engine_ids,
    )


def tribunal_record(bundle: RoleArtifactBundle) -> TribunalDecisionRecord:
    votes = (
        tribunal_vote(
            role_id="planner",
            phase=TribunalPhase.PROPOSAL,
            evidence_ids=("vote-evidence:planner",),
            rationale="Planner proposes a bounded review package.",
        ),
        tribunal_vote(
            role_id="skeptic-red-team",
            phase=TribunalPhase.CRITIQUE,
            position=TribunalVotePosition.CONCERN,
            evidence_ids=("vote-evidence:skeptic",),
            rationale="Skeptic records non-blocking review concerns.",
            concerns=("Rollback evidence must remain attached.",),
        ),
        tribunal_vote(
            role_id="verifier",
            phase=TribunalPhase.VERIFICATION,
            evidence_ids=("vote-evidence:verifier",),
            rationale="Verifier confirms review evidence is visible.",
        ),
        tribunal_vote(
            role_id="tool-safety-officer",
            phase=TribunalPhase.SAFETY,
            evidence_ids=("vote-evidence:safety",),
            rationale="Safety role confirms no execution authority is granted.",
        ),
        tribunal_vote(
            role_id="translator-interpreter",
            phase=TribunalPhase.TRANSLATION,
            evidence_ids=("vote-evidence:translator",),
            rationale="Translator keeps the package human-readable.",
        ),
        tribunal_vote(
            role_id="execution-liaison",
            phase=TribunalPhase.HANDOFF,
            evidence_ids=("vote-evidence:handoff",),
            rationale="Execution liaison packages review-only handoff evidence.",
        ),
    )
    return TribunalDecisionRecord(
        tribunal_id="tribunal-substrate",
        role_artifact_bundle=bundle,
        votes=votes,
        required_role_ids=TRIBUNAL_ROLE_IDS,
    )


def reward_audit() -> RewardAuditRecord:
    return clean_reward_audit_record(
        audit_id="reward-substrate",
        objective="Improve substrate review quality without bypassing authority.",
        metric="visible-evidence-coverage",
        mission_boundary="No automatic execution and no AGI claim.",
        evidence_ids=("reward-evidence:substrate",),
    )


def curriculum_bundle() -> CurriculumTaskBundle:
    measurement = passing_curriculum_measurement(
        measurement_id="measurement:staged",
        metric_name="evidence-visibility",
        target="all failed evidence remains visible",
        observed="all failed evidence remained visible",
        evidence_id="measurement-evidence:staged",
    )
    staged = measured_curriculum_task(
        task_id="task-staged",
        task_kind=CurriculumTaskKind.STAGED_SELF_PLAY,
        stage=1,
        skill_under_test="belief update under evidence pressure",
        objective="Exercise bounded learning without hidden state updates.",
        challenge_description="Compare prediction and observation under review.",
        evidence_ids=("task-evidence:staged",),
        measurements=(measurement,),
    )
    adversarial = measured_curriculum_task(
        task_id="task-adversarial",
        task_kind=CurriculumTaskKind.ADVERSARIAL_CHALLENGE,
        stage=2,
        skill_under_test="reward hacking detection",
        objective="Detect hidden failed checks.",
        challenge_description="Pressure the score by hiding failed checks.",
        evidence_ids=("task-evidence:adversarial",),
        measurements=(
            passing_curriculum_measurement(
                measurement_id="measurement:adversarial",
                metric_name="hidden-failure-detection",
                target="hidden failure detected",
                observed="hidden failure detected",
                evidence_id="measurement-evidence:adversarial",
            ),
        ),
        adversarial_pressures=("hidden failed check",),
    )
    transfer = measured_curriculum_task(
        task_id="task-transfer",
        task_kind=CurriculumTaskKind.TRANSFER_CHECK,
        stage=3,
        skill_under_test="uncertainty preservation transfer",
        objective="Transfer uncertainty discipline to a new scenario.",
        challenge_description="Apply uncertainty labels to WorldTwin reasoning.",
        evidence_ids=("task-evidence:transfer",),
        measurements=(
            passing_curriculum_measurement(
                measurement_id="measurement:transfer",
                metric_name="uncertainty-preservation",
                target="uncertainty remains visible",
                observed="uncertainty remained visible",
                evidence_id="measurement-evidence:transfer",
            ),
        ),
        transfer_domains=("worldtwin scenario review",),
    )
    return CurriculumTaskBundle(
        bundle_id="curriculum-bundle-substrate",
        tasks=(staged, adversarial, transfer),
    )


def discovery_bundle() -> DiscoveryRecordBundle:
    candidate = DiscoveryCandidate(
        candidate_id="candidate-substrate",
        candidate_kind=DiscoveryCandidateKind.SKILL_CANDIDATE,
        summary="A reusable visible-evidence check may improve substrate review.",
        source_artifact_ids=("tribunal-record:tribunal-substrate",),
        proposed_update_targets=(DiscoveryUpdateTarget.SKILL_GENOME,),
        novelty_claim="The candidate binds visible failure evidence to reuse gating.",
        risk_notes=("Could become metric gaming if failed checks are hidden.",),
        evidence_ids=("candidate-evidence:substrate",),
    )
    evaluation = EvaluationRecord(
        evaluation_id="evaluation-discovery",
        title="Discovery candidate evaluator review.",
        evaluated_artifact_ids=(candidate.artifact_id,),
        criteria=(
            AcceptanceCriterion(
                criterion_id="criterion-discovery",
                description="Candidate has visible evidence and risk notes.",
                required=True,
                satisfied=True,
                evidence_ids=("criterion-evidence:discovery",),
            ),
        ),
        status=EvaluationStatus.PASSED,
        evidence_ids=("evaluation-evidence:discovery",),
        reasons=(),
        evaluator_role_id="verifier",
    )
    record = DiscoveryRecord(
        discovery_id="discovery-substrate",
        candidate=candidate,
        evaluation_ledger=EvaluationLedger(records=(evaluation,)),
        required_evaluation_ids=("evaluation-discovery",),
        evidence_ids=("discovery-evidence:substrate",),
    )
    return DiscoveryRecordBundle(
        bundle_id="discovery-bundle-substrate",
        records=(record,),
    )


def outcome_record() -> OutcomeLearningRecord:
    return OutcomeLearningRecord(
        outcome_id="outcome-substrate",
        summary="Outcome supports memory and skill governance evidence.",
        status=OutcomeLearningStatus.ACCEPTED,
        pressure=OutcomePressure.CONFIRMED,
        belief_revision_ids=("belief-revision-substrate",),
        causal_revision_ids=("causal-revision-substrate",),
        prediction_comparison_ids=("prediction-comparison-substrate",),
        evidence_ids=("outcome-evidence:substrate",),
        learning_summary="Accepted outcome evidence supports reuse governance.",
        reasons=("Outcome was accepted with visible evidence.",),
    )


def memory_candidate() -> MemoryCandidate:
    return MemoryCandidate(
        candidate_id="memory-substrate",
        kind=MemoryCandidateKind.PROCEDURE_HINT,
        content="Validated evidence checks can be reused under review.",
        provenance=("wave3-substrate-test",),
        evidence_ids=("memory-evidence:substrate",),
        source_outcome_ids=("outcome-substrate",),
        confidence=0.84,
        proposed_audit_index=0,
    )


def memory_decision_bundle(bundle: RoleArtifactBundle) -> MemoryRoleDecisionBundle:
    ledger = MemoryQuarantineLedger(
        candidates=(memory_candidate(),),
        validations=(
            MemoryValidationRecord(
                validation_id="memory-validation-substrate",
                candidate_id="memory-substrate",
                status=MemoryValidationStatus.ACCEPTED,
                evidence_ids=("memory-evidence:substrate",),
                outcome_ids=("outcome-substrate",),
                reviewer_role_id="memory-integrity-specialist",
                reasons=("Memory candidate stayed bounded to reviewed evidence.",),
            ),
        ),
    )
    decision = MemoryRoleDecisionRecord(
        decision_id="memory-decision-substrate",
        memory_ledger=ledger,
        role_artifact_bundle=bundle,
        evidence_ids=("memory-decision-evidence:substrate",),
    )
    return MemoryRoleDecisionBundle(
        bundle_id="memory-bundle-substrate",
        decisions=(decision,),
    )


def skill_update_bundle(bundle: RoleArtifactBundle) -> SkillGenomeUpdateBundle:
    outcome_ledger = OutcomeLearningLedger(records=(outcome_record(),))
    memory_ledger = MemoryQuarantineLedger(
        candidates=(memory_candidate(),),
        validations=(
            MemoryValidationRecord(
                validation_id="memory-validation-substrate",
                candidate_id="memory-substrate",
                status=MemoryValidationStatus.ACCEPTED,
                evidence_ids=("memory-evidence:substrate",),
                outcome_ids=("outcome-substrate",),
                reviewer_role_id="memory-integrity-specialist",
                reasons=("Memory candidate stayed bounded to reviewed evidence.",),
            ),
        ),
    )
    skill = SkillCandidate(
        skill_id="skill-substrate",
        kind=SkillCandidateKind.EVALUATION_CHECK,
        name="Visible failed-evidence check",
        procedure_steps=(
            "Inspect review artifact evidence.",
            "Confirm failed checks remain visible.",
        ),
        applicability_conditions=("Use only for governance evidence review.",),
        failure_modes=("Fails if hidden failed checks can improve score.",),
        source_memory_candidate_ids=("memory-substrate",),
        source_outcome_ids=("outcome-substrate",),
        confidence=0.86,
        provenance=("wave3-substrate-test",),
        proposed_audit_index=1,
    )
    reuse = SkillReuseEvidenceRecord(
        reuse_id="reuse-substrate",
        skill_id="skill-substrate",
        outcome_id="outcome-substrate",
        evidence_ids=("reuse-evidence:substrate",),
        succeeded=True,
        audit_index=2,
        applicability_condition_ids=("condition-visible-evidence",),
        failure_mode_ids=(),
        reasons=("Reuse preserved failed-evidence visibility.",),
    )
    skill_ledger = evaluate_skill_candidates(
        candidates=(skill,),
        reuse_records=(reuse,),
        memory_ledger=memory_ledger,
        outcome_ledger=outcome_ledger,
        reviewer_role_id="learning-archivist",
    )
    update = SkillGenomeUpdateRecord(
        update_id="skill-update-substrate",
        skill_ledger=skill_ledger,
        role_artifact_bundle=bundle,
        evidence_ids=("skill-update-evidence:substrate",),
        allowed_transfer_domains=("repo governance evidence review",),
        reuse_limitations=("Fresh human review is required before every reuse.",),
    )
    return SkillGenomeUpdateBundle(
        bundle_id="skill-bundle-substrate",
        updates=(update,),
    )


def worldtwin_bundle() -> WorldTwinScenarioBundle:
    assumptions = (
        WorldTwinAssumption(
            assumption_id="assumption-substrate",
            statement="The package remains review-only at the handoff boundary.",
            status=WorldTwinAssumptionStatus.ACTIVE,
            confidence=0.77,
            impact_if_wrong=WorldTwinImpactLevel.MEDIUM,
            evidence_ids=("worldtwin-evidence:assumption",),
            required_evidence=(),
        ),
    )
    outcomes = (
        WorldTwinExpectedOutcome(
            outcome_id="worldtwin-outcome-substrate",
            description="Handoff remains human-review-required.",
            measurement_name="authority-state",
            expected_result="human-review-required and automatic-execution-false",
            uncertainty_notes=("Scenario is bounded and not complete reality.",),
            evidence_ids=("worldtwin-evidence:outcome",),
        ),
    )
    scenario = WorldTwinScenarioRecord(
        scenario_id="worldtwin-substrate",
        title="Wave 3 review-only handoff scenario",
        bounded_question="Does the substrate preserve review-only boundaries?",
        system_under_test="IX-CognitionKernel Wave 3 substrate",
        boundaries=tuple(
            WorldTwinScenarioBoundary(
                boundary_id=f"worldtwin-boundary:{kind.value}",
                kind=kind,
                description=f"{kind.value} boundary is visible.",
            )
            for kind in REQUIRED_WORLDTWIN_BOUNDARY_KINDS
        ),
        assumptions=assumptions,
        expected_outcomes=outcomes,
        counterfactual_branches=(
            WorldTwinCounterfactualBranch(
                branch_id="branch-substrate",
                changed_assumption_ids=("assumption-substrate",),
                expected_outcome_ids=("worldtwin-outcome-substrate",),
                rationale="Flip the review-only assumption and observe boundary risk.",
                risk_notes=("Hidden authority would block the scenario.",),
                evidence_ids=("worldtwin-evidence:branch",),
            ),
        ),
        evidence_ids=("worldtwin-evidence:scenario",),
    )
    return WorldTwinScenarioBundle(
        bundle_id="worldtwin-bundle-substrate",
        scenarios=(scenario,),
    )


def blackfox_handoff_bundle() -> BlackFoxHandoffBundle:
    package = BlackFoxHandoffPackage(
        handoff_id="blackfox-substrate",
        subject="Wave 3 review-only cognition handoff",
        cognition_artifact_ids=(
            "tribunal-record:tribunal-substrate",
            "worldtwin-scenario:worldtwin-substrate",
        ),
        evidence_bundle_ids=("substrate-bundle",),
        execution_boundaries=tuple(
            BlackFoxExecutionBoundary(
                boundary_id=f"blackfox-boundary:{kind.value}",
                kind=kind,
                description=f"{kind.value} is enforced for the handoff.",
                evidence_ids=(f"blackfox-evidence:boundary:{kind.value}",),
            )
            for kind in REQUIRED_BLACKFOX_BOUNDARY_KINDS
        ),
        review_requirements=tuple(
            BlackFoxReviewRequirement(
                requirement_id=f"blackfox-requirement:{kind.value}",
                requirement_kind=kind,
                reviewer_role="human-reviewer",
                description=f"{kind.value} remains visible before review.",
                evidence_ids=(f"blackfox-evidence:requirement:{kind.value}",),
            )
            for kind in REQUIRED_BLACKFOX_REVIEW_REQUIREMENT_KINDS
        ),
        rollback_references=(
            BlackFoxRollbackReference(
                rollback_id="rollback-substrate",
                description="Return to the pre-handoff review package on failure.",
                trigger_conditions=("Stop if human authority is absent.",),
                evidence_ids=("blackfox-evidence:rollback",),
            ),
        ),
        evidence_ids=("blackfox-evidence:handoff",),
    )
    return BlackFoxHandoffBundle(
        bundle_id="blackfox-bundle-substrate",
        packages=(package,),
    )


def assurance_bundle(  # type: ignore[no-untyped-def]
    component_bundles,
) -> AssuranceRecordBundle:
    artifacts = tuple(
        artifact for bundle in component_bundles for artifact in bundle.artifacts
    )
    artifact_ids = tuple(sorted(artifact.artifact_id for artifact in artifacts))
    claims = tuple(
        supported_assurance_claim(
            claim_id=f"claim:{kind.value}",
            claim_kind=kind,
            statement=f"The substrate preserves {kind.value} for human review.",
            supporting_artifact_ids=artifact_ids,
            evidence_ids=(f"assurance-evidence:{kind.value}",),
            limitations=(
                "This supports human review only; it is not certification.",
                "This does not prove AGI or production readiness.",
            ),
        )
        for kind in REQUIRED_ASSURANCE_CLAIM_KINDS
    )
    required_artifact_kinds = tuple(
        kind
        for kind in CORE_WAVE_THREE_ARTIFACT_KINDS
        if kind is not WaveThreeArtifactKind.ASSURANCE_RECORD
    )
    record = AssuranceRecord(
        assurance_id="assurance-substrate",
        artifact_bundles=component_bundles,
        claims=claims,
        evidence_ids=("assurance-evidence:substrate",),
        required_artifact_kinds=required_artifact_kinds,
    )
    return AssuranceRecordBundle(
        bundle_id="assurance-bundle-substrate",
        records=(record,),
    )


def ready_substrate() -> WaveThreeSubstrateResult:
    roles = role_bundle()
    coordination = coordination_result()
    tribunal = tribunal_record(roles)
    reward = reward_audit()
    curriculum = curriculum_bundle()
    discovery = discovery_bundle()
    memory = memory_decision_bundle(roles)
    skill = skill_update_bundle(roles)
    worldtwin = worldtwin_bundle()
    blackfox = blackfox_handoff_bundle()
    pre_assurance_bundles = (
        coordination.artifact_bundle,
        roles.to_artifact_bundle(artifact_bundle_id="assurance-input:roles"),
        tribunal.to_artifact_bundle(artifact_bundle_id="assurance-input:tribunal"),
        reward.to_artifact_bundle(artifact_bundle_id="assurance-input:reward"),
        curriculum.to_artifact_bundle(artifact_bundle_id="assurance-input:curriculum"),
        discovery.to_artifact_bundle(artifact_bundle_id="assurance-input:discovery"),
        memory.to_artifact_bundle(artifact_bundle_id="assurance-input:memory"),
        skill.to_artifact_bundle(artifact_bundle_id="assurance-input:skill"),
        worldtwin.to_artifact_bundle(artifact_bundle_id="assurance-input:worldtwin"),
        blackfox.to_artifact_bundle(artifact_bundle_id="assurance-input:blackfox"),
    )
    return WaveThreeSubstrateResult(
        substrate_id="substrate-001",
        coordination_result=coordination,
        role_artifact_bundle=roles,
        tribunal_record=tribunal,
        reward_audit=reward,
        curriculum_bundle=curriculum,
        discovery_bundle=discovery,
        memory_decision_bundle=memory,
        skill_update_bundle=skill,
        worldtwin_bundle=worldtwin,
        blackfox_handoff_bundle=blackfox,
        assurance_bundle=assurance_bundle(pre_assurance_bundles),
        evidence_ids=("substrate-evidence:001",),
    )


def test_core_artifacts_exclude_readiness_snapshot_until_next_gate() -> None:
    assert CORE_WAVE_THREE_ARTIFACT_KINDS == (
        WaveThreeArtifactKind.ENGINE_COORDINATION,
        WaveThreeArtifactKind.ROLE_ARTIFACT,
        WaveThreeArtifactKind.TRIBUNAL_RECORD,
        WaveThreeArtifactKind.REWARD_AUDIT,
        WaveThreeArtifactKind.CURRICULUM_TASK,
        WaveThreeArtifactKind.DISCOVERY_RECORD,
        WaveThreeArtifactKind.MEMORY_QUARANTINE_DECISION,
        WaveThreeArtifactKind.SKILL_GENOME_UPDATE,
        WaveThreeArtifactKind.WORLDTWIN_SCENARIO,
        WaveThreeArtifactKind.BLACKFOX_HANDOFF,
        WaveThreeArtifactKind.ASSURANCE_RECORD,
    )


def test_ready_substrate_integrates_layers_without_execution_or_agi() -> None:
    substrate = ready_substrate()

    assert substrate.status is WaveThreeSubstrateStatus.READY_FOR_READINESS_SNAPSHOT
    assert substrate.ready_for_readiness_snapshot is True
    assert substrate.permits_automatic_execution is False
    assert substrate.certifies_agi is False
    assert substrate.represented_artifact_kinds == CORE_WAVE_THREE_ARTIFACT_KINDS
    assert substrate.missing_required_artifact_kinds == ()
    assert substrate.readiness_gaps == ()
    assert substrate.blocking_gaps == ()
    assert "automatic execution and AGI certification are not permitted" in (
        substrate.review_summary
    )


def test_substrate_requires_top_level_evidence_before_snapshot() -> None:
    source = ready_substrate()
    substrate = WaveThreeSubstrateResult(
        substrate_id="substrate-001",
        coordination_result=source.coordination_result,
        role_artifact_bundle=source.role_artifact_bundle,
        tribunal_record=source.tribunal_record,
        reward_audit=source.reward_audit,
        curriculum_bundle=source.curriculum_bundle,
        discovery_bundle=source.discovery_bundle,
        memory_decision_bundle=source.memory_decision_bundle,
        skill_update_bundle=source.skill_update_bundle,
        worldtwin_bundle=source.worldtwin_bundle,
        blackfox_handoff_bundle=source.blackfox_handoff_bundle,
        assurance_bundle=source.assurance_bundle,
        evidence_ids=(),
    )

    assert substrate.status is WaveThreeSubstrateStatus.NEEDS_EVIDENCE
    assert substrate.ready_for_readiness_snapshot is False
    assert "substrate-001 has no top-level evidence ids" in substrate.readiness_gaps


def test_substrate_reports_missing_artifact_without_faking_readiness() -> None:
    source = ready_substrate()
    substrate = WaveThreeSubstrateResult(
        substrate_id="substrate-001",
        coordination_result=source.coordination_result,
        role_artifact_bundle=source.role_artifact_bundle,
        tribunal_record=source.tribunal_record,
        reward_audit=source.reward_audit,
        curriculum_bundle=source.curriculum_bundle,
        discovery_bundle=source.discovery_bundle,
        memory_decision_bundle=source.memory_decision_bundle,
        skill_update_bundle=source.skill_update_bundle,
        worldtwin_bundle=source.worldtwin_bundle,
        blackfox_handoff_bundle=source.blackfox_handoff_bundle,
        assurance_bundle=source.assurance_bundle,
        evidence_ids=("substrate-evidence:001",),
        required_artifact_kinds=CORE_WAVE_THREE_ARTIFACT_KINDS
        + (WaveThreeArtifactKind.READINESS_SNAPSHOT,),
    )

    assert substrate.status is WaveThreeSubstrateStatus.NEEDS_EVIDENCE
    assert substrate.missing_required_artifact_kinds == (
        WaveThreeArtifactKind.READINESS_SNAPSHOT,
    )
    assert "integrated substrate missing artifact kinds: readiness-snapshot" in (
        substrate.readiness_gaps
    )


def test_substrate_blocks_when_component_bundle_blocks() -> None:
    source = ready_substrate()
    blocked_worldtwin = WorldTwinScenarioRecord(
        scenario_id="worldtwin-blocked",
        title="Blocked scenario",
        bounded_question="Does a critical disputed assumption block progress?",
        system_under_test="IX-CognitionKernel Wave 3 substrate",
        boundaries=tuple(
            WorldTwinScenarioBoundary(
                boundary_id=f"blocked-boundary:{kind.value}",
                kind=kind,
                description=f"{kind.value} boundary is visible.",
            )
            for kind in REQUIRED_WORLDTWIN_BOUNDARY_KINDS
        ),
        assumptions=(
            WorldTwinAssumption(
                assumption_id="assumption-blocked",
                statement="The review-only boundary is disputed.",
                status=WorldTwinAssumptionStatus.DISPUTED,
                confidence=0.2,
                impact_if_wrong=WorldTwinImpactLevel.CRITICAL,
                evidence_ids=("blocked-evidence:assumption",),
                required_evidence=(),
            ),
        ),
        expected_outcomes=(
            WorldTwinExpectedOutcome(
                outcome_id="blocked-outcome",
                description="Boundary remains review-only.",
                measurement_name="authority-state",
                expected_result="human-review-required",
                uncertainty_notes=("Disputed assumption blocks this scenario.",),
                evidence_ids=("blocked-evidence:outcome",),
            ),
        ),
        counterfactual_branches=(
            WorldTwinCounterfactualBranch(
                branch_id="blocked-branch",
                changed_assumption_ids=("assumption-blocked",),
                expected_outcome_ids=("blocked-outcome",),
                rationale="A disputed assumption should stop progress.",
                risk_notes=("Hidden authority risk is critical.",),
                evidence_ids=("blocked-evidence:branch",),
            ),
        ),
        evidence_ids=("blocked-evidence:scenario",),
    )
    substrate = WaveThreeSubstrateResult(
        substrate_id="substrate-001",
        coordination_result=source.coordination_result,
        role_artifact_bundle=source.role_artifact_bundle,
        tribunal_record=source.tribunal_record,
        reward_audit=source.reward_audit,
        curriculum_bundle=source.curriculum_bundle,
        discovery_bundle=source.discovery_bundle,
        memory_decision_bundle=source.memory_decision_bundle,
        skill_update_bundle=source.skill_update_bundle,
        worldtwin_bundle=WorldTwinScenarioBundle(
            bundle_id="worldtwin-bundle-blocked",
            scenarios=(blocked_worldtwin,),
        ),
        blackfox_handoff_bundle=source.blackfox_handoff_bundle,
        assurance_bundle=source.assurance_bundle,
        evidence_ids=("substrate-evidence:001",),
    )

    assert substrate.status is WaveThreeSubstrateStatus.BLOCKED
    assert substrate.ready_for_readiness_snapshot is False
    assert any(
        "worldtwin-scenario:worldtwin-blocked" in gap for gap in substrate.blocking_gaps
    )


def test_substrate_fingerprint_is_deterministic() -> None:
    first = ready_substrate().fingerprint()
    second = ready_substrate().fingerprint()

    assert first == second
    assert len(first) == 64
