from pathlib import Path

from robin.actions.apps import App, AppIndex
from robin.actions.files import find_files, known_folder, resolve_path
from robin.actions.text_match import normalize, score
from robin.actions.tools import ActionRunner


def test_normalize_strips_accents_and_symbols():
    assert normalize("Música  (Groove)") == "musica groove"


def test_score_prefers_exact_and_prefix():
    assert score("excel", "excel") == 1.0
    assert score("excel", "excel 2016") > score("excel", "access")


def _index_with(apps: list[App]) -> AppIndex:
    index = AppIndex()
    index._apps = apps
    index._loaded_at = 10**12  # evita recargar desde PowerShell
    return index


def test_app_search_uses_spanish_alias():
    index = _index_with([App("Calculator", "calc!App"), App("Calendar", "cal!App"), App("Spotify", "sp")])
    best = index.search("calculadora")[0][1]
    assert best.name == "Calculator"


def test_known_folders_resolve():
    downloads = known_folder("descargas")
    assert downloads is not None and downloads.exists()
    assert resolve_path("Downloads") == downloads


def test_find_files(tmp_path: Path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "Informe de Ventas 2026.xlsx").write_text("x")
    (tmp_path / "otro.txt").write_text("x")
    found = find_files("informe ventas", [tmp_path])
    assert [p.name for p in found] == ["Informe de Ventas 2026.xlsx"]


def _runner(allowed: bool = True) -> ActionRunner:
    runner = ActionRunner.__new__(ActionRunner)
    runner._is_allowed = lambda: allowed
    runner._on_action = None
    runner._automations = None
    runner._confirm = None
    runner.apps = _index_with([App("Spotify", "sp")])
    runner._handlers = {
        "open_app": runner._open_app,
        "open_url": runner._open_url,
        "open_path": runner._open_path,
        "find_files": runner._find_files,
    }
    return runner


def test_tools_respect_switch():
    result = _runner(allowed=False).run("open_url", {"url": "https://example.com"})
    assert not result.success and "Ajustes" in result.text


def test_open_url_rejects_non_web_schemes():
    result = _runner().run("open_url", {"url": "file:///C:/Windows/System32/cmd.exe"})
    assert not result.success


def test_open_path_blocks_executables(tmp_path: Path):
    script = tmp_path / "malo.bat"
    script.write_text("echo hola")
    result = _runner().run("open_path", '{"path": "%s"}' % str(script).replace("\\", "\\\\"))
    assert not result.success and "seguridad" in result.text


def test_open_app_unknown_returns_suggestions():
    result = _runner().run("open_app", {"name": "photoshop"})
    assert not result.success and "Parecidas" in result.text
