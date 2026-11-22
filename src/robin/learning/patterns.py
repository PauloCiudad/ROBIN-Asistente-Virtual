"""Detección de rutinas repetidas a partir del registro de actividad (funciones puras, fáciles de probar).

Rutinas que se detectan:
  1. Inicio del día: apps y archivos que el usuario abre en los primeros minutos de su jornada casi todos
     los días (≥3 días y ≥50 % de sus últimos días activos).
  2. Combinaciones de acciones que le pide a ROBIN juntas (≥2 acciones en la misma sesión, ≥3 días).
"""

from __future__ import annotations

import hashlib
import os
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from urllib.parse import urlparse

from robin.learning.activity import Event

START_WINDOW_S = 30 * 60
SESSION_GAP_S = 10 * 60
MIN_DAYS = 3
RECENT_ACTIVE_DAYS = 7
MAX_STEPS = 6

_FRIENDLY_EXES = {
    "msedge": "Edge", "chrome": "Chrome", "firefox": "Firefox", "winword": "Word", "excel": "Excel",
    "powerpnt": "PowerPoint", "outlook": "Outlook", "olk": "Outlook", "ms-teams": "Teams", "teams": "Teams",
    "code": "VS Code", "spotify": "Spotify", "notepad": "Bloc de notas", "acrord32": "Acrobat",
    "chatgpt": "ChatGPT", "windowsterminal": "Terminal", "whatsapp": "WhatsApp",
}


@dataclass(frozen=True)
class Step:
    kind: str  # "open_app_path" | "open_app_id" | "open_path" | "open_url"
    target: str
    label: str


@dataclass
class Pattern:
    kind: str  # "inicio_dia" | "rutina_acciones"
    title: str
    description: str
    steps: list[Step]
    days: int
    trigger: str  # cómo pedírsela a ROBIN
    id: str = field(default="")

    def __post_init__(self) -> None:
        if not self.id:
            key = "|".join(sorted(f"{s.kind}:{s.target.casefold()}" for s in self.steps))
            self.id = hashlib.sha1(f"{self.kind}|{key}".encode()).hexdigest()[:12]


def friendly_exe(exe: str) -> str:
    stem = os.path.splitext(os.path.basename(exe))[0]
    return _FRIENDLY_EXES.get(stem.casefold(), stem[:1].upper() + stem[1:])


def step_from_event(event: Event) -> Step | None:
    meta = event.meta or {}
    if event.source == "app" and meta.get("path"):
        return Step("open_app_path", meta["path"], friendly_exe(event.value))
    if event.source == "file" and meta.get("path"):
        return Step("open_path", meta["path"], os.path.basename(meta["path"]))
    if event.source == "action":
        if event.kind == "open_app" and meta.get("app_id"):
            return Step("open_app_id", meta["app_id"], event.value)
        if event.kind == "open_path" and meta.get("path"):
            return Step("open_path", meta["path"], event.value)
        if event.kind == "open_url" and meta.get("url"):
            return Step("open_url", meta["url"], urlparse(meta["url"]).netloc or event.value)
    return None


def _join_labels(labels: list[str]) -> str:
    if len(labels) <= 1:
        return "".join(labels)
    return ", ".join(labels[:-1]) + " y " + labels[-1]


def _daily_start_routine(events: list[Event]) -> Pattern | None:
    by_day: dict[str, list[Event]] = defaultdict(list)
    for e in events:
        if e.source in ("app", "file", "action"):
            by_day[e.day].append(e)
    active_days = sorted(by_day)[-RECENT_ACTIVE_DAYS:]
    if len(active_days) < MIN_DAYS:
        return None
    seen_days: dict[Step, set[str]] = defaultdict(set)
    offsets: dict[Step, list[float]] = defaultdict(list)
    for day in active_days:
        day_events = sorted(by_day[day], key=lambda e: e.ts)
        start = day_events[0].ts
        for e in day_events:
            if e.ts - start > START_WINDOW_S:
                break
            step = step_from_event(e)
            if step is not None and day not in seen_days[step]:
                seen_days[step].add(day)
                offsets[step].append(e.ts - start)
    needed = max(MIN_DAYS, (len(active_days) + 1) // 2)
    frequent = [s for s, days in seen_days.items() if len(days) >= needed]
    if len(frequent) < 2:
        return None
    frequent.sort(key=lambda s: statistics.median(offsets[s]))
    steps = frequent[:MAX_STEPS]
    days = min(len(seen_days[s]) for s in steps)
    labels = [s.label for s in steps]
    return Pattern(
        kind="inicio_dia",
        title="Rutina de inicio del día",
        description=f"Casi todos los días, al empezar, abres {_join_labels(labels)} "
                    f"({days} de tus últimos {len(active_days)} días).",
        steps=steps,
        days=days,
        trigger="ejecuta mi rutina de inicio",
    )


def _robin_action_routines(events: list[Event]) -> list[Pattern]:
    actions = sorted((e for e in events if e.source == "action"), key=lambda e: e.ts)
    sessions: list[list[Event]] = []
    for e in actions:
        if sessions and e.ts - sessions[-1][-1].ts <= SESSION_GAP_S:
            sessions[-1].append(e)
        else:
            sessions.append([e])
    days_by_signature: dict[frozenset, set[str]] = defaultdict(set)
    order_by_signature: dict[frozenset, list[Step]] = {}
    for session in sessions:
        steps: list[Step] = []
        for e in session:
            step = step_from_event(e)
            if step is not None and step not in steps:
                steps.append(step)
        if len(steps) < 2:
            continue
        signature = frozenset(steps[:MAX_STEPS])
        days_by_signature[signature].add(session[0].day)
        order_by_signature.setdefault(signature, steps[:MAX_STEPS])
    patterns = []
    for signature, days in days_by_signature.items():
        if len(days) < MIN_DAYS:
            continue
        steps = order_by_signature[signature]
        labels = [s.label for s in steps]
        patterns.append(Pattern(
            kind="rutina_acciones",
            title=f"Abrir {_join_labels(labels)}",
            description=f"Me has pedido abrir {_join_labels(labels)} juntos en {len(days)} días distintos.",
            steps=steps,
            days=len(days),
            trigger=f"ejecuta abrir {labels[0]}",
        ))
    return patterns


def detect_patterns(events: list[Event]) -> list[Pattern]:
    found: list[Pattern] = []
    start = _daily_start_routine(events)
    if start is not None:
        found.append(start)
    found.extend(_robin_action_routines(events))
    return sorted(found, key=lambda p: -p.days)
