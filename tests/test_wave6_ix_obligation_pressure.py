from __future__ import annotations

from typing import Any

import pytest

from ix_cognition_kernel.wave6_falsification import WaveSixFalsificationProbeKind
from ix_cognition_kernel.wave6_gap_register import (
    WaveSixGapDisposition,
    WaveSixGapSeverity,
    WaveSixGapState,
)
from ix_cognition_kernel.wave6_ix_handoff import (
    CANONICAL_IX_COGNITION_OBLIGATIONS,
    WaveSixIxHandoffPackage,
    canonical_ix_cognition_obligation_ids,
    load_ix_cognition_handoff,
)
from ix_cognition_kernel.wave6_ix_obligation_pressure import (
    WAVE_SIX_IX_OBLIGATION_PRESSURE_ENGINE_ID,
    WaveSixIxObligationPressureBundle,
    WaveSixIxObligationPressureDecision,
    WaveSixIxObligationPressureStatus,
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
        "evidence_required": list(definition.evidence_artifacts),
        "falsify_if": list(definition.falsification_conditions),
        "id": obligation_id,
        "source": _source(line=8 + (index * 5)),
    }


def _canonical_payload() -> dict[str, Any]:
    return {
        "handoff_type": "ix.cognitionkernel.handoff",
        "packages": [
            {
                "attempt": "wave6_measured_cognition",
                "claim_boundaries": [
                    "measured system-level cognition only",
                    "not an AGI claim",
                    "human and independent review required",
                ],
                "execution_authority": "none",
                "human_approval_required": ["human authority required"],
                "human_authority_required": True,
                "non_goals": ["do not claim AGI", "do not self-certify"],
                "obligations": [
                    _obligation_payload(index, obligation_id)
                    for index, obligation_id in enumerate(
                        canonical_ix_cognition_obligation_ids()
                    )
                ],
                "purpose": ["test measured system-level cognition"],
                "runtime_semantics": "metadata_only_not_executed",
                "schema": "ix.cognition.contract.v1",
                "self_certification_allowed": False,
                "source": _source(line=6),
                "target": "IX-CognitionKernel",
            }
        ],
        "runtime_semantics": "metadata_only_not_executed",
        "schema_version": "1.0",
    }


def _ix_package() -> WaveSixIxHandoffPackage:
    return load_ix_cognition_handoff(_canonical_payload()).packages[0]


def test_ix_obligation_pressure_builds_one_pressure_per_canonical_obligation() -> None:
    package = _ix_package()

    bundle = build_ix_obligation_pressure_bundle(package)

    assert bundle.attempt == "wave6_measured_cognition"
    assert bundle.source_package_fingerprint == package.fingerprint()
    assert bundle.source_evidence_id == package.ix_evidence_id
    assert bundle.contract_artifact_id == (
        "ix-handoff-artifact-wave6_measured_cognition"
    )
    assert bundle.generated_by_engine_id == (
        WAVE_SIX_IX_OBLIGATION_PRESSURE_ENGINE_ID
    )
    assert bundle.obligation_ids == canonical_ix_cognition_obligation_ids()
    assert len(bundle.pressures) == len(canonical_ix_cognition_obligation_ids())


def test_ix_obligation_pressure_starts_fail_closed_with_blocking_gaps() -> None:
    bundle = build_ix_obligation_pressure_bundle(_ix_package())

    assert bundle.decision is (
        WaveSixIxObligationPressureDecision.BLOCKED_BY_MISSING_OBLIGATION_EVIDENCE
    )
    assert not bundle.ready_for_bounded_review
    assert bundle.blocking_gap_ids == bundle.evidence_gap_ids
    assert len(bundle.blocking_gap_ids) == len(canonical_ix_cognition_obligation_ids())

    first_pressure = bundle.pressures[0]
    assert first_pressure.status is WaveSixIxObligationPressureStatus.BLOCKING
    assert first_pressure.evidence_gap.state is WaveSixGapState.OPEN
    assert first_pressure.evidence_gap.disposition is (
        WaveSixGapDisposition.REQUIRE_EVIDENCE
    )
    assert first_pressure.evidence_gap.severity is WaveSixGapSeverity.MAJOR
    assert first_pressure.evidence_gap.blocks_review
    assert first_pressure.evidence_gap.blocks_bounded_review
    assert first_pressure.evidence_gap.requires_follow_up


