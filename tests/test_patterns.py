import py_compile
import time
from datetime import datetime, timedelta
from pathlib import Path

from robin.learning.activity import ActivityLog, Event
from robin.learning.automations import AutomationStore
from robin.learning.patterns import Step, detect_patterns


def _ts(day_offset: int, hour: int, minute: int) -> float:
    base = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=day_offset)
    return (base + timedelta(hours=hour, minutes=minute)).timestamp()


def _app(day, h, m, exe):
    return Event(_ts(day, h, m), "app", "app_open", exe, {"path": rf"C:\Program Files\X\{exe}"})


def _file(day, h, m, path):
    return Event(_ts(day, h, m), "file", "file_open", Path(path).name, {"path": path})


def test_daily_start_routine_detected():
    events = []
    for day in range(1, 6):  # 5 días: Outlook + Excel + informe al empezar; Chrome a veces y tarde
        events += [_app(day, 8, 0, "OUTLOOK.EXE"), _app(day, 8, 3, "EXCEL.EXE"),
                   _file(day, 8, 5, r"C:\Users\p\Documents\informe.xlsx")]
        if day % 2:
            events.append(_app(day, 11, 0, "chrome.exe"))  # fuera de la ventana de inicio
    patterns = detect_patterns(events)
    assert len(patterns) == 1
    p = patterns[0]
    assert p.kind == "inicio_dia"
    assert [s.label for s in p.steps] == ["Outlook", "Excel", "informe.xlsx"]
    assert p.days == 5


def test_no_pattern_with_too_few_days():
    events = [_app(d, 8, 0, "OUTLOOK.EXE") for d in (1, 2)] + [_app(d, 8, 2, "EXCEL.EXE") for d in (1, 2)]
    assert detect_patterns(events) == []


def test_robin_action_routine_detected():
    events = []
    for day in (1, 3, 6):
        events += [
            Event(_ts(day, 15, 0), "action", "open_app", "Excel", {"app_id": "excel!App"}),
            Event(_ts(day, 15, 1), "action", "open_url", "https://erp.example.com", {"url": "https://erp.example.com"}),
        ]
    events.append(Event(_ts(2, 9, 0), "action", "open_app", "Excel", {"app_id": "excel!App"}))  # suelta
    patterns = [p for p in detect_patterns(events) if p.kind == "rutina_acciones"]
    assert len(patterns) == 1
    assert [s.kind for s in patterns[0].steps] == ["open_app_id", "open_url"]


def test_pattern_id_is_stable():
    a = detect_patterns([_app(d, 8, 0, "OUTLOOK.EXE") for d in range(1, 5)] +
                        [_app(d, 8, 1, "EXCEL.EXE") for d in range(1, 5)])[0]
    b = detect_patterns([_app(d, 9, 0, "OUTLOOK.EXE") for d in range(2, 6)] +
                        [_app(d, 9, 1, "EXCEL.EXE") for d in range(2, 6)])[0]
    assert a.id == b.id


def test_store_creates_valid_script_and_dry_run(tmp_path: Path):
    events = []
    for day in range(1, 5):
        events += [_app(day, 8, 0, "OUTLOOK.EXE"), _file(day, 8, 2, r"C:\docs\plan.pdf"),
                   Event(_ts(day, 8, 4), "action", "open_url", "https://mail.google.com",
                         {"url": "https://mail.google.com"})]
    pattern = detect_patterns(events)[0]
    store = AutomationStore(folder=tmp_path, state_path=tmp_path / "state.json")
    automation = store.create(pattern)
    script = tmp_path / automation.file
    py_compile.compile(str(script), doraise=True)
    out, _ = store.run(automation, dry_run=True).communicate(timeout=30)
    assert "[simulación] Abriendo Outlook" in out and "plan.pdf" in out and "mail.google.com" in out
    assert store.find("rutina de inicio") == store.list()[0]
    assert not store.should_suggest(pattern)  # ya automatizada
    assert not store.list()[0].approved
    store.approve(automation)
    assert store.list()[0].approved


def test_run_automation_requires_first_approval(tmp_path: Path):
    from robin.actions.tools import ActionRunner
    from robin.learning.patterns import Pattern

    store = AutomationStore(folder=tmp_path, state_path=tmp_path / "state.json")
    pattern = Pattern("inicio_dia", "Rutina de inicio del día", "Abres a y b.",
                      [Step("open_url", "https://a.com", "a"), Step("open_url", "https://b.com", "b")], 3,
                      "ejecuta mi rutina de inicio")
    store.create(pattern)
    ran = []
    store.run = lambda automation, dry_run=False: ran.append(automation.name)  # no abrir nada en el test
    answers = iter([False, True])
    asked = []

    def confirm(question):
        asked.append(question)
        return next(answers)

    runner = ActionRunner.__new__(ActionRunner)
    runner._is_allowed, runner._on_action, runner._automations, runner._confirm = (lambda: True), None, store, confirm
    runner._handlers = {"run_automation": runner._run_automation, "list_automations": runner._list_automations}

    assert "Rutina de inicio" in runner.run("list_automations", {}).text
    refused = runner.run("run_automation", {"name": "rutina de inicio"})
    assert not refused.success and ran == []
    accepted = runner.run("run_automation", {"name": "mi rutina de inicio"})
    assert accepted.success and ran == ["Rutina de inicio del día"]
    assert store.list()[0].approved
    runner.run("run_automation", {"name": "rutina de inicio"})  # ya aprobada: no vuelve a preguntar
    assert len(asked) == 2 and len(ran) == 2


def test_snooze_and_dismiss(tmp_path: Path):
    store = AutomationStore(folder=tmp_path, state_path=tmp_path / "state.json")
    from robin.learning.patterns import Pattern
    p = Pattern("inicio_dia", "t", "d", [Step("open_url", "https://a.com", "a"), Step("open_url", "https://b.com", "b")], 3, "x")
    assert store.should_suggest(p)
    store.snooze(p.id)
    assert not store.should_suggest(p)
    store.reset_suggestions()
    store.dismiss(p.id)
    assert not store.should_suggest(p)


def test_activity_log_roundtrip(tmp_path: Path):
    log = ActivityLog(tmp_path / "a.db")
    log.record("app", "app_open", "EXCEL.EXE", {"path": "C:/x/EXCEL.EXE"})
    log.record("file", "file_open", "a.pdf", {"path": "C:/a.pdf"}, ts=time.time() - 30 * 86400)
    assert [e.value for e in log.events(since_days=7)] == ["EXCEL.EXE"]
    assert log.count() == 2
    log.clear()
    assert log.count() == 0
    log.close()
