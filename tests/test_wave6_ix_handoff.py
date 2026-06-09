import copy
from typing import Any

import pytest

from ix_cognition_kernel.wave6_contracts import (
    WaveSixArtifactKind,
    WaveSixDecisionState,
    WaveSixLoopStage,
    WaveSixSourceSystem,
)
from ix_cognition_kernel.wave6_ix_handoff import (
    CANONICAL_IX_COGNITION_OBLIGATIONS,
    IX_COGNITION_CONTRACT_SCHEMA,
    IX_COGNITION_KERNEL_TARGET,
    IX_KERNEL_HANDOFF_TYPE,
    IX_KERNEL_HANDOFF_PAYLOAD_SCHEMA_VERSION,
    IX_METADATA_ONLY_RUNTIME_SEMANTICS,
    WAVE_SIX_IX_HANDOFF_ENGINE_ID,
    canonical_ix_cognition_obligation_ids,
    load_ix_cognition_handoff,
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


def test_ix_handoff_imports_canonical_metadata_only_contract() -> None:
    bundle = load_ix_cognition_handoff(_canonical_payload())

    assert bundle.package_count == 1
    assert bundle.obligation_count == len(canonical_ix_cognition_obligation_ids())
    assert bundle.fingerprint() == bundle.fingerprint()
    assert len(bundle.fingerprint()) == 64

    package = bundle.packages[0]
    assert package.attempt == "wave6_measured_cognition"
    assert package.target == IX_COGNITION_KERNEL_TARGET
    assert package.schema == IX_COGNITION_CONTRACT_SCHEMA
    assert package.runtime_semantics == IX_METADATA_ONLY_RUNTIME_SEMANTICS
    assert package.execution_authority == "none"
    assert not package.self_certification_allowed
    assert package.human_authority_required
    assert package.obligation_ids == canonical_ix_cognition_obligation_ids()
    assert "attempt_purpose_record" in package.required_evidence_ids
    assert "kernel_handoff_missing" in package.falsification_gate_ids


def test_ix_handoff_converts_to_non_promoting_wave6_contract_artifact() -> None:
    bundle = load_ix_cognition_handoff(_canonical_payload())

    artifact = bundle.contract_artifacts[0]

    assert artifact.artifact_id == "ix-handoff-artifact-wave6_measured_cognition"
    assert artifact.kind is WaveSixArtifactKind.MASTER_LOOP_CONTRACT
    assert artifact.source_system is WaveSixSourceSystem.IX_MAIN
    assert artifact.loop_stages == (
        WaveSixLoopStage.INTENT,
        WaveSixLoopStage.PERMISSION,
        WaveSixLoopStage.PREDICTION,
        WaveSixLoopStage.TRIAL,
        WaveSixLoopStage.OUTCOME,
        WaveSixLoopStage.DELTA,
        WaveSixLoopStage.MEMORY_UPDATE,
        WaveSixLoopStage.TRANSFER_CHECK,
        WaveSixLoopStage.FALSIFICATION,
        WaveSixLoopStage.HUMAN_REVIEW,
    )
    assert artifact.decision is WaveSixDecisionState.NEEDS_MORE_EVIDENCE
    assert artifact.produced_by_engine_id == WAVE_SIX_IX_HANDOFF_ENGINE_ID
    assert artifact.evidence_ids == (
        "ix-kernel-handoff:wave6_measured_cognition:kernel-handoff-json",
    )
    assert not artifact.allows_autonomous_execution
    assert not artifact.claims_agi
    assert not artifact.self_validated


def test_ix_handoff_rejects_wrong_handoff_type() -> None:
    payload = _canonical_payload()
    payload["handoff_type"] = "ix.other.handoff"

    with pytest.raises(ValueError, match="IX kernel handoff type"):
        load_ix_cognition_handoff(payload)


def test_ix_handoff_rejects_wrong_target() -> None:
    payload = _canonical_payload()
    payload["packages"][0]["target"] = "OtherKernel"

    with pytest.raises(ValueError, match="IX handoff target"):
        load_ix_cognition_handoff(payload)


def test_ix_handoff_rejects_execution_authority() -> None:
    payload = _canonical_payload()
    payload["packages"][0]["execution_authority"] = "execute"

    with pytest.raises(ValueError, match="execution authority"):
        load_ix_cognition_handoff(payload)


def test_ix_handoff_rejects_self_certification() -> None:
    payload = _canonical_payload()
    payload["packages"][0]["self_certification_allowed"] = True

    with pytest.raises(ValueError, match="must not allow self-certification"):
        load_ix_cognition_handoff(payload)


def test_ix_handoff_rejects_missing_human_authority() -> None:
    payload = _canonical_payload()
    payload["packages"][0]["human_authority_required"] = False

    with pytest.raises(ValueError, match="must require human authority"):
        load_ix_cognition_handoff(payload)


def test_ix_handoff_rejects_missing_obligation() -> None:
    payload = _canonical_payload()
    payload["packages"][0]["obligations"] = payload["packages"][0]["obligations"][:-1]

    with pytest.raises(ValueError, match="Missing IX cognition obligation"):
        load_ix_cognition_handoff(payload)


def test_ix_handoff_rejects_noncanonical_obligation() -> None:
    payload = _canonical_payload()
    payload["packages"][0]["obligations"][0]["canonical"] = False

    with pytest.raises(ValueError, match="must be marked canonical"):
        load_ix_cognition_handoff(payload)


def test_ix_handoff_rejects_canonical_definition_drift() -> None:
    payload = _canonical_payload()
    definition = payload["packages"][0]["obligations"][0]["canonical_definition"]
    definition["title"] = "Changed title"

    with pytest.raises(ValueError, match="definition drift"):
        load_ix_cognition_handoff(payload)


def test_ix_handoff_rejects_unknown_evidence_requirement() -> None:
    payload = _canonical_payload()
    payload["packages"][0]["obligations"][0]["evidence_required"] = [
        "not_canonical_evidence",
    ]

    with pytest.raises(ValueError, match="not canonical"):
        load_ix_cognition_handoff(payload)


def test_ix_handoff_rejects_duplicate_attempt_packages() -> None:
    payload = _canonical_payload()
    payload["packages"].append(copy.deepcopy(payload["packages"][0]))

    with pytest.raises(ValueError, match="Duplicate attempt"):
        load_ix_cognition_handoff(payload)