def test_ix_obligation_pressure_uses_critical_severity_for_safety_obligations() -> None:
    bundle = build_ix_obligation_pressure_bundle(_ix_package())
    severity_by_obligation = {
        pressure.obligation_id: pressure.evidence_gap.severity
        for pressure in bundle.pressures
    }

    assert severity_by_obligation["claim_boundary_discipline"] is (
        WaveSixGapSeverity.CRITICAL
    )
    assert severity_by_obligation["human_authority"] is WaveSixGapSeverity.CRITICAL
    assert severity_by_obligation["no_self_certification"] is (
        WaveSixGapSeverity.CRITICAL
    )
    assert severity_by_obligation["falsification_ledger"] is (
        WaveSixGapSeverity.CRITICAL
    )
    assert severity_by_obligation["independent_replay_review"] is (
        WaveSixGapSeverity.CRITICAL
    )
    assert severity_by_obligation["kernel_handoff_package"] is (
        WaveSixGapSeverity.CRITICAL
    )


def test_ix_obligation_pressure_maps_probe_kinds_to_obligation_families() -> None:
    bundle = build_ix_obligation_pressure_bundle(_ix_package())
    probe_kind_by_obligation = {
        pressure.obligation_id: pressure.falsification_probe.probe_kind
        for pressure in bundle.pressures
    }

    assert probe_kind_by_obligation["cross_domain_transfer_probe"] is (
        WaveSixFalsificationProbeKind.TRANSFER_COUNTEREXAMPLE
    )
    assert probe_kind_by_obligation["novelty_generality_pressure"] is (
        WaveSixFalsificationProbeKind.NOVELTY_REVERSAL
    )
    assert probe_kind_by_obligation["contradiction_handling"] is (
        WaveSixFalsificationProbeKind.CONTRADICTION_PROBE
    )
    assert probe_kind_by_obligation["claim_boundary_discipline"] is (
        WaveSixFalsificationProbeKind.SAFETY_GATE_PROBE
    )
    assert probe_kind_by_obligation["future_reasoning_change"] is (
        WaveSixFalsificationProbeKind.REGRESSION_PROBE
    )
    assert probe_kind_by_obligation["prediction_before_trial"] is (
        WaveSixFalsificationProbeKind.NEGATIVE_CONTROL
    )


def test_ix_obligation_pressure_payload_is_deterministic_and_reviewable() -> None:
    package = _ix_package()
    bundle = build_ix_obligation_pressure_bundle(package)

    payload = bundle.canonical_payload()

    assert payload["schema_version"] == (
        "ix-cognition-kernel-wave6-ix-obligation-pressure-bundle-v1"
    )
    assert payload["attempt"] == "wave6_measured_cognition"
    assert payload["source_package_fingerprint"] == package.fingerprint()
    assert payload["ready_for_bounded_review"] is False
    assert payload["decision"] == "blocked-by-missing-obligation-evidence"
    assert payload["obligation_ids"] == list(canonical_ix_cognition_obligation_ids())
    assert payload["blocking_gap_ids"] == list(bundle.blocking_gap_ids)
    assert payload["falsification_probe_ids"] == list(bundle.falsification_probe_ids)
    assert len(bundle.fingerprint()) == 64
    assert bundle.fingerprint() == bundle.fingerprint()


def test_ix_obligation_pressure_links_each_gap_and_probe_to_source_evidence() -> None:
    package = _ix_package()
    bundle = build_ix_obligation_pressure_bundle(package)

    for pressure in bundle.pressures:
        assert pressure.evidence_gap.required_evidence_ids == (
            pressure.required_evidence_ids
        )
        assert pressure.evidence_gap.evidence_ids == ()
        assert pressure.falsification_probe.evidence_ids == (package.ix_evidence_id,)
        assert not pressure.falsification_probe.allows_autonomous_execution
        assert not pressure.falsification_probe.claims_agi
        assert pressure.falsification_probe.requires_human_review


def test_ix_obligation_pressure_rejects_missing_pressure_coverage() -> None:
    package = _ix_package()
    bundle = build_ix_obligation_pressure_bundle(package)

    with pytest.raises(ValueError, match="Missing IX obligation pressure"):
        WaveSixIxObligationPressureBundle(
            attempt=bundle.attempt,
            source_package_fingerprint=bundle.source_package_fingerprint,
            source_evidence_id=bundle.source_evidence_id,
            contract_artifact_id=bundle.contract_artifact_id,
            pressures=bundle.pressures[:-1],
        )


def test_ix_obligation_pressure_rejects_handoff_engine_identity() -> None:
    package = _ix_package()
    bundle = build_ix_obligation_pressure_bundle(package)

    with pytest.raises(ValueError, match="own engine id"):
        WaveSixIxObligationPressureBundle(
            attempt=bundle.attempt,
            source_package_fingerprint=bundle.source_package_fingerprint,
            source_evidence_id=bundle.source_evidence_id,
            contract_artifact_id=bundle.contract_artifact_id,
            pressures=bundle.pressures,
            generated_by_engine_id="wave6-ix-handoff-ingestion-engine",
        )
