from ix_cognition_kernel import PROJECT_NAME, WAVE, __version__


def test_package_identity_is_locked() -> None:
    assert PROJECT_NAME == "IX-CognitionKernel"
    assert WAVE == "Wave 2"
    assert __version__ == "0.2.0"
