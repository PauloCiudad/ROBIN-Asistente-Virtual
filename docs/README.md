# ROBIN — Documentación

Asistente virtual de escritorio para Windows 11. Esta carpeta es la **fuente única de verdad** del proyecto
para humanos y agentes de IA (Claude, Gemini, Codex, etc.).

## Visión

ROBIN está siempre en la bandeja del sistema, escuchando de forma local y ligera. Cuando el usuario dice
"**Oye Robin**" o pulsa **Alt + X**, se activa, escucha la petición, la resuelve con ayuda de ChatGPT
(sesión OAuth del usuario, plan Plus) y responde con su propia voz (acento peruano) y en una pequeña ventana
con estilo *glass*.

## Stack

Python 3.12 + PySide6, gestionado con `uv`. IA vía SDK oficial `openai-codex` ("Sign in with ChatGPT").
Detalle en [decisiones.md](decisiones.md).

## Cómo ejecutar (desarrollo)

```powershell
uv sync          # instala dependencias en .venv (Python 3.12)
uv run robin     # arranca ROBIN (queda en la bandeja; Alt + X abre la ventana)
```

## Capacidades previstas

| Capacidad | Fase | Estado |
|---|---|---|
| App en tray, instancia única, iniciar con Windows | 1 | Hecho |
| Atajo global Alt + X → ventana glass | 1 | Hecho |
| Login OAuth con ChatGPT (sin API key) | 1 | Hecho |
| Chat por texto con ChatGPT (streaming) | 1 | Hecho |
| Panel de ajustes con switches (ADR-003) | 1 | Hecho (los switches de fases futuras se guardan, sin efecto aún) |
| Palabra de activación "Oye Robin" | 2 | Hecho (v1) |
| Reconocimiento de voz (voz → texto) + botón de micrófono | 2 | Hecho |
| Voz propia peruana (`es-PE-CamilaNeural`) | 2 | Hecho |
| Abrir apps, archivos y webs del PC | 2 | Hecho |
| Configuración inicial: nombre + entrenamiento de voz, "solo mi voz" | 2.5 | Hecho |
| Detección de patrones → genera scripts Python | 3 | Hecho (v1) |
| Google Calendar, Gmail y demás apps conectadas en ChatGPT | 4 | Lectura verificada; escritura con permiso del usuario (sin prueba real) |
| Otras funciones (las irá definiendo el usuario) | 4+ | Pendiente |

## Índice

- [reglas.md](reglas.md) — reglas obligatorias
- [plan.md](plan.md) — hoja de ruta
- [estado.md](estado.md) — estado actual
- [decisiones.md](decisiones.md) — decisiones de arquitectura (ADR)
- [aprendizajes.md](aprendizajes.md) — lecciones aprendidas
- [arquitectura.md](arquitectura.md) — estructura del código y flujo
- [investigacion/stack-tecnologico.md](investigacion/stack-tecnologico.md) — análisis de lenguajes y librerías
