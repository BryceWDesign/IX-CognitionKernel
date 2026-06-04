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
from ix_cognition_kernel.wave5_reproducibility import (
    EXTERNAL_REPRODUCTION_SOURCE_SYSTEMS,
    REQUIRED_WAVE_FIVE_REPLAY_CHECKS,
    WaveFiveCommandOutcome,
    WaveFiveCommandRecord,
    WaveFiveDigestKind,
    WaveFiveDigestRecord,
    WaveFiveReplayCheck,
    WaveFiveReplayCheckKind,
    WaveFiveReproducibleEvidenceBundle,
    WaveFiveReproductionGap,
    WaveFiveReproductionGapSeverity,
    WaveFiveReproductionStatus,
    external_reproduction_source_systems,
    required_wave_five_replay_checks,
)

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64
DIGEST_E = "e" * 64


def command(
    command_id: str = "command-pytest",
    *,
    outcome: WaveFiveCommandOutcome = WaveFiveCommandOutcome.PASSED,
    expected_exit_code: int = 0,
    observed_exit_code: int = 0,
) -> WaveFiveCommandRecord:
    return WaveFiveCommandRecord(
        command_id=command_id,
        command=("python", "-m", "pytest", "-q"),
        working_directory=".",
        expected_exit_code=expected_exit_code,
        observed_exit_code=observed_exit_code,
        outcome=outcome,
        stdout_digest=DIGEST_A,
        stderr_digest=DIGEST_B,
        evidence_ids=(f"evidence-{command_id}",),
    )


def digest(
    digest_id: str,
    digest_kind: WaveFiveDigestKind,
    value: str,
) -> WaveFiveDigestRecord:
    return WaveFiveDigestRecord(
        digest_id=digest_id,
        digest_kind=digest_kind,
        path=f"artifacts/{digest_id}.txt",
        digest=value,
        evidence_ids=(f"evidence-{digest_id}",),
    )


def required_digests() -> tuple[WaveFiveDigestRecord, ...]:
    return (
        digest("digest-output", WaveFiveDigestKind.OUTPUT_ARTIFACT, DIGEST_C),
        digest("digest-source", WaveFiveDigestKind.SOURCE_TREE, DIGEST_D),
        digest("digest-tests", WaveFiveDigestKind.TEST_TREE, DIGEST_E),
    )


def check(
    check_id: str,
    check_kind: WaveFiveReplayCheckKind,
    *,
    passed: bool = True,
    blocking: bool = True,
) -> WaveFiveReplayCheck:
    return WaveFiveReplayCheck(
        check_id=check_id,
        check_kind=check_kind,
        description="Replay check preserves reproducible Wave 5 evidence.",
        passed=passed,
        blocking=blocking,
        evidence_ids=(f"evidence-{check_id}",),
    )


def required_checks() -> tuple[WaveFiveReplayCheck, ...]:
    return tuple(
        check(f"check-{kind.value}", kind)
        for kind in REQUIRED_WAVE_FIVE_REPLAY_CHECKS
    )


def bundle(
    *,
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    status: WaveFiveReproductionStatus = (
        WaveFiveReproductionStatus.INTERNAL_REPLAY_READY
    ),
    commands: tuple[WaveFiveCommandRecord, ...] = (command(),),
    digests: tuple[WaveFiveDigestRecord, ...] = required_digests(),
    checks: tuple[WaveFiveReplayCheck, ...] = required_checks(),
    gaps: tuple[WaveFiveReproductionGap, ...] = (),
    claim_boundaries: tuple[WaveFiveClaimBoundary, ...] = (
        WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
    ),
) -> WaveFiveReproducibleEvidenceBundle:
    return WaveFiveReproducibleEvidenceBundle(
        bundle_id="wave5-reproducible-bundle-001",
        title="Wave 5 reproducible evidence bundle for independent replay.",
        source_system=source_system,
        reproduction_status=status,
        protocol_ids=("wave5-external-protocol-001",),
        command_records=commands,
        digests=digests,
        replay_checks=checks,
        environment_notes=(
            "Python version, platform, package metadata, and command order captured.",
        ),
        reproduction_gaps=gaps,
        claim_boundaries=claim_boundaries,
        notes=("Internal replay is not treated as independent validation.",),
    )


