# Investigación: lenguaje y stack para ROBIN

Fecha: 2026-11-21

## Requisitos que condicionan la elección

| Requisito | Qué exige técnicamente |
|---|---|
| Login OAuth con ChatGPT (sin API key) | Hablar con el **Codex app-server** (JSON-RPC por stdio). SDK oficiales solo en **Python** (`openai-codex`) y **TypeScript** (`@openai/codex-sdk`). |
| "Oye Robin" siempre escuchando | Motor de wake word local y ligero. Porcupine queda descartado (fin del free tier 2026-06-30). Opción viable: **openWakeWord** (Python/ONNX, entrenable con frases propias). |
| Voz → texto en español | Whisper local (**faster-whisper**, Python) o whisper.cpp. |
| Voz propia de mujer ~30 años | **edge-tts** (voces neuronales de Microsoft, gratis, requiere internet; incluye voces como `es-PE-CamilaNeural`, `es-MX-DaliaNeural`, `es-ES-ElviraNeural`) o **Kokoro / Piper** (local, offline). |
| Tray + atajo global Alt + X | Disponible en todos los stacks. |
| Ventana glass | Mica/Acrylic de Windows 11: nativo en WinUI 3; en Qt/Tauri/Electron mediante APIs de DWM o plugins. |
| Generar scripts Python por patrones | Se necesita Python en el equipo de todos modos para ejecutarlos. |

La conclusión clave: **el ecosistema de voz local (wake word, STT, TTS) y el SDK de ChatGPT existen de forma
madura en Python**. Cualquier otro stack termina necesitando Python como proceso auxiliar o reimplementar piezas.

## Opciones

### Opción A — Python puro (recomendada)

- UI: **PySide6 (Qt 6) + QML**, ventana sin bordes con efecto Acrylic/Mica vía DWM.
- Tray: `QSystemTrayIcon`. Atajo global: `keyboard` / `pynput` o `RegisterHotKey` vía `pywin32`.
- IA: `openai-codex` (SDK oficial, controla el Codex app-server; login "Sign in with ChatGPT").
- Wake word: openWakeWord (modelo propio "oye robin"). STT: faster-whisper. TTS: edge-tts o Kokoro.
- Empaquetado: PyInstaller o Nuitka.
- **Pros:** todo en un solo lenguaje; todas las piezas críticas tienen librerías maduras; los scripts
  generados por patrones corren en el mismo runtime; desarrollo rápido.
- **Contras:** ejecutable más pesado (~150–300 MB con modelos); la UI glass requiere algo de trabajo con DWM;
  hay que fijar Python 3.12/3.13 (el 3.15 instalado es demasiado nuevo).

### Opción B — Híbrido Tauri (Rust + web) con "sidecar" Python

- UI en HTML/CSS/JS (glass muy fácil con CSS + `window-vibrancy` para Mica/Acrylic), tray y atajo global
  con plugins oficiales de Tauri. Proceso Python aparte para voz e IA.
- **Pros:** la UI más bonita y ligera (WebView2 del sistema); ejecutable de la shell pequeño.
- **Contras:** tres lenguajes (Rust, TS, Python) y comunicación entre procesos; hay que instalar Rust;
  más complejidad para un proyecto personal.

### Opción C — Electron + TypeScript

- SDK oficial `@openai/codex-sdk` en TS; UI web; `backgroundMaterial: 'acrylic'` en Windows.
- **Pros:** un solo lenguaje para UI e IA; ecosistema enorme.
- **Contras:** pesado (~150 MB+ y bastante RAM para estar siempre en el tray); wake word y STT en Node son
  menos maduros (habría que usar onnxruntime-node / whisper.cpp con bindings); igual se necesita Python para
  los scripts de automatización.

### Opción D — C# / .NET con WinUI 3

- La plataforma nativa recomendada por Microsoft; Mica/Acrylic y tray de primera clase, bajo consumo.
- **Contras:** no hay SDK oficial de Codex en C# (hay que implementar el JSON-RPC del app-server a mano);
  openWakeWord y Whisper vía ONNX Runtime/whisper.net con más trabajo manual; .NET no está instalado;
  igual se necesita Python para los scripts.

## Comparativa

| Criterio | A: Python | B: Tauri + Python | C: Electron | D: C# WinUI |
|---|---|---|---|---|
| Login ChatGPT oficial | SDK oficial | SDK oficial (sidecar) | SDK oficial | Manual |
| Wake word / STT / TTS locales | Excelente | Excelente (sidecar) | Regular | Regular |
| Estilo glass | Bueno | Excelente | Bueno | Excelente |
| Consumo en reposo | Medio | Bajo–medio | Alto | Bajo |
| Complejidad | Baja | Alta | Media | Media–alta |
| Scripts Python por patrones | Nativo | Nativo | Requiere Python | Requiere Python |

## Recomendación

**Opción A (Python + PySide6/QML)** para empezar: es la que menos piezas tiene, y todas las capacidades
difíciles (login ChatGPT, wake word, STT, TTS, generación de scripts) son nativas de Python. La arquitectura
modular permite migrar la UI a Tauri (opción B) más adelante si se quiere una interfaz más vistosa, sin tocar
el núcleo.

## Fuentes

- Codex App Server (login ChatGPT, JSON-RPC): https://developers.openai.com/codex/app-server
- Sign in with ChatGPT para apps open-source locales: https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server
- Codex SDK (Python / TypeScript): https://developers.openai.com/codex/sdk
- Fin del free tier de Picovoice: https://community.home-assistant.io/t/fyi-picovoice-confirmed-free-tier-accesskeys-will-stop-working-after-june-30-2026/1012744
- openWakeWord: https://github.com/dscripka/openWakeWord
- Wake words en Home Assistant: https://home-assistant.io/voice_control/about_wake_word
- Comparativa TTS en español: https://dev.to/tarunyadav1/spanish-text-to-speech-best-voices-and-models-204b
- Piper vs Kokoro: https://www.promptquorum.com/es/power-local-llm/piper-vs-kokoro-tts
- Frameworks de escritorio 2026: https://teamdev.com/mobrowser/blog/top-7-desktop-app-frameworks-in-2026/
- Tauri 2026: https://dev.to/ottoaria/tauri-in-2026-build-cross-platform-desktop-apps-with-web-technologies-better-than-electron-11mo
- WinUI 3 / Windows App SDK: https://learn.microsoft.com/en-us/windows/apps/get-started/windows-developer-faq
