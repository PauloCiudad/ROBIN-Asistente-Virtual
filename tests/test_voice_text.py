from robin.voice.text import SentenceSplitter, clean_for_speech


def test_clean_removes_markdown_and_urls():
    text = "**Hola** soy `ROBIN`. Mira [esta web](https://x.com) o https://y.com\n- punto uno"
    assert clean_for_speech(text) == "Hola soy ROBIN. Mira esta web o el enlace\npunto uno"


def test_splitter_emits_complete_sentences_while_streaming():
    s = SentenceSplitter(min_chars=10)
    out = []
    for delta in ["¡Hola! Soy ROBIN, tu asis", "tente. ¿En qué te ", "ayudo hoy?"]:
        out += s.feed(delta)
    assert out == ["¡Hola! Soy ROBIN, tu asistente."]
    assert s.flush() == ["¿En qué te ayudo hoy?"]


def test_splitter_skips_code_blocks():
    s = SentenceSplitter(min_chars=5)
    out = s.feed("Aquí va el código:\n```\nprint('x')\n```\nListo, eso es todo.\n")
    out += s.flush()
    assert out == ["Aquí va el código:", "Listo, eso es todo."]


def test_splitter_ignores_punctuation_only():
    s = SentenceSplitter(min_chars=1)
    assert s.feed("...\n") == []