def test_required_replay_checks_are_locked() -> None:
    assert required_wave_five_replay_checks() == REQUIRED_WAVE_FIVE_REPLAY_CHECKS
    assert len(REQUIRED_WAVE_FIVE_REPLAY_CHECKS) == 7
    assert WaveFiveReplayCheckKind.FAILURE_CAPTURE in REQUIRED_WAVE_FIVE_REPLAY_CHECKS


def test_external_reproduction_source_systems_are_locked() -> None:
    assert external_reproduction_source_systems() == (
        EXTERNAL_REPRODUCTION_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.INDEPENDENT_REPLICATION_LAB in (
        EXTERNAL_REPRODUCTION_SOURCE_SYSTEMS
    )
    assert WaveFiveSourceSystem.IX_COGNITION_KERNEL not in (
        EXTERNAL_REPRODUCTION_SOURCE_SYSTEMS
    )


def test_command_record_rejects_empty_command() -> None:
    with pytest.raises(ValueError, match="at least one command argument"):
        WaveFiveCommandRecord(
            command_id="command-empty",
            command=(),
            working_directory=".",
            expected_exit_code=0,
            observed_exit_code=0,
            outcome=WaveFiveCommandOutcome.PASSED,
            stdout_digest=DIGEST_A,
            stderr_digest=DIGEST_B,
            evidence_ids=("evidence-command",),
        )


def test_command_record_rejects_passed_command_with_bad_exit_code() -> None:
    with pytest.raises(ValueError, match="expected exit code"):
        command(observed_exit_code=1)


def test_command_record_rejects_failed_command_with_expected_exit_code() -> None:
    with pytest.raises(ValueError, match="Failed commands"):
        command(
            outcome=WaveFiveCommandOutcome.FAILED,
            expected_exit_code=0,
            observed_exit_code=0,
        )


def test_digest_record_rejects_malformed_sha256() -> None:
    with pytest.raises(ValueError, match="64-character"):
        digest("digest-bad", WaveFiveDigestKind.SOURCE_TREE, "bad")


def test_replay_check_reports_blocking_failure() -> None:
    failed = check(
        "check-command-replay",
        WaveFiveReplayCheckKind.COMMAND_REPLAY,
        passed=False,
    )
    non_blocking = check(
        "check-warning",
        WaveFiveReplayCheckKind.FAILURE_CAPTURE,
        passed=False,
        blocking=False,
    )

    assert failed.blocks_reproduction is True
    assert non_blocking.blocks_reproduction is False


def test_blocking_reproduction_gap_requires_evidence() -> None:
    with pytest.raises(ValueError, match="require evidence ids"):
        WaveFiveReproductionGap(
            gap_id="gap-blocking",
            severity=WaveFiveReproductionGapSeverity.BLOCKING,
            description="External replay cannot recreate required output.",
            mitigation="Record as blocked until reproduced externally.",
            evidence_ids=(),
        )


def test_bundle_rejects_missing_required_sections() -> None:
    with pytest.raises(ValueError, match="command records"):
        bundle(commands=())

    with pytest.raises(ValueError, match="digest records"):
        bundle(digests=())

    with pytest.raises(ValueError, match="replay checks"):
        bundle(checks=())


def test_bundle_rejects_missing_claim_boundary() -> None:
    with pytest.raises(ValueError, match="no-self-validation"):
        bundle(
            claim_boundaries=tuple(
                boundary
                for boundary in WAVE_FIVE_REQUIRED_CLAIM_BOUNDARIES
                if boundary is not WaveFiveClaimBoundary.NO_SELF_VALIDATION
            )
        )


def test_bundle_reports_required_coverage() -> None:
    item = bundle()

    assert item.has_required_digest_coverage is True
    assert item.has_required_replay_check_coverage is True
    assert item.missing_required_replay_checks == ()
    assert item.ready_for_external_reproduction is True
    assert item.externally_reproduced_with_boundaries is False


def test_bundle_reports_missing_replay_check_coverage() -> None:
    incomplete = bundle(checks=required_checks()[:-1])

    assert incomplete.has_required_replay_check_coverage is False
    assert incomplete.missing_required_replay_checks == (
        WaveFiveReplayCheckKind.FAILURE_CAPTURE,
    )
    assert incomplete.ready_for_external_reproduction is False


def test_bundle_blocks_when_command_failed() -> None:
    failed_command = command(
        outcome=WaveFiveCommandOutcome.FAILED,
        expected_exit_code=0,
        observed_exit_code=1,
    )
    item = bundle(
        status=WaveFiveReproductionStatus.REPRODUCTION_FAILED,
        commands=(failed_command,),
    )
    artifact = item.to_artifact_ref()

    assert item.has_failed_command is True
    assert artifact.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact.authority_state is WaveFiveAuthorityState.BLOCKED
    assert artifact.validation_status is WaveFiveValidationStatus.REJECTED


def test_bundle_blocks_when_blocking_gap_exists() -> None:
    gap = WaveFiveReproductionGap(
        gap_id="gap-blocking",
        severity=WaveFiveReproductionGapSeverity.BLOCKING,
        description="External lab cannot reproduce a required evidence digest.",
        mitigation="Preserve failed reproduction and block maturity claim.",
        evidence_ids=("evidence-gap",),
    )
    item = bundle(gaps=(gap,))
    artifact = item.to_artifact_ref()

    assert item.has_blocking_reproduction_gap is True
    assert artifact.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact.validation_status is WaveFiveValidationStatus.DISPUTED


def test_internal_ready_bundle_exports_reviewable_artifact() -> None:
    artifact = bundle().to_artifact_ref()

    assert artifact.kind is WaveFiveArtifactKind.REPRODUCIBLE_EVIDENCE_BUNDLE
    assert artifact.capability_area is WaveFiveCapabilityArea.REPRODUCIBILITY
    assert artifact.source_system is WaveFiveSourceSystem.IX_COGNITION_KERNEL
    assert artifact.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    assert artifact.validation_status is (
        WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    )
    assert artifact.ready_for_independent_review is True


def test_externally_reproduced_bundle_requires_external_source() -> None:
    with pytest.raises(ValueError, match="external source system"):
        bundle(status=WaveFiveReproductionStatus.EXTERNALLY_REPRODUCED)


def test_external_bundle_exports_external_reproduction_artifact() -> None:
    item = bundle(
        source_system=WaveFiveSourceSystem.INDEPENDENT_REPLICATION_LAB,
        status=WaveFiveReproductionStatus.EXTERNALLY_REPRODUCED,
    )
    artifact = item.to_artifact_ref()

    assert item.externally_reproduced_with_boundaries is True
    assert artifact.decision is WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
    assert artifact.validation_status is WaveFiveValidationStatus.EXTERNALLY_REPRODUCED
    assert artifact.externally_validated_with_boundaries is True


def test_failed_reproduction_status_requires_actual_failure() -> None:
    with pytest.raises(ValueError, match="failed command or gap"):
        bundle(status=WaveFiveReproductionStatus.REPRODUCTION_FAILED)


def test_bundle_collects_unique_evidence_ids() -> None:
    item = bundle()

    assert item.all_evidence_ids == (
        "evidence-command-pytest",
        "evidence-digest-output",
        "evidence-digest-source",
        "evidence-digest-tests",
        "evidence-check-clean-checkout",
        "evidence-check-command-replay",
        "evidence-check-environment-capture",
        "evidence-check-failure-capture",
        "evidence-check-output-digest",
        "evidence-check-source-fingerprint",
        "evidence-check-test-fingerprint",
    )


def test_bundle_fingerprint_is_deterministic() -> None:
    item = bundle()

    assert item.fingerprint() == item.fingerprint()
    assert len(item.fingerprint()) == 64
