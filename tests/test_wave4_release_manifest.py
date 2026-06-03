from dataclasses import dataclass

import pytest

from ix_cognition_kernel.wave4_completion_receipt import (
    WaveFourCompletionReceiptStatus,
)
from ix_cognition_kernel.wave4_contracts import (
    WaveFourArtifactKind,
    WaveFourAuthorityState,
    WaveFourCapabilityArea,
)
from ix_cognition_kernel.wave4_release_manifest import (
    REQUIRED_WAVE_FOUR_RELEASE_COMPONENT_KINDS,
    REQUIRED_WAVE_FOUR_VALIDATION_COMMAND_KINDS,
    WaveFourReleaseComponent,
    WaveFourReleaseComponentKind,
    WaveFourReleaseManifest,
    WaveFourReleaseManifestDecision,
    WaveFourReleaseManifestStatus,
    WaveFourValidationCommandKind,
    WaveFourValidationCommandRecord,
    WaveFourValidationResult,
    build_wave_four_release_manifest,
    passed_validation_command,
    release_component,
)


@dataclass(frozen=True)
class FakeReceipt:
    receipt_id: str = "completion-receipt-001"
    artifact_id: str = "artifact:completion-receipt-001"
    status: WaveFourCompletionReceiptStatus = (
        WaveFourCompletionReceiptStatus.READY_FOR_WAVE_FOUR_RECORD
    )
    receipt_digest: str = "b" * 64
    all_evidence_ids: tuple[str, ...] = (
        "evidence:completion-receipt",
        "evidence:review-docket",
    )
    readiness_gaps: tuple[str, ...] = ()
    blocking_gaps: tuple[str, ...] = ()
    permits_automatic_execution: bool = False
    permits_automatic_promotion: bool = False
    claims_agi: bool = False
    independently_validated: bool = False
    production_ready: bool = False


def ready_receipt() -> FakeReceipt:
    return FakeReceipt()


def validation_commands() -> tuple[WaveFourValidationCommandRecord, ...]:
    return (
        passed_validation_command(
            command_id="validation:pytest",
            command_kind=WaveFourValidationCommandKind.PYTEST,
            command="PYTHONPATH=src pytest -q",
            expected_gate="all tests pass",
            evidence_id="evidence:validation:pytest",
        ),
        passed_validation_command(
            command_id="validation:ruff",
            command_kind=WaveFourValidationCommandKind.RUFF,
            command="ruff check .",
            expected_gate="lint clean",
            evidence_id="evidence:validation:ruff",
        ),
        passed_validation_command(
            command_id="validation:mypy",
            command_kind=WaveFourValidationCommandKind.MYPY,
            command="mypy src tests",
            expected_gate="type checks pass",
            evidence_id="evidence:validation:mypy",
        ),
        passed_validation_command(
            command_id="validation:py-compile",
            command_kind=WaveFourValidationCommandKind.PY_COMPILE,
            command="python -m compileall -q src tests",
            expected_gate="all Python files compile",
            evidence_id="evidence:validation:py-compile",
        ),
        passed_validation_command(
            command_id="validation:line-length",
            command_kind=WaveFourValidationCommandKind.LINE_LENGTH_SCAN,
            command="line-length scan for files over 88 characters",
            expected_gate="no long lines in delivered Wave 4 files",
            evidence_id="evidence:validation:line-length",
        ),
    )


def ready_manifest() -> WaveFourReleaseManifest:
    return build_wave_four_release_manifest(
        manifest_id="release-manifest-001",
        completion_receipt=ready_receipt(),
        validation_commands=validation_commands(),
        scenario_ids=("worldtwin:release-manifest",),
        blackfox_receipt_ids=("blackfox:release-manifest",),
    )


def test_required_release_component_and_validation_kinds_are_locked() -> None:
    assert REQUIRED_WAVE_FOUR_RELEASE_COMPONENT_KINDS == (
        WaveFourReleaseComponentKind.SOURCE_MODULE,
        WaveFourReleaseComponentKind.TEST_MODULE,
        WaveFourReleaseComponentKind.VALIDATION_COMMAND,
        WaveFourReleaseComponentKind.COMPLETION_RECEIPT,
        WaveFourReleaseComponentKind.REVIEW_DOCKET,
        WaveFourReleaseComponentKind.README_PENDING,
    )
    assert REQUIRED_WAVE_FOUR_VALIDATION_COMMAND_KINDS == (
        WaveFourValidationCommandKind.PYTEST,
        WaveFourValidationCommandKind.RUFF,
        WaveFourValidationCommandKind.MYPY,
        WaveFourValidationCommandKind.PY_COMPILE,
        WaveFourValidationCommandKind.LINE_LENGTH_SCAN,
    )


