# ROBIN — Instrucciones para agentes de IA

> **Este archivo existe en tres copias idénticas: `CLAUDE.md`, `GEMINI.md` y `AGENTS.md`.**
> Si modificas uno, aplica exactamente el mismo cambio a los otros dos. Nunca deben diferir.

## Qué es este proyecto

ROBIN es una asistente virtual de escritorio para Windows (PC personal). Vive en la bandeja del sistema (tray),
siempre a la espera. Se activa por voz ("**Oye Robin**") o con el atajo **Alt + X**, que abre una pequeña
interfaz con estilo *glass*. Habla con voz propia (mujer de ~30 años, amigable). Se conecta a ChatGPT/OpenAI
mediante **inicio de sesión OAuth con la cuenta de ChatGPT, nunca con API key**. Detecta tareas repetitivas y
genera scripts de Python para automatizarlas. Con el tiempo sumará integraciones (Google Calendar, etc.).

## Fuente única de verdad: carpeta `docs/`

Todas las reglas, planes, estado y aprendizajes del repositorio viven en `docs/`. **Léela antes de trabajar.**

| Archivo | Contenido |
|---|---|
| [docs/README.md](docs/README.md) | Índice y visión general |
| [docs/reglas.md](docs/reglas.md) | Reglas obligatorias de trabajo y de código |
| [docs/plan.md](docs/plan.md) | Hoja de ruta por fases |
| [docs/estado.md](docs/estado.md) | Estado actual, en qué se está trabajando, próximos pasos |
| [docs/decisiones.md](docs/decisiones.md) | Registro de decisiones de arquitectura (ADR) |
| [docs/aprendizajes.md](docs/aprendizajes.md) | Lecciones aprendidas, trampas y soluciones |
| [docs/arquitectura.md](docs/arquitectura.md) | Estructura del código, hilos y flujo |
| [docs/investigacion/](docs/investigacion/) | Investigaciones técnicas de soporte |

## Reglas esenciales (resumen; el detalle está en `docs/reglas.md`)

1. Idioma: la documentación, los mensajes al usuario y la voz de ROBIN son en **español**. El código
   (identificadores) en inglés; comentarios en español cuando aporten.
2. **Prohibido usar API keys de proveedores de IA.** El acceso a OpenAI es solo vía "Sign in with ChatGPT" (OAuth).
3. Nunca guardar tokens, credenciales ni datos personales en el repositorio ni en logs.
4. Al terminar una tarea: actualiza `docs/estado.md`; si tomaste una decisión de arquitectura, agrégala a
   `docs/decisiones.md`; si aprendiste algo no obvio, agrégalo a `docs/aprendizajes.md`.
5. No agregar dependencias ni cambiar el stack sin registrarlo en `docs/decisiones.md`.
6. Mantener `CLAUDE.md`, `GEMINI.md` y `AGENTS.md` idénticos.

## Stack y comandos

Python 3.12 + PySide6, gestionado con `uv` (ver `docs/decisiones.md`).

```powershell
uv sync          # instalar dependencias
uv run robin     # ejecutar ROBIN (bandeja del sistema; Alt + X abre la ventana)
uv run pytest    # tests
powershell -ExecutionPolicy Bypass -File packaging\build.ps1   # ejecutable + instalador (requiere Inno Setup 6)
```
