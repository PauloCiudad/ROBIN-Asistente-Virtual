import pytest

from robin.voice import stt
from robin.voice.stt import extract_name, find_wake, wake_variant_from


@pytest.mark.parametrize(
    "text, name",
    [
        ("Me llamo Paulo.", "Paulo"),
        ("Hola, mi nombre es Paulo Ciudad", "Paulo Ciudad"),
        ("Soy María.", "María"),
        ("Paulo", "Paulo"),
        ("paulo.", "Paulo"),
        ("", ""),
    ],
)
def test_extract_name(text, name):
    assert extract_name(text) == name


def test_personal_variant_learned_and_used():
    assert wake_variant_from("Oye Rubén.") == "ruben"
    assert wake_variant_from("Oye, ¿bien?") is None  # no se parece a "robin"
    assert wake_variant_from("Oye Robin") is None  # ya se reconoce
    assert find_wake("Oye Rubén, abre Excel")[0] is False
    stt.set_personal_variants({"ruben"})
    try:
        assert find_wake("Oye Rubén, abre Excel") == (True, "abre Excel")
    finally:
        stt.set_personal_variants(set())


@pytest.mark.parametrize(
    "text, command",
    [
        ("Oye Robin.", ""),
        ("Oye, Robin, abre Excel.", "abre Excel."),
        ("Robin, ¿qué hora es?", "¿qué hora es?"),
        ("Hey Robín abre mis descargas", "abre mis descargas"),
        ("Oye Robbin", ""),
    ],
)
def test_wake_detected(text, command):
    assert find_wake(text) == (True, command)


@pytest.mark.parametrize(
    "text",
    ["Hola, ¿cómo estás?", "Ayer vi la película de Batman y Robin", "Oye, ¿viste el partido?", ""],
)
def test_wake_not_detected(text):
    assert find_wake(text)[0] is False


def test_strict_requires_caller():
    assert find_wake("Robin, abre Excel", strict=True)[0] is False
    assert find_wake("Oye Robin, abre Excel", strict=True)[0] is True