def test_release_component_requires_evidence_when_required() -> None:
    with pytest.raises(ValueError, match="required .* require evidence ids"):
        WaveFourReleaseComponent(
            component_id="component:invalid",
            component_kind=WaveFourReleaseComponentKind.SOURCE_MODULE,
            path="src/ix_cognition_kernel/invalid.py",
            summary="Invalid component.",
            evidence_ids=(),
        )


def test_validation_command_requires_evidence_and_failure_text() -> None:
    with pytest.raises(ValueError, match="validation command records require evidence"):
        WaveFourValidationCommandRecord(
            command_id="validation:invalid",
            command_kind=WaveFourValidationCommandKind.PYTEST,
            command="pytest",
            expected_gate="tests pass",
            result=WaveFourValidationResult.PASSED,
            evidence_ids=(),
        )

    with pytest.raises(ValueError, match="require failure text"):
        WaveFourValidationCommandRecord(
            command_id="validation:failed",
            command_kind=WaveFourValidationCommandKind.PYTEST,
            command="pytest",
            expected_gate="tests pass",
            result=WaveFourValidationResult.FAILED,
            evidence_ids=("evidence:validation:failed",),
        )


def test_ready_release_manifest_records_closeout_without_overclaim() -> None:
    manifest = ready_manifest()

    assert manifest.status is WaveFourReleaseManifestStatus.READY_FOR_CLOSEOUT
    assert manifest.decision is WaveFourReleaseManifestDecision.RECORD_CLOSEOUT
    assert manifest.ready_for_closeout is True
    assert manifest.missing_required_component_kinds == ()
    assert manifest.missing_required_validation_command_kinds == ()
    assert manifest.failed_command_ids == ()
    assert manifest.not_run_command_ids == ()
    assert manifest.readiness_gaps == ()
    assert manifest.blocking_gaps == ()
    assert manifest.permits_automatic_execution is False
    assert manifest.permits_automatic_promotion is False
    assert manifest.claims_agi is False
    assert manifest.independently_validated is False
    assert manifest.production_ready is False
    assert len(manifest.release_digest) == 64
    assert "README remains final documentation step" in manifest.review_summary


def test_manifest_holds_for_missing_component_coverage() -> None:
    component = release_component(
        component_id="component:source-only",
        component_kind=WaveFourReleaseComponentKind.SOURCE_MODULE,
        path="src/ix_cognition_kernel/wave4_release_manifest.py",
        summary="Only source coverage is present.",
        evidence_id="evidence:source-only",
    )
    manifest = WaveFourReleaseManifest(
        manifest_id="release-manifest-missing-components",
        completion_receipt=ready_receipt(),
        components=(component,),
        validation_commands=validation_commands(),
        scenario_ids=("worldtwin:release-manifest",),
        blackfox_receipt_ids=("blackfox:release-manifest",),
    )

    assert manifest.status is WaveFourReleaseManifestStatus.NEEDS_EVIDENCE
    assert WaveFourReleaseComponentKind.TEST_MODULE in (
        manifest.missing_required_component_kinds
    )
    assert "missing release component coverage" in manifest.readiness_gaps[0]


def test_manifest_holds_for_not_run_validation_command() -> None:
    commands = (
        *validation_commands()[:-1],
        WaveFourValidationCommandRecord(
            command_id="validation:line-length",
            command_kind=WaveFourValidationCommandKind.LINE_LENGTH_SCAN,
            command="line-length scan for files over 88 characters",
            expected_gate="no long lines",
            result=WaveFourValidationResult.NOT_RUN,
            evidence_ids=("evidence:validation:line-length",),
        ),
    )
    manifest = build_wave_four_release_manifest(
        manifest_id="release-manifest-not-run",
        completion_receipt=ready_receipt(),
        validation_commands=commands,
        scenario_ids=("worldtwin:release-manifest",),
        blackfox_receipt_ids=("blackfox:release-manifest",),
    )

    assert manifest.status is WaveFourReleaseManifestStatus.NEEDS_EVIDENCE
    assert manifest.not_run_command_ids == ("validation:line-length",)
    assert "validation:line-length was not run" in manifest.readiness_gaps


def test_manifest_needs_repair_for_failed_validation_command() -> None:
    commands = (
        *validation_commands()[:-1],
        WaveFourValidationCommandRecord(
            command_id="validation:line-length",
            command_kind=WaveFourValidationCommandKind.LINE_LENGTH_SCAN,
            command="line-length scan for files over 88 characters",
            expected_gate="no long lines",
            result=WaveFourValidationResult.FAILED,
            evidence_ids=("evidence:validation:line-length",),
            failure_summary="one delivered line exceeded the closeout limit",
        ),
    )
    manifest = build_wave_four_release_manifest(
        manifest_id="release-manifest-failed-command",
        completion_receipt=ready_receipt(),
        validation_commands=commands,
        scenario_ids=("worldtwin:release-manifest",),
        blackfox_receipt_ids=("blackfox:release-manifest",),
    )

    assert manifest.status is WaveFourReleaseManifestStatus.NEEDS_REPAIR
    assert manifest.decision is WaveFourReleaseManifestDecision.HOLD_FOR_REPAIR
    assert manifest.failed_command_ids == ("validation:line-length",)


