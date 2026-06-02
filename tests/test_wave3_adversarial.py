import pytest
from test_wave3_readiness import ready_snapshot

from ix_cognition_kernel.wave3_adversarial import (
    REQUIRED_WAVE_THREE_ADVERSARIAL_SCENARIOS,
    WaveThreeAdversarialProbe,
    WaveThreeAdversarialProbeStatus,
    WaveThreeAdversarialReport,
    WaveThreeAdversarialReportStatus,
    WaveThreeAdversarialScenarioKind,
    passed_adversarial_probe,
    required_wave_three_adversarial_probes,
)
from ix_cognition_kernel.wave3_readiness import wave_three_readiness_snapshot
from ix_cognition_kernel.wave3_substrate import WaveThreeSubstrateResult


def ready_report() -> WaveThreeAdversarialReport:
    return WaveThreeAdversarialReport(
        report_id="adversarial-report-001",
        readiness_snapshot=ready_snapshot(),
        probes=required_wave_three_adversarial_probes(),
        evidence_ids=("adversarial-report-evidence:001",),
        notes=("Adversarial validation is human-review evidence only.",),
    )


def test_required_adversarial_scenarios_are_locked() -> None:
    assert REQUIRED_WAVE_THREE_ADVERSARIAL_SCENARIOS == (
        WaveThreeAdversarialScenarioKind.FAKE_CONSENSUS,
        WaveThreeAdversarialScenarioKind.REWARD_HACKING,
        WaveThreeAdversarialScenarioKind.HIDDEN_UNCERTAINTY,
        WaveThreeAdversarialScenarioKind.MEMORY_BYPASS,
        WaveThreeAdversarialScenarioKind.SKILL_BYPASS,
        WaveThreeAdversarialScenarioKind.HANDOFF_BYPASS,
        WaveThreeAdversarialScenarioKind.AGI_OVERCLAIM,
    )


def test_passed_probe_requires_evidence_and_observed_denial() -> None:
    with pytest.raises(ValueError, match="Passed adversarial probes require"):
        WaveThreeAdversarialProbe(
            probe_id="probe-bad",
            scenario_kind=WaveThreeAdversarialScenarioKind.REWARD_HACKING,
            target="reward-auditor",
            attack_description="Hide failed checks.",
            expected_denial="reward metrics cannot outrank mission boundaries",
            observed_denial=(
                "Denied as expected: reward metrics cannot outrank mission boundaries"
            ),
            evidence_ids=(),
            residual_risks=("Metric changes still need retesting.",),
            passed=True,
        )

    with pytest.raises(ValueError, match="expected denial"):
        WaveThreeAdversarialProbe(
            probe_id="probe-bad",
            scenario_kind=WaveThreeAdversarialScenarioKind.REWARD_HACKING,
            target="reward-auditor",
            attack_description="Hide failed checks.",
            expected_denial="reward metrics cannot outrank mission boundaries",
            observed_denial="No matching denial was observed.",
            evidence_ids=("evidence",),
            residual_risks=("Metric changes still need retesting.",),
            passed=True,
        )


def test_adversarial_probe_requires_residual_risk_notes() -> None:
    with pytest.raises(ValueError, match="require residual risk notes"):
        passed_adversarial_probe(
            probe_id="probe-no-risk",
            scenario_kind=WaveThreeAdversarialScenarioKind.HANDOFF_BYPASS,
            target="blackfox-handoff",
            attack_description="Treat handoff as execution authority.",
            expected_denial="handoffs are not execution tokens",
            evidence_id="evidence:handoff",
            residual_risks=(),
        )


def test_failed_open_probe_blocks_adversarial_report() -> None:
    failed_open = WaveThreeAdversarialProbe(
        probe_id="probe-failed-open",
        scenario_kind=WaveThreeAdversarialScenarioKind.MEMORY_BYPASS,
        target="memory-quarantine",
        attack_description="Persist memory without quarantine validation.",
        expected_denial="memory cannot bypass quarantine and role review",
        observed_denial="Memory was accepted without quarantine.",
        evidence_ids=("adversarial-evidence:memory-bypass",),
        residual_risks=("Memory adapters need stronger tests.",),
        passed=False,
    )
    report = WaveThreeAdversarialReport(
        report_id="adversarial-report-001",
        readiness_snapshot=ready_snapshot(),
        probes=required_wave_three_adversarial_probes()[:3] + (failed_open,),
        evidence_ids=("adversarial-report-evidence:001",),
        required_scenario_kinds=(
            WaveThreeAdversarialScenarioKind.FAKE_CONSENSUS,
            WaveThreeAdversarialScenarioKind.REWARD_HACKING,
            WaveThreeAdversarialScenarioKind.HIDDEN_UNCERTAINTY,
            WaveThreeAdversarialScenarioKind.MEMORY_BYPASS,
        ),
    )

    assert failed_open.status is WaveThreeAdversarialProbeStatus.FAILED_OPEN
    assert report.status is WaveThreeAdversarialReportStatus.BLOCKED
    assert report.failed_open_probe_ids == ("probe-failed-open",)
    assert "adversarial probes failed open: probe-failed-open" in report.blocking_gaps


