# ROBIN — Asistente virtual de escritorio para Windows

ROBIN vive en la bandeja del sistema y se activa diciendo **"Oye Robin"** o pulsando **Alt + X**.
Responde con voz propia (español de Perú), usa tu cuenta de **ChatGPT** con el inicio de sesión oficial de
OpenAI (sin API keys), abre apps, archivos y webs, usa tus apps conectadas de ChatGPT (Google Calendar,
Gmail…) pidiendo permiso antes de cambiar nada, y aprende tus rutinas para crear automatizaciones en Python.

## Funciones

- Ventana flotante estilo *glass* (abajo a la izquierda), sin historial: un asistente de órdenes rápidas.
- "Oye Robin" y dictado 100 % locales (Silero VAD + Whisper); huella de voz para responder solo a ti.
- Voz `es-PE-CamilaNeural` (edge-tts), hablando frase a frase mientras llega la respuesta.
- Acciones seguras en el PC: abrir apps, webs, documentos y buscar archivos (sin terminal).
- Configuración inicial: tu nombre y entrenamiento de voz.
- Detección de rutinas repetidas → scripts `.py` revisables en `Documentos\ROBIN\automatizaciones`.
- Ajustes con un switch por cada permiso; todo lo aprendido se queda en tu PC.

## Requisitos

- Windows 10/11, micrófono.
- [uv](https://docs.astral.sh/uv/) (instala Python 3.12 automáticamente).
- Una cuenta de ChatGPT de pago (Plus o superior).

## Uso (desarrollo)

```powershell
uv sync          # instala dependencias
uv run robin     # inicia ROBIN en la bandeja del sistema
uv run pytest    # tests
```

La primera vez se abre el navegador para iniciar sesión en ChatGPT y se descargan los modelos de voz
(~250 MB, una sola vez).

## Documentación

Toda la documentación (reglas, plan, estado, decisiones de arquitectura y aprendizajes) está en
[`docs/`](docs/README.md). Las instrucciones para agentes de IA están en `CLAUDE.md`, `GEMINI.md` y
`AGENTS.md` (idénticos).