def test_manifest_needs_repair_when_completion_receipt_needs_repair() -> None:
    manifest = build_wave_four_release_manifest(
        manifest_id="release-manifest-repair",
        completion_receipt=FakeReceipt(
            status=WaveFourCompletionReceiptStatus.NEEDS_REPAIR,
            readiness_gaps=("completion receipt repair required",),
        ),
        validation_commands=validation_commands(),
        scenario_ids=("worldtwin:release-manifest",),
        blackfox_receipt_ids=("blackfox:release-manifest",),
    )

    assert manifest.status is WaveFourReleaseManifestStatus.NEEDS_REPAIR
    assert "completion receipt repair required" in manifest.readiness_gaps


def test_manifest_blocks_when_completion_receipt_blocks() -> None:
    manifest = build_wave_four_release_manifest(
        manifest_id="release-manifest-blocked",
        completion_receipt=FakeReceipt(
            status=WaveFourCompletionReceiptStatus.BLOCKED,
            blocking_gaps=("completion receipt blocked",),
        ),
        validation_commands=validation_commands(),
        scenario_ids=("worldtwin:release-manifest",),
        blackfox_receipt_ids=("blackfox:release-manifest",),
    )

    assert manifest.status is WaveFourReleaseManifestStatus.BLOCKED
    assert manifest.decision is WaveFourReleaseManifestDecision.BLOCK_CLOSEOUT
    assert manifest.blocking_gaps == ("completion receipt blocked",)


def test_manifest_reports_missing_scenarios_and_receipts() -> None:
    manifest = build_wave_four_release_manifest(
        manifest_id="release-manifest-context-gaps",
        completion_receipt=ready_receipt(),
        validation_commands=validation_commands(),
        scenario_ids=(),
        blackfox_receipt_ids=(),
    )

    assert manifest.status is WaveFourReleaseManifestStatus.NEEDS_EVIDENCE
    assert "release-manifest-context-gaps has no WorldTwin scenario ids" in (
        manifest.readiness_gaps
    )
    assert "release-manifest-context-gaps has no BlackFox receipt ids" in (
        manifest.readiness_gaps
    )


def test_manifest_rejects_execution_promotion_agi_validation_and_production() -> None:
    kwargs = {
        "manifest_id": "invalid-manifest",
        "completion_receipt": ready_receipt(),
        "components": ready_manifest().components,
        "validation_commands": validation_commands(),
        "scenario_ids": ("worldtwin:release-manifest",),
        "blackfox_receipt_ids": ("blackfox:release-manifest",),
    }

    with pytest.raises(ValueError, match="cannot permit execution"):
        WaveFourReleaseManifest(**kwargs, permits_automatic_execution=True)

    with pytest.raises(ValueError, match="cannot permit promotion"):
        WaveFourReleaseManifest(**kwargs, permits_automatic_promotion=True)

    with pytest.raises(ValueError, match="cannot claim AGI"):
        WaveFourReleaseManifest(**kwargs, claims_agi=True)

    with pytest.raises(ValueError, match="cannot claim independent validation"):
        WaveFourReleaseManifest(**kwargs, independently_validated=True)

    with pytest.raises(ValueError, match="cannot claim production readiness"):
        WaveFourReleaseManifest(**kwargs, production_ready=True)


def test_manifest_converts_to_readiness_artifact_and_bundle() -> None:
    manifest = ready_manifest()
    artifact = manifest.to_artifact_ref()
    bundle = manifest.to_artifact_bundle()

    assert artifact.kind is WaveFourArtifactKind.READINESS_SNAPSHOT
    assert artifact.capability_area is WaveFourCapabilityArea.AUDIT_TRAIL
    assert artifact.ready_for_controlled_review is True
    assert artifact.allowed_for_automatic_execution is False
    assert artifact.claims_agi is False
    assert bundle.has_required_kind_coverage is True
    assert bundle.has_required_capability_coverage is True
    assert bundle.ready_for_controlled_review_artifact_ids == (artifact.artifact_id,)


def test_manifest_fingerprint_is_deterministic_despite_input_order() -> None:
    first = ready_manifest()
    second = WaveFourReleaseManifest(
        manifest_id="release-manifest-001",
        completion_receipt=ready_receipt(),
        components=tuple(reversed(first.components)),
        validation_commands=tuple(reversed(first.validation_commands)),
        scenario_ids=("worldtwin:release-manifest",),
        blackfox_receipt_ids=("blackfox:release-manifest",),
    )

    assert first.fingerprint() == second.fingerprint()
    assert len(first.fingerprint()) == 64