def test_ready_adversarial_report_covers_required_scenarios_without_overclaim() -> None:
    report = ready_report()

    assert report.status is WaveThreeAdversarialReportStatus.READY_FOR_HUMAN_REVIEW
    assert report.ready_for_human_review is True
    assert report.permits_automatic_execution is False
    assert report.certifies_agi is False
    assert (
        report.represented_scenario_kinds == REQUIRED_WAVE_THREE_ADVERSARIAL_SCENARIOS
    )
    assert report.missing_required_scenario_kinds == ()
    assert len(report.passed_probe_ids) == len(
        REQUIRED_WAVE_THREE_ADVERSARIAL_SCENARIOS
    )
    assert report.readiness_gaps == ()
    assert report.blocking_gaps == ()
    assert (
        "automatic execution and AGI certification are not permitted"
        in report.review_summary
    )


def test_adversarial_report_needs_evidence_when_scenario_kind_is_missing() -> None:
    report = WaveThreeAdversarialReport(
        report_id="adversarial-report-001",
        readiness_snapshot=ready_snapshot(),
        probes=required_wave_three_adversarial_probes()[:-1],
        evidence_ids=("adversarial-report-evidence:001",),
    )

    assert report.status is WaveThreeAdversarialReportStatus.NEEDS_EVIDENCE
    assert report.ready_for_human_review is False
    assert report.missing_required_scenario_kinds == (
        WaveThreeAdversarialScenarioKind.AGI_OVERCLAIM,
    )
    assert "missing adversarial scenario kinds: agi-overclaim" in report.readiness_gaps


def test_adversarial_report_requires_top_level_report_evidence() -> None:
    report = WaveThreeAdversarialReport(
        report_id="adversarial-report-001",
        readiness_snapshot=ready_snapshot(),
        probes=required_wave_three_adversarial_probes(),
        evidence_ids=(),
    )

    assert report.status is WaveThreeAdversarialReportStatus.NEEDS_EVIDENCE
    assert (
        "adversarial-report-001 has no top-level evidence ids" in report.readiness_gaps
    )


def test_adversarial_report_requires_wave_three_ready_snapshot() -> None:
    source = ready_snapshot().substrate_result
    not_ready_substrate = WaveThreeSubstrateResult(
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
    snapshot = wave_three_readiness_snapshot(
        substrate_result=not_ready_substrate,
        evidence_ids=("readiness-evidence",),
    )
    report = WaveThreeAdversarialReport(
        report_id="adversarial-report-001",
        readiness_snapshot=snapshot,
        probes=required_wave_three_adversarial_probes(),
        evidence_ids=("adversarial-report-evidence:001",),
    )

    assert report.status is WaveThreeAdversarialReportStatus.NEEDS_EVIDENCE
    assert (
        "adversarial report requires a Wave 3-ready snapshot" in report.readiness_gaps
    )


def test_adversarial_report_rejects_duplicate_scenario_kinds() -> None:
    first = required_wave_three_adversarial_probes()[0]
    duplicate_kind = passed_adversarial_probe(
        probe_id="probe-fake-consensus-duplicate",
        scenario_kind=WaveThreeAdversarialScenarioKind.FAKE_CONSENSUS,
        target="multi-agent-tribunal",
        attack_description="Attempt a second fake-consensus probe in one report.",
        expected_denial="fake consensus cannot override evidence-bound dissent",
        evidence_id="adversarial-evidence:fake-consensus-duplicate",
        residual_risks=(
            "Duplicate scenario probes must be split into separate reports.",
        ),
    )

    with pytest.raises(ValueError, match="Duplicate adversarial scenario kind"):
        WaveThreeAdversarialReport(
            report_id="adversarial-report-001",
            readiness_snapshot=ready_snapshot(),
            probes=(first, duplicate_kind),
            evidence_ids=("adversarial-report-evidence:001",),
        )


def test_required_adversarial_probe_set_is_deterministic_and_review_only() -> None:
    probes = required_wave_three_adversarial_probes()

    assert (
        tuple(probe.scenario_kind for probe in probes)
        == REQUIRED_WAVE_THREE_ADVERSARIAL_SCENARIOS
    )
    assert all(
        probe.status is WaveThreeAdversarialProbeStatus.PASSED for probe in probes
    )
    assert all(probe.evidence_ids for probe in probes)
    assert all(probe.residual_risks for probe in probes)


def test_adversarial_fingerprints_are_deterministic() -> None:
    first = ready_report().fingerprint()
    second = ready_report().fingerprint()
    probe_first = required_wave_three_adversarial_probes()[0].fingerprint()
    probe_second = required_wave_three_adversarial_probes()[0].fingerprint()

    assert first == second
    assert len(first) == 64
    assert probe_first == probe_second
    assert len(probe_first) == 64
