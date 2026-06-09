from typing import Any

import pytest

from ix_cognition_kernel.wave6_falsification import WaveSixFalsificationProbeKind
from ix_cognition_kernel.wave6_gap_register import (
    WaveSixGapKind,
    WaveSixGapSeverity,
    WaveSixGapState,
)
from ix_cognition_kernel.wave6_ix_handoff import (
    CANONICAL_IX_COGNITION_OBLIGATIONS,
    IX_COGNITION_CONTRACT_SCHEMA,
    IX_COGNITION_KERNEL_TARGET,
    IX_KERNEL_HANDOFF_TYPE,
    IX_KERNEL_HANDOFF_PAYLOAD_SCHEMA_VERSION,
    IX_METADATA_ONLY_RUNTIME_SEMANTICS,
    canonical_ix_cognition_obligation_ids,
    load_ix_cognition_handoff,
)
from ix_cognition_kernel.wave6_ix_obligation_pressure import (
    WAVE_SIX_IX_OBLIGATION_PRESSURE_ENGINE_ID,
    WaveSixIxObligationPressureBundle,
    WaveSixIxObligationPressureDecision,
    build_ix_obligation_pressure_bundle,
)


def _source(line: int = 1) -> dict[str, Any]:
    return {
        "column": 5,
        "filename": "examples/cognitionkernel_wave6_contract.ix",
        "line": line,
    }


def _obligation_payload(index: int, obligation_id: str) -> dict[str, Any]:
    definition = next(
        definition
        for definition in CANONICAL_IX_COGNITION_OBLIGATIONS
        if definition.obligation_id == obligation_id
    )
    return {
        "canonical": True,
        "canonical_definition": definition.canonical_payload(),
        "evidence_required": [definition.evidence_artifacts[0]],
        "falsify_if": [definition.falsification_conditions[0]],
        "id": obligation_id,
        "source": _source(line=8 + (index * 5)),
    }


def _canonical_payload() -> dict[str, Any]:
    return {
        "handoff_type": IX_KERNEL_HANDOFF_TYPE,
        "packages": [
            {
                "attempt": "wave6_measured_cognition",
                "claim_boundaries": [
                    "Research candidate only, evaluation use only, not deployment",
                ],
                "execution_authority": "none",
                "human_approval_required": [
                    "Human review required before any advancement or public claim",
                ],
                "human_authority_required": True,
                "non_goals": [
                    "Do not claim AGI, certify AGI, or allow system self-approval",
                ],
                "obligations": [
                    _obligation_payload(index, obligation_id)
                    for index, obligation_id in enumerate(
                        canonical_ix_cognition_obligation_ids()
                    )
                ],
                "purpose": [
                    "Define a governed IX-CognitionKernel Wave 6 contract for "
                    "measured reality correction",
                ],
                "runtime_semantics": IX_METADATA_ONLY_RUNTIME_SEMANTICS,
                "schema": IX_COGNITION_CONTRACT_SCHEMA,
                "self_certification_allowed": False,
                "source": _source(line=6),
                "target": IX_COGNITION_KERNEL_TARGET,
            }
        ],
        "runtime_semantics": IX_METADATA_ONLY_RUNTIME_SEMANTICS,
        "schema_version": IX_KERNEL_HANDOFF_PAYLOAD_SCHEMA_VERSION,
    }


def _pressure_bundle() -> WaveSixIxObligationPressureBundle:
    package = load_ix_cognition_handoff(_canonical_payload()).packages[0]
    return build_ix_obligation_pressure_bundle(package)


def test_ix_obligation_pressure_builds_one_gap_and_probe_per_obligation() -> None:
    bundle = _pressure_bundle()

    assert bundle.attempt == "wave6_measured_cognition"
    assert bundle.generated_by_engine_id == WAVE_SIX_IX_OBLIGATION_PRESSURE_ENGINE_ID
    assert bundle.obligation_ids == canonical_ix_cognition_obligation_ids()
    assert len(bundle.pressures) == len(canonical_ix_cognition_obligation_ids())
    assert len(bundle.evidence_gap_ids) == len(canonical_ix_cognition_obligation_ids())
    assert len(bundle.falsification_probe_ids) == len(
        canonical_ix_cognition_obligation_ids()
    )
    assert bundle.source_evidence_id == (
        "ix-kernel-handoff:wave6_measured_cognition:kernel-handoff-json"
    )
    assert bundle.contract_artifact_id == "ix-handoff-artifact-wave6_measured_cognition"
    assert bundle.decision is (
        WaveSixIxObligationPressureDecision.BLOCKED_BY_MISSING_OBLIGATION_EVIDENCE
    )
    assert not bundle.ready_for_bounded_review
    assert bundle.blocking_gap_ids == bundle.evidence_gap_ids
    assert len(bundle.fingerprint()) == 64
    assert bundle.fingerprint() == bundle.fingerprint()


