import pytest

from ix_cognition_kernel.wave5_contracts import (
    WaveFiveArtifactDecision,
    WaveFiveAuthorityState,
    WaveFiveSourceSystem,
    WaveFiveValidationStatus,
)
from ix_cognition_kernel.wave5_reproducibility import (
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

DIGEST = "a" * 64
ALT_DIGEST = "b" * 64


def _command_record(
    *,
    command_id: str = "command-1",
    outcome: WaveFiveCommandOutcome = WaveFiveCommandOutcome.PASSED,
    expected_exit_code: int = 0,
    observed_exit_code: int = 0,
) -> WaveFiveCommandRecord:
    return WaveFiveCommandRecord(
        command_id=command_id,
        command=("python", "-m", "pytest"),
        working_directory=".",
        expected_exit_code=expected_exit_code,
        observed_exit_code=observed_exit_code,
        outcome=outcome,
        stdout_digest=DIGEST,
        stderr_digest=ALT_DIGEST,
        evidence_ids=(f"evidence-{command_id}",),
    )


def _digest_records() -> tuple[WaveFiveDigestRecord, ...]:
    return (
        WaveFiveDigestRecord(
            digest_id="digest-source",
            digest_kind=WaveFiveDigestKind.SOURCE_TREE,
            path="src",
            digest=DIGEST,
            evidence_ids=("evidence-source",),
        ),
        WaveFiveDigestRecord(
            digest_id="digest-tests",
            digest_kind=WaveFiveDigestKind.TEST_TREE,
            path="tests",
            digest=DIGEST,
            evidence_ids=("evidence-tests",),
        ),
        WaveFiveDigestRecord(
            digest_id="digest-output",
            digest_kind=WaveFiveDigestKind.OUTPUT_ARTIFACT,
            path="artifacts/wave5",
            digest=DIGEST,
            evidence_ids=("evidence-output",),
        ),
    )


def _replay_checks(
    *,
    passed: bool = True,
) -> tuple[WaveFiveReplayCheck, ...]:
    return tuple(
        WaveFiveReplayCheck(
            check_id=f"check-{check_kind.value}",
            check_kind=check_kind,
            description=f"Replay check for {check_kind.value}",
            passed=passed,
            evidence_ids=(f"check-evidence-{check_kind.value}",),
        )
        for check_kind in required_wave_five_replay_checks()
    )


def _bundle(
    *,
    reproduction_status: WaveFiveReproductionStatus = (
        WaveFiveReproductionStatus.NEEDS_EXTERNAL_REPRODUCTION
    ),
    source_system: WaveFiveSourceSystem = WaveFiveSourceSystem.IX_COGNITION_KERNEL,
    commands: tuple[WaveFiveCommandRecord, ...] | None = None,
    digests: tuple[WaveFiveDigestRecord, ...] | None = None,
    checks: tuple[WaveFiveReplayCheck, ...] | None = None,
    gaps: tuple[WaveFiveReproductionGap, ...] = (),
) -> WaveFiveReproducibleEvidenceBundle:
    return WaveFiveReproducibleEvidenceBundle(
        bundle_id="bundle-1",
        title="Wave 5 reproducible evidence bundle",
        source_system=source_system,
        reproduction_status=reproduction_status,
        protocol_ids=("protocol-1",),
        command_records=commands or (_command_record(),),
        digests=digests or _digest_records(),
        replay_checks=checks or _replay_checks(),
        environment_notes=("Python environment captured for replay.",),
        reproduction_gaps=gaps,
    )


def test_required_replay_checks_and_external_sources_are_locked() -> None:
    assert len(required_wave_five_replay_checks()) >= 6
    assert WaveFiveReplayCheckKind.CLEAN_CHECKOUT in required_wave_five_replay_checks()
    assert (
        WaveFiveSourceSystem.INDEPENDENT_REPLICATION_LAB
        in external_reproduction_source_systems()
    )


def test_reproducible_bundle_ready_for_external_reproduction_when_complete() -> None:
    bundle = _bundle()

    assert bundle.has_required_digest_coverage
    assert bundle.has_required_replay_check_coverage
    assert bundle.ready_for_external_reproduction
    assert not bundle.has_failed_command
    assert not bundle.has_failed_blocking_check
    assert not bundle.has_blocking_reproduction_gap

    artifact_ref = bundle.to_artifact_ref()
    assert (
        artifact_ref.decision is WaveFiveArtifactDecision.READY_FOR_INDEPENDENT_REVIEW
    )
    assert artifact_ref.authority_state is WaveFiveAuthorityState.HUMAN_REVIEW_REQUIRED
    assert (
        artifact_ref.validation_status
        is WaveFiveValidationStatus.UNDER_INDEPENDENT_REVIEW
    )
    assert artifact_ref.evidence_ids == bundle.all_evidence_ids


def test_reproducible_bundle_reports_missing_replay_check() -> None:
    checks = tuple(
        check
        for check in _replay_checks()
        if check.check_kind is not WaveFiveReplayCheckKind.CLEAN_CHECKOUT
    )

    bundle = _bundle(checks=checks)

    assert bundle.missing_required_replay_checks == (
        WaveFiveReplayCheckKind.CLEAN_CHECKOUT,
    )
    assert not bundle.has_required_replay_check_coverage
    assert not bundle.ready_for_external_reproduction


def test_reproducible_bundle_blocks_failed_command() -> None:
    failed_command = _command_record(
        outcome=WaveFiveCommandOutcome.FAILED,
        expected_exit_code=0,
        observed_exit_code=1,
    )
    bundle = _bundle(
        reproduction_status=WaveFiveReproductionStatus.REPRODUCTION_FAILED,
        commands=(failed_command,),
    )

    assert bundle.has_failed_command
    assert not bundle.ready_for_external_reproduction

    artifact_ref = bundle.to_artifact_ref()
    assert artifact_ref.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact_ref.authority_state is WaveFiveAuthorityState.BLOCKED
    assert artifact_ref.validation_status is WaveFiveValidationStatus.REJECTED


def test_reproducible_bundle_blocks_failed_replay_check() -> None:
    bundle = _bundle(checks=_replay_checks(passed=False))

    assert bundle.has_failed_blocking_check
    assert not bundle.ready_for_external_reproduction

    artifact_ref = bundle.to_artifact_ref()
    assert artifact_ref.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact_ref.validation_status is WaveFiveValidationStatus.REJECTED


def test_reproducible_bundle_blocks_reproduction_gap() -> None:
    gap = WaveFiveReproductionGap(
        gap_id="gap-1",
        severity=WaveFiveReproductionGapSeverity.BLOCKING,
        description="External replay environment is not reproducible.",
        mitigation="Capture the missing environment lock before review.",
        evidence_ids=("gap-evidence-1",),
    )
    bundle = _bundle(gaps=(gap,))

    assert bundle.has_blocking_reproduction_gap
    assert not bundle.ready_for_external_reproduction

    artifact_ref = bundle.to_artifact_ref()
    assert artifact_ref.decision is WaveFiveArtifactDecision.BLOCKED
    assert artifact_ref.validation_status is WaveFiveValidationStatus.DISPUTED


def test_externally_reproduced_bundle_requires_external_source() -> None:
    with pytest.raises(ValueError, match="external source system"):
        _bundle(
            reproduction_status=WaveFiveReproductionStatus.EXTERNALLY_REPRODUCED,
            source_system=WaveFiveSourceSystem.IX_COGNITION_KERNEL,
        )


def test_externally_reproduced_bundle_exports_reviewed_artifact() -> None:
    bundle = _bundle(
        reproduction_status=WaveFiveReproductionStatus.EXTERNALLY_REPRODUCED,
        source_system=WaveFiveSourceSystem.INDEPENDENT_REPLICATION_LAB,
    )

    assert bundle.externally_reproduced_with_boundaries
    artifact_ref = bundle.to_artifact_ref()
    assert artifact_ref.decision is WaveFiveArtifactDecision.EXTERNALLY_REVIEWED
    assert (
        artifact_ref.validation_status is WaveFiveValidationStatus.EXTERNALLY_REPRODUCED
    )


def test_command_record_rejects_passed_command_with_wrong_exit_code() -> None:
    with pytest.raises(ValueError, match="Passed commands"):
        _command_record(
            outcome=WaveFiveCommandOutcome.PASSED,
            expected_exit_code=0,
            observed_exit_code=1,
        )


def test_digest_record_requires_sha256_shape() -> None:
    with pytest.raises(ValueError, match="64-character SHA-256"):
        WaveFiveDigestRecord(
            digest_id="digest-invalid",
            digest_kind=WaveFiveDigestKind.SOURCE_TREE,
            path="src",
            digest="not-a-digest",
            evidence_ids=("evidence-invalid",),
        )
