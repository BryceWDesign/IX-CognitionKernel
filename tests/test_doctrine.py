import pytest

from ix_cognition_kernel.doctrine import (
    FORBIDDEN_CLAIMS_BEFORE_WAVE_6,
    NON_ATTACHED_PURPOSE_RULES,
    WAVE_LADDER,
    ClaimBoundary,
    allows_agi_claim,
    current_wave,
    doctrine_summary,
    final_wave,
    wave_by_number,
)


def test_wave_ladder_is_locked_from_zero_to_six() -> None:
    assert [wave.number for wave in WAVE_LADDER] == list(range(7))
    assert WAVE_LADDER[0].name == "Repository Foundation"
    assert WAVE_LADDER[6].name == "AGI, Only If Overwhelming Evidence Justifies It"


def test_current_wave_is_repository_foundation() -> None:
    wave = current_wave()

    assert wave.number == 0
    assert wave.claim_boundary is ClaimBoundary.FOUNDATION
    assert "no AGI overclaim" in wave.final_form


def test_final_wave_is_evidence_gated() -> None:
    wave = final_wave()

    assert wave.number == 6
    assert wave.claim_boundary is ClaimBoundary.AGI_ONLY_WITH_OVERWHELMING_EVIDENCE
    assert "independently validated general intelligence" in wave.final_form


def test_wave_lookup_rejects_unknown_wave_numbers() -> None:
    with pytest.raises(ValueError, match="Unknown IX-CognitionKernel wave number"):
        wave_by_number(7)


def test_agi_claim_requires_wave_six_and_overwhelming_evidence() -> None:
    assert allows_agi_claim(6, overwhelming_evidence=True) is True
    assert allows_agi_claim(6, overwhelming_evidence=False) is False
    assert allows_agi_claim(5, overwhelming_evidence=True) is False


def test_non_attached_purpose_rules_are_architectural() -> None:
    assert "truth-over-winning" in NON_ATTACHED_PURPOSE_RULES
    assert "evidence-over-confidence" in NON_ATTACHED_PURPOSE_RULES
    assert "human-authority-preserved" in NON_ATTACHED_PURPOSE_RULES
    assert "no-runtime-reward-chasing-purpose" in NON_ATTACHED_PURPOSE_RULES


def test_forbidden_claims_prevent_early_overclaiming() -> None:
    assert "AGI achieved" in FORBIDDEN_CLAIMS_BEFORE_WAVE_6
    assert "independently validated AGI" in FORBIDDEN_CLAIMS_BEFORE_WAVE_6
    assert "production-ready autonomy" in FORBIDDEN_CLAIMS_BEFORE_WAVE_6


def test_doctrine_summary_preserves_locked_principles() -> None:
    summary = doctrine_summary()

    assert "architectural, not mystical" in summary
    assert "truth over winning" in summary
    assert "evidence over confidence" in summary
    assert "no AGI claim without overwhelming independent evidence" in summary