def test_ix_obligation_pressure_keeps_imported_gaps_open_and_blocking() -> None:
    bundle = _pressure_bundle()
    pressure = bundle.pressures[0]

    assert pressure.obligation_id == "purpose_discipline"
    assert pressure.evidence_gap.state is WaveSixGapState.OPEN
    assert pressure.evidence_gap.kind is WaveSixGapKind.REQUIRED_EVIDENCE_GAP
    assert pressure.evidence_gap.severity is WaveSixGapSeverity.MAJOR
    assert pressure.evidence_gap.requires_follow_up
    assert pressure.evidence_gap.blocks_review
    assert pressure.evidence_gap.required_evidence_ids == ("attempt_purpose_record",)
    assert pressure.evidence_gap.evidence_ids == ()
    assert pressure.falsification_gate_ids == ("purpose_missing",)
    assert pressure.falsification_probe.probe_kind is (
        WaveSixFalsificationProbeKind.NEGATIVE_CONTROL
    )
    assert not pressure.falsification_probe.allows_autonomous_execution
    assert not pressure.falsification_probe.claims_agi
    assert pressure.falsification_probe.requires_human_review


def test_ix_obligation_pressure_marks_authority_obligation_critical() -> None:
    bundle = _pressure_bundle()
    pressure_by_id = {pressure.obligation_id: pressure for pressure in bundle.pressures}

    pressure = pressure_by_id["human_authority"]

    assert pressure.evidence_gap.kind is WaveSixGapKind.HUMAN_REVIEW_GAP
    assert pressure.evidence_gap.severity is WaveSixGapSeverity.CRITICAL
    assert pressure.evidence_gap.claim_boundary_impact
    assert pressure.falsification_probe.probe_kind is (
        WaveSixFalsificationProbeKind.SAFETY_GATE_PROBE
    )


def test_ix_obligation_pressure_maps_transfer_and_novelty_to_specific_probes() -> None:
    bundle = _pressure_bundle()
    pressure_by_id = {pressure.obligation_id: pressure for pressure in bundle.pressures}

    transfer = pressure_by_id["cross_domain_transfer_probe"]
    novelty = pressure_by_id["novelty_generality_pressure"]

    assert transfer.evidence_gap.kind is WaveSixGapKind.TRANSFER_EVIDENCE_GAP
    assert transfer.falsification_probe.probe_kind is (
        WaveSixFalsificationProbeKind.TRANSFER_COUNTEREXAMPLE
    )
    assert novelty.evidence_gap.kind is WaveSixGapKind.TRANSFER_EVIDENCE_GAP
    assert novelty.falsification_probe.probe_kind is (
        WaveSixFalsificationProbeKind.NOVELTY_REVERSAL
    )


def test_ix_obligation_pressure_rejects_missing_pressure_coverage() -> None:
    bundle = _pressure_bundle()

    with pytest.raises(ValueError, match="Missing IX obligation pressure"):
        WaveSixIxObligationPressureBundle(
            attempt=bundle.attempt,
            source_package_fingerprint=bundle.source_package_fingerprint,
            source_evidence_id=bundle.source_evidence_id,
            contract_artifact_id=bundle.contract_artifact_id,
            pressures=bundle.pressures[:-1],
        )


def test_ix_obligation_pressure_rejects_tampered_artifact_link() -> None:
    bundle = _pressure_bundle()

    with pytest.raises(ValueError, match="artifact ids must match"):
        WaveSixIxObligationPressureBundle(
            attempt=bundle.attempt,
            source_package_fingerprint=bundle.source_package_fingerprint,
            source_evidence_id=bundle.source_evidence_id,
            contract_artifact_id="different-artifact",
            pressures=bundle.pressures,
        )
